"""
Train stacking ensemble combining GNN embeddings and sklearn predictions.

Combines:
- GNN: 256-dim embeddings from trained ChebConv K=5 (z1, rank, cm)
- Sklearn: RandomForest predictions for rank (96% acc) and cm (100% acc)
- z1: GNN-only (sklearn baseline not available in LMFDB ML dataset)

Usage:
    python scripts/train_ensemble.py --target rank
    python scripts/train_ensemble.py --target cm
    python scripts/train_ensemble.py --target all
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from loguru import logger
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import StratifiedKFold

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"

# ---------------------------------------------------------------------------
# Configure loguru
# ---------------------------------------------------------------------------

logger.remove()
logger.add(
    __import__("sys").stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)


# ---------------------------------------------------------------------------
# Weighted focal loss for rank-2 rare class
# ---------------------------------------------------------------------------

class FocalLoss(nn.Module):
    """Focal loss ignoring -1 labels (missing sklearn predictions)."""

    def __init__(self, num_classes: int = 3, gamma: float = 2.0, class_weights: list[float] | None = None):
        super().__init__()
        self.num_classes = num_classes
        self.gamma = gamma
        if class_weights is None:
            # Emphasize rank-2 (rare: 1.5% in full dataset)
            class_weights = [1.0, 1.0, 8.0]
        self.register_buffer("class_weights", torch.tensor(class_weights, dtype=torch.float32))

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Args:
            logits: (N, num_classes)
            targets: (N,) with values {0, 1, 2}
        Returns:
            Scalar focal loss
        """
        # Cross-entropy loss
        ce_loss = nn.functional.cross_entropy(logits, targets, reduction='none', weight=self.class_weights)

        # Focal term: (1 - p_t)^gamma
        probs = torch.softmax(logits, dim=1)
        pt = probs[torch.arange(len(targets)), targets]
        focal_term = (1.0 - pt) ** self.gamma

        return (focal_term * ce_loss).mean()


# ---------------------------------------------------------------------------
# Ensemble models
# ---------------------------------------------------------------------------

