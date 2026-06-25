# scripts/covariance_analysis/matrix_builder.py
import numpy as np
import pandas as pd
from loguru import logger

def build_correlation_matrix(df, rate=1.0):
    """Build P×P correlation matrix from trace columns.

    Args:
        df: DataFrame with trace columns (trace_2, trace_3, trace_5, ...)
        rate: Exponential decay rate for slot variance ratio (default 1.0)

    Returns:
        np.ndarray: P×P symmetric correlation matrix
    """
    trace_columns = [col for col in df.columns if col.startswith('trace_')]

    if not trace_columns:
        raise ValueError("No trace columns found in DataFrame")

    # Extract trace matrix: N_forms × P_traces
    trace_matrix = df[trace_columns].values

    # Apply exponential decay slot variance ratio
    # Weight traces based on their index with decay: w_i = exp(-rate * (i / P))
    P_traces = trace_matrix.shape[1]
    weights = np.exp(-rate * np.arange(P_traces) / P_traces)
    weights = weights.reshape(1, -1)  # Shape: 1 × P

    # Apply weights to traces
    weighted_trace_matrix = trace_matrix * weights

    # Compute correlation matrix
    corr_matrix = np.corrcoef(weighted_trace_matrix.T)  # Transpose to get P×P

    # Handle NaN values (perfectly constant columns)
    corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

    # Ensure numerical symmetry
    corr_matrix = (corr_matrix + corr_matrix.T) / 2

    logger.info(f"Built correlation matrix {corr_matrix.shape} from {trace_matrix.shape} trace data (rate={rate})")

    return corr_matrix


def subsample_forms(df, n_samples=1000, random_state=42):
    """Stratified random subsampling to reduce computational load.

    Args:
        df: DataFrame to sample from
        n_samples: Target number of samples
        random_state: Random seed for reproducibility

    Returns:
        pd.DataFrame: Subsampled DataFrame
    """
    if len(df) <= n_samples:
        logger.info(f"Using all {len(df)} forms (no subsampling needed)")
        return df.copy()

    # Sample without replacement
    sampled = df.sample(n=n_samples, random_state=random_state, replace=False)
    logger.info(f"Subsampled from {len(df)} to {len(sampled)} forms")

    return sampled