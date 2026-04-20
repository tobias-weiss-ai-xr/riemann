"""
Multi-task GNN training for spectral prediction on SL(2,F_p) Cayley graphs.

Architecture: shared GIN encoder with 5 task-specific prediction heads
and uncertainty-weighted multi-task loss (Kendall et al. 2018).

Tasks:
    1. spectral_gap       (primary)   — from augmented y
    2. algebraic_conn     (auxiliary) — 4 - λ₂ (from eigenvalue .npy)
    3. spectral_radius    (auxiliary) — max|λ| nontrivial (from .npz)
    4. log_num_nodes      (auxiliary) — log(num_nodes) per sample
    5. eigenvalue_ratio   (auxiliary) — ramanujan_ratio (from .npz)

Usage:
    python train_multitask.py --augmented --epochs 200 --batch-size 32 --hidden 128 --lr 1e-3
    python train_multitask.py --epochs 100 --train-primes 2-50 --test-primes 53-101
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger
from torch_geometric.data import Data, DataLoader
from torch_geometric.nn import GINConv, global_max_pool, global_mean_pool
from torch_geometric.nn.norm import BatchNorm

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_DIR = DATA_DIR / "cayley-graphs"
EIGEN_DIR = DATA_DIR / "eigenvalues"
AUG_DIR = DATA_DIR / "augmented"

TASK_NAMES = [
    "spectral_gap",
    "algebraic_conn",
    "spectral_radius",
    "log_num_nodes",
    "eigenvalue_ratio",
]
NUM_TASKS = len(TASK_NAMES)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class MultiTaskSpectralGNN(nn.Module):
    """Shared GIN encoder + 5 task heads with learnable uncertainty weighting."""

    def __init__(
        self,
        in_channels: int = 3,
        hidden_dim: int = 128,
        num_layers: int = 4,
        num_tasks: int = NUM_TASKS,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_tasks = num_tasks

        # Input projection
        self.input_proj = nn.Linear(in_channels, hidden_dim)

        # Shared GIN encoder
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for _ in range(num_layers):
            nn_mlp = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            )
            self.convs.append(GINConv(nn_mlp))
            self.norms.append(BatchNorm(hidden_dim))

        # Task-specific heads (input: 2*hidden_dim from dual pooling)
        head_in = hidden_dim * 2
        self.spectral_gap_head = nn.Sequential(
            nn.Linear(head_in, 64), nn.ReLU(), nn.Linear(64, 1)
        )
        self.algebraic_conn_head = nn.Sequential(
            nn.Linear(head_in, 64), nn.ReLU(), nn.Linear(64, 1)
        )
        self.spectral_radius_head = nn.Sequential(
            nn.Linear(head_in, 64), nn.ReLU(), nn.Linear(64, 1)
        )
        self.log_num_nodes_head = nn.Sequential(
            nn.Linear(head_in, 32), nn.ReLU(), nn.Linear(32, 1)
        )
        self.eigenvalue_ratio_head = nn.Sequential(
            nn.Linear(head_in, 64), nn.ReLU(), nn.Linear(64, 1)
        )

        self.heads = [
            self.spectral_gap_head,
            self.algebraic_conn_head,
            self.spectral_radius_head,
            self.log_num_nodes_head,
            self.eigenvalue_ratio_head,
        ]

        # Learnable log-variance for uncertainty weighting (Kendall 2018)
        self.log_vars = nn.Parameter(torch.zeros(num_tasks))

    def forward(
        self, x: torch.Tensor, edge_index: torch.Tensor, batch: torch.Tensor
    ) -> dict[str, torch.Tensor]:
        # Input projection
        h = self.input_proj(x)

        # GIN layers with BatchNorm + residual
        for conv, norm in zip(self.convs, self.norms):
            h_new = conv(h, edge_index)
            h_new = norm(h_new)
            h_new = F.relu(h_new)
            h = h + h_new  # residual connection

        # Dual pooling
        h_mean = global_mean_pool(h, batch)
        h_max = global_max_pool(h, batch)
        graph_emb = torch.cat([h_mean, h_max], dim=1)  # (batch, 2*hidden_dim)

        # Task predictions
        predictions = {}
        for name, head in zip(TASK_NAMES, self.heads):
            predictions[name] = head(graph_emb)

        return predictions

    def compute_loss(
        self, predictions: dict[str, torch.Tensor], targets: torch.Tensor
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """Uncertainty-weighted multi-task loss.

        L = Σ_i (1/(2σ_i²)) * L_i + log(σ_i)
        where σ_i = exp(log_vars[i]).
        """
        total = torch.tensor(0.0, device=targets.device)
        per_task = {}
        for i, name in enumerate(TASK_NAMES):
            task_loss = F.mse_loss(predictions[name].squeeze(-1), targets[:, i])
            precision = torch.exp(-self.log_vars[i])
            total = total + precision * task_loss + self.log_vars[i]
            per_task[name] = task_loss.item()
        return total, per_task


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_multitask_augmented(split: str = "train") -> list[Data]:
    """Load augmented dataset and attach multi-task targets.

    For each sample, extracts the parent prime from the filename,
    loads eigenvalue data, and constructs a 5-dim target vector.
    """
    split_dir = AUG_DIR / split
    if not split_dir.exists():
        raise FileNotFoundError(
            f"Augmented dataset not found at {split_dir}. "
            f"Run augment_dataset.py --all first."
        )

    dataset = []
    skipped = 0

    for pt_file in sorted(split_dir.glob("*.pt")):
        data = torch.load(pt_file, weights_only=False)

        # Extract parent prime from filename: p{N}_fundamental_... or p{N}_root_weyl_...
        m = re.match(r"p(\d+)", pt_file.stem)
        if m is None:
            skipped += 1
            continue
        prime = int(m.group(1))

        # Load eigenvalue stats (.npz) and eigenvalues (.npy)
        stats_path = EIGEN_DIR / f"sl2fp_p{prime}_stats.npz"
        eigs_path = EIGEN_DIR / f"sl2fp_p{prime}_eigenvalues.npy"

        if not stats_path.exists():
            skipped += 1
            continue

        stats = dict(np.load(stats_path))
        stats = {k: float(v) for k, v in stats.items()}

        # Compute 5 targets
        spectral_gap = float(data.y.item()) if data.y.numel() == 1 else float(data.y[0])

        # Algebraic connectivity: d - λ₂ (second-largest adj eigenvalue)
        if eigs_path.exists():
            eigenvalues = np.load(eigs_path)
            if len(eigenvalues) >= 2:
                # eigenvalues sorted descending; λ₁ = d = 4 (trivial)
                algebraic_conn = 4.0 - eigenvalues[1]
            else:
                algebraic_conn = 0.0
        else:
            algebraic_conn = 0.0

        # Spectral radius: max |λ| of nontrivial eigenvalues
        spectral_radius = stats.get("max_abs_eigenvalue", 0.0)

        # Log num nodes
        log_num_nodes = np.log(max(data.num_nodes, 1))

        # Eigenvalue ratio (ramanujan_ratio)
        eigenvalue_ratio = stats.get("ramanujan_ratio", 0.0)

        y = torch.tensor(
            [
                spectral_gap,
                algebraic_conn,
                spectral_radius,
                log_num_nodes,
                eigenvalue_ratio,
            ],
            dtype=torch.float32,
        )

        # Strip non-tensor attributes (same as train_gnn.py)
        keys_to_remove = [
            k
            for k in data.keys()
            if not isinstance(data[k], torch.Tensor) and k != "num_nodes"
        ]
        for k in keys_to_remove:
            del data[k]

        data.y = y
        dataset.append(data)

    logger.info(
        f"Loaded {len(dataset)} multitask samples from {split_dir.name}/ "
        f"(skipped {skipped}, in_channels={dataset[0].x.shape[1] if dataset else '?'})"
    )
    return dataset


def load_multitask_full(primes: list[int]) -> list[Data]:
    """Load full graphs (non-augmented) with multi-task targets."""
    dataset = []
    for p in primes:
        pt_path = GRAPH_DIR / f"sl2fp_p{p}.pt"
        if not pt_path.exists():
            logger.warning(f"Skipping p={p}: no graph file")
            continue

        data = torch.load(pt_path, weights_only=False)

        stats_path = EIGEN_DIR / f"sl2fp_p{p}_stats.npz"
        eigs_path = EIGEN_DIR / f"sl2fp_p{p}_eigenvalues.npy"

        if not stats_path.exists():
            logger.warning(f"Skipping p={p}: no eigenvalue stats")
            continue

        stats = dict(np.load(stats_path))
        stats = {k: float(v) for k, v in stats.items()}

        spectral_gap = stats.get("spectral_gap", 0.0)

        algebraic_conn = 0.0
        if eigs_path.exists():
            eigenvalues = np.load(eigs_path)
            if len(eigenvalues) >= 2:
                algebraic_conn = 4.0 - eigenvalues[1]

        spectral_radius = stats.get("max_abs_eigenvalue", 0.0)
        log_num_nodes = np.log(max(data.num_nodes, 1))
        eigenvalue_ratio = stats.get("ramanujan_ratio", 0.0)

        data.y = torch.tensor(
            [
                spectral_gap,
                algebraic_conn,
                spectral_radius,
                log_num_nodes,
                eigenvalue_ratio,
            ],
            dtype=torch.float32,
        )
        dataset.append(data)

    logger.info(f"Loaded {len(dataset)} full graphs")
    return dataset


# ---------------------------------------------------------------------------
# Training / evaluation
# ---------------------------------------------------------------------------


def train_epoch(
    model: MultiTaskSpectralGNN,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> tuple[float, dict[str, float]]:
    model.train()
    total_loss = 0.0
    total_graphs = 0
    all_per_task = {name: 0.0 for name in TASK_NAMES}

    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        predictions = model(data.x, data.edge_index, data.batch)
        targets = data.y.view(-1, NUM_TASKS)
        loss, per_task = model.compute_loss(predictions, targets)
        loss.backward()
        optimizer.step()

        n = data.num_graphs
        total_loss += loss.item() * n
        total_graphs += n
        for name in TASK_NAMES:
            all_per_task[name] += per_task[name] * n

    avg_loss = total_loss / max(total_graphs, 1)
    avg_per_task = {name: v / max(total_graphs, 1) for name, v in all_per_task.items()}
    return avg_loss, avg_per_task


@torch.no_grad()
def evaluate(
    model: MultiTaskSpectralGNN,
    loader: DataLoader,
    device: torch.device,
) -> tuple[float, dict[str, float], dict[str, float]]:
    """Evaluate model. Returns (avg_loss, per_task_mse, per_task_r2)."""
    model.eval()
    total_loss = 0.0
    total_graphs = 0

    all_preds = {name: [] for name in TASK_NAMES}
    all_targets = {name: [] for name in TASK_NAMES}

    for data in loader:
        data = data.to(device)
        predictions = model(data.x, data.edge_index, data.batch)
        targets = data.y.view(-1, NUM_TASKS)
        loss, _ = model.compute_loss(predictions, targets)

        n = data.num_graphs
        total_loss += loss.item() * n
        total_graphs += n

        for i, name in enumerate(TASK_NAMES):
            all_preds[name].append(predictions[name].squeeze(-1).cpu())
            all_targets[name].append(targets[:, i].cpu())

    avg_loss = total_loss / max(total_graphs, 1)

    per_task_mse = {}
    per_task_r2 = {}
    for name in TASK_NAMES:
        pred = torch.cat(all_preds[name])
        target = torch.cat(all_targets[name])
        mse = F.mse_loss(pred, target).item()
        per_task_mse[name] = mse

        # R² = 1 - SS_res / SS_tot
        ss_res = ((target - pred) ** 2).sum().item()
        ss_tot = ((target - target.mean()) ** 2).sum().item()
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
        per_task_r2[name] = r2

    return avg_loss, per_task_mse, per_task_r2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_primes(spec: str) -> list[int]:
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return [
            p
            for p in range(int(lo), int(hi) + 1)
            if p >= 2 and all(p % d for d in range(2, int(p**0.5) + 1))
        ]
    return [int(x.strip()) for x in spec.split(",")]


def main():
    parser = argparse.ArgumentParser(
        description="Multi-task GNN training for spectral prediction"
    )
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--num-layers", type=int, default=4)
    parser.add_argument(
        "--augmented",
        action="store_true",
        help="Load augmented dataset from data/augmented/",
    )
    parser.add_argument(
        "--train-primes", type=str, default="2-50", help="Primes for training"
    )
    parser.add_argument(
        "--test-primes", type=str, default="53-101", help="Primes for testing"
    )
    parser.add_argument(
        "--log-interval", type=int, default=10, help="Log every N epochs"
    )
    args = parser.parse_args()

    # Load data
    if args.augmented:
        train_data = load_multitask_augmented(split="train")
        test_data = load_multitask_augmented(split="test")
        logger.info(f"Train: {len(train_data)} samples, Test: {len(test_data)} samples")
    else:
        train_primes = parse_primes(args.train_primes)
        test_primes = parse_primes(args.test_primes)
        logger.info(f"Train primes: {train_primes}")
        logger.info(f"Test primes: {test_primes}")
        train_data = load_multitask_full(train_primes)
        test_data = load_multitask_full(test_primes)

    if len(train_data) == 0:
        logger.error("No training data. Run augment_dataset.py first.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True)
    test_loader = DataLoader(test_data, batch_size=args.batch_size, shuffle=False)

    # Model
    in_channels = train_data[0].x.shape[1]
    model = MultiTaskSpectralGNN(
        in_channels=in_channels,
        hidden_dim=args.hidden,
        num_layers=args.num_layers,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Model: MultiTaskSpectralGNN (in={in_channels}, hidden={args.hidden}, "
        f"layers={args.num_layers}, params={total_params:,})"
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs, eta_min=1e-5
    )

    # Training loop
    logger.info(f"Training for {args.epochs} epochs")
    best_test_loss = float("inf")

    for epoch in range(1, args.epochs + 1):
        train_loss, train_per_task = train_epoch(model, train_loader, optimizer, device)
        scheduler.step()

        test_loss, test_per_task_mse, test_r2 = evaluate(model, test_loader, device)

        if test_loss < best_test_loss:
            best_test_loss = test_loss

        if epoch % args.log_interval == 0 or epoch == 1:
            # Learned uncertainties (σ² = exp(2*log_var))
            sigmas = torch.exp(model.log_vars).detach().cpu()
            sigma_str = ", ".join(
                f"{name}={s:.4f}" for name, s in zip(TASK_NAMES, sigmas)
            )

            task_loss_str = ", ".join(
                f"{name}={v:.4f}" for name, v in train_per_task.items()
            )
            r2_str = ", ".join(f"{name}={v:.4f}" for name, v in test_r2.items())

            logger.info(
                f"Epoch {epoch:3d} | Train: {train_loss:.4f} [{task_loss_str}] "
                f"| Test: {test_loss:.4f} | R²: [{r2_str}]"
            )
            logger.debug(f"  σ²: [{sigma_str}]")

    # Final evaluation
    logger.info("=" * 60)
    logger.info("Final evaluation:")
    test_loss, test_mse, test_r2 = evaluate(model, test_loader, device)
    for name in TASK_NAMES:
        logger.info(f"  {name:20s}: MSE={test_mse[name]:.6f}, R²={test_r2[name]:.4f}")

    # Learned uncertainties
    sigmas = torch.exp(model.log_vars).detach().cpu()
    logger.info("Learned uncertainties (σ²):")
    for name, s in zip(TASK_NAMES, sigmas):
        logger.info(f"  {name:20s}: σ²={s:.4f}")

    # Save model
    model_path = DATA_DIR / "models" / "multitask_spectral.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "config": {
                "in_channels": in_channels,
                "hidden_dim": args.hidden,
                "num_layers": args.num_layers,
                "num_tasks": NUM_TASKS,
                "task_names": TASK_NAMES,
            },
            "test_r2": test_r2,
            "test_mse": test_mse,
            "best_test_loss": best_test_loss,
        },
        model_path,
    )
    logger.success(f"Model saved to {model_path}")


if __name__ == "__main__":
    main()
