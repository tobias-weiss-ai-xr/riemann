#!/usr/bin/env python3
"""
Task 3: L-function Zero Spacing Prediction from Hecke Traces.

Two experiments:
  A) Single-task: Predict std_zero_spacing from Hecke traces + scalar features.
  B) Multi-task:  Predict all 9 individual spacings (z_{i+1}-z_i) + std_zero_spacing.

Compares GradientBoosting, RandomForest, and MLP across both formulations.
Also tests features-only (no traces) to quantify trace contribution.

Usage:
    python scripts/task_3_zero_spacing_prediction.py
"""

from __future__ import annotations

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
from loguru import logger
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CSV_PATH = "data/lmfdb/lmfdb_zeros_ml.csv"
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
# Feature columns
# ---------------------------------------------------------------------------

TRACE_COLS = [f"trace_{i}" for i in range(1, 101)]
SCALAR_COLS = ["level", "dim", "analytic_rank", "root_number",
               "order_of_vanishing", "num_zeros", "char_order"]
ZERO_POS_COLS = [f"z{i}" for i in range(1, 11)]  # z1..z10
SPACING_NAMES = [f"spacing_{i}" for i in range(1, 10)]  # 9 spacings


def compute_spacings(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 9 individual spacings from zero positions z1..z10."""
    spacings = pd.DataFrame(index=df.index)
    for i in range(9):
        spacings[f"spacing_{i+1}"] = df[f"z{i+2}"].values - df[f"z{i+1}"].values
    return spacings


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
# Model builders
# ---------------------------------------------------------------------------

def build_gb() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=42,
    )


def build_rf() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=200, max_depth=15, min_samples_leaf=5,
        n_jobs=-1, random_state=42,
    )


def build_mlp() -> MLPRegressor:
    return MLPRegressor(
        hidden_layer_sizes=(128, 64),
        activation='relu', solver='adam',
        alpha=1e-4, learning_rate_init=1e-3,
        batch_size=1024, max_iter=100,
        early_stopping=True, validation_fraction=0.1,
        random_state=42,
    )


MODELS = {
    "GB": ("GradientBoosting", build_gb),
    "RF": ("RandomForest", build_rf),
    "MLP": ("MLP", build_mlp),
}

# ---------------------------------------------------------------------------
# Single-task regression
# ---------------------------------------------------------------------------


def run_single_task(
    X: np.ndarray,
    y: np.ndarray,
    label: str = "std_zero_spacing",
) -> List[Dict[str, Any]]:
    """Run single-task regression with all models."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = []
    for name, (display_name, builder) in MODELS.items():
        logger.info(f"  Single-task {display_name} on {label}...")
        t0 = time.time()
        model = builder()
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        elapsed = time.time() - t0

        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)

        results.append({
            "model": name,
            "target": label,
            "r2": float(r2),
            "mae": float(mae),
            "fit_time": float(elapsed),
        })
        logger.info(f"    R²={fmt(r2)}, MAE={fmt(mae)}, time={elapsed:.1f}s")

    return results

# ---------------------------------------------------------------------------
# Multi-task regression
# ---------------------------------------------------------------------------


def build_gb_fast() -> GradientBoostingRegressor:
    """Faster GB for multi-task (10 outputs = 10 separate fits)."""
    return GradientBoostingRegressor(
        n_estimators=100, max_depth=4, learning_rate=0.1,
        subsample=0.8, random_state=42,
    )


def run_multi_task(
    X: np.ndarray,
    Y: np.ndarray,
    target_names: List[str],
) -> List[Dict[str, Any]]:
    """Run multi-task regression: predict all spacings + std simultaneously.
    
    Only runs GB (best single-task model) since MultiOutputRegressor
    fits one model per target — 10× RF/MLP is too slow.
    """
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.2, random_state=42,
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = []
    for name, builder in [("GB", build_gb_fast)]:
        logger.info(f"  Multi-task {name} ({len(target_names)} outputs)...")
        t0 = time.time()
        base = builder()
        model = MultiOutputRegressor(base, n_jobs=-1)
        model.fit(X_train_s, Y_train)
        Y_pred = model.predict(X_test_s)
        elapsed = time.time() - t0

        # Per-target metrics
        per_target = {}
        mean_r2 = 0.0
        for i, tname in enumerate(target_names):
            r2_i = r2_score(Y_test[:, i], Y_pred[:, i])
            mae_i = mean_absolute_error(Y_test[:, i], Y_pred[:, i])
            per_target[tname] = {"r2": float(r2_i), "mae": float(mae_i)}
            mean_r2 += r2_i
        mean_r2 /= len(target_names)

        results.append({
            "model": name,
            "mean_r2": float(mean_r2),
            "per_target": per_target,
            "fit_time": float(elapsed),
        })
        logger.info(f"    Mean R²={fmt(mean_r2)}, time={elapsed:.1f}s")

    return results

# ---------------------------------------------------------------------------
# Per-dimension breakdown
# ---------------------------------------------------------------------------


