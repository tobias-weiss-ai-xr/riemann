"""
Train sklearn models for ensemble (ExtraTrees for z1, XGBoost for rank/cm).
Fast training focused on best models from Exp 10/11.

Usage:
    python scripts/train_ensemble_sklearn.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from extract_sklearn_predictions import (
    get_scalar_columns,
    get_trace_columns,
    stratified_split_by_rank,
)

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"
L2_CSV_PATH = DATA_DIR / "lmfdb" / "lmfdb_sql_weight2_ml.csv"


def load_and_prepare_data(df: pd.DataFrame) -> tuple:
    """Load and normalize features."""
    trace_cols = get_trace_columns(100)
    scalar_cols = get_scalar_columns()
    feature_cols = trace_cols + scalar_cols

    X = df[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, feature_cols, scaler


def train_z1_model(X_train, y_train, X_test, y_test, scaler) -> Dict[str, Any]:
    """Train ExtraTreesRegressor for z1 regression."""
    logger.info("Training ExtraTreesRegressor for z1 regression")

    model = ExtraTreesRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    logger.info(f"  Test MSE: {mse:.4f}")
    logger.info(f"  Test MAE: {mae:.4f}")
    logger.info(f"  Test R²: {r2:.4f}")

    return {
        "model": model,
        "scaler": scaler,
        "test_metrics": {"mse": mse, "mae": mae, "r2": r2},
    }


def train_rank_model(X_train, y_train, X_test, y_test, scaler) -> Dict[str, Any]:
    """Train RandomForestClassifier for rank classification."""
    logger.info("Training RandomForestClassifier for rank classification")
    logger.info(f"  Class distribution: {np.bincount(y_train)}")

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1_mac = f1_score(y_test, y_pred, average="macro")
    f1_weighted = f1_score(y_test, y_pred, average="weighted")

    logger.info(f"  Test Accuracy: {acc:.4f}")
    logger.info(f"  Test F1 (macro): {f1_mac:.4f}")
    logger.info(f"  Test F1 (weighted): {f1_weighted:.4f}")

    return {
        "model": model,
        "scaler": scaler,
        "test_metrics": {
            "accuracy": acc,
            "f1_macro": f1_mac,
            "f1_weighted": f1_weighted,
        },
    }


def train_cm_model(X_train, y_train, X_test, y_test, scaler) -> Dict[str, Any]:
    """Train RandomForestClassifier for CM classification."""
    logger.info("Training RandomForestClassifier for CM classification")
    logger.info(f"  Class distribution: {np.bincount(y_train)}")

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    logger.info(f"  Test Accuracy: {acc:.4f}")
    logger.info(f"  Test F1: {f1:.4f}")

    return {
        "model": model,
        "scaler": scaler,
        "test_metrics": {"accuracy": acc, "f1": f1},
    }


def main():
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    )

    logger.info("Ensemble sklearn model training")
    logger.info("="*60)

    # Load data
    logger.info(f"Loading data from {L2_CSV_PATH}")
    df = pd.read_csv(L2_CSV_PATH)
    logger.info(f"  Loaded {len(df)} samples")

    # Get target columns (z1 is NOT in CSV - GNN-only target)
    y_rank = df['analytic_rank'].values
    y_cm = df['is_cm'].values

    # Reproduce GNN's stratified split (80/10/10, seed=42)
    logger.info("\nReproducing GNN's 80/10/10 stratified split (seed=42)")
    train_idx, val_idx, test_idx = stratified_split_by_rank(y_rank)
    logger.info(f"  Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

    # Prepare features
    logger.info("\nPreparing features...")
    X_all, _, scaler = load_and_prepare_data(df)
    X_train = X_all[train_idx]
    X_test = X_all[test_idx]

    # Get targets for split
    y_rank_train, y_rank_test = y_rank[train_idx], y_rank[test_idx]
    y_cm_train, y_cm_test = y_cm[train_idx], y_cm[test_idx]

    # Train models
    results = {}

    # NOTE: z1 is GNN-only (not in sklearn features)
    # Skip z1 model training - ensemble will use GNN predictions for z1

    logger.info("\n" + "="*60)
    model_data_rank = train_rank_model(
        X_train, y_rank_train, X_test, y_rank_test, scaler
    )
    results["rank"] = model_data_rank

    logger.info("\n" + "="*60)
    model_data_cm = train_cm_model(
        X_train, y_cm_train, X_test, y_cm_test, scaler
    )
    results["cm"] = model_data_cm

    logger.info("\n" + "="*60)
    logger.info("Note: z1 target excluded (GNN-only in our ensemble)")

    # Save models
    logger.info("\nSaving models...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for target, data in results.items():
        model_path = MODEL_DIR / f"sklearn_best_{target}.pkl"
        joblib.dump(data, model_path)
        logger.info(f"  Saved: {model_path}")

    logger.info("\n" + "="*60)
    logger.info("All models trained and saved successfully")


if __name__ == "__main__":
    main()