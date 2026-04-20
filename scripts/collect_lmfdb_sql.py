#!/usr/bin/env python3
"""
Bulk LMFDB weight-2 newform data collection via direct PostgreSQL access.

Connects to the LMFDB PostgreSQL mirror (devmirror.lmfdb.xyz:5432) to bulk-collect
weight-2 newform data with Hecke eigenvalues. Bypasses Cloudflare entirely.

Outputs:
    data/lmfdb/lmfdb_sql_weight2.json        -- raw SQL records (one JSON with all)
    data/lmfdb/lmfdb_sql_weight2_ml.csv      -- ML-ready CSV with scalar features + first 100 traces
    data/lmfdb/lmfdb_sql_traces_matrix.npy   -- numpy array (N, 1000) of Hecke traces
    data/lmfdb/lmfdb_sql_labels.json         -- labels corresponding to trace matrix rows

Usage:
    python collect_lmfdb_sql.py --test                     # Test connection + print counts
    python collect_lmfdb_sql.py                           # Full collection (default: levels 11-5000, trivial char)
    python collect_lmfdb_sql.py --max-level 1000          # Collect only up to level 1000
    python collect_lmfdb_sql.py --char-order 0             # ALL characters (not just trivial)
    python collect_lmfdb_sql.py --limit 5000               # Collect at most 5000 forms
    python collect_lmfdb_sql.py --no-traces-matrix         # Skip the large .npy file
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
import sys
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# psycopg2 import with helpful error message
# ---------------------------------------------------------------------------

try:
    import psycopg2
    from psycopg2 import sql as psql
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 is required but not installed.")
    print("  Install with:  pip install psycopg2-binary")
    print("  (or 'pip install psycopg2' if you have PostgreSQL dev headers)")
    sys.exit(1)

# ---------------------------------------------------------------------------
# JSON serialization helper
# ---------------------------------------------------------------------------


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, bytes, and other non-standard types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (bytes, memoryview)):
            return "<binary>"
        return super().default(obj)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_HOST = "devmirror.lmfdb.xyz"
DB_PORT = 5432
DB_NAME = "lmfdb"
DB_USER = "lmfdb"
DB_PASS = "lmfdb"

OUTPUT_DIR = Path("data/lmfdb")

ML_COLUMNS = [
    "label",
    "level",
    "dim",
    "analytic_rank",
    "analytic_conductor",
    "char_degree",
    "is_cm",
    "is_self_dual",
    "Nk2",
]
N_TRACE_CSV_COLS = 100  # First 100 Hecke traces as individual CSV columns
N_TRACE_MATRIX_COLS = 1000  # Full trace matrix for .npy

CONNECT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

NEWFORM_BATCH = 1000  # fetch newforms in batches
HECKE_BATCH = 10000  # fetch hecke eigenvalues per batch of orbit codes


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------


def connect_db(test: bool = False) -> "psycopg2.connection":
    """Connect to LMFDB PostgreSQL mirror with retry logic.

    Args:
        test: If True, use shorter timeout for quick connectivity check.

    Returns:
        psycopg2 connection object.

    Raises:
        SystemExit: If connection fails after all retries.
    """
    timeout = 10 if test else CONNECT_TIMEOUT
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(
                f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} "
                f"(attempt {attempt}/{MAX_RETRIES}, timeout={timeout}s)..."
            )
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                connect_timeout=timeout,
            )
            # Keep autocommit=False (default) so named cursors / transactions work
            print("  Connected successfully.")
            return conn

        except psycopg2.OperationalError as e:
            last_err = e
            print(f"  Connection failed: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
        except Exception as e:
            last_err = e
            print(f"  Unexpected error: {e}")
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)

    print(f"\nERROR: Failed to connect after {MAX_RETRIES} attempts.")
    print(f"  Last error: {last_err}")
    print(f"\nTroubleshooting:")
    print(f"  1. Check network connectivity: ping {DB_HOST}")
    print(f"  2. Check DNS resolution: nslookup {DB_HOST}")
    print(f"  3. Check firewall allows outbound TCP/{DB_PORT}")
    print(f"  4. Try from a different network (VPN may be required)")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Safe type extraction
# ---------------------------------------------------------------------------


def _safe_int(val, default=0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val, default=False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


def count_newforms(conn, min_level: int, max_level: int, char_order: int) -> int:
    """Count weight-2 newforms matching the filters."""
    if char_order == 0:
        where = "weight = 2"
        label = "all characters"
    else:
        where = f"weight = 2 AND char_order = {char_order}"
        label = f"char_order={char_order}"

    if min_level > 1 or max_level < float("inf"):
        level_filter = f" AND level >= {min_level} AND level <= {max_level}"
    else:
        level_filter = ""

    query = f"SELECT count(*) FROM mf_newforms WHERE {where}{level_filter}"
    print(f"\nCounting: {where}{level_filter}")

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            count = cur.fetchone()[0]
        print(
            f"  Found {count:,} weight-2 newforms ({label}, levels {min_level}..{max_level})"
        )
        return count
    except psycopg2.Error as e:
        print(f"  ERROR counting newforms: {e}")
        sys.exit(1)


def count_hecke(conn) -> int:
    """Count total rows in mf_hecke_nf."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM mf_hecke_nf")
            count = cur.fetchone()[0]
        print(f"  Total Hecke eigenvalue rows: {count:,}")
        return count
    except psycopg2.Error as e:
        print(f"  ERROR counting hecke: {e}")
        return 0


