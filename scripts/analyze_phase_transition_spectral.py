"""Experiment V: Spectral analysis of trace covariance phase transition at d≈21.

Computes eigenvalue spectrum of the P×P trace correlation matrix as a function
of dimension d. Identifies spectral signature of the d=21 phase transition.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from scipy.linalg import eigh

PRIMES_25 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
             53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
TRACE_COLS = [f"trace_{p}" for p in PRIMES_25]


def load_traces_by_dim(csv_path: str) -> dict[int, np.ndarray]:
    """Load trace matrix per dimension from LMFDB CSV.

    Returns: dict[dim] -> np.ndarray(n_forms, 25) of trace values.
    """
    df = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(df)} forms from {csv_path}")

    result = {}
    for dim, group in df.groupby("dim"):
        traces = group[TRACE_COLS].values.astype(float)
        result[dim] = traces
        if dim <= 25 or dim % 10 == 0:
            logger.info(f"  dim={dim}: {len(traces)} forms")
    return result


def analyze_dimension(traces: np.ndarray, dim: int) -> dict:
    """Full spectral analysis for one dimension."""
    n_forms, n_primes = traces.shape

    # Sato-Tate normalization: x_p = a_p_trace / (2 * dim * sqrt(p))
    primes_arr = np.array(PRIMES_25[:n_primes])
    sqrt_p = np.sqrt(primes_arr)[np.newaxis, :]
    x = traces / (2.0 * dim * sqrt_p)
    x = np.clip(x, -1.0, 1.0)

    # Cross-form correlation matrix (25 × 25)
    # C[p, q] = Pearson(x_p, x_q) across n_forms
    C = np.corrcoef(x.T)  # shape (25, 25)

    # Handle NaN (constant columns)
    C = np.nan_to_num(C, nan=0.0)

    # Eigenvalues (sorted descending)
    eigenvalues = np.sort(eigh(C)[0])[::-1]
    eigenvalues = np.maximum(eigenvalues, 0)  # numerical stability

    # Spectral properties
    total = eigenvalues.sum()
    eig_normalized = eigenvalues / total if total > 0 else eigenvalues

    # Effective rank (participation ratio)
    eff_rank = 1.0 / np.sum(eig_normalized ** 2) if total > 0 else 0

    # Spectral entropy
    eps = 1e-15
    entropy = -np.sum(eig_normalized * np.log(eig_normalized + eps))
    max_entropy = np.log(n_primes)
    entropy_norm = entropy / max_entropy if max_entropy > 0 else 0

    # Top-k concentration
    top1 = eigenvalues[0] / total if total > 0 else 0
    top3 = eigenvalues[:3].sum() / total if total > 0 else 0
    top5 = eigenvalues[:5].sum() / total if total > 0 else 0

    # Mean off-diagonal correlation (Sprint 4's rho)
    off_diag_mask = ~np.eye(n_primes, dtype=bool)
    mean_rho = C[off_diag_mask].mean()

    return {
        "dim": dim,
        "n_forms": n_forms,
        "eigenvalues": eigenvalues.tolist(),
        "effective_rank": float(eff_rank),
        "spectral_entropy": float(entropy),
        "spectral_entropy_normalized": float(entropy_norm),
        "top1_concentration": float(top1),
        "top3_concentration": float(top3),
        "top5_concentration": float(top5),
        "mean_off_diag_rho": float(mean_rho),
        "spectral_gap": float(eigenvalues[0] - eigenvalues[1]) if len(eigenvalues) > 1 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase transition spectral analysis")
    parser.add_argument("--csv", default="/workspace/data/lmfdb/lmfdb_sql_weight2_ml.csv")
    parser.add_argument("--output", default="/workspace/data/phase_transition_spectral/")
    parser.add_argument("--max-dim", type=int, default=65)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load traces
    traces_by_dim = load_traces_by_dim(args.csv)

    # Analyze each dimension
    results = []
    for dim in sorted(traces_by_dim.keys()):
        if dim > args.max_dim or dim < 1:
            continue
        result = analyze_dimension(traces_by_dim[dim], dim)
        results.append(result)
        logger.info(
            f"d={dim:3d}: n={result['n_forms']:5d} eff_rank={result['effective_rank']:.2f} "
            f"entropy={result['spectral_entropy_normalized']:.3f} "
            f"top1={result['top1_concentration']:.3f} "
            f"rho={result['mean_off_diag_rho']:.4f}"
        )

    # Save
    output_file = output_dir / "spectral_analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved {len(results)} dimension results to {output_file}")

    # Summary table
    print("\n=== Phase Transition Spectral Analysis ===")
    print(f"{'d':>4} {'n':>6} {'eff_rank':>10} {'entropy':>10} {'top1':>8} {'top3':>8} {'rho':>10}")
    for r in results:
        print(
            f"{r['dim']:4d} {r['n_forms']:6d} {r['effective_rank']:10.3f} "
            f"{r['spectral_entropy_normalized']:10.3f} {r['top1_concentration']:8.3f} "
            f"{r['top3_concentration']:8.3f} {r['mean_off_diag_rho']:10.4f}"
        )


if __name__ == "__main__":
    main()
