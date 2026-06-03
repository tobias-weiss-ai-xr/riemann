import pytest
import numpy as np
from investigate_phase_transition import find_phase_transition_boundary

def test_boundary_detection():
    # Sample correlations showing phase transition at d=20
    d_values = np.array([1, 5, 10, 15, 18, 19, 20, 21, 22, 25, 30])
    rho_values = np.array([0.001, 0.008, 0.012, 0.011, 0.009, 0.008, 0.003, 0.32, 0.33, 0.34, 0.33])

    transition_point = find_phase_transition_boundary(d_values, rho_values)

    assert 20 <= transition_point <= 21, f"Expected boundary at 20-21, got {transition_point}"