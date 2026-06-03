import pytest
import numpy as np

def test_correlation_recalculation():
    from recompute_galois_correlations import load_and_sample_forms, compute_form_pair_correlation

    # Sample subset: dim=2 forms, values that differ for correlation
    traces = np.array([
        [3.1, 4.2, -1.2, 2.5],
        [5.8, 2.1, 1.5, -0.8],
        [3.3, 4.1, -1.3, 2.7],
    ])

    # Correlation between first two forms across all primes
    rho = compute_form_pair_correlation(
        traces[0, :],
        traces[1, :],
        dim=2,
        num_primes=traces.shape[1]
    )

    # Should be a float between -1 and 1
    assert isinstance(rho, float)
    assert -1.0 <= rho <= 1.0, f"Invalid correlation: {rho}"