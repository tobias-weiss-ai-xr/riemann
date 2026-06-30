#!/usr/bin/env python3
"""
Task 1B: Trace Learning Curve — sklearn ML with Varying Trace Counts.

Shows how sklearn ML performance changes as we provide more trace data (100, 200, 500, 1000).
Answers: "How much trace data does arithmetic ML need for good performance?"

Usage:
    python scripts/train_lmfdb_ml_learning_curve.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import List, Tuple

# Fix matplotlib cache permission issue
os.environ['MPLCONFIGDIR'] = '/tmp'

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    train_test_split,
)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

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


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt(val: float, decimals: int = 4) -> str:
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
# Scalar features
# ---------------------------------------------------------------------------


def get_scalar_columns() -> List[str]:
    """Return scalar feature column names (excluding traces, targets, label)."""
    return ["level", "dim", "char_degree", "is_cm", "is_self_dual", "Nk2"]

# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------


def build_dim_regressor() -> GradientBoostingRegressor:
    """Best regressor for dimension prediction from Exp 10b."""
    return GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        random_state=42,
    )


def build_rank_classifier() -> GradientBoostingClassifier:
    """Best classifier for rank prediction."""
    return GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42,
    )


def build_cm_classifier() -> LogisticRegression:
    """Best classifier for CM prediction."""
    return LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced",
    )

# ---------------------------------------------------------------------------
# Learning curve experiment
# ---------------------------------------------------------------------------


def run_learning_curve_experiment(
    df: pd.DataFrame,
    traces_full: np.ndarray,
    n_traces_list: List[int],
    scalar_cols: List[str],
) -> dict:
    """Run sklearn ML with varying trace counts and collect results."""

    results = {
        "rank_classification": [],
        "dimension_regression": [],
        "cm_classification": [],
    }

    scalar_features = df[scalar_cols].values

    for n_traces in n_traces_list:
        print_header(f"Learning Curve with {n_traces} Traces")
        logger.info(f"Processing n_traces = {n_traces}")

        # Slice traces to requested count
        X_traces = traces_full[:, :n_traces]

        # Concatenate traces + scalars
        X = np.concatenate([X_traces, scalar_features], axis=1)
        logger.info(f"Feature matrix shape: {X.shape}")

        # === Task 1: Rank Classification (0 vs 1 vs 2) ===
        logger.info(f"Rank classification with {n_traces} traces...")
        t0 = time.time()
        y_rank = df["analytic_rank"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_rank, test_size=0.2, random_state=42, stratify=y_rank
        )

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        clf_rank = build_rank_classifier()
        clf_rank.fit(X_train_s, y_train)
        y_pred = clf_rank.predict(X_test_s)

        elapsed = time.time() - t0
        acc = accuracy_score(y_test, y_pred)
        f1_mac = f1_score(y_test, y_pred, average="macro", zero_division=0)

        results["rank_classification"].append({
            "n_traces": n_traces,
            "accuracy": float(acc),
            "f1_macro": float(f1_mac),
            "fit_time": float(elapsed),
        })
        logger.info(f"  rank: acc={fmt(acc)}, F1={fmt(f1_mac)}, time={elapsed:.1f}s")

        # === Task 2: Dimension Regression ===
        logger.info(f"Dimension regression with {n_traces} traces...")
        t0 = time.time()
        y_dim = df["dim"].values.astype(float)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_dim, test_size=0.2, random_state=42
        )

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        reg_dim = build_dim_regressor()
        reg_dim.fit(X_train_s, y_train)
        y_pred = reg_dim.predict(X_test_s)

        elapsed = time.time() - t0
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        results["dimension_regression"].append({
            "n_traces": n_traces,
            "mae": float(mae),
            "r2": float(r2),
            "fit_time": float(elapsed),
        })
        logger.info(f"  dim: MAE={fmt(mae)}, R²={fmt(r2)}, time={elapsed:.1f}s")

        # === Task 3: CM Classification (binary) ===
        logger.info(f"CM classification with {n_traces} traces...")
        t0 = time.time()
        y_cm = df["is_cm"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y_cm, test_size=0.2, random_state=42, stratify=y_cm
        )

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        clf_cm = build_cm_classifier()
        clf_cm.fit(X_train_s, y_train)
        y_pred = clf_cm.predict(X_test_s)

        elapsed = time.time() - t0
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        results["cm_classification"].append({
            "n_traces": n_traces,
            "accuracy": float(acc),
            "f1": float(f1),
            "fit_time": float(elapsed),
        })
        logger.info(f"  CM: acc={fmt(acc)}, F1={fmt(f1)}, time={elapsed:.1f}s")

        print()  # Blank line between trace counts

    return results


def print_learning_curve_tables(results: dict) -> None:
    """Print formatted learning curve tables."""

    # === Rank Classification ===
    print_header("Task 1B-a: Rank Classification Learning Curve")
    print(f"  {'N Traces':>10s} | {'Accuracy':>10s} | {'F1(mac)':>10s} | {'Time':>8s}")
    print(f"  {'-' * 10} | {'-' * 10} | {'-' * 10} | {'-' * 8}")
    for r in results["rank_classification"]:
        print(f"  {r['n_traces']:>10d} | "
              f"{fmt(r['accuracy']):>10s} | "
              f"{fmt(r['f1_macro']):>10s} | "
              f"{r['fit_time']:>7.1f}s")
    print()

    # === Dimension Regression ===
    print_header("Task 1B-b: Dimension Regression Learning Curve")
    print(f"  {'N Traces':>10s} | {'MAE':>10s} | {'R²':>10s} | {'Time':>8s}")
    print(f"  {'-' * 10} | {'-' * 10} | {'-' * 10} | {'-' * 8}")
    for r in results["dimension_regression"]:
        print(f"  {r['n_traces']:>10d} | "
              f"{fmt(r['mae']):>10s} | "
              f"{fmt(r['r2']):>10s} | "
              f"{r['fit_time']:>7.1f}s")
    print()

    # === CM Classification ===
    print_header("Task 1B-c: CM Classification Learning Curve")
    print(f"  {'N Traces':>10s} | {'Accuracy':>10s} | {'F1':>10s} | {'Time':>8s}")
    print(f"  {'-' * 10} | {'-' * 10} | {'-' * 10} | {'-' * 8}")
    for r in results["cm_classification"]:
        print(f"  {r['n_traces']:>10d} | "
              f"{fmt(r['accuracy']):>10s} | "
              f"{fmt(r['f1']):>10s} | "
              f"{r['fit_time']:>7.1f}s")
    print()


def plot_learning_curve(results: dict, output_path: Path) -> None:
    """Create learning curve plots."""

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # === Rank Classification ===
    ax = axes[0]
    x = [r["n_traces"] for r in results["rank_classification"]]
    y_acc = [r["accuracy"] for r in results["rank_classification"]]
    y_f1 = [r["f1_macro"] for r in results["rank_classification"]]

    ax.plot(x, y_acc, 'o-', label='Accuracy', linewidth=2, markersize=8)
    ax.plot(x, y_f1, 's-', label='F1 (macro)', linewidth=2, markersize=8)
    ax.set_xlabel('Number of Traces', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Rank Classification Learning Curve', fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=11)
    ax.set_xticks(x)
    ax.set_ylim([0.0, 1.05])

    # === Dimension Regression ===
    ax = axes[1]
    x = [r["n_traces"] for r in results["dimension_regression"]]
    y_r2 = [r["r2"] for r in results["dimension_regression"]]
    y_mae = [r["mae"] for r in results["dimension_regression"]]

    ax.plot(x, y_r2, 'o-', label='R²', linewidth=2, markersize=8, color='tab:blue')
    ax.set_xlabel('Number of Traces', fontsize=12, fontweight='bold')
    ax.set_ylabel('R²', fontsize=12, fontweight='bold', color='tab:blue')
    ax.set_title('Dimension Regression Learning Curve', fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=11)
    ax.tick_params(axis='y', labelcolor='tab:blue')

    # Add MAE on twin axis
    ax2 = ax.twinx()
    ax2.plot(x, y_mae, 's--', label='MAE', linewidth=2, markersize=8, color='tab:orange')
    ax2.set_ylabel('MAE', fontsize=12, fontweight='bold', color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')
    ax2.legend(loc='upper right', fontsize=11)
    ax.set_xticks(x)

    # === CM Classification ===
    ax = axes[2]
    x = [r["n_traces"] for r in results["cm_classification"]]
    y_acc = [r["accuracy"] for r in results["cm_classification"]]
    y_f1 = [r["f1"] for r in results["cm_classification"]]

    ax.plot(x, y_acc, 'o-', label='Accuracy', linewidth=2, markersize=8)
    ax.plot(x, y_f1, 's-', label='F1', linewidth=2, markersize=8)
    ax.set_xlabel('Number of Traces', fontsize=12, fontweight='bold')
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('CM Classification Learning Curve', fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower right', fontsize=11)
    ax.set_xticks(x)
    ax.set_ylim([0.0, 1.05])

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f"Saved learning curve plot: {output_path}")
    plt.close(fig)


def save_results(results: dict, output_path: Path) -> None:
    """Save results to JSON."""
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved results to: {output_path}")


def main() -> None:
    import sys  # Added import for sys.stderr
    print_header("Task 1B: Trace Learning Curve Experiment")

    # Trace counts to test
    n_traces_list = [100, 200, 500, 1000]

    logger.info(f"Testing trace counts: {n_traces_list}")
    print()

    # Load data
    df_csv, traces_full, labels = load_sql_data()

    # Get scalar features
    scalar_cols = get_scalar_columns()

    # Run learning curve experiment
    t0 = time.time()
    results = run_learning_curve_experiment(df_csv, traces_full, n_traces_list, scalar_cols)
    elapsed_total = time.time() - t0

    # Print tables
    print_learning_curve_tables(results)

    # Print summary
    print_header("Learning Curve Summary")
    logger.info(f"Total experiment time: {elapsed_total:.1f}s")
    print(f"  Experiment time: {elapsed_total:.1f}s")
    print()

    # Key findings (provisional - will fill in after seeing results)
    print("  Key Observations:")
    print("    (Results below will be correlated with actual values)")
    print()

    # Save results
    results_path = OUTPUT_DIR / "task_1b_trace_learning_curve_results.json"
    save_results(results, results_path)

    # Plot learning curves
    plot_path = OUTPUT_DIR / "task_1b_trace_learning_curve.png"
    plot_learning_curve(results, plot_path)

    print_header("Experiment Complete")
    print(f"  Results saved to: {results_path}")
    print(f"  Plot saved to: {plot_path}")


if __name__ == "__main__":
    main()
