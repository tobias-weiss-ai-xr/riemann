#!/usr/bin/env python3
"""
Build PyG graph datasets from LMFDB Hecke trace data (Phase 0 of Experiment 12).

Produces two paradigms:
  A (trace_index):    Per-sample graph with 1000 nodes (Hecke trace indices).
  C (multiplicative): Per-sample graph with ~608 nodes (squarefree indices only).

Each output directory contains: train.pt, val.pt, test.pt, metadata.json

Usage:
    python scripts/build_lmfdb_gnn_dataset.py                          # Both paradigms
    python scripts/build_lmfdb_gnn_dataset.py --paradigm trace_index   # Paradigm A only
    python scripts/build_lmfdb_gnn_dataset.py --paradigm multiplicative  # Paradigm C only
    python scripts/build_lmfdb_gnn_dataset.py --num-traces 100         # Subset for debug
    python scripts/build_lmfdb_gnn_dataset.py --debug                  # Verbose + small subset
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from math import gcd
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from loguru import logger
from scipy.spatial import cKDTree
from torch_geometric.data import Data

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data" / "lmfdb"

TRACES_PATH = DATA_DIR / "lmfdb_sql_traces_matrix.npy"
LABELS_PATH = DATA_DIR / "lmfdb_sql_labels.json"
WEIGHT2_ML_PATH = DATA_DIR / "lmfdb_sql_weight2_ml.csv"
ZEROS_ML_PATH = DATA_DIR / "lmfdb_zeros_ml.csv"

OUT_TRACE_INDEX = DATA_DIR / "gnn_trace_index"
OUT_MULTIPLICATIVE = DATA_DIR / "gnn_multiplicative"

# ---------------------------------------------------------------------------
# Configure loguru
# ---------------------------------------------------------------------------

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)

# ---------------------------------------------------------------------------
# Sieve helpers (computed once)
# ---------------------------------------------------------------------------


def sieve_smallest_prime_factor(limit: int) -> np.ndarray:
    """Sieve for smallest prime factor of each n in [1..limit]. spf[1] = 1."""
    spf = np.ones(limit + 1, dtype=np.int64)
    for i in range(2, limit + 1):
        if spf[i] == 1:
            spf[i] = i
            if i * i <= limit:
                for j in range(i * i, limit + 1, i):
                    if spf[j] == 1:
                        spf[j] = i
    return spf


def sieve_is_prime(limit: int) -> np.ndarray:
    """Boolean sieve: is_prime[n] = True iff n is prime (n in [1..limit])."""
    is_prime = np.zeros(limit + 1, dtype=bool)
    is_prime[2] = True
    for i in range(3, limit + 1, 2):
        if all(i % p != 0 for p in range(3, int(i**0.5) + 1, 2)):
            is_prime[i] = True
    return is_prime


def sieve_squarefree(limit: int) -> list[int]:
    """Return sorted list of squarefree numbers in [1..limit]."""
    # Mark numbers that are NOT squarefree
    not_sf = np.zeros(limit + 1, dtype=bool)
    for p in range(2, int(limit**0.5) + 1):
        if all(p % d != 0 for d in range(2, int(p**0.5) + 1)):
            pp = p * p
            for k in range(pp, limit + 1, pp):
                not_sf[k] = True
    return [n for n in range(1, limit + 1) if not not_sf[n]]


def compute_omega(limit: int) -> np.ndarray:
    """Number of distinct prime factors for each n in [1..limit]."""
    omega = np.zeros(limit + 1, dtype=np.int32)
    for p in range(2, limit + 1):
        if omega[p] == 0:  # p is prime
            for k in range(p, limit + 1, p):
                omega[k] += 1
    return omega


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_and_join_data(
    num_traces: int | None = None,
) -> tuple[np.ndarray, list[str], pd.DataFrame]:
    """
    Load traces matrix, labels, and join with weight2_ml + zeros_ml.

    Returns:
        traces: (N, 1000) float32 — only rows present in ALL sources
        labels: list of N label strings
        meta_df: DataFrame with columns [matrix_idx, label, analytic_rank, is_cm, dim, level, z1]
    """
    logger.info("Loading traces matrix (mmap)...")
    traces_full = np.load(TRACES_PATH, mmap_mode="r")
    logger.info(f"  traces_matrix shape: {traces_full.shape}, dtype: {traces_full.dtype}")

    with open(LABELS_PATH) as f:
        labels_full: list[str] = json.load(f)
    logger.info(f"  labels.json: {len(labels_full)} entries")

    logger.info("Loading weight2_ml CSV...")
    df_ml = pd.read_csv(WEIGHT2_ML_PATH, usecols=["label", "analytic_rank", "is_cm", "dim", "level"])
    logger.info(f"  weight2_ml: {len(df_ml)} rows")

    logger.info("Loading zeros_ml CSV (deduplicating)...")
    df_z = pd.read_csv(ZEROS_ML_PATH, usecols=["label", "z1"])
    before_dedup = len(df_z)
    df_z = df_z.drop_duplicates(subset="label", keep="first")
    logger.info(f"  zeros_ml: {before_dedup} rows -> {len(df_z)} unique labels")

    # Build join DataFrame from labels (indices into traces_matrix)
    labels_df = pd.DataFrame({"label": labels_full, "matrix_idx": np.arange(len(labels_full))})

    # Inner join: labels ∩ weight2_ml ∩ zeros_ml
    meta_df = labels_df.merge(df_ml, on="label", how="inner")
    meta_df = meta_df.merge(df_z, on="label", how="inner")
    logger.info(f"  After join: {len(meta_df)} forms in all three sources")

    # Sort by matrix_idx for deterministic ordering
    meta_df = meta_df.sort_values("matrix_idx").reset_index(drop=True)

    # Convert is_cm from bool to int
    meta_df["is_cm"] = meta_df["is_cm"].astype(int)

    # Optionally limit
    if num_traces is not None and num_traces < len(meta_df):
        meta_df = meta_df.iloc[:num_traces].reset_index(drop=True)
        logger.info(f"  Limited to {num_traces} traces (--num-traces)")

    # Extract traces for matching indices
    indices = meta_df["matrix_idx"].values
    traces = np.array(traces_full[indices], dtype=np.float32)
    labels = meta_df["label"].tolist()

    logger.info(f"  Final dataset: {len(meta_df)} samples, traces shape {traces.shape}")
    logger.info(
        f"  Rank dist: {dict(Counter(meta_df['analytic_rank'].values))}"
    )
    logger.info(
        f"  CM dist: {dict(Counter(meta_df['is_cm'].values))}"
    )
    logger.info(
        f"  z1: mean={meta_df['z1'].mean():.4f}, std={meta_df['z1'].std():.4f}"
    )

    return traces, labels, meta_df


# ---------------------------------------------------------------------------
# Stratified split
# ---------------------------------------------------------------------------


def stratified_split(
    ranks: np.ndarray,
    train_frac: float = 0.8,
    val_frac: float = 0.1,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """80/10/10 stratified split by analytic_rank. Returns index arrays."""
    rng = np.random.RandomState(seed)
    n = len(ranks)
    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    for rank_val in sorted(np.unique(ranks)):
        mask = ranks == rank_val
        class_indices = np.where(mask)[0]
        rng.shuffle(class_indices)

        n_train = int(len(class_indices) * train_frac)
        n_val = int(len(class_indices) * val_frac)

        train_idx.extend(class_indices[:n_train].tolist())
        val_idx.extend(class_indices[n_train : n_train + n_val].tolist())
        test_idx.extend(class_indices[n_train + n_val :].tolist())

    return np.array(train_idx), np.array(val_idx), np.array(test_idx)


def cross_level_split(
    levels: np.ndarray,
    ranks: np.ndarray,
    max_train_level: int = 3000,
    max_val_level: int = 4000,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split by conductor level: train on low levels, test on high levels.
    
    Tests whether the GNN generalizes to newforms with larger conductors.
    """
    rng = np.random.RandomState(seed)
    train_mask = levels <= max_train_level
    val_mask = (levels > max_train_level) & (levels <= max_val_level)
    test_mask = levels > max_val_level

    train_pool = np.where(train_mask)[0]
    val_pool = np.where(val_mask)[0]
    test_pool = np.where(test_mask)[0]

    logger.info(f"  Cross-level split: train<=N{max_train_level}={len(train_pool)}, "
                f"val N{max_train_level+1}-{max_val_level}={len(val_pool)}, "
                f"test>N{max_val_level}={len(test_pool)}")

    # Stratify within each pool by rank
    def stratify(pool, ranks):
        idx_list = []
        for rank_val in sorted(np.unique(ranks[pool])):
            class_idx = pool[ranks[pool] == rank_val]
            rng.shuffle(class_idx)
            idx_list.extend(class_idx.tolist())
        return np.array(idx_list)

    return stratify(train_pool, ranks), stratify(val_pool, ranks), stratify(test_pool, ranks)


