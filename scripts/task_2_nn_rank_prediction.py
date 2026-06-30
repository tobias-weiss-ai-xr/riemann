#!/usr/bin/env python3
"""
Task 2: Neural Network Rank Prediction from Hecke Eigenvalue Traces.

Tests whether deep learning can learn rank from trace data where sklearn failed.
Three architectures (1D-CNN, Transformer, CNN+Attention hybrid) × two formulations
(multi-class rank 0–6, binary rank=0 vs >0).

Key finding from Task 1B: sklearn GradientBoosting achieves only 0.519 accuracy on
multi-class rank (7 classes, barely above majority class ~0.43). This tests whether
neural nets with attention mechanisms can extract signal that tree-based methods miss.

Usage:
    python scripts/task_2_nn_rank_prediction.py
    python scripts/task_2_nn_rank_prediction.py --epochs 100 --batch-size 512
    python scripts/task_2_nn_rank_prediction.py --device cuda
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Fix matplotlib cache permission issue
os.environ['MPLCONFIGDIR'] = '/tmp'

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CSV_PATH = "data/lmfdb/lmfdb_sql_weight2_ml.csv"
TRACES_MATRIX_PATH = "data/lmfdb/lmfdb_sql_traces_matrix.npy"
LABELS_PATH = "data/lmfdb/lmfdb_sql_labels.json"
OUTPUT_DIR = Path("data/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
# Data loading
# ---------------------------------------------------------------------------


def load_sql_data() -> Tuple[pd.DataFrame, np.ndarray, List[str]]:
    """Load CSV metadata, traces matrix (.npy), and labels."""
    logger.info(f"Loading CSV metadata from {CSV_PATH}")
    df_csv = pd.read_csv(CSV_PATH)
    logger.info(f"Loaded {len(df_csv)} samples from CSV")

    logger.info(f"Loading traces matrix from {TRACES_MATRIX_PATH}")
    traces_full = np.load(TRACES_MATRIX_PATH)
    logger.info(f"Loaded traces matrix shape: {traces_full.shape}")

    logger.info(f"Loading labels from {LABELS_PATH}")
    with open(LABELS_PATH, "r") as f:
        labels = json.load(f)
    logger.info(f"Loaded {len(labels)} labels")

    return df_csv, traces_full, labels


def get_scalar_columns() -> List[str]:
    """Return scalar feature column names."""
    return ["level", "dim", "char_degree", "is_cm", "is_self_dual", "Nk2"]


def prepare_data(
    traces: np.ndarray,
    df_csv: pd.DataFrame,
    labels: List[str],
    n_traces: int = 1000,
    test_size: float = 0.2,
) -> Dict[str, Any]:
    """Prepare datasets for neural network training.

    Returns dict with train/val/test splits as TensorDatasets.
    """
    # Filter to samples with valid labels
    valid_mask = np.array([i < len(labels) for i in range(len(df_csv))])
    df = df_csv[valid_mask].reset_index(drop=True)
    traces_valid = traces[valid_mask]
    labels_valid = [labels[i] for i in range(len(labels)) if valid_mask[i]]

    logger.info(f"Using {len(df)} samples with valid labels")

    # Extract traces (use first n_traces columns)
    X_traces = traces_valid[:, :n_traces].astype(np.float32)

    # Extract scalar features
    scalar_cols = get_scalar_columns()
    X_scalars = df[scalar_cols].values.astype(np.float32)

    # Scale scalar features
    scaler = StandardScaler()
    X_scalars_scaled = scaler.fit_transform(X_scalars).astype(np.float32)

    # Multi-class target: rank 0-6
    y_rank = df["analytic_rank"].values.astype(np.int64)
    # Binary target: rank=0 vs rank>0
    y_binary = (y_rank > 0).astype(np.int64)

    # Stratified split
    X_tr_train, X_tr_test, X_sc_train, X_sc_test, y_rank_train, y_rank_test, y_bin_train, y_bin_test = train_test_split(
        X_traces, X_scalars_scaled, y_rank, y_binary,
        test_size=test_size, random_state=42, stratify=y_rank,
    )

    # Further split train into train/val
    X_tr_train, X_tr_val, X_sc_train, X_sc_val, y_rank_train, y_rank_val, y_bin_train, y_bin_val = train_test_split(
        X_tr_train, X_sc_train, y_rank_train, y_bin_train,
        test_size=0.1, random_state=42, stratify=y_rank_train,
    )

    logger.info(f"Train: {len(y_rank_train)}, Val: {len(y_rank_val)}, Test: {len(y_rank_test)}")

    # Class distributions
    unique, counts = np.unique(y_rank_train, return_counts=True)
    logger.info(f"Train rank distribution: {dict(zip(unique, counts))}")

    return {
        "X_tr_train": torch.from_numpy(X_tr_train),
        "X_tr_val": torch.from_numpy(X_tr_val),
        "X_tr_test": torch.from_numpy(X_tr_test),
        "X_sc_train": torch.from_numpy(X_sc_train),
        "X_sc_val": torch.from_numpy(X_sc_val),
        "X_sc_test": torch.from_numpy(X_sc_test),
        "y_rank_train": torch.from_numpy(y_rank_train),
        "y_rank_val": torch.from_numpy(y_rank_val),
        "y_rank_test": torch.from_numpy(y_rank_test),
        "y_bin_train": torch.from_numpy(y_bin_train),
        "y_bin_val": torch.from_numpy(y_bin_val),
        "y_bin_test": torch.from_numpy(y_bin_test),
        "y_rank_train_np": y_rank_train,
        "num_rank_classes": int(y_rank.max() + 1),
        "n_traces": n_traces,
        "n_scalars": len(scalar_cols),
    }


# ---------------------------------------------------------------------------
# Model architectures
# ---------------------------------------------------------------------------


class CNN1D(nn.Module):
    """1D-CNN: 3 conv blocks + GlobalAvgPool + FC.

    Processes trace vector as a 1D signal. Captures local patterns
    in the eigenvalue sequence via hierarchical convolution.
    """

    def __init__(self, n_traces: int, n_scalars: int, num_classes: int):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 32, kernel_size=7, padding=3)
        self.bn1 = nn.BatchNorm1d(32)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(64)
        self.conv3 = nn.Conv1d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm1d(128)

        # Trace feature dimension after convolutions
        self.trace_dim = 128

        # Scalar branch
        self.scalar_fc = nn.Linear(n_scalars, 64)

        # Combined
        self.fc1 = nn.Linear(self.trace_dim + 64, 128)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, traces: torch.Tensor, scalars: torch.Tensor) -> torch.Tensor:
        # traces: (B, n_traces), scalars: (B, n_scalars)
        x = traces.unsqueeze(1)  # (B, 1, n_traces)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.max_pool1d(x, 2)
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.max_pool1d(x, 2)
        x = F.relu(self.bn3(self.conv3(x)))
        x = F.adaptive_avg_pool1d(x, 1).squeeze(-1)  # (B, 128)

        s = F.relu(self.scalar_fc(scalars))  # (B, 64)

        combined = torch.cat([x, s], dim=1)
        out = F.relu(self.fc1(combined))
        out = self.dropout(out)
        return self.fc2(out)


class TransformerModel(nn.Module):
    """Transformer: Linear projection + positional encoding + 2× TransformerEncoder + FC.

    Treats each trace value as a token. Uses sinusoidal positional encoding
    to capture position information in the eigenvalue sequence.
    """

    def __init__(self, n_traces: int, n_scalars: int, num_classes: int,
                 d_model: int = 128, nhead: int = 4, num_layers: int = 2):
        super().__init__()
        self.d_model = d_model

        # Patchify traces into segments
        self.patch_size = 10
        self.n_patches = n_traces // self.patch_size
        self.patch_proj = nn.Linear(self.patch_size, d_model)

        # Positional encoding
        self.pos_enc = nn.Parameter(
            torch.randn(1, self.n_patches + 1, d_model) * 0.02
        )
        # Learnable [CLS] token
        self.cls_token = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=0.1, batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.layer_norm = nn.LayerNorm(d_model)

        # Scalar branch
        self.scalar_fc = nn.Linear(n_scalars, 64)

        # Combined
        self.fc1 = nn.Linear(d_model + 64, 128)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, traces: torch.Tensor, scalars: torch.Tensor) -> torch.Tensor:
        B = traces.shape[0]

        # Reshape traces into patches
        x = traces.view(B, self.n_patches, self.patch_size)  # (B, n_patches, patch_size)
        x = self.patch_proj(x)  # (B, n_patches, d_model)

        # Prepend CLS token
        cls = self.cls_token.expand(B, -1, -1)
        x = torch.cat([cls, x], dim=1)  # (B, n_patches+1, d_model)

        # Add positional encoding
        x = x + self.pos_enc

        # Transformer
        x = self.transformer(x)
        x = self.layer_norm(x[:, 0])  # CLS token output

        # Scalar branch
        s = F.relu(self.scalar_fc(scalars))

        combined = torch.cat([x, s], dim=1)
        out = F.relu(self.fc1(combined))
        out = self.dropout(out)
        return self.fc2(out)


class CNNAttentionHybrid(nn.Module):
    """CNN+Attention: 2 conv blocks + attention pooling + FC.

    Uses convolutional feature extraction followed by attention-based pooling
    to learn which positions in the trace sequence matter most for rank prediction.
    """

    def __init__(self, n_traces: int, n_scalars: int, num_classes: int):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 64, kernel_size=7, padding=3)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(128)

        # Attention pooling: learn query, use conv features as keys+values
        self.attn_query = nn.Parameter(torch.randn(1, 1, 128) * 0.02)
        self.attn_dim = 128

        # Scalar branch
        self.scalar_fc = nn.Linear(n_scalars, 64)

        # Combined
        self.fc1 = nn.Linear(self.attn_dim + 64, 128)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, traces: torch.Tensor, scalars: torch.Tensor) -> torch.Tensor:
        B = traces.shape[0]
        x = traces.unsqueeze(1)  # (B, 1, n_traces)
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))  # (B, 128, n_traces)

        # Attention pooling: query (1, 1, 128) dot features (B, 128, L)
        q = self.attn_query.expand(B, -1, -1)  # (B, 1, 128)
        attn_weights = torch.matmul(q, x)  # (B, 1, L)
        attn_weights = F.softmax(attn_weights, dim=-1)  # (B, 1, L)
        pooled = torch.matmul(attn_weights, x.transpose(1, 2)).squeeze(1)  # (B, 128)

        # Scalar branch
        s = F.relu(self.scalar_fc(scalars))

        combined = torch.cat([pooled, s], dim=1)
        out = F.relu(self.fc1(combined))
        out = self.dropout(out)
        return self.fc2(out)


# ---------------------------------------------------------------------------
# Training utilities
# ---------------------------------------------------------------------------


def compute_class_weights(y: np.ndarray) -> torch.Tensor:
    """Compute inverse frequency class weights."""
    unique, counts = np.unique(y, return_counts=True)
    total = len(y)
    weights = torch.zeros(len(unique), dtype=torch.float32)
    for cls, count in zip(unique, counts):
        weights[cls] = total / (len(unique) * count)
    return weights


def make_dataloaders(
    data: Dict[str, torch.Tensor],
    formulation: str,
    batch_size: int,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """Create train/val/test DataLoaders."""
    prefix = "y_rank" if formulation == "multiclass" else "y_bin"
    train_ds = TensorDataset(
        data["X_tr_train"], data["X_sc_train"], data[f"{prefix}_train"]
    )
    val_ds = TensorDataset(
        data["X_tr_val"], data["X_sc_val"], data[f"{prefix}_val"]
    )
    test_ds = TensorDataset(
        data["X_tr_test"], data["X_sc_test"], data[f"{prefix}_test"]
    )
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2)
    val_dl = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2)
    test_dl = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=2)
    return train_dl, val_dl, test_dl


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    class_weights: torch.Tensor | None = None,
) -> Tuple[float, float]:
    """Train one epoch. Returns (loss, accuracy)."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    criterion = nn.CrossEntropyLoss(reduction='mean')

    for traces, scalars, labels in loader:
        traces, scalars, labels = traces.to(device), scalars.to(device), labels.to(device)

        optimizer.zero_grad()
        logits = model(traces, scalars)
        loss = criterion(logits, labels)

        if class_weights is not None:
            # Recompute per-sample loss with weights
            loss_none = F.cross_entropy(logits, labels, reduction='none')
            sample_weights = class_weights[labels].to(device)
            loss = (loss_none * sample_weights).mean()

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += loss.item() * labels.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> Tuple[float, float]:
    """Evaluate model. Returns (loss, accuracy)."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    criterion = nn.CrossEntropyLoss(reduction='mean')

    for traces, scalars, labels in loader:
        traces, scalars, labels = traces.to(device), scalars.to(device), labels.to(device)
        logits = model(traces, scalars)
        loss = criterion(logits, labels)

        total_loss += loss.item() * labels.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

    return total_loss / total, correct / total


@torch.no_grad()
def predict_all(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> Tuple[np.ndarray, np.ndarray]:
    """Get predictions and true labels. Returns (preds, labels) as numpy arrays."""
    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []

    for traces, scalars, labels in loader:
        traces, scalars = traces.to(device), scalars.to(device)
        logits = model(traces, scalars)
        probs = F.softmax(logits, dim=1)
        preds = logits.argmax(dim=1)

        all_preds.append(preds.cpu().numpy())
        all_labels.append(labels.numpy())
        all_probs.append(probs.cpu().numpy())

    return (
        np.concatenate(all_preds),
        np.concatenate(all_labels),
        np.concatenate(all_probs),
    )


def train_model(
    model: nn.Module,
    train_dl: DataLoader,
    val_dl: DataLoader,
    device: torch.device,
    args: argparse.Namespace,
    class_weights: torch.Tensor | None = None,
) -> Dict[str, Any]:
    """Full training loop with early stopping.

    Returns dict with training history and best model state.
    """
    criterion_dummy = nn.CrossEntropyLoss(reduction='mean')  # not used, but keeps signature
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = 0.0
    best_state = None
    patience_counter = 0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    for epoch in range(args.epochs):
        train_loss, train_acc = train_epoch(
            model, train_dl, optimizer, device, class_weights
        )
        val_loss, val_acc = evaluate(model, val_dl, device)
        scheduler.step()

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            lr = optimizer.param_groups[0]['lr']
            logger.info(
                f"  Epoch {epoch+1:3d}/{args.epochs} | "
                f"Train: {train_acc:.4f} | Val: {val_acc:.4f} | "
                f"Best: {best_val_acc:.4f} | LR: {lr:.2e} | "
                f"Patience: {patience_counter}/{args.patience}"
            )

        if patience_counter >= args.patience:
            logger.info(f"  Early stopping at epoch {epoch+1}")
            break

    return {"history": history, "best_val_acc": best_val_acc, "best_state": best_state}


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

ARCHITECTURES = {
    "CNN1D": CNN1D,
    "Transformer": TransformerModel,
    "CNN+Attention": CNNAttentionHybrid,
}

FORMULATIONS = ["multiclass", "binary"]


def run_experiment(
    arch_name: str,
    formulation: str,
    data: Dict[str, Any],
    args: argparse.Namespace,
    device: torch.device,
) -> Dict[str, Any]:
    """Run a single experiment (architecture × formulation).

    Returns dict with metrics, history, and predictions.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Architecture: {arch_name} | Formulation: {formulation}")
    logger.info(f"{'='*60}")

    num_classes = data["num_rank_classes"] if formulation == "multiclass" else 2

    # Build model
    ArchClass = ARCHITECTURES[arch_name]
    model = ArchClass(data["n_traces"], data["n_scalars"], num_classes).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {n_params:,}")

    # DataLoaders
    train_dl, val_dl, test_dl = make_dataloaders(data, formulation, args.batch_size)

    # Class weights for multiclass
    cw = None
    if formulation == "multiclass" and args.class_weights:
        cw = compute_class_weights(data["y_rank_train_np"]).to(device)
        logger.info(f"Class weights: {cw.tolist()}")

    # Train
    t0 = time.time()
    result = train_model(model, train_dl, val_dl, device, args, cw)
    train_time = time.time() - t0

    # Load best model
    if result["best_state"] is not None:
        model.load_state_dict(result["best_state"])
        model.to(device)

    # Evaluate on test set
    preds, true, probs = predict_all(model, test_dl, device)

    # Metrics
    accuracy = accuracy_score(true, preds)
    f1_macro = f1_score(true, preds, average="macro")
    f1_weighted = f1_score(true, preds, average="weighted")
    report = classification_report(true, preds, output_dict=True, zero_division=0)
    cm = confusion_matrix(true, preds)

    metrics = {
        "architecture": arch_name,
        "formulation": formulation,
        "n_params": n_params,
        "accuracy": round(float(accuracy), 4),
        "f1_macro": round(float(f1_macro), 4),
        "f1_weighted": round(float(f1_weighted), 4),
        "train_time_s": round(train_time, 1),
        "confusion_matrix": cm.tolist(),
        "classification_report": {
            str(k): {str(kk): round(vv, 4) for kk, vv in v.items()} if isinstance(v, dict) else round(float(v), 4)
            for k, v in report.items()
        },
        "history": {k: [round(x, 4) for x in v] for k, v in result["history"].items()},
    }

    # AUC for binary
    if formulation == "binary" and len(np.unique(true)) == 2:
        try:
            metrics["roc_auc"] = round(float(roc_auc_score(true, probs[:, 1])), 4)
        except ValueError:
            metrics["roc_auc"] = None

    logger.info(f"  Test Accuracy: {accuracy:.4f} | F1(macro): {f1_macro:.4f}")
    logger.info(f"  Train time: {train_time:.1f}s")

    return metrics


