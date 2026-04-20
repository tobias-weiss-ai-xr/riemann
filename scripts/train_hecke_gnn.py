"""
Full-graph ChebConv for Hecke eigenvalue prediction on SL(2,F_p) Cayley graphs.

Reuses the proven architecture from train_fullgraph_cheb.py (Chebyshev precomputation,
RPE, dual pooling, LayerNorm MLP) but targets Hecke eigenvalue prediction instead of
spectral gap. This explores the LPS/Pizer bridge connecting graph eigenvalues to
Hecke eigenvalues of modular forms in S_2(Gamma_0(p)).

Target options:
  mean_a_p         - Mean |a_p| for primes p <= sqrt(N) (scalar regression)
  first_form_a2    - a_2 of the first cusp form (scalar regression)
  first_form_vector - First 10 Hecke eigenvalues of first cusp form (vector regression)
  dim_cuspforms    - Dimension of S_2(Gamma_0(p)) (classification)
  deligne_ratio    - max(|a_p|)/(2*sqrt(p)) over first 20 prime eigenvalues (scalar)

Usage:
    python train_hecke_gnn.py --target mean_a_p
    python train_hecke_gnn.py --target first_form_vector --epochs 500
    python train_hecke_gnn.py --target dim_cuspforms --leave-one-out
    python train_hecke_gnn.py --target deligne_ratio --K 5
"""

from __future__ import annotations

import argparse
import time
from collections import deque
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger
from scipy.sparse import csr_matrix, diags, eye as speye
from scipy.sparse.linalg import eigsh
from torch_geometric.nn import global_mean_pool, global_max_pool

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path("/workspace/data")
GRAPH_DIR = DATA_DIR / "cayley-graphs"
HECKE_DIR = DATA_DIR / "hecke"
CHEB_CACHE_DIR = DATA_DIR / "cheb_precomputed"
MODEL_DIR = DATA_DIR / "models"

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]

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

# Target types
TARGET_TYPES = [
    "mean_a_p",
    "first_form_a2",
    "first_form_vector",
    "dim_cuspforms",
    "deligne_ratio",
]


# ---------------------------------------------------------------------------
# Graph loading (same as spectral gap script)
# ---------------------------------------------------------------------------


