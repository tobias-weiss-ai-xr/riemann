"""
Thread M: Modern GNN architectures for trace-index graphs.

Adds GPSConv (GraphGPS hybrid) and TransformerConv to the architecture
search, comparing against the GAT baseline (R²=0.731).

Usage:
    python scripts/train_gnn_modern.py --all-architectures          # run all 3
    python scripts/train_gnn_modern.py --model gps                  # GPS only
    python scripts/train_gnn_modern.py --model transformer           # Transformer only
"""

from __future__ import annotations

"""
Thread M: Modern GNN architectures for trace-index graphs.

Adds GPSConv (GraphGPS hybrid) and TransformerConv to the architecture
search, comparing against the GAT baseline (R²=0.731).

Usage:
    python scripts/train_gnn_modern.py --all-architectures          # run all 3
    python scripts/train_gnn_modern.py --model gps                  # GPS only
    python scripts/train_gnn_modern.py --model transformer           # Transformer only

Data format: expects gnn_trace_index/ train/val/test/ directories with .npy files
(see build_lmfdb_gnn_dataset.py for generation).
"""

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

warnings.filterwarnings("ignore", message=".*torch-scatter.*")

from loguru import logger
from sklearn.metrics import r2_score
from torch import nn
from torch.utils.data import Dataset
from torch_geometric.loader import DataLoader as PyGDataLoader
from torch_geometric.data import Data
from torch_geometric.nn import (
    GATConv,
    GPSConv,
    TransformerConv,
    global_mean_pool,
    global_max_pool,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"
LMFDB_DIR = DATA_DIR / "lmfdb"

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)


# ---------------------------------------------------------------------------
# Dataset (copied from train_gnn_arch_search.py)
# ---------------------------------------------------------------------------

