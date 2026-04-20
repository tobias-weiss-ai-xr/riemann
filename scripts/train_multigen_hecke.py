"""
Full-graph ChebConv for Hecke eigenvalue prediction on SL(2,F_p) Cayley graphs
with MULTIPLE generator sets per prime.

Design: All generator sets for the same prime share the same Hecke target (since
Hecke eigenvalues are properties of the prime level, not the generator set). This
is an augmentation strategy — the GNN should learn to be INVARIANT to generator
choice.

Data layout:
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}.npz        — edges + num_nodes
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}_eigenvalues.npy — eigenvalues
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}_stats.npz   — spectral stats
    data/hecke/p{prime}_hecke.npz                              — Hecke targets

Target options:
    mean_a_p         - Mean |a_p| for primes p <= sqrt(N) (scalar regression)
    first_form_a2    - a_2 of the first cusp form (scalar regression)
    dim_cuspforms    - Dimension of S_2(Gamma_0(p)) (classification)
    deligne_ratio    - max(|a_p|)/(2*sqrt(p)) over first 20 prime eigenvalues (scalar)
    spectral_gap     - Graph's own spectral gap (scalar, NOT Hecke — architecture sanity check)

Evaluation:
    Primary:   Prime-level LOO-CV — leave one prime OUT (all ~10 gen sets). Average predictions.
    Secondary: Random 80/20 split by graph.

Usage:
    python train_multigen_hecke.py --target mean_a_p --leave-one-out
    python train_multigen_hecke.py --target spectral_gap --random-split
    python train_multigen_hecke.py --target dim_cuspforms
"""

from __future__ import annotations

import argparse
import time
from collections import deque
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from loguru import logger
from scipy.sparse import csr_matrix, diags, eye as speye
from scipy.sparse.linalg import eigsh
from torch_geometric.nn import global_mean_pool, global_max_pool

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path("/workspace/data")
MULTIGEN_DIR = DATA_DIR / "cayley-multigen"
HECKE_DIR = DATA_DIR / "hecke"
CHEB_CACHE_DIR = DATA_DIR / "cheb_multigen"

# Primes that HAVE cusp forms (skip 2,3,5,7,13 — dim_cuspforms=0)
PRIMES = [11, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]

# Generator types: fundamental_roots, root_weyl, rand_0..rand_7
GEN_TYPES = ["fr", "rw"] + [f"rand_{i}" for i in range(8)]
GEN_TYPE_TO_NAME = {
    "fr": "fundamental_roots",
    "rw": "root_weyl",
}
for _i in range(8):
    GEN_TYPE_TO_NAME[f"rand_{_i}"] = f"random_{_i}"

# Primes up to ~100 for computing mean_a_p
SMALL_PRIMES = [
    2,
    3,
    5,
    7,
    11,
    13,
    17,
    19,
    23,
    29,
    31,
    37,
    41,
    43,
    47,
    53,
    59,
    61,
    67,
    71,
    73,
    79,
    83,
    89,
    97,
    101,
]

# Number of random positional encoding dimensions
RPE_DIM = 8

