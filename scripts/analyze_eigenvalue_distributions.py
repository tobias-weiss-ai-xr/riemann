# scripts/analyze_eigenvalue_distributions.py
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
import matplotlib.pyplot as plt
from loguru import logger
import json

def load_traces():
    """Load LMFDB weight 2 trace data"""
    df = pd.read_csv('data/lmfdb/lmfdb_sql_weight2_ml.csv')
    # Filter non-CM forms
    df = df[df['is_cm'] == 0]
    return df

def compute_distribution_stats(values: np.ndarray) -> dict:
    """Compute comprehensive distribution statistics"""
    return {
        'mean': float(np.mean(values)),
        'std': float(np.std(values)),
        'skewness': float(stats.skew(values)),
        'kurtosis': float(stats.kurtosis(values)),
        'median': float(np.median(values)),
        'iqr': float(np.percentile(values, 75) - np.percentile(values, 25)),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'entropy': float(stats.entropy(np.histogram(values, bins=50)[0] + 1e-10)),
    }

def compute_dimension_distribution_stats(trace_cols, max_dim=12):
    """Compute distribution stats per dimension class"""
    df = load_traces()
    trace_df = df[trace_cols].values  # Shape: (N_forms, N_traces)

    results = {}
    for d in range(1, max_dim + 1):
        d_mask = df['dim'] == d
        if d_mask.sum() == 0:
            continue

        # Process each trace column
        for i, col in enumerate(trace_cols):
            values = trace_df[d_mask, i].astype(float)
            key = f'd{d}_{col}'
            results[key] = compute_distribution_stats(values)

    return results

def compute_clustering_metrics(trace_cols) -> dict:
    """Compute clustering metrics per dimension"""
    df = load_traces()
    trace_df = df[trace_cols].values

    results = {}
    for d in range(1, 13):
        d_mask = df['dim'] == d
        if d_mask.sum() == 0:
            continue

        for i, col in enumerate(trace_cols):
            values = trace_df[d_mask, i].astype(float)

            # Clustering metric: mean pairwise distance
            n = len(values)
            if n > 1000:  # Subsample for efficiency
                indices = np.random.choice(n, 1000, replace=False)
                values = values[indices]

            # Compute mean absolute deviation from median (clustering)
            mad = np.mean(np.abs(values - np.median(values)))
            key = f'd{d}_{col}'
            results[key] = float(mad)

    return results

def compare_moment_divergence():
    """Compare statistical moments between lower (d<=6) and higher (d>6) dimensions"""
    df = load_traces()
    trace_cols = ['trace_2', 'trace_3', 'trace_5', 'trace_7']

    results = {'low_dim': {}, 'high_dim': {}, 'divergence': {}}

    for col in trace_cols:
        low_dim_values = df[df['dim'] <= 6][col].values.astype(float)
        high_dim_values = df[df['dim'] > 6][col].values.astype(float)

        if len(low_dim_values) == 0 or len(high_dim_values) == 0:
            logger.warning(f"Insufficient data for {col}")
            continue

        results['low_dim'][col] = compute_distribution_stats(low_dim_values)
        results['high_dim'][col] = compute_distribution_stats(high_dim_values)

        # Compute divergence
        results['divergence'][col] = {
            metric: abs(results['low_dim'][col][metric] - results['high_dim'][col][metric])
            for metric in results['low_dim'][col]
        }

    return results

def visualize_distributions(trace_cols: list):
    """Generate distribution visualizations by dimension"""
    df = load_traces()
    out_dir = Path('plots/d21_analysis')
    out_dir.mkdir(parents=True, exist_ok=True)

    for col in trace_cols:
        fig, axes = plt.subplots(3, 4, figsize=(16, 12), sharex=True)
        axes = axes.flatten()

        for d in range(1, 13):
            d_mask = df['dim'] == d
            if d_mask.sum() == 0:
                continue

            values = df[d_mask][col].values.astype(float)

            if len(values) == 0:
                continue

            ax = axes[d - 1]
            ax.hist(values, bins=50, alpha=0.7, edgecolor='black', density=True)

            # Add vertical lines for mean and median
            ax.axvline(np.mean(values), color='red', linestyle='--', label='Mean')
            ax.axvline(np.median(values), color='blue', linestyle=':', label='Median')

            ax.set_title(f'Dimension {d}\n(n={len(values)})')
            ax.set_ylabel('Density')

            if d > 8:
                ax.set_xlabel(f'{col}')
                ax.legend(fontsize='small')

        plt.suptitle(f'Eigenvalue Distribution by Dimension - {col}')
        plt.tight_layout()
        plt.savefig(out_dir / f'eigenvalue_distr_{col}.png', dpi=150)
        plt.close()

        logger.info(f"Saved: {out_dir / f'eigenvalue_distr_{col}.png'}")

def main():
    logger.info("Analyzing eigenvalue distributions by dimension")

    trace_cols = ['trace_2', 'trace_3', 'trace_5', 'trace_7']

    # 1. Compute distribution statistics per dimension
    stats = compute_dimension_distribution_stats(trace_cols)

    # Save results
    out_dir = Path('data/d21_analysis/distributions')
    out_dir.mkdir(parents=True, exist_ok=True)

    low_dim_stats = {k: v for k, v in stats.items() if int(k.split('_')[0][1:]) <= 6}
    high_dim_stats = {k: v for k, v in stats.items() if int(k.split('_')[0][1:]) > 6}

    with open(out_dir / 'd1_6_stats.json', 'w') as f:
        json.dump(low_dim_stats, f, indent=2)

    with open(out_dir / 'd7_12_stats.json', 'w') as f:
        json.dump(high_dim_stats, f, indent=2)

    # 2. Compute clustering metrics
    clustering = compute_clustering_metrics(trace_cols)
    with open(out_dir / 'clustering_metrics.json', 'w') as f:
        json.dump(clustering, f, indent=2)

    # 3. Compute moment divergence between low and high dims
    divergence = compare_moment_divergence()
    with open(out_dir / 'moment_divergence.json', 'w') as f:
        json.dump(divergence, f, indent=2)

    logger.info(f"Low dimension (d<=6) mean skewness: {np.mean([v.get('skewness', 0) for v in low_dim_stats.values()]):.3f}")
    logger.info(f"High dimension (d>6) mean skewness: {np.mean([v.get('skewness', 0) for v in high_dim_stats.values()]):.3f}")
    logger.info(f"Low dimension (d<=6) mean kurtosis: {np.mean([v.get('kurtosis', 0) for v in low_dim_stats.values()]):.3f}")
    logger.info(f"High dimension (d>6) mean kurtosis: {np.mean([v.get('kurtosis', 0) for v in high_dim_stats.values()]):.3f}")

    # 4. Generate visualizations
    visualize_distributions(trace_cols)

    logger.info("Distribution analysis complete. Results saved to data/d21_analysis/distributions/")

if __name__ == '__main__':
    main()