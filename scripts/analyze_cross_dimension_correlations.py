from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
import argparse
import json
from scipy import stats


def compute_cross_dimension_correlation(
    df: pd.DataFrame,
    dim_a: int,
    dim_b: int,
    num_primes: int = 25
) -> float:
    """
    Compute correlation between dim=a and dim=b trace vectors.

    Correlates the mean trace at each prime across all forms in each dimension.
    Uses mean of eigenvalues across forms, which approximates mean trace behavior.

    Args:
        df: DataFrame with 'dim' and trace columns
        dim_a, dim_b: dimensions to correlate
        num_primes: number of traces to use

    Returns:
        Pearson correlation coefficient
    """
    # Get trace columns (only numbered ones, skip trace_mean, trace_std, trace_max_abs)
    trace_cols = [c for c in df.columns if c.startswith('trace_') and c[6:].isdigit()]
    trace_cols = sorted(trace_cols, key=lambda x: int(x.split('_')[1]))
    trace_cols = trace_cols[:num_primes]

    # Extract forms for each dimension
    forms_a = df[df.dim == dim_a][trace_cols].values
    forms_b = df[df.dim == dim_b][trace_cols].values

    if len(forms_a) == 0 or len(forms_b) == 0:
        logger.warning(f"No forms for dim={dim_a} or dim={dim_b}")
        return 0.0

    # Compute mean trace per prime for each dimension
    mean_trace_a = forms_a.mean(axis=0)  # (num_primes,)
    mean_trace_b = forms_b.mean(axis=0)  # (num_primes,)

    # Compute correlation
    corr, _ = stats.pearsonr(mean_trace_a, mean_trace_b)
    return float(corr if not np.isnan(corr) else 0.0)


def build_cross_dimension_matrix(
    df: pd.DataFrame,
    dimensions: list[int],
    num_primes: int = 25
) -> np.ndarray:
    """
    Build d×d correlation matrix computing cross-dimension correlations.

    Args:
        df: DataFrame with 'dim' and trace columns
        dimensions: list of dimensions to analyze (sorted)
        num_primes: number of traces to use

    Returns:
        d×d correlation matrix where matrix[i,j] = ρ_{dim_i, dim_j}
    """
    n_dims = len(dimensions)
    corr_matrix = np.zeros((n_dims, n_dims))

    for i, dim_a in enumerate(dimensions):
        for j, dim_b in enumerate(dimensions):
            if i <= j:  # Fill both (i,j) and (j,i) since correlation is symmetric
                corr = compute_cross_dimension_correlation(df, dim_a, dim_b, num_primes)
                corr_matrix[i, j] = corr
                corr_matrix[j, i] = corr

    return corr_matrix


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='data/lmfdb/lmfdb_sql_weight2_ml.csv')
    parser.add_argument('--max-dim', type=int, default=12, help='Max dimension to analyze')
    parser.add_argument('--min-forms', type=int, default=10, help='Min forms per dimension to include')
    parser.add_argument('--num-primes', type=int, default=25, help='Number of traces to use')
    args = parser.parse_args()

    logger.info(f"Loading data from {args.csv}...")
    df = pd.read_csv(args.csv)

    # Filter CM forms if present
    if 'is_cm' in df.columns:
        df = df[df.is_cm == 0]
        logger.info(f"Filtered to {len(df)} non-CM forms")

    # Get significant dimensions (enough sample size)
    dim_counts = df.dim.value_counts()
    significant_dims = sorted(dim_counts[dim_counts >= args.min_forms].index.tolist())

    # Limit to max_dim if specified
    dimensions = [d for d in significant_dims if d <= args.max_dim]

    logger.info(f"Analyzing dimensions: {dimensions}")
    logger.info(f"Form counts: {[int(dim_counts[d]) for d in dimensions[:10]]}")

    logger.info("Building cross-dimension correlation matrix...")
    corr_matrix = build_cross_dimension_matrix(df, dimensions, args.num_primes)

    # Save matrix
    results = {
        'dimensions': dimensions,
        'correlation_matrix': corr_matrix.tolist(),
        'params': {
            'num_primes': args.num_primes,
            'min_forms': args.min_forms,
        }
    }

    results_path = Path('data/galois_correlation/cross_dimension_matrix.json')
    results_path.parent.mkdir(parents=True, exist_ok=True)

    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.success(f"Saved {len(dimensions)}×{len(dimensions)} correlation matrix to {results_path}")

# Print key correlation pairs
    logger.info("\nKey cross-dimension correlations:")
    pairs_to_show = [(2, 4), (2, 6), (4, 6), (1, 2), (1, 10)]
    for d_a, d_b in pairs_to_show:
        if d_a in dimensions and d_b in dimensions:
            corr = corr_matrix[dimensions.index(d_a), dimensions.index(d_b)]
            logger.info(f"  ρ_{d_a},{d_b} = {corr:.4f}")
        else:
            logger.info(f"  ρ_{d_a},{d_b} = N/A (dim not analyzed)")

    # Diagonal values (self-correlations)
    logger.info(f"\nSelf-correlations (ρ_d,d):")
    for i, d in enumerate(dimensions):
        logger.info(f"  ρ_{d},{d} = {corr_matrix[i, i]:.4f}")


if __name__ == '__main__':
    main()