TARGET_TYPES = [
    "mean_a_p",
    "first_form_a2",
    "dim_cuspforms",
    "deligne_ratio",
    "spectral_gap",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def discover_multigen_files(multigen_dir: Path) -> list[dict]:
    """Discover all available (prime, gen_type) pairs from the multigen directory."""
    entries = []
    if not multigen_dir.exists():
        logger.warning(f"Multigen directory not found: {multigen_dir}")
        return entries

    for f in sorted(multigen_dir.glob("sl2fp_p*_*.npz")):
        # Filename: sl2fp_p{prime}_{gen_type}.npz
        stem = f.stem  # sl2fp_p11_fr
        # Parse prime and gen_type
        # Remove "sl2fp_p" prefix
        rest = stem[len("sl2fp_p") :]
        # rest = "11_fr" or "61_rand_7"
        parts = rest.split("_", 1)
        if len(parts) != 2:
            logger.debug(f"Skipping unrecognized file: {f.name}")
            continue
        prime_str, gen_type = parts
        try:
            prime = int(prime_str)
        except ValueError:
            logger.debug(f"Cannot parse prime from: {f.name}")
            continue

        # Skip stats/eigenvalue files
        if gen_type.endswith("_stats") or gen_type.endswith("_eigenvalues"):
            continue

        # Check eigenvalues file exists
        eig_path = multigen_dir / f"sl2fp_p{prime}_{gen_type}_eigenvalues.npy"
        stats_path = multigen_dir / f"sl2fp_p{prime}_{gen_type}_stats.npz"

        entries.append(
            {
                "prime": prime,
                "gen_type": gen_type,
                "graph_path": f,
                "eigenvalues_path": eig_path,
                "stats_path": stats_path,
            }
        )

    logger.info(f"Discovered {len(entries)} multigen graph entries")
    return entries


def load_multigen_graph(entry: dict) -> dict | None:
    """Load a single multigen Cayley graph."""
    g = np.load(entry["graph_path"])
    return {
        "p": entry["prime"],
        "gen_type": entry["gen_type"],
        "edges": g["edges"].astype(np.int64),
        "num_nodes": int(g["num_nodes"]),
    }


def load_multigen_stats(entry: dict) -> dict | None:
    """Load eigenvalue stats for a multigen graph."""
    if not entry["stats_path"].exists():
        logger.debug(f"Missing stats for p={entry['prime']} gen={entry['gen_type']}")
        return None
    s = np.load(entry["stats_path"])
    return {
        "spectral_gap": float(s["spectral_gap"]),
        "ramanujan_ratio": float(s["ramanujan_ratio"]),
        "max_abs_eigenvalue": float(s["max_abs_eigenvalue"]),
        "is_ramanujan": bool(s["is_ramanujan"]),
    }


def load_hecke_data(p: int, hecke_dir: Path) -> dict | None:
    """Load Hecke eigenvalue data for prime p."""
    hecke_path = hecke_dir / f"p{p}_hecke.npz"
    if not hecke_path.exists():
        logger.debug(f"Missing Hecke data for p={p}, skipping")
        return None
    h = np.load(hecke_path)
    return {
        "p": p,
        "eigenvalues": h["eigenvalues"],  # (num_forms, 100)
        "num_forms": int(h["num_forms"]),
        "dim_cuspforms": int(h["dim_cuspforms"]),
    }


# ---------------------------------------------------------------------------
# Target computation
# ---------------------------------------------------------------------------


def compute_hecke_target(
    hecke: dict, target_type: str, p: int
) -> float | np.ndarray | int | None:
    """Compute the Hecke target value from Hecke eigenvalue data."""
    eigenvalues = hecke["eigenvalues"]
    num_forms = hecke["num_forms"]
    dim_cusp = hecke["dim_cuspforms"]

    if target_type == "dim_cuspforms":
        return dim_cusp

    if target_type == "mean_a_p":
        if num_forms == 0:
            return None
        threshold = np.sqrt(p**3) if p > 1 else 10
        prime_indices = [q - 1 for q in SMALL_PRIMES if q <= threshold]
        if not prime_indices:
            prime_indices = [1, 2, 4]
        form_eigs = eigenvalues[0, :]
        prime_eigs = [
            abs(form_eigs[pi]) for pi in prime_indices if pi < form_eigs.shape[0]
        ]
        if not prime_eigs:
            return None
        return float(np.mean(prime_eigs))

    if target_type == "first_form_a2":
        if num_forms == 0:
            return None
        return float(eigenvalues[0, 1])

    if target_type == "deligne_ratio":
        if num_forms == 0:
            return None
        form_eigs = eigenvalues[0, :]
        prime_indices = [
            q - 1 for q in SMALL_PRIMES if q - 1 < 20 and q - 1 < form_eigs.shape[0]
        ]
        if not prime_indices:
            return None
        max_ratio = 0.0
        for pi in prime_indices:
            q = SMALL_PRIMES[pi] if pi < len(SMALL_PRIMES) else pi + 1
            a_q = abs(form_eigs[pi])
            bound = 2.0 * np.sqrt(q)
            if bound > 0:
                ratio = a_q / bound
                max_ratio = max(max_ratio, ratio)
        return float(max_ratio)

    return None


# ---------------------------------------------------------------------------
# Node feature computation (verbatim from train_hecke_gnn.py)
# ---------------------------------------------------------------------------


def compute_node_features(
    edges: np.ndarray, num_nodes: int, seed: int = 42
) -> np.ndarray:
    """Compute per-node features: degree/4, clustering, triangle_norm, RPE."""
    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)
    adj.setdiag(0.0)
    adj.eliminate_zeros()

    deg = np.array(adj.sum(axis=1)).flatten().astype(np.float64)
    deg_norm = deg / 4.0

    if num_nodes <= 10000:
        A_cubed = (adj @ adj @ adj).toarray()
        triangles = np.diag(A_cubed).astype(np.float64) / 6.0
    elif num_nodes <= 100000:
        triangles = _estimate_triangles_sampled(adj, num_nodes, n_samples=3000)
    else:
        triangles = np.zeros(num_nodes, dtype=np.float64)

    denom = deg * (deg - 1)
    denom[denom == 0] = 1.0
    clustering = 2.0 * triangles / denom
    tri_max = triangles.max() if triangles.max() > 0 else 1.0
    tri_norm = triangles / tri_max

    rng = np.random.RandomState(seed)
    rpe = rng.randn(num_nodes, RPE_DIM).astype(np.float32) * 0.1

    features = np.column_stack([deg_norm, clustering, tri_norm, rpe])
    return features.astype(np.float32)


def _estimate_triangles_sampled(
    adj: csr_matrix, num_nodes: int, n_samples: int = 3000
) -> np.ndarray:
    """Estimate per-node triangle count via edge sampling."""
    triangles = np.zeros(num_nodes, dtype=np.float64)
    rows, cols = adj.nonzero()
    if len(rows) == 0:
        return triangles

    mask = rows < cols
    rows, cols = rows[mask], cols[mask]
    n_undirected = len(rows)
    if n_undirected == 0:
        return triangles

    sample_idx = np.random.choice(
        n_undirected, size=min(n_samples, n_undirected), replace=False
    )
    for idx in sample_idx:
        u, v = rows[idx], cols[idx]
        u_nbrs = set(adj[u].indices)
        v_nbrs = set(adj[v].indices)
        n_common = len(u_nbrs & v_nbrs)
        triangles[u] += n_common
        triangles[v] += n_common

    scale = n_undirected / len(sample_idx)
    triangles *= scale / 3.0
    return triangles


# ---------------------------------------------------------------------------
# Chebyshev precomputation (verbatim from train_hecke_gnn.py)
# ---------------------------------------------------------------------------


def compute_lambda_max(edges: np.ndarray, num_nodes: int) -> float:
    """Compute largest eigenvalue of the normalized Laplacian."""
    if num_nodes > 50000:
        return 2.0  # Too large for eigsh — use theoretical max

    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)
    adj.setdiag(0.0)
    adj.eliminate_zeros()

    deg = np.array(adj.sum(axis=1)).flatten()
    deg[deg == 0] = 1.0
    d_inv_sqrt = 1.0 / np.sqrt(deg)
    D_inv_sqrt = diags(d_inv_sqrt)

    L_norm = speye(num_nodes) - D_inv_sqrt @ adj @ D_inv_sqrt
    L_norm = csr_matrix(L_norm)

    k = min(6, num_nodes - 1)
    try:
        eigenvalues, _ = eigsh(L_norm, k=k, which="LM")
        lam_max = float(np.max(eigenvalues))
    except Exception:
        lam_max = 2.0

    return max(lam_max, 1.0)


