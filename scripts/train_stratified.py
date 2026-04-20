"""
Stratified sampling for balanced spectral gap training.

Addresses the skewed spectral gap distribution by:
  1. BinBalancedBatchSampler — ensures each batch covers all spectral gap bins
  2. ReweightedMSELoss — upweights samples from rare bins
  3. CurriculumScheduler — gradually introduces extreme bins

Reuses SpectralGNN and load_augmented_dataset from train_gnn.py.

Usage:
    python train_stratified.py --num-bins 5 --batch-size 32 --epochs 200 --model gat --hidden 128
    python train_stratified.py --curriculum --num-bins 5 --epochs 300
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger
from torch_geometric.loader import DataLoader

# Ensure scripts/ is importable for train_gnn imports
sys.path.insert(0, str(Path(__file__).parent))
from train_gnn import SpectralGNN, load_augmented_dataset

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"


# ---------------------------------------------------------------------------
# Bin-balanced batch sampler
# ---------------------------------------------------------------------------


class BinBalancedBatchSampler(torch.utils.data.Sampler):
    """Sampler that ensures each mini-batch contains samples from ALL spectral gap bins.

    Samples are binned by their y value (spectral gap) into quantile bins.
    Each batch draws ``batch_size // num_bins`` samples from every bin.
    """

    def __init__(
        self,
        dataset,
        num_bins: int = 5,
        batch_size: int = 32,
        shuffle: bool = True,
        active_bins: set[int] | None = None,
    ):
        self.dataset = dataset
        self.num_bins = num_bins
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.active_bins = active_bins  # None → all bins

        # Build bin assignments (quantile-based)
        self.y_values = torch.tensor(
            [d.y.item() if d.y.numel() == 1 else d.y[0].item() for d in dataset],
            dtype=torch.float32,
        )
        quantiles = torch.linspace(0, 1, num_bins + 1)
        boundaries = torch.quantile(self.y_values, quantiles)
        # Clamp boundaries to handle ties at edges
        boundaries[0] = -math.inf
        boundaries[-1] = math.inf
        self.boundaries = boundaries

        # Assign each sample to a bin
        self.bin_indices: dict[int, list[int]] = {b: [] for b in range(num_bins)}
        for idx in range(len(dataset)):
            y = self.y_values[idx].item()
            bin_idx = int((y > boundaries[:-1]).sum().item()) - 1
            bin_idx = max(0, min(num_bins - 1, bin_idx))
            self.bin_indices[bin_idx].append(idx)

        # Log bin distribution (only once on first init)
        if not hasattr(BinBalancedBatchSampler, "_logged_bins"):
            for b in range(num_bins):
                lo, hi = boundaries[b].item(), boundaries[b + 1].item()
                logger.info(
                    f"  Bin {b}: [{lo:.4f}, {hi:.4f})  n={len(self.bin_indices[b])}"
                )
            BinBalancedBatchSampler._logged_bins = True

        # Build epoch-level batch schedule
        self._build_batches()

    def _build_batches(self):
        """Pre-compute batch indices for one epoch.

        Creates approximately ceil(n_active / batch_size) batches by cycling
        through all active bins, ensuring each batch has samples from every bin.
        """
        active = (
            self.active_bins
            if self.active_bins is not None
            else set(range(self.num_bins))
        )
        if not active:
            self.batches = []
            return

        n_active = sum(len(self.bin_indices[b]) for b in active)
        per_bin = max(1, self.batch_size // len(active))
        remainder = self.batch_size - per_bin * len(active)

        # Shuffle within each bin
        if self.shuffle:
            rng = torch.Generator().manual_seed(torch.initial_seed() & 0xFFFFFFFF)
            for b in active:
                n = len(self.bin_indices[b])
                perm = torch.randperm(n, generator=rng).tolist()
                self.bin_indices[b] = [self.bin_indices[b][i] for i in perm]

        # Build batches — enough to cover all samples roughly once
        num_batches = max(1, math.ceil(n_active / self.batch_size))
        batches = []
        iterators = {b: iter(self.bin_indices[b]) for b in active}

        for _ in range(num_batches):
            batch = []
            extra_bins = list(active)[:remainder] if remainder > 0 else []
            for b in active:
                count = per_bin + (1 if b in extra_bins else 0)
                for _ in range(count):
                    try:
                        batch.append(next(iterators[b]))
                    except StopIteration:
                        # If bin exhausted, wrap around
                        iterators[b] = iter(self.bin_indices[b])
                        try:
                            batch.append(next(iterators[b]))
                        except StopIteration:
                            pass
            if len(batch) >= per_bin:
                batches.append(batch)

        self.batches = batches

    def __iter__(self):
        self._build_batches()
        yield from self.batches

    def __len__(self):
        return len(self.batches)


# ---------------------------------------------------------------------------
# Curriculum scheduler
# ---------------------------------------------------------------------------


class CurriculumScheduler:
    """Gradually introduces spectral gap bins during training.

    Phases:
      - Epochs 1-20%:   middle 3 bins only (core spectral gap range)
      - Epochs 20-50%:  all bins (full range)
      - Epochs 50-100%: all bins with oversampling flag enabled
    """

    def __init__(self, total_epochs: int, num_bins: int = 5):
        self.total_epochs = total_epochs
        self.num_bins = num_bins

    def get_active_bins(self, epoch: int) -> set[int]:
        frac = epoch / max(self.total_epochs, 1)
        mid = self.num_bins // 2
        half = self.num_bins // 2

        if frac < 0.2:
            # Middle 3 bins
            lo = max(0, mid - 1)
            hi = min(self.num_bins, mid + 2)
            return set(range(lo, hi))
        else:
            # All bins
            return set(range(self.num_bins))

    def should_oversample(self, epoch: int) -> bool:
        return (epoch / max(self.total_epochs, 1)) >= 0.5


# ---------------------------------------------------------------------------
# Reweighted MSE loss
# ---------------------------------------------------------------------------


class ReweightedMSELoss:
    """MSE loss with per-sample weights inversely proportional to bin frequency.

    weight_i = (1 / freq_bin_i)^power
    power=0.5 → sqrt scaling (moderate reweighting)
    """

    def __init__(self, dataset, num_bins: int = 5, power: float = 0.5):
        self.power = power

        # Compute bin frequencies
        y_values = torch.tensor(
            [d.y.item() if d.y.numel() == 1 else d.y[0].item() for d in dataset],
            dtype=torch.float32,
        )
        quantiles = torch.linspace(0, 1, num_bins + 1)
        boundaries = torch.quantile(y_values, quantiles)
        boundaries[0] = -math.inf
        boundaries[-1] = math.inf

        # Count per bin
        bin_counts = torch.zeros(num_bins)
        bin_assignment = []
        for y in y_values:
            b = int((y > boundaries[:-1]).sum().item()) - 1
            b = max(0, min(num_bins - 1, b))
            bin_assignment.append(b)
            bin_counts[b] += 1

        # Compute weights
        self.sample_weights = torch.zeros(len(dataset))
        for i, b in enumerate(bin_assignment):
            freq = bin_counts[b].item() / len(dataset)
            self.sample_weights[i] = (1.0 / max(freq, 1e-8)) ** power

        # Normalize so mean weight = 1
        self.sample_weights = self.sample_weights / self.sample_weights.mean()

        logger.info(
            f"ReweightedMSELoss: power={power}, "
            f"weight_range=[{self.sample_weights.min():.2f}, {self.sample_weights.max():.2f}]"
        )

    def __call__(
        self, pred: torch.Tensor, target: torch.Tensor, indices: torch.Tensor
    ) -> torch.Tensor:
        """Compute weighted MSE loss.

        Args:
            pred: Model predictions (batch_size,)
            target: Ground truth (batch_size,)
            indices: Dataset indices for the batch samples
        """
        weights = self.sample_weights[indices].to(pred.device)
        per_sample = (pred - target) ** 2
        return (weights * per_sample).mean()


# ---------------------------------------------------------------------------
# Training / evaluation with per-bin metrics
# ---------------------------------------------------------------------------


def train_epoch(
    model, loader, optimizer, device, loss_fn, epoch_indices: dict | None = None
) -> float:
    """Train for one epoch.

    Args:
        model: GNN model
        loader: PyG DataLoader (with BinBalancedBatchSampler as batch_sampler)
        optimizer: optimizer
        device: torch device
        loss_fn: ReweightedMSELoss or F.mse_loss
        epoch_indices: optional dict mapping batch_idx → list of dataset indices
    """
    model.train()
    total_loss = 0.0
    total_graphs = 0
    for batch_idx, batch_data in enumerate(loader):
        batch_data = batch_data.to(device)

        optimizer.zero_grad()
        out = model(batch_data.x, batch_data.edge_index, batch_data.batch)

        if isinstance(loss_fn, ReweightedMSELoss) and epoch_indices is not None:
            indices = torch.tensor(epoch_indices[batch_idx], dtype=torch.long)
            loss = loss_fn(out.squeeze(), batch_data.y.squeeze(), indices)
        else:
            loss = F.mse_loss(out.squeeze(), batch_data.y.squeeze())

        loss.backward()
        optimizer.step()
        total_loss += loss.item() * batch_data.num_graphs
        total_graphs += batch_data.num_graphs

    return total_loss / max(total_graphs, 1)


@torch.no_grad()
def evaluate_per_bin(model, dataset, device, num_bins, boundaries) -> dict:
    """Evaluate model on dataset, computing per-bin and overall metrics."""
    model.eval()

    loader = DataLoader(dataset, batch_size=64, shuffle=False)

    all_preds = []
    all_targets = []
    all_y = []

    for data in loader:
        data = data.to(device)
        out = model(data.x, data.edge_index, data.batch)
        all_preds.append(out.squeeze().cpu())
        all_targets.append(data.y.squeeze().cpu())
        all_y.append(data.y.squeeze().cpu())

    all_preds = torch.cat(all_preds)
    all_targets = torch.cat(all_targets)
    all_y = torch.cat(all_y)

    # Overall metrics
    mae = (all_preds - all_targets).abs().mean().item()
    mse = F.mse_loss(all_preds, all_targets).item()
    rmse = math.sqrt(mse)
    ss_res = ((all_targets - all_preds) ** 2).sum().item()
    ss_tot = ((all_targets - all_targets.mean()) ** 2).sum().item()
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0

    # Per-bin metrics
    bin_results = []
    for b in range(num_bins):
        lo, hi = boundaries[b].item(), boundaries[b + 1].item()
        if b < num_bins - 1:
            mask = (all_y >= lo) & (all_y < hi)
        else:
            mask = (all_y >= lo) & (all_y <= hi)

        if mask.sum() == 0:
            bin_results.append({"bin": b, "range": f"[{lo:.4f}, {hi:.4f})", "n": 0})
            continue

        bp = all_preds[mask]
        bt = all_targets[mask]
        b_mae = (bp - bt).abs().mean().item()
        b_mse = F.mse_loss(bp, bt).item()
        b_n = mask.sum().item()

        bin_results.append(
            {
                "bin": b,
                "range": f"[{lo:.4f}, {hi:.4f})",
                "n": b_n,
                "mae": b_mae,
                "mse": b_mse,
            }
        )

    return {
        "overall": {"mae": mae, "rmse": rmse, "mse": mse, "r2": r2},
        "per_bin": bin_results,
        "preds": all_preds,
        "targets": all_targets,
    }


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------


def load_baseline(model_type: str, in_channels: int, hidden: int, device):
    """Load baseline GAT model if available."""
    baseline_path = MODEL_DIR / f"{model_type}_spectral_gap.pt"
    if not baseline_path.exists():
        logger.warning(f"No baseline model at {baseline_path}, skipping comparison")
        return None

    model = SpectralGNN(
        in_channels=in_channels,
        hidden_channels=hidden,
        out_channels=1,
        model_type=model_type,
    ).to(device)
    state = torch.load(baseline_path, weights_only=False)
    # Handle both raw state_dict and wrapped dict
    if isinstance(state, dict) and "model_state_dict" in state:
        model.load_state_dict(state["model_state_dict"])
    else:
        model.load_state_dict(state)
    logger.info(f"Loaded baseline model from {baseline_path}")
    return model


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Stratified sampling for balanced spectral gap training"
    )
    parser.add_argument(
        "--num-bins", type=int, default=5, help="Number of spectral gap bins"
    )
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--model", type=str, choices=["gcn", "gat"], default="gat")
    parser.add_argument(
        "--curriculum", action="store_true", help="Enable curriculum learning"
    )
    parser.add_argument(
        "--reweight-power",
        type=float,
        default=0.5,
        help="Power for reweighting (0=off, 0.5=sqrt, 1.0=inverse)",
    )
    parser.add_argument(
        "--baseline-hidden",
        type=int,
        default=64,
        help="Hidden dim of baseline model (for loading)",
    )
    parser.add_argument(
        "--log-interval", type=int, default=10, help="Log every N epochs"
    )
    args = parser.parse_args()

    # Load data
    train_data = load_augmented_dataset("spectral_gap", split="train")
    test_data = load_augmented_dataset("spectral_gap", split="test")
    logger.info(f"Train: {len(train_data)} samples, Test: {len(test_data)} samples")

    if len(train_data) == 0:
        logger.error("No training data. Run augment_dataset.py first.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Compute bin boundaries from training data for consistent evaluation
    y_values = torch.tensor(
        [d.y.item() if d.y.numel() == 1 else d.y[0].item() for d in train_data],
        dtype=torch.float32,
    )
    quantiles = torch.linspace(0, 1, args.num_bins + 1)
    boundaries = torch.quantile(y_values, quantiles)
    boundaries[0] = -math.inf
    boundaries[-1] = math.inf

    logger.info(f"Spectral gap range: [{y_values.min():.4f}, {y_values.max():.4f}]")
    logger.info(f"Train bin boundaries: {boundaries.tolist()}")

    # Log test data distribution relative to train bins
    test_y = torch.tensor(
        [d.y.item() if d.y.numel() == 1 else d.y[0].item() for d in test_data],
        dtype=torch.float32,
    )
    logger.info(f"Test spectral gap range: [{test_y.min():.4f}, {test_y.max():.4f}]")
    for b in range(args.num_bins):
        lo, hi = boundaries[b].item(), boundaries[b + 1].item()
        if b < args.num_bins - 1:
            n = ((test_y >= lo) & (test_y < hi)).sum().item()
        else:
            n = ((test_y >= lo) & (test_y <= hi)).sum().item()
        logger.info(f"  Test Bin {b}: [{lo:.4f}, {hi:.4f})  n={n}")

    # Loss function
    if args.reweight_power > 0:
        loss_fn = ReweightedMSELoss(train_data, args.num_bins, args.reweight_power)
    else:
        loss_fn = F.mse_loss
        logger.info("Using standard MSE loss (no reweighting)")

    # Curriculum scheduler
    curriculum = (
        CurriculumScheduler(args.epochs, args.num_bins) if args.curriculum else None
    )
    if curriculum:
        logger.info("Curriculum learning enabled")

    # Model
    in_channels = train_data[0].x.shape[1]
    model = SpectralGNN(
        in_channels=in_channels,
        hidden_channels=args.hidden,
        out_channels=1,
        model_type=args.model,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Model: SpectralGNN ({args.model}, in={in_channels}, hidden={args.hidden}, params={total_params:,})"
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-5
    )

    # Training loop
    logger.info(f"Training with stratified sampling for {args.epochs} epochs")
    best_test_r2 = float("-inf")

    for epoch in range(1, args.epochs + 1):
        # Determine active bins (curriculum)
        if curriculum:
            active_bins = curriculum.get_active_bins(epoch)
        else:
            active_bins = None

        # Create batch sampler for this epoch
        batch_sampler = BinBalancedBatchSampler(
            train_data,
            num_bins=args.num_bins,
            batch_size=args.batch_size,
            shuffle=True,
            active_bins=active_bins,
        )

        # Build index map: batch_idx → list of dataset indices
        epoch_indices = {i: batch for i, batch in enumerate(batch_sampler.batches)}

        # Create DataLoader with the batch sampler
        train_loader = DataLoader(train_data, batch_sampler=batch_sampler)

        epoch_loss = train_epoch(
            model, train_loader, optimizer, device, loss_fn, epoch_indices
        )
        scheduler.step()

        # Evaluate periodically
        if epoch % args.log_interval == 0 or epoch == 1:
            results = evaluate_per_bin(
                model, test_data, device, args.num_bins, boundaries
            )
            o = results["overall"]
            logger.info(
                f"Epoch {epoch:3d} | Train Loss: {epoch_loss:.4f} | "
                f"Test MAE: {o['mae']:.4f} | RMSE: {o['rmse']:.4f} | R²: {o['r2']:.4f}"
            )
            # Per-bin MAE
            bin_str = "  ".join(
                f"Bin{r['bin']}({r['n']:2d}):{r['mae']:.4f}"
                for r in results["per_bin"]
                if r.get("n", 0) > 0
            )
            logger.info(f"  Per-bin MAE: {bin_str}")

            if o["r2"] > best_test_r2:
                best_test_r2 = o["r2"]

    # Final evaluation
    logger.info("=" * 70)
    logger.info("Final evaluation (stratified model):")
    results = evaluate_per_bin(model, test_data, device, args.num_bins, boundaries)
    o = results["overall"]
    logger.info(
        f"  Overall: MAE={o['mae']:.4f}, RMSE={o['rmse']:.4f}, R²={o['r2']:.4f}"
    )
    for r in results["per_bin"]:
        if r.get("n", 0) > 0:
            logger.info(
                f"  Bin {r['bin']} {r['range']:20s}  n={r['n']:3d}  "
                f"MAE={r['mae']:.4f}  MSE={r['mse']:.4f}"
            )

    # Save model (before baseline comparison to avoid crash losing results)
    model_path = MODEL_DIR / "stratified_spectral_gap.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": {
                "in_channels": in_channels,
                "hidden_channels": args.hidden,
                "model_type": args.model,
                "num_bins": args.num_bins,
                "reweight_power": args.reweight_power,
                "curriculum": args.curriculum,
            },
            "test_r2": o["r2"],
            "test_mae": o["mae"],
            "best_test_r2": best_test_r2,
        },
        model_path,
    )
    logger.success(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
