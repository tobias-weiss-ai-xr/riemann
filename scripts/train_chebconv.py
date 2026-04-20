"""
ChebConv training for spectral gap prediction on SL(2,F_p) Cayley graphs.

Uses spectral convolution (Chebyshev polynomials) with scale-invariant features.
Full-graph training — no subgraph augmentation (vertex-transitive graphs have identical local structure).

Key design decisions from Experiment 1-2:
- Vertex-transitive → local neighborhoods are useless → need full-graph spectral convolution
- Size range 6 → 1M nodes → size-stratified sampling + scale-invariant features
- 22 training samples (p=2..79) → small dataset → weight decay + early stopping

Usage:
    python train_chebconv.py --all           # All primes with eigenvalues
    python train_chebconv.py --train 2,3,5 --test 7,11
    python train_chebconv.py --k 5 --hops 3  # Chebyshev K=5, 3-hop ChebConv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger
from torch.utils.data import WeightedRandomSampler
from torch_geometric.data import Data, Batch, DataLoader
from torch_geometric.nn import ChebConv, global_mean_pool
from sklearn.preprocessing import KBinsDiscretizer

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_DIR = DATA_DIR / "cayley-graphs"
EIGEN_DIR = DATA_DIR / "eigenvalues"


# ─── Feature engineering ───────────────────────────────────────────────────


def compute_scale_invariant_features(
    num_nodes: int, degree: int, prime: int
) -> np.ndarray:
    """
    Compute scale-invariant features that are useful for predicting spectral properties.

    Key features:
    - log(num_nodes): group-theoretic invariant (grows ~p^3 for SL(2,F_p))
    - log(degree): always 4 for fundamental generators, but useful for comparison
    - prime: encoded as sin/cos for smooth periodicity
    - log_prime_over_log_nodes: relationship between prime and graph size
    - 1/log(num_nodes): scale normalization
    """
    log_nodes = np.log(num_nodes)
    log_prime = np.log(prime)

    return np.array(
        [
            log_nodes,  # log(|G|) — primary scale invariant
            degree / 4.0,  # normalized degree (always 1.0 for SL(2,F_p))
            np.sin(2 * np.pi * prime / 100.0),  # prime encoding (periodic)
            np.cos(2 * np.pi * prime / 100.0),
            log_prime / log_nodes if log_nodes > 0 else 0,  # prime/graph-size ratio
            1.0 / log_nodes if log_nodes > 0 else 0,  # scale normalization
        ],
        dtype=np.float32,
    )


def load_full_graph(prime: int, max_nodes: int = 500000) -> tuple[Data, dict] | None:
    """
    Load a full Cayley graph as a PyG Data object.

    For large graphs (>max_nodes), subsample edges and remap node indices.
    Returns None if graph doesn't exist.
    """
    pt_path = GRAPH_DIR / f"sl2fp_p{prime}.pt"
    if not pt_path.exists():
        return None

    data = torch.load(pt_path, weights_only=False)
    edges = data.edge_index.numpy()
    orig_num_nodes = int(data.num_nodes)

    # For graphs > max_nodes, subsample edges to keep manageable
    if orig_num_nodes > max_nodes:
        logger.warning(
            f"  p={prime}: {orig_num_nodes:,} nodes > {max_nodes:,} limit, subsampling"
        )
        rng = np.random.RandomState(prime)  # deterministic subsampling
        indices = rng.choice(edges.shape[1], size=max_nodes * 4, replace=False)
        edges = edges[:, indices]

        # Remap node indices to 0..N-1 to avoid index out of bounds
        unique_nodes = np.unique(edges)
        node_map = {old: new for new, old in enumerate(unique_nodes.tolist())}
        edges = np.array(
            [[node_map[s] for s in edges[0]], [node_map[d] for d in edges[1]]]
        )
        num_nodes = len(unique_nodes)
    else:
        num_nodes = orig_num_nodes

    # Build adjacency with proper edge weights for ChebConv normalization
    # ChebConv expects edge_index with shape (2, E) and optional edge_weight
    n_edges = edges.shape[1]
    if n_edges == 0:
        edge_index = torch.zeros((2, 0), dtype=torch.long)
        edge_weight = torch.ones(0, dtype=torch.float32)
    else:
        # Create edge_index with both directions for undirected graph
        src = torch.tensor(edges[0], dtype=torch.long)
        dst = torch.tensor(edges[1], dtype=torch.long)
        # Add reverse edges
        edge_index = torch.cat(
            [
                torch.stack([src, dst]),
                torch.stack([dst, src]),
            ],
            dim=1,
        )

        # Symmetric edge weights: 1/√(degree(i)*degree(j)) for proper normalization
        degree = torch.zeros(num_nodes, dtype=torch.float32)
        degree.scatter_add_(0, src, torch.ones_like(src, dtype=torch.float32))
        degree.scatter_add_(0, dst, torch.ones_like(dst, dtype=torch.float32))

        # Normalize weights
        norm_weight_src = (1.0 / torch.sqrt(degree[src] + 1e-8)).float()
        norm_weight_dst = (1.0 / torch.sqrt(degree[dst] + 1e-8)).float()
        edge_weight = torch.cat([norm_weight_src, norm_weight_dst], dim=0)

    # Node features: constant 1 (no local structural info in Cayley graphs)
    x = torch.ones((num_nodes, 1), dtype=torch.float32)

    stats = {}

    return Data(
        x=x, edge_index=edge_index, edge_weight=edge_weight, num_nodes=num_nodes
    ), stats


def load_eigenvalue_target(prime: int) -> tuple[float, float] | None:
    """Load spectral gap and Ramanujan ratio from eigenvalue stats."""
    stats_path = EIGEN_DIR / f"sl2fp_p{prime}_stats.npz"
    if not stats_path.exists():
        return None

    stats = np.load(stats_path)
    return float(stats["spectral_gap"]), float(stats["ramanujan_ratio"])


# ─── Dataset ───────────────────────────────────────────────────────────────


class FullGraphDataset:
    """Dataset of full Cayley graphs with spectral targets."""

    def __init__(self, primes: list[int], max_nodes: int = 500000):
        self.data = []
        self.targets = []
        self.ramanujan_ratios = []
        self.primes = []
        self.sizes = []
        self.graph_features = []

        for p in primes:
            full_data, _ = load_full_graph(p, max_nodes=max_nodes)
            if full_data is None:
                logger.warning(f"Skipping p={p}: no graph file")
                continue

            target = load_eigenvalue_target(p)
            if target is None:
                logger.warning(f"Skipping p={p}: no eigenvalue stats")
                continue

            spectral_gap, ramanujan_ratio = target
            num_nodes = full_data.num_nodes
            normalized_gap = np.log1p(spectral_gap)

            self.data.append(full_data)
            self.targets.append(normalized_gap)
            self.ramanujan_ratios.append(ramanujan_ratio)
            self.primes.append(p)
            self.sizes.append(num_nodes)

            # Compute graph-level features (scale-invariant)
            log_group_order = np.log(num_nodes)
            prime_sin = np.sin(2 * np.pi * p / 100.0)
            prime_cos = np.cos(2 * np.pi * p / 100.0)
            inv_log_p = 1.0 / np.log(p)
            self.graph_features.append(
                [log_group_order, prime_sin, prime_cos, inv_log_p]
            )

        if len(self.data) == 0:
            raise ValueError("No valid data loaded. Check graph and eigenvalue files.")

        self.targets = np.array(self.targets, dtype=np.float32)
        self.ramanujan_ratios = np.array(self.ramanujan_ratios, dtype=np.float32)
        self.graph_features = np.array(self.graph_features, dtype=np.float32)

        logger.info(
            f"Loaded {len(self.data)} graphs (p={min(self.primes)}..{max(self.primes)})"
        )
        logger.info(
            f"  Spectral gap range: {np.log(np.expm1(self.targets.min())):.4f} — {np.log(np.expm1(self.targets.max())):.4f}"
        )
        logger.info(f"  Graph sizes: {min(self.sizes):,} — {max(self.sizes):,} nodes")

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Data:
        data = self.data[idx].clone()
        data.y = torch.tensor([self.targets[idx]], dtype=torch.float32)
        data.raman_ratio = torch.tensor(self.ramanujan_ratios[idx], dtype=torch.float32)
        data.prime = self.primes[idx]
        data.size = self.sizes[idx]

        # Ensure graph_features is a 2D tensor [1, 4] for the batch collation
        data.graph_features = torch.tensor(
            self.graph_features[idx], dtype=torch.float32
        ).unsqueeze(0)
        return data


# ─── Size-stratified sampler ──────────────────────────────────────────────


def create_size_stratified_sampler(
    dataset: FullGraphDataset, power: float = 0.5
) -> WeightedRandomSampler:
    """
    Create WeightedRandomSampler that ensures balanced representation across graph sizes.

    Uses quantile-binned discretization to create equal-frequency bins,
    then inverse-frequency weighting per bin.
    """
    sizes = np.array(dataset.sizes, dtype=np.float64)

    # Quantile binning
    binning = KBinsDiscretizer(n_bins=4, strategy="quantile", encode="ordinal")
    bins = binning.fit_transform(sizes.reshape(-1, 1)).flatten().astype(int)

    # Compute inverse-frequency weights
    bin_counts = np.bincount(bins, minlength=4)
    bin_weights = 1.0 / (bin_counts[bins] + 1e-6)

    # Apply sqrt scaling to avoid instability (power=0.5)
    weights = np.sqrt(bin_weights)

    sampler = WeightedRandomSampler(
        weights=weights,
        num_samples=len(weights),
        replacement=True,
    )

    logger.info(
        f"Size-stratified sampler: bins={bin_counts}, weights=1/sqrt(counts) * sqrt({power:.1f})"
    )
    return sampler


# ─── Model ─────────────────────────────────────────────────────────────────


class ChebConvSpectralPredictor(torch.nn.Module):
    """
    Chebyshev spectral convolution + multi-scale readout for spectral prediction.

    Architecture:
    1. ChebConv layers (spectral convolution via Chebyshev polynomials)
    2. Global readout (mean + max pooling over nodes)
    3. MLP head with scale-invariant conditioning

    This architecture was recommended by the librarian agent research as:
    "ChebConv encoder + spectral-preserving sparse pooling + multi-scale readout"
    """

    def __init__(
        self,
        in_channels: int = 1,
        hidden_channels: int = 64,
        cheb_order: int = 5,
        num_layers: int = 3,
        num_graph_features: int = 4,
    ):
        super().__init__()
        self.cheb_order = cheb_order

        # Chebyshev spectral convolution layers
        self.convs = torch.nn.ModuleList()
        in_dim = in_channels
        for _ in range(num_layers):
            self.convs.append(ChebConv(in_dim, hidden_channels, K=cheb_order))
            in_dim = hidden_channels

        # Multi-scale readout: combine mean and max pooling
        self.readout_dim = hidden_channels * 2 + num_graph_features

        # MLP head with dropout
        self.head = torch.nn.Sequential(
            torch.nn.Linear(self.readout_dim, hidden_channels),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.3),
            torch.nn.Linear(hidden_channels, 1),
        )

    def forward(self, batch: Batch) -> torch.Tensor:
        x, edge_index, edge_weight, batch_idx = (
            batch.x,
            batch.edge_index,
            batch.edge_weight,
            batch.batch,
        )

        # Apply ChebConv layers
        for conv in self.convs:
            x = conv(x, edge_index, edge_weight).relu()

        # Multi-scale readout: concatenate mean and max pooling
        mean_pool = global_mean_pool(x, batch_idx)
        max_pool, _ = torch.max(x, dim=0)
        max_pool = max_pool.unsqueeze(0).expand(mean_pool.size(0), -1)

        # Get the graph-level features from the batch
        # They are [batch_size, 4] or [1, 4]. We MUST ensure it's [batch_size, 4]
        graph_feats = batch.graph_features
        if graph_feats.dim() == 1:
            graph_feats = graph_feats.unsqueeze(0)

        # Explicitly expand to the current batch size
        batch_size = mean_pool.size(0)
        graph_feats = graph_feats.expand(batch_size, -1)

        # Concatenate: [batch_size, 64] + [batch_size, 64] + [batch_size, 4] -> [batch_size, 132]
        readout = torch.cat([mean_pool, max_pool, graph_feats], dim=1)

        # MLP head
        return self.head(readout).squeeze()


# ─── Training ─────────────────────────────────────────────────────────────


def train_epoch(
    model: torch.nn.Module,
    loader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> float:
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    total_samples = 0

    for batch in loader:
        batch = batch.to(device)
        optimizer.zero_grad()

        # Forward pass
        out = model(batch)
        loss = F.mse_loss(out, batch.y.squeeze())

        # Backward
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item() * batch.num_graphs
        total_samples += batch.num_graphs

    return total_loss / total_samples


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    loader,
    device: torch.device,
    dataset: FullGraphDataset,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Evaluate model and return metrics + predictions."""
    model.eval()
    total_loss = 0.0
    total_samples = 0

    all_preds = []
    all_targets = []

    for batch in loader:
        batch = batch.to(device)
        out = model(batch)

        loss = F.mse_loss(out, batch.y.squeeze())
        total_loss += loss.item() * batch.num_graphs
        total_samples += batch.num_graphs

        # Inverse-transform predictions (log1p → original scale)
        preds = np.expm1(out.cpu().numpy())
        targets = np.expm1(batch.y.cpu().numpy())

        all_preds.extend(preds.flatten())
        all_targets.extend(targets.flatten())

    avg_loss = total_loss / total_samples
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)

    # R² score
    ss_res = np.sum((all_targets - all_preds) ** 2)
    ss_tot = np.sum((all_targets - np.mean(all_targets)) ** 2)
    r2 = 1.0 - (ss_res / (ss_tot + 1e-10))

    # MAE
    mae = np.mean(np.abs(all_targets - all_preds))

    return avg_loss, r2, mae, all_preds, all_targets