def precompute_cheb_features(
    edges: np.ndarray,
    num_nodes: int,
    node_features: np.ndarray,
    K: int,
    lambda_max: float,
) -> np.ndarray:
    """Precompute Chebyshev polynomial features for a graph.

    T_0(L) = I, T_1(L) = L_scaled, T_k(L) = 2*L_scaled @ T_{k-1} - T_{k-2}
    where L_scaled = 2*L_norm/lambda_max - I.

    Returns (N, in_channels * (K+1)).
    """
    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)
    adj.setdiag(0.0)
    adj.eliminate_zeros()

    deg = np.array(adj.sum(axis=1)).flatten()
    deg[deg == 0] = 1.0
    d_inv_sqrt = 1.0 / np.sqrt(deg)
    D_inv_sqrt = diags(d_inv_sqrt)

    L_norm = speye(num_nodes, format="csr") - (D_inv_sqrt @ adj @ D_inv_sqrt)
    L_norm = csr_matrix(L_norm)

    L_scaled = (2.0 / lambda_max) * L_norm - speye(num_nodes, format="csr")
    L_scaled = csr_matrix(L_scaled)

    x = node_features.astype(np.float64)

    T_prev2 = x.copy()
    features_list = [T_prev2.copy()]

    if K >= 1:
        T_prev1 = L_scaled.dot(x)
        features_list.append(T_prev1.copy())

    for k in range(2, K + 1):
        T_k = 2.0 * L_scaled.dot(T_prev1) - T_prev2
        features_list.append(T_k.copy())
        T_prev2 = T_prev1
        T_prev1 = T_k

    cheb_features = np.concatenate(features_list, axis=1)
    return cheb_features.astype(np.float32)


# ---------------------------------------------------------------------------
# Graph-level statistics (extended with gen_type embedding + spectral stats)
# ---------------------------------------------------------------------------


def compute_graph_statistics(graph: dict) -> np.ndarray:
    """Compute graph-level scalar features (log nodes, log edges, density, diameter)."""
    num_nodes = graph["num_nodes"]
    num_edges = graph["edges"].shape[1]

    density = (2 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0.0
    diameter_est = _estimate_diameter(graph["edges"], num_nodes, n_samples=3)

    log_nodes = np.log(num_nodes)
    log_edges = np.log(num_edges)

    stats = np.array(
        [log_nodes, log_edges, density, float(diameter_est)],
        dtype=np.float32,
    )
    return stats


def _estimate_diameter(edges: np.ndarray, num_nodes: int, n_samples: int = 3) -> float:
    """Estimate graph diameter via BFS from random nodes."""
    if num_nodes > 100000:
        return 0.0

    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)

    max_dist = 0
    for _ in range(n_samples):
        start = np.random.randint(num_nodes)
        visited = np.zeros(num_nodes, dtype=bool)
        visited[start] = True
        queue = deque([(start, 0)])
        while queue:
            node, dist = queue.popleft()
            if dist > max_dist:
                max_dist = dist
            for nb in adj[node].indices:
                if not visited[nb]:
                    visited[nb] = True
                    queue.append((nb, dist + 1))

    return float(max_dist)


def encode_gen_type_onehot(gen_type: str) -> np.ndarray:
    """One-hot encode generator type (11 classes: fr, rw, rand_0..rand_7)."""
    vec = np.zeros(len(GEN_TYPES), dtype=np.float32)
    if gen_type in GEN_TYPES:
        vec[GEN_TYPES.index(gen_type)] = 1.0
    return vec


def build_graph_stats_extended(
    graph: dict, spec_stats: dict | None, gen_type: str
) -> np.ndarray:
    """Build extended graph stats: [base_stats(4), gen_type_onehot(11), spectral_gap, ramanujan_ratio]."""
    base_stats = compute_graph_statistics(graph)  # (4,)
    gen_onehot = encode_gen_type_onehot(gen_type)  # (11,)

    if spec_stats is not None:
        spectral = np.array(
            [spec_stats["spectral_gap"], spec_stats["ramanujan_ratio"]],
            dtype=np.float32,
        )
    else:
        spectral = np.zeros(2, dtype=np.float32)

    return np.concatenate([base_stats, gen_onehot, spectral])  # (17,)


# ---------------------------------------------------------------------------
# Dataset preparation with separate caching
# ---------------------------------------------------------------------------