def precompute_arithmetic_features(N: int) -> dict[str, np.ndarray]:
    """Precompute ω(n), μ(n), d(n), λ(n) for n=1..N via sieve."""
    omega = np.zeros(N + 1, dtype=np.int32)
    mu = np.ones(N + 1, dtype=np.int32)
    d = np.ones(N + 1, dtype=np.int32)
    liouville = np.ones(N + 1, dtype=np.int32)
    spf = np.zeros(N + 1, dtype=np.int32)

    for i in range(2, N + 1):
        if spf[i] == 0:
            spf[i] = i
            for j in range(i * i, N + 1, i):
                if spf[j] == 0:
                    spf[j] = i

    for i in range(2, N + 1):
        p = spf[i]
        j = i // p
        if j % p == 0:
            mu[i] = 0
            omega[i] = omega[j]
            d[i] = d[j] * (1 + (i // (p * p)) % p)
        else:
            mu[i] = -mu[j]
            omega[i] = omega[j] + 1
            d[i] = d[j] * 2
        liouville[i] = -liouville[j] if p == i else -liouville[j if j % p != 0 else j // p]

    # Normalize: z-score
    arith = np.stack([
        omega[1:].astype(np.float32),
        mu[1:].astype(np.float32),
        np.log(d[1:] + 1).astype(np.float32),
        liouville[1:].astype(np.float32),
    ], axis=1)
    mean = arith.mean(axis=0, keepdims=True)
    std = arith.std(axis=0, keepdims=True) + 1e-8
    arith = (arith - mean) / std

    return {"tensor": torch.from_numpy(arith.astype(np.float32))}


class TraceIndexDataset(Dataset):
    """Loads pre-built trace-index graphs from gnn_trace_index/{split}/ files.

    Each graph has 1000 nodes, 3 edge types, and per-split .npy files.
    Adds enhanced node features (ω, μ, d, λ) on-the-fly.
    """

    def __init__(self, split_dir: Path, num_nodes: int = 1000,
                 use_edge_features: bool = True):
        super().__init__()
        self.num_nodes = num_nodes
        self.use_edge_features = use_edge_features

        self.x = np.load(str(split_dir / "x.npy"), mmap_mode="r")
        self.edge_index = np.load(str(split_dir / "edge_index.npy"), mmap_mode="r")
        self.edge_ptr = np.load(str(split_dir / "edge_ptr.npy"), mmap_mode="r")
        self.y = np.load(str(split_dir / "y_z1.npy"), mmap_mode="r").astype(np.float32)
        self.n_graphs = len(self.edge_ptr) - 1

        # Edge attributes: distance, sequential, prime-relation
        if use_edge_features:
            if (split_dir / "edge_attr.npy").exists():
                self.edge_attr = np.load(str(split_dir / "edge_attr.npy"), mmap_mode="r")
            else:
                self.edge_attr = self._compute_edge_attrs()
        else:
            self.edge_attr = None

        # Enhanced arithmetic features (shared across graphs)
        arith = precompute_arithmetic_features(num_nodes)
        self.arith_tensor = arith["tensor"]  # (N, 4)

    def _compute_edge_attrs(self):
        """Compute 3-dim edge features from edge_index structure."""
        ei = self.edge_index
        n_edges = ei.shape[1]
        attrs = np.zeros((n_edges, 3), dtype=np.float32)

        for i in range(n_edges):
            u, v = ei[0, i], ei[1, i]
            attrs[i, 0] = abs(int(u) - int(v))  # distance
            attrs[i, 1] = 1.0 if abs(int(u) - int(v)) == 1 else 0.0  # sequential
            # prime relation: v % u == 0 or u % v == 0
            if u > 0 and v > 0:
                attrs[i, 2] = 1.0 if (v % u == 0 or u % v == 0) and u != v else 0.0
        return attrs

    def __len__(self):
        return self.n_graphs

    def __getitem__(self, idx: int):
        node_start = idx * self.num_nodes
        node_end = node_start + self.num_nodes

        x = torch.from_numpy(np.array(self.x[node_start:node_end])).float()  # (N, 5)
        x = torch.cat([x, self.arith_tensor], dim=1)  # (N, 9)

        edge_start = int(self.edge_ptr[idx])
        edge_end = int(self.edge_ptr[idx + 1])
        edge_index = torch.from_numpy(self.edge_index[:, edge_start:edge_end].astype(np.int64))

        data = Data(x=x, edge_index=edge_index, y=torch.tensor([self.y[idx]], dtype=torch.float))

        if self.use_edge_features and self.edge_attr is not None:
            data.edge_attr = torch.from_numpy(self.edge_attr[edge_start:edge_end].astype(np.float32))

        return data


def get_dataloaders(data_dir: Path, batch_size: int = 128, num_workers: int = 2):
    train_ds = TraceIndexDataset(data_dir / "train")
    val_ds = TraceIndexDataset(data_dir / "val")
    test_ds = TraceIndexDataset(data_dir / "test")

    logger.info(f"Train: {len(train_ds)}, Val: {len(val_ds)}, Test: {len(test_ds)}")

    train_loader = PyGDataLoader(train_ds, batch_size=batch_size, shuffle=True,
                                  num_workers=num_workers, pin_memory=True)
    val_loader = PyGDataLoader(val_ds, batch_size=batch_size, shuffle=False,
                                num_workers=num_workers, pin_memory=True)
    test_loader = PyGDataLoader(test_ds, batch_size=batch_size, shuffle=False,
                                 num_workers=num_workers, pin_memory=True)
    return train_loader, val_loader, test_loader


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TraceIndexGPS(nn.Module):
    """GraphGPS: GPSConv with GATConv as local MPNN + global Transformer.

    Each GPSConv layer combines a local GAT message-passing step with
    a multi-head self-attention (Transformer) over the full node set.
    """

    def __init__(
        self,
        node_feat_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 3,
        num_targets: int = 1,
        edge_feat_dim: int = 3,
        heads: int = 4,
    ):
        super().__init__()
        self.node_encoder = nn.Linear(node_feat_dim, hidden_dim)
        self.layers = nn.ModuleList()
        self.norms = nn.ModuleList()

        for _ in range(num_layers):
            # Local MPNN: GATConv as the message-passing backbone
            local_conv = GATConv(
                hidden_dim, hidden_dim // heads, heads=heads,
                edge_dim=edge_feat_dim, concat=True,
            )
            # GPSConv wraps local conv + global Transformer attention
            gps_layer = GPSConv(
                channels=hidden_dim,
                conv=local_conv,
                heads=heads,
                dropout=0.1,
                act="relu",
                norm="batch_norm",
                attn_type="multihead",
            )
            self.layers.append(gps_layer)
            self.norms.append(nn.BatchNorm1d(hidden_dim))

        self.head = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_targets),
        )

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        edge_attr = getattr(data, "edge_attr", None)

        x = self.node_encoder(x)
        for layer, norm in zip(self.layers, self.norms):
            x = layer(x, edge_index, batch, edge_attr=edge_attr)
            x = norm(x).relu()
            x = F.dropout(x, p=0.1, training=self.training)

        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )
        return self.head(readout)