# ---------------------------------------------------------------------------
# Paradigm A: Trace-Index Graph
# ---------------------------------------------------------------------------


def build_trace_index_graph(
    trace_row: np.ndarray,
    spf: np.ndarray,
    is_prime: np.ndarray,
    n_traces: int = 1000,
    k_nn: int = 3,
) -> Data:
    """
    Build one PyG Data object for a single newform (Paradigm A).

    Node features (1000 × 5):
        [trace_value, log_abs_trace, sign(trace), n/1000, is_prime(n)]
    """
    n = n_traces
    indices = np.arange(1, n + 1)  # 1-indexed Hecke indices

    # Node features
    x = np.zeros((n, 5), dtype=np.float32)
    x[:, 0] = trace_row                        # trace_value
    x[:, 1] = np.log(np.abs(trace_row) + 1.0)  # log_abs_trace
    x[:, 2] = np.sign(trace_row)                # sign(trace): -1, 0, +1
    x[:, 3] = indices / float(n)                # n / 1000
    x[:, 4] = is_prime[indices].astype(np.float32)  # is_prime(n)

    # --- Edge construction ---
    edge_list: list[tuple[int, int]] = []

    # 1. Sequential chain (bidirectional)
    for i in range(n - 1):
        edge_list.append((i, i + 1))
        edge_list.append((i + 1, i))

    # 2. Prime-factor links (bidirectional)
    #    For each n, connect n to its smallest prime factor p
    for i in range(1, n):  # skip n=1 (index 0)
        n_val = i + 1
        p = int(spf[n_val])
        if p != n_val and p <= n:  # connect to spf if it's a proper factor
            p_idx = p - 1
            edge_list.append((i, p_idx))
            edge_list.append((p_idx, i))

    # 3. K-NN in trace-value space (bidirectional)
    trace_values = trace_row.reshape(-1, 1)
    tree = cKDTree(trace_values)
    _, nn_indices = tree.query(trace_values, k=k_nn + 1)  # +1 because self is included
    for i in range(n):
        for j_idx in range(1, k_nn + 1):
            j = nn_indices[i, j_idx]
            edge_list.append((i, j))
            edge_list.append((j, i))

    # Deduplicate edges
    edge_set = set(edge_list)
    edge_list = list(edge_set)

    if len(edge_list) == 0:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
    else:
        edge_array = np.array(edge_list, dtype=np.int64).T
        edge_index = torch.from_numpy(edge_array)

    return Data(
        x=torch.from_numpy(x),
        edge_index=edge_index.contiguous(),
    )


