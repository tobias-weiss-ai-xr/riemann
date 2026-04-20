"""
Hierarchical ChebConv GNN for spectral gap prediction on SL(2,F_p) Cayley graphs.

Architecture: Multi-scale ChebConv encoder with Chebyshev polynomial spectral
filters, residual connections, BatchNorm, and hierarchical readout (pool at
each layer, concatenate).

Motivation: Cayley graphs are vertex-transitive — every node is locally identical.
ChebConv operates in the spectral domain via Chebyshev polynomial approximation
of graph filters, making it theoretically better suited for spectral property
prediction than spatial message-passing GNNs.

Usage:
    python train_cheb_hierarchical.py --K 3 --hidden 128 --layers 3 --epochs 200 --batch-size 32
    python train_cheb_hierarchical.py --K 5 --contrastive-weight 0.1 --epochs 100
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import ChebConv, global_max_pool, global_mean_pool
from torch_geometric.nn.norm import BatchNorm

# Reuse paths and loader from train_gnn
DATA_DIR = Path(__file__).parent.parent / "data"
AUG_DIR = DATA_DIR / "augmented"


# ---------------------------------------------------------------------------
# Lambda-max computation (cached)
# ---------------------------------------------------------------------------

# For normalized Laplacian L_norm = I - D^{-1/2} A D^{-1/2}, eigenvalues ∈ [0, 2].
# Cayley graphs of SL(2,F_p) are 4-regular connected graphs, so λ_max(L_norm) ≤ 2.
# We compute exact λ_max for small graphs (≤5000 nodes) via sparse eigsh,
# and use the safe upper bound of 2.0 for larger graphs.

_lambda_max_cache: dict[int, float] = {}
SMALL_GRAPH_THRESHOLD = 5000


def compute_lambda_max(edge_index: torch.Tensor, num_nodes: int) -> float:
    """Compute largest eigenvalue of the normalized Laplacian.

    Uses scipy sparse eigsh for small graphs; falls back to 2.0 for large graphs.
    """
    import scipy.sparse as sp
    import scipy.sparse.linalg as sla

    cache_key = (num_nodes, edge_index.shape[1])
    if cache_key in _lambda_max_cache:
        return _lambda_max_cache[cache_key]

    # Safe default for large graphs
    if num_nodes > SMALL_GRAPH_THRESHOLD:
        _lambda_max_cache[cache_key] = 2.0
        return 2.0

    row = edge_index[0].numpy()
    col = edge_index[1].numpy()
    data = np.ones(len(row), dtype=np.float32)

    A = sp.coo_matrix((data, (row, col)), shape=(num_nodes, num_nodes))
    A = (A + A.T).multiply(A.T > 0)  # symmetrize, remove duplicates
    A = sp.csr_matrix(A)

    deg = np.array(A.sum(axis=1)).flatten()
    deg[deg == 0] = 1.0
    deg_inv_sqrt = 1.0 / np.sqrt(deg)
    D_inv_sqrt = sp.diags(deg_inv_sqrt)

    L_norm = sp.eye(num_nodes) - D_inv_sqrt @ A @ D_inv_sqrt
    L_norm = sp.csr_matrix(L_norm)

    k = min(6, num_nodes - 1)
    try:
        eigenvalues, _ = sla.eigsh(L_norm, k=k, which="LM")
        lam_max = float(np.max(eigenvalues))
    except sla.ArpackNoConvergence as e:
        lam_max = float(np.max(e.eigenvalues))
    except Exception:
        lam_max = 2.0

    lam_max = max(lam_max, 1.0)
    _lambda_max_cache[cache_key] = lam_max
    return lam_max


def compute_lambda_max_for_data(data: Data) -> float:
    """Compute lambda_max for a single PyG Data object."""
    return compute_lambda_max(data.edge_index, data.num_nodes)


def attach_lambda_max(dataset: list[Data]) -> list[Data]:
    """Pre-compute and attach lambda_max to each graph in the dataset."""
    n_computed = 0
    for i, data in enumerate(dataset):
        if hasattr(data, "lambda_max") and data.lambda_max is not None:
            continue
        lam = compute_lambda_max_for_data(data)
        if lam < 2.0:
            n_computed += 1
        data.lambda_max = torch.tensor([lam], dtype=torch.float32)

    exact = [d.lambda_max.item() for d in dataset if d.lambda_max.item() < 2.0]
    if exact:
        logger.info(
            f"  Computed exact λ_max for {len(exact)} small graphs, "
            f"used 2.0 for {len(dataset) - len(exact)} large graphs. "
            f"Exact range: {min(exact):.4f} – {max(exact):.4f}"
        )
    else:
        logger.info(f"  All {len(dataset)} graphs use default λ_max=2.0 (all large)")
    return dataset


# ---------------------------------------------------------------------------
# Contrastive loss
# ---------------------------------------------------------------------------


def contrastive_loss(
    embeddings: torch.Tensor,
    targets: torch.Tensor,
    temperature: float = 1.0,
) -> torch.Tensor:
    """Spectral distance contrastive loss.

    For each pair (i, j) in the batch, penalize distance in embedding space
    proportional to |y_i - y_j|. Encourages smooth spectral embedding.
    """
    n = embeddings.size(0)
    if n < 2:
        return torch.tensor(0.0, device=embeddings.device)

    # Pairwise L2 distances in embedding space
    diff = embeddings.unsqueeze(1) - embeddings.unsqueeze(0)  # (n, n, d)
    emb_dist = (diff**2).sum(dim=2)  # (n, n)

    # Pairwise target differences
    target_diff = (targets.unsqueeze(1) - targets.unsqueeze(0)).abs()  # (n, n)

    # Mask diagonal
    mask = ~torch.eye(n, dtype=torch.bool, device=embeddings.device)

    # Weight: pairs with similar targets should have similar embeddings
    # Loss = target_diff * emb_dist (weighted MSE in embedding space)
    loss = (target_diff[mask] * emb_dist[mask]).mean()

    return loss / temperature


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class HierarchicalChebGNN(nn.Module):
    """Multi-scale ChebConv GNN with hierarchical readout.

    At each ChebConv layer, we pool (mean + max) and collect the representation.
    All layer pools are concatenated for the final prediction, capturing
    graph structure at multiple spectral scales.
    """

    def __init__(
        self,
        in_channels: int = 3,
        hidden_dim: int = 128,
        K: int = 3,
        num_layers: int = 3,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # Build ChebConv layers
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        # Layer 0: in_channels -> hidden_dim
        self.convs.append(ChebConv(in_channels, hidden_dim, K=K))
        self.norms.append(BatchNorm(hidden_dim))

        # Layers 1..num_layers-1: hidden_dim -> hidden_dim (with residual)
        for _ in range(num_layers - 1):
            self.convs.append(ChebConv(hidden_dim, hidden_dim, K=K))
            self.norms.append(BatchNorm(hidden_dim))

        # Multi-scale readout: each layer produces hidden_dim via mean + max = 2*hidden_dim
        # Total readout dim: num_layers * 2 * hidden_dim
        readout_dim = num_layers * 2 * hidden_dim

        # Prediction MLP
        self.predictor = nn.Sequential(
            nn.Linear(readout_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        lambda_max: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Node features (N, in_channels)
            edge_index: Edge indices (2, E)
            batch: Batch assignment vector (N,)
            lambda_max: Per-graph max eigenvalue of normalized Laplacian (num_graphs,)

        Returns:
            Predicted spectral gap (batch_size, 1)
        """
        h = x
        layer_pools = []

        for i, (conv, norm) in enumerate(zip(self.convs, self.norms)):
            h_new = conv(h, edge_index, batch=batch, lambda_max=lambda_max)
            h_new = norm(h_new)
            h_new = F.relu(h_new)

            # Residual connection (after first layer if dims match)
            if i > 0 and h_new.shape[-1] == h.shape[-1]:
                h_new = h_new + h

            h = h_new

            # Multi-scale pool at every layer
            pool_mean = global_mean_pool(h, batch)  # (batch, hidden_dim)
            pool_max = global_max_pool(h, batch)  # (batch, hidden_dim)
            layer_pools.append(torch.cat([pool_mean, pool_max], dim=1))

        # Concatenate all layer representations
        graph_emb = torch.cat(
            layer_pools, dim=1
        )  # (batch, num_layers * 2 * hidden_dim)

        return self.predictor(graph_emb)

    def forward_with_embedding(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        lambda_max: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Forward pass that also returns the graph embedding (for contrastive loss)."""
        h = x
        layer_pools = []

        for i, (conv, norm) in enumerate(zip(self.convs, self.norms)):
            h_new = conv(h, edge_index, batch=batch, lambda_max=lambda_max)
            h_new = norm(h_new)
            h_new = F.relu(h_new)

            if i > 0 and h_new.shape[-1] == h.shape[-1]:
                h_new = h_new + h

            h = h_new

            pool_mean = global_mean_pool(h, batch)
            pool_max = global_max_pool(h, batch)
            layer_pools.append(torch.cat([pool_mean, pool_max], dim=1))

        graph_emb = torch.cat(layer_pools, dim=1)
        pred = self.predictor(graph_emb)
        return pred, graph_emb


# ---------------------------------------------------------------------------
# Data loading (reuse from train_gnn.py pattern)
# ---------------------------------------------------------------------------


def load_augmented_dataset(
    target: str = "spectral_gap", split: str = "train"
) -> list[Data]:
    """Load augmented PyG dataset from data/augmented/{split}/."""
    split_dir = AUG_DIR / split
    if not split_dir.exists():
        raise FileNotFoundError(
            f"Augmented dataset not found at {split_dir}. "
            f"Run augment_dataset.py --all first."
        )

    dataset = []
    for pt_file in sorted(split_dir.glob("*.pt")):
        data = torch.load(pt_file, weights_only=False)
        keys_to_remove = [
            k
            for k in data.keys()
            if not isinstance(data[k], torch.Tensor) and k != "num_nodes"
        ]
        for k in keys_to_remove:
            del data[k]
        dataset.append(data)

    logger.info(
        f"Loaded {len(dataset)} augmented samples from {split_dir.name}/ "
        f"(in_channels={dataset[0].x.shape[1] if dataset else '?'})"
    )
    return dataset


# ---------------------------------------------------------------------------
# Training / evaluation
# ---------------------------------------------------------------------------


def train_epoch(
    model: HierarchicalChebGNN,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    contrastive_weight: float = 0.0,
) -> tuple[float, float]:
    """Train one epoch. Returns (mse_loss, contrastive_loss)."""
    model.train()
    total_mse = 0.0
    total_contrastive = 0.0
    total_graphs = 0

    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()

        # Gather lambda_max per graph, expand to per-node for batched graph
        lam_max_graph = getattr(data, "lambda_max", None)
        if lam_max_graph is not None:
            # Map per-graph lambda_max to per-node using batch assignment
            lam_max = lam_max_graph[data.batch]  # (num_nodes,)
        else:
            lam_max = None

        pred, graph_emb = model.forward_with_embedding(
            data.x, data.edge_index, data.batch, lambda_max=lam_max
        )

        # Primary MSE loss
        mse_loss = F.mse_loss(pred.squeeze(-1), data.y.squeeze())

        # Contrastive auxiliary loss
        if contrastive_weight > 0:
            contr_loss = contrastive_loss(graph_emb, data.y.squeeze())
        else:
            contr_loss = torch.tensor(0.0, device=device)

        loss = mse_loss + contrastive_weight * contr_loss
        loss.backward()
        optimizer.step()

        n = data.num_graphs
        total_mse += mse_loss.item() * n
        total_contrastive += contr_loss.item() * n
        total_graphs += n

    avg_mse = total_mse / max(total_graphs, 1)
    avg_contr = total_contrastive / max(total_graphs, 1)
    return avg_mse, avg_contr


@torch.no_grad()
def evaluate(
    model: HierarchicalChebGNN,
    loader: DataLoader,
    device: torch.device,
) -> tuple[float, float, float, float]:
    """Evaluate model. Returns (mse, mae, rmse, r2)."""
    model.eval()
    all_preds = []
    all_targets = []

    for data in loader:
        data = data.to(device)
        lam_max_graph = getattr(data, "lambda_max", None)
        if lam_max_graph is not None:
            lam_max = lam_max_graph[data.batch]
        else:
            lam_max = None

        out = model(data.x, data.edge_index, data.batch, lambda_max=lam_max)
        all_preds.append(out.squeeze(-1).cpu())
        all_targets.append(data.y.squeeze().cpu())

    preds = torch.cat(all_preds)
    targets = torch.cat(all_targets)

    mse = F.mse_loss(preds, targets).item()
    mae = F.l1_loss(preds, targets).item()
    rmse = mse**0.5

    ss_res = ((targets - preds) ** 2).sum().item()
    ss_tot = ((targets - targets.mean()) ** 2).sum().item()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

    return mse, mae, rmse, r2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Hierarchical ChebConv GNN for spectral gap prediction"
    )
    parser.add_argument(
        "--K",
        type=int,
        default=3,
        help="Chebyshev polynomial order (spectral filter resolution)",
    )
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument(
        "--layers", type=int, default=3, help="Number of ChebConv layers"
    )
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument(
        "--contrastive-weight",
        type=float,
        default=0.0,
        help="Weight for contrastive auxiliary loss (0=disabled)",
    )
    parser.add_argument("--log-interval", type=int, default=10)
    args = parser.parse_args()

    # Load data
    train_data = load_augmented_dataset(split="train")
    test_data = load_augmented_dataset(split="test")

    if len(train_data) == 0:
        logger.error("No training data. Run augment_dataset.py first.")
        return

    # Compute lambda_max per graph
    logger.info("Computing lambda_max for training graphs...")
    train_data = attach_lambda_max(train_data)
    logger.info("Computing lambda_max for test graphs...")
    test_data = attach_lambda_max(test_data)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=args.batch_size, shuffle=False)

    # Model
    in_channels = train_data[0].x.shape[1]
    model = HierarchicalChebGNN(
        in_channels=in_channels,
        hidden_dim=args.hidden,
        K=args.K,
        num_layers=args.layers,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Model: HierarchicalChebGNN (in={in_channels}, hidden={args.hidden}, "
        f"K={args.K}, layers={args.layers}, params={total_params:,})"
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-5
    )

    # Training loop
    logger.info(
        f"Training for {args.epochs} epochs (contrastive_w={args.contrastive_weight})"
    )
    best_test_mae = float("inf")
    best_test_r2 = float("-inf")

    for epoch in range(1, args.epochs + 1):
        train_mse, train_contr = train_epoch(
            model, train_loader, optimizer, device, args.contrastive_weight
        )
        scheduler.step()

        test_mse, test_mae, test_rmse, test_r2 = evaluate(model, test_loader, device)

        if test_mae < best_test_mae:
            best_test_mae = test_mae
        if test_r2 > best_test_r2:
            best_test_r2 = test_r2

        if epoch % args.log_interval == 0 or epoch == 1:
            contr_str = (
                f" | Contr: {train_contr:.4f}" if args.contrastive_weight > 0 else ""
            )
            logger.info(
                f"Epoch {epoch:3d} | "
                f"Train MSE: {train_mse:.6f}{contr_str} | "
                f"Test MAE: {test_mae:.6f} RMSE: {test_rmse:.6f} R²: {test_r2:.4f}"
            )

    # Final evaluation
    logger.info("=" * 70)
    logger.info("Final evaluation:")
    test_mse, test_mae, test_rmse, test_r2 = evaluate(model, test_loader, device)
    logger.info(f"  MAE:  {test_mae:.6f}")
    logger.info(f"  RMSE: {test_rmse:.6f}")
    logger.info(f"  R²:   {test_r2:.4f}")
    logger.info(f"  Best MAE:  {best_test_mae:.6f}")
    logger.info(f"  Best R²:   {best_test_r2:.4f}")

    # Save model
    model_path = DATA_DIR / "models" / "cheb_hierarchical_spectral_gap.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": {
                "in_channels": in_channels,
                "hidden_dim": args.hidden,
                "K": args.K,
                "num_layers": args.layers,
            },
            "test_metrics": {
                "mae": test_mae,
                "rmse": test_rmse,
                "r2": test_r2,
                "mse": test_mse,
            },
            "best_test_mae": best_test_mae,
            "best_test_r2": best_test_r2,
        },
        model_path,
    )
    logger.success(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
