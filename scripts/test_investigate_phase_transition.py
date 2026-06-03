import pytest
import numpy as np
from investigate_phase_transition import find_phase_transition_boundary, estimate_embedding_eigenvalues

def test_boundary_detection():
    # Sample correlations showing phase transition at d=20
    d_values = np.array([1, 5, 10, 15, 18, 19, 20, 21, 22, 25, 30])
    rho_values = np.array([0.001, 0.008, 0.012, 0.011, 0.009, 0.008, 0.003, 0.32, 0.33, 0.34, 0.33])

    transition_point = find_phase_transition_boundary(d_values, rho_values)

    assert 20 <= transition_point <= 21, f"Expected boundary at 20-21, got {transition_point}"


def test_eigenvalue_estimation():
    # Simulated trace data: 2 forms, dim=2, 3 primes
    traces = np.array([
        [3.1, 4.2, -1.2],  # form 1: eig=[1.5, 1.6], [pi=2.1, 2.6, -0.73]
        [2.8, 3.9, -1.1],  # form 2: eig=[1.4, 1.4], [pi=2.0, 2.8, -0.79]
    ])

    eigenvalues = estimate_embedding_eigenvalues(traces, dim=2, num_eigvals=2)

    assert eigenvalues.shape == (2, 3, 2), f"Expected shape (2,3,2), got {eigenvalues.shape}"
    assert np.allclose(eigenvalues[0, 0, :].sum(), traces[0, 0], atol=1e-1), "Trace_1[0] should match sum of eigvals at prime 0"