def build_paradigm_a(
    traces: np.ndarray,
    labels: list[str],
    meta_df: pd.DataFrame,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    debug: bool = False,
) -> dict:
    """Build all graphs for Paradigm A and return save dict + metadata."""
    n_traces = traces.shape[1]
    logger.info(f"Paradigm A: building trace-index graphs ({n_traces} nodes each)...")

    # Precompute sieves
    spf = sieve_smallest_prime_factor(n_traces)
    is_prime = sieve_is_prime(n_traces)

    splits = {"train": train_idx, "val": val_idx, "test": test_idx}
    result: dict[str, list[Data]] = {}

    for split_name, idx_array in splits.items():
        n_samples = len(idx_array)
        logger.info(f"  Building {split_name} split ({n_samples} graphs)...")

        graphs: list[Data] = []
        for i, sample_i in enumerate(idx_array):
            row = traces[sample_i]
            data = build_trace_index_graph(row, spf, is_prime, n_traces=n_traces)

            # Attach targets
            meta = meta_df.iloc[sample_i]
            data.y_z1 = torch.tensor(float(meta["z1"]), dtype=torch.float32)
            data.y_rank = torch.tensor(int(meta["analytic_rank"]), dtype=torch.long)
            data.y_cm = torch.tensor(int(meta["is_cm"]), dtype=torch.long)
            data.y_dim = torch.tensor(int(meta["dim"]), dtype=torch.long)
            data.level = torch.tensor(int(meta["level"]), dtype=torch.long)
            data.label_str = meta["label"]

            graphs.append(data)

            if debug and i >= 4:
                graphs = graphs[:5]
                logger.info(f"  [debug] Limited {split_name} to 5 graphs")
                break

            if (i + 1) % 5000 == 0:
                logger.info(f"    {split_name}: {i + 1}/{n_samples}")

        result[split_name] = graphs

    # Compute normalization stats from training set only
    train_graphs = result["train"]
    all_node_feats = np.concatenate([g.x.numpy() for g in train_graphs], axis=0)
    feat_mean = all_node_feats.mean(axis=0).tolist()
    feat_std = all_node_feats.std(axis=0).tolist()

    logger.info(f"  Node feat mean: {[f'{v:.4f}' for v in feat_mean]}")
    logger.info(f"  Node feat std:  {[f'{v:.4f}' for v in feat_std]}")

    # Target stats from training set
    train_indices = train_idx
    train_meta = meta_df.iloc[train_indices]

    # Edge count stats
    edge_counts = [g.edge_index.shape[1] for g in train_graphs]
    logger.info(
        f"  Edge counts: min={min(edge_counts)}, max={max(edge_counts)}, "
        f"mean={np.mean(edge_counts):.0f}"
    )

    metadata = {
        "paradigm": "trace_index",
        "num_nodes_per_graph": n_traces,
        "node_feat_dim": 5,
        "num_edge_types": 3,
        "train_size": len(result["train"]),
        "val_size": len(result["val"]),
        "test_size": len(result["test"]),
        "train_node_feat_mean": feat_mean,
        "train_node_feat_std": feat_std,
        "edge_count_mean": float(np.mean(edge_counts)),
        "edge_count_min": int(min(edge_counts)),
        "edge_count_max": int(max(edge_counts)),
        "target_stats": {
            "z1": {
                "mean": float(train_meta["z1"].mean()),
                "std": float(train_meta["z1"].std()),
                "n_valid": int(train_meta["z1"].notna().sum()),
            },
            "rank": {
                "distribution": {
                    str(k): int(v)
                    for k, v in train_meta["analytic_rank"]
                    .value_counts()
                    .sort_index()
                    .items()
                }
            },
            "cm": {
                "distribution": {
                    str(k): int(v)
                    for k, v in train_meta["is_cm"]
                    .value_counts()
                    .sort_index()
                    .items()
                }
            },
            "dim": {
                "mean": float(train_meta["dim"].mean()),
                "std": float(train_meta["dim"].std()),
                "min": int(train_meta["dim"].min()),
                "max": int(train_meta["dim"].max()),
            },
        },
    }

    return result, metadata