class EnsembleRegressor(nn.Module):
    """Stacking ensemble for regression (z1 target)."""

    def __init__(self, gnn_dim: int = 256):
        super().__init__()
        self.gnn_dim = gnn_dim
        self.meta = nn.Sequential(
            nn.Linear(gnn_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

    def forward(self, gnn_embeddings: torch.Tensor) -> torch.Tensor:
        """
        Args:
            gnn_embeddings: (N, 256)
        Returns:
            (N,) predictions
        """
        return self.meta(gnn_embeddings).squeeze(1)


class EnsembleClassifier(nn.Module):
    """Stacking ensemble for classification (rank, cm)."""

    def __init__(self, gnn_dim: int = 256, sklearn_dim: int = 0, num_classes: int = 3):
        super().__init__()
        input_dim = gnn_dim + sklearn_dim
        self.sklearn_dim = sklearn_dim
        self.num_classes = num_classes

        # If sklearn predictions available, concat them
        self.use_sklearn = sklearn_dim > 0

        layers = []
        for i, (in_d, out_d) in enumerate([(input_dim, 128), (128, 64), (64, num_classes)]):
            layers.append(nn.Linear(in_d, out_d))
            if i < len([(input_dim, 128), (128, 64), (64, num_classes)]) - 1:
                layers.append(nn.ReLU())
                layers.append(nn.Dropout(0.2))
        self.meta = nn.Sequential(*layers)

    def forward(self, gnn_embeddings: torch.Tensor, sklearn_preds: torch.Tensor | None = None) -> torch.Tensor:
        """
        Args:
            gnn_embeddings: (N, 256)
            sklearn_preds: (N, num_classes) if use_sklearn else None
        Returns:
            (N, num_classes) logits
        """
        if self.use_sklearn and sklearn_preds is not None:
            x = torch.cat([gnn_embeddings, sklearn_preds], dim=1)
        else:
            x = gnn_embeddings
        return self.meta(x)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_epoch(
    model: nn.Module,
    gnn_emb: torch.Tensor,
    targets: torch.Tensor,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    sklearn_preds: torch.Tensor | None = None,
) -> float:
    """Train ensemble meta-learner for one epoch."""
    model.train()
    optimizer.zero_grad()

    if isinstance(model, EnsembleClassifier):
        logits = model(gnn_emb, sklearn_preds)
        loss = criterion(logits, targets)
    else:
        preds = model(gnn_emb)
        loss = criterion(preds, targets)

    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    return loss.item()


@torch.no_grad()
def evaluate(
    model: nn.Module,
    gnn_emb: torch.Tensor,
    targets: torch.Tensor,
    task_type: str,
    sklearn_preds: torch.Tensor | None = None,
) -> tuple[float, np.ndarray]:
    """Evaluate meta-learner on test data."""
    model.eval()
    if isinstance(model, EnsembleClassifier):
        logits = model(gnn_emb, sklearn_preds)
        loss = nn.functional.cross_entropy(logits, targets)
        preds = logits.argmax(dim=1).cpu().numpy()
    else:
        preds = model(gnn_emb)
        loss = nn.functional.mse_loss(preds, targets)
        preds = preds.cpu().numpy()

    return loss.item(), preds, targets.cpu().numpy()


# ---------------------------------------------------------------------------
# Load pretrained GNN embeddings and sklearn predictions
# ---------------------------------------------------------------------------

def load_gnn_predictions(target: str, data_dir: Path) -> dict:
    """Load GNN embeddings, predictions, and ground truth."""
    emb_path = data_dir / f"gnn_embeddings_{target}.npy"
    pred_path = data_dir / f"gnn_raw_preds_{target}.npy"
    targets_path = data_dir / f"gnn_targets_{target}.npy"

    if not all(p.exists() for p in [emb_path, pred_path, targets_path]):
        raise FileNotFoundError(
            f"Missing GNN export files for {target}. "
            f"Run extract_gnn_embeddings.py first."
        )

    return {
        "embeddings": np.load(emb_path),
        "predictions": np.load(pred_path),
        "targets": np.load(targets_path),
    }


def load_sklearn_predictions(target: str, data_dir: Path) -> np.ndarray:
    """Load sklearn predictions as probability vectors (from predict_proba)."""
    pred_path = data_dir / f"sklearn_preds_{target}.npy"

    if not pred_path.exists():
        # No sklearn baseline for z1
        if target == "z1":
            return None
        raise FileNotFoundError(f"Missing sklearn predictions for {target}")

    preds = np.load(pred_path)

    # Already in probability format from predict_proba()
    return preds.astype(np.float32)


# ---------------------------------------------------------------------------
# Train ensemble for single target
# ---------------------------------------------------------------------------

def train_single_target(
    target: str,
    data_dir: Path,
    output_dir: Path,
    epochs: int = 100,
    lr: float = 1e-3,
    use_focal_loss: bool = False,
) -> dict:
    """Train ensemble meta-learner for one target."""
    print(f"\n{'='*80}")
    print(f"Ensemble Training: {target.upper()}")
    print(f"{'='*80}\n")

    # Load data
    logger.info(f"Loading GNN data for {target}")
    gnn_data = load_gnn_predictions(target, data_dir)
    gnn_emb = torch.from_numpy(gnn_data["embeddings"]).float()
    # Use float for regression (z1), long for classification
    targets_dtype = torch.float if target == "z1" else torch.long
    targets = torch.from_numpy(gnn_data["targets"]).to(targets_dtype)

    # sklearn predictions
    sklearn_preds = load_sklearn_predictions(target, data_dir)
    use_sklearn = sklearn_preds is not None
    if use_sklearn:
        sklearn_preds = torch.from_numpy(sklearn_preds).float()
        logger.info(f"  Sklearn predictions available: {sklearn_preds.shape}")
    else:
        logger.info(f"  No sklearn predictions (GNN-only ensemble)")

    n_samples = len(gnn_emb)
    logger.info(f"  Samples: {n_samples}, GNN emb dim: {gnn_emb.shape[1]}")

    # Split for validation
    if targets.dim() == 1 and target in ["rank", "cm"]:
        # Stratified split for classification
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        val_idx = list(skf.split(gnn_emb.numpy(), targets.numpy()))[0][1]
    else:
        # Random split for regression
        n_val = n_samples // 5
        val_idx = torch.randperm(n_samples)[:n_val].numpy()

    train_idx = np.array([i for i in range(n_samples) if i not in set(val_idx)])

    gnn_train, gnn_val = gnn_emb[train_idx], gnn_emb[val_idx]
    targets_train, targets_val = targets[train_idx], targets[val_idx]
    if use_sklearn:
        sklearn_train, sklearn_val = sklearn_preds[train_idx], sklearn_preds[val_idx]
    else:
        sklearn_train = sklearn_val = None

    logger.info(f"  Train: {len(train_idx)}, Val: {len(val_idx)}")

    # Build model
    if target == "z1":
        model = EnsembleRegressor(gnn_dim=256)
        criterion = nn.MSELoss()
        task_type = "regression"
        num_classes = 1
    else:
        num_classes = {"rank": 3, "cm": 2}[target]
        sklearn_dim = sklearn_preds.shape[1] if use_sklearn else 0
        model = EnsembleClassifier(gnn_dim=256, sklearn_dim=sklearn_dim, num_classes=num_classes)
        if target == "rank" and use_focal_loss:
            criterion = FocalLoss(num_classes=num_classes, gamma=2.0)
            logger.info(f"  Using focal loss for rank-2 rare class")
        else:
            criterion = nn.CrossEntropyLoss()
        task_type = "classification"

    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    # Training loop
    best_val_loss = float("inf")
    best_state = None
    patience = 15
    epochs_no_improve = 0

    logger.info(f"Training ensemble meta-learner ({epochs} epochs, patience={patience})")

    for epoch in range(1, epochs + 1):
        # Train
        train_loss = train_epoch(
            model, gnn_train, targets_train, optimizer, criterion, sklearn_train
        )

        # Val
        if isinstance(model, EnsembleClassifier):
            val_loss, _, _ = evaluate(model, gnn_val, targets_val, "classification", sklearn_val)
        else:
            val_loss, _, _ = evaluate(model, gnn_val, targets_val, "regression")

        if epoch % 10 == 0 or epoch == 1:
            logger.info(f"  Epoch {epoch:3d}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= patience:
            logger.info(f"  Early stopping at epoch {epoch}")
            break

    # Load best
    if best_state is not None:
        model.load_state_dict(best_state)

    # Evaluate on val & full
    logger.info("\nValidation metrics:")
    if isinstance(model, EnsembleClassifier):
        val_loss, val_preds, val_targets = evaluate(model, gnn_val, targets_val, "classification", sklearn_val)
        val_acc = accuracy_score(val_targets, val_preds)
        val_f1 = f1_score(val_targets, val_preds, average="macro", zero_division=0)
        logger.info(f"  Loss: {val_loss:.4f} | Accuracy: {val_acc:.4f} | F1 (macro): {val_f1:.4f}")
        metrics = {"val_loss": float(val_loss), "val_acc": float(val_acc), "val_f1_macro": float(val_f1)}
    else:
        val_loss, val_preds, val_targets = evaluate(model, gnn_val, targets_val, "regression")
        val_r2 = r2_score(val_targets, val_preds)
        val_mae = mean_absolute_error(val_targets, val_preds)
        logger.info(f"  Loss: {val_loss:.4f} | MAE: {val_mae:.4f} | R²: {val_r2:.4f}")
        metrics = {"val_loss": float(val_loss), "val_mae": float(val_mae), "val_r2": float(val_r2)}

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = output_dir / f"ensemble_{target}.pt"
    torch.save(
        {
            "model_state_dict": best_state,
            "config": {
                "target": target,
                "gnn_dim": 256,
                "sklearn_dim": sklearn_preds.shape[1] if use_sklearn else 0,
                "num_classes": num_classes if task_type == "classification" else 1,
                "focal_loss": use_focal_loss and target == "rank",
            },
        },
        ckpt_path,
    )
    logger.info(f"\nSaved ensemble: {ckpt_path}")

    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train GNN+sklearn stacking ensemble")
    parser.add_argument("--target", choices=["z1", "rank", "cm", "all"], default="all")
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--use-focal-loss", action="store_true", help="Use focal loss for rank-2")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else MODEL_DIR
    output_dir = Path(args.output_dir) if args.output_dir else MODEL_DIR

    targets = ["z1", "rank", "cm"] if args.target == "all" else [args.target]

    all_metrics = {}
    for target in targets:
        metrics = train_single_target(
            target=target,
            data_dir=data_dir,
            output_dir=output_dir,
            epochs=args.epochs,
            lr=args.lr,
            use_focal_loss=args.use_focal_loss,
        )
        all_metrics[target] = metrics
        print()

    # Summary
    print(f"\n{'='*80}")
    print("ENSEMBLE TRAINING SUMMARY")
    print(f"{'='*80}")
    for target, metrics in all_metrics.items():
        print(f"\n{target.upper()}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()