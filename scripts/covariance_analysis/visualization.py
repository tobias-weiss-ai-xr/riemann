# scripts/covariance_analysis/visualization.py
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from loguru import logger

def plot_eigenvalue_scree(low_evals, high_evals, output_path):
    """Plot eigenvalue scree plots for both classes."""
    fig, ax = plt.subplots(figsize=(10, 6))

    n = max(len(low_evals), len(high_evals))

    ax.plot(range(len(low_evals)), low_evals, 'o-', label='Low dimensions (d≤6)', linewidth=2)
    ax.plot(range(len(high_evals)), high_evals, 's-', label='High dimensions (d>6)', linewidth=2)

    ax.set_xlabel('Eigenvector index', fontsize=12)
    ax.set_ylabel('Eigenvalue (descending)', fontsize=12)
    ax.set_title('Eigenvalue Scree Plot Comparison', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Saved eigenvalue scree plot to {output_path}")

def plot_top_eigenvectors(low_modes, high_modes, output_path, k=5):
    """Plot top-k eigenvector components as bar charts."""
    n_primes = len(low_modes[0]['eigenvector'])
    k = min(k, len(low_modes), len(high_modes))

    fig, axes = plt.subplots(2, k, figsize=(4*k, 8))

    for i in range(k):
        # Low dimensions
        axes[0, i].bar(range(n_primes), low_modes[i]['eigenvector'])
        axes[0, i].set_title(f'Low-dim Mode {i+1}\n(λ={low_modes[i]["eigenvalue"]:.3f})')
        axes[0, i].set_xlabel('Prime index')
        axes[0, i].set_ylabel('Eigenvector component')
        axes[0, i].grid(True, alpha=0.3)

        # High dimensions
        axes[1, i].bar(range(n_primes), high_modes[i]['eigenvector'])
        axes[1, i].set_title(f'High-dim Mode {i+1}\n(λ={high_modes[i]["eigenvalue"]:.3f})')
        axes[1, i].set_xlabel('Prime index')
        axes[1, i].grid(True, alpha=0.3)

    plt.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Saved top-{k} eigenvector plot to {output_path}")

def plot_spectral_metrics_comparison(comparison, output_path):
    """Plot bar charts of spectral comparison metrics."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # Metric names and values
    metrics = {
        'KL Divergence': comparison['kl_divergence'],
        'Rank Difference': comparison['rank_difference'],
        'Entropy Difference': comparison['entropy_difference']
    }

    for ax, (name, value) in zip(axes, metrics.items()):
        ax.bar([name], [value], color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
        ax.set_ylabel('Value')
        ax.set_title(name, fontsize=12)
        ax.tick_params(axis='x', labelsize=10)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value annotation
        ax.text(0, value * 1.05, f'{value:.4f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Saved spectral metrics comparison to {output_path}")