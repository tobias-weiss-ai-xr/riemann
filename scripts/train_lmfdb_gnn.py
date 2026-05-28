"""
Experiment 12: GNN on LMFDB Hecke Trace Graphs.

Trains GCN and ChebConv models on graph-structured Hecke trace data
(Paradigm A: trace-index graphs, Paradigm C: multiplicative graphs).

Experiments:
  12a: z1 regression (first L-function zero)
  12b: analytic_rank classification (3-class: 0/1/2)
  12c: is_cm classification (binary)

Usage:
    python scripts/train_lmfdb_gnn.py --target z1 --model gcn
    python scripts/train_lmfdb_gnn.py --target rank --model chebconv --K 5
    python scripts/train_lmfdb_gnn.py --all-gcn
    python scripts/train_lmfdb_gnn.py --all-chebconv
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import warnings
warnings.filterwarnings("ignore", message=".*torch-scatter.*")

from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from torch import nn
from torch.utils.data import DataLoader
from torch_geometric.loader import DataLoader as PyGDataLoader
from torch_geometric.data import Data
from torch_geometric.nn import ChebConv, GCNConv, global_mean_pool, global_max_pool

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
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt(val: float, decimals: int = 4) -> str:
    return f"{val:.{decimals}f}"


def print_separator(char: str = "=", width: int = 78) -> None:
    print(char * width)


def print_header(text: str, width: int = 78) -> None:
    print_separator()
    padding = max(0, (width - len(text) - 2) // 2)
    print(f"  {text}".center(width))
    print_separator()


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


class CompactGraphDataset(torch.utils.data.Dataset):
    """Dataset backed by numpy mmap files for fast loading of large edge tensors."""

    def __init__(self, split_dir: Path, target: str, num_nodes_per_graph: int):
        self.num_nodes = num_nodes_per_graph
        self.x = np.load(split_dir / "x.npy", mmap_mode="r")
        self.edge_index = np.load(split_dir / "edge_index.npy", mmap_mode="r")
        self.edge_ptr = np.load(split_dir / "edge_ptr.npy", mmap_mode="r")
        self.n_graphs = len(self.edge_ptr) - 1

        if target == "z1":
            self.y = np.load(split_dir / "y_z1.npy", mmap_mode="r").astype(np.float32)
        elif target == "rank":
            self.y = np.load(split_dir / "y_rank.npy", mmap_mode="r").astype(np.int64)
        elif target == "cm":
            self.y = np.load(split_dir / "y_cm.npy", mmap_mode="r").astype(np.int64)
        else:
            raise ValueError(f"Unknown target: {target}")

    def __len__(self):
        return self.n_graphs

    def __getitem__(self, idx: int):
        node_start = idx * self.num_nodes
        node_end = node_start + self.num_nodes
        x = torch.from_numpy(np.array(self.x[node_start:node_end]))

        edge_start = int(self.edge_ptr[idx])
        edge_end = int(self.edge_ptr[idx + 1])
        edge_index = torch.from_numpy(self.edge_index[:, edge_start:edge_end].astype(np.int64))

        data = Data(x=x, edge_index=edge_index, y=torch.tensor([self.y[idx]], dtype=torch.float32 if self.y.dtype == np.float32 else torch.long))
        return data


def load_dataset(data_dir: Path, target: str):
    """Load train/val/test splits from numpy mmap directories."""
    with open(data_dir / "metadata.json") as f:
        meta = json.load(f)
    num_nodes = meta["num_nodes_per_graph"]

    train = CompactGraphDataset(data_dir / "train", target, num_nodes)
    val = CompactGraphDataset(data_dir / "val", target, num_nodes)
    test = CompactGraphDataset(data_dir / "test", target, num_nodes)
    return train, val, test


class MultiplicativeGraphDataset(torch.utils.data.Dataset):
    """Dataset for Paradigm C — shared edge_index across all graphs."""

    def __init__(self, data_dir: Path, split_name: str, target: str, num_nodes: int):
        self.num_nodes = num_nodes
        self.x = np.load(data_dir / split_name / "x.npy", mmap_mode="r")
        self.edge_index = torch.from_numpy(
            np.load(data_dir / "shared_edge_index.npy").astype(np.int64)
        )
        self.n_graphs = self.x.shape[0] // num_nodes

        if target == "z1":
            self.y = np.load(data_dir / split_name / "y_z1.npy", mmap_mode="r").astype(np.float32)
        elif target == "rank":
            self.y = np.load(data_dir / split_name / "y_rank.npy", mmap_mode="r").astype(np.int64)
        elif target == "cm":
            self.y = np.load(data_dir / split_name / "y_cm.npy", mmap_mode="r").astype(np.int64)
        else:
            raise ValueError(f"Unknown target: {target}")

    def __len__(self):
        return self.n_graphs

    def __getitem__(self, idx: int):
        node_start = idx * self.num_nodes
        node_end = node_start + self.num_nodes
        x = torch.from_numpy(np.array(self.x[node_start:node_end]))
        return Data(
            x=x,
            edge_index=self.edge_index,
            y=torch.tensor([self.y[idx]], dtype=torch.float32 if self.y.dtype == np.float32 else torch.long),
        )


def load_dataset(data_dir: Path, target: str):
    """Load train/val/test splits from numpy mmap directories."""
    with open(data_dir / "metadata.json") as f:
        meta = json.load(f)
    num_nodes = meta["num_nodes_per_graph"]
    is_multiplicative = meta.get("shared_edge_index", False)

    if is_multiplicative:
        train = MultiplicativeGraphDataset(data_dir, "train", target, num_nodes)
        val = MultiplicativeGraphDataset(data_dir, "val", target, num_nodes)
        test = MultiplicativeGraphDataset(data_dir, "test", target, num_nodes)
    else:
        train = CompactGraphDataset(data_dir / "train", target, num_nodes)
        val = CompactGraphDataset(data_dir / "val", target, num_nodes)
        test = CompactGraphDataset(data_dir / "test", target, num_nodes)
    return train, val, test


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TraceIndexGCN(nn.Module):
    """GCN on trace-index graphs with mean+max readout."""

    def __init__(
        self,
        node_feat_dim: int = 5,
        hidden_dim: int = 128,
        num_layers: int = 3,
        num_targets: int = 1,
    ):
        super().__init__()
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for i in range(num_layers):
            in_dim = node_feat_dim if i == 0 else hidden_dim
            self.convs.append(GCNConv(in_dim, hidden_dim))
            self.norms.append(nn.BatchNorm1d(hidden_dim))

        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_targets),
        )

    def forward(self, data, return_embeddings: bool = False):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        for conv, norm in zip(self.convs, self.norms):
            x = norm(conv(x, edge_index)).relu()
            x = F.dropout(x, p=0.1, training=self.training)
        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )
        logits = self.head(readout)
        if return_embeddings:
            return logits, readout
        return logits


class TraceIndexChebConv(nn.Module):
    """ChebConv on trace-index graphs with mean+max readout."""

    def __init__(
        self,
        node_feat_dim: int = 5,
        hidden_dim: int = 128,
        K: int = 5,
        num_layers: int = 3,
        num_targets: int = 1,
    ):
        super().__init__()
        self.K = K
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for i in range(num_layers):
            in_dim = node_feat_dim if i == 0 else hidden_dim
            self.convs.append(ChebConv(in_dim, hidden_dim, K=K))
            self.norms.append(nn.BatchNorm1d(hidden_dim))

        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_targets),
        )

    def forward(self, data, return_embeddings: bool = False):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        for conv, norm in zip(self.convs, self.norms):
            x = norm(conv(x, edge_index)).relu()
            x = F.dropout(x, p=0.1, training=self.training)
        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )
        logits = self.head(readout)
        if return_embeddings:
            return logits, readout
        return logits


def build_model(model_type: str, node_feat_dim: int, hidden_dim: int, num_layers: int,
                K: int, num_targets: int) -> nn.Module:
    """Build model by type."""
    if model_type == "gcn":
        return TraceIndexGCN(node_feat_dim, hidden_dim, num_layers, num_targets)
    elif model_type == "chebconv":
        return TraceIndexChebConv(node_feat_dim, hidden_dim, K, num_layers, num_targets)
    else:
        raise ValueError(f"Unknown model: {model_type}")


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_epoch(model, loader, optimizer, device, task_type: str):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    total_samples = 0

    for batch in loader:
        batch = batch.to(device)
        optimizer.zero_grad()

        out = model(batch)

        if task_type == "regression":
            loss = F.mse_loss(out.squeeze(), batch.y.squeeze())
        else:
            loss = F.cross_entropy(out, batch.y.squeeze())

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item() * batch.num_graphs
        total_samples += batch.num_graphs

    return total_loss / total_samples


@torch.no_grad()
def evaluate(model, loader, device, task_type: str):
    """Evaluate and return loss + predictions + targets."""
    model.eval()
    total_loss = 0.0
    total_samples = 0
    all_preds = []
    all_targets = []

    for batch in loader:
        batch = batch.to(device)
        out = model(batch)

        if task_type == "regression":
            loss = F.mse_loss(out.squeeze(), batch.y.squeeze())
            preds = out.squeeze().cpu().numpy()
        else:
            loss = F.cross_entropy(out, batch.y.squeeze())
            preds = out.argmax(dim=1).cpu().numpy()

        total_loss += loss.item() * batch.num_graphs
        total_samples += batch.num_graphs
        all_preds.extend(preds.flatten())
        all_targets.extend(batch.y.squeeze().cpu().numpy().flatten())

    avg_loss = total_loss / total_samples
    return avg_loss, np.array(all_preds), np.array(all_targets)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_regression_metrics(preds, targets):
    """Compute regression metrics."""
    mse = mean_squared_error(targets, preds)
    mae = mean_absolute_error(targets, preds)
    r2 = r2_score(targets, preds)
    return {"mse": mse, "mae": mae, "r2": r2}


def compute_classification_metrics(preds, targets):
    """Compute classification metrics."""
    acc = accuracy_score(targets, preds)
    f1_mac = f1_score(targets, preds, average="macro", zero_division=0)
    f1_wt = f1_score(targets, preds, average="weighted", zero_division=0)
    classes = sorted(np.unique(targets).astype(int))
    per_class_f1 = {}
    for c in classes:
        per_class_f1[c] = f1_score(
            (targets == c).astype(int), (preds == c).astype(int), zero_division=0
        )
    return {
        "accuracy": acc,
        "f1_macro": f1_mac,
        "f1_weighted": f1_wt,
        "per_class_f1": per_class_f1,
        "classes": classes,
    }


# ---------------------------------------------------------------------------
# Single experiment runner
# ---------------------------------------------------------------------------


def run_experiment(
    target: str,
    model_type: str,
    data_dir: Path,
    hidden_dim: int,
    num_layers: int,
    K: int,
    epochs: int,
    batch_size: int,
    lr: float,
    patience: int,
    output_dir: Path,
    export_embeddings: bool = False,
):
    """Run a single training experiment."""
    task_type = "regression" if target == "z1" else "classification"
    num_targets = 1 if task_type == "regression" else 3 if target == "rank" else 2
    exp_name = f"12{'abc'['z1 rank cm'.split().index(target)]}"
    target_names = {"z1": "z1 Regression", "rank": "Analytic Rank Classification",
                    "cm": "CM Classification"}
    paradigm_name = data_dir.name.replace("gnn_", "").replace("_", "-")

    print_header(f"Experiment {exp_name}: {target_names[target]} ({model_type.upper()} on {paradigm_name} graphs)")

    # Load data
    logger.info(f"Loading dataset from {data_dir}")
    train_graphs, val_graphs, test_graphs = load_dataset(data_dir, target)
    logger.info(f"  train={len(train_graphs)}, val={len(val_graphs)}, test={len(test_graphs)}")

    node_feat_dim = train_graphs[0].x.shape[1]
    logger.info(f"  node_feat_dim={node_feat_dim}")

    # Create data loaders
    train_loader = PyGDataLoader(train_graphs, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = PyGDataLoader(val_graphs, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = PyGDataLoader(test_graphs, batch_size=batch_size, shuffle=False, num_workers=0)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Build model
    model = build_model(model_type, node_feat_dim, hidden_dim, num_layers, K, num_targets).to(device)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"Model: {model_type.upper()}(hidden={hidden_dim}, layers={num_layers}, K={K})")
    logger.info(f"  Parameters: {param_count:,}")

    # Optimizer + scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # Training loop
    best_val_loss = float("inf")
    best_state = None
    best_epoch = 0
    epochs_no_improve = 0

    logger.info(f"Training: {epochs} epochs, patience={patience}")
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device, task_type)
        val_loss, val_preds, val_targets = evaluate(model, val_loader, device, task_type)
        scheduler.step()

        # Extra metric for logging
        if task_type == "regression":
            val_r2 = r2_score(val_targets, val_preds)
            extra = f" | Val R²: {val_r2:.4f}"
        else:
            val_acc = accuracy_score(val_targets, val_preds)
            extra = f" | Val Acc: {val_acc:.4f}"

        if epoch % 10 == 0 or epoch == 1:
            logger.info(
                f"  Epoch {epoch:3d}/{epochs} | Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f}{extra}"
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= patience:
            logger.info(f"  Early stopping at epoch {epoch} (patience={patience})")
            break

    elapsed = time.time() - t0
    logger.info(f"  Best model at epoch {best_epoch} (val_loss={best_val_loss:.4f}, time={elapsed:.1f}s)")

    # Load best model and evaluate on test
    model.load_state_dict(best_state)
    model = model.to(device)
    test_loss, test_preds, test_targets = evaluate(model, test_loader, device, task_type)

    # Print results
    print()
    if task_type == "regression":
        metrics = compute_regression_metrics(test_preds, test_targets)
        print(f"  {'Metric':<12s} | {'Value':>10s}")
        print(f"  {'-' * 12} | {'-' * 10}")
        print(f"  {'MSE':<12s} | {fmt(metrics['mse']):>10s}")
        print(f"  {'MAE':<12s} | {fmt(metrics['mae']):>10s}")
        print(f"  {'R²':<12s} | {fmt(metrics['r2']):>10s}")
        print(f"\n  (Compare R² against Exp 11 sklearn baselines)")
        test_metrics = metrics
    else:
        metrics = compute_classification_metrics(test_preds, test_targets)
        print(f"  {'Metric':<16s} | {'Value':>10s}")
        print(f"  {'-' * 16} | {'-' * 10}")
        print(f"  {'Accuracy':<16s} | {fmt(metrics['accuracy']):>10s}")
        print(f"  {'F1(macro)':<16s} | {fmt(metrics['f1_macro']):>10s}")
        print(f"  {'F1(weighted)':<16s} | {fmt(metrics['f1_weighted']):>10s}")
        print()
        print("  Per-class F1:")
        class_strs = [str(c) for c in metrics["classes"]]
        print(f"  {'Class':>8s} | " + " | ".join(f"{s:>8s}" for s in class_strs))
        print(f"  {'-' * 8} | " + " | ".join(f"{'-' * 8}" for _ in class_strs))
        vals = [fmt(metrics["per_class_f1"][c]) for c in metrics["classes"]]
        print(f"  {'F1':>8s} | " + " | ".join(f"{v:>8s}" for v in vals))
        print(f"\n  (Compare F1 against Exp 10 sklearn baselines)")
        test_metrics = metrics

    print()

    # Save checkpoint
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = output_dir / f"lmfdb_gnn_{model_type}_{target}.pt"
    torch.save(
        {
            "model_state_dict": best_state,
            "config": {
                "model_type": model_type,
                "hidden_dim": hidden_dim,
                "num_layers": num_layers,
                "K": K,
                "node_feat_dim": node_feat_dim,
                "num_targets": num_targets,
            },
            "best_epoch": best_epoch,
            "val_loss": best_val_loss,
            "test_metrics": {k: float(v) if isinstance(v, (np.floating, float)) else v
                             for k, v in test_metrics.items()},
            "target": target,
            "paradigm": paradigm_name,
        },
        ckpt_path,
    )
    logger.info(f"  Saved checkpoint: {ckpt_path}")

    # Export embeddings and raw predictions if requested
    if export_embeddings:
        model.eval()
        all_embeddings, all_raw_preds = [], []
        with torch.no_grad():
            for batch in test_loader:
                batch = batch.to(device)
                out, embeddings = model(batch, return_embeddings=True)
                all_embeddings.append(embeddings.cpu())
                all_raw_preds.append(out.cpu())
        all_embeddings = torch.cat(all_embeddings, dim=0).numpy()
        all_raw_preds = torch.cat(all_raw_preds, dim=0).numpy()
        emb_path = output_dir / f"gnn_embeddings_{target}.npy"
        pred_path = output_dir / f"gnn_raw_preds_{target}.npy"
        np.save(emb_path, all_embeddings)
        np.save(pred_path, all_raw_preds)
        logger.info(f"  Exported embeddings: {all_embeddings.shape}, raw_preds: {all_raw_preds.shape}")

    return test_metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Experiment 12: GNN on LMFDB trace graphs")
    parser.add_argument("--target", choices=["z1", "rank", "cm"], default="z1")
    parser.add_argument("--model", choices=["gcn", "chebconv"], default="gcn")
    parser.add_argument("--K", type=int, default=5, help="Chebyshev order for ChebConv")
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--all-gcn", action="store_true", help="Run GCN on all 3 targets")
    parser.add_argument("--all-chebconv", action="store_true", help="Run ChebConv on all 3 targets")
    parser.add_argument("--paradigm", choices=["trace_index", "multiplicative"], default="trace_index")
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--export-embeddings", action="store_true",
                        help="Export test-set embeddings and predictions to MODEL_DIR")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else DATA_DIR / "lmfdb" / f"gnn_{args.paradigm}"
    output_dir = Path(args.output_dir) if args.output_dir else MODEL_DIR

    if args.all_gcn:
        for target in ["z1", "rank", "cm"]:
            run_experiment(
                target=target, model_type="gcn", data_dir=data_dir,
                hidden_dim=args.hidden, num_layers=args.layers, K=args.K,
                epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                patience=args.patience, output_dir=output_dir,
                export_embeddings=args.export_embeddings,
            )
    elif args.all_chebconv:
        for target in ["z1", "rank", "cm"]:
            run_experiment(
                target=target, model_type="chebconv", data_dir=data_dir,
                hidden_dim=args.hidden, num_layers=args.layers, K=args.K,
                epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                patience=args.patience, output_dir=output_dir,
                export_embeddings=args.export_embeddings,
            )
    else:
        run_experiment(
            target=args.target, model_type=args.model, data_dir=data_dir,
            hidden_dim=args.hidden, num_layers=args.layers, K=args.K,
            epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            patience=args.patience, output_dir=output_dir,
            export_embeddings=args.export_embeddings,
        )


if __name__ == "__main__":
    main()
