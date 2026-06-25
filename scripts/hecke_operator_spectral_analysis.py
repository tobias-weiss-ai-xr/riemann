# scripts/hecke_operator_spectral_analysis.py
import numpy as np
import pandas as pd
from pathlib import Path
import json
from loguru import logger

def load_traces():
    """Load LMFDB weight 2 trace data"""
    df = pd.read_csv('data/lmfdb/lmfdb_sql_weight2_ml.csv')
    df = df[df['is_cm'] == 0]
    return df

def build_hecke_matrix(trace_col: str, dimension: int, max_students: int = 1000) -> np.ndarray:
    """
    Build Hecke matrix for a specific prime from traces.

    For dimension d, the Hecke operator T_p acts on a d-dimensional vector space.
    For each newform of dimension d, the trace of T_p is the sum of its d eigenvalues.

    To reconstruct the full d×d Hecke matrix, we're using a proxy:
    treat each trace as an element in the eigenvalue spectrum.

    Note: This is an approximation. True Hecke matrices would require access to
    individual embedding eigenvalues, which LMFDB traces don't provide.
    """
    df = load_traces()
    d_mask = df['dim'] == dimension

    if d_mask.sum() == 0:
        return np.array([])

    # Take traces for this dimension
    traces = df[d_mask][trace_col].values.astype(float)

    if len(traces) > max_students:
        # Subsample forms to avoid memory issues
        traces = np.random.choice(traces, max_students, replace=False)

    # Hecke matrix construction: build a symmetric matrix whose spectral
    # properties reflect the trace distribution
    # Using covariance matrix as proxy for eigenvalue structure
    traces_centered = traces - traces.mean()
    N = len(traces_centered)

    # Symmetric matrix: (T_traces)^T * (T_traces) / N
    # This gives us a proxy for the symmetric eigenvalue structure
    hecke_proxy = np.outer(traces_centered, traces_centered) / N

    return hecke_proxy

def compute_hecke_eigenvalues_by_dimension(p: int = 2, max_dim: int = 12) -> dict:
    """
    Compute eigenvalues of Hecke operator T_p for each dimension.

    Uses trace data as proxy for individual embedding eigenvalues.
    """
    trace_col = f'trace_{p}'
    df = load_traces()

    eigenvalues_by_dim = {}
    dims_to_analyze = list(range(1, max_dim + 1))  # All available dimensions 1-12

    for d in dims_to_analyze:
        d_mask = df['dim'] == d
        if d_mask.sum() == 0:
            logger.warning(f"No forms for dimension {d}")
            continue

        # Build Hecke matrix proxy
        hecke_matrix = build_hecke_matrix(trace_col, d)

        if hecke_matrix.size == 0:
            continue

        # Compute eigenvalues
        eigvals = np.linalg.eigvalsh(hecke_matrix)  # Symmetric → real eigenvalues
        eigvals = np.real(eigvals)  # Remove tiny imaginary parts from numerical noise
        eigenvalues_by_dim[f'd{d}'] = eigvals.tolist()

        logger.info(f"Dimension {d}: computed {len(eigvals)} Hecke eigenvalues (p={p})")

    return eigenvalues_by_dim

def compute_eigenvalue_spacing(eigvals_by_dim: dict):
    """Compute gaps between consecutive eigenvalues (sorted)"""
    spacing = {}
    for dim, eigvals in eigvals_by_dim.items():
        sorted_eigvals = np.sort(eigvals)
        gaps = np.diff(sorted_eigvals)
        spacing[dim] = gaps.tolist()
    return spacing

def compute_spectral_gaps(p: int = 2, max_dim: int = 12) -> dict:
    """Compute spectral gap (λ_2 - λ_1) for each dimension"""
    eigvals_by_dim = compute_hecke_eigenvalues_by_dimension(p, max_dim)

    gaps = {}
    for dim, eigvals in eigvals_by_dim.items():
        if len(eigvals) >= 2:
            sorted_eigvals = np.sort(eigvals)
            gaps[dim] = sorted_eigvals[1] - sorted_eigvals[0]

    return gaps

