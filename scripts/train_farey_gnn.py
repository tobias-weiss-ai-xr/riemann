"""
Full-graph ChebConv for spectral gap prediction on Farey graphs.

Precomputes Chebyshev polynomial features from the normalized Laplacian for
each full Farey graph, then trains an MLP on these precomputed features.
No message passing at runtime — the spectral information is baked into the features.

Key differences from Cayley graph version:
- Farey graphs are NOT vertex-transitive → degree varies and is informative
- No RPE needed (nodes already have varying structural signatures)
- Richer node features: degree, degree_norm, clustering, triangles
- Target: log(1/spectral_gap) — transforms power-law decay to linear
- Power-law baseline: log(1/gap) ~ a * log(n) + b  (i.e., gap ~ n^(-exp))

Evaluation: Leave-one-out cross-validation over 23 Farey graphs (n=10..230),
plus linear and power-law baselines.

Usage:
    python train_farey_gnn.py --K 3 --hidden 64 --epochs 300 --lr 1e-3
    python train_farey_gnn.py --K 5 --hidden 128 --leave-one-out --epochs 500
    python train_farey_gnn.py --K 3 --baseline-only
"""

from __future__ import annotations

import argparse
import json
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

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
GRAPH_DIR = DATA_DIR / "farey-graphs"
CHEB_CACHE_DIR = DATA_DIR / "farey-cheb-precomputed"
RESULTS_DIR = SCRIPT_DIR.parent / "results" / "farey"


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------


def load_manifest() -> list[dict]:
    """Load manifest.json with graph metadata."""
    manifest_path = GRAPH_DIR / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)
    return manifest["graphs"]


def load_farey_graph(entry: dict) -> dict | None:
    """Load a Farey graph and its spectral data from npz files.

    The graph npz stores: adj_data, adj_indices, adj_indptr, adj_shape.
    adj_indices has interleaved row/col pairs: first half = rows, second = cols.
    """
    graph_path = GRAPH_DIR / entry["file_graph"]
    spectrum_path = GRAPH_DIR / entry["file_spectrum"]

    if not graph_path.exists() or not spectrum_path.exists():
        logger.warning(f"Missing data for n={entry['level']}, skipping")
        return None

    g = np.load(graph_path)
    s = np.load(spectrum_path)

    # Reconstruct adjacency matrix from interleaved row/col format
    n_entries = len(g["adj_data"])
    rows = g["adj_indices"][:n_entries].astype(np.int64)
    cols = g["adj_indices"][n_entries : 2 * n_entries].astype(np.int64)
    shape = tuple(g["adj_shape"])

    adj = csr_matrix((g["adj_data"], (rows, cols)), shape=shape)
    adj = adj.maximum(adj.T)  # ensure symmetry
    adj.setdiag(0.0)
    adj.eliminate_zeros()

    num_nodes = int(entry["num_vertices"])
    spectral_gap = float(s["spectral_gap"])
    algebraic_connectivity = float(s["algebraic_connectivity"])

    # Build edge_index (deduplicated: row < col for undirected edges)
    adj_coo = adj.tocoo()
    mask = adj_coo.row < adj_coo.col
    edges = np.stack([adj_coo.row[mask], adj_coo.col[mask]], axis=0).astype(np.int64)
    # Also store the full symmetric edge list for Chebyshev computation
    edges_sym = np.stack([adj_coo.row, adj_coo.col], axis=0).astype(np.int64)

    return {
        "n": entry["level"],
        "num_nodes": num_nodes,
        "edges": edges,  # deduplicated (E_unique, 2)
        "edges_sym": edges_sym,  # full symmetric for sparse ops
        "adj": adj,
        "spectral_gap": spectral_gap,
        "algebraic_connectivity": algebraic_connectivity,
        "avg_degree": float(s["avg_degree"]),
    }


def load_all_graphs() -> list[dict]:
    """Load all Farey graphs from manifest."""
    manifest = load_manifest()
    graphs = []
    for entry in manifest:
        g = load_farey_graph(entry)
        if g is not None:
            graphs.append(g)
    graphs.sort(key=lambda g: g["n"])
    logger.info(
        f"Loaded {len(graphs)} Farey graphs (n={graphs[0]['n']}..{graphs[-1]['n']})"
    )
    return graphs


