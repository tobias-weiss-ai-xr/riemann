"""Train GNN on Pizer graphs: predict T_3 eigenvalue statistics from T_2 graph structure.

Pizer graph adjacency = Hecke operator T_2 on S_2(Gamma_0(p)).
Target = eigenvalue statistics of T_3 (mean, std, spectral_radius, etc.).
Key insight: Hecke operators commute, so T_2 structure encodes T_3 info.

Architecture: Weighted ChebConv + LayerNorm MLP readout (adapted from train_fullgraph_cheb.py)

Usage:
    python scripts/train_pizer_gnn.py --leave-one-out --epochs 200
    python scripts/train_pizer_gnn.py --baseline-only
    python scripts/train_pizer_gnn.py --K 5 --hidden 128 --leave-one-out
"""

import argparse
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Batch
from torch_geometric.nn import ChebConv, global_mean_pool, global_max_pool


# ────────────────────────────────────────────────────────────
# Model
# ────────────────────────────────────────────────────────────


class WeightedChebNet(nn.Module):
    """Full-graph ChebConv for small weighted Pizer graphs."""

    def __init__(self, node_dim=3, graph_stats_dim=6, K=3, hidden=64):
        super().__init__()
        self.K = K
        self.conv1 = ChebConv(node_dim, hidden, K)
        self.conv2 = ChebConv(hidden, hidden, K)
        self.conv3 = ChebConv(hidden, hidden, K)
        self.ln1 = nn.LayerNorm(hidden)
        self.ln2 = nn.LayerNorm(hidden)
        self.ln3 = nn.LayerNorm(hidden)
        # Readout: mean_pool + max_pool + graph_stats
        readout_dim = hidden * 2 + graph_stats_dim
        self.mlp = nn.Sequential(
            nn.Linear(readout_dim, hidden),
            nn.GELU(),
            nn.LayerNorm(hidden),
            nn.Linear(hidden, hidden // 2),
            nn.GELU(),
            nn.LayerNorm(hidden // 2),
            nn.Linear(hidden // 2, 9),  # 9 eigenvalue statistics
        )

    def forward(self, x, edge_index, edge_weight, batch, graph_stats):
        # graph_stats may be (B, 1, D) from PyG batching — squeeze to (B, D)
        if graph_stats.dim() == 3:
            graph_stats = graph_stats.squeeze(1)
        h = self.ln1(F.gelu(self.conv1(x, edge_index, edge_weight)))
        h2 = self.ln2(F.gelu(h + self.conv2(h, edge_index, edge_weight)))
        h = self.ln3(F.gelu(h2 + self.conv3(h2, edge_index, edge_weight)))
        mean_p = global_mean_pool(h, batch)
        max_p = global_max_pool(h, batch)
        return self.mlp(torch.cat([mean_p, max_p, graph_stats], dim=-1))


# ────────────────────────────────────────────────────────────
# Eigenvalue statistics
# ────────────────────────────────────────────────────────────

STAT_NAMES = ["mean", "std", "min", "max", "median", "Q25", "Q75", "radius", "pos_frac"]


def get_graph_targets(batch):
    """Extract per-graph y and target_mask from batched data.

    PyG concatenates 1D tensors along dim 0: y goes from (41,) per graph
    to (sum_dims,) in batch. We need to reshape to (num_graphs, max_dim).
    Each graph contributes max_dim values (padded), so just reshape.
    """
    y = batch.y
    mask = batch.target_mask
    max_dim = 41  # known from dataset construction

    if y.dim() == 1:
        # Concatenated: (sum_dims,) -> need (num_graphs, max_dim)
        # Use batch vector to count graphs
        num_graphs = batch.batch.max().item() + 1
        total = y.shape[0]
        if total == num_graphs * max_dim:
            # Clean reshape
            y = y.reshape(num_graphs, max_dim)
            mask = mask.reshape(num_graphs, max_dim)
        else:
            # Uneven dims — extract using batch vector
            y_list, mask_list = [], []
            for g in range(num_graphs):
                idx = batch.batch == g
                n = idx.sum().item()
                y_list.append(y[idx][:max_dim])  # take first max_dim values
                mask_list.append(mask[idx][:max_dim])
            y = torch.nn.utils.rnn.pad_sequence(
                y_list, batch_first=True, padding_value=0.0
            )
            mask = torch.nn.utils.rnn.pad_sequence(
                mask_list, batch_first=True, padding_value=False
            )
    return y, mask


def compute_stats(eigenvalues, mask):
    """Compute 9 summary statistics from masked eigenvalues. Returns (B, 9)."""
    if eigenvalues.dim() == 1:
        eigenvalues = eigenvalues.unsqueeze(0)
        mask = mask.unsqueeze(0)
    B = eigenvalues.shape[0]
    stats = torch.zeros(B, 9, device=eigenvalues.device)
    for i in range(B):
        m = mask[i].bool()
        if m.sum() < 2:
            continue
        e = eigenvalues[i, m]
        stats[i, 0] = e.mean()
        stats[i, 1] = e.std() if e.numel() > 1 else 0.0
        stats[i, 2] = e.min()
        stats[i, 3] = e.max()
        stats[i, 4] = e.median()
        se, _ = torch.sort(e)
        n = len(se)
        stats[i, 5] = se[n // 4]
        stats[i, 6] = se[3 * n // 4]
        stats[i, 7] = e.abs().max()
        stats[i, 8] = (e > 0).float().mean()
    return stats


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────


def make_batch(data_list, indices):
    return Batch.from_data_list([data_list[i] for i in indices])


def normalize_edge_weights(batch):
    """Degree-normalize edge weights for message passing."""
    ew = (
        batch.edge_attr[:, 0]
        if batch.edge_attr is not None
        else torch.ones(batch.edge_index.shape[1], device=batch.x.device)
    )
    deg = torch.zeros(batch.x.shape[0], device=batch.x.device)
    deg.scatter_add_(0, batch.edge_index[0], ew.abs())
    deg = deg.clamp(min=1e-8)
    return ew / deg[batch.edge_index[0]].sqrt()


def compute_r2(pred, target):
    ss_res = np.sum((target - pred) ** 2)
    ss_tot = np.sum((target - np.mean(target)) ** 2)
    return 1 - ss_res / ss_tot if ss_tot > 1e-10 else 0.0


# ────────────────────────────────────────────────────────────
# Training loop
# ────────────────────────────────────────────────────────────


def run_fold(model, train_batch, test_batch, epochs, lr, device, verbose=False):
    """Train model on train_batch, evaluate on test_batch. Returns best metrics."""
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_loss = float("inf")
    best_pred = best_target = None

    # Normalize edge weights BEFORE moving to device (avoid CPU/CUDA mismatch)
    train_ew = normalize_edge_weights(train_batch)
    test_ew = normalize_edge_weights(test_batch)

    # ── Target normalization (per-stat standardization) ──
    # Compute targets once on CPU before training
    tr_y, tr_mask = get_graph_targets(train_batch)
    te_y, te_mask = get_graph_targets(test_batch)
    tr_target_raw = compute_stats(tr_y, tr_mask)  # (n_train, 9)
    te_target_raw = compute_stats(te_y, te_mask)  # (n_test, 9)

    target_mean = tr_target_raw.mean(dim=0, keepdim=True)  # (1, 9)
    target_std = tr_target_raw.std(dim=0, keepdim=True).clamp(min=1e-8)  # (1, 9)
    tr_target = (tr_target_raw - target_mean) / target_std
    te_target = (te_target_raw - target_mean) / target_std

    train_batch = train_batch.to(device)
    test_batch = test_batch.to(device)
    train_ew = train_ew.to(device)
    test_ew = test_ew.to(device)
    tr_target = tr_target.to(device)

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        pred = model(
            train_batch.x,
            train_batch.edge_index,
            train_ew,
            train_batch.batch,
            train_batch.graph_stats,
        )
        loss = criterion(pred, tr_target)
        if verbose and (epoch % 20 == 0 or epoch == epochs - 1):
            print(
                f"    ep {epoch}: loss={loss.item():.6f} pred=[{pred.min():.4f},{pred.max():.4f}]"
            )
        loss.backward()
        optimizer.step()
        scheduler.step()

        if (epoch + 1) % 50 == 0 or epoch == epochs - 1:
            model.eval()
            with torch.no_grad():
                t_pred = model(
                    test_batch.x,
                    test_batch.edge_index,
                    test_ew,
                    test_batch.batch,
                    test_batch.graph_stats,
                )
                # Denormalize predictions for evaluation
                t_pred_raw = t_pred.cpu() * target_std.cpu() + target_mean.cpu()
                t_loss = criterion(t_pred_raw, te_target_raw)
                if t_loss < best_loss:
                    best_loss = t_loss
                    best_pred = t_pred_raw
                    best_target = te_target_raw

    return best_pred, best_target


# ────────────────────────────────────────────────────────────
# Baseline
# ────────────────────────────────────────────────────────────


def baseline_loo(data_list, loo_splits):
    """Linear baseline: graph_stats -> target_stats (LOO-CV)."""
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    all_stats = np.array(
        [compute_stats(g.y, g.target_mask).squeeze().numpy() for g in data_list]
    )
    all_feats = np.array([g.graph_stats.squeeze().numpy() for g in data_list])

    preds = np.zeros_like(all_stats)
    for s in loo_splits:
        ti = s["test_indices"][0]
        tri = s["train_indices"]
        sc = StandardScaler()
        X_train = sc.fit_transform(all_feats[tri])
        X_test = sc.transform(all_feats[ti : ti + 1])
        for j in range(9):
            m = Ridge(alpha=1.0)
            m.fit(X_train, all_stats[tri, j])
            preds[ti, j] = m.predict(X_test)[0]

    metrics = {}
    for i, name in enumerate(STAT_NAMES):
        metrics[name] = {"r2": compute_r2(preds[:, i], all_stats[:, i])}
    metrics["overall"] = {"r2": np.mean([m["r2"] for m in metrics.values()])}
    return metrics


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--K", type=int, default=3)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--leave-one-out", action="store_true")
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",  # Pizer graphs are tiny, no GPU needed
    )
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    ds_path = Path("/workspace/data/pizer/dataset_cross_l2_to_l3.pt")
    if not ds_path.exists():
        print(f"Dataset not found: {ds_path}")
        return

    ds = torch.load(ds_path, weights_only=False)
    data_list, splits = ds["data_list"], ds["splits"]
    loo_splits = [s for s in splits if s["split_type"] == "prime_loo"]
    random_split = [s for s in splits if s["split_type"] == "random_prime"]
    print(
        f"Dataset: {len(data_list)} graphs, {len(loo_splits)} LOO folds, {len(random_split)} random splits"
    )

    print(f"Dataset: {len(data_list)} graphs, {len(loo_splits)} LOO folds")

    # ── Baseline ──
    print(f"\n{'=' * 60}\nLINEAR BASELINE\n{'=' * 60}")
    base = baseline_loo(data_list, loo_splits)
    print(f"  Overall R²: {base['overall']['r2']:.4f}")
    for name in STAT_NAMES:
        print(f"  {name:10s}: R²={base[name]['r2']:+.4f}")

    if args.baseline_only:
        return

    # ── LOO-CV ──
    if args.leave_one_out:
        print(f"\n{'=' * 60}\nGNN LOO-CV ({len(loo_splits)} folds)\n{'=' * 60}")

        fold_metrics = []
        per_size = {"small (4-10)": [], "medium (11-20)": [], "large (21-41)": []}

        for i, split in enumerate(loo_splits):
            tri, tei = split["train_indices"], split["test_indices"]
            tp = split.get("test_prime", "?")
            dim = int(data_list[tei[0]].dim)

            train_b = make_batch(data_list, tri)
            test_b = make_batch(data_list, tei)

            model = WeightedChebNet(
                node_dim=train_b.x.shape[1],
                graph_stats_dim=int(
                    train_b.graph_stats.shape[-1]
                ),  # handle (B,1,D) or (B,D)
                K=args.K,
                hidden=args.hidden,
            )

            pred, target = run_fold(
                model,
                train_b,
                test_b,
                args.epochs,
                args.lr,
                args.device,
                verbose=(i == 0),
            )

            if pred is not None:
                metrics = {}
                for j, name in enumerate(STAT_NAMES):
                    p, t = pred[:, j].numpy(), target[:, j].numpy()
                    metrics[name] = {"r2": compute_r2(p, t)}
                metrics["overall"] = {
                    "r2": np.mean([m["r2"] for m in metrics.values()])
                }
                fold_metrics.append(metrics)

                # Size bucket
                if dim <= 10:
                    per_size["small (4-10)"].append(metrics["overall"]["r2"])
                elif dim <= 20:
                    per_size["medium (11-20)"].append(metrics["overall"]["r2"])
                else:
                    per_size["large (21-41)"].append(metrics["overall"]["r2"])

                if (i + 1) % 20 == 0 or i < 5:
                    print(
                        f"  [{i + 1:3d}/{len(loo_splits)}] p={tp:4d} dim={dim:2d} R²={metrics['overall']['r2']:+.4f}"
                    )

        # Aggregate
        print(f"\n{'─' * 60}")
        print(f"{'Stat':10s} {'GNN R²':>10s} {'Base R²':>10s} {'Delta':>10s}")
        print(f"{'─' * 10} {'─' * 10} {'─' * 10} {'─' * 10}")
        for name in STAT_NAMES + ["overall"]:
            gnn = np.mean([fm[name]["r2"] for fm in fold_metrics])
            b = base[name]["r2"]
            d = gnn - b
            star = " ★" if d > 0.01 else ""
            print(f"  {name:10s} {gnn:>+10.4f} {b:>+10.4f} {d:>+10.4f}{star}")

        print(f"\n  Per graph size:")
        for label, r2s in per_size.items():
            if r2s:
                print(f"    {label:20s}: R²={np.mean(r2s):+.4f} (n={len(r2s)})")

    # ── Random split ──
    if random_split:
        print(f"\n{'=' * 60}\nRANDOM PRIME SPLIT (80/20)\n{'=' * 60}")
        split = random_split[0]
        tri, tei = split["train_indices"], split["test_indices"]
        print(f"  Train: {len(tri)}, Test: {len(tei)}")

        train_b = make_batch(data_list, tri)
        test_b = make_batch(data_list, tei)

        model = WeightedChebNet(
            node_dim=train_b.x.shape[1],
            graph_stats_dim=int(train_b.graph_stats.shape[-1]),
            K=args.K,
            hidden=args.hidden,
        )

        pred, target = run_fold(
            model, train_b, test_b, args.epochs, args.lr, args.device
        )

        if pred is not None:
            print(f"\n  Random split results:")
            for j, name in enumerate(STAT_NAMES):
                r2 = compute_r2(pred[:, j].numpy(), target[:, j].numpy())
                print(f"    {name:10s}: R²={r2:+.4f}")

    # Save model
    save_path = Path("/workspace/data/models/pizer_hecke_gnn.pt")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "args": vars(args)}, save_path)
    print(f"\nModel saved to {save_path}")


if __name__ == "__main__":
    main()