def prepare_dataset(
    entries: list[dict],
    target_type: str,
    K: int,
    hecke_dir: Path,
    multigen_dir: Path,
    force_recompute: bool = False,
) -> list[dict]:
    """Prepare dataset with precomputed Chebyshev features and targets.

    For Hecke targets (mean_a_p, first_form_a2, dim_cuspforms, deligne_ratio):
      target comes from Hecke data (same for all gen_types of same prime).
    For spectral_gap:
      target comes from per-graph eigenvalue stats (varies by gen_type).
    """
    CHEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dataset = []
    t0 = time.time()

    skipped_no_graph = 0
    skipped_no_hecke = 0
    skipped_no_target = 0

    # Pre-load Hecke data for all primes (shared across gen_types)
    hecke_cache: dict[int, dict | None] = {}
    for entry in entries:
        p = entry["prime"]
        if p not in hecke_cache:
            hecke_cache[p] = load_hecke_data(p, hecke_dir)

    for entry in entries:
        p = entry["prime"]
        gen_type = entry["gen_type"]

        # Load graph
        graph = load_multigen_graph(entry)
        if graph is None:
            skipped_no_graph += 1
            continue

        # Load eigenvalue stats
        spec_stats = load_multigen_stats(entry)

        # Compute target
        if target_type == "spectral_gap":
            if spec_stats is not None:
                target = spec_stats["spectral_gap"]
            else:
                skipped_no_target += 1
                continue
        else:
            hecke = hecke_cache.get(p)
            if hecke is None:
                skipped_no_hecke += 1
                continue
            target = compute_hecke_target(hecke, target_type, p)
            if target is None:
                skipped_no_target += 1
                logger.debug(
                    f"  p={p} gen={gen_type}: cannot compute target '{target_type}'"
                )
                continue

        # Chebyshev feature cache key
        cache_path = CHEB_CACHE_DIR / f"sl2fp_p{p}_{gen_type}_K{K}.npz"

        if cache_path.exists() and not force_recompute:
            cached = np.load(cache_path)
            cheb_features = cached["cheb_features"]
            graph_stats = cached["graph_stats"]
            logger.debug(
                f"  p={p} gen={gen_type}: loaded cached features {cheb_features.shape}"
            )
        else:
            logger.info(
                f"  p={p} gen={gen_type}: computing features "
                f"(N={graph['num_nodes']}, E={graph['edges'].shape[1]})..."
            )
            # Seed based on prime+gen_type for reproducibility
            seed_val = hash(f"{p}_{gen_type}") % (2**31)
            node_feats = compute_node_features(
                graph["edges"], graph["num_nodes"], seed=seed_val
            )
            lam_max = compute_lambda_max(graph["edges"], graph["num_nodes"])
            logger.debug(f"    lambda_max={lam_max:.4f}")

            t1 = time.time()
            cheb_features = precompute_cheb_features(
                graph["edges"], graph["num_nodes"], node_feats, K, lam_max
            )
            t2 = time.time()
            logger.debug(f"    Cheb features: {cheb_features.shape} in {t2 - t1:.2f}s")

            # Build extended graph stats
            graph_stats = build_graph_stats_extended(graph, spec_stats, gen_type)

            np.savez_compressed(
                cache_path, cheb_features=cheb_features, graph_stats=graph_stats
            )

        # For Hecke targets, also store dim_cuspforms for classification baseline
        hecke_info = hecke_cache.get(p)
        dim_cusp = hecke_info["dim_cuspforms"] if hecke_info else 0

        dataset.append(
            {
                "p": p,
                "gen_type": gen_type,
                "num_nodes": graph["num_nodes"],
                "target": target,
                "dim_cuspforms": dim_cusp,
                "cheb_features": cheb_features,
                "graph_stats": graph_stats,
            }
        )

    elapsed = time.time() - t0
    logger.info(
        f"Prepared {len(dataset)} graphs in {elapsed:.1f}s "
        f"(skipped {skipped_no_graph} no graph, {skipped_no_hecke} no Hecke, "
        f"{skipped_no_target} no target)"
    )
    return dataset


# ---------------------------------------------------------------------------
# Model (verbatim from train_hecke_gnn.py)
# ---------------------------------------------------------------------------