class TraceIndexTransformer(nn.Module):
    """TransformerConv: graph transformer with edge features.

    TransformerConv supports edge features natively and learns
    attention weights for each edge type.
    """

    def __init__(
        self,
        node_feat_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 3,
        num_targets: int = 1,
        edge_feat_dim: int = 3,
        heads: int = 4,
    ):
        super().__init__()
        self.node_encoder = nn.Linear(node_feat_dim, hidden_dim)
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        for i in range(num_layers):
            in_dim = hidden_dim
            out_dim = hidden_dim // heads
            if i < num_layers - 1:
                conv = TransformerConv(
                    in_dim, out_dim, heads=heads,
                    edge_dim=edge_feat_dim,
                    concat=True,
                    beta=True,
                    dropout=0.1,
                )
                norm_dim = hidden_dim
            else:
                conv = TransformerConv(
                    hidden_dim, hidden_dim // 2, heads=1,
                    edge_dim=edge_feat_dim,
                    concat=False,
                    beta=True,
                    dropout=0.1,
                )
                norm_dim = hidden_dim // 2

            self.convs.append(conv)
            self.norms.append(nn.BatchNorm1d(norm_dim))

        self.head = nn.Sequential(
            nn.Linear(norm_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_targets),
        )

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        edge_attr = getattr(data, "edge_attr", None)

        x = self.node_encoder(x)
        for conv, norm in zip(self.convs, self.norms):
            x = conv(x, edge_index, edge_attr=edge_attr)
            x = norm(x).relu()
            x = F.dropout(x, p=0.1, training=self.training)

        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )
        return self.head(readout)