def print_separator(char: str = "=", width: int = 78) -> None:
    print(char * width)


def print_results_table(all_results: List[Dict[str, Any]]) -> None:
    """Print a formatted results table."""
    print_separator()
    print("  TASK 2: NEURAL NETWORK RANK PREDICTION RESULTS".center(78))
    print_separator()

    for formulation in FORMULATIONS:
        print(f"\n  Formulation: {formulation.upper()}")
        print(f"  {'Architecture':<18} {'Params':>8} {'Acc':>7} {'F1(mac)':>8} {'F1(wtd)':>8} {'Time':>7} {'AUC':>6}")
        print(f"  {'-'*17} {'-'*8} {'-'*7} {'-'*8} {'-'*8} {'-'*7} {'-'*6}")

        for r in all_results:
            if r["formulation"] != formulation:
                continue
            auc = f"{r.get('roc_auc', 'N/A')}" if r.get("roc_auc") is not None else "N/A"
            print(
                f"  {r['architecture']:<18} {r['n_params']:>8,} "
                f"{r['accuracy']:>7.4f} {r['f1_macro']:>8.4f} {r['f1_weighted']:>8.4f} "
                f"{r['train_time_s']:>6.1f}s {auc:>6}"
            )

    # Comparison with sklearn baseline
    print(f"\n  sklearn GradientBoosting baseline (Task 1B, 1000 traces):")
    print(f"    Multi-class rank:  Acc=0.5192, F1(macro)=0.3481")

    print_separator()


