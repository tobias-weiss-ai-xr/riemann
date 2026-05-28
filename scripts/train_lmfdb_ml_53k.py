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

Extended pipeline (v2):
 - --hpo: Optuna hyperparameter optimization (50+ trials, TPESampler)
 - --cv:   StratifiedKFold/KFold cross-validation
 - Stacking ensemble (GBT+RF+LR → LR meta)
 - Polynomial & interaction features
 - XGBoost with Optuna tuning
 - Model persistence via joblib
 - Feature importance plots (PNG)
 - --features: feature subset selection

Usage:
    python scripts/train_lmfdb_ml_53k.py
    python scripts/train_lmfdb_ml_53k.py --hpo --cv
    python scripts/train_lmfdb_ml_53k.py --features all --hpo --hpo-trials 100
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    import optuna as optuna_lib

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
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
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    train_test_split,
)
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import StandardScaler, PolynomialFeatures

# Optional imports — gracefully degrade if not available
try:
    import joblib
except ImportError:  # pragma: no cover
    joblib = None  # type: ignore[assignment]

try:
    import optuna
except ImportError:  # pragma: no cover
    optuna = None  # type: ignore[assignment]

try:
    import xgboost as xgb
except ImportError:  # pragma: no cover
    xgb = None  # type: ignore[assignment]

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", category=FutureWarning, module="xgboost")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_PATH = "data/lmfdb/lmfdb_sql_weight2_ml.csv"
MODEL_DIR = Path("data/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

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
# Feature selection
# ---------------------------------------------------------------------------


def select_features(df: pd.DataFrame, feature_mode: str) -> List[str]:
    """Return feature column list based on --features flag."""
    trace_100 = get_trace_columns(100)
    scalar_cols = get_scalar_columns()

    if feature_mode == "traces":
        return trace_100
    elif feature_mode == "scalars":
        return scalar_cols
    elif feature_mode == "all":
        return trace_100 + scalar_cols
    else:
        raise ValueError(f"Unknown feature mode: {feature_mode}")


def build_polynomial_features(
    X: np.ndarray,
    trace_indices: Optional[List[int]] = None,
    degree: int = 2,
) -> np.ndarray:
    """Add polynomial and interaction features on top-K trace columns.

    If trace_indices is None, transforms all columns.
    Original features are prepended unchanged, then polynomial terms appended.
    """
    if trace_indices is not None:
        X_sub = X[:, trace_indices]
    else:
        X_sub = X

    poly = PolynomialFeatures(degree=degree, include_bias=False, interaction_only=False)
    X_poly = poly.fit_transform(X_sub)

    # poly includes original terms at indices [0:n_sub]; we want to deduplicate
    n_sub = X_sub.shape[1]
    n_new = X_poly.shape[1] - n_sub  # poly + interaction terms only
    if n_new == 0:
        return X

    # Append only the new (higher-degree) terms
    X_ext = np.concatenate([X, X_poly[:, n_sub:]], axis=1)
    logger.info(f"Polynomial features: {X.shape[1]} → {X_ext.shape[1]} "
                f"(+{n_new} poly/interaction terms on {n_sub} base columns)")
    return X_ext


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
            "MLP (128->64)",
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


def build_xgb_classifiers(n_trials: Optional[int] = None) -> List[Tuple[str, Any]]:
    """Return XGBoost classifier(s). If n_trials given, returns untrained
    placeholder — actual best params are loaded from the HPO study."""
    if xgb is None:
        return []
    return [
        (
            "XGBoost",
            xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbosity=0,
                use_label_encoder=False,
                eval_metric="mlogloss" if n_trials else "logloss",
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


def build_xgb_regressors() -> List[Tuple[str, Any]]:
    """Return XGBoost regressor(s)."""
    if xgb is None:
        return []
    return [
        (
            "XGBoost",
            xgb.XGBRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                verbosity=0,
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
    elif name == "MLP (128->64)":
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
    elif name == "XGBoost":
        if xgb is None:
            raise ImportError("xgboost not available")
        return xgb.XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
            use_label_encoder=False,
        )
    else:
        raise ValueError(f"Unknown classifier: {name}")


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
    elif name == "XGBoost":
        if xgb is None:
            raise ImportError("xgboost not available")
        return xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )
    else:
        raise ValueError(f"Unknown regressor: {name}")


# ---------------------------------------------------------------------------
# Cross-validation wrapper
# ---------------------------------------------------------------------------


def cross_validate_model(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    task_type: str,
    n_folds: int = 5,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Run k-fold CV and return aggregated metrics."""
    if task_type == "classification":
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    else:
        cv = KFold(n_splits=n_folds, shuffle=True, random_state=random_state)

    metrics_list: List[Dict[str, float]] = []
    scaler = StandardScaler()

    for fold, (train_idx, val_idx) in enumerate(cv.split(X, y)):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        X_tr_s = scaler.fit_transform(X_tr)
        X_val_s = scaler.transform(X_val)

        model_cp = (
            model.__class__(**model.get_params())
            if hasattr(model, "get_params")
            else model
        )
        if hasattr(model_cp, "set_params"):
            # Ensure reproducibility
            model_cp.set_params(random_state=random_state + fold)
        model_cp.fit(X_tr_s, y_tr)
        y_pred = model_cp.predict(X_val_s)

        fold_metrics: Dict[str, float] = {}
        if task_type == "classification":
            fold_metrics["accuracy"] = float(accuracy_score(y_val, y_pred))
            fold_metrics["f1_macro"] = float(
                f1_score(y_val, y_pred, average="macro", zero_division=0)
            )
            fold_metrics["f1_weighted"] = float(
                f1_score(y_val, y_pred, average="weighted", zero_division=0)
            )
            fold_metrics["precision_macro"] = float(
                precision_score(y_val, y_pred, average="macro", zero_division=0)
            )
            fold_metrics["recall_macro"] = float(
                recall_score(y_val, y_pred, average="macro", zero_division=0)
            )
        else:
            fold_metrics["r2"] = float(r2_score(y_val, y_pred))
            fold_metrics["mae"] = float(mean_absolute_error(y_val, y_pred))
            fold_metrics["mse"] = float(mean_squared_error(y_val, y_pred))
            fold_metrics["rmse"] = float(np.sqrt(mean_squared_error(y_val, y_pred)))

        metrics_list.append(fold_metrics)

    # Aggregate
    agg: Dict[str, Any] = {"n_folds": n_folds}
    keys = metrics_list[0].keys()
    for k in keys:
        vals = [m[k] for m in metrics_list]
        agg[k] = float(np.mean(vals))
        agg[f"{k}_std"] = float(np.std(vals))

    return agg


# ---------------------------------------------------------------------------
# Stacking ensemble
# ---------------------------------------------------------------------------


def build_stacking_classifier() -> Any:
    """Build a stacking ensemble for classification.

    Base estimators: GradientBoosting, RandomForest, LogisticRegression
    Meta estimator: LogisticRegression
    """
    from sklearn.ensemble import StackingClassifier

    estimators = [
        ("gb", GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)),
        ("rf", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
        ("lr", LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")),
    ]
    meta = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    return StackingClassifier(
        estimators=estimators,
        final_estimator=meta,
        cv=5,
        n_jobs=-1,
    )


def build_stacking_regressor() -> Any:
    """Build a stacking ensemble for regression.

    Base estimators: GradientBoosting, RandomForest
    Meta estimator: LinearRegression
    """
    from sklearn.ensemble import StackingRegressor
    from sklearn.linear_model import LinearRegression

    estimators = [
        ("gb", GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)),
        ("rf", RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)),
    ]
    meta = LinearRegression()
    return StackingRegressor(
        estimators=estimators,
        final_estimator=meta,
        cv=5,
        n_jobs=-1,
    )


# ---------------------------------------------------------------------------
# Optuna HPO
# ---------------------------------------------------------------------------


def _get_classifier_param_space(trial: optuna_lib.Trial, name: str) -> Dict[str, Any]:  # type: ignore[type-arg]
    """Sample hyperparameters for a classifier."""
    if name == "LogisticRegression":
        return {
            "C": trial.suggest_float("C", 1e-4, 1e2, log=True),
            "solver": trial.suggest_categorical("solver", ["lbfgs", "saga"]),
            "max_iter": trial.suggest_int("max_iter", 500, 3000, step=500),
        }
    elif name == "RandomForest":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 30),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }
    elif name == "GradientBoosting":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        }
    elif name == "MLP (128->64)":
        return {
            "hidden_layer_size_1": trial.suggest_int("hidden_layer_size_1", 32, 256, step=32),
            "hidden_layer_size_2": trial.suggest_int("hidden_layer_size_2", 16, 128, step=16),
            "alpha": trial.suggest_float("alpha", 1e-5, 1e-2, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
            "batch_size": trial.suggest_categorical("batch_size", [128, 256, 512]),
        }
    elif name == "XGBoost":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.3, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        }
    return {}


def _get_regressor_param_space(trial: optuna_lib.Trial, name: str) -> Dict[str, Any]:  # type: ignore[type-arg]
    """Sample hyperparameters for a regressor."""
    if name == "RandomForest":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 30),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        }
    elif name == "GradientBoosting":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        }
    elif name == "MLP (128->64)":
        return {
            "hidden_layer_size_1": trial.suggest_int("hidden_layer_size_1", 32, 256, step=32),
            "hidden_layer_size_2": trial.suggest_int("hidden_layer_size_2", 16, 128, step=16),
            "alpha": trial.suggest_float("alpha", 1e-5, 1e-2, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
            "batch_size": trial.suggest_categorical("batch_size", [128, 256, 512]),
        }
    elif name == "XGBoost":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.3, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        }
    return {}


def _build_hpo_model(name: str, params: Dict[str, Any], task_type: str) -> Any:
    """Build a model with the given hyperparameters."""
    if task_type == "classification":
        if name == "LogisticRegression":
            return LogisticRegression(
                C=params.get("C", 1.0),
                solver=params.get("solver", "lbfgs"),
                max_iter=params.get("max_iter", 1000),
                random_state=42,
                class_weight="balanced",
            )
        elif name == "RandomForest":
            return RandomForestClassifier(
                n_estimators=params.get("n_estimators", 100),
                max_depth=params.get("max_depth", 10),
                min_samples_split=params.get("min_samples_split", 2),
                min_samples_leaf=params.get("min_samples_leaf", 1),
                random_state=42,
                n_jobs=-1,
            )
        elif name == "GradientBoosting":
            return GradientBoostingClassifier(
                n_estimators=params.get("n_estimators", 100),
                max_depth=params.get("max_depth", 5),
                learning_rate=params.get("learning_rate", 0.1),
                subsample=params.get("subsample", 1.0),
                min_samples_split=params.get("min_samples_split", 2),
                random_state=42,
            )
        elif name == "MLP (128->64)":
            hs1 = params.get("hidden_layer_size_1", 128)
            hs2 = params.get("hidden_layer_size_2", 64)
            return MLPClassifier(
                hidden_layer_sizes=(hs1, hs2),
                activation="relu",
                solver="adam",
                alpha=params.get("alpha", 1e-4),
                batch_size=params.get("batch_size", 256),
                learning_rate_init=params.get("learning_rate_init", 1e-3),
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
            )
        elif name == "XGBoost":
            if xgb is None:
                raise ImportError("xgboost not available")
            return xgb.XGBClassifier(
                n_estimators=params.get("n_estimators", 200),
                max_depth=params.get("max_depth", 6),
                learning_rate=params.get("learning_rate", 0.1),
                subsample=params.get("subsample", 0.8),
                colsample_bytree=params.get("colsample_bytree", 0.8),
                min_child_weight=params.get("min_child_weight", 1),
                gamma=params.get("gamma", 0.0),
                random_state=42,
                n_jobs=-1,
                verbosity=0,
                use_label_encoder=False,
            )
    else:
        if name == "RandomForest":
            return RandomForestRegressor(
                n_estimators=params.get("n_estimators", 100),
                max_depth=params.get("max_depth", 10),
                min_samples_split=params.get("min_samples_split", 2),
                min_samples_leaf=params.get("min_samples_leaf", 1),
                random_state=42,
                n_jobs=-1,
            )
        elif name == "GradientBoosting":
            return GradientBoostingRegressor(
                n_estimators=params.get("n_estimators", 100),
                max_depth=params.get("max_depth", 5),
                learning_rate=params.get("learning_rate", 0.1),
                subsample=params.get("subsample", 1.0),
                min_samples_split=params.get("min_samples_split", 2),
                random_state=42,
            )
        elif name == "MLP (128->64)":
            hs1 = params.get("hidden_layer_size_1", 128)
            hs2 = params.get("hidden_layer_size_2", 64)
            return MLPRegressor(
                hidden_layer_sizes=(hs1, hs2),
                activation="relu",
                solver="adam",
                alpha=params.get("alpha", 1e-4),
                batch_size=params.get("batch_size", 256),
                learning_rate_init=params.get("learning_rate_init", 1e-3),
                max_iter=500,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
            )
        elif name == "XGBoost":
            if xgb is None:
                raise ImportError("xgboost not available")
            return xgb.XGBRegressor(
                n_estimators=params.get("n_estimators", 200),
                max_depth=params.get("max_depth", 6),
                learning_rate=params.get("learning_rate", 0.1),
                subsample=params.get("subsample", 0.8),
                colsample_bytree=params.get("colsample_bytree", 0.8),
                min_child_weight=params.get("min_child_weight", 1),
                gamma=params.get("gamma", 0.0),
                random_state=42,
                n_jobs=-1,
                verbosity=0,
            )
    raise ValueError(f"Unknown model: {name}")


def run_hpo(
    X: np.ndarray,
    y: np.ndarray,
    model_names: List[str],
    task_type: str,
    n_trials: int = 50,
    cv_folds: int = 3,
) -> Dict[str, Dict[str, Any]]:
    """Run Optuna HPO for each model type.

    Returns dict mapping model_name -> {"best_params": dict, "best_value": float,
                                         "study": optuna.Study}
    """
    if optuna is None:
        logger.error("optuna is not installed. Cannot run HPO.")
        return {}

    results: Dict[str, Dict[str, Any]] = {}

    for name in model_names:
        logger.info(f"HPO: Optimizing {name} ({task_type}) — {n_trials} trials, {cv_folds}-fold CV")

        def objective(trial: Any, _name: str = name, _task: str = task_type) -> float:
            if _task == "classification":
                params = _get_classifier_param_space(trial, _name)
            else:
                params = _get_regressor_param_space(trial, _name)

            model = _build_hpo_model(_name, params, _task)
            scaler = StandardScaler()
            X_s = scaler.fit_transform(X)

            from sklearn.model_selection import cross_val_score
            if _task == "classification":
                cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
                scores = cross_val_score(model, X_s, y, cv=cv, scoring="f1_macro", n_jobs=1)
            else:
                cv = KFold(n_splits=cv_folds, shuffle=True, random_state=42)
                scores = cross_val_score(model, X_s, y, cv=cv, scoring="r2", n_jobs=1)
            return float(np.mean(scores))

        sampler = optuna.samplers.TPESampler(seed=42)
        study = optuna.create_study(direction="maximize", sampler=sampler)
        study.optimize(objective, n_trials=n_trials, n_jobs=1)

        logger.info(
            f"HPO {name}: best value = {study.best_value:.4f}, "
            f"best params = {study.best_params}"
        )

        results[name] = {
            "best_params": study.best_params,
            "best_value": study.best_value,
            "study": study,
        }

    return results


# ---------------------------------------------------------------------------
# Feature importance plotting
# ---------------------------------------------------------------------------


def plot_feature_importance(
    model: Any,
    feature_names: List[str],
    target_name: str,
    model_name: str,
    top_k: int = 20,
    save_dir: Path = MODEL_DIR,
) -> None:
    """Plot feature importance (tree-based models) or coefficient magnitude.

    Saves plot to {save_dir}/{target_name}_{model_name}_feature_importance.png
    """
    importance: Optional[np.ndarray] = None

    if hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    elif hasattr(model, "coef_"):
        coef = model.coef_
        if coef.ndim > 1:
            importance = np.linalg.norm(coef, ord=2, axis=0)
        else:
            importance = np.abs(coef)
    elif hasattr(model, "estimators_"):
        # Stacking ensemble — get feature importance from first base estimator
        try:
            imp = model.estimators_[0].feature_importances_
            importance = imp
        except (AttributeError, IndexError, TypeError):
            pass

    if importance is None:
        logger.warning(f"Cannot compute feature importance for {model_name}")
        return

    importance = np.asarray(importance).flatten()
    if len(importance) != len(feature_names):
        logger.warning(
            f"Feature importance shape mismatch: {len(importance)} vs "
            f"{len(feature_names)} names. Truncating."
        )
        min_len = min(len(importance), len(feature_names))
        importance = importance[:min_len]
        feature_names = feature_names[:min_len]

    # Sort by importance
    idx = np.argsort(importance)[::-1][:top_k]
    top_features = [feature_names[i] for i in idx]
    top_importance = importance[idx]

    fig, ax = plt.subplots(figsize=(10, max(6, top_k * 0.35)))
    ax.barh(range(len(top_features)), top_importance[::-1])
    ax.set_yticks(range(len(top_features)))
    ax.set_yticklabels(top_features[::-1])
    ax.set_xlabel("Importance")
    ax.set_title(f"Feature Importance — {model_name} on {target_name}")
    plt.tight_layout()

    safe_model = model_name.replace(" ", "_").replace("(", "").replace(")", "").replace("->", "_to_")
    safe_target = target_name.replace(" ", "_")
    path = save_dir / f"{safe_target}_{safe_model}_feature_importance.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved feature importance plot: {path}")


# ---------------------------------------------------------------------------
# Model persistence
# ---------------------------------------------------------------------------


def save_model(model: Any, target_name: str, model_name: str, save_dir: Path = MODEL_DIR) -> Path:
    """Save model via joblib and return path."""
    if joblib is None:
        logger.warning("joblib not available, skipping model save")
        return save_dir  # type: ignore[return-value]
    safe_target = target_name.replace(" ", "_")
    safe_model = model_name.replace(" ", "_").replace("(", "").replace(")", "").replace("->", "_to_")
    path = save_dir / f"{safe_target}_{safe_model}.joblib"
    joblib.dump(model, path)
    logger.info(f"Saved model: {path}")
    return path


def save_metrics_table(
    all_metrics: List[Dict[str, Any]],
    save_dir: Path = MODEL_DIR,
) -> None:
    """Save comprehensive metrics table as JSON and CSV."""
    table_path = save_dir / "metrics_table.json"
    with open(table_path, "w") as f:
        json.dump(all_metrics, f, indent=2, default=str)
    logger.info(f"Saved metrics table: {table_path}")

    # Also write a CSV
    flat_rows = []
    for entry in all_metrics:
        row = {k: v for k, v in entry.items() if not k.endswith("_std")}
        flat_rows.append(row)
    df_metrics = pd.DataFrame(flat_rows)
    csv_path = save_dir / "metrics_table.csv"
    df_metrics.to_csv(csv_path, index=False)
    logger.info(f"Saved metrics CSV: {csv_path}")


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
        "  \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"
    )
    print(
        "  \u2502 Exp 10a: Multi-class Rank Classification                                \u2502"
    )
    print(
        "  \u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524"
    )
    print(f"  \u2502 Best model:       {best_rank_model:<48s} \u2502")
    print(f"  \u2502 Accuracy:         {fmt(best_r['accuracy']):<48s} \u2502")
    print(f"  \u2502 F1 (macro):       {fmt(best_r['f1_macro']):<48s} \u2502")
    print(f"  \u2502 F1 (weighted):    {fmt(best_r['f1_weighted']):<48s} \u2502")
    per_class = best_r["per_class_f1"]
    for c in sorted(per_class.keys()):
        print(f"  \u2502 F1 (rank {c}):       {fmt(per_class[c]):<48s} \u2502")
    print(f"  \u2502 Exp 9 baseline:   F1=0.839 (binary, 1000 records)              \u2502")
    print(
        "  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518"
    )
    print()

    # Dimension regression summary
    best_d = max(dim_results, key=lambda r: r["r2"])
    print(
        "  \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"
    )
    print(
        "  \u2502 Exp 10b: Dimension Regression                                           \u2502"
    )
    print(
        "  \u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524"
    )
    print(f"  \u2502 Best model:       {best_dim_model:<48s} \u2502")
    print(f"  \u2502 MAE:              {fmt(best_d['mae']):<48s} \u2502")
    print(f"  \u2502 R\u00b2:               {fmt(best_d['r2']):<48s} \u2502")
    print(f"  \u2502 Exp 9 baseline:   R\u00b2=0.976 (1000 records)                       \u2502")
    print(
        "  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518"
    )
    print()

    # Conductor regression summary
    best_c = max(cond_results, key=lambda r: r["r2_log"])
    print(
        "  \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"
    )
    print(
        "  \u2502 Exp 10c: Analytic Conductor Regression (log-transformed)                 \u2502"
    )
    print(
        "  \u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524"
    )
    print(f"  \u2502 Best model:       {best_cond_model:<48s} \u2502")
    print(f"  \u2502 MAE (log):        {fmt(best_c['mae_log']):<48s} \u2502")
    print(f"  \u2502 R\u00b2 (log):         {fmt(best_c['r2_log']):<48s} \u2502")
    print(f"  \u2502 R\u00b2 (original):    {fmt(best_c['r2_orig']):<48s} \u2502")
    print(f"  \u2502 Exp 9 baseline:   R\u00b2(log)=0.142 (1000 records)                  \u2502")
    print(
        "  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518"
    )
    print()

    # CM classification summary
    best_cm = max(cm_results, key=lambda r: r["f1"])
    print(
        "  \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510"
    )
    print(
        "  \u2502 Exp 10d: CM Form Classification (NEW \u2014 not tested in Exp 9)             \u2502"
    )
    print(
        "  \u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2524"
    )
    print(f"  \u2502 Best model:       {best_cm_model:<48s} \u2502")
    print(f"  \u2502 Accuracy:         {fmt(best_cm['accuracy']):<48s} \u2502")
    print(f"  \u2502 Precision:        {fmt(best_cm['precision']):<48s} \u2502")
    print(f"  \u2502 Recall:           {fmt(best_cm['recall']):<48s} \u2502")
    print(f"  \u2502 F1:               {fmt(best_cm['f1']):<48s} \u2502")
    print(
        "  \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518"
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
        f"  {'Dimension Regression':<30s} | {'R\u00b2':>8s} | {fmt(e9_dim_r2):>10s} | {fmt(e10_dim_r2):>10s} | {sign}{fmt(delta):>10s}"
    )

    # Conductor
    e9_cond_r2 = 0.142
    e10_cond_r2 = best_c["r2_log"]
    delta = e10_cond_r2 - e9_cond_r2
    sign = "+" if delta >= 0 else ""
    print(
        f"  {'Conductor Reg (log)':<30s} | {'R\u00b2':>8s} | {fmt(e9_cond_r2):>10s} | {fmt(e10_cond_r2):>10s} | {sign}{fmt(delta):>10s}"
    )

    print()
    print("  Key differences:")
    print("    - Exp 10 uses 53,779 records (53x more than Exp 9's 1,000)")
    print(
        "    - Exp 10 has 3-class rank classification (rank 0/1/2); Exp 9 was binary (0/1)"
    )
    print("    - Exp 10 adds CM form classification (Exp 9 did not test this)")
    print("    - Exp 10 uses larger MLP (128->64) vs Exp 9 (64->32)")
    print()
    print_separator()
    print()


# ---------------------------------------------------------------------------
# Extended pipeline helpers
# ---------------------------------------------------------------------------


def _get_model_names_for_target(target: str, task_type: str) -> List[str]:
    """Return the list of applicable model names for a target."""
    base_names = ["LogisticRegression", "RandomForest", "GradientBoosting", "MLP (128->64)"] if task_type == "classification" else ["RandomForest", "GradientBoosting", "MLP (128->64)"]
    if task_type == "classification":
        # LR is replaced by XGBoost conceptually, but we keep both
        pass
    return base_names


def _compute_metrics_for_entry(
    y_test: np.ndarray,
    y_pred: np.ndarray,
    task_type: str,
) -> Dict[str, float]:
    """Compute a standard set of metrics for a prediction task."""
    m: Dict[str, float] = {}
    if task_type == "classification":
        m["accuracy"] = float(accuracy_score(y_test, y_pred))
        m["f1_macro"] = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        m["f1_weighted"] = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        m["precision_macro"] = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        m["recall_macro"] = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    else:
        m["r2"] = float(r2_score(y_test, y_pred))
        m["mae"] = float(mean_absolute_error(y_test, y_pred))
        m["mse"] = float(mean_squared_error(y_test, y_pred))
        m["rmse"] = float(np.sqrt(m["mse"]))
    return m


def _print_metrics_comparison_table(all_metrics: List[Dict[str, Any]]) -> None:
    """Print a comprehensive metrics table across all (model, target) combinations."""
    print_header("Comprehensive Metrics Table")
    print(f"  {'Model':<32s} | {'Target':<24s} | {'Metric':>10s} | {'Value':>10s}")
    print(f"  {'-' * 32} | {'-' * 24} | {'-' * 10} | {'-' * 10}")

    for entry in all_metrics:
        model_name = entry.get("model_name", "?")
        target_name = entry.get("target_name", "?")
        metrics = entry.get("metrics", {})

        primary_key, primary_val = _get_primary_metric(metrics, entry.get("task_type", "classification"))
        print(
            f"  {model_name:<32s} | {target_name:<24s} | {primary_key:>10s} | {fmt(primary_val):>10s}"
        )

    print()

    # Also print per-target best
    print("  Best model per target:")
    targets = set(e["target_name"] for e in all_metrics)
    for target in sorted(targets):
        target_entries = [e for e in all_metrics if e["target_name"] == target]
        best = _find_best_entry(target_entries)
        if best:
            pk, pv = _get_primary_metric(best.get("metrics", {}), best.get("task_type", "classification"))
            print(f"    {target:<24s} → {best['model_name']:<28s} ({pk}={fmt(pv)})")
    print()


def _get_primary_metric(metrics: Dict[str, float], task_type: str) -> Tuple[str, float]:
    if task_type == "classification":
        for key in ("f1_macro", "accuracy", "f1_weighted"):
            if key in metrics:
                return key, metrics[key]
    else:
        for key in ("r2", "mae", "rmse"):
            if key in metrics:
                return key, metrics[key]
    return ("?", 0.0)


def _find_best_entry(entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not entries:
        return None

    def _score(e):
        m = e.get("metrics", {})
        t = e.get("task_type", "classification")
        if t == "classification":
            return m.get("f1_macro", 0.0)
        else:
            return m.get("r2", -999.0)

    return max(entries, key=_score)


# ---------------------------------------------------------------------------
# Extended pipeline runner
# ---------------------------------------------------------------------------


def run_extended_pipeline(
    df: pd.DataFrame,
    feature_cols: List[str],
    enable_hpo: bool = False,
    enable_cv: bool = False,
    enable_stacking: bool = False,
    enable_poly: bool = False,
    enable_xgboost: bool = False,
    hpo_trials: int = 50,
    cv_folds: int = 5,
) -> List[Dict[str, Any]]:
    """Run the extended ML pipeline (HPO, CV, stacking, XGBoost).

    Returns a flat list of metrics dicts for the comprehensive metrics table.
    """
    all_metrics: List[Dict[str, Any]] = []

    # Define targets
    targets = [
        ("analytic_rank", "classification", False),
        ("dim", "regression", False),
        ("analytic_conductor", "regression", True),  # log-transform
        ("is_cm", "classification", False),
    ]

    for target_col, task_type, log_transform in targets:
        print_header(f"Extended Pipeline — {target_col} ({task_type})")

        X_raw = df[feature_cols].values
        y_raw = df[target_col].values

        if log_transform:
            y = np.log1p(y_raw.astype(float))
        else:
            y = y_raw if task_type == "classification" else y_raw.astype(float)

        # -------------------
        # Polynomial features
        # -------------------
        X = X_raw
        if enable_poly and len(feature_cols) >= 10:
            # Apply polynomial features to top 10 Hecke traces
            trace_10_idx = list(range(min(10, X.shape[1])))
            X = build_polynomial_features(X, trace_indices=trace_10_idx, degree=2)

        n_features_total = X.shape[1]

        # Split
        stratify = y if task_type == "classification" else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=stratify,
        )

        # Scale
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        # Gather model names
        model_names: List[Tuple[str, Any]] = []
        if task_type == "classification":
            model_names = build_classifiers()
            if enable_xgboost and xgb is not None:
                model_names += build_xgb_classifiers()
        else:
            model_names = build_regressors()
            if enable_xgboost and xgb is not None:
                model_names += build_xgb_regressors()

        # -------------------
        # HPO
        # -------------------
        hpo_results: Dict[str, Any] = {}
        if enable_hpo and optuna is not None:
            hpo_model_names = [n for n, _ in model_names]
            if hpo_model_names:
                hpo_results = run_hpo(
                    X_train, y_train, hpo_model_names, task_type,
                    n_trials=hpo_trials, cv_folds=min(cv_folds, 3),
                )

        # -------------------
        # Train & evaluate each model
        # -------------------
        for name, base_model in model_names:
            logger.info(f"Extended: training {name} on {target_col}...")
            t0 = time.time()

            if enable_hpo and name in hpo_results:
                # Use HPO-optimized params
                best_params = hpo_results[name]["best_params"]
                model = _build_hpo_model(name, best_params, task_type)
            else:
                model = base_model

            model.fit(X_train_s, y_train)
            train_time = time.time() - t0

            y_pred = model.predict(X_test_s)

            # Compute metrics
            if log_transform:
                y_test_actual = np.expm1(y_test)
                y_pred_actual = np.expm1(y_pred)
                test_metrics = _compute_metrics_for_entry(y_test, y_pred, "regression")
            else:
                test_metrics = _compute_metrics_for_entry(y_test, y_pred, task_type)

            entry: Dict[str, Any] = {
                "model_name": name,
                "target_name": target_col,
                "task_type": task_type,
                "log_transform": log_transform,
                "n_features": n_features_total,
                "train_time_s": round(train_time, 2),
                "metrics": test_metrics,
            }

            if enable_hpo and name in hpo_results:
                entry["hpo_best_value"] = round(hpo_results[name]["best_value"], 4)
                entry["hpo_best_params"] = hpo_results[name]["best_params"]

            all_metrics.append(entry)

            # Log result
            pk, pv = _get_primary_metric(test_metrics, task_type)
            logger.info(f"  {name} on {target_col}: {pk}={fmt(pv)} [{train_time:.1f}s]")

            # -------------------
            # CV
            # -------------------
            if enable_cv:
                cv_metrics = cross_validate_model(
                    model, X_train, y_train, task_type, n_folds=cv_folds,
                )
                cv_entry: Dict[str, Any] = {
                    "model_name": f"{name}+CV({cv_folds})",
                    "target_name": target_col,
                    "task_type": task_type,
                    "log_transform": log_transform,
                    "n_features": n_features_total,
                    "cv_folds": cv_folds,
                    "metrics": cv_metrics,
                }
                all_metrics.append(cv_entry)
                logger.info(f"  CV {name}: {pk}={fmt(cv_metrics.get(pk, 0.0))} \u00b1 {fmt(cv_metrics.get(f'{pk}_std', 0.0))}")

            # -------------------
            # Feature importance plot
            # -------------------
            plot_feature_importance(model, feature_cols, target_col, name)

            # -------------------
            # Model persistence
            # -------------------
            save_model(model, target_col, name)

        # -------------------
        # Stacking ensemble
        # -------------------
        if enable_stacking:
            logger.info(f"Extended: training stacking ensemble on {target_col}...")

            if task_type == "classification":
                stack_model = build_stacking_classifier()
            else:
                stack_model = build_stacking_regressor()

            t0 = time.time()
            stack_model.fit(X_train_s, y_train)
            train_time = time.time() - t0

            y_pred_stack = stack_model.predict(X_test_s)

            if log_transform:
                y_test_actual = np.expm1(y_test)
                y_pred_actual = np.expm1(y_pred_stack)
                stack_metrics = _compute_metrics_for_entry(y_test, y_pred_stack, "regression")
            else:
                stack_metrics = _compute_metrics_for_entry(y_test, y_pred_stack, task_type)

            stack_entry: Dict[str, Any] = {
                "model_name": "StackingEnsemble",
                "target_name": target_col,
                "task_type": task_type,
                "log_transform": log_transform,
                "n_features": n_features_total,
                "train_time_s": round(train_time, 2),
                "metrics": stack_metrics,
            }
            all_metrics.append(stack_entry)

            pk, pv = _get_primary_metric(stack_metrics, task_type)
            logger.info(f"  Stacking on {target_col}: {pk}={fmt(pv)} [{train_time:.1f}s]")

            plot_feature_importance(stack_model, feature_cols, target_col, "StackingEnsemble")
            save_model(stack_model, target_col, "StackingEnsemble")

        print()

    return all_metrics


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

    # Extended pipeline flags
    parser.add_argument(
        "--hpo",
        action="store_true",
        help="Run Optuna hyperparameter optimization (50+ trials, TPESampler)",
    )
    parser.add_argument(
        "--hpo-trials",
        type=int,
        default=50,
        help="Number of HPO trials per model (default: 50)",
    )
    parser.add_argument(
        "--cv",
        action="store_true",
        help="Run k-fold cross-validation (StratifiedKFold for classification, KFold for regression)",
    )
    parser.add_argument(
        "--cv-folds",
        type=int,
        default=5,
        help="Number of CV folds (default: 5)",
    )
    parser.add_argument(
        "--features",
        type=str,
        default="traces",
        choices=["traces", "scalars", "all"],
        help="Feature subset: 'traces' (100 Hecke traces), 'scalars' (level, dim, ...), 'all' (both)",
    )
    parser.add_argument(
        "--no-xgboost",
        action="store_true",
        help="Skip XGBoost models (included by default)",
    )
    parser.add_argument(
        "--no-stacking",
        action="store_true",
        help="Skip stacking ensemble (included by default)",
    )
    parser.add_argument(
        "--polynomial",
        action="store_true",
        help="Add polynomial & interaction features (degree=2 on top 10 traces)",
    )
    parser.add_argument(
        "--no-extended",
        action="store_true",
        help="Run only the original 4-model pipeline (no extended features)",
    )
    args = parser.parse_args()

    t_start = time.time()

    print()
    print("=" * 78)
    print(
        "  Experiment 10: LMFDB SQL Mirror \u2014 ML Training Pipeline (53,779 records)".center(
            78
        )
    )
    print("=" * 78)
    print()

    # Load data
    df = load_data(args.data)

    # Dataset statistics
    print_dataset_statistics(df)

    # Select features
    feature_cols = select_features(df, args.features)
    logger.info(f"Feature columns: {len(feature_cols)} ({args.features})")

    # ------------------------------------------------------------------
    # Original pipeline (always runs unless --no-extended)
    # ------------------------------------------------------------------
    if not args.no_extended:
        trace_100 = get_trace_columns(100)

        # Exp 10a-d: use trace columns regardless of --features for backward compat
        rank_results, best_rank_model = experiment_rank_classification(df, trace_100)
        dim_results, best_dim_model = experiment_dimension_regression(df, trace_100)
        cond_results, best_cond_model = experiment_conductor_regression(df, trace_100)
        cm_results, best_cm_model = experiment_cm_classification(df, trace_100)

        # Exp 10e: Feature Ablation
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
    else:
        rank_results = []
        dim_results = []
        cond_results = []
        cm_results = []
        best_rank_model = "?"
        best_dim_model = "?"
        best_cond_model = "?"
        best_cm_model = "?"

    # ------------------------------------------------------------------
    # Extended pipeline
    # ------------------------------------------------------------------
    extended_metrics: List[Dict[str, Any]] = []
    if not args.no_extended:
        run_extended = (
            args.hpo
            or args.cv
            or args.features != "traces"
            or args.polynomial
            or not args.no_xgboost
            or not args.no_stacking
        )
        if run_extended:
            extended_metrics = run_extended_pipeline(
                df,
                feature_cols,
                enable_hpo=args.hpo,
                enable_cv=args.cv,
                enable_stacking=not args.no_stacking,
                enable_poly=args.polynomial,
                enable_xgboost=not args.no_xgboost,
                hpo_trials=args.hpo_trials,
                cv_folds=args.cv_folds,
            )

    # ------------------------------------------------------------------
    # Save comprehensive metrics table
    # ------------------------------------------------------------------
    if extended_metrics:
        save_metrics_table(extended_metrics, MODEL_DIR)
        _print_metrics_comparison_table(extended_metrics)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    if not args.no_extended:
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
