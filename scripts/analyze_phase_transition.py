from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
import argparse

from investigate_phase_transition import (
    find_phase_transition_boundary,
    estimate_embedding_eigenvalues,
    compute_classical_galois_correlation
)
from recompute_galois_correlations import (
    compute_classical_rho_d,
    load_and_sample_forms
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default='data/lmfdb/lmfdb_sql_weight2_ml.csv')
    parser.add_argument('--min-dim', type=int, default=1)
    parser.add_argument('--max-dim', type=int, default=65)
    parser.add_argument('--min-forms', type=int, default=50)
    args = parser.parse_args()

    logger.info("Loading data...")
    df = pd.read_csv(args.csv)
    df = df[df.dim >= args.min_dim]
    df = df[df.dim <= args.max_dim]

    # Load existing cross-form results
    cross_form = pd.read_csv('data/galois_correlation/cross_form_correlation.csv')

    logger.info("Analyzing phase transition...")
    d_vals = cross_form.dim.values
    rho_vals = cross_form.mean_rho.values

    boundary = find_phase_transition_boundary(d_vals, rho_vals)
    logger.info(f"Phase transition boundary: d={boundary:.1f}")

    # Compute classical correlations for dim=2, 21
    logger.info("Computing classical correlations...")
    rho2_classical = compute_classical_rho_d(
        load_and_sample_forms(Path(args.csv), target_dim=2),
        dim=2,
        num_primes=25
    )
    logger.info(f"Classical ρ_2 = {rho2_classical:.4f}")

    rho21_classical = compute_classical_rho_d(
        load_and_sample_forms(Path(args.csv), target_dim=21),
        dim=21,
        num_primes=25
    )
    logger.info(f"Classical ρ_21 = {rho21_classical:.4f}")

    # Save results
    results = {
        'boundary_d': boundary,
        'classical_rho_2': rho2_classical,
        'classical_rho_21': rho21_classical,
        'cross_form_rho_2': cross_form[cross_form.dim == 2]['mean_rho'].values[0],
        'cross_form_rho_21': cross_form[cross_form.dim == 21]['mean_rho'].values[0],
    }

    results_path = Path('data/galois_correlation/phase_transition_analysis.json')
    import json
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.success(f"Results saved to {results_path}")


if __name__ == '__main__':
    main()