def build_model(
    model_type: str,
    node_feat_dim: int,
    hidden_dim: int,
    num_layers: int,
    num_targets: int,
    edge_feat_dim: int = 3,
    heads: int = 4,
) -> nn.Module:
    if model_type == "gps":
        return TraceIndexGPS(node_feat_dim, hidden_dim, num_layers, num_targets,
                              edge_feat_dim=edge_feat_dim, heads=heads)
    elif model_type == "transformer":
        return TraceIndexTransformer(node_feat_dim, hidden_dim, num_layers, num_targets,
                                     edge_feat_dim=edge_feat_dim, heads=heads)
    else:
        raise ValueError(f"Unknown model: {model_type}")


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_epoch(model, loader, optimizer, device):
    model.train()
    total_loss = 0.0
    for batch in loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        out = model(batch)
        loss = F.mse_loss(out.squeeze(), batch.y.squeeze())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item() * batch.num_graphs
    return total_loss


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    all_preds, all_targets = [], []
    for batch in loader:
        batch = batch.to(device)
        out = model(batch)
        all_preds.append(out.squeeze().cpu())
        all_targets.append(batch.y.squeeze().cpu())
    preds = torch.cat(all_preds)
    targets = torch.cat(all_targets)
    return float(r2_score(targets.numpy(), preds.numpy()))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_experiment(
    model_type: str,
    data_dir: Path,
    epochs: int = 100,
    hidden_dim: int = 128,
    num_layers: int = 3,
    heads: int = 4,
    batch_size: int = 128,
    patience: int = 15,
    lr: float = 1e-3,
    weight_decay: float = 1e-5,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

    train_loader, val_loader, test_loader = get_dataloaders(data_dir, batch_size=batch_size)
    sample_batch = next(iter(train_loader))
    node_feat_dim = sample_batch.x.shape[1]
    logger.info(f"Node feature dim: {node_feat_dim}")

    model = build_model(model_type, node_feat_dim, hidden_dim, num_layers,
                         num_targets=1, edge_feat_dim=3, heads=heads)
    model = model.to(device)
    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"{model_type}: {n_params:,} parameters")

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_r2 = -float("inf")
    best_state = None
    stall = 0
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device)
        scheduler.step()

        if epoch % 5 == 0:
            val_r2 = evaluate(model, val_loader, device)
            logger.info(
                f"Epoch {epoch:3d}/{epochs} | Loss: {train_loss:.4f} | Val R²: {val_r2:.4f}"
            )

            if val_r2 > best_val_r2:
                best_val_r2 = val_r2
                best_state = model.state_dict()
                stall = 0
            else:
                stall += 1
                if stall >= patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break

    # Restore best and test
    if best_state is not None:
        model.load_state_dict(best_state)

    test_r2 = evaluate(model, test_loader, device)
    elapsed = time.time() - t0

    logger.info(f"\n{'='*50}")
    logger.info(f"{model_type.upper()} RESULTS")
    logger.info(f"{'='*50}")
    logger.info(f"Test R²: {test_r2:.4f}")
    logger.info(f"Best Val R²: {best_val_r2:.4f}")
    logger.info(f"Params: {n_params:,}")
    logger.info(f"Time: {elapsed:.1f}s")

    # Save
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = MODEL_DIR / f"modern_{model_type}.pt"
    torch.save({"model_state": best_state, "test_r2": test_r2,
                 "val_r2": best_val_r2, "params": n_params}, ckpt_path)
    logger.info(f"Saved to {ckpt_path}")

    return {
        "model": model_type,
        "test_r2": test_r2,
        "val_r2": best_val_r2,
        "params": n_params,
        "time_s": elapsed,
        "hidden_dim": hidden_dim,
        "num_layers": num_layers,
        "heads": heads,
    }


def main():
    parser = argparse.ArgumentParser(description="Thread M: modern GNN architectures")
    parser.add_argument("--model", choices=["gps", "transformer", "all"], default="all")
    parser.add_argument("--all-architectures", action="store_true", default=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--num-layers", type=int, default=3)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Path to gnn_trace_index/ dir (default: data/lmfdb/gnn_trace_index)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else LMFDB_DIR / "gnn_trace_index"
    logger.info(f"Data dir: {data_dir}")

    models_to_run = []
    if args.model == "all":
        models_to_run = ["gps", "transformer"]
    else:
        models_to_run = [args.model]

    results = []
    for mtype in models_to_run:
        logger.info(f"\n{'#'*60}")
        logger.info(f"# Running: {mtype}")
        logger.info(f"{'#'*60}")
        try:
            result = run_experiment(
                model_type=mtype,
                data_dir=data_dir,
                epochs=args.epochs,
                hidden_dim=args.hidden_dim,
                num_layers=args.num_layers,
                heads=args.heads,
                batch_size=args.batch_size,
                lr=args.lr,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"{mtype} failed: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("THREAD M SUMMARY")
    logger.info(f"{'='*50}")
    for r in results:
        logger.info(f"  {r['model']:12s} | Test R²: {r['test_r2']:.4f} | "
                     f"Val R²: {r['val_r2']:.4f} | Params: {r['params']:,} | "
                     f"Time: {r['time_s']:.1f}s")

    result_path = MODEL_DIR / "thread_m_results.json"
    result_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Results saved to {result_path}")


if __name__ == "__main__":
    main()