# ---------------------------------------------------------------------------
# Paradigm C: Multiplicative Graph
# ---------------------------------------------------------------------------


def build_multiplicative_graph(
    trace_row: np.ndarray,
    sf_indices: list[int],
    omega_arr: np.ndarray,
    max_omega: int,
    n_traces: int = 1000,
) -> Data:
    """
    Build one PyG Data object for a single newform (Paradigm C).

    Nodes: only squarefree indices n in [1, 1000] (608 nodes).
    Node features (3-dim): [trace(n), omega(n)/max_omega, log(n)/log(1000)]
    """
    n_nodes = len(sf_indices)

    # Node features
    x = np.zeros((n_nodes, 3), dtype=np.float32)
    for i, n in enumerate(sf_indices):
        x[i, 0] = trace_row[n - 1]                        # trace(n)
        x[i, 1] = omega_arr[n] / float(max_omega)          # omega(n) / max_omega
        x[i, 2] = np.log(n) / np.log(n_traces)            # log(n) / log(1000)

    # --- Edge construction ---
    # Precompute divisibility pairs
    edge_list: list[tuple[int, int]] = []
    divisibility_set: set[tuple[int, int]] = set()

    # 1. Divisibility edges: n1 | n2 or n2 | n1 (n1 != n2)
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            n1, n2 = sf_indices[i], sf_indices[j]
            if n1 % n2 == 0 or n2 % n1 == 0:
                edge_list.append((i, j))
                edge_list.append((j, i))
                divisibility_set.add((i, j))
                divisibility_set.add((j, i))

    # 2. Shared prime factor edges: gcd > 1 AND NOT already divisibility-connected
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if (i, j) in divisibility_set:
                continue
            n1, n2 = sf_indices[i], sf_indices[j]
            if gcd(n1, n2) > 1:
                edge_list.append((i, j))
                edge_list.append((j, i))

    if len(edge_list) == 0:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
    else:
        edge_array = np.array(edge_list, dtype=np.int64).T
        edge_index = torch.from_numpy(edge_array)

    return Data(
        x=torch.from_numpy(x),
        edge_index=edge_index.contiguous(),
    )


