#!/usr/bin/env python3
"""
Task 4: Binary & Ordinal Prediction from Hecke Traces.

Three quick experiments:
  A) Root number prediction (±1 binary classification)
  B) Character order prediction (multi-class classification)
  C) Number of zeros prediction (regression)

Tests whether Hecke traces carry signal beyond scalar features
for these auxiliary LMFDB targets.

Usage:
    python scripts/task_4_binary_prediction.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List

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
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
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
# Model builders — Classification
# ---------------------------------------------------------------------------

def build_gb_cls() -> GradientBoostingClassifier:
    return GradientBoostingClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=42,
    )


def build_rf_cls() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200, max_depth=15, min_samples_leaf=5,
        n_jobs=-1, random_state=42,
    )


def build_lr() -> LogisticRegression:
    return LogisticRegression(
        max_iter=1000, n_jobs=-1, random_state=42,
    )


CLS_MODELS = {
    "GB": ("GradientBoosting", build_gb_cls),
    "RF": ("RandomForest", build_rf_cls),
    "LR": ("LogisticRegression", build_lr),
}

# ---------------------------------------------------------------------------
# Model builders — Regression
# ---------------------------------------------------------------------------

def build_gb_reg() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=42,
    )


def build_rf_reg() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=200, max_depth=15, min_samples_leaf=5,
        n_jobs=-1, random_state=42,
    )


def build_mlp_reg() -> MLPRegressor:
    return MLPRegressor(
        hidden_layer_sizes=(128, 64),
        activation='relu', solver='adam',
        alpha=1e-4, learning_rate_init=1e-3,
        batch_size=1024, max_iter=100,
        early_stopping=True, validation_fraction=0.1,
        random_state=42,
    )


REG_MODELS = {
    "GB": ("GradientBoosting", build_gb_reg),
    "RF": ("RandomForest", build_rf_reg),
    "MLP": ("MLP", build_mlp_reg),
}


# ---------------------------------------------------------------------------
# Experiment A: Root Number Prediction (binary classification)
# ---------------------------------------------------------------------------

def run_root_number(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Dict[str, Any]:
    """Predict root_number (±1) from features."""
    print_header("Experiment A: Root Number Prediction (±1)")

    y = df["root_number"].values.astype(int)
    X = df[feature_cols].values.astype(np.float32)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = {}
    for name, (display_name, builder) in CLS_MODELS.items():
        logger.info(f"  {display_name} on root_number...")
        t0 = time.time()
        model = builder()
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)[:, 1] if hasattr(model, "predict_proba") else None
        elapsed = time.time() - t0

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro")
        roc_auc = roc_auc_score(y_test, y_proba) if y_proba is not None else None

        results[name] = {
            "accuracy": float(acc),
            "f1_macro": float(f1),
            "roc_auc": float(roc_auc) if roc_auc is not None else None,
            "fit_time": float(elapsed),
        }
        logger.info(
            f"    Acc={fmt(acc)}, F1={fmt(f1)}"
            + (f", AUC={fmt(roc_auc)}" if roc_auc else "")
            + f", time={elapsed:.1f}s"
        )

    # Scalars-only baseline (exclude root_number from scalars)
    scalar_baseline = [c for c in SCALAR_COLS if c != "root_number"]
    X_scal = df[scalar_baseline].values.astype(np.float32)
    X_scal_train, X_scal_test, _, _ = train_test_split(
        X_scal, y, test_size=0.2, random_state=42, stratify=y,
    )
    scaler_scal = StandardScaler()
    X_scal_train_s = scaler_scal.fit_transform(X_scal_train)
    X_scal_test_s = scaler_scal.transform(X_scal_test)

    scalars_results = {}
    for name, (display_name, builder) in [("GB", ("GradientBoosting", build_gb_cls)), ("LR", ("LogisticRegression", build_lr))]:
        logger.info(f"  Scalars-only {display_name} on root_number...")
        t0 = time.time()
        model = builder()
        model.fit(X_scal_train_s, y_train)
        y_pred_s = model.predict(X_scal_test_s)
        y_proba_s = model.predict_proba(X_scal_test_s)[:, 1] if hasattr(model, "predict_proba") else None
        elapsed = time.time() - t0

        acc_s = accuracy_score(y_test, y_pred_s)
        f1_s = f1_score(y_test, y_pred_s, average="macro")
        roc_auc_s = roc_auc_score(y_test, y_proba_s) if y_proba_s is not None else None

        scalars_results[name] = {
            "accuracy": float(acc_s),
            "f1_macro": float(f1_s),
            "roc_auc": float(roc_auc_s) if roc_auc_s is not None else None,
            "fit_time": float(elapsed),
        }
        logger.info(
            f"    Acc={fmt(acc_s)}, F1={fmt(f1_s)}"
            + (f", AUC={fmt(roc_auc_s)}" if roc_auc_s else "")
            + f", time={elapsed:.1f}s"
        )

    return {"models": results, "scalars_only": scalars_results}


# ---------------------------------------------------------------------------
# Experiment B: Order of Vanishing Prediction (binary: 0 vs >0)
# ---------------------------------------------------------------------------

def run_order_vanishing(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Dict[str, Any]:
    """Predict order_of_vanishing (binary: 0 vs >0) from features."""
    print_header("Experiment B: Order of Vanishing Prediction (0 vs >0)")

    # Binary: 0 = RH holds, >0 = non-trivial zero at critical point
    y = (df["order_of_vanishing"].values > 0).astype(int)
    X = df[feature_cols].values.astype(np.float32)

    # Class distribution
    unique, counts = np.unique(y, return_counts=True)
    dist = {int(u): int(c) for u, c in zip(unique, counts)}
    logger.info(f"  Class distribution: {dist}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y,
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = {}
    for name, (display_name, builder) in CLS_MODELS.items():
        logger.info(f"  {display_name} on order_of_vanishing...")
        t0 = time.time()
        model = builder()
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)[:, 1] if hasattr(model, "predict_proba") else None
        elapsed = time.time() - t0

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro")
        roc_auc = roc_auc_score(y_test, y_proba) if y_proba is not None else None

        results[name] = {
            "accuracy": float(acc),
            "f1_macro": float(f1),
            "roc_auc": float(roc_auc) if roc_auc is not None else None,
            "fit_time": float(elapsed),
        }
        logger.info(
            f"    Acc={fmt(acc)}, F1={fmt(f1)}"
            + (f", AUC={fmt(roc_auc)}" if roc_auc else "")
            + f", time={elapsed:.1f}s"
        )

    # Scalars-only baseline
    scalar_baseline = [c for c in SCALAR_COLS if c != "order_of_vanishing"]
    X_scal = df[scalar_baseline].values.astype(np.float32)
    X_scal_train, X_scal_test, _, _ = train_test_split(
        X_scal, y, test_size=0.2, random_state=42, stratify=y,
    )
    scaler_scal = StandardScaler()
    X_scal_train_s = scaler_scal.fit_transform(X_scal_train)
    X_scal_test_s = scaler_scal.transform(X_scal_test)

    scalars_results = {}
    for name, (display_name, builder) in [("GB", ("GradientBoosting", build_gb_cls)), ("LR", ("LogisticRegression", build_lr))]:
        logger.info(f"  Scalars-only {display_name} on order_of_vanishing...")
        t0 = time.time()
        model = builder()
        model.fit(X_scal_train_s, y_train)
        y_pred_s = model.predict(X_scal_test_s)
        y_proba_s = model.predict_proba(X_scal_test_s)[:, 1] if hasattr(model, "predict_proba") else None
        elapsed = time.time() - t0

        acc_s = accuracy_score(y_test, y_pred_s)
        f1_s = f1_score(y_test, y_pred_s, average="macro")
        roc_auc_s = roc_auc_score(y_test, y_proba_s) if y_proba_s is not None else None

        scalars_results[name] = {
            "accuracy": float(acc_s),
            "f1_macro": float(f1_s),
            "roc_auc": float(roc_auc_s) if roc_auc_s is not None else None,
            "fit_time": float(elapsed),
        }
        logger.info(
            f"    Acc={fmt(acc_s)}, F1={fmt(f1_s)}"
            + (f", AUC={fmt(roc_auc_s)}" if roc_auc_s else "")
            + f", time={elapsed:.1f}s"
        )

    return {"models": results, "scalars_only": scalars_results, "class_distribution": dist}


# ---------------------------------------------------------------------------
# Experiment C: Number of Zeros Prediction (regression)
# ---------------------------------------------------------------------------

def run_num_zeros(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Dict[str, Any]:
    """Predict num_zeros from features."""
    print_header("Experiment C: Number of Zeros Prediction (regression)")

    y = df["num_zeros"].values.astype(float)
    X = df[feature_cols].values.astype(np.float32)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = {}
    for name, (display_name, builder) in REG_MODELS.items():
        logger.info(f"  {display_name} on num_zeros...")
        t0 = time.time()
        model = builder()
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        elapsed = time.time() - t0

        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)

        results[name] = {
            "r2": float(r2),
            "mae": float(mae),
            "fit_time": float(elapsed),
        }
        logger.info(f"    R²={fmt(r2)}, MAE={fmt(mae)}, time={elapsed:.1f}s")

    # Scalars-only baseline
    scalar_baseline = [c for c in SCALAR_COLS if c != "num_zeros"]
    X_scal = df[scalar_baseline].values.astype(np.float32)
    X_scal_train, X_scal_test, _, _ = train_test_split(
        X_scal, y, test_size=0.2, random_state=42,
    )
    scaler_scal = StandardScaler()
    X_scal_train_s = scaler_scal.fit_transform(X_scal_train)
    X_scal_test_s = scaler_scal.transform(X_scal_test)

    scalars_results = {}
    for name, (display_name, builder) in [("GB", ("GradientBoosting", build_gb_reg)), ("MLP", ("MLP", build_mlp_reg))]:
        logger.info(f"  Scalars-only {display_name} on num_zeros...")
        t0 = time.time()
        model = builder()
        model.fit(X_scal_train_s, y_train)
        y_pred_s = model.predict(X_scal_test_s)
        elapsed = time.time() - t0

        r2_s = r2_score(y_test, y_pred_s)
        mae_s = mean_absolute_error(y_test, y_pred_s)

        scalars_results[name] = {
            "r2": float(r2_s),
            "mae": float(mae_s),
            "fit_time": float(elapsed),
        }
        logger.info(f"    R²={fmt(r2_s)}, MAE={fmt(mae_s)}, time={elapsed:.1f}s")

    return {"models": results, "scalars_only": scalars_results}


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_results(
    root_results: Dict[str, Any],
    order_results: Dict[str, Any],
    zeros_results: Dict[str, Any],
) -> None:
    """Create 2×2 summary plot."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Task 4: Binary & Ordinal Prediction from Hecke Traces", fontsize=14, fontweight="bold")

    # Panel 1: Root number — accuracy comparison
    ax = axes[0, 0]
    models = list(root_results["models"].keys())
    acc_full = [root_results["models"][m]["accuracy"] for m in models]
    acc_scal = [root_results["scalars_only"].get(m, {}).get("accuracy", 0) for m in models]

    x = np.arange(len(models))
    w = 0.35
    bars1 = ax.bar(x - w/2, acc_full, w, label="Traces + Scalars", color="#4C72B0")
    bars2 = ax.bar(x + w/2, acc_scal, w, label="Scalars Only", color="#DD8452")
    ax.set_ylabel("Accuracy")
    ax.set_title("Root Number (±1)")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend(fontsize=8)
    ax.set_ylim(0.4, 1.05)
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha='center', va='bottom', fontsize=8)

    # Panel 2: Order of vanishing — accuracy comparison
    ax = axes[0, 1]
    models = list(order_results["models"].keys())
    acc_full = [order_results["models"][m]["accuracy"] for m in models]
    acc_scal = [order_results["scalars_only"].get(m, {}).get("accuracy", 0) for m in models]

    x = np.arange(len(models))
    bars1 = ax.bar(x - w/2, acc_full, w, label="Traces + Scalars", color="#4C72B0")
    bars2 = ax.bar(x + w/2, acc_scal, w, label="Scalars Only", color="#DD8452")
    ax.set_ylabel("Accuracy")
    ax.set_title("Order of Vanishing (0 vs >0)")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend(fontsize=8)
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha='center', va='bottom', fontsize=8)

    # Panel 3: Number of zeros — R² comparison
    ax = axes[1, 0]
    models = list(zeros_results["models"].keys())
    r2_full = [zeros_results["models"][m]["r2"] for m in models]
    r2_scal = [zeros_results["scalars_only"].get(m, {}).get("r2", 0) for m in models]

    x = np.arange(len(models))
    bars1 = ax.bar(x - w/2, r2_full, w, label="Traces + Scalars", color="#4C72B0")
    bars2 = ax.bar(x + w/2, r2_scal, w, label="Scalars Only", color="#DD8452")
    ax.set_ylabel("R²")
    ax.set_title("Number of Zeros (regression)")
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend(fontsize=8)
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha='center', va='bottom', fontsize=8)

    # Panel 4: Trace contribution summary (Δ metric for each target)
    ax = axes[1, 1]
    # Best full vs best scalars for each target
    targets = ["Root Number", "Order of Vanishing", "Num Zeros"]
    full_best = [
        max(root_results["models"][m]["accuracy"] for m in root_results["models"]),
        max(order_results["models"][m]["accuracy"] for m in order_results["models"]),
        max(zeros_results["models"][m]["r2"] for m in zeros_results["models"]),
    ]
    scal_best = [
        max(root_results["scalars_only"][m]["accuracy"] for m in root_results["scalars_only"]),
        max(order_results["scalars_only"][m]["accuracy"] for m in order_results["scalars_only"]),
        max(zeros_results["scalars_only"][m]["r2"] for m in zeros_results["scalars_only"]),
    ]
    delta = [f - s for f, s in zip(full_best, scal_best)]

    colors = ["#2ca02c" if d > 0.01 else "#d62728" if d < -0.01 else "#999999" for d in delta]
    bars = ax.barh(targets, delta, color=colors)
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_xlabel("Δ (Full − Scalars)")
    ax.set_title("Trace Contribution (Best Model)")
    for bar, d in zip(bars, delta):
        ax.text(bar.get_width() + 0.002 if bar.get_width() >= 0 else bar.get_width() - 0.002,
                bar.get_y() + bar.get_height()/2,
                f"{d:+.4f}", ha='left' if bar.get_width() >= 0 else 'right',
                va='center', fontsize=9)

    plt.tight_layout()
    out_path = OUTPUT_DIR / "task_4_binary_prediction.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Plot saved to {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    t_start = time.time()

    # Load data
    logger.info(f"Loading data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    logger.info(f"  Loaded {len(df)} forms, {len(df.columns)} columns")

    # All feature columns (traces + scalars)
    all_feature_cols = TRACE_COLS + SCALAR_COLS

    # Run experiments
    root_results = run_root_number(df, all_feature_cols)
    order_results = run_order_vanishing(df, all_feature_cols)
    zeros_results = run_num_zeros(df, all_feature_cols)

    # Plot
    plot_results(root_results, order_results, zeros_results)

    # Summary
    print_header("TASK 4 SUMMARY")
    print()
    print("Experiment A — Root Number (±1):")
    for name, res in root_results["models"].items():
        auc_str = f", AUC={fmt(res['roc_auc'])}" if res.get("roc_auc") else ""
        print(f"  {name:12s}  Acc={fmt(res['accuracy'])}, F1={fmt(res['f1_macro'])}{auc_str}")
    for name, res in root_results["scalars_only"].items():
        auc_str = f", AUC={fmt(res['roc_auc'])}" if res.get("roc_auc") else ""
        print(f"  {name:12s} (scalars)  Acc={fmt(res['accuracy'])}, F1={fmt(res['f1_macro'])}{auc_str}")
    print()

    print("Experiment B — Order of Vanishing (0 vs >0):")
    for name, res in order_results["models"].items():
        auc_str = f", AUC={fmt(res['roc_auc'])}" if res.get("roc_auc") else ""
        print(f"  {name:12s}  Acc={fmt(res['accuracy'])}, F1={fmt(res['f1_macro'])}{auc_str}")
    for name, res in order_results["scalars_only"].items():
        auc_str = f", AUC={fmt(res['roc_auc'])}" if res.get("roc_auc") else ""
        print(f"  {name:12s} (scalars)  Acc={fmt(res['accuracy'])}, F1={fmt(res['f1_macro'])}{auc_str}")
    print()

    print("Experiment C — Number of Zeros:")
    for name, res in zeros_results["models"].items():
        print(f"  {name:12s}  R²={fmt(res['r2'])}, MAE={fmt(res['mae'])}")
    for name, res in zeros_results["scalars_only"].items():
        print(f"  {name:12s} (scalars)  R²={fmt(res['r2'])}, MAE={fmt(res['mae'])}")

    # Save results
    all_results = {
        "root_number": root_results,
        "order_of_vanishing": order_results,
        "num_zeros": zeros_results,
        "timing": {"total_seconds": time.time() - t_start},
    }
    out_path = OUTPUT_DIR / "task_4_binary_prediction_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info(f"Results saved to {out_path}")

    print_separator()
    elapsed = time.time() - t_start
    logger.info(f"Task 4 complete in {elapsed:.1f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
