"""
Full-graph ChebConv for spectral gap prediction on SL(2,F_p) Cayley graphs.

Precomputes Chebyshev polynomial features from the normalized Laplacian for
each full Cayley graph, then trains an MLP on these precomputed features.
No message passing at runtime — the spectral information is baked into the features.

Key insight: Cayley graphs are vertex-transitive (all nodes locally identical),
so uniform structural features (degree, clustering) produce uniform Chebyshev
features after pooling. To extract spectral information, we add random positional
encodings that break symmetry — the Laplacian propagation then encodes graph
structure into these random features, making them informative after pooling.

Evaluation: Leave-one-out cross-validation over 18 primes (primary metric),
plus a held-out split (train p<=37, test p>=41) and a linear baseline.

Usage:
    python train_fullgraph_cheb.py --K 3 --hidden 64 --epochs 300 --lr 1e-3
    python train_fullgraph_cheb.py --K 5 --hidden 128 --leave-one-out --epochs 500
    python train_fullgraph_cheb.py --K 3 --baseline-only
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
EIGEN_DIR = DATA_DIR / "eigenvalues"
CHEB_CACHE_DIR = DATA_DIR / "cheb_precomputed"

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]

# Number of random positional encoding dimensions
RPE_DIM = 8


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------


def load_full_graph(p: int) -> dict | None:
    """Load a full Cayley graph and its eigenvalue stats."""
    graph_path = GRAPH_DIR / f"sl2fp_p{p}.npz"
    stats_path = EIGEN_DIR / f"sl2fp_p{p}_stats.npz"

    if not graph_path.exists() or not stats_path.exists():
        logger.warning(f"Missing data for p={p}, skipping")
        return None

    g = np.load(graph_path)
    s = np.load(stats_path)

    return {
        "p": p,
        "edges": g["edges"].astype(np.int64),  # (2, E)
        "num_nodes": int(g["num_nodes"]),
        "spectral_gap": float(s["spectral_gap"]),
        "ramanujan_ratio": float(s["ramanujan_ratio"]),
        "max_abs_eigenvalue": float(s["max_abs_eigenvalue"]),
        "ramanujan_bound": float(s["ramanujan_bound"]),
        "is_ramanujan": bool(s["is_ramanujan"]),
        "num_eigenvalues": int(s["num_eigenvalues"]),
    }


def load_all_graphs() -> list[dict]:
    """Load all 18 graphs with eigenvalue data."""
    graphs = []
    for p in PRIMES:
        g = load_full_graph(p)
        if g is not None:
            graphs.append(g)
    logger.info(f"Loaded {len(graphs)} full Cayley graphs")
    return graphs


# ---------------------------------------------------------------------------
# Node feature computation
# ---------------------------------------------------------------------------


def compute_node_features(
    edges: np.ndarray, num_nodes: int, seed: int = 42
) -> np.ndarray:
    """Compute per-node features: degree/4, clustering, triangle_norm, RPE.

    For vertex-transitive graphs, degree/clustering/triangles are uniform.
    Random positional encoding (RPE) breaks symmetry so Chebyshev propagation
    produces meaningful per-node variation.

    Returns (N, 3 + RPE_DIM) array.
    """
    # Build sparse adjacency
    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)
    adj.setdiag(0.0)
    adj.eliminate_zeros()

    deg = np.array(adj.sum(axis=1)).flatten().astype(np.float64)
    deg_norm = deg / 4.0  # 4-regular

    # Clustering + triangles
    if num_nodes <= 10000:
        A_cubed = (adj @ adj @ adj).toarray()
        triangles = np.diag(A_cubed).astype(np.float64) / 6.0
    elif num_nodes <= 100000:
        triangles = _estimate_triangles_sampled(adj, num_nodes, n_samples=3000)
    else:
        # Very large: set triangles to 0, clustering to 0
        triangles = np.zeros(num_nodes, dtype=np.float64)

    denom = deg * (deg - 1)
    denom[denom == 0] = 1.0
    clustering = 2.0 * triangles / denom
    tri_max = triangles.max() if triangles.max() > 0 else 1.0
    tri_norm = triangles / tri_max

    # Random positional encoding (deterministic per graph via seed)
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
# Chebyshev precomputation
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

    # T_0 @ x = x
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
# Graph-level statistics
# ---------------------------------------------------------------------------


def compute_graph_statistics(graph: dict) -> np.ndarray:
    """Compute graph-level scalar features."""
    num_nodes = graph["num_nodes"]
    num_edges = graph["edges"].shape[1]

    density = (2 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0.0

    # Approximate diameter via BFS (sample a few starting nodes)
    diameter_est = _estimate_diameter(graph["edges"], num_nodes, n_samples=3)

    log_nodes = np.log(num_nodes)
    log_edges = np.log(num_edges)

    stats = np.array(
        [
            log_nodes,
            log_edges,
            density,
            float(diameter_est),
        ],
        dtype=np.float32,
    )

    return stats


def _estimate_diameter(edges: np.ndarray, num_nodes: int, n_samples: int = 3) -> float:
    """Estimate graph diameter via BFS from random nodes."""
    if num_nodes > 100000:
        return 0.0  # skip for very large graphs

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
# Dataset preparation with caching
# ---------------------------------------------------------------------------


def prepare_dataset(
    graphs: list[dict], K: int, force_recompute: bool = False
) -> list[dict]:
    """Prepare dataset with precomputed Chebyshev features."""
    CHEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dataset = []
    t0 = time.time()

    for graph in graphs:
        p = graph["p"]
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
            # Use p as seed for reproducible RPE
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
                "spectral_gap": graph["spectral_gap"],
                "cheb_features": cheb_features,
                "graph_stats": graph_stats,
            }
        )

    elapsed = time.time() - t0
    logger.info(f"Prepared {len(dataset)} graphs in {elapsed:.1f}s")
    return dataset


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class FullGraphChebNet(nn.Module):
    """MLP over precomputed Chebyshev features with dual pooling.

    Uses LayerNorm instead of BatchNorm to handle batch_size=1 (we train
    on individual graphs). Input = [mean_pool, max_pool, graph_stats].
    """

    def __init__(
        self,
        cheb_feature_dim: int,
        graph_stats_dim: int,
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
            nn.Linear(hidden_dim // 2, 1),
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
        return self.mlp(x).squeeze(-1)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(preds: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    """Compute MAE, RMSE, R²."""
    mae = float(np.mean(np.abs(preds - targets)))
    rmse = float(np.sqrt(np.mean((preds - targets) ** 2)))
    ss_res = float(np.sum((targets - preds) ** 2))
    ss_tot = float(np.sum((targets - targets.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return {"mae": mae, "rmse": rmse, "r2": r2}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_single_graph(
    model: FullGraphChebNet,
    graph: dict,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    """Train on a single graph (one sample in the batch)."""
    model.train()
    cheb = torch.from_numpy(graph["cheb_features"]).to(device)
    stats = torch.from_numpy(graph["graph_stats"]).unsqueeze(0).to(device)
    target = torch.tensor([graph["spectral_gap"]], dtype=torch.float32).to(device)
    batch = torch.zeros(graph["num_nodes"], dtype=torch.long, device=device)

    optimizer.zero_grad()
    pred = model(cheb, stats, batch)
    loss = F.mse_loss(pred, target)
    loss.backward()
    optimizer.step()
    return loss.item()


@torch.no_grad()
def predict_single(
    model: FullGraphChebNet,
    graph: dict,
    device: torch.device,
) -> float:
    """Predict spectral gap for a single graph."""
    model.eval()
    cheb = torch.from_numpy(graph["cheb_features"]).to(device)
    stats = torch.from_numpy(graph["graph_stats"]).unsqueeze(0).to(device)
    batch = torch.zeros(graph["num_nodes"], dtype=torch.long, device=device)
    return model(cheb, stats, batch).item()


def train_and_evaluate_fold(
    train_graphs: list[dict],
    test_graphs: list[dict],
    cheb_feature_dim: int,
    graph_stats_dim: int,
    hidden_dim: int,
    epochs: int,
    lr: float,
    seed: int,
    device: torch.device,
) -> dict:
    """Train on train_graphs, evaluate on test_graphs."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    model = FullGraphChebNet(
        cheb_feature_dim=cheb_feature_dim,
        graph_stats_dim=graph_stats_dim,
        hidden_dim=hidden_dim,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    for epoch in range(1, epochs + 1):
        indices = np.random.permutation(len(train_graphs))
        for idx in indices:
            train_single_graph(model, train_graphs[idx], optimizer, device)
        scheduler.step()

    predictions = {}
    for g in test_graphs:
        pred = predict_single(model, g, device)
        predictions[g["p"]] = {
            "predicted": pred,
            "actual": g["spectral_gap"],
            "error": pred - g["spectral_gap"],
            "abs_error": abs(pred - g["spectral_gap"]),
        }

    return predictions


