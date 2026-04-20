#!/usr/bin/env python3
"""
Bulk LMFDB weight-2 newform data collection for GNN x Number Theory research.

Fetches 10,000 weight-2 newforms from the LMFDB API (100 pages x 100 records)
and saves structured datasets for ML training.

Outputs:
    data/lmfdb/lmfdb_weight2.json        — raw API records (one JSON with all)
    data/lmfdb/lmfdb_weight2_ml.csv      — ML-ready CSV with scalar features + first 100 traces
    data/lmfdb/traces_matrix.npy         — numpy array (N, 1000) of Hecke traces
    data/lmfdb/labels.json               — labels corresponding to trace matrix rows

Usage:
    python collect_lmfdb_data.py                          # Full collection (10k forms)
    python collect_lmfdb_data.py --max 5000               # Collect fewer
    python collect_lmfdb_data.py --skip-collect            # Rebuild CSV from existing JSON
    python collect_lmfdb_data.py --no-traces-matrix        # Skip large .npy output
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://www.lmfdb.org/api/mf_newforms/"
OUTPUT_DIR = Path("data/lmfdb")
CHECKPOINT_FILE = OUTPUT_DIR / "checkpoint.json"

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
N_TRACE_CSV_COLS = 100  # First 100 Hecke traces as individual columns
N_TRACE_MATRIX_COLS = 1000  # Full trace matrix for .npy


def _create_session() -> requests.Session:
    """Create a requests Session with User-Agent header set."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)",
        }
    )
    return session


def fetch_page(
    session: requests.Session,
    offset: int,
    retries: int = 5,
    base_delay: float = 2.0,
) -> list[dict]:
    """Fetch one page of 100 newforms from LMFDB API.

    Args:
        session: requests.Session with User-Agent header.
        offset: Pagination offset (0, 100, 200, ...).
        retries: Number of retry attempts on failure.
        base_delay: Base delay in seconds between retries (exponential backoff).

    Returns:
        List of newform record dicts, or empty list if all retries fail.
    """
    params = {"weight": "i2", "_offset": str(offset), "_format": "json"}
    last_error = ""

    for attempt in range(retries):
        try:
            r = session.get(BASE_URL, params=params, timeout=60)

            # Handle HTTP-level errors (4xx, 5xx)
            if r.status_code == 429:
                wait = base_delay * (2**attempt)
                print(
                    f"  Rate limited (429) at offset {offset}, "
                    f"attempt {attempt + 1}/{retries}, waiting {wait:.1f}s..."
                )
                time.sleep(wait)
                continue

            if r.status_code >= 500:
                wait = base_delay * (2**attempt)
                print(
                    f"  Server error ({r.status_code}) at offset {offset}, "
                    f"attempt {attempt + 1}/{retries}, waiting {wait:.1f}s..."
                )
                time.sleep(wait)
                continue

            r.raise_for_status()

            # Check content-type before parsing — Cloudflare may return HTML
            content_type = r.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                body_preview = r.text[:200].replace("\n", "\\n")
                print(
                    f"  Non-JSON response at offset {offset} "
                    f"(status={r.status_code}, type={content_type}): "
                    f"{body_preview}"
                )
                last_error = f"non-JSON content-type: {content_type}"
                wait = base_delay * (2**attempt)
                if attempt < retries - 1:
                    time.sleep(wait)
                continue

            # Parse JSON — may still fail if body is malformed
            try:
                data = r.json()
            except (ValueError, requests.exceptions.JSONDecodeError) as e:
                body_preview = r.text[:200].replace("\n", "\\n")
                print(
                    f"  JSON decode error at offset {offset}, "
                    f"attempt {attempt + 1}/{retries}: {e}"
                )
                print(f"    Status={r.status_code}, Content-Type={content_type}")
                print(f"    Body preview: {body_preview}")
                last_error = f"JSON decode: {e}"
                wait = base_delay * (2**attempt)
                if attempt < retries - 1:
                    time.sleep(wait)
                continue

            # Validate response structure
            if not isinstance(data, dict) or "data" not in data:
                print(
                    f"  Warning: no 'data' key at offset {offset}, "
                    f"response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
                )
                return []

            records = data["data"]
            if not isinstance(records, list):
                print(
                    f"  Warning: 'data' is not a list at offset {offset}: {type(records)}"
                )
                return []

            return records

        except requests.exceptions.ConnectionError as e:
            print(
                f"  Connection error at offset {offset}, "
                f"attempt {attempt + 1}/{retries}: {e}"
            )
            last_error = f"connection: {e}"
            wait = base_delay * (2**attempt)
            if attempt < retries - 1:
                time.sleep(wait)
        except requests.exceptions.Timeout as e:
            print(f"  Timeout at offset {offset}, attempt {attempt + 1}/{retries}: {e}")
            last_error = f"timeout: {e}"
            wait = base_delay * (2**attempt)
            if attempt < retries - 1:
                time.sleep(wait)
        except requests.exceptions.HTTPError as e:
            print(
                f"  HTTP error at offset {offset}, attempt {attempt + 1}/{retries}: {e}"
            )
            last_error = f"HTTP {e}"
            wait = base_delay * (2**attempt)
            if attempt < retries - 1:
                time.sleep(wait)
        except Exception as e:
            print(
                f"  Unexpected error at offset {offset}, "
                f"attempt {attempt + 1}/{retries}: {e}"
            )
            last_error = str(e)
            wait = base_delay * (2**attempt)
            if attempt < retries - 1:
                time.sleep(wait)

    print(f"  All {retries} retries failed at offset {offset} ({last_error}), skipping")
    return []


