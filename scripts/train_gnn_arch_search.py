"""
Thread B: GNN architecture search on LMFDB trace-index graphs.

Extends Experiment 12 with GATConv, GINConv (GINEConv), richer node features
(omega, mu, divisor count, Liouville function), and edge features.

Usage:
    python scripts/train_gnn_arch_search.py --all-architectures
    python scripts/train_gnn_arch_search.py --all-targets --model gat
    python scripts/train_gnn_arch_search.py --target z1 --model gin
    python scripts/train_gnn_arch_search.py --compare        # run all 4 x 3 = 12 experiments
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
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
from torch.utils.data import Dataset
from torch_geometric.loader import DataLoader as PyGDataLoader
from torch_geometric.data import Data
from torch_geometric.nn import (
    ChebConv,
    GATConv,
    GCNConv,
    GINEConv,
    global_mean_pool,
    global_max_pool,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"
LMFDB_DIR = DATA_DIR / "lmfdb"

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
# Arithmetic functions (precomputed for n=1..N)
# ---------------------------------------------------------------------------


def precompute_arithmetic_features(N: int) -> dict[str, np.ndarray]:
    """Precompute omega, mu, d, liouville for n=1..N.

    Returns dict with keys 'omega', 'mu', 'd', 'liouville', each (N+1,)
    array indexed by n (index 0 is unused/padding).
    """
    omega = np.zeros(N + 1, dtype=np.int32)
    mu = np.ones(N + 1, dtype=np.int32)
    d = np.ones(N + 1, dtype=np.int32)  # divisor count
    liouville = np.ones(N + 1, dtype=np.int32)
    smallest_prime_factor = np.zeros(N + 1, dtype=np.int32)
    prime_count = np.zeros(N + 1, dtype=np.int32)  # total prime factors w/ mult

    for i in range(2, N + 1):
        if smallest_prime_factor[i] == 0:  # i is prime
            smallest_prime_factor[i] = i
            for j in range(i * i, N + 1, i):
                if smallest_prime_factor[j] == 0:
                    smallest_prime_factor[j] = i

    for i in range(2, N + 1):
        p = smallest_prime_factor[i]
        j = i // p
        if j % p == 0:
            # p^2 divides i
            mu[i] = 0
            omega[i] = omega[j]
            prime_count[i] = prime_count[j] + 1
        else:
            mu[i] = -mu[j]
            omega[i] = omega[j] + 1
            prime_count[i] = prime_count[j] + 1

    # Divisor count via prime factorization
    # d(n) = product (e_i + 1) over prime powers p_i^e_i || n
    d[1] = 1
    for i in range(2, N + 1):
        p = smallest_prime_factor[i]
        j = i // p
        exp = 1
        while j % p == 0:
            j //= p
            exp += 1
        d[i] = d[j] * (exp + 1)

    liouville = np.where(prime_count % 2 == 0, 1, -1)

    return {
        "omega": omega.astype(np.float32),
        "mu": mu.astype(np.float32),
        "d": d.astype(np.float32),
        "liouville": liouville.astype(np.float32),
    }


# ---------------------------------------------------------------------------
# Edge feature construction
# ---------------------------------------------------------------------------


def build_edge_features(
    edge_index: torch.Tensor,
    N: int,
) -> torch.Tensor:
    """Build 3-dim edge features from node indices.

    Features:
      [0]: normalized distance |i - j| / N
      [1]: is_sequential (|i-j| == 1) 0/1
      [2]: is_prime_related (i+1 divides j+1 or vice versa) 0/1
    """
    src, dst = edge_index[0], edge_index[1]
    n_src = src + 1  # 1-indexed
    n_dst = dst + 1

    dist = (n_src - n_dst).abs().float() / N
    sequential = (dist * N <= 1.0 + 1e-6).float()

    # Check divisibility
    divides = (n_src % n_dst == 0) | (n_dst % n_src == 0)
    prime_related = divides.float()

    edge_attr = torch.stack([dist, sequential, prime_related], dim=1)
    return edge_attr


# ---------------------------------------------------------------------------
# Enhanced dataset wrapper
# ---------------------------------------------------------------------------


class AugmentedTraceIndexDataset(Dataset):
    """Wraps CompactGraphDataset, appending arithmetic node features
    and computing edge features on the fly."""

    def __init__(
        self,
        split_dir: Path,
        target: str,
        num_nodes: int,
        arithmetic: dict[str, np.ndarray],
        use_enhanced_features: bool = True,
        use_edge_features: bool = True,
    ):
        self.num_nodes = num_nodes
        self.arithmetic = arithmetic
        self.use_enhanced_features = use_enhanced_features
        self.use_edge_features = use_edge_features

        # Load mmap arrays
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

        # Precompute arithmetic feature tensor for all nodes (shared across graphs)
        if use_enhanced_features:
            self._build_arithmetic_tensor()
        else:
            self.arith_tensor = None

    def _build_arithmetic_tensor(self):
        """Build (N, 4) tensor of arithmetic features, normalized."""
        N = self.num_nodes
        a = self.arithmetic
        arith = np.stack(
            [
                a["omega"][1 : N + 1] / np.log(np.arange(1, N + 1) + 1),  # omega / log(n)
                a["mu"][1 : N + 1].astype(np.float32),  # mu(n) ∈ {-1, 0, 1}
                np.log(a["d"][1 : N + 1] + 1) / np.log(np.arange(1, N + 1) + 1),  # log d(n) / log n
                a["liouville"][1 : N + 1].astype(np.float32),  # λ(n) ∈ {-1, 1}
            ],
            axis=1,
        )
        # Normalize each column to [0, 1] or standardize
        mean = arith.mean(axis=0, keepdims=True)
        std = arith.std(axis=0, keepdims=True) + 1e-8
        arith = (arith - mean) / std
        self.arith_tensor = torch.from_numpy(arith.astype(np.float32))  # (N, 4)

    def __len__(self):
        return self.n_graphs

    def __getitem__(self, idx: int):
        node_start = idx * self.num_nodes
        node_end = node_start + self.num_nodes

        x = torch.from_numpy(np.array(self.x[node_start:node_end]))  # (N, 5)

        if self.arith_tensor is not None:
            x = torch.cat([x, self.arith_tensor], dim=1)  # (N, 9)

        edge_start = int(self.edge_ptr[idx])
        edge_end = int(self.edge_ptr[idx + 1])
        edge_index = torch.from_numpy(
            self.edge_index[:, edge_start:edge_end].astype(np.int64)
        )

        data = Data(
            x=x,
            edge_index=edge_index,
            y=torch.tensor(
                [self.y[idx]],
                dtype=torch.float32 if self.y.dtype == np.float32 else torch.long,
            ),
        )

        if self.use_edge_features:
            data.edge_attr = build_edge_features(edge_index, self.num_nodes)

        return data


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

NUM_BASE_FEATURES = 5  # original: trace, log_abs, sign, n/N, is_prime
NUM_ARITH_FEATURES = 4  # added: omega, mu, d, liouville


class TraceIndexGCN(nn.Module):
    """GCNConv baseline (same as exp 12 but with optional richer features)."""

    def __init__(
        self,
        node_feat_dim: int,
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
        return (logits, readout) if return_embeddings else logits


class TraceIndexChebConv(nn.Module):
    """ChebConv baseline (same as exp 12 but with optional richer features)."""

    def __init__(
        self,
        node_feat_dim: int,
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
        return (logits, readout) if return_embeddings else logits


class TraceIndexGAT(nn.Module):
    """GATConv with edge feature support via edge_dim."""

    def __init__(
        self,
        node_feat_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 3,
        num_targets: int = 1,
        edge_feat_dim: int = 0,
        heads: int = 4,
    ):
        super().__init__()
        self.heads = heads
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        for i in range(num_layers):
            in_dim = node_feat_dim if i == 0 else hidden_dim
            out_dim = hidden_dim // heads
            if i < num_layers - 1:
                # Intermediate layers: multi-head, concat
                conv = GATConv(
                    in_dim, out_dim, heads=heads,
                    edge_dim=edge_feat_dim if edge_feat_dim > 0 else None,
                    concat=True,
                )
                norm_in = hidden_dim
            else:
                # Last layer: single head, mean aggregation
                conv = GATConv(
                    hidden_dim, hidden_dim // 2, heads=1,
                    edge_dim=edge_feat_dim if edge_feat_dim > 0 else None,
                    concat=False,
                )
                norm_in = hidden_dim // 2

            self.convs.append(conv)
            self.norms.append(nn.BatchNorm1d(norm_in))

        self.head = nn.Sequential(
            nn.Linear(norm_in * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_targets),
        )
        self._final_dim = norm_in

    def forward(self, data, return_embeddings: bool = False):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        edge_attr = data.edge_attr if hasattr(data, "edge_attr") else None

        for i, (conv, norm) in enumerate(zip(self.convs, self.norms)):
            if edge_attr is not None and hasattr(conv, "edge_dim") and conv.edge_dim is not None:
                x = conv(x, edge_index, edge_attr=edge_attr)
            else:
                x = conv(x, edge_index)
            x = norm(x).relu()
            x = F.dropout(x, p=0.1, training=self.training)

        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )
        logits = self.head(readout)
        return (logits, readout) if return_embeddings else logits


class TraceIndexGIN(nn.Module):
    """GINEConv with edge feature support."""

    def __init__(
        self,
        node_feat_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 3,
        num_targets: int = 1,
        edge_feat_dim: int = 0,
    ):
        super().__init__()
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        for i in range(num_layers):
            in_dim = node_feat_dim if i == 0 else hidden_dim
            mlp = nn.Sequential(
                nn.Linear(in_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            )
            if edge_feat_dim > 0:
                conv = GINEConv(mlp, edge_dim=edge_feat_dim)
            else:
                # GINConv without edge features: use nn.Identity as edge_nn
                from torch_geometric.nn import GINConv as GINConvSimple
                conv = GINConvSimple(mlp)
            self.convs.append(conv)
            self.norms.append(nn.BatchNorm1d(hidden_dim))

        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_targets),
        )

    def forward(self, data, return_embeddings: bool = False):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        edge_attr = data.edge_attr if hasattr(data, "edge_attr") and data.edge_attr is not None else None

        for conv, norm in zip(self.convs, self.norms):
            if edge_attr is not None and isinstance(conv, GINEConv):
                x = conv(x, edge_index, edge_attr=edge_attr)
            else:
                x = conv(x, edge_index)
            x = norm(x).relu()
            x = F.dropout(x, p=0.1, training=self.training)

        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )
        logits = self.head(readout)
        return (logits, readout) if return_embeddings else logits


def build_model(
    model_type: str,
    node_feat_dim: int,
    hidden_dim: int,
    num_layers: int,
    K: int,
    num_targets: int,
    edge_feat_dim: int = 3,
    heads: int = 4,
) -> nn.Module:
    """Build model by type."""
    if model_type == "gcn":
        return TraceIndexGCN(node_feat_dim, hidden_dim, num_layers, num_targets)
    elif model_type == "chebconv":
        return TraceIndexChebConv(node_feat_dim, hidden_dim, K, num_layers, num_targets)
    elif model_type == "gat":
        return TraceIndexGAT(node_feat_dim, hidden_dim, num_layers, num_targets,
                             edge_feat_dim=edge_feat_dim, heads=heads)
    elif model_type == "gin":
        return TraceIndexGIN(node_feat_dim, hidden_dim, num_layers, num_targets,
                              edge_feat_dim=edge_feat_dim)
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
    mse = mean_squared_error(targets, preds)
    mae = mean_absolute_error(targets, preds)
    r2 = r2_score(targets, preds)
    return {"mse": mse, "mae": mae, "r2": r2}


def compute_classification_metrics(preds, targets):
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
# Single experiment runner
# ---------------------------------------------------------------------------


def run_experiment(
    target: str,
    model_type: str,
    data_dir: Path,
    arithmetic: dict[str, np.ndarray],
    hidden_dim: int,
    num_layers: int,
    K: int,
    epochs: int,
    batch_size: int,
    lr: float,
    patience: int,
    output_dir: Path,
    use_enhanced_features: bool = True,
    use_edge_features: bool = True,
    heads: int = 4,
    export_embeddings: bool = False,
):
    """Run a single training experiment."""
    task_type = "regression" if target == "z1" else "classification"
    num_targets = 1 if task_type == "regression" else 3 if target == "rank" else 2
    target_names = {"z1": "z1 Regression", "rank": "Analytic Rank Clf", "cm": "CM Clf"}
    feat_tag = "enh" if use_enhanced_features else "base"
    ef_tag = "+ef" if use_edge_features else ""
    model_tag = f"{model_type.upper()}[{feat_tag}{ef_tag}]"

    print_header(
        f"Thread B: {model_tag} on {target_names[target]}"
    )

    # Load config
    with open(data_dir / "metadata.json") as f:
        meta = json.load(f)
    num_nodes = meta["num_nodes_per_graph"]

    # Build datasets
    logger.info("Loading augmented datasets...")
    train_ds = AugmentedTraceIndexDataset(
        data_dir / "train", target, num_nodes, arithmetic,
        use_enhanced_features=use_enhanced_features,
        use_edge_features=use_edge_features,
    )
    val_ds = AugmentedTraceIndexDataset(
        data_dir / "val", target, num_nodes, arithmetic,
        use_enhanced_features=use_enhanced_features,
        use_edge_features=use_edge_features,
    )
    test_ds = AugmentedTraceIndexDataset(
        data_dir / "test", target, num_nodes, arithmetic,
        use_enhanced_features=use_enhanced_features,
        use_edge_features=use_edge_features,
    )

    logger.info(f"  train={len(train_ds)}, val={len(val_ds)}, test={len(test_ds)}")

    # Get feature dimensions
    sample = train_ds[0]
    node_feat_dim = sample.x.shape[1]
    edge_feat_dim = sample.edge_attr.shape[1] if (
        use_edge_features and hasattr(sample, "edge_attr")
        and sample.edge_attr is not None
    ) else 0
    logger.info(f"  node_feat_dim={node_feat_dim}, edge_feat_dim={edge_feat_dim}")

    # Data loaders
    train_loader = PyGDataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=0
    )
    val_loader = PyGDataLoader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=0
    )
    test_loader = PyGDataLoader(
        test_ds, batch_size=batch_size, shuffle=False, num_workers=0
    )

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Build model
    model = build_model(
        model_type, node_feat_dim, hidden_dim, num_layers,
        K, num_targets, edge_feat_dim, heads,
    ).to(device)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info(
        f"Model: {model_type.upper()}(hidden={hidden_dim}, layers={num_layers}, "
        f"K={K}, heads={heads})"
    )
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
            best_state = {
                k: v.cpu().clone() for k, v in model.state_dict().items()
            }
            best_epoch = epoch
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= patience:
            logger.info(f"  Early stopping at epoch {epoch} (patience={patience})")
            break

    elapsed = time.time() - t0
    logger.info(
        f"  Best model at epoch {best_epoch} "
        f"(val_loss={best_val_loss:.4f}, time={elapsed:.1f}s)"
    )

    # Test evaluation
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
        test_metrics = metrics

    print()

    # Save checkpoint
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_name = f"arch_search_{model_type}_{target}_{feat_tag}{ef_tag}.pt"
    ckpt_path = output_dir / ckpt_name
    torch.save(
        {
            "model_state_dict": best_state,
            "config": {
                "model_type": model_type,
                "hidden_dim": hidden_dim,
                "num_layers": num_layers,
                "K": K,
                "heads": heads,
                "node_feat_dim": node_feat_dim,
                "edge_feat_dim": edge_feat_dim,
                "num_targets": num_targets,
                "use_enhanced_features": use_enhanced_features,
                "use_edge_features": use_edge_features,
            },
            "best_epoch": best_epoch,
            "val_loss": best_val_loss,
            "test_metrics": {
                k: float(v) if isinstance(v, (np.floating, float)) else v
                for k, v in test_metrics.items()
            },
            "target": target,
        },
        ckpt_path,
    )
    logger.info(f"  Saved checkpoint: {ckpt_path}")

    return test_metrics, model_tag


# ---------------------------------------------------------------------------
# Comparison runner
# ---------------------------------------------------------------------------


def run_comparison(target: str, data_dir: Path, arithmetic: dict[str, np.ndarray],
                   args):
    """Run all 4 architectures for a given target and produce a summary table."""
    results = []

    architectures = []
    if args.gcn:
        architectures.append("gcn")
    if args.chebconv:
        architectures.append("chebconv")
    if args.gat:
        architectures.append("gat")
    if args.gin:
        architectures.append("gin")
    if args.all_architectures or args.compare:
        architectures = ["gcn", "chebconv", "gat", "gin"]

    for model_type in architectures:
        metrics, tag = run_experiment(
            target=target,
            model_type=model_type,
            data_dir=data_dir,
            arithmetic=arithmetic,
            hidden_dim=args.hidden,
            num_layers=args.layers,
            K=args.K,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            patience=args.patience,
            output_dir=Path(args.output_dir) if args.output_dir else MODEL_DIR,
            use_enhanced_features=not args.no_enhanced,
            use_edge_features=not args.no_edge_features,
            heads=args.heads,
        )
        results.append((tag, metrics))

    # Summary table
    print()
    print_header(f"Architecture Comparison: {target}")
    task_type = "regression" if target == "z1" else "classification"

    if task_type == "regression":
        print(f"  {'Architecture':<28s} | {'R²':>8s} | {'MAE':>8s} | {'MSE':>8s}")
        print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 8}")
        for tag, m in results:
            print(
                f"  {tag:<28s} | {fmt(m['r2']):>8s} | {fmt(m['mae']):>8s} | {fmt(m['mse']):>8s}"
            )
    else:
        print(f"  {'Architecture':<28s} | {'Acc':>8s} | {'F1(mac)':>8s} | {'F1(wt)':>8s}")
        print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 8}")
        for tag, m in results:
            print(
                f"  {tag:<28s} | {fmt(m['accuracy']):>8s} | "
                f"{fmt(m['f1_macro']):>8s} | {fmt(m['f1_weighted']):>8s}"
            )

    print()
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Thread B: GNN architecture search on trace-index graphs"
    )
    # Architecture selection
    parser.add_argument("--gcn", action="store_true", help="Run GCN")
    parser.add_argument("--chebconv", action="store_true", help="Run ChebConv")
    parser.add_argument("--gat", action="store_true", help="Run GAT")
    parser.add_argument("--gin", action="store_true", help="Run GIN")
    parser.add_argument("--all-architectures", action="store_true",
                        help="Run all 4 architectures for given target")
    parser.add_argument("--compare", action="store_true",
                        help="Run ALL 4 architectures on ALL 3 targets (12 experiments)")

    # Target
    parser.add_argument("--target", choices=["z1", "rank", "cm"], default="z1")
    parser.add_argument("--all-targets", action="store_true",
                        help="Run on all 3 targets")

    # Model hyperparameters
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--K", type=int, default=5, help="Chebyshev order")
    parser.add_argument("--heads", type=int, default=4, help="GAT attention heads")

    # Training
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=20)

    # Features
    parser.add_argument("--no-enhanced", action="store_true",
                        help="Disable arithmetic node features (use baseline 5-dim only)")
    parser.add_argument("--no-edge-features", action="store_true",
                        help="Disable edge features")

    # Paths
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)

    args = parser.parse_args()

    # Resolve data dir
    data_dir = Path(args.data_dir) if args.data_dir else LMFDB_DIR / "gnn_trace_index"
    output_dir = Path(args.output_dir) if args.output_dir else MODEL_DIR

    # Precompute arithmetic features
    logger.info("Precomputing arithmetic features for n=1..1000...")
    arithmetic = precompute_arithmetic_features(1000)
    logger.info(
        f"  omega: {arithmetic['omega'][1:].mean():.3f} ± {arithmetic['omega'][1:].std():.3f}"
    )
    logger.info(f"  mu: {arithmetic['mu'][1:].mean():.3f} ± {arithmetic['mu'][1:].std():.3f}")
    logger.info(f"  d: {arithmetic['d'][1:].mean():.1f} ± {arithmetic['d'][1:].std():.1f}")
    logger.info(f"  liouville: {arithmetic['liouville'][1:].mean():.3f} ± {arithmetic['liouville'][1:].std():.3f}")

    # Run experiments
    if args.compare:
        targets = ["z1", "rank", "cm"]
        for t in targets:
            run_comparison(t, data_dir, arithmetic, args)
    elif args.all_targets:
        for t in ["z1", "rank", "cm"]:
            if args.all_architectures or (args.gcn or args.chebconv or args.gat or args.gin):
                run_comparison(t, data_dir, arithmetic, args)
            else:
                metrics, tag = run_experiment(
                    target=t, model_type="gcn", data_dir=data_dir,
                    arithmetic=arithmetic, hidden_dim=args.hidden,
                    num_layers=args.layers, K=args.K,
                    epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                    patience=args.patience, output_dir=output_dir,
                    use_enhanced_features=not args.no_enhanced,
                    use_edge_features=not args.no_edge_features,
                    heads=args.heads,
                )
    else:
        if args.all_architectures or (args.gcn or args.chebconv or args.gat or args.gin):
            run_comparison(args.target, data_dir, arithmetic, args)
        else:
            run_experiment(
                target=args.target, model_type="gcn", data_dir=data_dir,
                arithmetic=arithmetic, hidden_dim=args.hidden,
                num_layers=args.layers, K=args.K,
                epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                patience=args.patience, output_dir=output_dir,
                use_enhanced_features=not args.no_enhanced,
                use_edge_features=not args.no_edge_features,
                heads=args.heads,
            )


if __name__ == "__main__":
    main()
