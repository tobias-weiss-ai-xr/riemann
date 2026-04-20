#!/usr/bin/env python3
"""
Experiment 11: Train ML models to predict L-function zeros from Hecke traces.

Predicts L-function zero positions and statistics using sklearn models.
Directly connects to the Riemann Hypothesis via Montgomery pair correlation.

Sub-experiments:
  11a: First L-function zero (z1) regression
  11b: Second L-function zero (z2) regression
  11c: Third L-function zero (z3) regression
  11d: Mean zero spacing regression
  11e: Number of zeros regression
  11f: Feature Ablation (best model per task)

Usage:
    python scripts/train_lmfdb_zeros.py
    python scripts/train_lmfdb_zeros.py --data data/lmfdb/lmfdb_zeros_ml.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_PATH = "data/lmfdb/lmfdb_zeros_ml.csv"

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


def load_data(path: str) -> pd.DataFrame:
    """Load LMFDB zeros ML dataset."""
    logger.info(f"Loading data from {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} samples with {len(df.columns)} columns")
    return df


def get_trace_columns(n: int = 100) -> List[str]:
    """Return column names for first n Hecke traces."""
    return [f"trace_{i}" for i in range(1, n + 1)]


def get_scalar_columns() -> List[str]:
    """Return scalar feature column names for zeros dataset."""
    return ["level", "dim", "analytic_rank"]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt(val: float, decimals: int = 3) -> str:
    """Format a float for table display."""
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


def build_regressors() -> List[Tuple[str, Any]]:
    """Return list of (name, model) tuples for regression."""
    return [
        (
            "RandomForest",
            RandomForestRegressor(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "GradientBoosting",
            GradientBoostingRegressor(
                n_estimators=100,
                max_depth=5,
                random_state=42,
            ),
        ),
        (
            "MLP (128->64)",
            MLPRegressor(
                hidden_layer_sizes=(128, 64),
                activation="relu",
                solver="adam",
                alpha=1e-4,
                batch_size=256,
                learning_rate_init=1e-3,
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
            ),
        ),
    ]


def build_named_regressor(name: str):
    """Build a fresh regressor by name."""
    if name == "RandomForest":
        return RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    elif name == "GradientBoosting":
        return GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
    elif name == "MLP (128->64)":
        return MLPRegressor(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size=256,
            learning_rate_init=1e-3,
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
        )
    else:
        raise ValueError(f"Unknown regressor: {name}")


# ---------------------------------------------------------------------------
# Generic regression experiment
# ---------------------------------------------------------------------------


def run_regression_experiment(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    experiment_label: str,
) -> Tuple[List[Dict], str]:
    """Run a regression experiment for a given target column."""
    print_header(f"Exp: {experiment_label}")

    # Filter out rows where target is 0 or NaN (missing data)
    df_clean = (
        df[df[target_col] > 0].copy()
        if target_col.startswith("z")
        else df.dropna(subset=[target_col]).copy()
    )

    # Ensure all feature columns exist
    feature_cols = [c for c in feature_cols if c in df_clean.columns]
    if not feature_cols:
        print(f"  WARNING: No valid feature columns found, skipping.")
        return [], ""

    # Drop rows with NaN in features or target
    df_clean = df_clean.dropna(subset=feature_cols + [target_col])

    X = df_clean[feature_cols].values
    y = df_clean[target_col].values.astype(float)

    n_samples, n_features = X.shape
    print(f"  Dataset: {n_samples} samples, {n_features} features")
    print(
        f"  Target: {target_col} — range=[{y.min():.4f}, {y.max():.4f}], "
        f"mean={y.mean():.4f}, std={y.std():.4f}"
    )
    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )
    print(f"  Split: {len(X_train)} train / {len(X_test)} test")
    print()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Baseline: mean of training set
    y_mean = np.mean(y_train)
    y_pred_base = np.full_like(y_test, y_mean, dtype=float)
    base_mae = mean_absolute_error(y_test, y_pred_base)
    base_rmse = np.sqrt(mean_squared_error(y_test, y_pred_base))
    base_r2 = r2_score(y_test, y_pred_base)
    print(
        f"  Mean baseline: MAE={fmt(base_mae)}, RMSE={fmt(base_rmse)}, R²={fmt(base_r2)}"
    )
    print()

    results = []
    regressors = build_regressors()

    for name, model in regressors:
        logger.info(f"Training {name} for {target_col}...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        y_pred = model.predict(X_test_s)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        results.append(
            {
                "name": name,
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "elapsed": elapsed,
            }
        )
        logger.info(
            f"  {name}: MAE={fmt(mae)}, RMSE={fmt(rmse)}, R²={fmt(r2)}, time={elapsed:.1f}s"
        )

    # Print table
    print(f"  {'Model':<28s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s} | {'Time':>6s}")
    print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 8} | {'-' * 6}")
    for r in results:
        print(
            f"  {r['name']:<28s} | {fmt(r['mae']):>8s} | {fmt(r['rmse']):>8s} | "
            f"{fmt(r['r2']):>8s} | {r['elapsed']:>5.1f}s"
        )
    print()

    best = max(results, key=lambda r: r["r2"])
    print(
        f"  Best model: {best['name']} (MAE={fmt(best['mae'])}, RMSE={fmt(best['rmse'])}, R²={fmt(best['r2'])})"
    )
    print()

    return results, best["name"]


# ---------------------------------------------------------------------------
# Feature Ablation
# ---------------------------------------------------------------------------


def experiment_ablation(
    df: pd.DataFrame,
    target_col: str,
    best_model_name: str,
    experiment_label: str,
) -> None:
    """Feature Ablation — test best model with different feature sets."""
    print_header(f"Feature Ablation — {experiment_label}")

    trace_10 = get_trace_columns(10)
    trace_50 = get_trace_columns(50)
    trace_100 = get_trace_columns(100)
    scalar_cols = get_scalar_columns()
    all_features = trace_100 + scalar_cols

    feature_sets = [
        ("First 10 traces", trace_10),
        ("First 50 traces", trace_50),
        ("All 100 traces", trace_100),
        ("100 traces + scalars", all_features),
    ]

    print(f"  Best model: {best_model_name}")
    print(f"  Target: {target_col}")
    print()

    # Filter for valid target values
    df_clean = (
        df[df[target_col] > 0].copy()
        if target_col.startswith("z")
        else df.dropna(subset=[target_col]).copy()
    )

    results = []

    for set_name, feat_cols in feature_sets:
        # Ensure all feature columns exist
        feat_cols = [c for c in feat_cols if c in df_clean.columns]
        if not feat_cols:
            continue

        # Drop rows with NaN in features or target
        df_sub = df_clean.dropna(subset=feat_cols + [target_col])

        X = df_sub[feat_cols].values
        y = df_sub[target_col].values.astype(float)

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
        )

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = build_named_regressor(best_model_name)
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        results.append(
            {
                "name": set_name,
                "features": len(feat_cols),
                "r2": r2,
                "mae": mae,
                "rmse": rmse,
            }
        )
        logger.info(
            f"  {set_name} ({len(feat_cols)} feat): R²={fmt(r2)}, MAE={fmt(mae)}, RMSE={fmt(rmse)}"
        )

    # Print ablation table
    print(
        f"  {'Feature Set':<32s} | {'Feats':>5s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s}"
    )
    print(f"  {'-' * 32} | {'-' * 5} | {'-' * 8} | {'-' * 8} | {'-' * 8}")
    for r in results:
        print(
            f"  {r['name']:<32s} | {r['features']:>5d} | "
            f"{fmt(r['mae']):>8s} | {fmt(r['rmse']):>8s} | {fmt(r['r2']):>8s}"
        )
    print()


# ---------------------------------------------------------------------------
# Dataset statistics
# ---------------------------------------------------------------------------


def print_dataset_statistics(df: pd.DataFrame) -> None:
    """Print comprehensive dataset statistics."""
    print_header("Dataset Statistics")

    print(f"  Total samples: {len(df)}")
    print(f"  Total columns: {len(df.columns)}")
    print(f"  Level range: [{df['level'].min()}, {df['level'].max()}]")

    # Zero statistics
    for col in ["z1", "z2", "z3", "z4", "z5", "z10"]:
        if col in df.columns:
            valid = df[(df[col] > 0) & df[col].notna()][col]
            if len(valid) > 0:
                print(
                    f"  {col}: n={len(valid)}, range=[{valid.min():.4f}, {valid.max():.4f}], "
                    f"mean={valid.mean():.4f}"
                )

    if "num_zeros" in df.columns:
        print(
            f"  num_zeros: range=[{df['num_zeros'].min()}, {df['num_zeros'].max()}], mean={df['num_zeros'].mean():.1f}"
        )

    if "mean_zero_spacing" in df.columns:
        valid = df[df["mean_zero_spacing"] > 0]["mean_zero_spacing"]
        if len(valid) > 0:
            print(
                f"  mean_zero_spacing: range=[{valid.min():.4f}, {valid.max():.4f}], "
                f"mean={valid.mean():.4f}"
            )

    if "root_number" in df.columns:
        rn = df["root_number"].value_counts().sort_index()
        print(f"\n  Root number distribution:")
        for val, count in rn.items():
            print(f"    {val}: {count} ({100 * count / len(df):.1f}%)")

    if "order_of_vanishing" in df.columns:
        ov = df["order_of_vanishing"].value_counts().sort_index()
        print(f"\n  Order of vanishing distribution:")
        for val, count in ov.items():
            print(f"    {int(val)}: {count} ({100 * count / len(df):.1f}%)")

    # Rank distribution
    if "analytic_rank" in df.columns:
        rank_counts = df["analytic_rank"].value_counts().sort_index()
        print(f"\n  Analytic rank distribution:")
        for rank, count in rank_counts.items():
            print(f"    rank {int(rank)}: {count} ({100 * count / len(df):.1f}%)")

    print()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(
    all_results: Dict[str, Tuple[List[Dict], str]],
    total_time: float,
) -> None:
    """Print final summary of all experiments."""
    print_separator()
    print("  EXPERIMENT 11 — SUMMARY (L-function Zeros Prediction)".center(78))
    print_separator()
    print(f"  Total training time: {total_time:.1f}s")
    print()

    print(
        "  ┌─────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "  │ Exp 11: Predicting L-function Zeros from Hecke Traces                  │"
    )
    print(
        "  ├─────────────────────────────────────────────────────────────────────────┤"
    )

    for label, (results, best_name) in all_results.items():
        best = max(results, key=lambda r: r["r2"])
        print(f"  │ {label:<66s} │")
        print(f"  │   Best model:    {best_name:<54s} │")
        print(f"  │   MAE:           {fmt(best['mae']):<54s} │")
        print(f"  │   RMSE:          {fmt(best['rmse']):<54s} │")
        print(f"  │   R²:            {fmt(best['r2']):<54s} │")
        print(
            "  ├─────────────────────────────────────────────────────────────────────────┤"
        )

    print(
        "  │ RH Connection:                                                         │"
    )
    print(
        "  │   - Zeros of L-functions encode deep arithmetic via the explicit formula│"
    )
    print(
        "  │   - GRH says all non-trivial zeros lie on Re(s) = 1/2                  │"
    )
    print(
        "  │   - Montgomery pair correlation of zeros ~ random matrix theory        │"
    )
    print(
        "  │   - Predicting zeros from traces validates ML learns number theory     │"
    )
    print(
        "  └─────────────────────────────────────────────────────────────────────────┘"
    )
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment 11: Train ML models to predict L-function zeros",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=DATA_PATH,
        help=f"Path to CSV dataset (default: {DATA_PATH})",
    )
    parser.add_argument(
        "--skip-ablation",
        action="store_true",
        help="Skip feature ablation experiments",
    )
    args = parser.parse_args()

    t_start = time.time()

    print()
    print("=" * 78)
    print("  Experiment 11: L-function Zeros Prediction from Hecke Traces".center(78))
    print("=" * 78)
    print()

    # Load data
    df = load_data(args.data)

    # Dataset statistics
    print_dataset_statistics(df)

    trace_cols = get_trace_columns(100)
    logger.info(f"Feature columns: {len(trace_cols)} trace features")

    all_results: Dict[str, Tuple[List[Dict], str]] = {}

    # ------------------------------------------------------------------
    # Exp 11a: First L-function zero (z1) regression
    # ------------------------------------------------------------------
    if "z1" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "z1", "11a: First L-function Zero (z1) Regression"
        )
        all_results["11a: z1 (first zero)"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11b: Second L-function zero (z2) regression
    # ------------------------------------------------------------------
    if "z2" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "z2", "11b: Second L-function Zero (z2) Regression"
        )
        all_results["11b: z2 (second zero)"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11c: Third L-function zero (z3) regression
    # ------------------------------------------------------------------
    if "z3" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "z3", "11c: Third L-function Zero (z3) Regression"
        )
        all_results["11c: z3 (third zero)"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11c2: Fourth L-function zero (z4) regression
    # ------------------------------------------------------------------
    if "z4" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "z4", "11c2: Fourth L-function Zero (z4) Regression"
        )
        all_results["11c2: z4 (fourth zero)"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11c3: Fifth L-function zero (z5) regression
    # ------------------------------------------------------------------
    if "z5" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "z5", "11c3: Fifth L-function Zero (z5) Regression"
        )
        all_results["11c3: z5 (fifth zero)"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11c4: Tenth L-function zero (z10) regression
    # ------------------------------------------------------------------
    if "z10" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "z10", "11c4: Tenth L-function Zero (z10) Regression"
        )
        all_results["11c4: z10 (tenth zero)"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11d: Mean zero spacing regression
    # ------------------------------------------------------------------
    if "mean_zero_spacing" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "mean_zero_spacing", "11d: Mean Zero Spacing Regression"
        )
        all_results["11d: mean zero spacing"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11e: Number of zeros regression
    # ------------------------------------------------------------------
    if "num_zeros" in df.columns:
        results, best = run_regression_experiment(
            df, trace_cols, "num_zeros", "11e: Number of Zeros Regression"
        )
        all_results["11e: num zeros"] = (results, best)

    # ------------------------------------------------------------------
    # Exp 11f: Feature Ablation
    # ------------------------------------------------------------------
    if not args.skip_ablation:
        for label, (_, best_name) in all_results.items():
            target_map = {
                "11a: z1 (first zero)": "z1",
                "11b: z2 (second zero)": "z2",
                "11c: z3 (third zero)": "z3",
                "11c2: z4 (fourth zero)": "z4",
                "11c3: z5 (fifth zero)": "z5",
                "11c4: z10 (tenth zero)": "z10",
                "11d: mean zero spacing": "mean_zero_spacing",
                "11e: num zeros": "num_zeros",
            }
            target = target_map.get(label)
            if target:
                experiment_ablation(df, target, best_name, label)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_time = time.time() - t_start
    print_summary(all_results, total_time)


if __name__ == "__main__":
    main()