def collect_all(
    max_offset: int = 10000,
    batch_size: int = 100,
    delay: float = 2.0,
) -> list[dict]:
    """Collect all weight-2 newforms up to max_offset.

    Supports resuming from checkpoint if interrupted. Skips pages that
    fail after all retries instead of stopping the entire collection.

    Args:
        max_offset: Maximum offset to fetch (default 10000 = 10k records).
        batch_size: Records per page (LMFDB returns 100).
        delay: Delay in seconds between requests (default 2.0).

    Returns:
        List of all collected newform records.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start_offset = 0
    all_records: list[dict] = []

    # Resume from checkpoint
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, encoding="utf-8") as f:
                ckpt = json.load(f)
            start_offset = ckpt.get("next_offset", 0)
            prev_file = OUTPUT_DIR / "lmfdb_weight2.json"
            if prev_file.exists():
                with open(prev_file, encoding="utf-8") as f:
                    all_records = json.load(f)
            print(
                f"Resuming from offset {start_offset} with {len(all_records)} records"
            )
        except (json.JSONDecodeError, OSError) as e:
            print(f"  Warning: could not load checkpoint ({e}), starting fresh")
            start_offset = 0

    session = _create_session()
    print(
        f"Collecting weight-2 newforms (offset {start_offset}..{max_offset}), delay={delay}s..."
    )
    t0 = time.time()

    consecutive_failures = 0
    max_consecutive_failures = 10  # Stop only after many pages fail in a row

    for offset in range(start_offset, max_offset, batch_size):
        records = fetch_page(session, offset, base_delay=delay)

        if not records:
            consecutive_failures += 1
            print(
                f"  Offset {offset:>5d}: no records "
                f"(consecutive failures: {consecutive_failures}/{max_consecutive_failures})"
            )
            if consecutive_failures >= max_consecutive_failures:
                print(
                    f"  Too many consecutive failures ({max_consecutive_failures}), stopping."
                )
                break
            time.sleep(delay)
            continue

        consecutive_failures = 0
        all_records.extend(records)
        print(
            f"  Offset {offset:>5d}: +{len(records)} records (total: {len(all_records)})"
        )

        # Save checkpoint every 500 records
        if len(all_records) % 500 < batch_size or len(all_records) % 500 == 0:
            _save_checkpoint(offset + batch_size, len(all_records), all_records)

        time.sleep(delay)

    # Save final JSON
    with open(OUTPUT_DIR / "lmfdb_weight2.json", "w", encoding="utf-8") as f:
        json.dump(all_records, f)

    # Clean up checkpoint
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    elapsed = time.time() - t0
    print(f"Collection complete: {len(all_records)} records in {elapsed:.1f}s")
    return all_records


def _save_checkpoint(next_offset: int, count: int, records: list[dict]) -> None:
    """Save checkpoint with current progress and partial JSON."""
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({"next_offset": next_offset, "count": count}, f)
    with open(OUTPUT_DIR / "lmfdb_weight2.json", "w", encoding="utf-8") as f:
        json.dump(records, f)
    print(f"    Checkpoint saved ({count} records)")


def _safe_int(val, default=0) -> int:
    """Extract integer from API value, handling various types."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0) -> float:
    """Extract float from API value, handling various types."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val, default=False) -> bool:
    """Extract boolean from API value."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return bool(val)


def build_ml_csv(records: list[dict]) -> None:
    """Build ML-ready CSV from raw records.

    CSV columns: label, level, dim, analytic_rank, analytic_conductor,
    char_degree, is_cm, is_self_dual, Nk2,
    trace_1..trace_100, trace_mean, trace_std, trace_max_abs
    """
    csv_path = OUTPUT_DIR / "lmfdb_weight2_ml.csv"
    trace_cols = [f"trace_{i}" for i in range(1, N_TRACE_CSV_COLS + 1)]
    header = ML_COLUMNS + trace_cols + ["trace_mean", "trace_std", "trace_max_abs"]

    print(f"Building ML CSV ({len(records)} records, {len(header)} columns)...")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for rec in records:
            label = rec.get("label", "")
            level = _safe_int(rec.get("level"))
            dim = _safe_int(rec.get("dim"))
            analytic_rank = _safe_int(rec.get("analytic_rank"))
            analytic_conductor = _safe_float(rec.get("analytic_conductor"))
            char_degree = _safe_int(rec.get("char_degree"))
            is_cm = _safe_bool(rec.get("is_cm"))
            is_self_dual = _safe_bool(rec.get("is_self_dual"))
            nk2 = level * 4  # N * k^2 where k=2

            # Extract traces
            traces = rec.get("traces", [])
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

    print(f"  CSV saved: {csv_path} ({len(records)} rows)")


