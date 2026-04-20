"""
GNN training scaffold — spectral prediction on SL(2,F_p) Cayley graphs.

Task: Given a Cayley graph, predict its eigenvalue distribution (or top-k eigenvalues).

Usage:
    python train_gnn.py --config configs/default.yaml
    python train_gnn.py --epochs 100 --batch-size 32 --model gat
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn.functional as F
from loguru import logger
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import GCNConv, GATConv, global_mean_pool

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_DIR = DATA_DIR / "cayley-graphs"
EIGEN_DIR = DATA_DIR / "eigenvalues"
AUG_DIR = DATA_DIR / "augmented"


class SpectralGNN(torch.nn.Module):
    """GNN for predicting spectral properties from graph structure."""

    def __init__(
        self,
        in_channels: int = 1,
        hidden_channels: int = 64,
        out_channels: int = 1,
        model_type: str = "gcn",
    ):
        super().__init__()
        Conv = GCNConv if model_type == "gcn" else GATConv

        self.conv1 = Conv(in_channels, hidden_channels)
        self.conv2 = Conv(hidden_channels, hidden_channels)
        self.conv3 = Conv(hidden_channels, hidden_channels)
        self.lin = torch.nn.Linear(hidden_channels, out_channels)

    def forward(
        self, x: torch.Tensor, edge_index: torch.Tensor, batch: torch.Tensor
    ) -> torch.Tensor:
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index).relu()
        x = self.conv3(x, edge_index).relu()
        x = global_mean_pool(x, batch)
        x = self.lin(x)
        return x


def load_dataset(primes: list[int], target: str = "spectral_gap") -> list[Data]:
    """Load graphs with eigenvalue targets."""
    dataset = []
    for p in primes:
        # Load graph
        pt_path = GRAPH_DIR / f"sl2fp_p{p}.pt"
        if not pt_path.exists():
            logger.warning(f"Skipping p={p}: no graph file")
            continue

        data = torch.load(pt_path, weights_only=False)

        # Load eigenvalue stats
        stats_path = EIGEN_DIR / f"sl2fp_p{p}_stats.npz"
        if not stats_path.exists():
            logger.warning(f"Skipping p={p}: no eigenvalue stats")
            continue

        stats = (
            dict(np.load(stats_path)) if False else __import__("numpy").load(stats_path)
        )
        stats = {k: float(v) for k, v in stats.items()}

        if target == "spectral_gap":
            data.y = torch.tensor([stats["spectral_gap"]], dtype=torch.float32)
        elif target == "ramanujan_ratio":
            data.y = torch.tensor([stats["ramanujan_ratio"]], dtype=torch.float32)
        elif target == "is_ramanujan":
            data.y = torch.tensor([stats["is_ramanujan"]], dtype=torch.long)
        else:
            raise ValueError(f"Unknown target: {target}")

        dataset.append(data)

    return dataset


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
        # PyG Data stores everything; only tensors and special keys are collatable.
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


def train_epoch(model, loader, optimizer, device, target: str) -> float:
    model.train()
    total_loss = 0.0
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        out = model(data.x, data.edge_index, data.batch)
        if target == "is_ramanujan":
            loss = F.cross_entropy(out, data.y)
        else:
            loss = F.mse_loss(out.squeeze(), data.y.squeeze())
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * data.num_graphs
    return total_loss / sum(d.num_graphs for d in loader)


@torch.no_grad()
def evaluate(model, loader, device, target: str) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    for data in loader:
        data = data.to(device)
        out = model(data.x, data.edge_index, data.batch)
        if target == "is_ramanujan":
            loss = F.cross_entropy(out, data.y)
            pred = out.argmax(dim=1)
            correct += (pred == data.y).sum().item()
            total += data.y.size(0)
        else:
            loss = F.mse_loss(out.squeeze(), data.y.squeeze())
        total_loss += loss.item() * data.num_graphs
    avg_loss = total_loss / sum(d.num_graphs for d in loader)
    acc = correct / total if total > 0 else 0.0
    return avg_loss, acc


def main():
    parser = argparse.ArgumentParser(description="Train GNN on Cayley graphs")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--model", type=str, choices=["gcn", "gat"], default="gat")
    parser.add_argument(
        "--target",
        type=str,
        choices=["spectral_gap", "ramanujan_ratio", "is_ramanujan"],
        default="spectral_gap",
    )
    parser.add_argument(
        "--train-primes", type=str, default="2-50", help="Primes for training"
    )
    parser.add_argument(
        "--test-primes", type=str, default="53-101", help="Primes for testing"
    )
    parser.add_argument(
        "--augmented",
        action="store_true",
        help="Load augmented dataset from data/augmented/ instead of individual graph files",
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

    train_primes = parse_primes(args.train_primes)
    test_primes = parse_primes(args.test_primes)

    if args.augmented:
        # Load augmented dataset (already has y targets and split)
        train_data = load_augmented_dataset(args.target, split="train")
        test_data = load_augmented_dataset(args.target, split="test")
        logger.info(
            f"Train: {len(train_data)} augmented samples, "
            f"Test: {len(test_data)} augmented samples"
        )
    else:
        logger.info(f"Train primes: {train_primes}")
        logger.info(f"Test primes: {test_primes}")
        train_data = load_dataset(train_primes, args.target)
        test_data = load_dataset(test_primes, args.target)
        logger.info(f"Train: {len(train_data)} graphs, Test: {len(test_data)} graphs")

    if len(train_data) == 0:
        logger.error(
            "No training data found. Run generate_graphs.py and compute_eigenvalues.py first."
        )
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=args.batch_size, shuffle=False)

    # Model — infer in_channels from data
    out_channels = 2 if args.target == "is_ramanujan" else 1
    in_channels = train_data[0].x.shape[1] if train_data else 1
    model = SpectralGNN(
        in_channels=in_channels,
        hidden_channels=args.hidden,
        out_channels=out_channels,
        model_type=args.model,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    # Training loop
    logger.info(
        f"Training {args.model.upper()} for {args.epochs} epochs (target: {args.target})"
    )
    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device, args.target)
        test_loss, test_acc = evaluate(model, test_loader, device, args.target)

        if epoch % 10 == 0 or epoch == 1:
            logger.info(
                f"Epoch {epoch:3d} | Train Loss: {train_loss:.4f} | Test Loss: {test_loss:.4f} | Test Acc: {test_acc:.2%}"
            )

    # Save model
    model_path = (
        Path(__file__).parent.parent
        / "data"
        / "models"
        / f"{args.model}_{args.target}.pt"
    )
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_path)
    logger.success(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
