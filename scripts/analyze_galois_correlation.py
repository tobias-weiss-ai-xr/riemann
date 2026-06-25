#!/usr/bin/env python3
"""
Analyze Hecke trace covariance structure across the 200K LMFDB newform dataset.

Computes the trace covariance matrix C_{p,q} = cov(trace_p, trace_q) for each form,
then analyzes its spectral properties (eigenvalues, rank ratio, mean correlation).
Stratifies results by dimension, level range, conductor, and prime window.

This formalizes and extends the ρ₂ = -0.607 Galois anti-correlation finding
from Experiment F (53K dataset) to the full 200K dataset with deep stratification.

Usage:
    python scripts/analyze_galois_correlation.py
    python scripts/analyze_galois_correlation.py --min-dim 2 --max-primes 50
    python scripts/analyze_galois_correlation.py --level-bins "100,500,2000"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = DATA_DIR / "galois_correlation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Primes up to 541 (100th prime) — Sato-Tate applies only to prime-index eigenvalues
PRIMES_UP_TO_100 = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71,
    73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151,
    157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229, 233,
    239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313, 317,
    331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409, 419,
    421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499, 503,
    509, 521, 523, 541,
]
# Only first 25 primes <= 100 for Sato-Tate analysis
PRIMES_LE_100 = [p for p in PRIMES_UP_TO_100 if p <= 100]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hecke trace covariance analysis")
    parser.add_argument("--data", type=str, default="data/lmfdb/lmfdb_sql_weight2_ml.csv",
                        help="Path to ML-ready CSV")
    parser.add_argument("--min-dim", type=int, default=1,
                        help="Minimum dimension to include (default: 1)")
    parser.add_argument("--max-primes", type=int, default=25,
                        help="Max number of prime indices to use (default: 25)")
    parser.add_argument("--level-bins", type=str, default="100,500,2000",
                        help="Comma-separated level bin edges (default: 100,500,2000)")
    parser.add_argument("--exclude-cm", action="store_true", default=True,
                        help="Exclude CM forms (default: True)")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR),
                        help="Output directory")
    return parser.parse_args()


def load_and_filter(args: argparse.Namespace) -> tuple[pd.DataFrame, list[int], list[str]]:
    """Load 200K CSV and apply dimension/CM/level filters."""
    logger.info(f"Loading data from {args.data}...")
    df = pd.read_csv(args.data)
    logger.info(f"Loaded {len(df):,} forms with {len(df.columns)} columns")

    # Filter CM forms
    if args.exclude_cm:
        n_before = len(df)
        df = df[df["is_cm"] == 0].copy()
        logger.info(f"Excluded CM: {n_before:,} -> {len(df):,} forms")

    # Filter by dimension
    n_before = len(df)
    df = df[df["dim"] >= args.min_dim].copy()
    logger.info(f"Filter dim >= {args.min_dim}: {n_before:,} -> {len(df):,} forms")

    # Report dimension distribution
    dim_counts = df["dim"].value_counts().sort_index()
    logger.info("Dimension distribution:")
    for dim, count in dim_counts.items():
        logger.info(f"  dim={dim}: {count:,} forms ({100 * count / len(df):.1f}%)")

    # Build trace column list
    primes = PRIMES_LE_100[:args.max_primes]
    trace_cols = [f"trace_{p}" for p in primes]
    missing = [c for c in trace_cols if c not in df.columns]
    if missing:
        logger.error(f"Missing trace columns: {missing}")
        raise ValueError(f"CSV missing columns: {missing}")

    return df, primes, trace_cols


def compute_covariance_spectrum(
    traces: np.ndarray, dim: int, n_primes: int
) -> dict[str, float]:
    """
    Compute the Hecke trace outer-product structure for one form.

    For dim=1, traces are scalar eigenvalues and the outer product x @ x^T has rank 1.
    For dim>=2, traces are sums of conjugate pairs, giving a richer structure.
    We use the normalized outer-product correlation matrix as a form-level signature.

    Args:
        traces: (n_primes,) array of Hecke traces at prime indices for one form
        dim: dimension of the Hecke eigenvalue field
        n_primes: number of prime indices used

    Returns:
        Dict with: mean_corr, rank_ratio, top1_frac, spectral_entropy, cond_number
    """
    if n_primes < 3:
        return {
            "mean_corr": np.nan, "rank_ratio": np.nan,
            "top1_frac": np.nan, "spectral_entropy": np.nan,
            "cond_number": np.nan,
        }

    # Normalize traces by Hasse bound: x_p = a_p / (2*sqrt(p)) in [-1, 1]
    sqrt_p = np.sqrt(np.array(PRIMES_LE_100[:n_primes], dtype=float))
    x = traces / (2.0 * sqrt_p)
    x = np.clip(x, -1.0, 1.0)

    if np.std(x) < 1e-10:
        return {
            "mean_corr": 0.0, "rank_ratio": 1.0,
            "top1_frac": 1.0, "spectral_entropy": 0.0, "cond_number": 1.0,
        }

    # Outer-product correlation matrix: C[i,j] = x_i * x_j
    # This has rank 1 for dim=1 (pure scalar eigenvalues)
    n = len(x)
    outer = np.outer(x, x)
    eigenvalues = np.linalg.eigvalsh(outer)
    eigenvalues = np.sort(np.abs(eigenvalues))[::-1]

    total = np.sum(eigenvalues)
    if total < 1e-10:
        return {
            "mean_corr": 0.0, "rank_ratio": 1.0,
            "top1_frac": 1.0, "spectral_entropy": 0.0, "cond_number": 1.0,
        }

    # Mean off-diagonal of the outer product (analogous to ρ for single form)
    mask = ~np.eye(n, dtype=bool)
    mean_offdiag = np.mean(outer[mask])

    # Rank-d concentration
    top_d_sum = np.sum(eigenvalues[:min(dim, n)])

    # Spectral entropy
    p = eigenvalues / total
    p = p[p > 1e-15]
    spec_ent = -np.sum(p * np.log(p))

    return {
        "mean_corr": float(mean_offdiag),
        "rank_ratio": float(top_d_sum / total),
        "top1_frac": float(eigenvalues[0] / total),
        "spectral_entropy": float(spec_ent),
        "cond_number": float(eigenvalues[0] / eigenvalues[-1]) if eigenvalues[-1] > 1e-10 else float("inf"),
    }


def compute_all_spectra(
    df: pd.DataFrame, trace_cols: list[str], n_primes: int
) -> pd.DataFrame:
    """Compute covariance spectra for all forms. Returns augmented DataFrame."""
    n_forms = len(df)
    records = []

    for i in range(n_forms):
        row = df.iloc[i]
        dim = int(row["dim"])
        traces = np.array([row[c] for c in trace_cols[:n_primes]], dtype=float)

        spec = compute_covariance_spectrum(traces, dim, n_primes)
        record = {
            "label": row["label"], "dim": dim, "level": row["level"],
            "analytic_conductor": row.get("analytic_conductor", np.nan),
        }
        record.update(spec)
        records.append(record)

        if (i + 1) % 10000 == 0:
            logger.info(f"  Computed {i + 1}/{n_forms} forms")

    logger.info(f"  Computed all {n_forms} forms")
    return pd.DataFrame(records)


def compute_cross_form_correlation(
    df: pd.DataFrame, trace_cols: list[str], n_primes: int
) -> dict[int, dict[str, float]]:
    """
    Compute cross-form trace correlation matrix and extract rho_d analogues.

    For each dimension d, compute the PxP correlation matrix of traces
    across all dim=d forms (P = number of prime indices).
    The off-diagonal mean of this matrix is rho_d: how much do traces at
    different primes co-vary across forms of the same dimension?
    """
    results = {}

    for dim in sorted(df["dim"].unique()):
        subset = df[df["dim"] == dim]
        if len(subset) < 50:
            logger.warning(f"  Skipping dim={dim}: only {len(subset)} forms")
            continue

        traces = subset[trace_cols[:n_primes]].values  # (n_forms, n_primes)
        n_forms_d = len(traces)

        # Correlation matrix across forms: C[p,q] = corr(trace_p, trace_q) across forms
        corr_matrix = np.corrcoef(traces.T)  # (n_primes, n_primes)

        # Mean off-diagonal correlation = rho_d analogue
        mask = ~np.eye(n_primes, dtype=bool)
        mean_rho = np.mean(corr_matrix[mask])

        # Eigenvalues of the cross-form correlation matrix
        eigenvalues = np.linalg.eigvalsh(corr_matrix)
        eigenvalues = np.sort(eigenvalues)[::-1]

        # Rank-d concentration: how much of the variance is in top-d components?
        total_var = np.sum(np.abs(eigenvalues))
        top_d_var = np.sum(np.abs(eigenvalues[:min(dim, n_primes)]))

        results[dim] = {
            "n_forms": n_forms_d,
            "mean_rho": float(mean_rho),
            "rho_std": float(np.std(corr_matrix[mask])),
            "top1_eigenvalue": float(eigenvalues[0]),
            "rank_d_concentration": float(top_d_var / total_var) if total_var > 1e-10 else 1.0,
            "spectral_entropy": float(-np.sum(
                (eigenvalues / total_var) * np.log(np.abs(eigenvalues / total_var) + 1e-15)
            )) if total_var > 1e-10 else 0.0,
        }

        logger.info(
            f"  dim={dim}: n={n_forms_d:,}, rho={mean_rho:.4f} +/- {results[dim]['rho_std']:.4f}, "
            f"top1={eigenvalues[0]:.4f}, rank_conc={results[dim]['rank_d_concentration']:.4f}"
        )

    return results


def stratified_analysis(
    df: pd.DataFrame,
    trace_cols: list[str],
    n_primes: int,
    level_bins: list[int],
) -> dict[str, pd.DataFrame]:
    """
    Stratify cross-form correlation by level range, conductor, and prime window.

    Returns dict of {stratification_key: DataFrame} with per-stratum rho_d results.
    """
    results = {}

    # 1. Stratify by level range
    level_edges = [0] + level_bins + [float("inf")]
    level_labels = []
    for i in range(len(level_edges) - 1):
        lo, hi = level_edges[i], level_edges[i + 1]
        if hi == float("inf"):
            level_labels.append(f"level_{lo}+")
        else:
            level_labels.append(f"level_{lo}-{hi}")

    df_copy = df.copy()
    df_copy["level_bin"] = pd.cut(
        df_copy["level"], bins=level_edges, labels=level_labels, right=False
    )

    for bin_label in level_labels:
        subset = df_copy[df_copy["level_bin"] == bin_label]
        if len(subset) < 50:
            logger.warning(f"  Skipping {bin_label}: only {len(subset)} forms")
            continue

        logger.info(f"\n--- Level bin: {bin_label} ({len(subset):,} forms) ---")
        corr = compute_cross_form_correlation(subset, trace_cols, n_primes)
        corr_df = pd.DataFrame([{"dim": d, **v} for d, v in corr.items()])
        results[f"level_{bin_label}"] = corr_df
        logger.info(f"  Saved {len(corr_df)} dimension groups")

    # 2. Stratify by conductor (log-scale bins)
    if "analytic_conductor" in df_copy.columns:
        df_copy["log_conductor"] = np.log10(df_copy["analytic_conductor"].clip(lower=1))
        cond_bins = [0, 2, 3, 4, 5, float("inf")]
        cond_labels = ["cond_1-100", "cond_100-1K", "cond_1K-10K", "cond_10K-100K", "cond_100K+"]
        df_copy["cond_bin"] = pd.cut(df_copy["log_conductor"], bins=cond_bins, labels=cond_labels, right=False)

        for bin_label in cond_labels:
            subset = df_copy[df_copy["cond_bin"] == bin_label]
            if len(subset) < 50:
                continue
            logger.info(f"\n--- Conductor bin: {bin_label} ({len(subset):,} forms) ---")
            corr = compute_cross_form_correlation(subset, trace_cols, n_primes)
            corr_df = pd.DataFrame([{"dim": d, **v} for d, v in corr.items()])
            results[f"conductor_{bin_label}"] = corr_df

    # 3. Stratify by prime window
    for n_p in [10, 25, 50]:
        if n_p > n_primes:
            continue
        logger.info(f"\n--- Prime window: first {n_p} primes ---")
        corr = compute_cross_form_correlation(df_copy, trace_cols, n_p)
        corr_df = pd.DataFrame([{"dim": d, **v} for d, v in corr.items()])
        results[f"primes_{n_p}"] = corr_df

    return results


def plot_results(
    cross_df: pd.DataFrame,
    strata: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Generate publication-quality plots."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # --- Plot 1: rho_d vs dimension (the dilution law) ---
    fig, ax = plt.subplots(figsize=(10, 6))
    dims = cross_df["dim"].values.astype(float)
    rhos = cross_df["mean_rho"].values.astype(float)
    rho_errs = cross_df["rho_std"].values.astype(float)

    ax.errorbar(dims, rhos, yerr=rho_errs, fmt="o", capsize=4, markersize=6, color="steelblue")
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Dimension (d)", fontsize=12)
    ax.set_ylabel("Mean cross-form correlation $\\rho_d$", fontsize=12)
    ax.set_title("Hecke Trace Cross-Form Correlation vs. Dimension", fontsize=14)
    ax.set_xscale("log")
    ax.grid(True, alpha=0.3)

    # Fit power law for dim >= 2
    mask = dims >= 2
    if np.sum(mask) >= 3:
        from scipy.optimize import curve_fit

        def power_law(x, a, alpha):
            return a * x ** alpha

        try:
            popt, _ = curve_fit(power_law, dims[mask], rhos[mask], p0=[-0.6, -1.3])
            x_fit = np.linspace(dims[mask].min(), dims[mask].max(), 100)
            ax.plot(x_fit, power_law(x_fit, *popt), "r--", linewidth=2,
                    label=f"$\\rho \\propto d^{{{popt[1]:.2f}}}$ (a={popt[0]:.3f})")
            ax.legend(fontsize=11)
            logger.info(f"  Dilution law fit: rho = {popt[0]:.4f} * d^{{{popt[1]:.3f}}}")
        except Exception as e:
            logger.warning(f"  Power law fit failed: {e}")

    plt.tight_layout()
    plt.savefig(output_dir / "rho_vs_dimension.png", dpi=200, bbox_inches="tight")
    plt.close()
    logger.info("  Saved rho_vs_dimension.png")

    # --- Plot 2: Stratified rho by level range ---
    level_strata = {k: v for k, v in strata.items() if k.startswith("level_")}
    if level_strata:
        fig, axes = plt.subplots(1, len(level_strata), figsize=(5 * len(level_strata), 5),
                                sharey=True)
        if len(level_strata) == 1:
            axes = [axes]

        for idx, (key, sdf) in enumerate(sorted(level_strata.items())):
            ax = axes[idx]
            d = sdf["dim"].values.astype(float)
            r = sdf["mean_rho"].values.astype(float)
            ax.plot(d, r, "o-", markersize=5, color=f"C{idx}")
            ax.axhline(0, color="gray", linestyle="--", alpha=0.3)
            ax.set_title(key.replace("level_", "Level "), fontsize=11)
            ax.set_xlabel("dim")
            if idx == 0:
                ax.set_ylabel("$\\rho_d$")
            ax.grid(True, alpha=0.3)

        plt.suptitle("Cross-Form Correlation by Level Range", fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig(output_dir / "rho_by_level.png", dpi=200, bbox_inches="tight")
        plt.close()
        logger.info("  Saved rho_by_level.png")

    # --- Plot 3: Rank concentration vs dimension ---
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(cross_df["dim"].astype(str), cross_df["rank_d_concentration"],
           color="steelblue", alpha=0.7)
    ax.axhline(1.0, color="gray", linestyle="--", alpha=0.3)
    ax.set_xlabel("Dimension (d)")
    ax.set_ylabel("Rank-$d$ Concentration")
    ax.set_title("Covariance Rank-$d$ Concentration vs Dimension", fontsize=14)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(output_dir / "rank_concentration.png", dpi=200, bbox_inches="tight")
    plt.close()
    logger.info("  Saved rank_concentration.png")

    logger.info("All plots saved.")


def generate_latex_tables(
    cross_df: pd.DataFrame,
    strata: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    """Generate LaTeX tables for the paper."""

    # Table 1: Overall rho_d by dimension
    latex = "\\begin{table}[h]\n\\centering\n"
    latex += "\\caption{Cross-form Hecke trace correlation $\\rho_d$ by dimension.}\n"
    latex += "\\label{tab:galois-correlation}\n"
    latex += "\\begin{tabular}{rrrrr}\n\\toprule\n"
    latex += "$d$ & $N$ & $\\rho_d$ & $\\sigma_{\\rho}$ & Rank-$d$ Conc. \\\\\n"
    latex += "\\midrule\n"

    for _, row in cross_df.iterrows():
        latex += (f"{int(row['dim'])} & {int(row['n_forms']):,} & "
                  f"{row['mean_rho']:.4f} & {row['rho_std']:.4f} & "
                  f"{row['rank_d_concentration']:.4f} \\\\\n")

    latex += "\\bottomrule\n\\end{tabular}\n\\end{table}\n"

    path = output_dir / "table_galois_correlation.tex"
    path.write_text(latex, encoding="utf-8")
    logger.info(f"  Saved {path}")

    # Table 2: Stratified summary for dim=2
    latex2 = "\\begin{table}[h]\n\\centering\n"
    latex2 += "\\caption{Stratified $\\rho_2$ by level range and conductor.}\n"
    latex2 += "\\label{tab:galois-stratified}\n"
    latex2 += "\\begin{tabular}{lrr}\n\\toprule\n"
    latex2 += "Stratum & $N$ & $\\rho_2$ \\\\\n\\midrule\n"

    for key, sdf in strata.items():
        dim2 = sdf[sdf["dim"] == 2]
        if len(dim2) == 0:
            continue
        rho2 = dim2.iloc[0]["mean_rho"]
        n = int(dim2.iloc[0]["n_forms"])
        label = key.replace("_", " ").title()
        latex2 += f"{label} & {n:,} & {rho2:.4f} \\\\\n"

    latex2 += "\\bottomrule\n\\end{tabular}\n\\end{table}\n"

    path2 = output_dir / "table_stratified.tex"
    path2.write_text(latex2, encoding="utf-8")
    logger.info(f"  Saved {path2}")


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Hecke Trace Covariance Analysis")
    logger.info("=" * 60)
    logger.info(f"Data: {args.data}")
    logger.info(f"Min dim: {args.min_dim}, Max primes: {args.max_primes}")
    logger.info(f"Level bins: {args.level_bins}")

    # Load and filter
    df, primes, trace_cols = load_and_filter(args)
    logger.info(f"Analysis ready: {len(df):,} forms, {len(primes)} prime indices")

    # Per-form covariance spectra
    logger.info("\nComputing per-form covariance spectra...")
    spectra = compute_all_spectra(df, trace_cols, len(primes))
    spectra.to_csv(OUTPUT_DIR / "covariance_spectra.csv", index=False)
    logger.info(f"Saved spectra to {OUTPUT_DIR / 'covariance_spectra.csv'}")

    # Cross-form Galois correlation (the true rho_d)
    logger.info("\nComputing cross-form Galois correlations...")
    cross_corr = compute_cross_form_correlation(df, trace_cols, len(primes))

    cross_df = pd.DataFrame([
        {"dim": dim, **vals} for dim, vals in cross_corr.items()
    ])
    cross_df.to_csv(OUTPUT_DIR / "cross_form_correlation.csv", index=False)
    logger.info(f"Saved to {OUTPUT_DIR / 'cross_form_correlation.csv'}")

    # Stratified analysis
    level_bins = [int(b) for b in args.level_bins.split(",")]
    logger.info(f"\nStratified analysis (level bins: {level_bins})...")
    strata = stratified_analysis(df, trace_cols, len(primes), level_bins)

    for key, strat_df in strata.items():
        path = OUTPUT_DIR / f"stratified_{key}.csv"
        strat_df.to_csv(path, index=False)
        logger.info(f"  Saved {path}")

    # Combined stratified summary
    all_strata = []
    for key, strat_df in strata.items():
        strat_df_copy = strat_df.copy()
        strat_df_copy["stratification"] = key
        all_strata.append(strat_df_copy)
    combined = pd.concat(all_strata, ignore_index=True)
    combined.to_csv(OUTPUT_DIR / "stratified_summary.csv", index=False)
    logger.info(f"Saved combined stratified summary")

    # Visualization
    logger.info("\nGenerating plots...")
    plot_results(cross_df, strata, OUTPUT_DIR)

    # LaTeX tables
    logger.info("Generating LaTeX tables...")
    generate_latex_tables(cross_df, strata, OUTPUT_DIR)

    logger.info(f"\nDone! All results saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