def build_traces_matrix(records: list[dict]) -> None:
    """Build numpy-compatible traces matrix and labels file.

    Saves:
        data/lmfdb/traces_matrix.npy — float32 array of shape (N, 1000)
        data/lmfdb/labels.json       — list of labels for row indexing

    Uses manual .npy writing (no numpy dependency) to keep requirements minimal.
    """
    if not records:
        print("  No records, skipping traces matrix.")
        return

    print(f"Building traces matrix ({len(records)} x {N_TRACE_MATRIX_COLS})...")

    labels = []
    rows: list[list[float]] = []

    for rec in records:
        label = rec.get("label", "")
        traces = rec.get("traces", [])
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
    labels_path = OUTPUT_DIR / "labels.json"
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(labels, f)

    # Save .npy manually (numpy format, float32)
    npy_path = OUTPUT_DIR / "traces_matrix.npy"
    n_rows = len(rows)
    n_cols = N_TRACE_MATRIX_COLS
    _write_npy_float32(npy_path, rows, n_rows, n_cols)

    print(f"  Traces matrix saved: {npy_path} ({n_rows} x {n_cols} float32)")
    print(f"  Labels saved: {labels_path} ({len(labels)} labels)")


def _write_npy_float32(
    path: Path, rows: list[list[float]], n_rows: int, n_cols: int
) -> None:
    """Write a 2D float32 array in .npy format without numpy.

    numpy .npy v1 format:
        magic (6 bytes: \\x93NUMPY) + version (2 bytes) + header_len (2 bytes LE)
        + header (padded to multiple of 16) + raw data
    """
    # Build header dict string (Python literal format, not JSON — numpy uses ast.literal_eval)
    header_dict_str = (
        f"{{'descr': '<f4', 'fortran_order': False, 'shape': ({n_rows}, {n_cols})}}"
    )
    header_str = header_dict_str + "\n"

    # Pad header to make total (header_len + 10) divisible by 16
    # 10 = 6 (magic) + 2 (version) + 2 (header_len field)
    prefix_len = 10
    padding_needed = (16 - (prefix_len + len(header_str) % 16) % 16) % 16
    # Insert padding BEFORE the newline so ast.literal_eval doesn't see leading spaces
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


def print_summary(records: list[dict]) -> None:
    """Print dataset statistics."""
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

    # Level range
    print(f"\n  Total newforms: {n}")
    print(f"  Level range: {min(levels)} .. {max(levels)}")
    print(f"  Analytic conductor range: {min(conductors):.4f} .. {max(conductors):.4f}")

    # Dimension distribution
    dim_counts: dict[int, int] = {}
    for d in dims:
        dim_counts[d] = dim_counts.get(d, 0) + 1
    print(f"\n  Dimension distribution:")
    for d in sorted(dim_counts.keys())[:10]:
        print(f"    dim={d}: {dim_counts[d]}")
    if len(dim_counts) > 10:
        print(f"    ... and {len(dim_counts) - 10} more dimensions")

    # Analytic rank distribution
    rank_counts: dict[int, int] = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    print(f"\n  Analytic rank distribution:")
    for r in sorted(rank_counts.keys())[:10]:
        print(f"    rank={r}: {rank_counts[r]}")
    if len(rank_counts) > 10:
        print(f"    ... and {len(rank_counts) - 10} more ranks")

    # CM vs non-CM
    n_cm = sum(is_cm)
    print(f"\n  CM forms: {n_cm} ({100 * n_cm / n:.1f}%)")
    print(f"  Non-CM forms: {n - n_cm} ({100 * (n - n_cm) / n:.1f}%)")

    # Self-dual
    n_sd = sum(is_self_dual)
    print(f"  Self-dual: {n_sd} ({100 * n_sd / n:.1f}%)")

    # Trace statistics
    all_trace_lengths = []
    all_trace_means = []
    for rec in records:
        traces = rec.get("traces", [])
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

    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect LMFDB weight-2 newform data for ML training"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10000,
        help="Max records to collect (default: 10000)",
    )
    parser.add_argument(
        "--skip-collect",
        action="store_true",
        help="Skip collection, just build CSV/matrix from existing JSON",
    )
    parser.add_argument(
        "--no-traces-matrix",
        action="store_true",
        help="Skip building the large traces_matrix.npy file",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between API requests (default: 2.0)",
    )
    args = parser.parse_args()

    if not args.skip_collect:
        records = collect_all(max_offset=args.max, delay=args.delay)
    else:
        json_path = OUTPUT_DIR / "lmfdb_weight2.json"
        if not json_path.exists():
            print(f"Error: {json_path} not found. Run without --skip-collect first.")
            sys.exit(1)
        with open(json_path, encoding="utf-8") as f:
            records = json.load(f)
        print(f"Loaded {len(records)} records from {json_path}")

    if not records:
        print("No records collected. Nothing to do.")
        sys.exit(1)

    build_ml_csv(records)

    if not args.no_traces_matrix:
        build_traces_matrix(records)

    print_summary(records)


if __name__ == "__main__":
    main()
