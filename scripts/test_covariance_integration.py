# scripts/test_covariance_integration.py
"""Integration test for full covariance analysis pipeline."""

import pytest
import json
from pathlib import Path

def test_full_pipeline_reduced_data():
    """Run full pipeline on reduced dataset to verify all components work together."""
    import sys
    sys.path.insert(0, "scripts")

    import numpy as np
    import pandas as pd

    # Create synthetic reduced dataset
    np.random.seed(42)
    n_low = 50  # Reduced from 1000
    n_high = 50
    P = 5  # Reduced from 25

    # Low dimensions (d=1-6)
    low_data = {
        f'trace_{2+i}': np.random.randn(n_low) for i in range(P)
    }
    low_data['dim'] = np.random.randint(1, 7, n_low)
    low_data['is_cm'] = [0] * n_low
    low_df = pd.DataFrame(low_data)

    # High dimensions (d=7-12)
    high_data = {
        f'trace_{2+i}': np.random.randn(n_high) for i in range(P)
    }
    high_data['dim'] = np.random.randint(7, 13, n_high)
    high_data['is_cm'] = [0] * n_high
    high_df = pd.DataFrame(high_data)

    from covariance_analysis.matrix_builder import build_correlation_matrix
    from covariance_analysis.spectral_decomp import compute_full_spectrum, compute_spectral_stats

    # Build matrices
    low_corr = build_correlation_matrix(low_df)
    high_corr = build_correlation_matrix(high_df)

    # Check matrices
    assert low_corr.shape == (P, P)
    assert high_corr.shape == (P, P)

    # Spectral decomposition
    low_evals, low_vecs = compute_full_spectrum(low_corr)
    high_evals, high_vecs = compute_full_spectrum(high_corr)

    # Check eigenvalues sum to trace (within tolerance)
    assert abs(low_evals.sum() - np.trace(low_corr)) < 1e-10
    assert abs(high_evals.sum() - np.trace(high_corr)) < 1e-10

    # Spectral stats
    low_stats = compute_spectral_stats(low_evals)
    high_stats = compute_spectral_stats(high_evals)

    # Check ranges
    assert 1 <= low_stats['effective_rank'] <= P
    assert 1 <= high_stats['effective_rank'] <= P
    assert 0 <= low_stats['entropy'] <= np.log(P) + 1e-10
    assert 0 <= high_stats['entropy'] <= np.log(P) + 1e-10

    print("Integration test PASSED: Full pipeline works correctly")