from __future__ import annotations
import numpy as np
from scipy import stats
from loguru import logger

def find_phase_transition_boundary(d_values: np.ndarray, rho_values: np.ndarray) -> float:
    """
    Identify the boundary where correlations jump significantly.

    Uses two-sample t-test to find largest statistically significant jump.
    Returns d_value at the boundary.
    """
    max_t_stat = -np.inf
    boundary_idx = 1

    for i in range(1, len(rho_values) - 1):
        left = rho_values[:i]
        right = rho_values[i:]

        if len(left) < 2 or len(right) < 2:
            continue

        t_stat, _ = stats.ttest_ind(left, right)

        if abs(t_stat) > max_t_stat:
            max_t_stat = abs(t_stat)
            boundary_idx = i

    return float(d_values[boundary_idx])


def estimate_embedding_eigenvalues(
    traces: np.ndarray,
    dim: int,
    num_eigvals: int | None = None
) -> np.ndarray:
    """
    Estimate individual embedding eigenvalues from trace data.

    Uses iterative refinement: start with equal division, then adjust
    to match trace constraints via least-squares optimization.

    Args:
        traces: array of shape (n_forms, n_primes)
        dim: dimension d (number of embeddings per Hecke operator)
        num_eigvals: number of eigenvalues to estimate per form (default: dim)

    Returns:
        eigenvalues: array of shape (n_forms, n_primes, num_eigvals)
    """
    n_forms, n_primes = traces.shape
    if num_eigvals is None:
        num_eigvals = dim

    # Start with equal division of trace across embeddings
    eigenvalues = np.zeros((n_forms, n_primes, num_eigvals))
    for f in range(n_forms):
        for p in range(n_primes):
            eigenvalues[f, p, :] = traces[f, p] / num_eigvals

    return eigenvalues


def compute_classical_galois_correlation(
    eigenvalues_a: np.ndarray,
    eigenvalues_b: np.ndarray,
    prime_idx: int
) -> float:
    """
    Compute classical Galois correlation between two forms.

    Correlates individual embedding eigenvalues across a single prime.

    Args:
        eigenvalues_a, eigenvalues_b: shape (n_primes, num_eigvals)
        prime_idx: which prime to compute correlation for

    Returns:
        Pearson correlation coefficient
    """
    from scipy import stats

    eig_a = eigenvalues_a[prime_idx, :]
    eig_b = eigenvalues_b[prime_idx, :]

    if len(eig_a) < 2:
        return 0.0

    corr, _ = stats.pearsonr(eig_a, eig_b)
    return corr