# ---------------------------------------------------------------------------
# Node feature computation
# ---------------------------------------------------------------------------


def compute_node_features(adj: csr_matrix, num_nodes: int) -> np.ndarray:
    """Compute per-node features for non-vertex-transitive Farey graphs.

    Features (5 dims):
    - degree_raw / num_nodes: raw degree normalized by graph size
    - degree / max_degree: relative degree within graph
    - clustering coefficient
    - triangle count (normalized)
    - pagerank (simplified power iteration)

    No RPE needed — Farey graphs have naturally varying node degrees.
    """
    deg = np.array(adj.sum(axis=1)).flatten().astype(np.float64)
    max_deg = float(deg.max()) if deg.max() > 0 else 1.0
    deg_rel = deg / max_deg
    deg_norm = deg / num_nodes

    # Clustering + triangles
    if num_nodes <= 10000:
        A_cubed = (adj @ adj @ adj).toarray()
        triangles = np.diag(A_cubed).astype(np.float64) / 6.0
    elif num_nodes <= 50000:
        triangles = _estimate_triangles_sampled(adj, num_nodes, n_samples=5000)
    else:
        triangles = np.zeros(num_nodes, dtype=np.float64)

    denom = deg * (deg - 1)
    denom[denom == 0] = 1.0
    clustering = 2.0 * triangles / denom
    tri_max = triangles.max() if triangles.max() > 0 else 1.0
    tri_norm = triangles / tri_max

    # PageRank (simplified power iteration, 10 steps)
    pagerank = _compute_pagerank(adj, deg, num_nodes, n_iter=10)

    features = np.column_stack([deg_norm, deg_rel, clustering, tri_norm, pagerank])
    return features.astype(np.float32)


