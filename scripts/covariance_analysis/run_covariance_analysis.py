#!/usr/bin/env python
"""Main script for covariance structure analysis."""

import numpy as np
import json
from pathlib import Path

from loguru import logger

from covariance_analysis.data_loader import load_lmfdb_correlation_data, separate_by_dimension_boundary
from covariance_analysis.matrix_builder import build_correlation_matrix, subsample_forms
from covariance_analysis.spectral_decomp import compute_full_spectrum, compute_spectral_stats
from covariance_analysis.mode_analysis import extract_top_modes, compare_spectra, identify_driver_modes

def main():
    logger.info("Starting covariance structure analysis")

    # Phase 1: Load and split data
    logger.info("=" * 60)
    logger.info("Phase 1: Loading data and separating by dimension")
    logger.info("=" * 60)

    df = load_lmfdb_correlation_data()
    low_df, high_df = separate_by_dimension_boundary(df, boundary_dim=6)

    # Subsample
    n_samples = 1000
    low_sampled = subsample_forms(low_df, n_samples)
    high_sampled = subsample_forms(high_df, n_samples)

    # Phase 2: Build correlation matrices
    logger.info("=" * 60)
    logger.info("Phase 2: Building correlation matrices")
    logger.info("=" * 60)

    low_corr = build_correlation_matrix(low_sampled)
    high_corr = build_correlation_matrix(high_sampled)

    # Phase 3: Spectral decomposition
    logger.info("=" * 60)
    logger.info("Phase 3: Spectral decomposition")
    logger.info("=" * 60)

    low_evals, low_vecs = compute_full_spectrum(low_corr)
    high_evals, high_vecs = compute_full_spectrum(high_corr)

    low_stats = compute_spectral_stats(low_evals)
    high_stats = compute_spectral_stats(high_evals)

    logger.info(f"Low-dim stats: effective_rank={low_stats['effective_rank']:.2f}, entropy={low_stats['entropy']:.3f}")
    logger.info(f"High-dim stats: effective_rank={high_stats['effective_rank']:.2f}, entropy={high_stats['entropy']:.3f}")

    # Phase 4: Mode extraction and comparison
    logger.info("=" * 60)
    logger.info("Phase 4: Mode analysis and comparison")
    logger.info("=" * 60)

    low_modes = extract_top_modes(low_evals, low_vecs, k=10)
    high_modes = extract_top_modes(high_evals, high_vecs, k=10)

    comparison = compare_spectra(low_evals, high_evals, low_vecs, high_vecs)
    driver_modes = identify_driver_modes(
        [m['eigenvector'] for m in low_modes],
        [m['eigenvector'] for m in high_modes],
        top_k=10,
        threshold=0.3
    )

    # Phase 5: Save results
    logger.info("=" * 60)
    logger.info("Phase 5: Saving results")
    logger.info("=" * 60)

    output_dir = Path("data/covariance_analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save low-dim spectrum
    low_spectrum = {
        'eigenvalues': low_evals.tolist(),
        'eigenvectors': low_vecs.tolist(),
        'spectral_stats': low_stats,
        'top_modes': low_modes
    }
    (output_dir / "low_dim_spectrum.json").write_text(json.dumps(low_spectrum, indent=2))

    # Save high-dim spectrum
    high_spectrum = {
        'eigenvalues': high_evals.tolist(),
        'eigenvectors': high_vecs.tolist(),
        'spectral_stats': high_stats,
        'top_modes': high_modes
    }
    (output_dir / "high_dim_spectrum.json").write_text(json.dumps(high_spectrum, indent=2))

    # Save comparison
    comparison['driver_modes'] = driver_modes
    comparison['rank_difference'] = float(abs(low_stats['effective_rank'] - high_stats['effective_rank']))
    comparison['entropy_difference'] = float(abs(low_stats['entropy'] - high_stats['entropy']))

    (output_dir / "spectral_comparison.json").write_text(json.dumps(comparison, indent=2))

    # Summary
    logger.info("=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"KL divergence between spectra: {comparison['kl_divergence']:.4f}")
    logger.info(f"Wasserstein distance: {comparison['wasserstein_distance']:.4f}")
    logger.info(f"Rank difference: {comparison['rank_difference']:.2f}")
    logger.info(f"Entropy difference: {comparison['entropy_difference']:.4f}")
    logger.info(f"Driver modes identified: {driver_modes}")

    if len(driver_modes) >= 2:
        logger.info("SUCCESS: Multiple significant spectral modes differ between classes")
    elif len(driver_modes) == 1:
        logger.info("WARNING: Only one significant spectral mode differs")
    else:
        logger.info("NO DIFFERENCE: No significant spectral mode differences found")

if __name__ == "__main__":
    main()