def load_full_graph(p: int) -> dict | None:
    """Load a full Cayley graph."""
    graph_path = GRAPH_DIR / f"sl2fp_p{p}.npz"
    if not graph_path.exists():
        logger.warning(f"Missing graph for p={p}, skipping")
        return None

    g = np.load(graph_path)
    return {
        "p": p,
        "edges": g["edges"].astype(np.int64),
        "num_nodes": int(g["num_nodes"]),
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


def compute_target(
    hecke: dict, target_type: str, p: int
) -> float | np.ndarray | int | None:
    """Compute the target value from Hecke eigenvalue data.

    Returns None if the target cannot be computed for this prime.
    """
    eigenvalues = hecke["eigenvalues"]  # (num_forms, 100)
    num_forms = hecke["num_forms"]
    dim_cusp = hecke["dim_cuspforms"]

    if target_type == "dim_cuspforms":
        return dim_cusp

    if target_type == "mean_a_p":
        if num_forms == 0:
            return None
        # eigenvalues[i, j] = a_{j+1} for the i-th form
        # Use eigenvalues at prime indices: a_2, a_3, a_5, a_7, ...
        # For primes p_i <= sqrt(N) where N ~ p^3 for SL(2,F_p)
        threshold = np.sqrt(p**3) if p > 1 else 10
        prime_indices = [q - 1 for q in SMALL_PRIMES if q <= threshold]
        if not prime_indices:
            prime_indices = [1, 2, 4]  # fallback: indices for a_2, a_3, a_5

        # Take first form's eigenvalues at prime positions
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
        return float(
            eigenvalues[0, 1]
        )  # a_2 is at index 1 (eigenvalues[i,j] = a_{j+1})

    if target_type == "first_form_vector":
        if num_forms == 0:
            return None
        return eigenvalues[0, 1:11].astype(np.float32)  # a_2..a_11

    if target_type == "deligne_ratio":
        if num_forms == 0:
            return None
        form_eigs = eigenvalues[0, :]
        # Check first 20 eigenvalues at prime indices
        # eigenvalues[i, j] = a_{j+1}, so a_q is at index q-1
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
# Node feature computation (identical to spectral gap script)
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
# Chebyshev precomputation (identical to spectral gap script)
# ---------------------------------------------------------------------------


def compute_lambda_max(edges: np.ndarray, num_nodes: int) -> float:
    """Compute largest eigenvalue of the normalized Laplacian."""
    if num_nodes > 5000:
        return 2.0

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
# Graph-level statistics (identical to spectral gap script)
# ---------------------------------------------------------------------------


def compute_graph_statistics(graph: dict) -> np.ndarray:
    """Compute graph-level scalar features."""
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


# ---------------------------------------------------------------------------
# Dataset preparation with caching (same cache as spectral gap script)
# ---------------------------------------------------------------------------


def prepare_dataset(
    graphs: list[dict],
    target_type: str,
    K: int,
    hecke_dir: Path,
    force_recompute: bool = False,
) -> list[dict]:
    """Prepare dataset with precomputed Chebyshev features and Hecke targets."""
    CHEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dataset = []
    t0 = time.time()

    skipped_no_hecke = 0
    skipped_no_target = 0

    for graph in graphs:
        p = graph["p"]

        # Load Hecke data
        hecke = load_hecke_data(p, hecke_dir)
        if hecke is None:
            skipped_no_hecke += 1
            logger.debug(f"  p={p}: no Hecke data, skipping")
            continue

        # Compute target
        target = compute_target(hecke, target_type, p)
        if target is None:
            skipped_no_target += 1
            logger.debug(f"  p={p}: cannot compute target '{target_type}', skipping")
            continue

        # Load or compute Chebyshev features (shared cache with spectral gap script)
        cache_path = CHEB_CACHE_DIR / f"sl2fp_p{p}_K{K}.npz"

        if cache_path.exists() and not force_recompute:
            cached = np.load(cache_path)
            cheb_features = cached["cheb_features"]
            graph_stats = cached["graph_stats"]
            logger.debug(f"  p={p}: loaded cached features {cheb_features.shape}")
        else:
            logger.info(
                f"  p={p}: computing features (N={graph['num_nodes']}, "
                f"E={graph['edges'].shape[1]})..."
            )
            node_feats = compute_node_features(
                graph["edges"], graph["num_nodes"], seed=p
            )
            lam_max = compute_lambda_max(graph["edges"], graph["num_nodes"])
            logger.debug(f"    lambda_max={lam_max:.4f}")

            t1 = time.time()
            cheb_features = precompute_cheb_features(
                graph["edges"], graph["num_nodes"], node_feats, K, lam_max
            )
            t2 = time.time()
            logger.debug(f"    Cheb features: {cheb_features.shape} in {t2 - t1:.2f}s")

            graph_stats = compute_graph_statistics(graph)

            np.savez_compressed(
                cache_path, cheb_features=cheb_features, graph_stats=graph_stats
            )

        dataset.append(
            {
                "p": p,
                "num_nodes": graph["num_nodes"],
                "target": target,
                "dim_cuspforms": hecke["dim_cuspforms"],
                "cheb_features": cheb_features,
                "graph_stats": graph_stats,
            }
        )

    elapsed = time.time() - t0
    logger.info(
        f"Prepared {len(dataset)} graphs in {elapsed:.1f}s "
        f"(skipped {skipped_no_hecke} no Hecke, {skipped_no_target} no target)"
    )
    return dataset


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class FullGraphChebNet(nn.Module):
    """MLP over precomputed Chebyshev features with dual pooling.

    Uses LayerNorm instead of BatchNorm to handle batch_size=1.
    Input = [mean_pool, max_pool, graph_stats].
    Supports variable output dimensions for scalar/vector targets.
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

    # Per-class F1
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


def check_deligne_bound(preds: np.ndarray, target_type: str) -> dict:
    """Check if predicted eigenvalues satisfy the Deligne bound |a_p| <= 2*sqrt(p)."""
    if target_type != "first_form_vector":
        return {"applicable": False}

    # For vector predictions, each position corresponds to a_n
    # Check against 2*sqrt(n) (not prime-specific, but the Ramanujan-Petersson bound)
    violations = []
    n_values = np.arange(1, 11)  # a_1 through a_10
    for i, n in enumerate(n_values):
        bound = 2.0 * np.sqrt(n)
        violations_at_n = np.sum(np.abs(preds[:, i]) > bound)
        if violations_at_n > 0:
            violations.append(
                {
                    "n": n,
                    "bound": bound,
                    "max_abs_pred": float(np.max(np.abs(preds[:, i]))),
                    "violations": int(violations_at_n),
                }
            )

    return {
        "applicable": True,
        "total_violations": sum(v["violations"] for v in violations),
        "violation_details": violations,
    }


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
    """Train on train_graphs, evaluate on test_graphs."""
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

        predictions[g["p"]] = {
            "predicted": pred_np,
            "actual": actual_np,
            "error": pred_np - actual_np,
            "abs_error": np.abs(pred_np - actual_np),
        }

    return predictions


# ---------------------------------------------------------------------------
# Linear baseline
# ---------------------------------------------------------------------------


def linear_baseline_scalar(graphs: list[dict]) -> dict:
    """Predict scalar target as linear function of log(num_nodes)."""
    log_nodes = np.array([np.log(g["num_nodes"]) for g in graphs])
    targets = np.array([float(g["target"]) for g in graphs])

    X = np.column_stack([log_nodes, np.ones(len(log_nodes))])
    coeffs, _, _, _ = np.linalg.lstsq(X, targets, rcond=None)
    slope, intercept = coeffs

    preds = slope * log_nodes + intercept
    metrics = compute_metrics(preds, targets)

    return {
        "slope": slope,
        "intercept": intercept,
        "metrics": metrics,
        "predictions": {
            g["p"]: {"predicted": p, "actual": float(g["target"])}
            for g, p in zip(graphs, preds)
        },
    }


def linear_baseline_vector(graphs: list[dict], output_dim: int = 10) -> dict:
    """Predict vector target per-component as linear function of log(num_nodes)."""
    log_nodes = np.array([np.log(g["num_nodes"]) for g in graphs])
    targets = np.array([g["target"] for g in graphs])  # (N, output_dim)

    per_pos_metrics = {}
    per_pos_preds = {}
    for d in range(output_dim):
        y = targets[:, d]
        X = np.column_stack([log_nodes, np.ones(len(log_nodes))])
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        pred_d = X @ coeffs
        per_pos_metrics[d] = compute_metrics(pred_d, y)
        per_pos_preds[d] = pred_d

    all_preds = np.column_stack([per_pos_preds[d] for d in range(output_dim)])
    total_mae = float(np.mean(np.abs(all_preds - targets)))
    total_rmse = float(np.sqrt(np.mean((all_preds - targets) ** 2)))

    return {
        "per_position_metrics": per_pos_metrics,
        "total_mae": total_mae,
        "total_rmse": total_rmse,
        "predictions": {
            g["p"]: {"predicted": all_preds[i], "actual": targets[i]}
            for i, g in enumerate(graphs)
        },
    }


def linear_baseline_classification(graphs: list[dict]) -> dict:
    """Baseline: always predict the majority class."""
    targets = np.array([int(g["target"]) for g in graphs])
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
        "predictions": {
            g["p"]: {"predicted": majority_class, "actual": int(g["target"])}
            for g in graphs
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Full-graph ChebConv for Hecke eigenvalue prediction on Cayley graphs"
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
        help="Run leave-one-out cross-validation",
    )
    parser.add_argument(
        "--force-recompute",
        action="store_true",
        help="Force recomputation of cached Chebyshev features",
    )
    parser.add_argument(
        "--hecke-dir",
        type=str,
        default="/workspace/data/hecke/",
        help="Directory containing Hecke eigenvalue data",
    )
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    hecke_dir = Path(args.hecke_dir)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")
    logger.info(f"Target: {args.target}")

    # Determine output dimensions and loss
    is_classification = args.target == "dim_cuspforms"
    is_vector = args.target == "first_form_vector"

    if is_classification:
        output_dim = 0  # will be set after loading data
        logger.info("Mode: classification (CrossEntropyLoss)")
    elif is_vector:
        output_dim = 10
        logger.info(f"Mode: vector regression (output_dim={output_dim})")
    else:
        output_dim = 1
        logger.info("Mode: scalar regression (MSELoss)")

    # --- Load all graphs ---
    graphs = []
    for p in PRIMES:
        g = load_full_graph(p)
        if g is not None:
            graphs.append(g)
    logger.info(f"Loaded {len(graphs)} full Cayley graphs")

    # --- Prepare dataset with Hecke targets ---
    logger.info("=" * 70)
    logger.info(f"Preparing dataset (K={args.K}, RPE_DIM={RPE_DIM})...")
    dataset = prepare_dataset(
        graphs, args.target, args.K, hecke_dir, force_recompute=args.force_recompute
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
        f"Cheb feature dim: {cheb_feature_dim}, Graph stats dim: {graph_stats_dim}, "
        f"Output dim: {output_dim}, Dataset size: {len(dataset)}"
    )

    # Verify consistent dimensions
    for g in dataset:
        assert g["cheb_features"].shape[1] == cheb_feature_dim, (
            f"Inconsistent cheb dim for p={g['p']}: "
            f"{g['cheb_features'].shape[1]} vs {cheb_feature_dim}"
        )

    # --- Linear baseline ---
    logger.info("=" * 70)
    if is_classification:
        logger.info("LINEAR BASELINE: majority class prediction")
        baseline = linear_baseline_classification(dataset)
        m = baseline["metrics"]
        logger.info(f"  Majority class: {baseline['majority_class']}")
        logger.info(f"  Accuracy={m['accuracy']:.4f}  Macro-F1={m['macro_f1']:.4f}")
    elif is_vector:
        logger.info("LINEAR BASELINE: target ~ a * log(num_nodes) + b (per position)")
        baseline = linear_baseline_vector(dataset, output_dim=output_dim)
        logger.info(
            f"  Total MAE={baseline['total_mae']:.6f}  Total RMSE={baseline['total_rmse']:.6f}"
        )
        for d in range(min(output_dim, 10)):
            pm = baseline["per_position_metrics"][d]
            logger.info(
                f"  a_{d + 1}: MAE={pm['mae']:.6f}  RMSE={pm['rmse']:.6f}  R²={pm['r2']:.4f}"
            )
    else:
        logger.info("LINEAR BASELINE: target ~ a * log(num_nodes) + b")
        baseline = linear_baseline_scalar(dataset)
        logger.info(
            f"  slope={baseline['slope']:.6f}, intercept={baseline['intercept']:.6f}"
        )
        m = baseline["metrics"]
        logger.info(f"  MAE={m['mae']:.6f}  RMSE={m['rmse']:.6f}  R²={m['r2']:.4f}")
        logger.info("  Per-graph predictions:")
        for p in sorted(baseline["predictions"].keys()):
            pred = baseline["predictions"][p]
            logger.info(
                f"    p={p:3d}: predicted={pred['predicted']:.6f}  "
                f"actual={pred['actual']:.6f}  "
                f"error={pred['predicted'] - pred['actual']:+.6f}"
            )

    # --- Loss function ---
    if is_classification:
        loss_fn = nn.CrossEntropyLoss()
    else:
        loss_fn = nn.MSELoss()

    # --- Standard train/test split ---
    train_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    test_primes = [41, 43, 47, 53, 59, 61]

    train_data = [g for g in dataset if g["p"] in train_primes]
    test_data = [g for g in dataset if g["p"] in test_primes]

    if len(train_data) == 0 or len(test_data) == 0:
        logger.warning(
            f"Standard split has train={len(train_data)}, test={len(test_data)}. "
            f"Skipping standard split evaluation."
        )
    else:
        logger.info("\n" + "=" * 70)
        logger.info(
            f"STANDARD SPLIT: train p<=37 ({len(train_data)} graphs), "
            f"test p>=41 ({len(test_data)} graphs)"
        )
        logger.info("-" * 70)

        t0 = time.time()
        predictions = train_and_evaluate_fold(
            train_graphs=train_data,
            test_graphs=test_data,
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
        elapsed = time.time() - t0

        # Collect predictions and actuals
        split_preds_list = []
        split_actuals_list = []

        for g in test_data:
            p = g["p"]
            pred = predictions[p]
            actual = g["target"]
            if isinstance(actual, np.ndarray):
                split_preds_list.append(pred["predicted"])
                split_actuals_list.append(actual)
                logger.info(
                    f"  p={p:3d}: predicted={np.array2string(pred['predicted'], precision=4, separator=', ')}"
                )
                logger.info(
                    f"          actual  ={np.array2string(actual, precision=4, separator=', ')}"
                )
            else:
                split_preds_list.append(pred["predicted"])
                split_actuals_list.append(actual)
                logger.info(
                    f"  p={p:3d}: predicted={pred['predicted'][0] if isinstance(pred['predicted'], np.ndarray) else pred['predicted']:.6f}  "
                    f"actual={actual:.6f}  "
                    f"error={(pred['predicted'][0] if isinstance(pred['predicted'], np.ndarray) else pred['predicted']) - actual:+.6f}"
                )

        # Compute metrics
        if is_classification:
            all_preds_np = np.array(split_preds_list)
            all_actuals_np = np.array(split_actuals_list, dtype=int)
            split_metrics = compute_classification_metrics(
                all_preds_np, all_actuals_np, num_classes
            )

            # Baseline on same split
            bl_train = [g for g in dataset if g["p"] in train_primes]
            bl_test = [g for g in dataset if g["p"] in test_primes]
            bl = linear_baseline_classification(bl_test)
            bl_m = bl["metrics"]
        elif is_vector:
            all_preds_np = np.array(split_preds_list)
            all_actuals_np = np.array(split_actuals_list)
            total_mae = float(np.mean(np.abs(all_preds_np - all_actuals_np)))
            total_rmse = float(np.sqrt(np.mean((all_preds_np - all_actuals_np) ** 2)))
            per_pos_mae = [
                float(np.mean(np.abs(all_preds_np[:, d] - all_actuals_np[:, d])))
                for d in range(output_dim)
            ]
            split_metrics = {
                "total_mae": total_mae,
                "total_rmse": total_rmse,
                "per_position_mae": per_pos_mae,
            }

            bl = linear_baseline_vector(bl_test, output_dim=output_dim)
            bl_m = {"total_mae": bl["total_mae"], "total_rmse": bl["total_rmse"]}
        else:
            all_preds_np = np.array(
                [p if isinstance(p, (int, float)) else p[0] for p in split_preds_list]
            )
            all_actuals_np = np.array(split_actuals_list, dtype=float)
            split_metrics = compute_metrics(all_preds_np, all_actuals_np)

            bl_train = [g for g in dataset if g["p"] in train_primes]
            bl_test = [g for g in dataset if g["p"] in test_primes]
            bl_fit = linear_baseline_scalar(bl_train)
            bl_preds = (
                bl_fit["slope"] * np.log([g["num_nodes"] for g in bl_test])
                + bl_fit["intercept"]
            )
            bl_actuals = np.array([float(g["target"]) for g in bl_test])
            bl_m = compute_metrics(bl_preds, bl_actuals)

        # Report results
        logger.info("=" * 70)
        logger.info("STANDARD SPLIT RESULTS")
        logger.info("=" * 70)
        if is_classification:
            logger.info(
                f"  Model:  Accuracy={split_metrics['accuracy']:.4f}  Macro-F1={split_metrics['macro_f1']:.4f}"
            )
            logger.info(
                f"  Baseline: Accuracy={bl_m['accuracy']:.4f}  Macro-F1={bl_m['macro_f1']:.4f}"
            )
        elif is_vector:
            logger.info(
                f"  Model:  Total MAE={split_metrics['total_mae']:.6f}  Total RMSE={split_metrics['total_rmse']:.6f}"
            )
            for d in range(min(output_dim, 10)):
                logger.info(
                    f"    a_{d + 1}: MAE={split_metrics['per_position_mae'][d]:.6f}"
                )
            logger.info(
                f"  Baseline: Total MAE={bl_m['total_mae']:.6f}  Total RMSE={bl_m['total_rmse']:.6f}"
            )
        else:
            logger.info(
                f"  Model:  MAE={split_metrics['mae']:.6f}  "
                f"RMSE={split_metrics['rmse']:.6f}  R²={split_metrics['r2']:.4f}"
            )
            logger.info(
                f"  Baseline: MAE={bl_m['mae']:.6f}  "
                f"RMSE={bl_m['rmse']:.6f}  R²={bl_m['r2']:.4f}"
            )
        logger.info(f"  Training time: {elapsed:.1f}s")

    # --- Deligne bound check (for vector targets) ---
    if is_vector and len(test_data) > 0:
        logger.info("\n" + "=" * 70)
        logger.info("DELIGNE BOUND CHECK")
        logger.info("-" * 70)
        # Collect all predictions for the bound check
        all_pred_vecs = np.array(split_preds_list)
        bound_check = check_deligne_bound(all_pred_vecs, args.target)
        if bound_check["applicable"]:
            if bound_check["total_violations"] == 0:
                logger.success("  All predictions satisfy |a_n| <= 2*sqrt(n)")
            else:
                logger.warning(f"  {bound_check['total_violations']} violations found:")
                for v in bound_check["violation_details"]:
                    logger.warning(
                        f"    n={v['n']}: bound=2*sqrt({v['n']})={v['bound']:.4f}, "
                        f"max|pred|={v['max_abs_pred']:.4f}, "
                        f"violations={v['violations']}"
                    )
        # Also check actual targets
        all_actual_vecs = np.array(split_actuals_list)
        actual_violations = 0
        for i, n in enumerate(range(1, 11)):
            bound = 2.0 * np.sqrt(n)
            actual_violations += np.sum(np.abs(all_actual_vecs[:, i]) > bound)
        if actual_violations > 0:
            logger.warning(
                f"  Note: {actual_violations} actual target values also violate the bound (expected for non-prime indices)"
            )
        else:
            logger.info("  All actual targets satisfy |a_n| <= 2*sqrt(n)")

    # --- Leave-one-out cross-validation ---
    if args.leave_one_out:
        logger.info("\n" + "=" * 70)
        logger.info(
            f"LEAVE-ONE-OUT CROSS-VALIDATION "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs}, target={args.target})"
        )
        logger.info("-" * 70)

        all_preds = []
        all_actuals = []
        t_loo_start = time.time()

        for i, test_graph in enumerate(dataset):
            p = test_graph["p"]
            train_graphs_loo = [g for j, g in enumerate(dataset) if j != i]

            logger.info(
                f"\nFold {i + 1}/{len(dataset)}: testing on p={p} "
                f"(N={test_graph['num_nodes']}), "
                f"training on {len(train_graphs_loo)} graphs"
            )

            t0 = time.time()
            predictions = train_and_evaluate_fold(
                train_graphs=train_graphs_loo,
                test_graphs=[test_graph],
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
            elapsed = time.time() - t0

            pred = predictions[p]
            actual = test_graph["target"]
            if isinstance(actual, np.ndarray):
                all_preds.append(pred["predicted"])
                all_actuals.append(actual)
                logger.info(
                    f"  p={p:3d}: predicted={np.array2string(pred['predicted'], precision=4, separator=', ')} ({elapsed:.1f}s)"
                )
            else:
                pred_val = (
                    pred["predicted"][0]
                    if isinstance(pred["predicted"], np.ndarray)
                    else pred["predicted"]
                )
                all_preds.append(pred_val)
                all_actuals.append(actual)
                logger.info(
                    f"  p={p:3d}: predicted={pred_val:.6f}  "
                    f"actual={actual:.6f}  error={pred_val - actual:+.6f}  "
                    f"abs_error={abs(pred_val - actual):.6f}  ({elapsed:.1f}s)"
                )

        loo_elapsed = time.time() - t_loo_start

        logger.info("\n" + "=" * 70)
        logger.info("LEAVE-ONE-OUT CROSS-VALIDATION RESULTS")
        logger.info("=" * 70)

        if is_classification:
            loo_preds_np = np.array(all_preds)
            loo_actuals_np = np.array(all_actuals, dtype=int)
            loo_metrics = compute_classification_metrics(
                loo_preds_np, loo_actuals_np, num_classes
            )
            logger.info(
                f"  Model:  Accuracy={loo_metrics['accuracy']:.4f}  Macro-F1={loo_metrics['macro_f1']:.4f}"
            )
            if isinstance(m, dict) and "accuracy" in m:
                logger.info(
                    f"  Baseline: Accuracy={m['accuracy']:.4f}  Macro-F1={m['macro_f1']:.4f}"
                )
        elif is_vector:
            loo_preds_np = np.array(all_preds)
            loo_actuals_np = np.array(all_actuals)
            loo_total_mae = float(np.mean(np.abs(loo_preds_np - loo_actuals_np)))
            loo_total_rmse = float(
                np.sqrt(np.mean((loo_preds_np - loo_actuals_np) ** 2))
            )
            loo_per_pos_mae = [
                float(np.mean(np.abs(loo_preds_np[:, d] - loo_actuals_np[:, d])))
                for d in range(output_dim)
            ]
            logger.info(
                f"  Model:  Total MAE={loo_total_mae:.6f}  Total RMSE={loo_total_rmse:.6f}"
            )
            for d in range(min(output_dim, 10)):
                logger.info(f"    a_{d + 1}: MAE={loo_per_pos_mae[d]:.6f}")
        else:
            loo_preds_arr = np.array(all_preds, dtype=float)
            loo_actuals_arr = np.array(all_actuals, dtype=float)
            loo_metrics = compute_metrics(loo_preds_arr, loo_actuals_arr)
            logger.info(
                f"  Model:  MAE={loo_metrics['mae']:.6f}  "
                f"RMSE={loo_metrics['rmse']:.6f}  R²={loo_metrics['r2']:.4f}"
            )
            if isinstance(m, dict) and "mae" in m:
                logger.info(
                    f"  Baseline (full): MAE={m['mae']:.6f}  "
                    f"RMSE={m['rmse']:.6f}  R²={m['r2']:.4f}"
                )

        logger.info(f"  Total LOO time: {loo_elapsed:.1f}s")

    # --- Save final model (trained on all data) ---
    logger.info("\n" + "=" * 70)
    logger.info("Training final model on all data...")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    final_model = FullGraphChebNet(
        cheb_feature_dim=cheb_feature_dim,
        graph_stats_dim=graph_stats_dim,
        output_dim=output_dim,
        hidden_dim=args.hidden,
        dropout=args.dropout,
    ).to(device)

    final_optimizer = torch.optim.Adam(
        final_model.parameters(), lr=args.lr, weight_decay=1e-4
    )
    final_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        final_optimizer, T_max=args.epochs
    )

    for epoch in range(1, args.epochs + 1):
        indices = np.random.permutation(len(dataset))
        for idx in indices:
            train_single_graph(
                final_model, dataset[idx], final_optimizer, device, loss_fn
            )
        final_scheduler.step()

    model_path = MODEL_DIR / f"hecke_{args.target}.pt"
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "args": vars(args),
            "cheb_feature_dim": cheb_feature_dim,
            "graph_stats_dim": graph_stats_dim,
            "output_dim": output_dim,
            "num_classes": num_classes if is_classification else None,
            "dataset_primes": [g["p"] for g in dataset],
        },
        model_path,
    )
    logger.info(f"Saved model to {model_path}")


if __name__ == "__main__":
    main()
