#!/usr/bin/env python3
"""
Thread A: Incremental LMFDB collector — memory efficient, checkpointed.

Queries mf_newforms.traces[] ARRAY (100 pre-computed traces, available for ALL
987K weight-2 trivial-char newforms). Writes each batch to CSV append mode.
No lfunc_lfunctions join (too slow/unreliable on mirror).
No mf_hecke_nf join (only 11% coverage).

Memory: ~500MB regardless of total rows.

Usage:
    python scripts/collect_lmfdb_incremental.py                      # Collect as many as possible
    python scripts/collect_lmfdb_incremental.py --target 200000      # Target N forms
    python scripts/collect_lmfdb_incremental.py --target 500000      # Target N forms
    python scripts/collect_lmfdb_incremental.py --test               # Quick test (50 forms)
    python scripts/collect_lmfdb_incremental.py --checkpoint path    # Resume from checkpoint
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 is required.")
    print("  pip install psycopg2-binary")
    sys.exit(1)

DB_HOST = "devmirror.lmfdb.xyz"
DB_PORT = 5432
DB_NAME = "lmfdb"
DB_USER = "lmfdb"
DB_PASS = "lmfdb"
OUTPUT_DIR = Path("data/lmfdb")
BATCH_SIZE = 500
N_TRACES = 100
CONNECT_TIMEOUT = 15

ML_COLUMNS = [
    "label", "level", "dim", "analytic_rank", "analytic_conductor",
    "char_degree", "char_order", "is_cm", "is_self_dual", "Nk2",
]
TRACE_COLS = [f"trace_{i}" for i in range(1, N_TRACES + 1)]
CSV_HEADER = ML_COLUMNS + TRACE_COLS + ["trace_mean", "trace_std", "trace_max_abs"]


def _safe_int(v):
    if v is None:
        return 0
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def _safe_float(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _safe_bool(v):
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("true", "t", "1")


def connect():
    print(f"Connecting to {DB_HOST}:{DB_PORT}/{DB_NAME} ...")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS, connect_timeout=CONNECT_TIMEOUT,
    )
    print("  Connected.")
    return conn


def get_total_count(conn):
    """Count total weight-2 trivial-char newforms."""
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM mf_newforms WHERE weight = 2 AND char_order = 1")
    return cur.fetchone()[0]


def check_available_columns(conn):
    """Check which columns exist in mf_newforms."""
    candidate_cols = ["label", "level", "dim", "analytic_rank", "analytic_conductor",
                      "char_degree", "char_order", "is_cm", "is_self_dual",
                      "traces", "hecke_orbit_code"]
    available = []
    with conn.cursor() as cur:
        for col in candidate_cols:
            try:
                cur.execute(f"SELECT {col} FROM mf_newforms WHERE weight=2 LIMIT 0")
                available.append(col)
            except psycopg2.Error:
                print(f"  WARNING: column '{col}' not found, skipping")
    return available


def build_ml_row(rec):
    """Build a single CSV row from a mf_newforms record."""
    level = _safe_int(rec.get("level"))
    dim = _safe_int(rec.get("dim"))
    analytic_conductor = _safe_float(rec.get("analytic_conductor"))
    char_degree = _safe_int(rec.get("char_degree"))
    is_cm = _safe_bool(rec.get("is_cm"))
    is_self_dual = _safe_bool(rec.get("is_self_dual"))
    nk2 = level * 4

    traces_raw = rec.get("traces", [])
    if not isinstance(traces_raw, (list, tuple)):
        traces_raw = []
    traces = [float(t) for t in traces_raw]  # Decimal -> float
    trace_100 = traces[:N_TRACES]

    if traces:
        trace_mean = float(sum(traces) / len(traces))
        trace_var = sum((t - trace_mean) ** 2 for t in traces) / len(traces)
        trace_std = float(trace_var) ** 0.5
        trace_max_abs = float(max(abs(t) for t in traces))
    else:
        trace_mean = trace_std = trace_max_abs = 0.0

    row = [
        str(rec.get("label", "")),
        level, dim, _safe_int(rec.get("analytic_rank")),
        round(analytic_conductor, 6), char_degree,
        _safe_int(rec.get("char_order")), is_cm, is_self_dual, nk2,
    ] + trace_100 + [
        round(trace_mean, 6), round(trace_std, 6), round(trace_max_abs, 6),
    ]
    return row


def main():
    parser = argparse.ArgumentParser(description="Incremental LMFDB collector")
    parser.add_argument("--target", type=int, default=200000, help="Target number of forms")
    parser.add_argument("--test", action="store_true", help="Quick test (50 forms, no checkpoint)")
    parser.add_argument("--checkpoint", type=str, help="Resume from checkpoint file")
    parser.add_argument("--csv", type=str, default="lmfdb_incremental_ml.csv",
                        help="Output CSV filename")
    parser.add_argument("--json", type=str, default="",
                        help="Optional: output JSON filename (memory-intensive)")
    args = parser.parse_args()

    csv_path = OUTPUT_DIR / args.csv
    json_path = OUTPUT_DIR / args.json if args.json else None
    checkpoint_path = args.checkpoint or (OUTPUT_DIR / "incremental_checkpoint.json")

    target = 50 if args.test else args.target

    print(f"\n{'='*60}")
    print(f"  LMFDB Incremental Collector")
    print(f"  Target: {target:,} forms")
    if args.test:
        print(f"  MODE: TEST (50 forms)")
    print(f"{'='*60}")

    conn = connect()
    total = get_total_count(conn)
    print(f"  Total available: {total:,} weight-2 trivial newforms")

    available_cols = check_available_columns(conn)
    print(f"  Available columns: {available_cols}")
    cols_str = ", ".join(available_cols)

    # Handle checkpoint resume
    start_offset = 0
    skip_header = False
    if os.path.exists(str(checkpoint_path)):
        try:
            with open(str(checkpoint_path)) as f:
                cp = json.load(f)
            if isinstance(cp, dict) and "next_offset" in cp:
                start_offset = cp["next_offset"]
                skip_header = True
                print(f"\n  Resuming from offset {start_offset:,}")
        except (json.JSONDecodeError, KeyError):
            pass

    # Open CSV for writing (append if resuming)
    csv_mode = "a" if skip_header else "w"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_file = open(str(csv_path), csv_mode, newline="", encoding="utf-8")
    writer = csv.writer(csv_file)

    if not skip_header:
        writer.writerow(CSV_HEADER)
        csv_file.flush()

    # Open JSON for write (if requested) — only write at end
    all_records = [] if json_path else None

    # Server-side cursor for memory efficiency
    query = f"""
        SELECT {cols_str}
        FROM mf_newforms
        WHERE weight = 2 AND char_order = 1
        ORDER BY level, label
    """

    # For test mode, append LIMIT
    if args.test:
        query += " LIMIT 50"

    print(f"\nFetching newforms (server-side cursor, batch={BATCH_SIZE})...")
    t0 = time.time()
    total_collected = 0

    try:
        cur = conn.cursor("incr_cursor")
        cur.execute(query)

        batch_num = 0
        while True:
            rows = cur.fetchmany(BATCH_SIZE)
            if not rows:
                break

            batch_num += 1
            col_names = [desc[0] for desc in cur.description]

            for row in rows:
                rec = dict(zip(col_names, row))

                # Skip if before resume offset
                total_collected += 1
                if total_collected < start_offset + 1:
                    continue

                csv_row = build_ml_row(rec)
                writer.writerow(csv_row)

                if all_records is not None:
                    # Store for JSON output (minimal fields)
                    clean = {k: v for k, v in rec.items() if k != "traces"}
                    if "traces" in rec:
                        clean["trace_vector"] = rec["traces"]
                    all_records.append(clean)

            csv_file.flush()
            elapsed = time.time() - t0
            rate = total_collected / elapsed if elapsed > 0 else 0
            print(
                f"  Batch {batch_num}: +{len(rows)} rows "
                f"(total CSV: {total_collected:,}, {rate:.0f} rec/s, "
                f"csv={csv_path.stat().st_size / 1024 / 1024:.1f}MB)",
                flush=True,
            )

            # Checkpoint every batch
            if not args.test:
                with open(str(checkpoint_path), "w") as f:
                    json.dump({"next_offset": total_collected, "count": total_collected}, f)

            # Early stop if we hit target (and not test mode)
            if not args.test and total_collected >= target:
                print(f"  Reached target: {target:,} forms. Stopping.")
                break

        cur.close()
        conn.commit()

    except psycopg2.Error as e:
        print(f"\n  ERROR during fetch: {e}")
        conn.rollback()
        # Save checkpoint so we can resume
        if not args.test:
            with open(str(checkpoint_path), "w") as f:
                json.dump({"next_offset": total_collected, "count": total_collected}, f)
            print(f"  Checkpoint saved at offset {total_collected:,}")
        sys.exit(1)

    elapsed = time.time() - t0
    print(f"\n  Collection complete: {total_collected:,} records in {elapsed:.1f}s")
    print(f"  CSV: {csv_path} ({csv_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Save JSON if requested
    if all_records:
        with open(str(json_path), "w", encoding="utf-8") as f:
            json.dump(all_records, f, cls=_DecimalEncoder)
        print(f"  JSON: {json_path} ({json_path.stat().st_size / 1024 / 1024:.1f} MB)")

    csv_file.close()
    conn.close()
    print("Done.")


class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (bytes, memoryview)):
            return "<binary>"
        return super().default(obj)


if __name__ == "__main__":
    main()