def build_paradigm_c(
    traces: np.ndarray,
    labels: list[str],
    meta_df: pd.DataFrame,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    output_dir: Path | None = None,
    debug: bool = False,
) -> tuple:
    """Build all graphs for Paradigm C — shared edge_index, per-graph node features only."""
    n_traces = traces.shape[1]
    logger.info("Paradigm C: building multiplicative graphs...")

    sf_indices = sieve_squarefree(n_traces)
    n_nodes = len(sf_indices)
    logger.info(f"  Squarefree numbers in [1, {n_traces}]: {n_nodes}")

    omega_arr = compute_omega(n_traces)
    max_omega = int(omega_arr[sf_indices].max())
    logger.info(f"  Max omega among squarefree n <= {n_traces}: {max_omega}")

    # Build shared edge_index ONCE (divisibility poset is structural, same for all graphs)
    logger.info("  Building shared edge_index (divisibility poset)...")
    t0 = time.time()
    edge_list = []
    divisibility_set = set()
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            n1, n2 = sf_indices[i], sf_indices[j]
            if n1 % n2 == 0 or n2 % n1 == 0:
                edge_list.append((i, j))
                edge_list.append((j, i))
                divisibility_set.add((i, j))
                divisibility_set.add((j, i))
    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if (i, j) in divisibility_set:
                continue
            n1, n2 = sf_indices[i], sf_indices[j]
            if gcd(n1, n2) > 1:
                edge_list.append((i, j))
                edge_list.append((j, i))

    shared_edge_index = np.array(edge_list, dtype=np.int32).T if edge_list else np.zeros((2, 0), dtype=np.int32)
    n_edges = shared_edge_index.shape[1]
    logger.info(f"  Shared edge_index: {n_edges:,} edges ({time.time()-t0:.1f}s)")

    # Precompute omega/log features for squarefree indices (same for all graphs)
    omega_feat = np.array([omega_arr[n] / float(max_omega) for n in sf_indices], dtype=np.float32)
    log_feat = np.array([np.log(n) / np.log(n_traces) for n in sf_indices], dtype=np.float32)
    static_feats = np.stack([omega_feat, log_feat], axis=1)  # (n_nodes, 2)

    splits = {"train": train_idx, "val": val_idx, "test": test_idx}
    all_indices = np.concatenate([train_idx, val_idx, test_idx])

    # Build node features for ALL forms at once (vectorized)
    logger.info(f"  Building node features for {len(all_indices)} forms...")
    all_traces = traces[all_indices]  # (N, n_traces) — only need squarefree columns
    sf_cols = [n - 1 for n in sf_indices]  # 0-indexed columns
    trace_feats = all_traces[:, sf_cols].astype(np.float32)  # (N, n_nodes)
    # Broadcast static features: (N, n_nodes, 3) = trace(N,n_nodes,1) + static(1,n_nodes,2)
    all_x = np.concatenate([
        trace_feats[:, :, np.newaxis],
        np.broadcast_to(static_feats[np.newaxis, :, :], (len(all_indices), n_nodes, 2)),
    ], axis=2)  # (N, n_nodes, 3)

    # Compute normalization stats from training set
    train_x = all_x[:len(train_idx)]
    feat_mean = train_x.reshape(-1, 3).mean(axis=0).tolist()
    feat_std = train_x.reshape(-1, 3).std(axis=0).tolist()
    logger.info(f"  Node feat mean: {[f'{v:.4f}' for v in feat_mean]}")
    logger.info(f"  Node feat std:  {[f'{v:.4f}' for v in feat_std]}")

    # Targets
    train_meta = meta_df.iloc[train_idx]

    # Save using numpy mmap format (shared edge_index)
    output_dir = output_dir or DATA_DIR / "gnn_multiplicative"
    output_dir.mkdir(parents=True, exist_ok=True)

    np.save(output_dir / "shared_edge_index.npy", shared_edge_index)
    logger.info(f"  Saved shared_edge_index.npy ({n_edges:,} edges)")

    offset = 0
    for split_name, idx_array in splits.items():
        n_samples = len(idx_array)
        split_dir = output_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        split_x = all_x[offset:offset + n_samples]  # (n_samples, n_nodes, 3)
        np.save(split_dir / "x.npy", split_x.reshape(n_samples * n_nodes, 3))

        # Targets
        split_meta = meta_df.iloc[idx_array]
        np.save(split_dir / "y_z1.npy", split_meta["z1"].values.astype(np.float32))
        np.save(split_dir / "y_rank.npy", split_meta["analytic_rank"].values.astype(np.int64))
        np.save(split_dir / "y_cm.npy", split_meta["is_cm"].values.astype(np.int64))
        np.save(split_dir / "y_dim.npy", split_meta["dim"].values.astype(np.int64))
        np.save(split_dir / "level.npy", split_meta["level"].values.astype(np.int64))

        # LMFDB labels (for alignment with sklearn predictions)
        with open(split_dir / "labels.txt", "w") as f:
            for label in split_meta["label"].tolist():
                f.write(f"{label}\n")

        logger.info(f"  Saved {split_dir}/ ({n_samples} graphs)")
        offset += n_samples

    metadata = {
        "paradigm": "multiplicative",
        "num_nodes_per_graph": n_nodes,
        "node_feat_dim": 3,
        "num_edge_types": 2,
        "n_edges_per_graph": int(n_edges),
        "train_size": len(train_idx),
        "val_size": len(val_idx),
        "test_size": len(test_idx),
        "train_node_feat_mean": feat_mean,
        "train_node_feat_std": feat_std,
        "squarefree_count": n_nodes,
        "max_omega": max_omega,
        "shared_edge_index": True,
        "target_stats": {
            "z1": {
                "mean": float(train_meta["z1"].mean()),
                "std": float(train_meta["z1"].std()),
                "n_valid": int(train_meta["z1"].notna().sum()),
            },
            "rank": {
                "distribution": {
                    str(k): int(v)
                    for k, v in train_meta["analytic_rank"]
                    .value_counts()
                    .sort_index()
                    .items()
                }
            },
            "cm": {
                "distribution": {
                    str(k): int(v)
                    for k, v in train_meta["is_cm"]
                    .value_counts()
                    .sort_index()
                    .items()
                }
            },
            "dim": {
                "mean": float(train_meta["dim"].mean()),
                "std": float(train_meta["dim"].std()),
                "min": int(train_meta["dim"].min()),
                "max": int(train_meta["dim"].max()),
            },
        },
    }

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"  Saved {meta_path}")

    return None, metadata


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


