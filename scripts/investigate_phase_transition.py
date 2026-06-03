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