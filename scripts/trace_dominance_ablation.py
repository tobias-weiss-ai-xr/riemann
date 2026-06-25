"""Experiment Y: Trace dominance ablation study.

Compares models for z1 (first L-function zero) prediction:
1. MLP: takes trace vector [trace_2, trace_3, ..., trace_97] directly
2. MLP-shuffled: traces with random noise added (simulates random graph mixing)
3. MLP-feature-shuffle: traces with COLUMNS randomly permuted (destroys trace identity)

If all three perform similarly, graph structure is irrelevant — trace vector alone
contains the signal. The GAT R²=0.731 vs MLP R²=0.714 gap (1.7%) may be just noise.

Reference results (from prior experiments):
- GAT on trace-index graph: R² = 0.731 (Experiment L)
- MLP (multi-task zeros):  R² = 0.714 (Experiment L)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from loguru import logger
from sklearn.model_selection import train_test_split

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37,
          41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


def load_dataset(csv_path: str, normalize: bool = True):
    """Load trace features (at primes) and z1 target.

    If normalize=True, applies Sato-Tate normalization:
        x_p = trace_p / (2 * dim * sqrt(p)),  clipped to [-1, 1]
    This is the standard normalization used in Experiment F / multi-task zeros.
    """
    df = pd.read_csv(csv_path)
    trace_cols = [f"trace_{p}" for p in PRIMES]
    X = df[trace_cols].values.astype(np.float32)
    y = df["z1"].values.astype(np.float32)
    dim = df["dim"].values.astype(np.float32)

    if normalize:
        # x_p = trace_p / (2 * dim * sqrt(p)), clipped to [-1, 1]
        sqrt_p = np.array([np.sqrt(p) for p in PRIMES], dtype=np.float32)
        X = X / (2.0 * dim[:, None] * sqrt_p[None, :])
        X = np.clip(X, -1.0, 1.0)

    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    return X[mask], y[mask]


class TraceMLP(nn.Module):
    def __init__(self, input_dim: int = 25, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_mlp(X_tr, y_tr, X_te, y_te, epochs: int = 200, lr: float = 1e-3) -> float:
    """Train MLP, return test R²."""
    torch.manual_seed(0)
    model = TraceMLP(X_tr.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    Xt = torch.from_numpy(X_tr)
    yt = torch.from_numpy(y_tr)
    Xv = torch.from_numpy(X_te)
    yv_np = y_te
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        pred = model(Xt)
        loss = loss_fn(pred, yt)
        loss.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        pred_test = model(Xv).numpy()
    ss_res = float(np.sum((yv_np - pred_test) ** 2))
    ss_tot = float(np.sum((yv_np - yv_np.mean()) ** 2))
    return 1.0 - ss_res / ss_tot


def train_mlp_noisy(X_tr, y_tr, X_te, y_te, epochs: int = 200, noise_std: float = 0.1) -> float:
    """MLP with additive Gaussian noise on trace features (simulates random graph mixing)."""
    rng = np.random.RandomState(42)
    X_tr_n = X_tr + rng.randn(*X_tr.shape).astype(np.float32) * noise_std
    rng2 = np.random.RandomState(99)
    X_te_n = X_te + rng2.randn(*X_te.shape).astype(np.float32) * noise_std
    return train_mlp(X_tr_n, y_tr, X_te_n, y_te, epochs=epochs)


def train_mlp_colshuf(X_tr, y_tr, X_te, y_te, epochs: int = 200) -> float:
    """MLP with COLUMNS randomly permuted (destroys per-prime identity but keeps magnitude stats)."""
    rng = np.random.RandomState(7)
    perm = rng.permutation(X_tr.shape[1])
    return train_mlp(X_tr[:, perm], y_tr, X_te[:, perm], y_te, epochs=epochs)


def main():
    parser = argparse.ArgumentParser(description="Trace dominance ablation")
    parser.add_argument("--csv", default="/workspace/data/lmfdb/lmfdb_zeros_ml.csv")
    parser.add_argument("--output", default="/workspace/data/trace_ablation/")
    parser.add_argument("--n-runs", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--noise-std", type=float, default=0.1)
    parser.add_argument("--no-normalize", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    X, y = load_dataset(args.csv, normalize=not args.no_normalize)
    logger.info(f"Loaded {len(X)} samples, {X.shape[1]} trace features (normalize={not args.no_normalize})")

    mlp_r2s, noisy_r2s, colshuf_r2s = [], [], []
    for run in range(args.n_runs):
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=run)
        r2_mlp = train_mlp(X_tr, y_tr, X_te, y_te, epochs=args.epochs)
        r2_noisy = train_mlp_noisy(X_tr, y_tr, X_te, y_te, epochs=args.epochs, noise_std=args.noise_std)
        r2_colshuf = train_mlp_colshuf(X_tr, y_tr, X_te, y_te, epochs=args.epochs)
        mlp_r2s.append(r2_mlp)
        noisy_r2s.append(r2_noisy)
        colshuf_r2s.append(r2_colshuf)
        logger.info(
            f"Run {run+1}: MLP R²={r2_mlp:.4f}, Noisy R²={r2_noisy:.4f}, ColShuf R²={r2_colshuf:.4f}"
        )

    result = {
        "n_runs": args.n_runs,
        "n_samples": int(len(X)),
        "mlp_r2_mean": float(np.mean(mlp_r2s)),
        "mlp_r2_std": float(np.std(mlp_r2s)),
        "noisy_r2_mean": float(np.mean(noisy_r2s)),
        "noisy_r2_std": float(np.std(noisy_r2s)),
        "colshuf_r2_mean": float(np.mean(colshuf_r2s)),
        "colshuf_r2_std": float(np.std(colshuf_r2s)),
        "gat_reference_r2": 0.731,
        "mlp_reference_r2": 0.714,
        "noise_std": args.noise_std,
    }

    output_file = output_dir / "ablation_results.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n=== Trace Dominance Ablation ({args.n_runs} runs, {len(X)} samples) ===")
    print(f"MLP:           R² = {result['mlp_r2_mean']:.4f} ± {result['mlp_r2_std']:.4f}")
    print(f"MLP-noisy:     R² = {result['noisy_r2_mean']:.4f} ± {result['noisy_r2_std']:.4f}")
    print(f"MLP-colshuf:   R² = {result['colshuf_r2_mean']:.4f} ± {result['colshuf_r2_std']:.4f}")
    print(f"GAT (ref):     R² = {result['gat_reference_r2']:.4f}")
    print(f"MLP (ref):     R² = {result['mlp_reference_r2']:.4f}")

    delta_mlp_noisy = result["mlp_r2_mean"] - result["noisy_r2_mean"]
    delta_mlp_colshuf = result["mlp_r2_mean"] - result["colshuf_r2_mean"]
    print(f"\nΔ(MLP - MLP-noisy)   = {delta_mlp_noisy:+.4f}")
    print(f"Δ(MLP - MLP-colshuf) = {delta_mlp_colshuf:+.4f}")

    if abs(delta_mlp_noisy) < 0.02 and abs(delta_mlp_colshuf) < 0.02:
        print("\n→ Trace MAGNITUDE carries the signal; per-prime identity & noise robustness")
        print("  suggest trace vector alone suffices. Graph structure is NOT essential.")
    elif delta_mlp_noisy > 0.05:
        print("\n→ Adding noise HURTS — features are sensitive. Graph mixing would also hurt.")
    else:
        print("\n→ Mixed evidence — interpret carefully.")


if __name__ == "__main__":
    main()