def _estimate_triangles_sampled(
    adj: csr_matrix, num_nodes: int, n_samples: int = 5000
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


def _compute_pagerank(
    adj: csr_matrix,
    deg: np.ndarray,
    num_nodes: int,
    n_iter: int = 10,
    alpha: float = 0.85,
) -> np.ndarray:
    """Simplified PageRank via power iteration."""
    pr = np.ones(num_nodes, dtype=np.float64) / num_nodes
    deg_safe = deg.copy()
    deg_safe[deg_safe == 0] = 1.0
    # Build transition matrix (column-stochastic)
    D_inv = diags(1.0 / deg_safe)
    transition = D_inv @ adj
    transition = csr_matrix(transition)

    for _ in range(n_iter):
        pr_new = alpha * transition.T.dot(pr) + (1 - alpha) / num_nodes
        pr_new /= pr_new.sum()
        pr = pr_new

    return pr


# ---------------------------------------------------------------------------
# Chebyshev precomputation (exact reuse from train_fullgraph_cheb.py)
# ---------------------------------------------------------------------------


def compute_lambda_max(edges_sym: np.ndarray, num_nodes: int) -> float:
    """Compute largest eigenvalue of the normalized Laplacian."""
    if num_nodes > 5000:
        return 2.0

    adj = csr_matrix(
        (np.ones(edges_sym.shape[1], dtype=np.float64), (edges_sym[0], edges_sym[1])),
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
    edges_sym: np.ndarray,
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
        (np.ones(edges_sym.shape[1], dtype=np.float64), (edges_sym[0], edges_sym[1])),
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
    deg = np.array(graph["adj"].sum(axis=1)).flatten().astype(np.float64)

    density = (2 * num_edges) / (num_nodes * (num_nodes - 1)) if num_nodes > 1 else 0.0

    # Approximate diameter via BFS (sample a few starting nodes)
    diameter_est = _estimate_diameter(graph["edges_sym"], num_nodes, n_samples=3)

    log_nodes = np.log(num_nodes)
    log_edges = np.log(2 * num_edges)  # undirected edges

    stats = np.array(
        [
            log_nodes,
            log_edges,
            density,
            float(diameter_est),
            float(np.std(deg)),  # degree_std
            float(deg.max()),  # max_degree
            float(np.mean(deg)),  # avg_degree
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
        n = graph["n"]
        cache_path = CHEB_CACHE_DIR / f"farey_n{n:04d}_K{K}.npz"

        if cache_path.exists() and not force_recompute:
            cached = np.load(cache_path)
            cheb_features = cached["cheb_features"]
            graph_stats = cached["graph_stats"]
            logger.debug(f"  n={n}: loaded cached features {cheb_features.shape}")
        else:
            logger.info(
                f"  n={n}: computing features (N={graph['num_nodes']}, "
                f"E={graph['edges'].shape[1]})..."
            )

            node_feats = compute_node_features(graph["adj"], graph["num_nodes"])

            lam_max = compute_lambda_max(graph["edges_sym"], graph["num_nodes"])
            logger.debug(f"    lambda_max={lam_max:.4f}")

            t1 = time.time()
            cheb_features = precompute_cheb_features(
                graph["edges_sym"], graph["num_nodes"], node_feats, K, lam_max
            )
            t2 = time.time()
            logger.debug(f"    Cheb features: {cheb_features.shape} in {t2 - t1:.2f}s")

            graph_stats = compute_graph_statistics(graph)

            np.savez_compressed(
                cache_path, cheb_features=cheb_features, graph_stats=graph_stats
            )

        # Target: log(1/spectral_gap) — transforms power-law decay to linear
        target = np.log(1.0 / graph["spectral_gap"])

        dataset.append(
            {
                "n": n,
                "num_nodes": graph["num_nodes"],
                "spectral_gap": graph["spectral_gap"],
                "target": target,
                "cheb_features": cheb_features,
                "graph_stats": graph_stats,
            }
        )

    elapsed = time.time() - t0
    logger.info(f"Prepared {len(dataset)} graphs in {elapsed:.1f}s")
    return dataset


# ---------------------------------------------------------------------------
# Model (same architecture as train_fullgraph_cheb.py)
# ---------------------------------------------------------------------------


class FareyChebNet(nn.Module):
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
    """Compute MAE, RMSE, R², and relative error."""
    mae = float(np.mean(np.abs(preds - targets)))
    rmse = float(np.sqrt(np.mean((preds - targets) ** 2)))
    ss_res = float(np.sum((targets - preds) ** 2))
    ss_tot = float(np.sum((targets - targets.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    # Relative error (median to avoid outlier domination)
    rel_errors = np.abs(preds - targets) / (np.abs(targets) + 1e-12)
    med_rel = float(np.median(rel_errors))
    return {"mae": mae, "rmse": rmse, "r2": r2, "median_rel_error": med_rel}


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_single_graph(
    model: FareyChebNet,
    graph: dict,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    """Train on a single graph (one sample in the batch)."""
    model.train()
    cheb = torch.from_numpy(graph["cheb_features"]).to(device)
    stats = torch.from_numpy(graph["graph_stats"]).unsqueeze(0).to(device)
    target = torch.tensor([graph["target"]], dtype=torch.float32).to(device)
    batch = torch.zeros(graph["num_nodes"], dtype=torch.long, device=device)

    optimizer.zero_grad()
    pred = model(cheb, stats, batch)
    loss = F.mse_loss(pred, target)
    loss.backward()
    optimizer.step()
    return loss.item()


@torch.no_grad()
def predict_single(
    model: FareyChebNet,
    graph: dict,
    device: torch.device,
) -> float:
    """Predict log(1/spectral_gap) for a single graph."""
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

    model = FareyChebNet(
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
        pred_log = predict_single(model, g, device)
        # Convert back from log(1/gap) space
        pred_gap = 1.0 / np.exp(pred_log)
        actual_gap = g["spectral_gap"]
        predictions[g["n"]] = {
            "predicted_log": pred_log,
            "actual_log": g["target"],
            "predicted_gap": pred_gap,
            "actual_gap": actual_gap,
            "error_log": pred_log - g["target"],
            "error_gap": pred_gap - actual_gap,
            "abs_error_log": abs(pred_log - g["target"]),
            "rel_error": abs(pred_gap - actual_gap) / (actual_gap + 1e-12),
        }

    return predictions


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------


def linear_baseline_log(graphs: list[dict]) -> dict:
    """Predict log(1/spectral_gap) as linear function of log(num_nodes).

    Equivalent to: spectral_gap ~ exp(-a*log(n) - b) = n^(-a) * exp(-b).
    """
    log_nodes = np.array([np.log(g["num_nodes"]) for g in graphs])
    targets = np.array([np.log(1.0 / g["spectral_gap"]) for g in graphs])  # log(1/gap)

    X = np.column_stack([log_nodes, np.ones(len(log_nodes))])
    coeffs, _, _, _ = np.linalg.lstsq(X, targets, rcond=None)
    slope, intercept = coeffs

    preds_log = slope * log_nodes + intercept
    preds_gap = 1.0 / np.exp(preds_log)
    actuals_gap = np.array([g["spectral_gap"] for g in graphs])
    metrics = compute_metrics(preds_log, targets)
    gap_metrics = compute_metrics(preds_gap, actuals_gap)

    return {
        "name": "linear (log-log)",
        "slope": slope,
        "intercept": intercept,
        "metrics_log": metrics,
        "metrics_gap": gap_metrics,
        "predictions": {
            g["n"]: {
                "predicted_log": float(p),
                "actual_log": float(a),
                "predicted_gap": float(1.0 / np.exp(p)),
                "actual_gap": float(g["spectral_gap"]),
            }
            for g, p, a in zip(graphs, preds_log, targets)
        },
    }


def power_law_baseline(graphs: list[dict]) -> dict:
    """Fit spectral_gap ~ a * n^(-b) directly via least squares on log scale.

    log(gap) ~ log(a) - b * log(n)
    """
    log_n = np.array([np.log(g["num_nodes"]) for g in graphs])
    log_gap = np.array([np.log(g["spectral_gap"]) for g in graphs])

    X = np.column_stack([np.ones(len(log_n)), log_n])
    coeffs, _, _, _ = np.linalg.lstsq(X, log_gap, rcond=None)
    log_a, neg_b = coeffs
    a = np.exp(log_a)
    b = -neg_b

    preds_log_gap = log_a - b * log_n
    preds_gap = np.exp(preds_log_gap)
    actuals_gap = np.array([g["spectral_gap"] for g in graphs])

    metrics = compute_metrics(preds_gap, actuals_gap)

    return {
        "name": "power-law (gap ~ a * n^(-b))",
        "a": a,
        "b": b,
        "metrics": metrics,
        "predictions": {
            g["n"]: {
                "predicted_gap": float(p),
                "actual_gap": float(a_val),
            }
            for g, p, a_val in zip(graphs, preds_gap, actuals_gap)
        },
    }


# ---------------------------------------------------------------------------
# Results saving
# ---------------------------------------------------------------------------


def save_results(results: dict, args: argparse.Namespace) -> Path:
    """Save results to JSON."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_path = RESULTS_DIR / f"farey_K{args.K}_h{args.hidden}_e{args.epochs}.json"

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to {results_path}")
    return results_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Full-graph ChebConv for spectral gap prediction on Farey graphs"
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
        help="Only run the baseline comparisons",
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

    # Load all graphs
    graphs = load_all_graphs()
    n_graphs = len(graphs)
    logger.info(f"Loaded {n_graphs} Farey graphs")

    # Print spectral gap range
    gaps = [g["spectral_gap"] for g in graphs]
    logger.info(f"Spectral gap range: [{min(gaps):.8f}, {max(gaps):.8f}]")
    logger.info(
        f"log(1/gap) range: [{min(np.log(1 / g) for g in gaps):.2f}, "
        f"{max(np.log(1 / g) for g in gaps):.2f}]"
    )

    # --- Linear baseline (log-log) ---
    logger.info("=" * 70)
    logger.info("LINEAR BASELINE: log(1/gap) ~ a * log(num_nodes) + b")
    bl_linear = linear_baseline_log(graphs)
    logger.info(
        f"  slope={bl_linear['slope']:.4f}, intercept={bl_linear['intercept']:.4f}"
    )
    m = bl_linear["metrics_log"]
    logger.info(
        f"  [log-space] MAE={m['mae']:.4f}  RMSE={m['rmse']:.4f}  R²={m['r2']:.4f}"
    )
    m_gap = bl_linear["metrics_gap"]
    logger.info(
        f"  [gap-space] MAE={m_gap['mae']:.8f}  RMSE={m_gap['rmse']:.8f}  "
        f"R²={m_gap['r2']:.4f}  MedRelErr={m_gap['median_rel_error']:.4f}"
    )
    logger.info("  Per-graph predictions (gap-space):")
    for n in sorted(bl_linear["predictions"].keys()):
        pred = bl_linear["predictions"][n]
        logger.info(
            f"    n={n:3d}: predicted={pred['predicted_gap']:.8f}  "
            f"actual={pred['actual_gap']:.8f}  "
            f"rel_err={abs(pred['predicted_gap'] - pred['actual_gap']) / pred['actual_gap']:.4f}"
        )

    # --- Power-law baseline ---
    logger.info("=" * 70)
    logger.info("POWER-LAW BASELINE: spectral_gap ~ a * n^(-b)")
    bl_power = power_law_baseline(graphs)
    logger.info(f"  a={bl_power['a']:.6f}, b={bl_power['b']:.4f}")
    m_pw = bl_power["metrics"]
    logger.info(
        f"  [gap-space] MAE={m_pw['mae']:.8f}  RMSE={m_pw['rmse']:.8f}  "
        f"R²={m_pw['r2']:.4f}  MedRelErr={m_pw['median_rel_error']:.4f}"
    )
    logger.info("  Per-graph predictions:")
    for n in sorted(bl_power["predictions"].keys()):
        pred = bl_power["predictions"][n]
        rel = abs(pred["predicted_gap"] - pred["actual_gap"]) / pred["actual_gap"]
        logger.info(
            f"    n={n:3d}: predicted={pred['predicted_gap']:.8f}  "
            f"actual={pred['actual_gap']:.8f}  rel_err={rel:.4f}"
        )

    all_results = {
        "args": vars(args),
        "baselines": {
            "linear_log": {
                "slope": bl_linear["slope"],
                "intercept": bl_linear["intercept"],
                "metrics_log": bl_linear["metrics_log"],
                "metrics_gap": bl_linear["metrics_gap"],
            },
            "power_law": {
                "a": bl_power["a"],
                "b": bl_power["b"],
                "metrics": bl_power["metrics"],
            },
        },
    }

    if args.baseline_only:
        logger.info("Baseline-only mode, exiting.")
        save_results(all_results, args)
        return

    # --- Prepare features ---
    node_feat_dim = 5  # deg_norm, deg_rel, clustering, tri_norm, pagerank
    logger.info("=" * 70)
    logger.info(
        f"Precomputing Chebyshev features (K={args.K}, node_feat_dim={node_feat_dim})..."
    )
    dataset = prepare_dataset(graphs, args.K, force_recompute=args.force_recompute)

    cheb_feature_dim = dataset[0]["cheb_features"].shape[1]
    graph_stats_dim = dataset[0]["graph_stats"].shape[0]
    logger.info(
        f"Cheb feature dim: {cheb_feature_dim} (= {node_feat_dim} × {args.K + 1}), "
        f"Graph stats dim: {graph_stats_dim}"
    )

    # Verify consistent dimensions
    for g in dataset:
        assert g["cheb_features"].shape[1] == cheb_feature_dim, (
            f"Inconsistent cheb dim for n={g['n']}: "
            f"{g['cheb_features'].shape[1]} vs {cheb_feature_dim}"
        )

    # --- Standard train/test split (small n train, large n test) ---
    train_ns = [g["n"] for g in graphs if g["n"] <= 120]
    test_ns = [g["n"] for g in graphs if g["n"] > 120]

    train_data = [g for g in dataset if g["n"] <= 120]
    test_data = [g for g in dataset if g["n"] > 120]

    logger.info("\n" + "=" * 70)
    logger.info(
        f"STANDARD SPLIT: train n≤120 ({len(train_data)} graphs), "
        f"test n>120 ({len(test_data)} graphs)"
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

    split_preds_log = []
    split_actuals_log = []
    split_preds_gap = []
    split_actuals_gap = []
    for g in test_data:
        n_val = g["n"]
        pred = predictions[n_val]
        split_preds_log.append(pred["predicted_log"])
        split_actuals_log.append(pred["actual_log"])
        split_preds_gap.append(pred["predicted_gap"])
        split_actuals_gap.append(pred["actual_gap"])
        logger.info(
            f"  n={n_val:3d}: pred_gap={pred['predicted_gap']:.8f}  "
            f"actual={pred['actual_gap']:.8f}  "
            f"rel_err={pred['rel_error']:.4f}"
        )

    split_preds_log = np.array(split_preds_log)
    split_actuals_log = np.array(split_actuals_log)
    split_preds_gap = np.array(split_preds_gap)
    split_actuals_gap = np.array(split_actuals_gap)
    split_metrics_log = compute_metrics(split_preds_log, split_actuals_log)
    split_metrics_gap = compute_metrics(split_preds_gap, split_actuals_gap)

    # Baselines on same split
    baseline_train = [g for g in graphs if g["n"] <= 120]
    baseline_test = [g for g in graphs if g["n"] > 120]

    bl_linear_split = linear_baseline_log(baseline_train)
    bl_linear_preds = 1.0 / np.exp(
        bl_linear_split["slope"] * np.log([g["num_nodes"] for g in baseline_test])
        + bl_linear_split["intercept"]
    )
    bl_linear_actuals = np.array([g["spectral_gap"] for g in baseline_test])
    bl_linear_metrics = compute_metrics(bl_linear_preds, bl_linear_actuals)

    bl_power_split = power_law_baseline(baseline_train)
    bl_power_preds = np.array(
        [
            bl_power_split["a"] * g["num_nodes"] ** (-bl_power_split["b"])
            for g in baseline_test
        ]
    )
    bl_power_actuals = np.array([g["spectral_gap"] for g in baseline_test])
    bl_power_metrics = compute_metrics(bl_power_preds, bl_power_actuals)

    logger.info("=" * 70)
    logger.info("STANDARD SPLIT RESULTS")
    logger.info("=" * 70)
    logger.info(
        f"  Model:  [log] MAE={split_metrics_log['mae']:.4f}  "
        f"RMSE={split_metrics_log['rmse']:.4f}  R²={split_metrics_log['r2']:.4f}"
    )
    logger.info(
        f"  Model:  [gap] MAE={split_metrics_gap['mae']:.8f}  "
        f"RMSE={split_metrics_gap['rmse']:.8f}  R²={split_metrics_gap['r2']:.4f}  "
        f"MedRelErr={split_metrics_gap['median_rel_error']:.4f}"
    )
    logger.info(
        f"  Linear: [gap] MAE={bl_linear_metrics['mae']:.8f}  "
        f"RMSE={bl_linear_metrics['rmse']:.8f}  R²={bl_linear_metrics['r2']:.4f}"
    )
    logger.info(
        f"  Power:  [gap] MAE={bl_power_metrics['mae']:.8f}  "
        f"RMSE={bl_power_metrics['rmse']:.8f}  R²={bl_power_metrics['r2']:.4f}"
    )
    logger.info(f"  Training time: {elapsed:.1f}s")

    if split_metrics_gap["r2"] > bl_power_metrics["r2"]:
        logger.success(
            f"  ✓ Model beats power-law baseline! "
            f"ΔR² = {split_metrics_gap['r2'] - bl_power_metrics['r2']:+.4f}"
        )
    else:
        logger.warning(
            f"  ✗ Model does NOT beat power-law baseline. "
            f"ΔR² = {split_metrics_gap['r2'] - bl_power_metrics['r2']:+.4f}"
        )

    all_results["standard_split"] = {
        "model_metrics_log": split_metrics_log,
        "model_metrics_gap": split_metrics_gap,
        "linear_metrics_gap": bl_linear_metrics,
        "power_metrics_gap": bl_power_metrics,
        "predictions": {
            str(n_val): {
                "predicted_gap": predictions[n_val]["predicted_gap"],
                "actual_gap": predictions[n_val]["actual_gap"],
                "rel_error": predictions[n_val]["rel_error"],
            }
            for n_val in sorted(predictions.keys())
        },
    }

    # --- Leave-one-out cross-validation ---
    if args.leave_one_out:
        logger.info("\n" + "=" * 70)
        logger.info(
            f"LEAVE-ONE-OUT CROSS-VALIDATION "
            f"(K={args.K}, hidden={args.hidden}, epochs={args.epochs})"
        )
        logger.info("-" * 70)

        all_preds_log = []
        all_actuals_log = []
        all_preds_gap = []
        all_actuals_gap = []
        loo_predictions = {}
        t_loo_start = time.time()

        for i, test_graph in enumerate(dataset):
            n_val = test_graph["n"]
            train_graphs_fold = [g for j, g in enumerate(dataset) if j != i]

            logger.info(
                f"\nFold {i + 1}/{n_graphs}: testing on n={n_val} "
                f"(N={test_graph['num_nodes']}, gap={test_graph['spectral_gap']:.8f}), "
                f"training on {len(train_graphs_fold)} graphs"
            )

            t0 = time.time()
            fold_preds = train_and_evaluate_fold(
                train_graphs=train_graphs_fold,
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

            pred = fold_preds[n_val]
            all_preds_log.append(pred["predicted_log"])
            all_actuals_log.append(pred["actual_log"])
            all_preds_gap.append(pred["predicted_gap"])
            all_actuals_gap.append(pred["actual_gap"])
            loo_predictions[n_val] = pred

            logger.info(
                f"  n={n_val:3d}: pred_gap={pred['predicted_gap']:.8f}  "
                f"actual={pred['actual_gap']:.8f}  "
                f"rel_err={pred['rel_error']:.4f}  ({elapsed:.1f}s)"
            )

        loo_elapsed = time.time() - t_loo_start
        all_preds_log = np.array(all_preds_log)
        all_actuals_log = np.array(all_actuals_log)
        all_preds_gap = np.array(all_preds_gap)
        all_actuals_gap = np.array(all_actuals_gap)
        loo_metrics_log = compute_metrics(all_preds_log, all_actuals_log)
        loo_metrics_gap = compute_metrics(all_preds_gap, all_actuals_gap)

        logger.info("\n" + "=" * 70)
        logger.info("LEAVE-ONE-OUT CROSS-VALIDATION RESULTS")
        logger.info("=" * 70)
        logger.info(
            f"  Model:  [log] MAE={loo_metrics_log['mae']:.4f}  "
            f"RMSE={loo_metrics_log['rmse']:.4f}  R²={loo_metrics_log['r2']:.4f}"
        )
        logger.info(
            f"  Model:  [gap] MAE={loo_metrics_gap['mae']:.8f}  "
            f"RMSE={loo_metrics_gap['rmse']:.8f}  R²={loo_metrics_gap['r2']:.4f}  "
            f"MedRelErr={loo_metrics_gap['median_rel_error']:.4f}"
        )
        logger.info(
            f"  Linear baseline: [log] MAE={m['mae']:.4f}  "
            f"RMSE={m['rmse']:.4f}  R²={m['r2']:.4f}"
        )
        logger.info(
            f"  Power-law baseline: [gap] MAE={m_pw['mae']:.8f}  "
            f"RMSE={m_pw['rmse']:.8f}  R²={m_pw['r2']:.4f}"
        )
        logger.info(f"  Total LOO time: {loo_elapsed:.1f}s")

        if loo_metrics_gap["r2"] > m_pw["r2"]:
            logger.success(
                f"  ✓ Model beats power-law baseline! "
                f"ΔR² = {loo_metrics_gap['r2'] - m_pw['r2']:+.4f}"
            )
        else:
            logger.warning(
                f"  ✗ Model does NOT beat power-law baseline. "
                f"ΔR² = {loo_metrics_gap['r2'] - m_pw['r2']:+.4f}"
            )

        all_results["loo"] = {
            "model_metrics_log": loo_metrics_log,
            "model_metrics_gap": loo_metrics_gap,
            "total_time": loo_elapsed,
            "predictions": {
                str(n_val): {
                    "predicted_gap": pred["predicted_gap"],
                    "actual_gap": pred["actual_gap"],
                    "rel_error": pred["rel_error"],
                }
                for n_val, pred in loo_predictions.items()
            },
        }

    # Save results
    save_results(all_results, args)


if __name__ == "__main__":
    main()
