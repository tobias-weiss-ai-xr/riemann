from __future__ import annotations
import numpy as np
from scipy import stats
from loguru import logger
import pandas as pd
from pathlib import Path


def compute_form_pair_correlation(
    trace_a: np.ndarray,
    trace_b: np.ndarray,
    dim: int,
    num_primes: int
) -> float:
    """
    Compute Galois correlation between two forms.

    Estimates embedding eigenvalues via equal division, computes
    per-prime correlations, averages across primes.

    Args:
        trace_a, trace_b: trace vectors (length num_primes)
        dim: dimension d
        num_primes: number of primes to use

    Returns:
        Mean correlation coefficient across all primes
    """
    correlations = []

    for p in range(num_primes):
        # Equal division: trace / dim for each embedding
        eig_a = np.full(dim, trace_a[p] / dim)
        eig_b = np.full(dim, trace_b[p] / dim)

        # Skip if arrays are constant (can't correlate)
        if np.all(eig_a ==eig_a[0]) or np.all(eig_b == eig_b[0]):
            continue

        corr, _ = stats.pearsonr(eig_a, eig_b)
        correlations.append(corr)

    # Return 0 if no valid correlations
    if not correlations:
        return 0.0

    return float(np.mean(correlations))


def compute_classical_rho_d(
    traces: np.ndarray,
    dim: int,
    num_primes: int = 25,
    sample_size: int = 1000
) -> float:
    """
    Compute classical ρ_d using pair-wise form correlations.

    Samples pairs of dim=d forms, computes correlation for each pair,
    returns mean across all pairs.

    Args:
        traces: array of shape (n_forms, num_primes)
        dim: dimension to analyze
        num_primes: number of primes to use
        sample_size: maximum number of pair correlations to compute

    Returns:
        Mean correlation ρ_d
    """
    n_forms = len(traces)
    correlations = []

    for i in range(min(sample_size, n_forms)):
        for j in range(i + 1, min(i + sample_size // n_forms + 1, n_forms)):
            rho = compute_form_pair_correlation(
                traces[i, :num_primes],
                traces[j, :num_primes],
                dim,
                num_primes
            )
            correlations.append(rho)

            if len(correlations) >= sample_size:
                break
        if len(correlations) >= sample_size:
            break

    return float(np.mean(correlations))


def load_and_sample_forms(
    csv_path: Path,
    target_dim: int,
    sample_size: int = 500
) -> np.ndarray:
    """Load dim=d forms from CSV and return early sample."""
    df = pd.read_csv(csv_path)
    dim_d = df[df.dim == target_dim].head(sample_size)

    # Get trace columns (only numbered ones, skip trace_mean, trace_std, trace_max_abs)
    trace_cols = [c for c in dim_d.columns if c.startswith('trace_') and c[6:].isdigit()]
    trace_cols = sorted(trace_cols, key=lambda x: int(x.split('_')[1]))
    trace_cols = trace_cols[:50]  # Use first 50 primes

    return dim_d[trace_cols].values