# ---------------------------------------------------------------------------
# Linear baseline
# ---------------------------------------------------------------------------


def linear_baseline(graphs: list[dict]) -> dict:
    """Predict spectral_gap as linear function of log(num_nodes)."""
    log_nodes = np.array([np.log(g["num_nodes"]) for g in graphs])
    spectral_gaps = np.array([g["spectral_gap"] for g in graphs])

    X = np.column_stack([log_nodes, np.ones(len(log_nodes))])
    coeffs, _, _, _ = np.linalg.lstsq(X, spectral_gaps, rcond=None)
    slope, intercept = coeffs

    preds = slope * log_nodes + intercept
    metrics = compute_metrics(preds, spectral_gaps)

    return {
        "slope": slope,
        "intercept": intercept,
        "metrics": metrics,
        "predictions": {
            g["p"]: {"predicted": p, "actual": a}
            for g, p, a in zip(graphs, preds, spectral_gaps)
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Full-graph ChebConv for spectral gap prediction on Cayley graphs"
    )
    parser.add_argument("--K", type=int, default=3, help="Chebyshev polynomial order")
    parser.add_argument("--hidden", type=int, default=64, help="MLP hidden dim")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--leave-one-out",
        action="store_true",
        help="Run leave-one-out cross-validation (primary evaluation)",
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="Only run the linear baseline comparison",
    )
    parser.add_argument(
        "--force-recompute",
        action="store_true",
        help="Force recomputation of cached Chebyshev features",
    )
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Load all 18 graphs
    graphs = load_all_graphs()
    if len(graphs) < 18:
        logger.warning(f"Only loaded {len(graphs)} graphs, expected 18")

    # --- Linear baseline ---
    logger.info("=" * 70)
    logger.info("LINEAR BASELINE: spectral_gap ~ a * log(num_nodes) + b")
    baseline = linear_baseline(graphs)
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

    if args.baseline_only:
        logger.info("Baseline-only mode, exiting.")
        return

    # --- Prepare features ---
    logger.info("=" * 70)
    logger.info(f"Precomputing Chebyshev features (K={args.K}, RPE_DIM={RPE_DIM})...")
    dataset = prepare_dataset(graphs, args.K, force_recompute=args.force_recompute)

    cheb_feature_dim = dataset[0]["cheb_features"].shape[1]
    graph_stats_dim = dataset[0]["graph_stats"].shape[0]
    logger.info(
        f"Cheb feature dim: {cheb_feature_dim}, Graph stats dim: {graph_stats_dim}"
    )

    # Verify consistent dimensions
    for g in dataset:
        assert g["cheb_features"].shape[1] == cheb_feature_dim, (
            f"Inconsistent cheb dim for p={g['p']}: "
            f"{g['cheb_features'].shape[1]} vs {cheb_feature_dim}"
        )

    # --- Standard train/test split (always runs) ---
    train_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    test_primes = [41, 43, 47, 53, 59, 61]

    train_data = [g for g in dataset if g["p"] in train_primes]
    test_data = [g for g in dataset if g["p"] in test_primes]

    logger.info("\n" + "=" * 70)
    logger.info(
        f"STANDARD SPLIT: train p≤37 ({len(train_data)} graphs), "
        f"test p≥41 ({len(test_data)} graphs)"
    )
    logger.info("-" * 70)

    t0 = time.time()
    predictions = train_and_evaluate_fold(
        train_graphs=train_data,
        test_graphs=test_data,
        cheb_feature_dim=cheb_feature_dim,
        graph_stats_dim=graph_stats_dim,
        hidden_dim=args.hidden,
        epochs=args.epochs,
        lr=args.lr,
        seed=args.seed,
        device=device,
    )
    elapsed = time.time() - t0

    split_preds = []
    split_actuals = []
    for g in test_data:
        p = g["p"]
        pred = predictions[p]
        split_preds.append(pred["predicted"])
        split_actuals.append(pred["actual"])
        logger.info(
            f"  p={p:3d}: predicted={pred['predicted']:.6f}  "
            f"actual={pred['actual']:.6f}  error={pred['error']:+.6f}"
        )

    split_preds = np.array(split_preds)
    split_actuals = np.array(split_actuals)
    split_metrics = compute_metrics(split_preds, split_actuals)

    # Baseline on same split
    baseline_train = [g for g in graphs if g["p"] in train_primes]
    baseline_test = [g for g in graphs if g["p"] in test_primes]
    bl_fit = linear_baseline(baseline_train)
    bl_preds = (
        bl_fit["slope"] * np.log([g["num_nodes"] for g in baseline_test])
        + bl_fit["intercept"]
    )
    bl_actuals = np.array([g["spectral_gap"] for g in baseline_test])
    bl_metrics = compute_metrics(bl_preds, bl_actuals)

    logger.info("=" * 70)
    logger.info("STANDARD SPLIT RESULTS")
    logger.info("=" * 70)
    logger.info(
        f"  Model:  MAE={split_metrics['mae']:.6f}  "
        f"RMSE={split_metrics['rmse']:.6f}  R²={split_metrics['r2']:.4f}"
    )
    logger.info(
        f"  Baseline: MAE={bl_metrics['mae']:.6f}  "
        f"RMSE={bl_metrics['rmse']:.6f}  R²={bl_metrics['r2']:.4f}"
    )
    logger.info(f"  Training time: {elapsed:.1f}s")

    if split_metrics["r2"] > bl_metrics["r2"]:
        logger.success(
            f"  ✓ Model beats baseline on test split! "
            f"ΔR² = {split_metrics['r2'] - bl_metrics['r2']:+.4f}"
        )
    else:
        logger.warning(
            f"  ✗ Model does NOT beat baseline on test split. "
            f"ΔR² = {split_metrics['r2'] - bl_metrics['r2']:+.4f}"
        )

    # --- Leave-one-out cross-validation ---
    if args.leave_one_out:
        logger.info("\n" + "=" * 70)
        logger.info(
            f"LEAVE-ONE-OUT CROSS-VALIDATION "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs})"
        )
        logger.info("-" * 70)

        all_preds = []
        all_actuals = []
        t_loo_start = time.time()

        for i, test_graph in enumerate(dataset):
            p = test_graph["p"]
            train_graphs = [g for j, g in enumerate(dataset) if j != i]

            logger.info(
                f"\nFold {i + 1}/18: testing on p={p} "
                f"(N={test_graph['num_nodes']}), "
                f"training on {len(train_graphs)} graphs"
            )

            t0 = time.time()
            predictions = train_and_evaluate_fold(
                train_graphs=train_graphs,
                test_graphs=[test_graph],
                cheb_feature_dim=cheb_feature_dim,
                graph_stats_dim=graph_stats_dim,
                hidden_dim=args.hidden,
                epochs=args.epochs,
                lr=args.lr,
                seed=args.seed,
                device=device,
            )
            elapsed = time.time() - t0

            pred = predictions[p]
            all_preds.append(pred["predicted"])
            all_actuals.append(pred["actual"])

            logger.info(
                f"  p={p:3d}: predicted={pred['predicted']:.6f}  "
                f"actual={pred['actual']:.6f}  error={pred['error']:+.6f}  "
                f"abs_error={pred['abs_error']:.6f}  ({elapsed:.1f}s)"
            )

        loo_elapsed = time.time() - t_loo_start
        all_preds = np.array(all_preds)
        all_actuals = np.array(all_actuals)
        loo_metrics = compute_metrics(all_preds, all_actuals)

        logger.info("\n" + "=" * 70)
        logger.info("LEAVE-ONE-OUT CROSS-VALIDATION RESULTS")
        logger.info("=" * 70)
        logger.info(
            f"  Model:  MAE={loo_metrics['mae']:.6f}  "
            f"RMSE={loo_metrics['rmse']:.6f}  R²={loo_metrics['r2']:.4f}"
        )
        logger.info(
            f"  Baseline (full): MAE={m['mae']:.6f}  "
            f"RMSE={m['rmse']:.6f}  R²={m['r2']:.4f}"
        )
        logger.info(f"  Total LOO time: {loo_elapsed:.1f}s")

        if loo_metrics["r2"] > m["r2"]:
            logger.success(
                f"  ✓ Model beats baseline! ΔR² = {loo_metrics['r2'] - m['r2']:+.4f}"
            )
        else:
            logger.warning(
                f"  ✗ Model does NOT beat baseline. "
                f"ΔR² = {loo_metrics['r2'] - m['r2']:+.4f}"
            )


if __name__ == "__main__":
    main()