def run_per_dimension(
    df: pd.DataFrame,
    spacings: pd.DataFrame,
    trace_features: np.ndarray,
    scalar_features: np.ndarray,
) -> List[Dict[str, Any]]:
    """Run single-task std_zero_spacing regression per dimension group."""
    X_all = np.concatenate([trace_features, scalar_features], axis=1)
    y_std = df["std_zero_spacing"].values

    results = []
    for dim_val in sorted(df["dim"].unique()):
        mask = df["dim"].values == dim_val
        if mask.sum() < 100:
            logger.info(f"  Skipping dim={dim_val}: only {mask.sum()} samples")
            continue

        X_d = X_all[mask]
        y_d = y_std[mask]

        # Need enough for split
        if mask.sum() < 50:
            continue

        X_tr, X_te, y_tr, y_te = train_test_split(
            X_d, y_d, test_size=0.2, random_state=42,
        )
        scaler = StandardScaler()
        X_tr_s = scaler.fit_transform(X_tr)
        X_te_s = scaler.transform(X_te)

        model = build_gb()
        model.fit(X_tr_s, y_tr)
        y_pred = model.predict(X_te_s)
        r2 = r2_score(y_te, y_pred)
        mae = mean_absolute_error(y_te, y_pred)

        results.append({
            "dim": int(dim_val),
            "n_samples": int(mask.sum()),
            "r2": float(r2),
            "mae": float(mae),
        })
        logger.info(f"  dim={dim_val}: n={mask.sum()}, R²={fmt(r2)}, MAE={fmt(mae)}")

    return results

# ---------------------------------------------------------------------------
# Print / plot
# ---------------------------------------------------------------------------


def print_results(
    single_task: List[Dict],
    single_task_scalars_only: List[Dict],
    multi_task: List[Dict],
    multi_task_scalars_only: List[Dict],
    per_dim: List[Dict],
) -> None:
    """Print formatted results tables."""
    print_header("Task 3A: Single-Task std_zero_spacing Regression")
    print(f"{'Model':<20} {'R²':>8} {'MAE':>10} {'Time':>8}")
    print("-" * 48)
    for r in single_task:
        print(f"{MODELS[r['model']][0]:<20} {fmt(r['r2']):>8} {fmt(r['mae']):>10} {r['fit_time']:>7.1f}s")
    print()
    print("  Scalars-only baseline (no traces):")
    for r in single_task_scalars_only:
        print(f"  {MODELS[r['model']][0]:<18} {fmt(r['r2']):>8} {fmt(r['mae']):>10} {r['fit_time']:>7.1f}s")
    print()

    print_header("Task 3B: Multi-Task Regression (9 spacings + std)")
    # Use best model (GB) for per-target table
    mt_best = next(r for r in multi_task if r["model"] == "GB")
    targets = list(mt_best["per_target"].keys())
    print(f"{'Target':<18} {'R²':>8} {'MAE':>10}")
    print("-" * 38)
    for t in targets:
        d = mt_best["per_target"][t]
        print(f"{t:<18} {fmt(d['r2']):>8} {fmt(d['mae']):>10}")
    print(f"\n  Mean R² across all targets: {fmt(mt_best['mean_r2'])}")
    print()
    print("  All models (mean R²):")
    print(f"  {'Model':<20} {'Mean R²':>10} {'Time':>8}")
    for r in multi_task:
        print(f"  {MODELS[r['model']][0]:<18} {fmt(r['mean_r2']):>10} {r['fit_time']:>7.1f}s")
    print()
    print("  Scalars-only baseline:")
    for r in multi_task_scalars_only:
        print(f"  {MODELS[r['model']][0]:<18} {fmt(r['mean_r2']):>10} {r['fit_time']:>7.1f}s")
    if not multi_task_scalars_only:
        print("  (skipped — see single-task scalars-only for trace contribution)")
    print()

    print_header("Per-Dimension std_zero_spacing (GradientBoosting)")
    print(f"{'Dim':>4} {'N':>6} {'R²':>8} {'MAE':>10}")
    print("-" * 30)
    for r in per_dim:
        print(f"{r['dim']:>4} {r['n_samples']:>6} {fmt(r['r2']):>8} {fmt(r['mae']):>10}")


