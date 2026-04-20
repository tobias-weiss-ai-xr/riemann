"""
SIGN (Scalable Inception Graph Neural Network) for spectral prediction.

Precomputes K-hop neighborhood aggregations offline using sparse matrix powers,
then trains a lightweight MLP — no message passing at runtime.

This addresses two key challenges with GNNs on Cayley graphs:
1. Vertex-transitivity: every node has identical local structure, so per-node
   features must encode multi-hop context to be discriminative.
2. Large graphs (up to 1M nodes): precomputing aggregations avoids repeated
   message passing per epoch.

Reference: Rossi et al., "SIGN: Scalable Inception Graph Neural Networks" (2020)

Usage:
    python train_sign.py --hops 2 --hidden 128 --epochs 200 --batch-size 32 --lr 1e-3
    python train_sign.py --full-graphs --hops 3 --epochs 100
"""

from __future__ import annotations

import argparse
import hashlib
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger
from scipy.sparse import csr_matrix, diags
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import global_mean_pool

# Reuse paths from train_gnn.py
DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_DIR = DATA_DIR / "cayley-graphs"
EIGEN_DIR = DATA_DIR / "eigenvalues"
AUG_DIR = DATA_DIR / "augmented"
SIGN_CACHE_DIR = DATA_DIR / "sign_precomputed"


# ---------------------------------------------------------------------------
# SIGN precomputation
# ---------------------------------------------------------------------------


def _build_symmetric_normalized_adj(
    edge_index: np.ndarray, num_nodes: int
) -> csr_matrix:
    """Build D^{-1/2} A D^{-1/2} (symmetric normalization) as sparse matrix."""
    adj = csr_matrix(
        (
            np.ones(edge_index.shape[1], dtype=np.float64),
            (edge_index[0], edge_index[1]),
        ),
        shape=(num_nodes, num_nodes),
    )
    # Symmetrize (undirected graph)
    adj = adj.maximum(adj.T)
    # Remove self-loops for cleaner aggregation
    adj.setdiag(0.0)
    adj.eliminate_zeros()

    # D^{-1/2}
    deg = np.array(adj.sum(axis=1)).flatten()
    deg[deg == 0] = 1.0  # avoid division by zero for isolated nodes
    d_inv_sqrt = 1.0 / np.sqrt(deg)
    D_inv_sqrt = diags(d_inv_sqrt)

    # D^{-1/2} A D^{-1/2}
    norm_adj = D_inv_sqrt @ adj @ D_inv_sqrt
    return norm_adj


def precompute_sign_features(
    edge_index: np.ndarray,
    node_features: np.ndarray,
    num_nodes: int,
    num_hops: int,
) -> np.ndarray:
    """
    Precompute multi-hop SIGN features via sparse matrix powers.

    Computes X_k = (D^{-1/2} A D^{-1/2})^k @ X for k=0,...,K
    and concatenates them: shape (N, in_channels * (K+1)).
    """
    norm_adj = _build_symmetric_normalized_adj(edge_index, num_nodes)

    hop_features = [node_features.astype(np.float64)]
    current = node_features.astype(np.float64)

    for k in range(1, num_hops + 1):
        current = norm_adj @ current
        hop_features.append(current)

    # Concatenate all hop features
    x_sign = np.concatenate(hop_features, axis=1)
    return x_sign.astype(np.float32)


def _data_hash(data: Data, num_hops: int) -> str:
    """Deterministic hash for caching precomputed features."""
    h = hashlib.md5()
    # Hash on graph structure + node features shape (not values — those are
    # deterministic from edge_index for augmented data)
    h.update(str(data.num_nodes).encode())
    h.update(str(data.edge_index.shape).encode())
    if hasattr(data, "edge_index"):
        h.update(data.edge_index.numpy().tobytes())
    h.update(str(num_hops).encode())
    return h.hexdigest()[:16]