def plot_results(all_results: List[Dict[str, Any]], output_dir: Path) -> Path:
    """Create comparison plots."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # --- Plot 1: Accuracy by architecture × formulation ---
    ax = axes[0, 0]
    formulations = ["multiclass", "binary"]
    archs = list(ARCHITECTURES.keys())
    x = np.arange(len(archs))
    width = 0.35
    for i, form in enumerate(formulations):
        accs = [r["accuracy"] for r in all_results if r["formulation"] == form]
        label = "Multi-class (rank 0-6)" if form == "multiclass" else "Binary (rank=0 vs >0)"
        ax.bar(x + i * width, accs, width, label=label)
    ax.set_xlabel("Architecture")
    ax.set_ylabel("Test Accuracy")
    ax.set_title("Neural Net Rank Prediction Accuracy")
    ax.set_xticks(x + width / 2)
    ax.set_xticklabels(archs, rotation=15)
    ax.legend(fontsize=8)
    ax.set_ylim(0.3, 1.05)
    # Add sklearn baseline
    ax.axhline(y=0.5192, color='red', linestyle='--', alpha=0.7, label='sklearn baseline (multi-class)')
    ax.legend(fontsize=8)

    # --- Plot 2: Training curves (multi-class) ---
    ax = axes[0, 1]
    for r in all_results:
        if r["formulation"] != "multiclass":
            continue
        h = r["history"]
        ax.plot(h["val_acc"], label=f'{r["architecture"]}', linewidth=1.5)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Validation Accuracy")
    ax.set_title("Training Curves (Multi-class)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # --- Plot 3: Training curves (binary) ---
    ax = axes[1, 0]
    for r in all_results:
        if r["formulation"] != "binary":
            continue
        h = r["history"]
        ax.plot(h["val_acc"], label=f'{r["architecture"]}', linewidth=1.5)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Validation Accuracy")
    ax.set_title("Training Curves (Binary)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # --- Plot 4: Confusion matrices (multi-class) ---
    ax = axes[1, 1]
    n_archs = sum(1 for r in all_results if r["formulation"] == "multiclass")
    for i, r in enumerate(all_results):
        if r["formulation"] != "multiclass":
            continue
        cm = np.array(r["confusion_matrix"])
        # Normalize by row
        cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True).clip(min=1)
        ax.imshow(cm_norm, cmap='Blues', alpha=0.3 + 0.7 * (i / max(n_archs - 1, 1)))

    ax.set_xlabel("Predicted Rank")
    ax.set_ylabel("True Rank")
    ax.set_title("Confusion Matrices (Multi-class, stacked)")

    plt.tight_layout()
    out_path = output_dir / "task_2_nn_rank_prediction.png"
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Saved plot to {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 2: NN Rank Prediction")
    parser.add_argument("--epochs", type=int, default=50, help="Max training epochs")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    parser.add_argument("--n-traces", type=int, default=1000, help="Number of traces to use")
    parser.add_argument("--device", type=str, default=None, help="Device (cuda/cpu)")
    parser.add_argument("--no-class-weights", action="store_true", help="Disable class weighting")
    args = parser.parse_args()

    args.class_weights = not args.no_class_weights

    # Device
    if args.device:
        device = torch.device(args.device)
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info(f"Using CUDA: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        logger.info("Using CPU")

    print_separator()
    print("  TASK 2: NEURAL NETWORK RANK PREDICTION".center(78))
    print("  Testing 3 architectures × 2 formulations on Hecke trace data".center(78))
    print_separator()

    # Load data
    df_csv, traces_full, labels = load_sql_data()
    data = prepare_data(traces_full, df_csv, labels, n_traces=args.n_traces)

    # Run experiments
    all_results: List[Dict[str, Any]] = []
    t_total = time.time()

    for formulation in FORMULATIONS:
        for arch_name in ARCHITECTURES:
            result = run_experiment(arch_name, formulation, data, args, device)
            all_results.append(result)

    total_time = time.time() - t_total
    logger.info(f"\nTotal experiment time: {total_time:.1f}s")

    # Print results
    print_results_table(all_results)

    # Plot
    plot_results(all_results, OUTPUT_DIR)

    # Save results
    results_out = {
        "description": "Task 2: Neural Network Rank Prediction from Hecke Traces",
        "n_samples": len(data["y_rank_train_np"]),
        "n_traces": args.n_traces,
        "n_scalars": data["n_scalars"],
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "patience": args.patience,
        "device": str(device),
        "total_time_s": round(total_time, 1),
        "sklearn_baseline": {
            "multiclass_acc": 0.5192,
            "multiclass_f1_macro": 0.3481,
        },
        "results": all_results,
    }

    out_path = OUTPUT_DIR / "task_2_nn_rank_prediction_results.json"
    with open(out_path, "w") as f:
        json.dump(results_out, f, indent=2)
    logger.info(f"Saved results to {out_path}")

    # Summary
    print_separator()
    best_mc = max(
        (r for r in all_results if r["formulation"] == "multiclass"),
        key=lambda r: r["accuracy"],
    )
    best_bin = max(
        (r for r in all_results if r["formulation"] == "binary"),
        key=lambda r: r["accuracy"],
    )
    print(f"  BEST Multi-class: {best_mc['architecture']} acc={best_mc['accuracy']:.4f} "
          f"(sklearn baseline: 0.5192)")
    print(f"  BEST Binary:      {best_bin['architecture']} acc={best_bin['accuracy']:.4f}")
    print_separator()


if __name__ == "__main__":
    main()
