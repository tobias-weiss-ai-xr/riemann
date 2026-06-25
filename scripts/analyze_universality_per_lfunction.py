"""Experiment W: Per-L-function r-statistic analysis.

Tests whether <r> = 0.391 (≈Poisson 0.386) is genuine or a pooling artifact.
Computes r-statistic for EACH individual L-function, then examines the
distribution of individual values.

Reference: Atas et al. arXiv:1212.5611
RMT values: Poisson=0.386, GOE=0.536, GUE=0.599, GSE=0.676
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

ZERO_COLS = [f"z{i}" for i in range(1, 11)]  # z1..z10


def unfold_zeros(zeros: np.ndarray, deg: int = 3) -> np.ndarray:
    """Unfold zeros using polynomial fit to counting function (Weyl law).

    Returns normalized spacings (mean=1).
    """
    if len(zeros) < 4:
        return np.array([])
    n = np.arange(1, len(zeros) + 1, dtype=float)
    coeffs = np.polyfit(zeros, n, deg=deg)
    unfolded = np.polyval(coeffs, zeros)
    spacings = np.diff(unfolded)
    if spacings.mean() <= 0:
        return np.array([])
    return spacings / spacings.mean()


def r_statistic(spacings: np.ndarray) -> float:
    """Compute the r-statistic from nearest-neighbor spacings.

    r_n = min(s_n, s_{n+1}) / max(s_n, s_{n+1})
    Returns mean r in [0,1], or NaN.
    """
    if len(spacings) < 3:
        return float("nan")
    r_vals = np.minimum(spacings[:-1], spacings[1:]) / np.maximum(
        spacings[:-1], spacings[1:]
    )
    # Avoid div-by-zero (degenerate spacings)
    valid = np.isfinite(r_vals)
    if not valid.any():
        return float("nan")
    return float(np.mean(r_vals[valid]))


def analyze_per_lfunction(df: pd.DataFrame) -> dict:
    """Compute r-statistic for each individual L-function, grouped by dim."""
    results_by_dim = {}

    for dim, group in df.groupby("dim"):
        individual_r = []
        for _, row in group.iterrows():
            zeros = row[ZERO_COLS].dropna().values.astype(float)
            if len(zeros) < 5:  # Need at least 5 zeros for 3 spacings
                continue
            zeros = np.sort(zeros)
            spacings = unfold_zeros(zeros)
            if len(spacings) < 3:
                continue
            r = r_statistic(spacings)
            if np.isnan(r):
                continue
            individual_r.append(r)

        if not individual_r:
            continue

        r_arr = np.array(individual_r)
        results_by_dim[int(dim)] = {
            "n_forms": len(r_arr),
            "mean_r": float(r_arr.mean()),
            "median_r": float(np.median(r_arr)),
            "std_r": float(r_arr.std()),
            "sem_r": float(r_arr.std() / np.sqrt(len(r_arr))),
            "fraction_goe_like": float(np.mean(r_arr > 0.50)),
            "fraction_poisson_like": float(np.mean(r_arr < 0.42)),
            "q25": float(np.percentile(r_arr, 25)),
            "q75": float(np.percentile(r_arr, 75)),
        }

    # Pooled (mimics original methodology)
    all_r = []
    for dim_data in results_by_dim.values():
        # We don't have individual values here, recompute for pooled
        pass
    # Pooled r from ALL forms together: unfold each, collect all spacings
    all_spacings = []
    for _, row in df.iterrows():
        zeros = row[ZERO_COLS].dropna().values.astype(float)
        if len(zeros) < 5:
            continue
        zeros = np.sort(zeros)
        sp = unfold_zeros(zeros)
        if len(sp) >= 3:
            all_spacings.extend(sp.tolist())

    pooled_r = r_statistic(np.array(all_spacings)) if all_spacings else float("nan")

    # Mean of individual (proper per-L-function measure)
    all_individual = [
        results_by_dim[d]["mean_r"] for d in sorted(results_by_dim.keys())
    ]
    mean_of_individuals = (
        float(np.mean(all_individual)) if all_individual else float("nan")
    )

    return {
        "by_dim": results_by_dim,
        "pooled_r_from_all_spacings": pooled_r,
        "mean_of_individual_means": mean_of_individuals,
        "reference": {
            "poisson": 0.386,
            "goe": 0.536,
            "gue": 0.599,
            "gse": 0.676,
            "original_pooled_finding": 0.391,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Per-L-function r-statistic")
    parser.add_argument(
        "--input",
        default="/workspace/data/lmfdb/lmfdb_zeros_ml.csv",
        help="CSV with z1..z10 columns",
    )
    parser.add_argument(
        "--output",
        default="/workspace/data/universality_per_lfunction/",
        help="Output directory",
    )
    parser.add_argument("--max-dim", type=int, default=20, help="Max dim to analyze")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading {args.input}")
    df = pd.read_csv(args.input)
    df = df[df["dim"] <= args.max_dim].copy()
    logger.info(f"Loaded {len(df)} forms (dim<= {args.max_dim})")

    result = analyze_per_lfunction(df)

    output_file = output_dir / "per_lfunction_r.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved to {output_file}")

    # Report
    print("\n=== Per-L-function Universality (Experiment W) ===")
    print(
        f"{'dim':>4} {'n_forms':>8} {'⟨r̃⟩':>8} {'±SEM':>8} {'med':>6} "
        f"{'GOE%':>6} {'Pois%':>6}"
    )
    print("-" * 56)
    for d in sorted(result["by_dim"].keys()):
        r = result["by_dim"][d]
        print(
            f"{d:>4} {r['n_forms']:>8} {r['mean_r']:>8.4f} {r['sem_r']:>8.4f} "
            f"{r['median_r']:>6.3f} {r['fraction_goe_like']:>5.0%} "
            f"{r['fraction_poisson_like']:>5.0%}"
        )
    print("-" * 56)
    print(f"Mean of individual ⟨r̃⟩: {result['mean_of_individual_means']:.4f}")
    print(f"Pooled r (all spacings): {result['pooled_r_from_all_spacings']:.4f}")
    print(
        f"Reference: Poisson={result['reference']['poisson']}, "
        f"GOE={result['reference']['goe']}, GUE={result['reference']['gue']}"
    )
    print(f"Original Experiment R pooled finding: {result['reference']['original_pooled_finding']}")


if __name__ == "__main__":
    main()