def plot_results(
    single_task: List[Dict],
    multi_task: List[Dict],
    per_dim: List[Dict],
    output_path: Path,
) -> None:
    """Create summary figure."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Single-task R² comparison
    ax = axes[0, 0]
    models = [MODELS[r["model"]][0] for r in single_task]
    r2s = [r["r2"] for r in single_task]
    colors = ['#2196F3', '#4CAF50', '#FF9800']
    bars = ax.bar(models, r2s, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_ylabel("R²")
    ax.set_title("A) Single-Task: std_zero_spacing")
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    for bar, r2 in zip(bars, r2s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{r2:.3f}", ha='center', va='bottom', fontsize=9)
    ax.set_ylim(bottom=min(-0.05, min(r2s) - 0.1))

    # Panel 2: Multi-task per-target R² (GB best)
    ax = axes[0, 1]
    mt_best = next(r for r in multi_task if r["model"] == "GB")
    targets = list(mt_best["per_target"].keys())
    target_r2s = [mt_best["per_target"][t]["r2"] for t in targets]
    bars = ax.bar(range(len(targets)), target_r2s,
                 color='#2196F3', edgecolor='black', linewidth=0.5)
    ax.set_xticks(range(len(targets)))
    ax.set_xticklabels(targets, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("R²")
    ax.set_title("B) Multi-Task: Per-Target R² (GB)")
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    # Panel 3: Multi-task all models mean R²
    ax = axes[1, 0]
    models_mt = [MODELS[r["model"]][0] for r in multi_task]
    mean_r2s = [r["mean_r2"] for r in multi_task]
    bars = ax.bar(models_mt, mean_r2s, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_ylabel("Mean R²")
    ax.set_title("C) Multi-Task: Mean R² Across All Targets")
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    for bar, r2 in zip(bars, mean_r2s):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f"{r2:.3f}", ha='center', va='bottom', fontsize=9)

    # Panel 4: Per-dimension std_zero_spacing R²
    ax = axes[1, 1]
    if per_dim:
        dims = [str(r["dim"]) for r in per_dim]
        dim_r2s = [r["r2"] for r in per_dim]
        bars = ax.bar(dims, dim_r2s, color='#9C27B0', edgecolor='black', linewidth=0.5)
        ax.set_xlabel("Dimension")
        ax.set_ylabel("R²")
        ax.set_title("D) Per-Dimension std_zero_spacing R²")
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        for bar, r2, n in zip(bars, dim_r2s, [r["n_samples"] for r in per_dim]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{r2:.3f}\n(n={n})", ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved plot to {output_path}")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    t_total = time.time()

    print_header("Task 3: L-function Zero Spacing Prediction from Hecke Traces")

    # --- Load data ---
    logger.info(f"Loading {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    logger.info(f"Loaded {len(df)} samples, {len(df.columns)} columns")

    # Extract features
    trace_features = df[TRACE_COLS].values.astype(np.float32)
    scalar_features = df[SCALAR_COLS].values.astype(np.float32)

    # Compute spacings
    spacings = compute_spacings(df)
    logger.info(f"Computed 9 spacings. Stats: mean={spacings.mean().mean():.4f}, "
                f"std={spacings.std().mean():.4f}")

    # Build feature matrices
    X_traces_scalars = np.concatenate([trace_features, scalar_features], axis=1)
    X_scalars_only = scalar_features

    # --- Task 3A: Single-task std_zero_spacing ---
    print_header("Task 3A: Single-Task std_zero_spacing Regression")
    y_std = df["std_zero_spacing"].values

    logger.info("With traces + scalars:")
    single_task = run_single_task(X_traces_scalars, y_std, "std_zero_spacing")

    logger.info("Scalars only (no traces):")
    single_task_scalars_only = run_single_task(X_scalars_only, y_std, "std_zero_spacing (scalars)")

    # --- Task 3B: Multi-task ---
    print_header("Task 3B: Multi-Task Regression (9 spacings + std)")
    # Target: 9 individual spacings + std_zero_spacing = 10 targets
    Y_multi = np.column_stack([
        spacings.values,          # 9 spacings
        df["std_zero_spacing"].values.reshape(-1, 1),  # std
    ])
    target_names = SPACING_NAMES + ["std_zero_spacing"]
    logger.info(f"Multi-task target matrix shape: {Y_multi.shape}")

    logger.info("With traces + scalars:")
    multi_task = run_multi_task(X_traces_scalars, Y_multi, target_names)

    logger.info("Scalars only (no traces):")
    multi_task_scalars_only = []  # Skip — single-task already shows trace contribution

    # --- Per-dimension breakdown ---
    print_header("Per-Dimension std_zero_spacing (GradientBoosting)")
    per_dim = run_per_dimension(df, spacings, trace_features, scalar_features)

    # --- Print summary ---
    print_results(
        single_task, single_task_scalars_only,
        multi_task, multi_task_scalars_only,
        per_dim,
    )

    # --- Plot ---
    plot_path = OUTPUT_DIR / "task_3_zero_spacing_prediction.png"
    plot_results(single_task, multi_task, per_dim, plot_path)

    # --- Save JSON ---
    all_results = {
        "n_samples": len(df),
        "n_trace_features": len(TRACE_COLS),
        "n_scalar_features": len(SCALAR_COLS),
        "single_task": single_task,
        "single_task_scalars_only": single_task_scalars_only,
        "multi_task": multi_task,
        "multi_task_scalars_only": multi_task_scalars_only,
        "per_dimension": per_dim,
        "total_time_s": float(time.time() - t_total),
    }
    json_path = OUTPUT_DIR / "task_3_zero_spacing_prediction_results.json"
    with open(json_path, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Saved results to {json_path}")

    elapsed = time.time() - t_total
    print_header(f"Done. Total time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