def precompute_dataset(
    dataset: list[Data], num_hops: int, cache_dir: Path
) -> list[Data]:
    """Precompute SIGN features for all samples, with disk caching."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    precomputed = []
    t0 = time.time()
    for i, data in enumerate(dataset):
        cache_key = f"{_data_hash(data, num_hops)}_{num_hops}_sign.pt"
        cache_path = cache_dir / cache_key

        if cache_path.exists():
            x_sign = torch.load(cache_path, weights_only=True)
            cached = True
        else:
            edge_index_np = data.edge_index.numpy()
            x_np = data.x.numpy()
            x_sign_arr = precompute_sign_features(
                edge_index_np, x_np, data.num_nodes, num_hops
            )
            x_sign = torch.from_numpy(x_sign_arr)
            torch.save(x_sign, cache_path)
            cached = False

        # Build new Data with precomputed features (no edge_index needed)
        new_data = Data(
            x=x_sign,
            y=data.y.clone(),
            num_nodes=data.num_nodes,
        )
        precomputed.append(new_data)

        if (i + 1) % 100 == 0 or cached:
            pass  # silent for cached items

    elapsed = time.time() - t0
    logger.info(
        f"Precomputed SIGN features ({num_hops}-hop) for {len(dataset)} samples "
        f"in {elapsed:.1f}s. Cache: {cache_dir}"
    )
    return precomputed


# ---------------------------------------------------------------------------
# SIGN MLP model
# ---------------------------------------------------------------------------


class SIGN(torch.nn.Module):
    """SIGN model: MLP over concatenated multi-hop node features + mean pool."""

    def __init__(
        self,
        in_channels: int,
        hidden_dim: int = 128,
        num_hops: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        # Input dim = in_channels * (num_hops + 1)
        input_dim = in_channels * (num_hops + 1)
        self.mlp = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.BatchNorm1d(hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.BatchNorm1d(hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        # x already contains concatenated hop features
        x = self.mlp(x)
        # Global mean pool over nodes in each graph
        x = global_mean_pool(x, batch)
        return x.squeeze(-1)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(preds: np.ndarray, targets: np.ndarray) -> dict[str, float]:
    """Compute MAE, RMSE, R²."""
    mae = float(np.mean(np.abs(preds - targets)))
    rmse = float(np.sqrt(np.mean((preds - targets) ** 2)))
    ss_res = float(np.sum((targets - preds) ** 2))
    ss_tot = float(np.sum((targets - targets.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return {"mae": mae, "rmse": rmse, "r2": r2}


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def train_epoch(model, loader, optimizer, device) -> float:
    model.train()
    total_loss = 0.0
    total_graphs = 0
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        out = model(data.x, data.batch)
        loss = F.mse_loss(out, data.y.squeeze())
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * data.num_graphs
        total_graphs += data.num_graphs
    return total_loss / max(total_graphs, 1)


@torch.no_grad()
def evaluate(model, loader, device) -> dict[str, float]:
    model.eval()
    all_preds = []
    all_targets = []
    for data in loader:
        data = data.to(device)
        out = model(data.x, data.batch)
        all_preds.append(out.cpu().numpy())
        all_targets.append(data.y.squeeze().cpu().numpy())
    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)
    return compute_metrics(preds, targets)


# ---------------------------------------------------------------------------
# Data loading (matches train_gnn.py patterns)
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
        # Remove non-tensor attributes that break PyG Batch collation.
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


def load_dataset(primes: list[int], target: str = "spectral_gap") -> list[Data]:
    """Load full graphs with eigenvalue targets (for cross-prime evaluation)."""
    dataset = []
    for p in primes:
        pt_path = GRAPH_DIR / f"sl2fp_p{p}.pt"
        if not pt_path.exists():
            logger.warning(f"Skipping p={p}: no graph file")
            continue

        data = torch.load(pt_path, weights_only=False)

        stats_path = EIGEN_DIR / f"sl2fp_p{p}_stats.npz"
        if not stats_path.exists():
            logger.warning(f"Skipping p={p}: no eigenvalue stats")
            continue

        stats = dict(np.load(stats_path))
        stats = {k: float(v) for k, v in stats.items()}

        if target == "spectral_gap":
            data.y = torch.tensor([stats["spectral_gap"]], dtype=torch.float32)
        else:
            raise ValueError(f"Unsupported target for full graphs: {target}")

        # Clean non-tensor keys
        keys_to_remove = [
            k
            for k in data.keys()
            if not isinstance(data[k], torch.Tensor) and k != "num_nodes"
        ]
        for k in keys_to_remove:
            del data[k]

        dataset.append(data)

    return dataset


def parse_primes(spec: str) -> list[int]:
    """Parse prime specification: '2-61', '2,3,5,7,11'."""

    def _is_prime(n: int) -> bool:
        if n < 2:
            return False
        if n < 4:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6
        return True

    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return [p for p in range(int(lo), int(hi) + 1) if _is_prime(p)]
    return [int(x.strip()) for x in spec.split(",")]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Train SIGN (Scalable Inception GNN) on Cayley graphs"
    )
    parser.add_argument("--hops", type=int, default=2, help="Number of hops (K)")
    parser.add_argument("--hidden", type=int, default=128, help="MLP hidden dim")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument(
        "--target",
        type=str,
        choices=["spectral_gap", "ramanujan_ratio"],
        default="spectral_gap",
    )
    parser.add_argument(
        "--full-graphs",
        action="store_true",
        help="Also evaluate on full graphs for cross-prime generalization",
    )
    parser.add_argument(
        "--train-primes", type=str, default="2-50", help="Primes for full-graph train"
    )
    parser.add_argument(
        "--test-primes", type=str, default="53-101", help="Primes for full-graph test"
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Load augmented dataset
    train_data = load_augmented_dataset(args.target, split="train")
    test_data = load_augmented_dataset(args.target, split="test")
    logger.info(
        f"Train: {len(train_data)} augmented samples, "
        f"Test: {len(test_data)} augmented samples"
    )

    in_channels = train_data[0].x.shape[1]

    # Precompute SIGN features
    logger.info(
        f"Precomputing {args.hops}-hop SIGN features (in_channels={in_channels})..."
    )
    train_data = precompute_dataset(train_data, args.hops, SIGN_CACHE_DIR / "train")
    test_data = precompute_dataset(test_data, args.hops, SIGN_CACHE_DIR / "test")
    sign_in_channels = train_data[0].x.shape[1]
    logger.info(f"SIGN feature dim: {sign_in_channels} (was {in_channels} per hop)")

    # Optionally load full graphs
    full_train_data = None
    full_test_data = None
    if args.full_graphs:
        logger.info("Loading full graphs for cross-prime evaluation...")
        train_primes = parse_primes(args.train_primes)
        test_primes = parse_primes(args.test_primes)
        full_train_data = load_dataset(train_primes, args.target)
        full_test_data = load_dataset(test_primes, args.target)
        logger.info(
            f"Full graphs: {len(full_train_data)} train, {len(full_test_data)} test"
        )

        # Precompute full graph features (can be slow for large graphs)
        if full_train_data:
            logger.info("Precomputing SIGN features for full train graphs...")
            full_train_data = precompute_dataset(
                full_train_data, args.hops, SIGN_CACHE_DIR / "full_train"
            )
        if full_test_data:
            logger.info("Precomputing SIGN features for full test graphs...")
            full_test_data = precompute_dataset(
                full_test_data, args.hops, SIGN_CACHE_DIR / "full_test"
            )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=args.batch_size, shuffle=False)

    # Model
    model = SIGN(
        in_channels=in_channels,
        hidden_dim=args.hidden,
        num_hops=args.hops,
        dropout=args.dropout,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(
        f"SIGN model: {sign_in_channels} → {args.hidden} → {args.hidden} → 1 ({total_params:,} params)"
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # Training loop
    logger.info(
        f"Training SIGN (hops={args.hops}, hidden={args.hidden}) for {args.epochs} epochs"
    )
    best_test_mae = float("inf")

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device)
        scheduler.step()

        # Evaluate every 10 epochs + first epoch + final epoch
        if epoch % 10 == 0 or epoch == 1 or epoch == args.epochs:
            train_metrics = evaluate(model, train_loader, device)
            test_metrics = evaluate(model, test_loader, device)

            if test_metrics["mae"] < best_test_mae:
                best_test_mae = test_metrics["mae"]

            logger.info(
                f"Epoch {epoch:3d} | "
                f"Train MAE={train_metrics['mae']:.4f} RMSE={train_metrics['rmse']:.4f} R²={train_metrics['r2']:.4f} | "
                f"Test  MAE={test_metrics['mae']:.4f} RMSE={test_metrics['rmse']:.4f} R²={test_metrics['r2']:.4f} | "
                f"LR={scheduler.get_last_lr()[0]:.2e}"
            )

    # Final evaluation
    train_metrics = evaluate(model, train_loader, device)
    test_metrics = evaluate(model, test_loader, device)
    logger.info("=" * 80)
    logger.info(
        f"FINAL  Train: MAE={train_metrics['mae']:.4f} RMSE={train_metrics['rmse']:.4f} R²={train_metrics['r2']:.4f}"
    )
    logger.info(
        f"FINAL  Test:  MAE={test_metrics['mae']:.4f} RMSE={test_metrics['rmse']:.4f} R²={test_metrics['r2']:.4f}"
    )
    logger.info(f"Best test MAE: {best_test_mae:.4f}")

    # Full graph evaluation
    if full_test_data:
        full_test_loader = DataLoader(full_test_data, batch_size=1, shuffle=False)
        full_metrics = evaluate(model, full_test_loader, device)
        logger.info(
            f"FULL   Test:  MAE={full_metrics['mae']:.4f} RMSE={full_metrics['rmse']:.4f} R²={full_metrics['r2']:.4f}"
        )

    # Save model
    model_path = DATA_DIR / "models" / "sign_spectral_gap.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_path)
    logger.success(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