def fetch_newforms(
    conn,
    min_level: int,
    max_level: int,
    char_order: int,
    limit: int = 0,
) -> list[dict]:
    """Fetch weight-2 newforms using a server-side WITH HOLD cursor.

    Returns list of dicts with all requested fields.
    """
    # Build WHERE clause
    if char_order == 0:
        conditions = ["weight = 2"]
    else:
        conditions = ["weight = 2", f"char_order = {char_order}"]

    if min_level > 1:
        conditions.append(f"level >= {min_level}")
    if max_level < float("inf"):
        conditions.append(f"level <= {max_level}")

    where_clause = " AND ".join(conditions)

    # Columns we need -- use try/except approach for missing columns
    base_cols = [
        "label",
        "level",
        "dim",
        "analytic_rank",
        "analytic_conductor",
        "char_degree",
        "char_order",
        "is_cm",
        "is_self_dual",
        "hecke_orbit_code",
        "traces",
    ]

    # First, probe which columns actually exist
    available_cols = []
    with conn.cursor() as cur:
        for col in base_cols:
            try:
                cur.execute(f"SELECT {col} FROM mf_newforms WHERE weight = 2 LIMIT 0")
                available_cols.append(col)
            except psycopg2.UndefinedColumn:
                print(f"  WARNING: column '{col}' not found in mf_newforms, skipping")
            except psycopg2.Error:
                # Some other error -- include it anyway and handle downstream
                available_cols.append(col)

    cols_str = ", ".join(available_cols)

    query = f"""
        SELECT {cols_str}
        FROM mf_newforms
        WHERE {where_clause}
        ORDER BY level, label
    """

    if limit > 0:
        query += f" LIMIT {limit}"

    print(f"\nFetching newforms (server-side cursor)...")
    print(f"  Query: {where_clause}")
    print(f"  Columns: {available_cols}")

    records = []
    t0 = time.time()

    try:
        # Named cursor creates a server-side cursor (requires transaction, not autocommit)
        cursor_name = "newforms_cursor"
        cur = conn.cursor(cursor_name)
        cur.execute(query)

        batch_num = 0
        while True:
            batch_num += 1
            rows = cur.fetchmany(NEWFORM_BATCH)

            if not rows:
                break

            # Convert to dicts
            col_names = [desc[0] for desc in cur.description]
            for row in rows:
                rec = dict(zip(col_names, row))
                records.append(rec)

            elapsed = time.time() - t0
            print(
                f"  Batch {batch_num}: +{len(rows)} records "
                f"(total: {len(records):,}, {elapsed:.1f}s)"
            )

            # Periodic progress
            if batch_num % 10 == 0:
                elapsed = time.time() - t0
                rate = len(records) / elapsed if elapsed > 0 else 0
                print(f"    Progress: {len(records):,} records ({rate:.0f} rec/s)")

        cur.close()
        conn.commit()

    except psycopg2.Error as e:
        print(f"  ERROR fetching newforms: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        sys.exit(1)

    elapsed = time.time() - t0
    print(f"  Fetched {len(records):,} newforms in {elapsed:.1f}s")
    return records


def fetch_hecke_traces(
    conn,
    orbit_codes: list[int],
) -> dict[int, dict[int, float]]:
    """Fetch Hecke eigenvalues for given orbit codes and compute traces.

    The mf_hecke_nf table stores eigenvalues in the `an` column as a 2D array
    where an[n] = [[a1, b1], [a2, b2], ...] representing number field embeddings.
    The trace a_n = sum of first components (the rational parts).

    For many forms, the traces field in mf_newforms already has pre-computed
    trace values. This function serves as an enrichment source.

    Args:
        conn: Database connection.
        orbit_codes: List of hecke_orbit_code values.

    Returns:
        Dict mapping hecke_orbit_code -> {n: trace_value, ...}
        where n is the index (1, 2, 3, ...) and trace_value is the trace.
    """
    if not orbit_codes:
        return {}

    result: dict[int, dict[int, float]] = {}
    total_orbits = 0
    t0 = time.time()

    # Process in batches
    n_batches = (len(orbit_codes) + HECKE_BATCH - 1) // HECKE_BATCH

    for batch_idx in range(n_batches):
        start = batch_idx * HECKE_BATCH
        end = min(start + HECKE_BATCH, len(orbit_codes))
        batch_codes = orbit_codes[start:end]

        # Query: get an column (array of eigenvalue vectors)
        # an is an array where index n gives the eigenvalues for coefficient a_n
        query = """
            SELECT hecke_orbit_code, an
            FROM mf_hecke_nf
            WHERE hecke_orbit_code = ANY(%s)
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query, (batch_codes,))
                rows = cur.fetchall()

            for row in rows:
                code = row[0]
                an_array = row[1]  # This is a list of [a, b] pairs or similar

                if code not in result:
                    result[code] = {}

                if an_array is None or not isinstance(an_array, list):
                    continue

                # an_array[n] gives eigenvalues for coefficient a_n
                # Each eigenvalue may be a number like [a, b] (representing a + b*sqrt(D))
                # or a simple number for QQ forms
                for n_idx, eigenvalues in enumerate(an_array):
                    if eigenvalues is None:
                        result[code][n_idx] = 0.0
                        continue

                    trace_val = 0.0
                    if isinstance(eigenvalues, (int, float)):
                        # Simple scalar eigenvalue (dim=1 forms)
                        trace_val = float(eigenvalues)
                    elif isinstance(eigenvalues, list) and eigenvalues:
                        # Number field representation: sum first components
                        # Each element might be [a, b] or just a number
                        for emb in eigenvalues:
                            if isinstance(emb, (int, float)):
                                trace_val += float(emb)
                            elif isinstance(emb, list) and len(emb) >= 1:
                                trace_val += float(emb[0])
                            elif isinstance(emb, Decimal):
                                trace_val += float(emb)
                    result[code][n_idx] = trace_val

                total_orbits += 1

        except psycopg2.Error as e:
            print(f"  ERROR fetching hecke batch {batch_idx + 1}/{n_batches}: {e}")
            conn.rollback()
            continue

        if (batch_idx + 1) % 5 == 0 or batch_idx == n_batches - 1:
            elapsed = time.time() - t0
            print(
                f"  Hecke batch {batch_idx + 1}/{n_batches}: "
                f"{total_orbits:,} orbits processed ({elapsed:.1f}s)"
            )

    elapsed = time.time() - t0
    print(f"  Hecke traces: {len(result):,} orbits computed in {elapsed:.1f}s")
    return result


def build_trace_vectors(
    records: list[dict],
    hecke_traces: dict[int, dict[int, float]],
) -> list[dict]:
    """Build complete trace vectors for each record.

    Strategy:
    1. Use hecke_traces from mf_hecke_nf if available (computed from an array)
    2. Fall back to the 'traces' field in mf_newforms if available
    3. If neither, leave empty trace list

    The traces field in mf_newforms is an array: [a_2, a_3, a_5, a_7, a_11, ...]
    indexed by prime (starting at index 0 for p=2).

    The hecke_traces dict has {n: trace} where n is the coefficient index
    (n=1 is a_1=1, n=2 is a_2, etc.). We extract n >= 2 for the trace vector.

    We merge both sources, preferring hecke_traces data.
    """
    enriched = []
    records_with_hecke = 0
    records_with_builtin = 0
    records_empty = 0

    for rec in records:
        code = rec.get("hecke_orbit_code")
        traces_list = []

        # Source 1: Hecke eigenvalue traces (from mf_hecke_nf an array)
        if code is not None and code in hecke_traces:
            orbit_data = hecke_traces[code]
            # an array is 0-indexed but represents a_1, a_2, a_3, ...
            # We want a_2, a_3, a_5, ... (coefficient indices >= 2)
            # Build a dense vector from n=2 to n=N_TRACE_MATRIX_COLS+some_buffer
            for n in range(2, N_TRACE_MATRIX_COLS + 1000):
                if n in orbit_data:
                    traces_list.append(orbit_data[n])
                else:
                    break  # Stop at first missing index
            records_with_hecke += 1
        else:
            # Source 2: Built-in traces field from mf_newforms
            builtin = rec.get("traces", [])
            if isinstance(builtin, list) and len(builtin) > 0:
                traces_list = [
                    float(t) if not isinstance(t, float) else t for t in builtin
                ]
                records_with_builtin += 1
            else:
                records_empty += 1

        rec["trace_vector"] = traces_list
        enriched.append(rec)

    total = len(records)
    print(f"\nTrace vector sources:")
    print(
        f"  From mf_hecke_nf (an array):    {records_with_hecke:,} ({100 * records_with_hecke / total:.1f}%)"
    )
    print(
        f"  From mf_newforms.traces:        {records_with_builtin:,} ({100 * records_with_builtin / total:.1f}%)"
    )
    print(
        f"  No traces:                       {records_empty:,} ({100 * records_empty / total:.1f}%)"
    )

    return enriched


# ---------------------------------------------------------------------------
# Output builders (matching collect_lmfdb_data.py format exactly)
# ---------------------------------------------------------------------------


def build_json(records: list[dict]) -> Path:
    """Save raw records to JSON (excluding internal trace_vector)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "lmfdb_sql_weight2.json"

    # Strip internal fields before saving
    clean_records = []
    for rec in records:
        clean = {k: v for k, v in rec.items() if k != "trace_vector"}
        clean_records.append(clean)

    print(f"\nSaving JSON ({len(clean_records):,} records)...")
    t0 = time.time()
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(clean_records, f, cls=_DecimalEncoder)
    elapsed = time.time() - t0
    size_mb = json_path.stat().st_size / (1024 * 1024)
    print(f"  JSON saved: {json_path} ({size_mb:.1f} MB, {elapsed:.1f}s)")
    return json_path


def build_ml_csv(records: list[dict]) -> Path:
    """Build ML-ready CSV matching the exact format of collect_lmfdb_data.py.

    CSV columns: label, level, dim, analytic_rank, analytic_conductor,
    char_degree, is_cm, is_self_dual, Nk2,
    trace_1..trace_100, trace_mean, trace_std, trace_max_abs
    """
    csv_path = OUTPUT_DIR / "lmfdb_sql_weight2_ml.csv"
    trace_cols = [f"trace_{i}" for i in range(1, N_TRACE_CSV_COLS + 1)]
    header = ML_COLUMNS + trace_cols + ["trace_mean", "trace_std", "trace_max_abs"]

    print(f"\nBuilding ML CSV ({len(records):,} records, {len(header)} columns)...")
    t0 = time.time()

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for rec in records:
            label = str(rec.get("label", ""))
            level = _safe_int(rec.get("level"))
            dim = _safe_int(rec.get("dim"))
            analytic_rank = _safe_int(rec.get("analytic_rank"))
            analytic_conductor = _safe_float(rec.get("analytic_conductor"))
            char_degree = _safe_int(rec.get("char_degree"))
            is_cm = _safe_bool(rec.get("is_cm"))
            is_self_dual = _safe_bool(rec.get("is_self_dual"))
            nk2 = level * 4  # N * k^2 where k=2

            # Extract trace vector
            traces = rec.get("trace_vector", [])
            if not isinstance(traces, list):
                traces = []

            # First 100 traces as columns
            trace_100 = traces[:N_TRACE_CSV_COLS]

            # Summary statistics over all traces
            if traces:
                trace_mean = sum(traces) / len(traces)
                trace_var = sum((t - trace_mean) ** 2 for t in traces) / len(traces)
                trace_std = math.sqrt(trace_var)
                trace_max_abs = max(abs(t) for t in traces)
            else:
                trace_mean = 0.0
                trace_std = 0.0
                trace_max_abs = 0.0

            row = (
                [
                    label,
                    level,
                    dim,
                    analytic_rank,
                    analytic_conductor,
                    char_degree,
                    is_cm,
                    is_self_dual,
                    nk2,
                ]
                + trace_100
                + [round(trace_mean, 6), round(trace_std, 6), round(trace_max_abs, 6)]
            )
            writer.writerow(row)

    elapsed = time.time() - t0
    size_mb = csv_path.stat().st_size / (1024 * 1024)
    print(
        f"  CSV saved: {csv_path} ({len(records):,} rows, {size_mb:.1f} MB, {elapsed:.1f}s)"
    )
    return csv_path


def build_traces_matrix(records: list[dict]) -> tuple[Path, Path]:
    """Build numpy-compatible traces matrix and labels file.

    Saves:
        data/lmfdb/lmfdb_sql_traces_matrix.npy -- float32 array of shape (N, 1000)
        data/lmfdb/lmfdb_sql_labels.json       -- list of labels for row indexing

    Uses manual .npy writing (no numpy dependency) matching collect_lmfdb_data.py.
    """
    if not records:
        print("  No records, skipping traces matrix.")
        return (
            OUTPUT_DIR / "lmfdb_sql_traces_matrix.npy",
            OUTPUT_DIR / "lmfdb_sql_labels.json",
        )

    print(f"\nBuilding traces matrix ({len(records):,} x {N_TRACE_MATRIX_COLS})...")
    t0 = time.time()

    labels = []
    rows: list[list[float]] = []

    for rec in records:
        label = str(rec.get("label", ""))
        traces = rec.get("trace_vector", [])
        if not isinstance(traces, list):
            traces = []

        labels.append(label)

        # Pad or truncate to exactly N_TRACE_MATRIX_COLS
        if len(traces) >= N_TRACE_MATRIX_COLS:
            row = [float(t) for t in traces[:N_TRACE_MATRIX_COLS]]
        else:
            row = [float(t) for t in traces] + [0.0] * (
                N_TRACE_MATRIX_COLS - len(traces)
            )
        rows.append(row)

    # Save labels
    labels_path = OUTPUT_DIR / "lmfdb_sql_labels.json"
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(labels, f)

    # Save .npy manually (numpy format, float32)
    npy_path = OUTPUT_DIR / "lmfdb_sql_traces_matrix.npy"
    n_rows = len(rows)
    n_cols = N_TRACE_MATRIX_COLS
    _write_npy_float32(npy_path, rows, n_rows, n_cols)

    elapsed = time.time() - t0
    size_mb = npy_path.stat().st_size / (1024 * 1024)
    print(
        f"  Traces matrix saved: {npy_path} ({n_rows:,} x {n_cols} float32, {size_mb:.1f} MB, {elapsed:.1f}s)"
    )
    print(f"  Labels saved: {labels_path} ({len(labels):,} labels)")
    return npy_path, labels_path


def _write_npy_float32(
    path: Path, rows: list[list[float]], n_rows: int, n_cols: int
) -> None:
    """Write a 2D float32 array in .npy format without numpy.

    numpy .npy v1 format:
        magic (6 bytes: \\x93NUMPY) + version (2 bytes) + header_len (2 bytes LE)
        + header (padded to multiple of 16) + raw data
    """
    header_dict_str = (
        f"{{'descr': '<f4', 'fortran_order': False, 'shape': ({n_rows}, {n_cols})}}"
    )
    header_str = header_dict_str + "\n"

    prefix_len = 10
    padding_needed = (16 - (prefix_len + len(header_str) % 16) % 16) % 16
    header_str = header_dict_str + " " * padding_needed + "\n"
    header_bytes = header_str.encode("ascii")
    header_len = len(header_bytes)

    with open(path, "wb") as f:
        f.write(b"\x93NUMPY")  # magic
        f.write(bytes([1, 0]))  # version 1.0
        f.write(struct.pack("<H", header_len))  # header length (uint16 LE)
        f.write(header_bytes)
        # Write float32 little-endian data
        for row in rows:
            for val in row:
                f.write(struct.pack("<f", val))


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


def print_summary(records: list[dict]) -> None:
    """Print comprehensive dataset statistics."""
    if not records:
        print("No records to summarize.")
        return

    print("\n" + "=" * 60)
    print("  DATASET SUMMARY")
    print("=" * 60)

    n = len(records)
    levels = [_safe_int(r.get("level")) for r in records]
    dims = [_safe_int(r.get("dim")) for r in records]
    ranks = [_safe_int(r.get("analytic_rank")) for r in records]
    is_cm = [_safe_bool(r.get("is_cm")) for r in records]
    is_self_dual = [_safe_bool(r.get("is_self_dual")) for r in records]
    conductors = [_safe_float(r.get("analytic_conductor")) for r in records]

    print(f"\n  Total newforms: {n:,}")
    print(f"  Level range: {min(levels)} .. {max(levels)}")
    print(f"  Analytic conductor range: {min(conductors):.4f} .. {max(conductors):.4f}")

    # Dimension distribution
    dim_counts: dict[int, int] = {}
    for d in dims:
        dim_counts[d] = dim_counts.get(d, 0) + 1
    print(f"\n  Dimension distribution:")
    for d in sorted(dim_counts.keys())[:10]:
        print(f"    dim={d}: {dim_counts[d]:,}")
    if len(dim_counts) > 10:
        print(f"    ... and {len(dim_counts) - 10} more dimensions")

    # Analytic rank distribution
    rank_counts: dict[int, int] = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    print(f"\n  Analytic rank distribution:")
    for r in sorted(rank_counts.keys())[:10]:
        print(f"    rank={r}: {rank_counts[r]:,}")
    if len(rank_counts) > 10:
        print(f"    ... and {len(rank_counts) - 10} more ranks")

    # CM vs non-CM
    n_cm = sum(is_cm)
    print(f"\n  CM forms: {n_cm:,} ({100 * n_cm / n:.1f}%)")
    print(f"  Non-CM forms: {n - n_cm:,} ({100 * (n - n_cm) / n:.1f}%)")

    # Self-dual
    n_sd = sum(is_self_dual)
    print(f"  Self-dual: {n_sd:,} ({100 * n_sd / n:.1f}%)")

    # Trace statistics
    all_trace_lengths = []
    all_trace_means = []
    for rec in records:
        traces = rec.get("trace_vector", [])
        if isinstance(traces, list) and traces:
            all_trace_lengths.append(len(traces))
            all_trace_means.append(sum(traces) / len(traces))

    if all_trace_lengths:
        print(
            f"\n  Trace vector lengths: min={min(all_trace_lengths)}, "
            f"max={max(all_trace_lengths)}, "
            f"median={sorted(all_trace_lengths)[len(all_trace_lengths) // 2]}"
        )
        print(
            f"  Trace mean (across forms): "
            f"mean={sum(all_trace_means) / len(all_trace_means):.4f}, "
            f"min={min(all_trace_means):.4f}, "
            f"max={max(all_trace_means):.4f}"
        )
    else:
        print("\n  No trace vectors available.")

    # Character order distribution
    char_orders = [_safe_int(r.get("char_order")) for r in records]
    co_counts: dict[int, int] = {}
    for co in char_orders:
        co_counts[co] = co_counts.get(co, 0) + 1
    if len(co_counts) > 1:
        print(f"\n  Character order distribution:")
        for co in sorted(co_counts.keys())[:10]:
            print(f"    order={co}: {co_counts[co]:,}")
        if len(co_counts) > 10:
            print(f"    ... and {len(co_counts) - 10} more orders")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect LMFDB weight-2 newform data via direct PostgreSQL access",
    )
    parser.add_argument(
        "--max-level",
        type=int,
        default=5000,
        help="Maximum level to include (default: 5000)",
    )
    parser.add_argument(
        "--min-level",
        type=int,
        default=11,
        help="Minimum level (default: 11)",
    )
    parser.add_argument(
        "--char-order",
        type=int,
        default=1,
        help="Character order filter (default: 1 for trivial; 0 for ALL)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of newforms to collect (default: 0 = no limit)",
    )
    parser.add_argument(
        "--no-traces-matrix",
        action="store_true",
        help="Skip building the large traces_matrix.npy file",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Just test connection and print counts, don't download data",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  LMFDB SQL Data Collection")
    print("  (Direct PostgreSQL mirror access)")
    print("=" * 60)

    # Step 1: Connect
    conn = connect_db(test=args.test)

    # Step 2: Count (always, even in --test mode)
    count = count_newforms(conn, args.min_level, args.max_level, args.char_order)
    hecke_count = count_hecke(conn)

    if args.test:
        print("\n--test mode: connection OK, exiting.")
        conn.close()
        return

    if count == 0:
        print("\nNo matching newforms found. Nothing to collect.")
        conn.close()
        return

    # Step 3: Fetch newforms
    records = fetch_newforms(
        conn,
        min_level=args.min_level,
        max_level=args.max_level,
        char_order=args.char_order,
        limit=args.limit,
    )

    if not records:
        print("\nNo records fetched. Exiting.")
        conn.close()
        return

    # Step 4: Fetch Hecke eigenvalues for all orbit codes
    orbit_codes = list(
        set(
            _safe_int(r.get("hecke_orbit_code"))
            for r in records
            if r.get("hecke_orbit_code") is not None
        )
    )
    # Filter out zeros (invalid orbit codes)
    orbit_codes = [c for c in orbit_codes if c != 0]

    print(
        f"\nFetching Hecke eigenvalues for {len(orbit_codes):,} unique orbit codes..."
    )

    hecke_traces = fetch_hecke_traces(conn, orbit_codes)

    # Step 5: Build trace vectors
    records = build_trace_vectors(records, hecke_traces)

    # Close DB connection
    conn.close()
    print("\nDatabase connection closed.")

    # Step 6: Save outputs
    t_save = time.time()

    build_json(records)
    build_ml_csv(records)

    if not args.no_traces_matrix:
        build_traces_matrix(records)

    elapsed_save = time.time() - t_save
    print(f"\nAll outputs saved in {elapsed_save:.1f}s")

    # Step 7: Summary
    print_summary(records)

    # Print output file listing
    print("\nOutput files:")
    for f in sorted(OUTPUT_DIR.glob("lmfdb_sql_*")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
