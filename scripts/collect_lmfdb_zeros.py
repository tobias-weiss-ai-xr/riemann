#!/usr/bin/env python3
"""
Experiment 11: Collect L-function zeros from LMFDB SQL mirror.

Joins mf_newforms -> lfunc_lfunctions via trace_hash to collect
L-function zeros alongside Hecke traces for ML prediction.

Outputs:
    data/lmfdb/lmfdb_zeros_raw.json     -- raw SQL records
    data/lmfdb/lmfdb_zeros_ml.csv       -- ML-ready CSV with traces + zero features

Usage:
    python collect_lmfdb_zeros.py --test                     # Quick test (LIMIT 100)
    python collect_lmfdb_zeros.py                           # Full collection
    python collect_lmfdb_zeros.py --max-level 1000          # Levels up to 1000
    python collect_lmfdb_zeros.py --limit 5000               # At most 5000 forms
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# psycopg2 import with helpful error message
# ---------------------------------------------------------------------------

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 is required but not installed.")
    print("  Install with:  pip install psycopg2-binary")
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

N_TRACE_CSV_COLS = 100

CONNECT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5

NEWFORM_BATCH = 1000
HECKE_BATCH = 10000


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------


def connect_db(test: bool = False) -> "psycopg2.connection":
    """Connect to LMFDB PostgreSQL mirror with retry logic."""
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


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


def count_zeros_records(conn, max_level: int) -> int:
    """Count newforms with L-function zeros data."""
    query = """
        SELECT count(*)
        FROM mf_newforms mf
        JOIN lfunc_lfunctions ll ON mf.trace_hash = ll.trace_hash
        WHERE mf.weight = 2
          AND ll.positive_zeros IS NOT NULL
          AND mf.char_order = 1
          AND mf.level <= %s
    """
    try:
        with conn.cursor() as cur:
            cur.execute(query, (max_level,))
            count = cur.fetchone()[0]
        print(
            f"  Found {count:,} weight-2 newforms with L-function zeros (level <= {max_level})"
        )
        return count
    except psycopg2.Error as e:
        print(f"  ERROR counting zeros records: {e}")
        sys.exit(1)


def fetch_newforms_with_zeros(
    conn,
    max_level: int,
    limit: int = 0,
) -> list[dict]:
    """Fetch weight-2 newforms joined with L-function zeros via trace_hash."""
    query = """
        SELECT
            mf.label,
            mf.level,
            mf.weight,
            mf.dim,
            mf.analytic_rank,
            mf.char_order,
            mf.trace_hash,
            mf.hecke_orbit_code,
            mf.traces,
            ll.positive_zeros,
            ll.z1,
            ll.order_of_vanishing,
            ll.root_number,
            ll.conductor
        FROM mf_newforms mf
        JOIN lfunc_lfunctions ll ON mf.trace_hash = ll.trace_hash
        WHERE mf.weight = 2
          AND ll.positive_zeros IS NOT NULL
          AND mf.char_order = 1
          AND mf.level <= %s
        ORDER BY mf.level, mf.label
    """
    if limit > 0:
        query += f" LIMIT {limit}"

    print(f"\nFetching newforms with L-function zeros (server-side cursor)...")
    print(f"  Max level: {max_level}")

    records = []
    t0 = time.time()

    try:
        cursor_name = "zeros_cursor"
        cur = conn.cursor(cursor_name)
        cur.execute(query, (max_level,))

        batch_num = 0
        while True:
            batch_num += 1
            rows = cur.fetchmany(NEWFORM_BATCH)

            if not rows:
                break

            col_names = [desc[0] for desc in cur.description]
            for row in rows:
                rec = dict(zip(col_names, row))
                records.append(rec)

            elapsed = time.time() - t0
            print(
                f"  Batch {batch_num}: +{len(rows)} records "
                f"(total: {len(records):,}, {elapsed:.1f}s)"
            )

            if batch_num % 10 == 0:
                elapsed = time.time() - t0
                rate = len(records) / elapsed if elapsed > 0 else 0
                print(f"    Progress: {len(records):,} records ({rate:.0f} rec/s)")

        cur.close()
        conn.commit()

    except psycopg2.Error as e:
        print(f"  ERROR fetching newforms with zeros: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        sys.exit(1)

    elapsed = time.time() - t0
    print(f"  Fetched {len(records):,} newforms with zeros in {elapsed:.1f}s")
    return records


def fetch_hecke_traces(
    conn,
    orbit_codes: list[int],
) -> dict[int, dict[int, float]]:
    """Fetch Hecke eigenvalues for given orbit codes and compute traces."""
    if not orbit_codes:
        return {}

    result: dict[int, dict[int, float]] = {}
    total_orbits = 0
    t0 = time.time()

    n_batches = (len(orbit_codes) + HECKE_BATCH - 1) // HECKE_BATCH

    for batch_idx in range(n_batches):
        start = batch_idx * HECKE_BATCH
        end = min(start + HECKE_BATCH, len(orbit_codes))
        batch_codes = orbit_codes[start:end]

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
                an_array = row[1]

                if code not in result:
                    result[code] = {}

                if an_array is None or not isinstance(an_array, list):
                    continue

                for n_idx, eigenvalues in enumerate(an_array):
                    if eigenvalues is None:
                        result[code][n_idx] = 0.0
                        continue

                    trace_val = 0.0
                    if isinstance(eigenvalues, (int, float)):
                        trace_val = float(eigenvalues)
                    elif isinstance(eigenvalues, list) and eigenvalues:
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
    """Build complete trace vectors for each record."""
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
            for n in range(2, N_TRACE_CSV_COLS + 1000):
                if n in orbit_data:
                    traces_list.append(orbit_data[n])
                else:
                    break
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


def parse_zero_features(records: list[dict]) -> list[dict]:
    """Parse positive_zeros JSONB and compute zero statistics.

    IMPORTANT: z1-z10 are ALWAYS extracted from the positive_zeros JSONB array.
    The SQL columns ll.z2 and ll.z3 do NOT contain zero positions — they store
    other data (num_zeros and mean_spacing respectively).  Only ll.z1 is a
    genuine zero position and is kept as a validation fallback only.
    """
    NUM_ZERO_COLS = 10
    parsed = 0
    missing_z1 = 0
    z1_mismatch = 0

    for rec in records:
        # Parse positive_zeros from JSONB (list of string t-values)
        pos_zeros_raw = rec.get("positive_zeros")
        pos_zeros = []

        if pos_zeros_raw is not None:
            if isinstance(pos_zeros_raw, str):
                try:
                    pos_zeros = json.loads(pos_zeros_raw)
                except (json.JSONDecodeError, TypeError):
                    pos_zeros = []
            elif isinstance(pos_zeros_raw, list):
                pos_zeros = pos_zeros_raw

        # Convert to floats
        zero_floats = []
        for z in pos_zeros:
            try:
                zero_floats.append(float(z))
            except (ValueError, TypeError):
                pass

        # ALWAYS use positive_zeros for z1-z10 (SQL z2/z3 are NOT zero positions)
        for i in range(NUM_ZERO_COLS):
            col_name = f"z{i + 1}"
            if i < len(zero_floats):
                rec[col_name] = zero_floats[i]
            else:
                rec[col_name] = 0.0

        # Validate z1 against SQL z1 (should match closely)
        sql_z1 = _safe_float(rec.get("z1"))
        if sql_z1 > 0 and rec["z1"] > 0 and abs(sql_z1 - rec["z1"]) > 0.01:
            z1_mismatch += 1

        # Zero statistics
        rec["num_zeros"] = len(zero_floats)

        if len(zero_floats) >= 2:
            spacings = [
                zero_floats[i + 1] - zero_floats[i] for i in range(len(zero_floats) - 1)
            ]
            rec["mean_zero_spacing"] = (
                sum(spacings) / len(spacings) if spacings else 0.0
            )
            if len(spacings) >= 2:
                mean_s = rec["mean_zero_spacing"]
                var_s = sum((s - mean_s) ** 2 for s in spacings) / len(spacings)
                rec["std_zero_spacing"] = math.sqrt(var_s)
            else:
                rec["std_zero_spacing"] = 0.0
        else:
            rec["mean_zero_spacing"] = 0.0
            rec["std_zero_spacing"] = 0.0

        rec["root_number"] = _safe_float(rec.get("root_number"))
        rec["order_of_vanishing"] = _safe_int(rec.get("order_of_vanishing"))

        if len(zero_floats) > 0:
            parsed += 1
        if rec["z1"] == 0.0:
            missing_z1 += 1

    total = len(records)
    print(f"\nZero feature parsing (z1-z{NUM_ZERO_COLS} from positive_zeros JSONB):")
    print(f"  Records with parsed zeros: {parsed:,} ({100 * parsed / total:.1f}%)")
    print(
        f"  Records missing z1:        {missing_z1:,} ({100 * missing_z1 / total:.1f}%)"
    )
    if z1_mismatch > 0:
        print(f"  z1 SQL vs JSONB mismatch:  {z1_mismatch:,} (using JSONB value)")

    return records


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------


def build_json(records: list[dict]) -> Path:
    """Save raw records to JSON (excluding internal trace_vector)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "lmfdb_zeros_raw.json"

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
    """Build ML-ready CSV with traces + zero features."""
    csv_path = OUTPUT_DIR / "lmfdb_zeros_ml.csv"

    meta_cols = ["label", "level", "dim", "analytic_rank", "char_order", "trace_hash"]
    trace_cols = [f"trace_{i}" for i in range(1, N_TRACE_CSV_COLS + 1)]
    zero_cols = [f"z{i}" for i in range(1, 11)] + [
        "num_zeros",
        "mean_zero_spacing",
        "std_zero_spacing",
        "root_number",
        "order_of_vanishing",
    ]
    header = meta_cols + trace_cols + zero_cols

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
            char_order = _safe_int(rec.get("char_order"))
            trace_hash = _safe_int(rec.get("trace_hash"))

            traces = rec.get("trace_vector", [])
            if not isinstance(traces, list):
                traces = []
            # Pad to exactly N_TRACE_CSV_COLS to avoid column misalignment
            trace_100 = (traces + [0.0] * N_TRACE_CSV_COLS)[:N_TRACE_CSV_COLS]

            z_vals = [round(rec.get(f"z{i}", 0.0), 10) for i in range(1, 11)]
            num_zeros = rec.get("num_zeros", 0)
            mean_spacing = round(rec.get("mean_zero_spacing", 0.0), 10)
            std_spacing = round(rec.get("std_zero_spacing", 0.0), 10)
            root_number = rec.get("root_number")
            order_vanishing = rec.get("order_of_vanishing", 0)

            # Use empty string for missing root_number (None/NaN) instead of 0
            if root_number is None or (
                isinstance(root_number, float) and math.isnan(root_number)
            ):
                root_number = ""

            row = (
                [label, level, dim, analytic_rank, char_order, trace_hash]
                + trace_100
                + z_vals
                + [
                    num_zeros,
                    mean_spacing,
                    std_spacing,
                    root_number,
                    order_vanishing,
                ]
            )
            writer.writerow(row)

    elapsed = time.time() - t0
    size_mb = csv_path.stat().st_size / (1024 * 1024)
    print(
        f"  CSV saved: {csv_path} ({len(records):,} rows, {size_mb:.1f} MB, {elapsed:.1f}s)"
    )
    return csv_path


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


