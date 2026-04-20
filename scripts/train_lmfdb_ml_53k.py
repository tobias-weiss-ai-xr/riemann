#!/usr/bin/env python3
"""
Experiment 10: Train ML models on LMFDB SQL Mirror Dataset (53,779 records).

Predicts analytic properties from Hecke traces using sklearn models.
This is a 53x scale-up from Experiment 9 (1,000 records).

Sub-experiments:
  10a: Multi-class Rank Classification (rank 0 vs 1 vs 2)
  10b: Dimension Regression
  10c: Analytic Conductor Regression (log-transformed)
  10d: CM Form Classification (binary)
  10e: Feature Ablation (best model per task)

Usage:
    python scripts/train_lmfdb_ml_53k.py
    python scripts/train_lmfdb_ml_53k.py --data data/lmfdb/lmfdb_sql_weight2_ml.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

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
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_PATH = "data/lmfdb/lmfdb_sql_weight2_ml.csv"

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
    """Load LMFDB ML dataset."""
    logger.info(f"Loading data from {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded {len(df)} samples with {len(df.columns)} columns")
    return df


def get_trace_columns(n: int = 100) -> List[str]:
    """Return column names for first n Hecke traces."""
    return [f"trace_{i}" for i in range(1, n + 1)]


def get_scalar_columns() -> List[str]:
    """Return scalar feature column names (excluding traces, targets, label)."""
    return ["level", "dim", "char_degree", "is_cm", "is_self_dual", "Nk2"]


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
# Model builders (larger hidden layers for 53k dataset)
# ---------------------------------------------------------------------------


def build_classifiers() -> List[Tuple[str, Any]]:
    """Return list of (name, model) tuples for classification."""
    return [
        (
            "LogisticRegression",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
                class_weight="balanced",
            ),
        ),
        (
            "RandomForest",
            RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight="balanced",
                n_jobs=-1,
            ),
        ),
        (
            "GradientBoosting",
            GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42,
            ),
        ),
        (
            "MLP (128→64)",
            MLPClassifier(
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
            "MLP (128→64)",
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


def build_named_classifier(name: str):
    """Build a fresh classifier by name."""
    if name == "LogisticRegression":
        return LogisticRegression(
            max_iter=1000, random_state=42, class_weight="balanced"
        )
    elif name == "RandomForest":
        return RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced", n_jobs=-1
        )
    elif name == "GradientBoosting":
        return GradientBoostingClassifier(
            n_estimators=100, max_depth=5, random_state=42
        )
    elif name == "MLP (128→64)":
        return MLPClassifier(
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
        raise ValueError(f"Unknown classifier: {name}")


def build_named_regressor(name: str):
    """Build a fresh regressor by name."""
    if name == "RandomForest":
        return RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    elif name == "GradientBoosting":
        return GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
    elif name == "MLP (128→64)":
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
# Experiment 10a: Multi-class Rank Classification
# ---------------------------------------------------------------------------


def experiment_rank_classification(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Tuple[List[Dict], str]:
    """
    Exp 10a: Multi-class Analytic Rank Classification (0 vs 1 vs 2).
    """
    print_header("Exp 10a: Multi-class Rank Classification (rank 0 / 1 / 2)")

    X = df[feature_cols].values
    y = df["analytic_rank"].values

    n_samples, n_features = X.shape
    classes = sorted(np.unique(y).astype(int))
    counts = {c: int(np.sum(y == c)) for c in classes}
    class_info = ", ".join(
        f"rank {c}={counts[c]} ({100 * counts[c] / n_samples:.1f}%)" for c in classes
    )

    print(
        f"  Dataset: {n_samples} samples, {n_features} features, {len(classes)} classes"
    )
    print(f"  Target: analytic_rank — {class_info}")
    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    print(f"  Split: {len(X_train)} train / {len(X_test)} test (stratified)")
    print()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Majority baseline
    from collections import Counter

    majority_class = Counter(y_train).most_common(1)[0][0]
    y_pred_base = np.full_like(y_test, majority_class)
    baseline_acc = accuracy_score(y_test, y_pred_base)
    baseline_f1 = f1_score(y_test, y_pred_base, average="macro", zero_division=0)
    print(
        f"  Majority baseline (predict {int(majority_class)}): accuracy={fmt(baseline_acc)}, F1(macro)={fmt(baseline_f1)}"
    )
    print()

    results = []
    classifiers = build_classifiers()

    for name, model in classifiers:
        logger.info(f"Training {name} for rank classification...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        y_pred = model.predict(X_test_s)
        acc = accuracy_score(y_test, y_pred)
        f1_mac = f1_score(y_test, y_pred, average="macro", zero_division=0)
        f1_wt = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        cm = confusion_matrix(y_test, y_pred)

        # Per-class F1
        per_class_f1 = {}
        for c in classes:
            per_class_f1[c] = f1_score(
                (y_test == c).astype(int),
                (y_pred == c).astype(int),
                zero_division=0,
            )

        results.append(
            {
                "name": name,
                "accuracy": acc,
                "f1_macro": f1_mac,
                "f1_weighted": f1_wt,
                "per_class_f1": per_class_f1,
                "confusion_matrix": cm,
                "elapsed": elapsed,
            }
        )
        logger.info(
            f"  {name}: accuracy={fmt(acc)}, F1(mac)={fmt(f1_mac)}, time={elapsed:.1f}s"
        )

    # Print table
    print(
        f"  {'Model':<28s} | {'Accuracy':>8s} | {'F1(mac)':>8s} | {'F1(wt)':>8s} | {'Time':>6s}"
    )
    print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 8} | {'-' * 6}")
    for r in results:
        print(
            f"  {r['name']:<28s} | {fmt(r['accuracy']):>8s} | {fmt(r['f1_macro']):>8s} | "
            f"{fmt(r['f1_weighted']):>8s} | {r['elapsed']:>5.1f}s"
        )
    print()

    # Per-class F1 table
    print("  Per-class F1 scores:")
    class_strs = [f"rank {c}" for c in classes]
    print(f"  {'Model':<28s} | " + " | ".join(f"{s:>8s}" for s in class_strs))
    print(f"  {'-' * 28} | " + " | ".join(f"{'-' * 8}" for _ in classes))
    for r in results:
        vals = [fmt(r["per_class_f1"][c]) for c in classes]
        print(f"  {r['name']:<28s} | " + " | ".join(f"{v:>8s}" for v in vals))
    print()

    # Confusion matrices
    for r in results:
        cm = r["confusion_matrix"]
        print(f"  Confusion matrix ({r['name']}):")
        for i, c in enumerate(classes):
            row = "  ".join(f"{cm[i][j]:>6d}" for j in range(len(classes)))
            print(f"    Actual {c}: {row}")
        print(f"    {'':>10s}  " + "  ".join(f"Pred {c:>5d}" for c in classes))
        print()

    # Classification report for best model
    best_idx = np.argmax([r["f1_macro"] for r in results])
    best_name = results[best_idx]["name"]
    best_model = build_named_classifier(best_name)
    best_model.fit(X_train_s, y_train)
    y_pred_best = best_model.predict(X_test_s)

    print(f"  Classification report (best: {best_name}):")
    print(classification_report(y_test, y_pred_best, digits=3))

    best = results[best_idx]
    print(
        f"  Best model: {best_name} (accuracy={fmt(best['accuracy'])}, F1(macro)={fmt(best['f1_macro'])})"
    )
    print()

    return results, best_name


# ---------------------------------------------------------------------------
# Experiment 10b: Dimension Regression
# ---------------------------------------------------------------------------


def experiment_dimension_regression(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Tuple[List[Dict], str]:
    """
    Exp 10b: Dimension (dim) Regression.
    """
    print_header("Exp 10b: Dimension Regression")

    X = df[feature_cols].values
    y = df["dim"].values.astype(float)

    n_samples, n_features = X.shape
    print(f"  Dataset: {n_samples} samples, {n_features} features")
    print(
        f"  Target: dim — range=[{y.min():.0f}, {y.max():.0f}], mean={y.mean():.2f}, std={y.std():.2f}"
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

    # Baseline
    y_mean = np.mean(y_train)
    y_pred_base = np.full_like(y_test, y_mean, dtype=float)
    base_mae = mean_absolute_error(y_test, y_pred_base)
    base_r2 = r2_score(y_test, y_pred_base)
    print(f"  Mean baseline: MAE={fmt(base_mae)}, R²={fmt(base_r2)}")
    print()

    results = []
    regressors = build_regressors()

    for name, model in regressors:
        logger.info(f"Training {name} for dimension regression...")
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
        logger.info(f"  {name}: MAE={fmt(mae)}, R²={fmt(r2)}, time={elapsed:.1f}s")

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
        f"  Best model: {best['name']} (MAE={fmt(best['mae'])}, R²={fmt(best['r2'])})"
    )
    print()

    return results, best["name"]


# ---------------------------------------------------------------------------
# Experiment 10c: Analytic Conductor Regression (log-transformed)
# ---------------------------------------------------------------------------


def experiment_conductor_regression(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Tuple[List[Dict], str]:
    """
    Exp 10c: Analytic Conductor Regression (log-transformed).
    """
    print_header("Exp 10c: Analytic Conductor Regression (log-transformed)")

    X = df[feature_cols].values
    y_raw = df["analytic_conductor"].values.astype(float)
    y = np.log1p(y_raw)

    n_samples, n_features = X.shape
    print(f"  Dataset: {n_samples} samples, {n_features} features")
    print(f"  Target: analytic_conductor (log-transformed: log(1+x))")
    print(f"  Raw range: [{y_raw.min():.2f}, {y_raw.max():.2f}]")
    print(f"  Log range: [{y.min():.4f}, {y.max():.4f}]")
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

    # Baseline
    y_mean = np.mean(y_train)
    y_pred_base = np.full_like(y_test, y_mean, dtype=float)
    base_mae = mean_absolute_error(y_test, y_pred_base)
    base_r2 = r2_score(y_test, y_pred_base)
    print(f"  Mean baseline: MAE(log)={fmt(base_mae)}, R²(log)={fmt(base_r2)}")
    print()

    results = []
    regressors = build_regressors()

    for name, model in regressors:
        logger.info(f"Training {name} for conductor regression...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        y_pred = model.predict(X_test_s)

        # Log-scale metrics
        mae_log = mean_absolute_error(y_test, y_pred)
        r2_log = r2_score(y_test, y_pred)

        # Original-scale metrics
        y_test_orig = np.expm1(y_test)
        y_pred_orig = np.expm1(y_pred)
        mae_orig = mean_absolute_error(y_test_orig, y_pred_orig)
        r2_orig = r2_score(y_test_orig, y_pred_orig)

        results.append(
            {
                "name": name,
                "mae_log": mae_log,
                "r2_log": r2_log,
                "mae_orig": mae_orig,
                "r2_orig": r2_orig,
                "elapsed": elapsed,
            }
        )
        logger.info(
            f"  {name}: MAE(log)={fmt(mae_log)}, R²(log)={fmt(r2_log)}, "
            f"MAE(orig)={fmt(mae_orig)}, R²(orig)={fmt(r2_orig)}, time={elapsed:.1f}s"
        )

    # Log-scale table
    print(f"  Metrics on LOG scale:")
    print(f"  {'Model':<28s} | {'MAE':>8s} | {'R²':>8s} | {'Time':>6s}")
    print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 6}")
    for r in results:
        print(
            f"  {r['name']:<28s} | {fmt(r['mae_log']):>8s} | {fmt(r['r2_log']):>8s} | {r['elapsed']:>5.1f}s"
        )
    print()

    # Original-scale table
    print(f"  Metrics on ORIGINAL scale (expm1):")
    print(f"  {'Model':<28s} | {'MAE':>8s} | {'R²':>8s}")
    print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8}")
    for r in results:
        print(
            f"  {r['name']:<28s} | {fmt(r['mae_orig']):>8s} | {fmt(r['r2_orig']):>8s}"
        )
    print()

    best = max(results, key=lambda r: r["r2_log"])
    print(
        f"  Best model: {best['name']} "
        f"(R²(log)={fmt(best['r2_log'])}, R²(orig)={fmt(best['r2_orig'])})"
    )
    print()

    return results, best["name"]


# ---------------------------------------------------------------------------
# Experiment 10d: CM Form Classification
# ---------------------------------------------------------------------------


def experiment_cm_classification(
    df: pd.DataFrame,
    feature_cols: List[str],
) -> Tuple[List[Dict], str]:
    """
    Exp 10d: CM Form Classification (binary: CM vs non-CM).
    """
    print_header("Exp 10d: CM Form Classification (binary)")

    X = df[feature_cols].values
    y = df["is_cm"].values

    n_samples, n_features = X.shape
    n_cm = int(np.sum(y == 1))
    n_non_cm = int(np.sum(y == 0))
    print(f"  Dataset: {n_samples} samples, {n_features} features")
    print(
        f"  Target: is_cm — non-CM={n_non_cm} ({100 * n_non_cm / n_samples:.1f}%), CM={n_cm} ({100 * n_cm / n_samples:.1f}%)"
    )
    print()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    print(f"  Split: {len(X_train)} train / {len(X_test)} test (stratified)")
    print()

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Majority baseline
    from collections import Counter

    majority_class = Counter(y_train).most_common(1)[0][0]
    y_pred_base = np.full_like(y_test, majority_class)
    base_acc = accuracy_score(y_test, y_pred_base)
    base_f1 = f1_score(y_test, y_pred_base, zero_division=0)
    print(
        f"  Majority baseline (predict {int(majority_class)}): accuracy={fmt(base_acc)}, F1={fmt(base_f1)}"
    )
    print()

    results = []
    classifiers = build_classifiers()

    for name, model in classifiers:
        logger.info(f"Training {name} for CM classification...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        y_pred = model.predict(X_test_s)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        f1_mac = f1_score(y_test, y_pred, average="macro", zero_division=0)
        cm = confusion_matrix(y_test, y_pred)

        results.append(
            {
                "name": name,
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "f1_macro": f1_mac,
                "confusion_matrix": cm,
                "elapsed": elapsed,
            }
        )
        logger.info(f"  {name}: accuracy={fmt(acc)}, F1={fmt(f1)}, time={elapsed:.1f}s")

    # Print table
    print(
        f"  {'Model':<28s} | {'Accuracy':>8s} | {'Prec':>7s} | {'Recall':>7s} | {'F1':>7s} | {'Time':>6s}"
    )
    print(f"  {'-' * 28} | {'-' * 8} | {'-' * 7} | {'-' * 7} | {'-' * 7} | {'-' * 6}")
    for r in results:
        print(
            f"  {r['name']:<28s} | {fmt(r['accuracy']):>8s} | {fmt(r['precision']):>7s} | "
            f"{fmt(r['recall']):>7s} | {fmt(r['f1']):>7s} | {r['elapsed']:>5.1f}s"
        )
    print()

    # Confusion matrices
    for r in results:
        cm = r["confusion_matrix"]
        print(f"  Confusion matrix ({r['name']}):")
        print(f"    TN(non-CM)={cm[0][0]:>6d}  FP={cm[0][1]:>6d}")
        print(f"    FN(CM)      ={cm[1][0]:>6d}  TP={cm[1][1]:>6d}")
        print()

    best = max(results, key=lambda r: r["f1"])
    print(
        f"  Best model: {best['name']} (accuracy={fmt(best['accuracy'])}, F1={fmt(best['f1'])})"
    )
    print()

    return results, best["name"]


# ---------------------------------------------------------------------------
# Experiment 10e: Feature Ablation
# ---------------------------------------------------------------------------


def experiment_ablation(
    df: pd.DataFrame,
    target_col: str,
    task_type: str,
    best_model_name: str,
    log_transform: bool = False,
    experiment_label: str = "",
) -> None:
    """
    Exp 10e: Feature Ablation — test best model with different feature sets.
    """
    label = experiment_label or f"{target_col}"
    print_header(f"Exp 10e: Feature Ablation — {label}")

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
    print(f"  Task: {task_type}")
    print()

    results = []

    for set_name, feat_cols in feature_sets:
        X = df[feat_cols].values
        y = df[target_col].values

        if task_type == "classification":
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
                stratify=y,
            )
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
            )

        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        if log_transform:
            y_train = np.log1p(y_train.astype(float))
            y_test = np.log1p(y_test.astype(float))

        if task_type == "classification":
            model = build_named_classifier(best_model_name)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            acc = accuracy_score(y_test, y_pred)
            f1_mac = f1_score(y_test, y_pred, average="macro", zero_division=0)
            results.append(
                {
                    "name": set_name,
                    "features": len(feat_cols),
                    "accuracy": acc,
                    "f1_macro": f1_mac,
                }
            )
            logger.info(
                f"  {set_name} ({len(feat_cols)} feat): acc={fmt(acc)}, F1={fmt(f1_mac)}"
            )
        else:
            model = build_named_regressor(best_model_name)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            results.append(
                {
                    "name": set_name,
                    "features": len(feat_cols),
                    "r2": r2,
                    "mae": mae,
                }
            )
            logger.info(
                f"  {set_name} ({len(feat_cols)} feat): R²={fmt(r2)}, MAE={fmt(mae)}"
            )

    # Print ablation table
    if task_type == "classification":
        print(
            f"  {'Feature Set':<32s} | {'Feats':>5s} | {'Accuracy':>8s} | {'F1(mac)':>8s}"
        )
        print(f"  {'-' * 32} | {'-' * 5} | {'-' * 8} | {'-' * 8}")
        for r in results:
            print(
                f"  {r['name']:<32s} | {r['features']:>5d} | "
                f"{fmt(r['accuracy']):>8s} | {fmt(r['f1_macro']):>8s}"
            )
    else:
        print(f"  {'Feature Set':<32s} | {'Feats':>5s} | {'MAE':>8s} | {'R²':>8s}")
        print(f"  {'-' * 32} | {'-' * 5} | {'-' * 8} | {'-' * 8}")
        for r in results:
            print(
                f"  {r['name']:<32s} | {r['features']:>5d} | "
                f"{fmt(r['mae']):>8s} | {fmt(r['r2']):>8s}"
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
    print(f"  Dimension range: [{df['dim'].min()}, {df['dim'].max()}]")
    print(
        f"  Analytic conductor range: [{df['analytic_conductor'].min():.2f}, {df['analytic_conductor'].max():.2f}]"
    )
    print()

    # Rank distribution
    rank_counts = df["analytic_rank"].value_counts().sort_index()
    print("  Analytic rank distribution:")
    for rank, count in rank_counts.items():
        pct = 100 * count / len(df)
        print(f"    rank {int(rank)}: {count:>6d} ({pct:.1f}%)")
    print()

    # CM statistics
    n_cm = int(df["is_cm"].sum())
    n_non_cm = len(df) - n_cm
    print(f"  CM forms: {n_cm} ({100 * n_cm / len(df):.1f}%)")
    print(f"  Non-CM forms: {n_non_cm} ({100 * n_non_cm / len(df):.1f}%)")
    print()

    # Self-dual statistics
    n_sd = int(df["is_self_dual"].sum())
    print(f"  Self-dual forms: {n_sd} ({100 * n_sd / len(df):.1f}%)")
    print()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(
    df: pd.DataFrame,
    rank_results: List[Dict],
    dim_results: List[Dict],
    cond_results: List[Dict],
    cm_results: List[Dict],
    best_rank_model: str,
    best_dim_model: str,
    best_cond_model: str,
    best_cm_model: str,
    total_time: float,
) -> None:
    """Print final summary with Experiment 9 comparison."""
    print_separator()
    print("  EXPERIMENT 10 — SUMMARY (53,779 records from LMFDB SQL Mirror)".center(78))
    print_separator()
    print(f"  Total training time: {total_time:.1f}s")
    print()

    # Rank classification summary
    best_r = max(rank_results, key=lambda r: r["f1_macro"])
    print(
        "  ┌─────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "  │ Exp 10a: Multi-class Rank Classification                                │"
    )
    print(
        "  ├─────────────────────────────────────────────────────────────────────────┤"
    )
    print(f"  │ Best model:       {best_rank_model:<48s} │")
    print(f"  │ Accuracy:         {fmt(best_r['accuracy']):<48s} │")
    print(f"  │ F1 (macro):       {fmt(best_r['f1_macro']):<48s} │")
    print(f"  │ F1 (weighted):    {fmt(best_r['f1_weighted']):<48s} │")
    per_class = best_r["per_class_f1"]
    for c in sorted(per_class.keys()):
        print(f"  │ F1 (rank {c}):       {fmt(per_class[c]):<48s} │")
    print(f"  │ Exp 9 baseline:   F1=0.839 (binary, 1000 records)              │")
    print(
        "  └─────────────────────────────────────────────────────────────────────────┘"
    )
    print()

    # Dimension regression summary
    best_d = max(dim_results, key=lambda r: r["r2"])
    print(
        "  ┌─────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "  │ Exp 10b: Dimension Regression                                           │"
    )
    print(
        "  ├─────────────────────────────────────────────────────────────────────────┤"
    )
    print(f"  │ Best model:       {best_dim_model:<48s} │")
    print(f"  │ MAE:              {fmt(best_d['mae']):<48s} │")
    print(f"  │ R²:               {fmt(best_d['r2']):<48s} │")
    print(f"  │ Exp 9 baseline:   R²=0.976 (1000 records)                       │")
    print(
        "  └─────────────────────────────────────────────────────────────────────────┘"
    )
    print()

    # Conductor regression summary
    best_c = max(cond_results, key=lambda r: r["r2_log"])
    print(
        "  ┌─────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "  │ Exp 10c: Analytic Conductor Regression (log-transformed)                 │"
    )
    print(
        "  ├─────────────────────────────────────────────────────────────────────────┤"
    )
    print(f"  │ Best model:       {best_cond_model:<48s} │")
    print(f"  │ MAE (log):        {fmt(best_c['mae_log']):<48s} │")
    print(f"  │ R² (log):         {fmt(best_c['r2_log']):<48s} │")
    print(f"  │ R² (original):    {fmt(best_c['r2_orig']):<48s} │")
    print(f"  │ Exp 9 baseline:   R²(log)=0.142 (1000 records)                  │")
    print(
        "  └─────────────────────────────────────────────────────────────────────────┘"
    )
    print()

    # CM classification summary
    best_cm = max(cm_results, key=lambda r: r["f1"])
    print(
        "  ┌─────────────────────────────────────────────────────────────────────────┐"
    )
    print(
        "  │ Exp 10d: CM Form Classification (NEW — not tested in Exp 9)             │"
    )
    print(
        "  ├─────────────────────────────────────────────────────────────────────────┤"
    )
    print(f"  │ Best model:       {best_cm_model:<48s} │")
    print(f"  │ Accuracy:         {fmt(best_cm['accuracy']):<48s} │")
    print(f"  │ Precision:        {fmt(best_cm['precision']):<48s} │")
    print(f"  │ Recall:           {fmt(best_cm['recall']):<48s} │")
    print(f"  │ F1:               {fmt(best_cm['f1']):<48s} │")
    print(
        "  └─────────────────────────────────────────────────────────────────────────┘"
    )
    print()

    # Comparison with Experiment 9
    print_separator()
    print("  Comparison with Experiment 9 (1,000 records)".center(78))
    print_separator()
    print(
        f"  {'Task':<30s} | {'Metric':>8s} | {'Exp 9':>10s} | {'Exp 10':>10s} | {'Change':>10s}"
    )
    print(f"  {'-' * 30} | {'-' * 8} | {'-' * 10} | {'-' * 10} | {'-' * 10}")

    # Rank
    e9_rank_f1 = 0.839
    e10_rank_f1 = best_r["f1_macro"]
    delta = e10_rank_f1 - e9_rank_f1
    sign = "+" if delta >= 0 else ""
    print(
        f"  {'Rank Classification':<30s} | {'F1(mac)':>8s} | {fmt(e9_rank_f1):>10s} | {fmt(e10_rank_f1):>10s} | {sign}{fmt(delta):>10s}"
    )

    # Dimension
    e9_dim_r2 = 0.976
    e10_dim_r2 = best_d["r2"]
    delta = e10_dim_r2 - e9_dim_r2
    sign = "+" if delta >= 0 else ""
    print(
        f"  {'Dimension Regression':<30s} | {'R²':>8s} | {fmt(e9_dim_r2):>10s} | {fmt(e10_dim_r2):>10s} | {sign}{fmt(delta):>10s}"
    )

    # Conductor
    e9_cond_r2 = 0.142
    e10_cond_r2 = best_c["r2_log"]
    delta = e10_cond_r2 - e9_cond_r2
    sign = "+" if delta >= 0 else ""
    print(
        f"  {'Conductor Reg (log)':<30s} | {'R²':>8s} | {fmt(e9_cond_r2):>10s} | {fmt(e10_cond_r2):>10s} | {sign}{fmt(delta):>10s}"
    )

    print()
    print("  Key differences:")
    print("    - Exp 10 uses 53,779 records (53x more than Exp 9's 1,000)")
    print(
        "    - Exp 10 has 3-class rank classification (rank 0/1/2); Exp 9 was binary (0/1)"
    )
    print("    - Exp 10 adds CM form classification (Exp 9 did not test this)")
    print("    - Exp 10 uses larger MLP (128→64) vs Exp 9 (64→32)")
    print()
    print_separator()
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experiment 10: Train ML models on LMFDB SQL Mirror (53k records)",
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
    print(
        "  Experiment 10: LMFDB SQL Mirror — ML Training Pipeline (53,779 records)".center(
            78
        )
    )
    print("=" * 78)
    print()

    # Load data
    df = load_data(args.data)

    # Dataset statistics
    print_dataset_statistics(df)

    trace_cols = get_trace_columns(100)
    logger.info(f"Feature columns: {len(trace_cols)} trace features")

    # ------------------------------------------------------------------
    # Exp 10a: Multi-class Rank Classification (0 vs 1 vs 2)
    # ------------------------------------------------------------------
    rank_results, best_rank_model = experiment_rank_classification(df, trace_cols)

    # ------------------------------------------------------------------
    # Exp 10b: Dimension Regression
    # ------------------------------------------------------------------
    dim_results, best_dim_model = experiment_dimension_regression(df, trace_cols)

    # ------------------------------------------------------------------
    # Exp 10c: Analytic Conductor Regression (log-transformed)
    # ------------------------------------------------------------------
    cond_results, best_cond_model = experiment_conductor_regression(df, trace_cols)

    # ------------------------------------------------------------------
    # Exp 10d: CM Form Classification
    # ------------------------------------------------------------------
    cm_results, best_cm_model = experiment_cm_classification(df, trace_cols)

    # ------------------------------------------------------------------
    # Exp 10e: Feature Ablation
    # ------------------------------------------------------------------
    if not args.skip_ablation:
        experiment_ablation(
            df,
            "analytic_rank",
            "classification",
            best_rank_model,
            experiment_label="Rank Classification",
        )
        experiment_ablation(
            df,
            "dim",
            "regression",
            best_dim_model,
            experiment_label="Dimension Regression",
        )
        experiment_ablation(
            df,
            "analytic_conductor",
            "regression",
            best_cond_model,
            log_transform=True,
            experiment_label="Conductor Regression (log)",
        )
        experiment_ablation(
            df,
            "is_cm",
            "classification",
            best_cm_model,
            experiment_label="CM Classification",
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    total_time = time.time() - t_start
    print_summary(
        df,
        rank_results,
        dim_results,
        cond_results,
        cm_results,
        best_rank_model,
        best_dim_model,
        best_cond_model,
        best_cm_model,
        total_time,
    )


if __name__ == "__main__":
    main()