class FullGraphChebNet(nn.Module):
    """MLP over precomputed Chebyshev features with dual pooling.

    Uses LayerNorm instead of BatchNorm to handle batch_size=1.
    Input = [mean_pool, max_pool, graph_stats].
    """

    def __init__(
        self,
        cheb_feature_dim: int,
        graph_stats_dim: int,
        output_dim: int = 1,
        hidden_dim: int = 64,
        dropout: float = 0.2,
    ):
        super().__init__()
        input_dim = 2 * cheb_feature_dim + graph_stats_dim

        self.mlp = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim),
        )

    def forward(
        self,
        cheb_features: torch.Tensor,
        graph_stats: torch.Tensor,
        batch: torch.Tensor,
    ) -> torch.Tensor:
        pool_mean = global_mean_pool(cheb_features, batch)
        pool_max = global_max_pool(cheb_features, batch)
        x = torch.cat([pool_mean, pool_max, graph_stats], dim=1)
        out = self.mlp(x)
        if out.shape[-1] == 1:
            return out.squeeze(-1)
        return out


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(preds: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    """Compute MAE, RMSE, R^2 for regression."""
    mae = float(np.mean(np.abs(preds - targets)))
    rmse = float(np.sqrt(np.mean((preds - targets) ** 2)))
    ss_res = float(np.sum((targets - preds) ** 2))
    ss_tot = float(np.sum((targets - targets.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return {"mae": mae, "rmse": rmse, "r2": r2}


def compute_classification_metrics(
    preds: np.ndarray, targets: np.ndarray, num_classes: int
) -> dict[str, float]:
    """Compute accuracy and macro-F1 for classification."""
    pred_labels = np.argmax(preds, axis=1)
    accuracy = float(np.mean(pred_labels == targets))

    f1_scores = []
    for c in range(num_classes):
        tp = np.sum((pred_labels == c) & (targets == c))
        fp = np.sum((pred_labels == c) & (targets != c))
        fn = np.sum((pred_labels != c) & (targets == c))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        f1_scores.append(f1)

    macro_f1 = float(np.mean(f1_scores)) if f1_scores else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_single_graph(
    model: FullGraphChebNet,
    graph: dict,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    loss_fn,
) -> float:
    """Train on a single graph (one sample in the batch)."""
    model.train()
    cheb = torch.from_numpy(graph["cheb_features"]).to(device)
    stats = torch.from_numpy(graph["graph_stats"]).unsqueeze(0).to(device)
    target = graph["target"]

    if isinstance(target, np.ndarray):
        target = torch.from_numpy(target).unsqueeze(0).to(device)
    else:
        target = torch.tensor([target], dtype=torch.float32).to(device)

    batch = torch.zeros(graph["num_nodes"], dtype=torch.long, device=device)

    optimizer.zero_grad()
    pred = model(cheb, stats, batch)
    loss = loss_fn(pred, target)
    loss.backward()
    optimizer.step()
    return loss.item()


@torch.no_grad()
def predict_single(
    model: FullGraphChebNet,
    graph: dict,
    device: torch.device,
) -> np.ndarray | float:
    """Predict target for a single graph."""
    model.eval()
    cheb = torch.from_numpy(graph["cheb_features"]).to(device)
    stats = torch.from_numpy(graph["graph_stats"]).unsqueeze(0).to(device)
    batch = torch.zeros(graph["num_nodes"], dtype=torch.long, device=device)
    out = model(cheb, stats, batch)
    result = out.cpu().numpy()
    return result[0]


def train_and_evaluate_fold(
    train_graphs: list[dict],
    test_graphs: list[dict],
    cheb_feature_dim: int,
    graph_stats_dim: int,
    output_dim: int,
    hidden_dim: int,
    epochs: int,
    lr: float,
    seed: int,
    device: torch.device,
    loss_fn,
    is_classification: bool = False,
) -> dict:
    """Train on train_graphs, evaluate on test_graphs. Returns keyed predictions."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    model = FullGraphChebNet(
        cheb_feature_dim=cheb_feature_dim,
        graph_stats_dim=graph_stats_dim,
        output_dim=output_dim,
        hidden_dim=hidden_dim,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    for epoch in range(1, epochs + 1):
        indices = np.random.permutation(len(train_graphs))
        for idx in indices:
            train_single_graph(model, train_graphs[idx], optimizer, device, loss_fn)
        scheduler.step()

    predictions = {}
    for g in test_graphs:
        key = (g["p"], g["gen_type"])
        pred = predict_single(model, g, device)
        actual = g["target"]
        if isinstance(actual, np.ndarray):
            actual_np = actual
        else:
            actual_np = np.array([actual])

        if isinstance(pred, np.ndarray):
            pred_np = pred
        else:
            pred_np = np.array([pred])

        predictions[key] = {
            "predicted": pred_np,
            "actual": actual_np,
        }

    return predictions


# ---------------------------------------------------------------------------
# Linear baseline
# ---------------------------------------------------------------------------


def linear_baseline_scalar(dataset: list[dict], target_type: str) -> dict:
    """Predict scalar target as linear function of log(num_nodes) + spectral_gap."""
    # For spectral_gap target, use log(num_nodes) as feature
    # For Hecke targets, also include spectral_gap from graph_stats if available
    log_nodes = np.array([np.log(g["num_nodes"]) for g in dataset])
    targets = np.array([float(g["target"]) for g in dataset])

    # Use log(num_nodes) and spectral_gap from graph_stats as features
    # graph_stats layout: [log_nodes, log_edges, density, diameter, gen_onehot(11), spectral_gap, ramanujan_ratio]
    spectral_gaps = np.array(
        [g["graph_stats"][15] for g in dataset]
    )  # index 15 = spectral_gap

    X = np.column_stack([log_nodes, spectral_gaps, np.ones(len(log_nodes))])
    coeffs, _, _, _ = np.linalg.lstsq(X, targets, rcond=None)

    preds = X @ coeffs
    metrics = compute_metrics(preds, targets)

    return {
        "metrics": metrics,
        "predictions": {
            (g["p"], g["gen_type"]): {"predicted": p, "actual": float(g["target"])}
            for g, p in zip(dataset, preds)
        },
    }


def linear_baseline_classification(dataset: list[dict]) -> dict:
    """Baseline: always predict the majority class."""
    targets = np.array([int(g["target"]) for g in dataset])
    unique, counts = np.unique(targets, return_counts=True)
    majority_class = unique[np.argmax(counts)]

    pred_labels = np.full_like(targets, majority_class)
    num_classes = int(targets.max()) + 1
    metrics = compute_classification_metrics(
        np.eye(num_classes)[pred_labels], targets, num_classes
    )

    return {
        "majority_class": int(majority_class),
        "metrics": metrics,
    }


# ---------------------------------------------------------------------------
# Prime-level LOO-CV
# ---------------------------------------------------------------------------


def run_prime_loo_cv(
    dataset: list[dict],
    cheb_feature_dim: int,
    graph_stats_dim: int,
    output_dim: int,
    hidden_dim: int,
    epochs: int,
    lr: float,
    seed: int,
    device: torch.device,
    loss_fn,
    is_classification: bool,
    target_type: str,
) -> dict:
    """Leave-one-prime-out cross-validation.

    For each fold, leave ALL graphs of one prime out. Train on the rest.
    Test on all held-out graphs. Average predictions across generator sets
    for the test prime.
    """
    # Get unique primes in dataset
    primes_in_data = sorted(set(g["p"] for g in dataset))
    logger.info(f"LOO-CV over {len(primes_in_data)} primes: {primes_in_data}")

    all_preds = []  # per-prime averaged predictions
    all_actuals = []
    per_prime_results = {}

    t_loo_start = time.time()

    for i, test_prime in enumerate(primes_in_data):
        test_graphs = [g for g in dataset if g["p"] == test_prime]
        train_graphs = [g for g in dataset if g["p"] != test_prime]

        logger.info(
            f"\nFold {i + 1}/{len(primes_in_data)}: "
            f"leaving out p={test_prime} "
            f"({len(test_graphs)} graphs), training on {len(train_graphs)} graphs "
            f"from {len(set(g['p'] for g in train_graphs))} primes"
        )

        t0 = time.time()
        predictions = train_and_evaluate_fold(
            train_graphs=train_graphs,
            test_graphs=test_graphs,
            cheb_feature_dim=cheb_feature_dim,
            graph_stats_dim=graph_stats_dim,
            output_dim=output_dim,
            hidden_dim=hidden_dim,
            epochs=epochs,
            lr=lr,
            seed=seed,
            device=device,
            loss_fn=loss_fn,
            is_classification=is_classification,
        )
        elapsed = time.time() - t0

        # Collect per-gen predictions
        per_gen_preds = []
        per_gen_actuals = []
        for g in test_graphs:
            key = (g["p"], g["gen_type"])
            pred = predictions[key]
            actual = g["target"]

            pred_val = pred["predicted"]
            if not isinstance(pred_val, np.ndarray):
                pred_val = np.array([pred_val])

            per_gen_preds.append(pred_val)
            if isinstance(actual, np.ndarray):
                per_gen_actuals.append(actual)
            else:
                per_gen_actuals.append(np.array([actual]))

            if isinstance(pred["predicted"], np.ndarray):
                logger.info(
                    f"  gen={g['gen_type']:8s}: "
                    f"predicted={np.array2string(pred['predicted'], precision=4, separator=', ')}"
                )
            else:
                logger.info(
                    f"  gen={g['gen_type']:8s}: "
                    f"predicted={pred['predicted']:.6f}  actual={actual:.6f}  "
                    f"error={pred['predicted'] - actual:+.6f}"
                )

        # Average predictions across generator sets for this prime
        avg_pred = np.mean(per_gen_preds, axis=0)
        avg_actual = per_gen_actuals[0]  # all the same for Hecke targets

        per_prime_results[test_prime] = {
            "avg_predicted": avg_pred,
            "actual": avg_actual,
            "num_gen_sets": len(test_graphs),
            "per_gen_preds": per_gen_preds,
            "time": elapsed,
        }

        all_preds.append(avg_pred)
        all_actuals.append(avg_actual)

        if not isinstance(avg_pred, np.ndarray):
            logger.info(
                f"  >>> p={test_prime:3d} AVG: predicted={avg_pred:.6f}  "
                f"actual={avg_actual:.6f}  error={avg_pred - float(avg_actual):+.6f}  "
                f"({elapsed:.1f}s)"
            )
        else:
            logger.info(
                f"  >>> p={test_prime:3d} AVG: "
                f"predicted={np.array2string(avg_pred, precision=4, separator=', ')}  "
                f"({elapsed:.1f}s)"
            )

    loo_elapsed = time.time() - t_loo_start

    # Compute aggregate metrics
    logger.info("\n" + "=" * 70)
    logger.info("PRIME-LEVEL LOO-CV RESULTS")
    logger.info("=" * 70)

    if is_classification:
        loo_preds_np = np.array(all_preds)
        loo_actuals_np = np.array([int(a) for a in all_actuals], dtype=int)
        num_classes_loo = int(loo_actuals_np.max()) + 1
        loo_metrics = compute_classification_metrics(
            loo_preds_np, loo_actuals_np, num_classes_loo
        )
        logger.info(
            f"  Model:  Accuracy={loo_metrics['accuracy']:.4f}  "
            f"Macro-F1={loo_metrics['macro_f1']:.4f}"
        )
    else:
        all_preds_arr = np.array(
            [p if isinstance(p, np.ndarray) else [p] for p in all_preds]
        ).squeeze()
        all_actuals_arr = (
            np.array([a if isinstance(a, np.ndarray) else [a] for a in all_actuals])
            .squeeze()
            .astype(float)
        )

        loo_metrics = compute_metrics(all_preds_arr.astype(float), all_actuals_arr)
        logger.info(
            f"  Model:  MAE={loo_metrics['mae']:.6f}  "
            f"RMSE={loo_metrics['rmse']:.6f}  R²={loo_metrics['r2']:.4f}"
        )

        # Per-prime table
        logger.info(
            f"\n  {'Prime':>6s}  {'Actual':>10s}  {'Predicted':>10s}  "
            f"{'Error':>10s}  {'Abs Err':>10s}  {'# GenSets':>8s}"
        )
        logger.info(
            f"  {'-' * 6}  {'-' * 10}  {'-' * 10}  {'-' * 10}  {'-' * 10}  {'-' * 8}"
        )
        for p in sorted(per_prime_results.keys()):
            r = per_prime_results[p]
            actual_val = (
                float(r["actual"])
                if not isinstance(r["actual"], np.ndarray)
                else float(r["actual"][0])
            )
            pred_val = (
                float(r["avg_predicted"])
                if not isinstance(r["avg_predicted"], np.ndarray)
                else float(r["avg_predicted"][0])
            )
            err = pred_val - actual_val
            logger.info(
                f"  {p:6d}  {actual_val:10.4f}  {pred_val:10.4f}  "
                f"{err:+10.4f}  {abs(err):10.4f}  {r['num_gen_sets']:8d}"
            )

    logger.info(f"\n  Total LOO time: {loo_elapsed:.1f}s")
    return {
        "metrics": loo_metrics,
        "per_prime": per_prime_results,
        "total_time": loo_elapsed,
    }


# ---------------------------------------------------------------------------
# Random split evaluation
# ---------------------------------------------------------------------------


def run_random_split(
    dataset: list[dict],
    cheb_feature_dim: int,
    graph_stats_dim: int,
    output_dim: int,
    hidden_dim: int,
    epochs: int,
    lr: float,
    seed: int,
    device: torch.device,
    loss_fn,
    is_classification: bool,
    test_ratio: float = 0.2,
) -> dict:
    """Random 80/20 split by graph (not by prime).

    This tests if the GNN can distinguish generator sets — since multiple
    gen_sets per prime share the same Hecke label, this is a harder test
    of overfitting to gen_set-specific features.
    """
    n = len(dataset)
    rng = np.random.RandomState(seed)
    indices = rng.permutation(n)
    n_test = max(1, int(n * test_ratio))
    test_idx = set(indices[:n_test].tolist())
    train_graphs = [g for i, g in enumerate(dataset) if i not in test_idx]
    test_graphs = [g for i, g in enumerate(dataset) if i in test_idx]

    logger.info(f"RANDOM SPLIT: train={len(train_graphs)}, test={len(test_graphs)}")

    t0 = time.time()
    predictions = train_and_evaluate_fold(
        train_graphs=train_graphs,
        test_graphs=test_graphs,
        cheb_feature_dim=cheb_feature_dim,
        graph_stats_dim=graph_stats_dim,
        output_dim=output_dim,
        hidden_dim=hidden_dim,
        epochs=epochs,
        lr=lr,
        seed=seed,
        device=device,
        loss_fn=loss_fn,
        is_classification=is_classification,
    )
    elapsed = time.time() - t0

    split_preds = []
    split_actuals = []

    for g in test_graphs:
        key = (g["p"], g["gen_type"])
        pred = predictions[key]
        actual = g["target"]

        pred_val = pred["predicted"]
        if not isinstance(pred_val, np.ndarray):
            pred_val = np.array([pred_val])

        split_preds.append(pred_val)
        if isinstance(actual, np.ndarray):
            split_actuals.append(actual)
        else:
            split_actuals.append(np.array([actual]))

        if isinstance(pred["predicted"], np.ndarray):
            logger.info(
                f"  p={g['p']:3d} gen={g['gen_type']:8s}: "
                f"predicted={np.array2string(pred['predicted'], precision=4, separator=', ')}"
            )
        else:
            logger.info(
                f"  p={g['p']:3d} gen={g['gen_type']:8s}: "
                f"predicted={pred['predicted']:.6f}  actual={actual:.6f}"
            )

    # Compute metrics
    logger.info("-" * 70)
    if is_classification:
        all_preds_np = np.array(split_preds)
        all_actuals_np = np.array([int(a) for a in split_actuals], dtype=int)
        num_classes_rs = int(all_actuals_np.max()) + 1
        metrics = compute_classification_metrics(
            all_preds_np, all_actuals_np, num_classes_rs
        )
        logger.info(
            f"  Accuracy={metrics['accuracy']:.4f}  Macro-F1={metrics['macro_f1']:.4f}"
        )
    else:
        all_preds_arr = np.array(
            [p if isinstance(p, np.ndarray) else [p] for p in split_preds]
        ).squeeze()
        all_actuals_arr = (
            np.array([a if isinstance(a, np.ndarray) else [a] for a in split_actuals])
            .squeeze()
            .astype(float)
        )
        metrics = compute_metrics(all_preds_arr, all_actuals_arr)
        logger.info(
            f"  MAE={metrics['mae']:.6f}  RMSE={metrics['rmse']:.6f}  "
            f"R²={metrics['r2']:.4f}"
        )

    logger.info(f"  Training time: {elapsed:.1f}s")
    return {"metrics": metrics, "time": elapsed}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Multi-generator GNN for Hecke eigenvalue prediction on Cayley graphs"
    )
    parser.add_argument("--K", type=int, default=3, help="Chebyshev polynomial order")
    parser.add_argument("--hidden", type=int, default=64, help="MLP hidden dim")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--target",
        type=str,
        default="mean_a_p",
        choices=TARGET_TYPES,
        help="Target to predict",
    )
    parser.add_argument(
        "--leave-one-out",
        action="store_true",
        help="Run prime-level LOO-CV",
    )
    parser.add_argument(
        "--random-split",
        action="store_true",
        help="Run random 80/20 split",
    )
    parser.add_argument(
        "--force-recompute",
        action="store_true",
        help="Force recomputation of cached Chebyshev features",
    )
    parser.add_argument(
        "--multigen-dir",
        type=str,
        default=None,
        help="Directory containing multi-generator graphs (default: data/cayley-multigen/)",
    )
    parser.add_argument(
        "--hecke-dir",
        type=str,
        default=None,
        help="Directory containing Hecke eigenvalue data",
    )
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    multigen_dir = Path(args.multigen_dir) if args.multigen_dir else MULTIGEN_DIR
    hecke_dir = Path(args.hecke_dir) if args.hecke_dir else HECKE_DIR

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")
    logger.info(f"Target: {args.target}")
    logger.info(f"Multigen dir: {multigen_dir}")
    logger.info(f"Hecke dir: {hecke_dir}")

    # Determine output dimensions and loss
    is_classification = args.target == "dim_cuspforms"
    is_spectral_gap = args.target == "spectral_gap"

    if is_classification:
        output_dim = 0  # will be set after loading data
        logger.info("Mode: classification (CrossEntropyLoss)")
    elif is_spectral_gap:
        output_dim = 1
        logger.info(
            "Mode: spectral_gap regression (NOT Hecke — architecture sanity check)"
        )
    else:
        output_dim = 1
        logger.info("Mode: scalar regression (MSELoss)")

    # --- Discover and load data ---
    logger.info("=" * 70)
    logger.info("Discovering multi-generator graphs...")
    entries = discover_multigen_files(multigen_dir)

    if len(entries) == 0:
        logger.error(
            "No multigen graph files found. "
            f"Expected: {multigen_dir}/sl2fp_p{{prime}}_{{gen_type}}.npz"
        )
        logger.info(
            "To generate multigen data, run the multi-generator graph generation script."
        )
        return

    # Filter to target primes
    target_entries = [e for e in entries if e["prime"] in PRIMES]
    logger.info(
        f"  {len(target_entries)} entries for target primes (filtered from {len(entries)})"
    )

    # --- Prepare dataset ---
    logger.info("=" * 70)
    logger.info(f"Preparing dataset (K={args.K}, RPE_DIM={RPE_DIM})...")
    dataset = prepare_dataset(
        entries=target_entries,
        target_type=args.target,
        K=args.K,
        hecke_dir=hecke_dir,
        multigen_dir=multigen_dir,
        force_recompute=args.force_recompute,
    )

    if len(dataset) == 0:
        logger.error("No graphs with valid targets found. Exiting.")
        return

    # Set classification output dim
    if is_classification:
        all_classes = sorted(set(int(g["target"]) for g in dataset))
        num_classes = max(all_classes) + 1
        output_dim = num_classes
        logger.info(f"Classification classes: {all_classes}, num_classes={num_classes}")

    cheb_feature_dim = dataset[0]["cheb_features"].shape[1]
    graph_stats_dim = dataset[0]["graph_stats"].shape[0]
    logger.info(
        f"Cheb feature dim: {cheb_feature_dim}, Graph stats dim: {graph_stats_dim} "
        f"(4 base + 11 gen_onehot + 2 spectral), "
        f"Output dim: {output_dim}, Dataset size: {len(dataset)}"
    )

    # Verify consistent dimensions
    for g in dataset:
        assert g["cheb_features"].shape[1] == cheb_feature_dim, (
            f"Inconsistent cheb dim for p={g['p']} gen={g['gen_type']}: "
            f"{g['cheb_features'].shape[1]} vs {cheb_feature_dim}"
        )
        assert g["graph_stats"].shape[0] == graph_stats_dim, (
            f"Inconsistent graph_stats dim for p={g['p']} gen={g['gen_type']}: "
            f"{g['graph_stats'].shape[0]} vs {graph_stats_dim}"
        )

    # Report per-prime graph counts
    prime_counts: dict[int, int] = {}
    for g in dataset:
        prime_counts[g["p"]] = prime_counts.get(g["p"], 0) + 1
    logger.info("Graphs per prime:")
    for p in sorted(prime_counts.keys()):
        logger.info(f"  p={p:3d}: {prime_counts[p]} graphs")

    # --- Linear baseline ---
    logger.info("\n" + "=" * 70)
    if is_classification:
        logger.info("LINEAR BASELINE: majority class prediction")
        baseline = linear_baseline_classification(dataset)
        m = baseline["metrics"]
        logger.info(f"  Majority class: {baseline['majority_class']}")
        logger.info(f"  Accuracy={m['accuracy']:.4f}  Macro-F1={m['macro_f1']:.4f}")
    else:
        logger.info("LINEAR BASELINE: target ~ a*log(N) + b*spectral_gap + c")
        baseline = linear_baseline_scalar(dataset, args.target)
        m = baseline["metrics"]
        logger.info(f"  MAE={m['mae']:.6f}  RMSE={m['rmse']:.6f}  R²={m['r2']:.4f}")

    # --- Loss function ---
    if is_classification:
        loss_fn = nn.CrossEntropyLoss()
    else:
        loss_fn = nn.MSELoss()

    # --- Prime-level LOO-CV ---
    if args.leave_one_out:
        logger.info("\n" + "=" * 70)
        logger.info(
            f"PRIME-LEVEL LEAVE-ONE-OUT CV "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs}, target={args.target})"
        )
        loo_results = run_prime_loo_cv(
            dataset=dataset,
            cheb_feature_dim=cheb_feature_dim,
            graph_stats_dim=graph_stats_dim,
            output_dim=output_dim,
            hidden_dim=args.hidden,
            epochs=args.epochs,
            lr=args.lr,
            seed=args.seed,
            device=device,
            loss_fn=loss_fn,
            is_classification=is_classification,
            target_type=args.target,
        )

    # --- Random split ---
    if args.random_split:
        logger.info("\n" + "=" * 70)
        logger.info(
            f"RANDOM SPLIT EVALUATION "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs}, target={args.target})"
        )
        rs_results = run_random_split(
            dataset=dataset,
            cheb_feature_dim=cheb_feature_dim,
            graph_stats_dim=graph_stats_dim,
            output_dim=output_dim,
            hidden_dim=args.hidden,
            epochs=args.epochs,
            lr=args.lr,
            seed=args.seed,
            device=device,
            loss_fn=loss_fn,
            is_classification=is_classification,
        )

    # --- If no evaluation mode specified, run both ---
    if not args.leave_one_out and not args.random_split:
        logger.info(
            "\nNo evaluation mode specified. Running both LOO-CV and random split."
        )
        logger.info("=" * 70)
        logger.info(
            f"PRIME-LEVEL LEAVE-ONE-OUT CV "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs}, target={args.target})"
        )
        loo_results = run_prime_loo_cv(
            dataset=dataset,
            cheb_feature_dim=cheb_feature_dim,
            graph_stats_dim=graph_stats_dim,
            output_dim=output_dim,
            hidden_dim=args.hidden,
            epochs=args.epochs,
            lr=args.lr,
            seed=args.seed,
            device=device,
            loss_fn=loss_fn,
            is_classification=is_classification,
            target_type=args.target,
        )

        logger.info("\n" + "=" * 70)
        logger.info(
            f"RANDOM SPLIT EVALUATION "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs}, target={args.target})"
        )
        rs_results = run_random_split(
            dataset=dataset,
            cheb_feature_dim=cheb_feature_dim,
            graph_stats_dim=graph_stats_dim,
            output_dim=output_dim,
            hidden_dim=args.hidden,
            epochs=args.epochs,
            lr=args.lr,
            seed=args.seed,
            device=device,
            loss_fn=loss_fn,
            is_classification=is_classification,
        )

    # --- Summary comparison ---
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Target:           {args.target}")
    logger.info(
        f"  Dataset size:     {len(dataset)} graphs from {len(prime_counts)} primes"
    )
    logger.info(f"  Cheb K:           {args.K}")
    logger.info(f"  Hidden dim:       {args.hidden}")
    logger.info(
        f"  Graph stats dim:  {graph_stats_dim} (4 base + 11 gen_onehot + 2 spectral)"
    )
    if not is_classification:
        logger.info(f"  Linear baseline:  MAE={m['mae']:.6f}  R²={m['r2']:.4f}")
        if args.leave_one_out or (not args.leave_one_out and not args.random_split):
            loo_m = loo_results["metrics"]
            logger.info(
                f"  LOO-CV model:     MAE={loo_m['mae']:.6f}  "
                f"R²={loo_m['r2']:.4f}  "
                f"(improvement over baseline: R² {loo_m['r2'] - m['r2']:+.4f})"
            )


if __name__ == "__main__":
    main()
