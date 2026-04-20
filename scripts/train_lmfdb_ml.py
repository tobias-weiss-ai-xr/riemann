#!/usr/bin/env python3
"""
Train ML models on LMFDB weight-2 newform data.

Predicts analytic properties (rank, dimension, analytic conductor) from
Hecke trace sequences using sklearn models: LogisticRegression, RandomForest,
GradientBoosting, and MLP.

Usage:
    python scripts/train_lmfdb_ml.py
    python scripts/train_lmfdb_ml.py --data data/lmfdb/lmfdb_weight2_ml.csv
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

DATA_PATH = "data/lmfdb/lmfdb_weight2_ml.csv"

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
    """Return scalar feature column names (excluding traces and targets)."""
    return ["level", "dim", "char_degree", "is_cm", "is_self_dual", "Nk2"]


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------


def majority_class_baseline(
    y_train: np.ndarray, y_test: np.ndarray
) -> Dict[str, float]:
    """Predict the majority class for all samples."""
    from collections import Counter

    counts = Counter(y_train)
    majority_class = counts.most_common(1)[0][0]
    y_pred = np.full_like(y_test, majority_class)
    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_macro": f1_score(y_test, y_pred, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred),
        "name": f"Majority baseline ({majority_class})",
    }


def mean_baseline(y_train: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
    """Predict the mean of the training target."""
    y_mean = np.mean(y_train)
    y_pred = np.full_like(y_test, y_mean, dtype=float)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "name": "Mean baseline",
    }


# ---------------------------------------------------------------------------
# Model builders
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
            "MLP (64→32)",
            MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                alpha=1e-4,
                batch_size=32,
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
            "MLP (64→32)",
            MLPRegressor(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                alpha=1e-4,
                batch_size=32,
                learning_rate_init=1e-3,
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt(val: float, decimals: int = 3) -> str:
    """Format a float for table display."""
    return f"{val:.{decimals}f}"


def print_separator(char: str = "=", width: int = 72) -> None:
    print(char * width)


def print_header(text: str, width: int = 72) -> None:
    print_separator()
    padding = max(0, (width - len(text) - 2) // 2)
    print(f"  {text}".center(width))
    print_separator()


def print_classification_table(results: List[Dict]) -> None:
    """Print classification results as a formatted table."""
    header = f"  {'Model':<28s} | {'Accuracy':>8s} | {'Prec':>7s} | {'Recall':>7s} | {'F1(mac)':>8s}"
    divider = f"  {'-' * 28} | {'-' * 8} | {'-' * 7} | {'-' * 7} | {'-' * 8}"
    print(header)
    print(divider)
    for r in results:
        name = r["name"]
        acc = fmt(r["accuracy"])
        prec = fmt(r["precision"])
        rec = fmt(r["recall"])
        f1 = fmt(r["f1_macro"])
        print(f"  {name:<28s} | {acc:>8s} | {prec:>7s} | {rec:>7s} | {f1:>8s}")


def print_regression_table(results: List[Dict]) -> None:
    """Print regression results as a formatted table."""
    header = f"  {'Model':<28s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s}"
    divider = f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 8}"
    print(header)
    print(divider)
    for r in results:
        name = r["name"]
        mae = fmt(r["mae"])
        rmse = fmt(r["rmse"])
        r2 = fmt(r["r2"])
        print(f"  {name:<28s} | {mae:>8s} | {rmse:>8s} | {r2:>8s}")


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


def experiment_classification(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
) -> Tuple[List[Dict], str]:
    """
    Experiment 1: Analytic Rank Classification (binary: 0 vs 1).

    Returns (results_list, best_model_name).
    """
    print_header(f"Experiment: {target_col} Classification")

    X = df[feature_cols].values
    y = df[target_col].values

    n_samples, n_features = X.shape
    classes, counts = np.unique(y, return_counts=True)
    class_info = ", ".join(
        f"{c}={cnt} ({100 * cnt / n_samples:.1f}%)" for c, cnt in zip(classes, counts)
    )

    print(
        f"  Dataset: {n_samples} samples, {n_features} features, {len(classes)} classes"
    )
    print(f"  Target: {target_col} — {class_info}")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    print(f"  Split: {len(X_train)} train / {len(X_test)} test (stratified)")
    print()

    # Scale features
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = []

    # Baseline
    baseline = majority_class_baseline(y_train, y_test)
    results.append(baseline)
    print(f"  Baseline: {baseline['name']} (accuracy={fmt(baseline['accuracy'])})")

    # Train models
    classifiers = build_classifiers()
    for name, model in classifiers:
        logger.info(f"Training {name} for {target_col} classification...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        y_pred = model.predict(X_test_s)
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
        cm = confusion_matrix(y_test, y_pred)

        results.append(
            {
                "name": name,
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1_macro": f1,
                "confusion_matrix": cm,
                "elapsed": elapsed,
            }
        )
        logger.info(
            f"  {name}: accuracy={fmt(acc)}, F1(macro)={fmt(f1)}, time={elapsed:.1f}s"
        )

    print()
    print_classification_table(results)
    print()

    # Confusion matrices
    for r in results:
        if "confusion_matrix" in r and r["name"] != "Majority baseline (0)":
            print(f"  Confusion matrix ({r['name']}):")
            cm = r["confusion_matrix"]
            print(f"    TN={cm[0][0]:>4d}  FP={cm[0][1]:>4d}")
            print(f"    FN={cm[1][0]:>4d}  TP={cm[1][1]:>4d}")
            print()

    # Find best by F1 macro (more informative than accuracy for imbalanced data)
    best = max(
        (r for r in results if r["name"] != "Majority baseline (0)"),
        key=lambda r: r["f1_macro"],
    )
    print(
        f"  Best model: {best['name']} (accuracy={fmt(best['accuracy'])}, F1={fmt(best['f1_macro'])})"
    )
    print()

    return results, best["name"]


def experiment_regression(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    log_transform: bool = False,
    experiment_label: str = "",
) -> Tuple[List[Dict], str]:
    """
    Regression experiment.

    Returns (results_list, best_model_name).
    """
    label = experiment_label or f"{target_col} Regression"
    print_header(f"Experiment: {label}")

    X = df[feature_cols].values
    y_raw = df[target_col].values.astype(float)

    if log_transform:
        y = np.log1p(y_raw)  # log(1 + x) to handle zeros
        print(f"  Target: {target_col} (log-transformed: log(1 + x))")
        print(f"  Raw range: [{y_raw.min():.4f}, {y_raw.max():.4f}]")
        print(f"  Log range: [{y.min():.4f}, {y.max():.4f}]")
    else:
        y = y_raw
        print(f"  Target: {target_col}")
        print(
            f"  Range: [{y.min():.4f}, {y.max():.4f}], mean={y.mean():.4f}, std={y.std():.4f}"
        )

    n_samples, n_features = X.shape
    print(f"  Dataset: {n_samples} samples, {n_features} features")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )
    print(f"  Split: {len(X_train)} train / {len(X_test)} test")
    print()

    # Scale features
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = []

    # Baseline
    baseline = mean_baseline(y_train, y_test)
    results.append(baseline)
    print(
        f"  Baseline: {baseline['name']} (MAE={fmt(baseline['mae'])}, R²={fmt(baseline['r2'])})"
    )

    # Train models
    regressors = build_regressors()
    for name, model in regressors:
        logger.info(f"Training {name} for {target_col} regression...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        elapsed = time.time() - t0

        y_pred = model.predict(X_test_s)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        result = {
            "name": name,
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "elapsed": elapsed,
        }

        # If log-transformed, also compute metrics on original scale
        if log_transform:
            y_test_orig = np.expm1(y_test)
            y_pred_orig = np.expm1(y_pred)
            result["mae_orig"] = mean_absolute_error(y_test_orig, y_pred_orig)
            result["rmse_orig"] = np.sqrt(mean_squared_error(y_test_orig, y_pred_orig))
            result["r2_orig"] = r2_score(y_test_orig, y_pred_orig)
            logger.info(
                f"  {name}: MAE(log)={fmt(mae)}, R²(log)={fmt(r2)}, "
                f"MAE(orig)={fmt(result['mae_orig'])}, R²(orig)={fmt(result['r2_orig'])}, "
                f"time={elapsed:.1f}s"
            )
        else:
            logger.info(f"  {name}: MAE={fmt(mae)}, R²={fmt(r2)}, time={elapsed:.1f}s")

        results.append(result)

    print()
    print_regression_table(results)
    print()

    if log_transform:
        print("  Metrics on original scale (expm1):")
        print(f"  {'Model':<28s} | {'MAE':>8s} | {'RMSE':>8s} | {'R²':>8s}")
        print(f"  {'-' * 28} | {'-' * 8} | {'-' * 8} | {'-' * 8}")
        for r in results[1:]:  # skip baseline
            name = r["name"]
            mae = fmt(r["mae_orig"])
            rmse = fmt(r["rmse_orig"])
            r2 = fmt(r["r2_orig"])
            print(f"  {name:<28s} | {mae:>8s} | {rmse:>8s} | {r2:>8s}")
        print()

    best = max(results[1:], key=lambda r: r["r2"])
    print(f"  Best model: {best['name']} (R²={fmt(best['r2'])})")
    print()

    return results, best["name"]


def experiment_ablation(
    df: pd.DataFrame,
    target_col: str,
    task_type: str,
    best_model_name: str,
) -> None:
    """
    Experiment 4: Feature Ablation.

    Tests the best model with different feature sets.
    """
    print_header(f"Feature Ablation — {target_col} ({task_type})")
    print(f"  Best model from previous experiment: {best_model_name}")
    print()

    trace_10 = get_trace_columns(10)
    trace_50 = get_trace_columns(50)
    trace_100 = get_trace_columns(100)
    scalar_cols = get_scalar_columns()
    all_features = trace_100 + scalar_cols

    feature_sets = [
        ("First 10 traces", trace_10),
        ("First 50 traces", trace_50),
        ("All 100 traces", trace_100),
        ("100 traces + scalar features", all_features),
    ]

    results = []

    for set_name, feature_cols in feature_sets:
        X = df[feature_cols].values
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

        # Build the best model (fresh instance)
        if task_type == "classification":
            model = _build_named_classifier(best_model_name)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            acc = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
            results.append(
                {
                    "name": set_name,
                    "features": len(feature_cols),
                    "accuracy": acc,
                    "f1_macro": f1,
                    "metric_label": "F1(mac)",
                    "metric_val": f1,
                }
            )
            logger.info(
                f"  {set_name} ({len(feature_cols)} feat): acc={fmt(acc)}, F1={fmt(f1)}"
            )
        else:
            model = _build_named_regressor(best_model_name)
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            results.append(
                {
                    "name": set_name,
                    "features": len(feature_cols),
                    "r2": r2,
                    "mae": mae,
                    "metric_label": "R²",
                    "metric_val": r2,
                }
            )
            logger.info(
                f"  {set_name} ({len(feature_cols)} feat): R²={fmt(r2)}, MAE={fmt(mae)}"
            )

    # Print ablation table
    if task_type == "classification":
        print(
            f"  {'Feature Set':<32s} | {'Feats':>5s} | {'Accuracy':>8s} | {'F1(mac)':>8s}"
        )
        print(f"  {'-' * 32} | {'-' * 5} | {'-' * 8} | {'-' * 8}")
        for r in results:
            print(
                f"  {r['name']:<32s} | {r['features']:>5d} | {fmt(r['accuracy']):>8s} | {fmt(r['f1_macro']):>8s}"
            )
    else:
        print(f"  {'Feature Set':<32s} | {'Feats':>5s} | {'MAE':>8s} | {'R²':>8s}")
        print(f"  {'-' * 32} | {'-' * 5} | {'-' * 8} | {'-' * 8}")
        for r in results:
            print(
                f"  {r['name']:<32s} | {r['features']:>5d} | {fmt(r['mae']):>8s} | {fmt(r['r2']):>8s}"
            )
    print()


def _build_named_classifier(name: str):
    """Build a fresh classifier by name."""
    if name == "LogisticRegression":
        return LogisticRegression(
            max_iter=1000, random_state=42, class_weight="balanced"
        )
    elif name == "RandomForest":
        return RandomForestClassifier(
            n_estimators=100, random_state=42, class_weight="balanced"
        )
    elif name == "GradientBoosting":
        return GradientBoostingClassifier(
            n_estimators=100, max_depth=5, random_state=42
        )
    elif name == "MLP (64→32)":
        return MLPClassifier(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size=32,
            learning_rate_init=1e-3,
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
        )
    else:
        raise ValueError(f"Unknown classifier: {name}")


def _build_named_regressor(name: str):
    """Build a fresh regressor by name."""
    if name == "RandomForest":
        return RandomForestRegressor(n_estimators=100, random_state=42)
    elif name == "GradientBoosting":
        return GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
    elif name == "MLP (64→32)":
        return MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation="relu",
            solver="adam",
            alpha=1e-4,
            batch_size=32,
            learning_rate_init=1e-3,
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
        )
    else:
        raise ValueError(f"Unknown regressor: {name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train ML models on LMFDB weight-2 newform data",
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
    print("=" * 72)
    print("  LMFDB Weight-2 Newforms — ML Training Pipeline".center(72))
    print("=" * 72)
    print()

    # Load data
    df = load_data(args.data)

    trace_cols = get_trace_columns(100)
    logger.info(f"Feature columns: {len(trace_cols)} trace features")
    logger.info(f"Columns: {list(df.columns[:15])} ...")

    # ------------------------------------------------------------------
    # Experiment 1: Analytic Rank Classification
    # ------------------------------------------------------------------
    rank_results, best_rank_model = experiment_classification(
        df,
        trace_cols,
        "analytic_rank",
    )

    # ------------------------------------------------------------------
    # Experiment 2: Dimension Regression
    # ------------------------------------------------------------------
    dim_results, best_dim_model = experiment_regression(
        df,
        trace_cols,
        "dim",
        experiment_label="Dimension (dim) Regression",
    )

    # ------------------------------------------------------------------
    # Experiment 3: Analytic Conductor Regression (log-transformed)
    # ------------------------------------------------------------------
    cond_results, best_cond_model = experiment_regression(
        df,
        trace_cols,
        "analytic_conductor",
        log_transform=True,
        experiment_label="Analytic Conductor Regression (log-transformed)",
    )

    # ------------------------------------------------------------------
    # Experiment 4: Feature Ablation
    # ------------------------------------------------------------------
    if not args.skip_ablation:
        experiment_ablation(df, "analytic_rank", "classification", best_rank_model)
        experiment_ablation(df, "dim", "regression", best_dim_model)
        experiment_ablation(df, "analytic_conductor", "regression", best_cond_model)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - t_start
    print_separator()
    print(f"  SUMMARY".center(72))
    print_separator()
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Samples: {len(df)}, Features: {len(trace_cols)}")
    print()
    print(f"  Analytic Rank Classification — Best: {best_rank_model}")
    best_r = max(
        (r for r in rank_results if r["name"] != "Majority baseline (0)"),
        key=lambda r: r["f1_macro"],
    )
    print(
        f"    Accuracy: {fmt(best_r['accuracy'])}, F1(macro): {fmt(best_r['f1_macro'])}"
    )
    print()
    print(f"  Dimension Regression — Best: {best_dim_model}")
    best_d = max(dim_results[1:], key=lambda r: r["r2"])
    print(f"    MAE: {fmt(best_d['mae'])}, R²: {fmt(best_d['r2'])}")
    print()
    print(f"  Analytic Conductor Regression — Best: {best_cond_model}")
    best_c = max(cond_results[1:], key=lambda r: r["r2"])
    print(
        f"    R²(log): {fmt(best_c['r2'])}, R²(orig): {fmt(best_c.get('r2_orig', best_c['r2']))}"
    )
    print()
    print_separator()
    print()


if __name__ == "__main__":
    main()