def print_summary(records: list[dict]) -> None:
    """Print comprehensive dataset statistics."""
    if not records:
        print("No records to summarize.")
        return

    print("\n" + "=" * 60)
    print("  DATASET SUMMARY — L-function Zeros")
    print("=" * 60)

    n = len(records)
    levels = [_safe_int(r.get("level")) for r in records]
    ranks = [_safe_int(r.get("analytic_rank")) for r in records]
    z1_vals = [r.get("z1", 0.0) for r in records if r.get("z1", 0.0) > 0]
    z2_vals = [r.get("z2", 0.0) for r in records if r.get("z2", 0.0) > 0]
    z3_vals = [r.get("z3", 0.0) for r in records if r.get("z3", 0.0) > 0]
    z4_vals = [r.get("z4", 0.0) for r in records if r.get("z4", 0.0) > 0]
    z5_vals = [r.get("z5", 0.0) for r in records if r.get("z5", 0.0) > 0]
    z10_vals = [r.get("z10", 0.0) for r in records if r.get("z10", 0.0) > 0]
    num_zeros = [r.get("num_zeros", 0) for r in records]
    spacings = [
        r.get("mean_zero_spacing", 0.0)
        for r in records
        if r.get("mean_zero_spacing", 0.0) > 0
    ]
    root_nums = [r.get("root_number", 0.0) for r in records]
    orders = [_safe_int(r.get("order_of_vanishing")) for r in records]

    print(f"\n  Total newforms: {n:,}")
    print(f"  Level range: {min(levels)} .. {max(levels)}")

    # Zeros
    print(
        f"\n  First zero (z1): count={len(z1_vals)}, range=[{min(z1_vals):.4f}, {max(z1_vals):.4f}], mean={sum(z1_vals) / len(z1_vals):.4f}"
    )
    if z2_vals:
        print(
            f"  Second zero (z2): count={len(z2_vals)}, range=[{min(z2_vals):.4f}, {max(z2_vals):.4f}], mean={sum(z2_vals) / len(z2_vals):.4f}"
        )
    if z3_vals:
        print(
            f"  Third zero (z3): count={len(z3_vals)}, range=[{min(z3_vals):.4f}, {max(z3_vals):.4f}], mean={sum(z3_vals) / len(z3_vals):.4f}"
        )
    if z4_vals:
        print(
            f"  Fourth zero (z4): count={len(z4_vals)}, range=[{min(z4_vals):.4f}, {max(z4_vals):.4f}], mean={sum(z4_vals) / len(z4_vals):.4f}"
        )
    if z5_vals:
        print(
            f"  Fifth zero (z5): count={len(z5_vals)}, range=[{min(z5_vals):.4f}, {max(z5_vals):.4f}], mean={sum(z5_vals) / len(z5_vals):.4f}"
        )
    if z10_vals:
        print(
            f"  Tenth zero (z10): count={len(z10_vals)}, range=[{min(z10_vals):.4f}, {max(z10_vals):.4f}], mean={sum(z10_vals) / len(z10_vals):.4f}"
        )

    # Zero counts
    print(
        f"\n  Zeros per form: min={min(num_zeros)}, max={max(num_zeros)}, mean={sum(num_zeros) / len(num_zeros):.1f}"
    )

    # Spacings
    if spacings:
        print(
            f"  Mean zero spacing: min={min(spacings):.4f}, max={max(spacings):.4f}, mean={sum(spacings) / len(spacings):.4f}"
        )

    # Root number distribution
    rn_pos = sum(1 for r in root_nums if r > 0)
    rn_neg = sum(1 for r in root_nums if r < 0)
    rn_zero = sum(1 for r in root_nums if r == 0)
    print(f"\n  Root number: +1={rn_pos:,}, -1={rn_neg:,}, 0={rn_zero:,}")

    # Order of vanishing
    ov_counts = {}
    for o in orders:
        ov_counts[o] = ov_counts.get(o, 0) + 1
    print(f"  Order of vanishing:")
    for o in sorted(ov_counts.keys())[:10]:
        print(f"    order={o}: {ov_counts[o]:,}")
    if len(ov_counts) > 10:
        print(f"    ... and {len(ov_counts) - 10} more")

    # Analytic rank
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    print(f"\n  Analytic rank distribution:")
    for r in sorted(rank_counts.keys())[:10]:
        print(f"    rank={r}: {rank_counts[r]:,}")

    # Trace statistics
    all_trace_lengths = []
    for rec in records:
        traces = rec.get("trace_vector", [])
        if isinstance(traces, list) and traces:
            all_trace_lengths.append(len(traces))

    if all_trace_lengths:
        print(
            f"\n  Trace vector lengths: min={min(all_trace_lengths)}, "
            f"max={max(all_trace_lengths)}, "
            f"median={sorted(all_trace_lengths)[len(all_trace_lengths) // 2]}"
        )

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect L-function zeros from LMFDB SQL mirror",
    )
    parser.add_argument(
        "--max-level",
        type=int,
        default=5000,
        help="Maximum level to include (default: 5000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of newforms to collect (default: 0 = no limit)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Quick test with LIMIT 100",
    )
    args = parser.parse_args()

    if args.test:
        args.limit = 100

    print("=" * 60)
    print("  LMFDB L-function Zeros Collection")
    print("  (Direct PostgreSQL mirror access)")
    print("=" * 60)

    # Step 1: Connect
    conn = connect_db(test=args.test)

    # Step 2: Count
    count = count_zeros_records(conn, args.max_level)

    if args.test:
        print("\n--test mode: connection OK, exiting.")
        conn.close()
        return

    if count == 0:
        print("\nNo matching newforms with zeros found. Nothing to collect.")
        conn.close()
        return

    # Step 3: Fetch newforms with L-function zeros
    records = fetch_newforms_with_zeros(
        conn,
        max_level=args.max_level,
        limit=args.limit,
    )

    if not records:
        print("\nNo records fetched. Exiting.")
        conn.close()
        return

    # Step 4: Parse zero features
    records = parse_zero_features(records)

    # Step 5: Fetch Hecke eigenvalues
    orbit_codes = list(
        set(
            _safe_int(r.get("hecke_orbit_code"))
            for r in records
            if r.get("hecke_orbit_code") is not None
        )
    )
    orbit_codes = [c for c in orbit_codes if c != 0]

    print(
        f"\nFetching Hecke eigenvalues for {len(orbit_codes):,} unique orbit codes..."
    )

    hecke_traces = fetch_hecke_traces(conn, orbit_codes)

    # Step 6: Build trace vectors
    records = build_trace_vectors(records, hecke_traces)

    # Close DB connection
    conn.close()
    print("\nDatabase connection closed.")

    # Step 7: Save outputs
    t_save = time.time()

    build_json(records)
    build_ml_csv(records)

    elapsed_save = time.time() - t_save
    print(f"\nAll outputs saved in {elapsed_save:.1f}s")

    # Step 8: Summary
    print_summary(records)

    print("\nOutput files:")
    for f in sorted(OUTPUT_DIR.glob("lmfdb_zeros*")):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
