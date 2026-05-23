"""
Load LMFDB sklearn models and export predictions aligned to GNN test split.

The GNN uses an 80/10/10 stratified split (seed=42) by analytic rank.
This script replicates that split and extracts sklearn predictions for the same test set.

Usage:
    python scripts/extract_sklearn_predictions.py --target z1
    python scripts/extract_sklearn_predictions.py --target rank
    python scripts/extract_sklearn_predictions.py --target cm
    python scripts/extract_sklearn_predictions.py --all
"""

from __future__ import annotations

import argparse
import joblib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"
L2_CSV_PATH = DATA_DIR / "lmfdb" / "lmfdb_sql_weight2_ml.csv"
GNN_TEST_INDICES_PATH = DATA_DIR / "models" / "gnn_test_indices.npy"


def stratified_split_by_rank(
    ranks: np.ndarray,
    train_frac: float = 0.8,
    val_frac: float = 0.1,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Reproduce GNN's 80/10/10 stratified split by analytic rank.

    Matches the exact split used in build_lmfdb_gnn_dataset.py:stratified_split()
    """
    rng = np.random.RandomState(seed)
    n = len(ranks)
    train_idx: list[int] = []
    val_idx: list[int] = []
    test_idx: list[int] = []

    for rank_val in sorted(np.unique(ranks)):
        mask = ranks == rank_val
        class_indices = np.where(mask)[0]
        rng.shuffle(class_indices)

        n_train = int(len(class_indices) * train_frac)
        n_val = int(len(class_indices) * val_frac)

        train_idx.extend(class_indices[:n_train].tolist())
        val_idx.extend(class_indices[n_train : n_train + n_val].tolist())
        test_idx.extend(class_indices[n_train + n_val :].tolist())

    return np.array(train_idx), np.array(val_idx), np.array(test_idx)


def load_lmfdb_ml_data(path: Path) -> pd.DataFrame:
    """Load LMFDB ML dataset."""
    logger.info(f"Loading LMFDB ML data from {path}")
    df = pd.read_csv(path)
    logger.info(f"  Loaded {len(df)} samples with {len(df.columns)} columns")
    return df


def get_trace_columns(n: int = 100) -> list[str]:
    """Return column names for first n Hecke traces."""
    return [f"trace_{i}" for i in range(1, n + 1)]


def get_scalar_columns() -> list[str]:
    return ["level", "dim", "char_degree", "is_cm", "is_self_dual", "Nk2"]


def prepare_features(df: pd.DataFrame) -> np.ndarray:
    """Normalize features (StandardScaler) like in Exp 10."""
    trace_cols = get_trace_columns(100)
    scalar_cols = get_scalar_columns()
    feature_cols = trace_cols + scalar_cols

    X = df[feature_cols].values
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled


def load_model(target: str) -> tuple:
    """Load best sklearn model for target and FeatureScaler from Exp 11."""
    model_path = MODEL_DIR / f"sklearn_best_{target}.pkl"

    if not model_path.exists():
        logger.error(f"Model not found: {model_path}")
        raise FileNotFoundError(model_path)

    logger.info(f"Loading model from {model_path}")
    model_data = joblib.load(model_path)

    # Exp 11 saves format: {'model': ..., 'scaler': ..., 'test_metrics': ...}
    if isinstance(model_data, dict):
        model = model_data['model']
        scaler = model_data.get('scaler')
        logger.info(f"  Model type: {type(model).__name__}")
        logger.info(f"  Test metrics: {model_data.get('test_metrics', {})}")
    else:
        model = model_data
        scaler = None

    return model, scaler


def extract_predictions(
    target: str,
    data_path: Path = None,
    output_dir: Path = None,
) -> dict:
    """Extract sklearn predictions aligned to GNN test split."""
    # Skip z1 - GNN-only target (not in sklearn features)
    if target == "z1":
        logger.info(f"Skipping {target}: GNN-only target (no sklearn model)")
        return {
            "skipped": True,
            "reason": "GNN-only target (not in sklearn features)",
        }

    data_path = data_path or L2_CSV_PATH
    output_dir = output_dir or MODEL_DIR

    # Load data
    df = load_lmfdb_ml_data(data_path)

    # Extract ranks for stratified split
    ranks = df['analytic_rank'].values

    # Reproduce GNN's stratified split
    logger.info("Reproducing GNN's 80/10/10 stratified split (seed=42)")
    train_idx, val_idx, test_idx = stratified_split_by_rank(ranks)
    logger.info(f"  Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

    # Save test indices for verification
    np.save(GNN_TEST_INDICES_PATH, test_idx)
    logger.info(f"  Saved GNN test indices: {GNN_TEST_INDICES_PATH}")

    # Prepare test features
    df_test = df.iloc[test_idx].copy()
    trace_cols = get_trace_columns(100)
    scalar_cols = get_scalar_columns()
    feature_cols = trace_cols + scalar_cols
    X_test = df_test[feature_cols].values

    # Normalize using the same scaler used during training
    model, scaler = load_model(target)
    if scaler is not None:
        X_test = scaler.transform(X_test)
    else:
        # Fallback: fit scaler on test set (not ideal but ensures data is normalized)
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        X_test = scaler.fit_transform(X_test)
        logger.warning("No scaler found in model checkpoint, fitted scaler on test set")

    # Extract targets
    if target == "rank":
        y_test = df_test['analytic_rank'].values
    elif target == "cm":
        y_test = df_test['is_cm'].values
    else:
        raise ValueError(f"Unknown target: {target}")

    logger.info(f"  Test targets shape: {y_test.shape}")

    # Get predictions (classification - get raw probabilities)
    logger.info("Generating predictions...")
    if hasattr(model, "predict_proba"):
        preds = model.predict_proba(X_test)  # Keep probabilities for ensemble
    else:
        logger.warning(f"Model {type(model).__name__} does not have predict_proba, using predict")
        preds = model.predict(X_test).reshape(-1, 1)

    # Save predictions
    output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = output_dir / f"sklearn_preds_{target}.npy"

    np.save(pred_path, preds)

    logger.info(f"✓ Saved predictions: {pred_path} (shape: {preds.shape})")

    return {
        "predictions_path": str(pred_path),
        "num_samples": preds.shape[0],
        "prediction_shape": preds.shape[1:],
    }


def main():
    parser = argparse.ArgumentParser(description="Extract sklearn predictions aligned to GNN test split")
    parser.add_argument(
        "--target",
        choices=["z1", "rank", "cm"],
        help="Target variable (z1, rank, or cm)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extract predictions for all three targets (z1, rank, cm)",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to LMFDB ML dataset CSV",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save extracted predictions",
    )
    args = parser.parse_args()

    if not args.all and not args.target:
        parser.error("Either --target or --all must be specified")

    targets = ["z1", "rank", "cm"] if args.all else [args.target]

    logger.info(f"Extracting sklearn predictions for targets: {targets}")

    results = {}
    for target in targets:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing target: {target}")
        logger.info(f"{'='*60}")
        result = extract_predictions(
            target=target,
            data_path=Path(args.data_path) if args.data_path else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
        results[target] = result

    # Save summary
    summary_path = MODEL_DIR / "sklearn_extraction_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\n✓ Summary saved: {summary_path}")


if __name__ == "__main__":
    main()