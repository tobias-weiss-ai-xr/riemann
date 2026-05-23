"""
Evaluate ensemble models on GNN test set.

Computes metrics for standalone models (GNN, sklearn, ensemble) to compare.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

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
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)


# ---------------------------------------------------------------------------
# Load utils
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


def load_ensemble_model(target: str, data_dir: Path) -> dict:
    """Load trained ensemble model."""
    ckpt_path = data_dir / f"ensemble_{target}.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Missing ensemble checkpoint: {ckpt_path}")

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    return ckpt


def load_sklearn_predictions(target: str, data_dir: Path) -> np.ndarray:
    """Load sklearn predictions as one-hot vectors."""
    pred_path = data_dir / f"sklearn_preds_{target}.npy"
    if not pred_path.exists():
        return None

    preds = np.load(pred_path)
    n_samples = preds.shape[0]
    n_classes = {"rank": 3, "cm": 2}[target]
    one_hot = np.zeros((n_samples, n_classes), dtype=np.float32)
    one_hot[np.arange(n_samples), preds.astype(int)] = 1.0
    return one_hot


# ---------------------------------------------------------------------------
# Model definitions (must match train_ensemble.py)
# ---------------------------------------------------------------------------

class EnsembleClassifier(torch.nn.Module):
    def __init__(self, gnn_dim: int = 256, sklearn_dim: int = 0, num_classes: int = 3):
        super().__init__()
        self.sklearn_dim = sklearn_dim
        self.num_classes = num_classes
        input_dim = gnn_dim + sklearn_dim

        layers = []
        dims = [(input_dim, 128), (128, 64), (64, num_classes)]
        for i, (in_d, out_d) in enumerate(dims):
            layers.append(torch.nn.Linear(in_d, out_d))
            if i < len(dims) - 1:
                layers.append(torch.nn.ReLU())
                layers.append(torch.nn.Dropout(0.2))
        self.meta = torch.nn.Sequential(*layers)

    def forward(self, gnn_embeddings: torch.Tensor, sklearn_preds: torch.Tensor = None):
        if self.sklearn_dim > 0 and sklearn_preds is not None:
            x = torch.cat([gnn_embeddings, sklearn_preds], dim=1)
        else:
            x = gnn_embeddings
        return self.meta(x)


class EnsembleRegressor(torch.nn.Module):
    def __init__(self, gnn_dim: int = 256):
        super().__init__()
        self.meta = torch.nn.Sequential(
            torch.nn.Linear(gnn_dim, 128),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(128, 64),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(64, 1),
        )

    def forward(self, gnn_embeddings: torch.Tensor):
        return self.meta(gnn_embeddings).squeeze(1)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_regression_metrics(preds, targets):
    mse = mean_squared_error(targets, preds)
    mae = mean_absolute_error(targets, preds)
    r2 = r2_score(targets, preds)
    return {"mse": mse, "mae": mae, "r2": r2}


def compute_classification_metrics(preds, targets):
    from sklearn.metrics import confusion_matrix

    acc = accuracy_score(targets, preds)
    f1_mac = f1_score(targets, preds, average="macro", zero_division=0)
    f1_wt = f1_score(targets, preds, average="weighted", zero_division=0)
    classes = sorted(np.unique(targets).astype(int))
    per_class_f1 = {}
    for c in classes:
        per_class_f1[c] = f1_score(
            (targets == c).astype(int), (preds == c).astype(int), zero_division=0
        )

    # Confusion matrix
    cm = confusion_matrix(targets, preds, labels=classes)

    return {
        "accuracy": acc,
        "f1_macro": f1_mac,
        "f1_weighted": f1_wt,
        "per_class_f1": per_class_f1,
        "classes": classes,
        "confusion_matrix": cm.tolist(),
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

@torch.no_grad()
def evaluate_ensemble(
    target: str, gnn_data: dict, sklearn_preds: np.ndarray | None, model: torch.nn.Module
) -> dict:
    """Evaluate ensemble predictions."""
    gnn_emb = torch.from_numpy(gnn_data["embeddings"]).float()
    targets = gnn_data["targets"]

    if sklearn_preds is not None:
        sklearn_t = torch.from_numpy(sklearn_preds).float()
        logits = model(gnn_emb, sklearn_t)
    else:
        logits = model(gnn_emb)

    if target == "z1":
        preds = logits.numpy()
        metrics = compute_regression_metrics(preds, targets)
    else:
        preds = logits.argmax(dim=1).numpy()
        targets_np = targets.astype(int)
        metrics = compute_classification_metrics(preds, targets_np)

    return {"metrics": metrics, "predictions": preds, "targets": targets_np if target != "z1" else None}


def evaluate_gnn_only(target: str, gnn_data: dict) -> dict:
    """Evaluate GNN baseline predictions."""
    preds = gnn_data["predictions"]
    targets = gnn_data["targets"]

    if target == "z1":
        metrics = compute_regression_metrics(preds, targets)
    else:
        preds_class = preds.argmax(axis=1)
        targets_np = targets.astype(int)
        metrics = compute_classification_metrics(preds_class, targets_np)

    return metrics


def evaluate_sklearn_only(target: str, sklearn_preds: np.ndarray, targets: np.ndarray) -> dict:
    """Evaluate sklearn baseline predictions."""
    if target == "z1":
        raise ValueError(" sklearn predictions not available for z1")

    preds = sklearn_preds.argmax(axis=1)
    targets_np = targets.astype(int)
    return compute_classification_metrics(preds, targets_np)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def print_comparison_table(target: str, gnn_metrics, sklearn_metrics, ensemble_metrics, verbose=True):
    """Print comparison of all three models."""

    def fmt(val, decimals=4):
        return f"{val:.{decimals}f}"

    print(f"\n{'='*80}")
    print(f"EXPERIMENT 13: Ensemble Evaluation - {target.upper()}")
    print(f"{'='*80}\n")

    if target == "z1":
        print(f"{'Metric':<12s} | {'GNN':>10s} | {'Ensemble':>10s} | {'Delta':>10s}")
        print(f"{'-'*12} | {'-'*10} | {'-'*10} | {'-'*10}")
        for metric in ["r2", "mae", "mse"]:
            gnn_val = gnn_metrics[metric]
            ens_val = ensemble_metrics[metric]
            delta = ens_val - gnn_val
            print(f"  {metric:<12s} | {fmt(gnn_val):>10s} | {fmt(ens_val):>10s} | {fmt(delta, 3):>+10s}")
    else:
        print(f"{'Metric':<16s} | {'GNN':>10s} | {'Sklearn':>10s} | {'Ensemble':>10s} | {'Best':>10s}")
        print(f"{'-'*16} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*10}")

        for metric in ["accuracy", "f1_macro", "f1_weighted"]:
            gnn_val = gnn_metrics[metric]
            skl_val = sklearn_metrics[metric]
            ens_val = ensemble_metrics[metric]

            # Find best
            best_val = max(gnn_val, skl_val, ens_val)
            if best_val == gnn_val:
                best = "GNN"
            elif best_val == skl_val:
                best = "Sklearn"
            else:
                best = "Ensemble"

            print(f"  {metric:<16s} | {fmt(gnn_val):>10s} | {fmt(skl_val):>10s} | {fmt(ens_val):>10s} | {best:>10s}")

            # Per-class F1
        print()
        print(f"{'-'*80}\nPer-class F1:")
        classes = sorted(list(set(ensemble_metrics["per_class_f1"].keys()) | set(gnn_metrics["per_class_f1"].keys())))
        class_strs = [str(c) for c in classes]
        gnn_f1 = [gnn_metrics["per_class_f1"].get(c, 0.0) for c in classes]
        skl_f1 = [sklearn_metrics["per_class_f1"].get(c, 0.0) for c in classes]
        ens_f1 = [ensemble_metrics["per_class_f1"].get(c, 0.0) for c in classes]

        print(f"  {'Class':>8s} | " + " | ".join(f"{s:>8s}" for s in ["GNN", "Sklearn", "Ensemble"]))
        print(f"  {'-'*8} | " + " | ".join(f"{'-'*8}" for _ in range(3)))
        for i, c in enumerate(classes):
            print(f"  {c:>8s} | {fmt(gnn_f1[i]):>8s} | {fmt(skl_f1[i]):>8s} | {fmt(ens_f1[i]):>8s}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Evaluate GNN+sklearn ensemble")
    parser.add_argument("--target", choices=["z1", "rank", "cm", "all"], default="all")
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--output-json", type=str, default=None, help="Save results to JSON")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else MODEL_DIR
    targets = ["z1", "rank", "cm"] if args.target == "all" else [args.target]

    all_results = {}

    for target in targets:
        logger.info(f"Evaluating {target}")

        # Load GNN data
        gnn_data = load_gnn_predictions(target, data_dir)
        n_samples = len(gnn_data["targets"])
        logger.info(f"  Loaded {n_samples} test samples")

        # Load sklearn predictions
        sklearn_preds = load_sklearn_predictions(target, data_dir)
        if sklearn_preds is not None:
            logger.info(f"  Loaded sklearn predictions: {sklearn_preds.shape}")

        # Load ensemble model
        ens_ckpt = load_ensemble_model(target, data_dir)
        config = ens_ckpt["config"]
        logger.info(f"  Ensemble config: {config}")

        # Build ensemble model
        if target == "z1":
            model = EnsembleRegressor(gnn_dim=256)
        else:
            model = EnsembleClassifier(
                gnn_dim=256,
                sklearn_dim=config["sklearn_dim"],
                num_classes=config["num_classes"],
            )
        model.load_state_dict(ens_ckpt["model_state_dict"])
        model.eval()

        # Evaluate GNN only
        gnn_metrics = evaluate_gnn_only(target, gnn_data)
        logger.info(f"  GNN: {gnn_metrics}")

        # Evaluate sklearn only
        sklearn_metrics = None
        if sklearn_preds is not None and target != "z1":
            sklearn_metrics = evaluate_sklearn_only(target, sklearn_preds, gnn_data["targets"])
            logger.info(f"  Sklearn: {sklearn_metrics}")

        # Evaluate ensemble
        ensemble_result = evaluate_ensemble(target, gnn_data, sklearn_preds, model)
        ensemble_metrics = ensemble_result["metrics"]
        logger.info(f"  Ensemble: {ensemble_metrics}")

        # Print comparison
        print_comparison_table(target, gnn_metrics, sklearn_metrics, ensemble_metrics)

        # Store results
        all_results[target] = {
            "gnn": gnn_metrics,
            "sklearn": sklearn_metrics,
            "ensemble": ensemble_metrics,
            "n_samples": n_samples,
            "ensemble_config": config,
        }

        # Save ensemble predictions
        pred_path = data_dir / f"ensemble_preds_{target}.npy"
        np.save(pred_path, ensemble_result["predictions"])
        logger.info(f"  Saved ensemble predictions: {pred_path}")

    # Save JSON if requested
    if args.output_json:
        output_path = Path(args.output_json)
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2, default=lambda x: float(x) if isinstance(x, np.floating) else x)
        logger.info(f"\nSaved results to {output_path}")

    print(f"\n{'='*80}")
    print("EVALUATION COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()