# ─── Main ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Train ChebConv on Cayley graphs")
    parser.add_argument(
        "--all", action="store_true", help="Use all primes with eigenvalues"
    )
    parser.add_argument(
        "--train-primes", type=str, default="2-79", help="Training primes"
    )
    parser.add_argument("--test-primes", type=str, default="83-101", help="Test primes")
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument(
        "--cheb-order", type=int, default=5, help="Chebyshev polynomial order K"
    )
    parser.add_argument("--hops", type=int, default=3, help="Number of ChebConv layers")
    parser.add_argument(
        "--max-nodes",
        type=int,
        default=500000,
        help="Max nodes per graph (subsample if larger)",
    )
    parser.add_argument(
        "--patience", type=int, default=50, help="Early stopping patience"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/models/chebconv.pt",
        help="Model output path",
    )
    args = parser.parse_args()

    import numpy as np

    # Parse primes
    def parse_primes(spec):
        if "-" in spec:
            lo, hi = spec.split("-", 1)
            return [
                p
                for p in range(int(lo), int(hi) + 1)
                if all(p % d for d in range(2, int(p**0.5) + 1)) and p >= 2
            ]
        return [int(x) for x in spec.split(",")]

    if args.all:
        # Auto-detect all primes with eigenvalue data
        train_primes = [
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
        ]
        test_primes = [83, 89, 97, 101]
    else:
        train_primes = parse_primes(args.train_primes)
        test_primes = parse_primes(args.test_primes)

    logger.info(f"Train primes: {train_primes} ({len(train_primes)} graphs)")
    logger.info(f"Test primes: {test_primes} ({len(test_primes)} graphs)")

    # Check CUDA
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Load full-graph dataset
    logger.info("Loading full-graph dataset...")
    train_dataset = FullGraphDataset(train_primes, max_nodes=args.max_nodes)

    # Create size-stratified sampler
    sampler = create_size_stratified_sampler(train_dataset, power=0.5)

    # DataLoader with sampler (use PyG's DataLoader for proper Data collation)
    from torch_geometric.loader import DataLoader as PyGDataLoader

    train_loader = PyGDataLoader(
        dataset=train_dataset,
        sampler=sampler,
        batch_size=args.batch_size,
    )

    # Test loader (no shuffling, all test primes as one batch or mini-batches)
    test_dataset = FullGraphDataset(test_primes, max_nodes=args.max_nodes)
    test_loader = PyGDataLoader(
        dataset=test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
    )

    # Test loader (no shuffling, all test primes as one batch or mini-batches)
    test_dataset = FullGraphDataset(test_primes, max_nodes=args.max_nodes)
    test_loader = DataLoader(
        dataset=test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
    )

    # Infer in_channels from first data point
    in_channels = train_dataset[0].x.shape[1]
    logger.info(f"Input channels: {in_channels}")

    # Initialize model
    model = ChebConvSpectralPredictor(
        in_channels=in_channels,
        hidden_channels=args.hidden,
        cheb_order=args.cheb_order,
        num_layers=args.hops,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)

    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    logger.info(
        f"Training for {args.epochs} epochs, batch_size={args.batch_size}, "
        f"lr={args.lr}, cheb_order={args.cheb_order}, hops={args.hops}"
    )

    # Training loop with early stopping
    best_loss = float("inf")
    best_state = None
    patience_counter = 0

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device)

        # Evaluate on training set
        _, train_r2, train_mae, _, _ = evaluate(
            model, train_loader, device, train_dataset
        )

        # Evaluate on test set (if any test primes)
        test_loss, test_r2, test_mae, preds, targets = None, None, None, None, None
        if len(test_dataset) > 0:
            test_loss, test_r2, test_mae, preds, targets = evaluate(
                model, test_loader, device, test_dataset
            )

        if epoch % 25 == 0 or epoch == 1:
            msg = (
                f"Epoch {epoch:3d} | Train Loss: {train_loss:.4f} | "
                f"Train R²: {train_r2:.3f} | Train MAE: {train_mae:.4f}"
            )
            if test_loss is not None:
                msg += f" | Test Loss: {test_loss:.4f} | Test R²: {test_r2:.3f} | Test MAE: {test_mae:.4f}"
            logger.info(msg)

        # Save best model
        if train_loss < best_loss:
            best_loss = train_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= args.patience:
            logger.info(f"Early stopping at epoch {epoch}")
            break

    # Load best model
    if best_state is not None:
        model.load_state_dict(best_state)

    # Final evaluation on training set
    _, final_train_r2, final_train_mae, _, _ = evaluate(
        model, train_loader, device, train_dataset
    )

    # Final evaluation on test set
    final_test_loss, final_test_r2, final_test_mae, preds, targets = (
        None,
        None,
        None,
        None,
        None,
    )
    if len(test_dataset) > 0:
        final_test_loss, final_test_r2, final_test_mae, preds, targets = evaluate(
            model, test_loader, device, test_dataset
        )
        logger.info("\nFinal test predictions:")
        for p, pred, target in zip(test_dataset.primes, preds, targets):
            logger.info(f"  p={p:3d}: pred={pred:.4f}, actual={target:.4f}")

    logger.info(f"\nFinal train R²: {final_train_r2:.3f}, MAE: {final_train_mae:.4f}")
    if final_test_r2 is not None:
        logger.info(f"Final test R²: {final_test_r2:.3f}, MAE: {final_test_mae:.4f}")

    # Save model
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
    logger.success(f"Model saved to {output_path}")

    # Save training config
    config = {
        "train_primes": train_primes,
        "test_primes": test_primes,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "hidden": args.hidden,
        "cheb_order": args.cheb_order,
        "hops": args.hops,
        "max_nodes": args.max_nodes,
        "best_train_loss": float(best_loss),
        "final_train_r2": float(final_train_r2),
        "final_test_r2": float(final_test_r2) if final_test_r2 is not None else None,
    }
    import json

    config_path = output_path.with_suffix(".json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    logger.info(f"Config saved to {config_path}")


if __name__ == "__main__":
    main()