def analyze_spectral_statistics(eigvals_by_dim: dict):
    """Compute spectral statistics: spacing distribution, level repulsion, etc."""
    results = {}

    for dim, eigvals in eigvals_by_dim.items():
        eigvals = np.array(eigvals)
        sorted_eigvals = np.sort(eigvals)
        gaps = np.diff(sorted_eigvals)

        if len(gaps) == 0:
            # Handle single eigenvalue case
            results[dim] = {
                'mean_gap': 0.0,
                'std_gap': 0.0,
                'eigenvalue_range': (float(np.min(eigvals)), float(np.max(eigvals))),
                'n_eigvals': len(eigvals),
            }
            continue

        mean_gap = np.mean(gaps)
        normalized_gaps = gaps / mean_gap if mean_gap > 0 else gaps  # Wigner surmise normalization

        # Level statistics
        results[dim] = {
            'mean_gap': float(np.mean(gaps)),
            'std_gap': float(np.std(gaps)),
            'mean_normalized_gap': float(np.mean(normalized_gaps)),
            'std_normalized_gap': float(np.std(normalized_gaps)),
            'eigenvalue_range': (float(np.min(eigvals)), float(np.max(eigvals))),
            'gap_histogram': np.histogram(normalized_gaps, bins=30, range=(0, 3))[0].tolist(),
            'n_eigvals': len(eigvals),
        }

    return results

def compare_dim_spectra():
    """Compare spectral properties between low and high dimensions"""
    eigvals = compute_hecke_eigenvalues_by_dimension(p=2)
    stats = analyze_spectral_statistics(eigvals)

    comparison = {
        'low_dim': {},
        'high_dim': {},
        'differences': {}
    }

    # Group by low (d<=6) and high (d>6) dimensions
    low_d = {k: v for k, v in stats.items() if int(k[1:]) <= 6}
    high_d = {k: v for k, v in stats.items() if int(k[1:]) > 6}

    # Aggregate statistics
    for group, dims in [('low_dim', low_d), ('high_dim', high_d)]:
        if dims:
            comparison[group] = {
                'mean_gap': float(np.mean([v['mean_gap'] for v in dims.values()])),
                'std_gap': float(np.mean([v['std_gap'] for v in dims.values()])),
                'mean_normalized_gap': float(np.mean([v['mean_normalized_gap'] for v in dims.values()])),
                'n_dimensions': len(dims),
            }

    # Compute differences
    if 'low_dim' in comparison and 'high_dim' in comparison:
        comparison['differences'] = {
            'mean_gap': comparison['high_dim']['mean_gap'] - comparison['low_dim']['mean_gap'],
            'std_gap': comparison['high_dim']['std_gap'] - comparison['low_dim']['std_gap'],
            'mean_normalized_gap': comparison['high_dim']['mean_normalized_gap'] - comparison['low_dim']['mean_normalized_gap'],
        }

    return comparison

def main():
    logger.info("Analyzing Hecke operator spectral properties")

    primes_to_test = [2, 3, 5]

    out_dir = Path('data/d21_analysis/hecke_eigenvalues')
    out_dir.mkdir(parents=True, exist_ok=True)

    for p in primes_to_test:
        logger.info(f"Analyzing T_{p}")

        # 1. Compute eigenvalues
        eigvals = compute_hecke_eigenvalues_by_dimension(p)
        for dim, vals in eigvals.items():
            path = out_dir / f'{dim}_p{p}.json'
            with open(path, 'w') as f:
                json.dump(vals, f, indent=2)
            logger.info(f"Saved: {path}")

        # 2. Compute spectral statistics
        stats = analyze_spectral_statistics(eigvals)
        with open(out_dir / f'spectral_stats_p{p}.json', 'w') as f:
            json.dump(stats, f, indent=2)

        # 3. Compare low vs high dimensions
        comparison = compare_dim_spectra()
        with open(out_dir / f'dim_comparison_p{p}.json', 'w') as f:
            json.dump(comparison, f, indent=2)

        logger.info(f"T_{p} comparison: {comparison['differences'] if 'differences' in comparison else 'N/A'}")

    logger.info("Hecke spectral analysis complete")

if __name__ == '__main__':
    main()