def save_paradigm(
    graphs_dict: dict[str, list[Data]],
    metadata: dict,
    indices_dict: dict[str, np.ndarray],
    output_dir: Path,
    meta_df: pd.DataFrame,
) -> None:
    """Save train/val/test splits as numpy mmap-compatible files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for split_name in ["train", "val", "test"]:
        graphs = graphs_dict[split_name]
        idx_array = indices_dict[split_name]
        n_graphs = len(graphs)
        if n_graphs == 0:
            continue

        split_dir = output_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)

        # Node features: (N_total_nodes, feat_dim) float32
        all_x = np.concatenate([g.x.numpy() for g in graphs], axis=0)
        np.save(split_dir / "x.npy", all_x)

        # Edge index: (2, E_total) int32 (node indices fit in int32)
        edge_index_list = [g.edge_index.numpy().astype(np.int32) for g in graphs]
        all_edge_index = np.concatenate(edge_index_list, axis=1)
        np.save(split_dir / "edge_index.npy", all_edge_index)

        # Edge ptr: (N+1,) int64 boundaries
        edge_ptr = np.zeros(n_graphs + 1, dtype=np.int64)
        for i, ei in enumerate(edge_index_list):
            edge_ptr[i + 1] = edge_ptr[i] + ei.shape[1]
        np.save(split_dir / "edge_ptr.npy", edge_ptr)

        # Targets
        np.save(split_dir / "y_z1.npy", np.array([g.y_z1 for g in graphs], dtype=np.float32))
        np.save(split_dir / "y_rank.npy", np.array([g.y_rank for g in graphs], dtype=np.int64))
        np.save(split_dir / "y_cm.npy", np.array([g.y_cm for g in graphs], dtype=np.int64))
        np.save(split_dir / "y_dim.npy", np.array([g.y_dim for g in graphs], dtype=np.int64))
        np.save(split_dir / "level.npy", np.array([g.level for g in graphs], dtype=np.int64))

        # LMFDB labels (for alignment with sklearn predictions)
        split_labels = meta_df.iloc[idx_array]["label"].tolist()
        with open(split_dir / "labels.txt", "w") as f:
            for label in split_labels:
                f.write(f"{label}\n")

        logger.info(f"  Saved {split_dir}/ ({n_graphs} graphs, "
                     f"x={all_x.shape}, edges={all_edge_index.shape[1]:,})")

    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"  Saved {meta_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build PyG graph datasets from LMFDB Hecke trace data (Exp 12 Phase 0)",
    )
    parser.add_argument(
        "--paradigm",
        type=str,
        choices=["trace_index", "multiplicative", "both"],
        default="both",
        help="Which paradigm to build (default: both)",
    )
    parser.add_argument(
        "--num-traces",
        type=int,
        default=None,
        help="Limit to first N traces (for debugging)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Verbose output, limit to 5 samples per split",
    )
    parser.add_argument(
        "--cross-level",
        action="store_true",
        help="Use cross-level split (train<=N3000, val N3001-4000, test>N4000) instead of random stratified",
    )
    parser.add_argument(
        "--output-suffix",
        type=str,
        default=None,
        help="Suffix for output directory (e.g. 'cross_level')",
    )
    args = parser.parse_args()

    if args.debug:
        logger.remove()
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | {message}",
        )
        if args.num_traces is None:
            args.num_traces = 100

    t_start = time.time()

    logger.info("=" * 60)
    logger.info("Experiment 12 Phase 0: GNN Dataset Builder")
    logger.info("=" * 60)

    # Load and join data
    traces, labels, meta_df = load_and_join_data(num_traces=args.num_traces)
    ranks = meta_df["analytic_rank"].values

    # Stratified split
    if args.cross_level:
        levels = meta_df["level"].values
        train_idx, val_idx, test_idx = cross_level_split(levels, ranks)
        split_label = "cross-level"
    else:
        train_idx, val_idx, test_idx = stratified_split(ranks)
        split_label = "stratified"
    logger.info(
        f"Split ({split_label}): train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}"
    )
    indices_dict = {"train": train_idx, "val": val_idx, "test": test_idx}

    out_trace = OUT_TRACE_INDEX
    out_multi = DATA_DIR / "gnn_multiplicative"
    if args.output_suffix:
        out_trace = DATA_DIR / f"gnn_trace_index_{args.output_suffix}"
        out_multi = DATA_DIR / f"gnn_multiplicative_{args.output_suffix}"

    # Build paradigms
    if args.paradigm in ("trace_index", "both"):
        logger.info("-" * 60)
        logger.info("PARADIGM A: Trace-Index Graph")
        logger.info("-" * 60)
        graphs_a, meta_a = build_paradigm_a(
            traces, labels, meta_df, train_idx, val_idx, test_idx, debug=args.debug
        )
        save_paradigm(graphs_a, meta_a, indices_dict, out_trace, meta_df)

    if args.paradigm in ("multiplicative", "both"):
        logger.info("-" * 60)
        logger.info("PARADIGM C: Multiplicative Graph")
        logger.info("-" * 60)
        build_paradigm_c(
            traces, labels, meta_df, train_idx, val_idx, test_idx, out_multi, debug=args.debug
        )

    elapsed = time.time() - t_start
    logger.info(f"Done in {elapsed:.1f}s")
    logger.success("Dataset build complete.")


if __name__ == "__main__":
    main()
