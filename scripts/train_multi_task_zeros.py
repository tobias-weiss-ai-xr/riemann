"""
Thread N: Multi-Task Zero Prediction.

Compares single-task MLP (z1 only) vs multi-task MLP (shared backbone, z1-z10)
on the same 63,844 weight-2 newforms. Key question: does sharing a backbone
across all 10 L-function zeros improve z1 prediction?

Usage:
    python scripts/train_multi_task_zeros.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
CSV_PATH = DATA_DIR / "lmfdb" / "lmfdb_zeros_ml.csv"
RESULTS_DIR = DATA_DIR / "multi_task"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    """Load Hecke traces (100 cols) and z1-z10 targets from CSV."""
    logger.info(f"Loading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)

    # Extract 100 Hecke trace columns (columns 4..103, 0-indexed)
    trace_cols = [f"trace_{i}" for i in range(1, 101)]
    missing = [c for c in trace_cols if c not in df.columns]
    if missing:
        logger.warning(f"Missing trace columns: {missing[:5]}")
        # Try positional indexing
        trace_cols = df.columns[4:104].tolist()

    X = df[trace_cols].values.astype(np.float32)

    # Extract z1-z10
    z_cols = [f"z{i}" for i in range(1, 11)]
    missing_z = [c for c in z_cols if c not in df.columns]
    if missing_z:
        logger.error(f"Missing z-columns: {missing_z}")
        sys.exit(1)

    Y = df[z_cols].values.astype(np.float32)

    # Drop rows with NaN in any target
    nan_mask = np.isnan(Y).any(axis=1)
    if nan_mask.any():
        logger.warning(f"Dropping {nan_mask.sum()} rows with NaN targets")
        X = X[~nan_mask]
        Y = Y[~nan_mask]

    logger.info(f"Loaded {len(X)} samples, {X.shape[1]} features, {Y.shape[1]} targets")
    logger.info(f"z1 range: [{Y[:, 0].min():.4f}, {Y[:, 0].max():.4f}]")
    logger.info(f"z range across all: [{Y.min():.4f}, {Y.max():.4f}]")

    return X, Y, df


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SingleTaskMLP(nn.Module):
    """Simple MLP — predict z1 only."""

    def __init__(self, in_dim=100, hidden_dim=256, num_layers=3, dropout=0.2):
        super().__init__()
        layers = []
        dims = [in_dim] + [hidden_dim] * num_layers
        for i in range(len(dims) - 1):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            layers.append(nn.BatchNorm1d(dims[i + 1]))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
        self.backbone = nn.Sequential(*layers)
        self.head = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        h = self.backbone(x)
        return self.head(h).squeeze(-1)


class MultiTaskMLP(nn.Module):
    """Shared backbone MLP — predict z1-z10 jointly."""

    def __init__(self, in_dim=100, hidden_dim=256, num_layers=3, dropout=0.2):
        super().__init__()
        layers = []
        dims = [in_dim] + [hidden_dim] * num_layers
        for i in range(len(dims) - 1):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            layers.append(nn.BatchNorm1d(dims[i + 1]))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
        self.backbone = nn.Sequential(*layers)
        self.head = nn.Linear(hidden_dim, 10)  # 10 outputs

    def forward(self, x):
        h = self.backbone(x)
        return self.head(h)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

@torch.no_grad()
def evaluate(model, X, Y, multi_task=True, scaler_Y=None):
    model.eval()
    preds = model(torch.from_numpy(X).to(device))
    if multi_task and scaler_Y is not None:
        preds_np = scaler_Y.inverse_transform(preds.cpu().numpy())
    elif multi_task:
        preds_np = preds.cpu().numpy()
    else:
        preds_np = preds.cpu().numpy().reshape(-1, 1)

    z1_pred = preds_np[:, 0]
    z1_true = Y[:, 0]
    r2 = r2_score(z1_true, z1_pred)
    mse = mean_squared_error(z1_true, z1_pred)

    # Per-zero R² for multi-task
    per_zero_r2 = {}
    if multi_task:
        for i in range(10):
            per_zero_r2[f"z{i+1}"] = float(r2_score(Y[:, i], preds_np[:, i]))

    return {"z1_r2": float(r2), "z1_mse": float(mse), "per_zero_r2": per_zero_r2}


def train_model(model, X_train, Y_train, X_val, Y_val, multi_task=True,
                epochs=200, lr=1e-3, weight_decay=1e-5, patience=30):
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    X_train_t = torch.from_numpy(X_train).to(device)
    Y_train_t = torch.from_numpy(Y_train).to(device)

    best_val_r2 = -float("inf")
    best_state = None
    patience_counter = 0
    history = []

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        preds = model(X_train_t)

        if multi_task:
            loss = F.mse_loss(preds, Y_train_t)
        else:
            loss = F.mse_loss(preds, Y_train_t[:, 0])

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        # Validation every 5 epochs
        if epoch % 5 == 0:
            val_metrics = evaluate(model, X_val, Y_val, multi_task)
            val_r2 = val_metrics["z1_r2"]

            history.append({
                "epoch": epoch,
                "train_loss": float(loss),
                "val_z1_r2": val_r2,
                "lr": float(scheduler.get_last_lr()[0]),
            })

            if val_r2 > best_val_r2:
                best_val_r2 = val_r2
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience // 5:
                    logger.info(f"Early stopping at epoch {epoch} (val z1 R²={val_r2:.4f})")
                    break

        if epoch % 20 == 0:
            val_metrics = evaluate(model, X_val, Y_val, multi_task)
            logger.info(f"  Epoch {epoch:3d} | loss={loss:.4f} | val z1 R²={val_metrics['z1_r2']:.4f}")

    # Restore best
    if best_state:
        model.load_state_dict(best_state)
        model = model.to(device)

    return model, history, best_val_r2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-size", type=float, default=0.15)
    parser.add_argument("--test-size", type=float, default=0.15)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Load data
    X, Y, df = load_data()

    # Normalize features
    scaler_X = StandardScaler()
    X_scaled = scaler_X.fit_transform(X)

    # Normalize targets per zero (for multi-task stability)
    scaler_Y = StandardScaler()
    Y_scaled = scaler_Y.fit_transform(Y)

    # Split: train/val/test
    X_rest, X_test, Y_rest, Y_test, Y_scaled_rest, Y_scaled_test = train_test_split(
        X_scaled, Y, Y_scaled, test_size=args.test_size, random_state=args.seed
    )
    X_train, X_val, Y_train, Y_val, Y_scaled_train, Y_scaled_val = train_test_split(
        X_rest, Y_rest, Y_scaled_rest, test_size=args.val_size / (1 - args.test_size),
        random_state=args.seed
    )

    logger.info(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    logger.info(f"Feature dim: {X.shape[1]}, Target dim: {Y.shape[1]}")

    results = {"args": vars(args), "n_samples": len(X)}

    # --- Single-task MLP (z1 only, raw z1) ---
    logger.info("=" * 60)
    logger.info("Single-Task MLP (z1 only)")
    logger.info("=" * 60)

    # For single-task: use unnormalized z1 as target
    y_z1_train = Y_train[:, 0:1]
    y_z1_val = Y_val[:, 0:1]

    model_st = SingleTaskMLP(
        in_dim=X.shape[1], hidden_dim=args.hidden,
        num_layers=args.layers, dropout=args.dropout
    )
    logger.info(f"Model: {sum(p.numel() for p in model_st.parameters()):,} params")

    t0 = time.time()
    model_st, hist_st, best_val_r2_st = train_model(
        model_st, X_train, y_z1_train, X_val, y_z1_val,
        multi_task=False, epochs=args.epochs, lr=args.lr, patience=30
    )
    t_st = time.time() - t0

    test_st = evaluate(model_st, X_test, Y_test, multi_task=False, scaler_Y=None)
    test_st["train_time_s"] = round(t_st, 1)
    test_st["best_val_z1_r2"] = float(best_val_r2_st)
    results["single_task"] = test_st

    logger.info(f"  Single-Task Test z1 R²: {test_st['z1_r2']:.4f}, MSE: {test_st['z1_mse']:.6f}")
    logger.info(f"  Training time: {t_st:.1f}s")

    # --- Multi-task MLP (z1-z10 shared backbone) ---
    logger.info("=" * 60)
    logger.info("Multi-Task MLP (z1-z10 shared backbone)")
    logger.info("=" * 60)

    # For multi-task: use scaled Y (all 10 zeros) — standardize per zero for equal weighting
    model_mt = MultiTaskMLP(
        in_dim=X.shape[1], hidden_dim=args.hidden,
        num_layers=args.layers, dropout=args.dropout
    )
    logger.info(f"Model: {sum(p.numel() for p in model_mt.parameters()):,} params")

    t0 = time.time()
    model_mt, hist_mt, best_val_r2_mt = train_model(
        model_mt, X_train, Y_scaled_train, X_val, Y_scaled_val,
        multi_task=True, epochs=args.epochs, lr=args.lr, patience=30
    )
    t_mt = time.time() - t0

    # IMPORTANT: pass scaler_Y to inverse-transform multi-task outputs for raw-space evaluation
    test_mt = evaluate(model_mt, X_test, Y_test, multi_task=True, scaler_Y=scaler_Y)
    test_mt["train_time_s"] = round(t_mt, 1)
    test_mt["best_val_z1_r2"] = float(best_val_r2_mt)
    results["multi_task"] = test_mt

    logger.info(f"  Multi-Task Test z1 R²: {test_mt['z1_r2']:.4f}, MSE: {test_mt['z1_mse']:.6f}")
    logger.info(f"  Training time: {t_mt:.1f}s")

    # Per-zero R²
    logger.info("  Per-zero R² (multi-task):")
    for z, r2 in sorted(test_mt["per_zero_r2"].items()):
        logger.info(f"    {z}: {r2:.4f}")

    # --- Comparison ---
    logger.info("=" * 60)
    logger.info("COMPARISON: Single-Task vs Multi-Task z1 R²")
    logger.info("=" * 60)

    st_r2 = test_st["z1_r2"]
    mt_r2 = test_mt["z1_r2"]
    delta = mt_r2 - st_r2
    results["comparison"] = {
        "single_task_z1_r2": st_r2,
        "multi_task_z1_r2": mt_r2,
        "delta": float(delta),
        "delta_pct": float(delta / abs(st_r2) * 100) if st_r2 != 0 else 0,
        "multi_task_wins": mt_r2 > st_r2,
    }

    logger.info(f"  Single-Task z1 R²: {st_r2:.4f}")
    logger.info(f"  Multi-Task  z1 R²: {mt_r2:.4f}")
    logger.info(f"  Δ: {delta:+.4f} ({results['comparison']['delta_pct']:+.1f}%)")

    if mt_r2 > st_r2:
        logger.info("  ✅ Multi-task improves z1 prediction — shared backbone helps!")
    else:
        logger.info("  ❌ Multi-task does NOT improve z1 prediction — task-specific head is better.")

    # Save results
    out_path = RESULTS_DIR / "multi_task_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {out_path}")

    # Save per-epoch history
    hist_path = RESULTS_DIR / "training_history.json"
    with open(hist_path, "w") as f:
        json.dump({"single_task": hist_st, "multi_task": hist_mt}, f, indent=2)
    logger.info(f"Training history saved to {hist_path}")

    # Save model checkpoints
    torch.save(model_st.state_dict(), RESULTS_DIR / "single_task_mlp.pt")
    torch.save(model_mt.state_dict(), RESULTS_DIR / "multi_task_mlp.pt")
    logger.info("Model checkpoints saved")


if __name__ == "__main__":
    main()
