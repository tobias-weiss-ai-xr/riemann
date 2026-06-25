# scripts/synthetic_trace_generator.py
import numpy as np
import pandas as pd
from pathlib import Path
import json
from loguru import logger

def hecke_bounds(p: int, dimension: int):
    """
    Return theoretical Hecke operator bounds for trace T_p.

    For weight 2 eigenforms:
    |a_p| ≤ 2 * p^(1/2)                      (Hasse bound)
    |Tr(T_p)| ≤ dimension * 2 * p^(1/2)     (sum of eigenvalues)
    """
    hecke_bound = 2 * np.sqrt(p)
    trace_bound = dimension * hecke_bound
    return -trace_bound, trace_bound

def generate_random_eigenvalues(d: int, p: int, distribution='semicircle'):
    """
    Generate d random eigenvalues for Hecke operator T_p.

    Distributions:
    - semicircle: Random matrix theory (GUE), typical for high-dimensional systems
    - uniform: Uniform within Hecke bounds
    - mixture: 50% semicircle + 50% outliers
    """
    hecke_bound = 2 * np.sqrt(p)

    if distribution == 'semicircle':
        # Wigner semicircle distribution
        radius = hecke_bound
        samples = []
        while len(samples) < d:
            x = np.random.uniform(-radius, radius)
            y = np.random.uniform(0, radius)
            if y <= np.sqrt(radius**2 - x**2):
                samples.append(x)
        eigenvalues = np.array(samples)

    elif distribution == 'uniform':
        eigenvalues = np.random.uniform(-hecke_bound, hecke_bound, d)

    elif distribution == 'mixture':
        # 80% semicircle, 20% outliers at bounds
        n_main = int(0.8 * d) if int(0.8 * d) > 0 else 1
        n_outliers = d - n_main

        main_eigs = generate_random_eigenvalues(n_main, p, 'semicircle')

        # Outliers at Hecke bounds
        outliers_p = np.random.rand(n_outliers)
        outliers = np.where(outliers_p < 0.5, -hecke_bound, hecke_bound)

        eigenvalues = np.concatenate([main_eigs, outliers])
        np.random.shuffle(eigenvalues)

    else:
        raise ValueError(f"Unknown distribution: {distribution}")

    return eigenvalues

def compute_trace_from_eigenvalues(eigenvalues: np.ndarray):
    """Trace = sum of eigenvalues"""
    return np.sum(eigenvalues)

def generate_synthetic_traces(n_forms: int, dimensions: list[int], p: int = 2,
                              distribution='semicircle'):
    """
    Generate synthetic LMFDB-like trace data.

    For each form of dimension d:
    1. Generate d random eigenvalues for T_p
    2. Compute trace = sum of eigenvalues
    3. Return as pandas DataFrame
    """
    forms = []

    for _ in range(n_forms):
        d = np.random.choice(dimensions)
        eigenvalues = generate_random_eigenvalues(d, p, distribution)
        trace = compute_trace_from_eigenvalues(eigenvalues)

        forms.append({
            'dim': d,
            f'trace_{p}': trace,
            'eigenvalues': eigenvalues.tolist(),
        })

    df = pd.DataFrame(forms)
    return df

def generate_controlled_phase_transition():
    """
    Generate synthetic data designed to probe phase transition at d=12 (max available).

    Varies eigenvalue distribution qualitatively at the boundary:
    - Dimensions < 6: semicircle distribution (RMT-like)
    - Dimensions >= 6: biased distribution with clustering at extremes
    """
    forms = []

    dims_low = list(range(1, 6))  # Could test boundary at 6 instead of 21
    dims_high = list(range(6, 13))

    n_forms_per_dim = 50

    for d in dims_low:
        for _ in range(n_forms_per_dim):
            eigenvalues = generate_random_eigenvalues(d, p=2, distribution='semicircle')
            trace = compute_trace_from_eigenvalues(eigenvalues)

            forms.append({
                'dim': d,
                'trace_2': trace,
                'distribution': 'semicircle',
            })

    for d in dims_high:
        for _ in range(n_forms_per_dim):
            # Post-6: mixture distribution with outliers
            eigenvalues = generate_random_eigenvalues(d, p=2, distribution='mixture')
            trace = compute_trace_from_eigenvalues(eigenvalues)

            forms.append({
                'dim': d,
                'trace_2': trace,
                'distribution': 'mixture',
            })

    df = pd.DataFrame(forms)
    return df

def compute_synthetic_correlations(df: pd.DataFrame):
    """Compute cross-form correlations for synthetic data"""
    results = {}

    for d in sorted(df['dim'].unique()):
        d_mask = df['dim'] == d
        traces = df[d_mask]['trace_2'].values.astype(float)

        if len(traces) < 2:
            continue

        # Build correlation matrix (size N_d × N_d)
        # Use outer product of centered traces as proxy
        traces_centered = traces - traces.mean()
        N = len(traces)

        # Correlation matrix: C[i,j] = (tr_i - mu_i)(tr_j - mu_j) / sigma
        # Simplified: correlation matrix from outer product
        corr_matrix = np.outer(traces_centered, traces_centered)
        std_dev = np.std(traces_centered) if np.std(traces_centered) > 0 else 1.0
        corr_matrix = corr_matrix / (std_dev * N)

        # Mean off-diagonal
        off_diagonal = corr_matrix[np.triu_indices(N, k=1)]
        mean_corr = np.mean(off_diagonal) if len(off_diagonal) > 0 else 0.0

        results[int(d)] = float(mean_corr)

    return results

def test_synthetic_phase_transition():
    """Test if controlled synthetic data shows phase-like behavior"""
    df = generate_controlled_phase_transition()
    correlations = compute_synthetic_correlations(df)

    low_vals = [v for d, v in correlations.items() if d < 6]
    high_vals = [v for d, v in correlations.items() if d >= 6]

    low_mean = np.mean(low_vals) if low_vals else 0
    high_mean = np.mean(high_vals) if high_vals else 0

    logger.info(f"Synthetic data: low-dim mean correlation = {low_mean:.4f}")
    logger.info(f"Synthetic data: high-dim mean correlation = {high_mean:.4f}")
    logger.info(f"Difference: {high_mean - low_mean:.4f}")

    return {
        'low_dim_mean': float(low_mean),
        'high_dim_mean': float(high_mean),
        'difference': float(high_mean - low_mean),
        'correlations_by_dim': correlations,
    }

def main():
    logger.info("Generating synthetic traces for controlled testing")

    # 1. Random baseline traces
    df_random = generate_synthetic_traces(
        n_forms=200, dimensions=list(range(1, 13)), p=2, distribution='semicircle'
    )
    out_dir = Path('data/d21_analysis/synthetic')
    out_dir.mkdir(parents=True, exist_ok=True)

    df_random.to_csv(out_dir / 'random_traces.csv', index=False)
    logger.info(f"Saved: {out_dir / 'random_traces.csv'} ({len(df_random)} forms)")

    # 2. Controlled phase transition test
    df_phase = generate_controlled_phase_transition()
    results = test_synthetic_phase_transition()

    df_phase.to_csv(out_dir / 'phase_transition_test.csv', index=False)
    logger.info(f"Saved: {out_dir / 'phase_transition_test.csv'} ({len(df_phase)} forms)")

    # 3. Save correlation results
    with open(out_dir / 'synthetic_correlation_test.json', 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"Synthetic phase transition difference: {results['difference']:.4f}")
    logger.info("Synthetic trace generation complete")

if __name__ == '__main__':
    main()