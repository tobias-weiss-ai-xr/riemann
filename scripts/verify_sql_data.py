#!/usr/bin/env python3
"""Verify the SQL mirror collected data."""

import json
import csv
import os
import struct


def verify_npy(path):
    """Read .npy header and report shape/dtype without numpy."""
    with open(path, "rb") as f:
        magic = f.read(6)
        assert magic == b"\x93NUMPY", f"Bad magic: {magic}"
        version = f.read(2)
        header_len = struct.unpack("<H", f.read(2))[0]
        header = f.read(header_len).decode("ascii")
        print(f"  NPY header: {header.strip()}")
        import ast

        meta = ast.literal_eval(header)
        shape = meta["shape"]
        dtype = meta["descr"]
        data_size = os.path.getsize(path) - 10 - header_len
        print(f"  Shape: {shape}")
        print(f"  Dtype: {dtype}")
        print(f"  File size: {os.path.getsize(path) / 1e6:.1f} MB")
        print(f"  Expected data size: {shape[0] * shape[1] * 4 / 1e6:.1f} MB (float32)")


def verify_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    print(f"  Rows: {len(rows)}")
    print(f"  Cols: {len(header)}")
    print(f"  Header[:12]: {header[:12]}")
    print(f"  Header[-3:]: {header[-3:]}")
    if rows:
        print(f"  First row[:12]: {rows[0][:12]}")
        print(f"  Last row[:5]: {rows[-1][:5]}")
    # Check for empty trace columns
    empty_traces = 0
    for row in rows:
        trace_vals = row[9:109]  # trace_1..trace_100
        if all(v == "0" or v == "0.0" for v in trace_vals):
            empty_traces += 1
    print(
        f"  Rows with all-zero traces: {empty_traces} ({100 * empty_traces / len(rows):.1f}%)"
    )


def verify_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  Records: {len(data)}")
    print(f"  File size: {os.path.getsize(path) / 1e6:.1f} MB")
    if data:
        sample = data[0]
        print(f"  Sample keys: {list(sample.keys())[:15]}")
        print(f"  Sample level: {sample.get('level')}")
        print(f"  Sample label: {sample.get('label')}")
        traces = sample.get("traces", [])
        if isinstance(traces, list):
            print(f"  Sample traces length: {len(traces)}")
        # Distribution of levels
        levels = [
            r.get("level", 0) for r in data if isinstance(r.get("level"), (int, float))
        ]
        if levels:
            print(f"  Level range: {min(levels)} .. {max(levels)}")
        # Distribution of analytic ranks
        ranks = [
            r.get("analytic_rank", -1)
            for r in data
            if isinstance(r.get("analytic_rank"), (int, float))
        ]
        if ranks:
            from collections import Counter

            rank_dist = Counter(ranks)
            print(f"  Rank distribution: {dict(sorted(rank_dist.items()))}")


if __name__ == "__main__":
    base = "data/lmfdb"
    print("=" * 60)
    print("  VERIFYING SQL MIRROR DATA")
    print("=" * 60)

    npy_path = os.path.join(base, "lmfdb_sql_traces_matrix.npy")
    csv_path = os.path.join(base, "lmfdb_sql_weight2_ml.csv")
    json_path = os.path.join(base, "lmfdb_sql_weight2.json")
    labels_path = os.path.join(base, "lmfdb_sql_labels.json")

    print("\n--- NPY Matrix ---")
    if os.path.exists(npy_path):
        verify_npy(npy_path)
    else:
        print(f"  MISSING: {npy_path}")

    print("\n--- CSV ---")
    if os.path.exists(csv_path):
        verify_csv(csv_path)
    else:
        print(f"  MISSING: {csv_path}")

    print("\n--- JSON ---")
    if os.path.exists(json_path):
        verify_json(json_path)
    else:
        print(f"  MISSING: {json_path}")

    print("\n--- Labels ---")
    if os.path.exists(labels_path):
        with open(labels_path, "r") as f:
            labels = json.load(f)
        print(f"  Labels: {len(labels)}")
        if labels:
            print(f"  First: {labels[0]}")
            print(f"  Last: {labels[-1]}")
    else:
        print(f"  MISSING: {labels_path}")

    print("\n" + "=" * 60)
    print("  VERIFICATION COMPLETE")
    print("=" * 60)
