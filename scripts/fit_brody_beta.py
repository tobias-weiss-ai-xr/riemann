"""
Fit Brody distribution P(s) = (beta+1) * a * s^beta * exp(-a * s^(beta+1))
to L-function zero spacings. Estimates the repulsion parameter beta
with bootstrap confidence intervals.

beta = 0 → Poisson (no repulsion)
beta = 1 → GOE (linear repulsion)
beta = 2 → GUE (quadratic repulsion)

Intermediate values quantify how far the zeros are from any standard class.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats, optimize
from scipy.special import gamma as gamma_func
from loguru import logger

# ── Parameters ────────────────────────────────────────────────────────────────

N_LEVELS = 10
N_SPACINGS_PER = 9
N_BOOTSTRAP = 2000           # Bootstrap iterations for CIs

OUTPUT_DIR = Path("data/spectral_rigidity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Brody Distribution ────────────────────────────────────────────────────────

def brody_cdf(s, beta):
    """Brody CDF: F(s) = 1 - exp(-a * s^(beta+1))."""
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    return 1 - np.exp(-a * s ** (beta + 1))


def brody_pdf(s, beta):
    """Brody PDF."""
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    return (beta + 1) * a * s**beta * np.exp(-a * s ** (beta + 1))


def neg_log_likelihood(beta, spacings):
    """Negative log-likelihood of spacings under Brody(beta)."""
    if beta < 0 or beta > 3:
        return 1e12
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    log_lik = np.log(beta + 1) + np.log(a) + beta * np.log(spacings) - a * spacings ** (beta + 1)
    return -np.sum(log_lik)


def fit_brody_mle(spacings) -> tuple[float, float, float]:
    """
    Fit Brody beta via MLE on the PDF.
    Returns (beta_mle, ks_stat, n_spacings).
    """
    # Remove any remaining NaNs or zeros/infs
    s = spacings[np.isfinite(spacings) & (spacings > 0)]

    # MLE
    result = optimize.minimize_scalar(neg_log_likelihood, args=(s,), bounds=(0, 3), method="bounded")
    beta_mle = result.x

    # KS stat against fitted CDF
    ks = stats.kstest(s, lambda x: brody_cdf(x, beta_mle))[0]

    return beta_mle, ks, len(s)


def fit_brody_ks_min(spacings) -> float:
    """
    Alternative: find beta that minimizes KS distance to Brody CDF.
    Used as a consistency check.
    """
    s = spacings[np.isfinite(spacings) & (spacings > 0)]
    ecdf = np.sort(s)
    n = len(ecdf)

    def ks_brody(beta):
        return np.max(np.abs(np.arange(1, n + 1) / n - brody_cdf(ecdf, beta)))

    result = optimize.minimize_scalar(ks_brody, bounds=(0, 3), method="bounded")
    return result.x, result.fun


def bootstrap_ci(spacings, n_iter=N_BOOTSTRAP, alpha=0.05) -> tuple[float, float, float, list[float]]:
    """
    Bootstrap the MLE beta estimate.
    Returns (beta_mean, beta_lower, beta_upper, all_samples).
    """
    s = spacings[np.isfinite(spacings) & (spacings > 0)]
    n = len(s)
    betas = []
    rng = np.random.default_rng(42)

    for i in range(n_iter):
        boot_sample = rng.choice(s, size=n, replace=True)
        try:
            result = optimize.minimize_scalar(neg_log_likelihood, args=(boot_sample,), bounds=(0, 3), method="bounded")
            betas.append(result.x)
        except Exception:
            continue
        if (i + 1) % 500 == 0:
            logger.info(f"  Bootstrap iteration {i + 1}/{n_iter}")

    betas = np.array(betas)
    beta_mean = np.mean(betas)
    beta_lower = np.percentile(betas, 100 * alpha / 2)
    beta_upper = np.percentile(betas, 100 * (1 - alpha / 2))
    return beta_mean, beta_lower, beta_upper, betas.tolist()


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_spacings(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Extract unfolded spacings from DataFrame, returning per-group arrays."""
    zero_cols = [f"z{k}" for k in range(1, N_LEVELS + 1)]
    df = df.dropna(subset=zero_cols)
    zeros = df[zero_cols].values  # (N_forms, 10)
    spacings_raw = np.diff(zeros, axis=1)  # (N_forms, 9)

    # Per-form mean-divide unfolding (matching MC tests exactly)
    form_means = np.nanmean(spacings_raw, axis=1, keepdims=True)
    unfolded = spacings_raw / form_means

    dims = df["dim"].values.astype(int)
    ranks = df["analytic_rank"].values.astype(int)
    d1 = dims == 1
    d2 = dims >= 2
    r0 = ranks == 0
    r1 = ranks == 1

    result = {}
    result["all"] = unfolded[np.isfinite(unfolded)]
    result["dim_1"] = unfolded[d1][np.isfinite(unfolded[d1])]
    result["dim_ge2"] = unfolded[d2][np.isfinite(unfolded[d2])]
    result["rank_0"] = unfolded[r0][np.isfinite(unfolded[r0])]
    result["rank_1"] = unfolded[r1][np.isfinite(unfolded[r1])]
    result["dim_2"] = unfolded[dims == 2][np.isfinite(unfolded[dims == 2])]
    result["dim_3"] = unfolded[dims == 3][np.isfinite(unfolded[dims == 3])]
    result["dim_4"] = unfolded[dims == 4][np.isfinite(unfolded[dims == 4])]
    result["dim_5"] = unfolded[dims == 5][np.isfinite(unfolded[dims == 5])]
    result["dim_6plus"] = unfolded[dims >= 6][np.isfinite(unfolded[dims >= 6])]

    for name, s in result.items():
        s_clean = s[(~np.isnan(s)) & (s > 0) & (s < 10)]
        result[name] = s_clean
        logger.info(f"  {name}: {len(s_clean):,} spacings (after filter)")

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("Loading LMFDB data...")
    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    logger.info(f"Loaded {len(df)} forms")

    spacings_dict = load_spacings(df)
    logger.info(f"Groups: {list(spacings_dict.keys())}")
    for name, s in spacings_dict.items():
        logger.info(f"  {name}: {len(s):>8,} spacings")

    # ── Fit Brody to each group ────────────────────────────────────────────────
    results = {}
    for name, spacings in spacings_dict.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Fitting Brody to: {name} ({len(spacings):,} spacings)")
        logger.info(f"{'='*60}")

        t0 = time.time()

        # MLE fit
        beta_mle, ks_fit, n = fit_brody_mle(spacings)

        # KS-min fit (consistency check)
        beta_ksmin, ks_min_val = fit_brody_ks_min(spacings)

        # Bootstrap CIs
        beta_mean, beta_lo, beta_hi, boot_samples = bootstrap_ci(spacings)

        elapsed = time.time() - t0

        # KS against Poisson (beta=0) and GOE (beta=1) for reference
        ks_poisson = stats.kstest(
            spacings[np.isfinite(spacings) & (spacings > 0)],
            lambda x: brody_cdf(x, 0)
        )[0]
        ks_goe = stats.kstest(
            spacings[np.isfinite(spacings) & (spacings > 0)],
            lambda x: brody_cdf(x, 1)
        )[0]
        ks_gue = stats.kstest(
            spacings[np.isfinite(spacings) & (spacings > 0)],
            lambda x: brody_cdf(x, 2)
        )[0]

        entry = {
            "group": name,
            "n_spacings": n,
            "beta_mle": float(f"{beta_mle:.4f}"),
            "ks_brody_fit": float(f"{ks_fit:.4f}"),
            "beta_ks_minimization": float(f"{beta_ksmin:.4f}"),
            "ks_at_ks_min": float(f"{ks_min_val:.4f}"),
            "beta_bootstrap_mean": float(f"{beta_mean:.4f}"),
            "beta_95_ci_lower": float(f"{beta_lo:.4f}"),
            "beta_95_ci_upper": float(f"{beta_hi:.4f}"),
            "ks_vs_poisson_beta0": float(f"{ks_poisson:.4f}"),
            "ks_vs_goe_beta1": float(f"{ks_goe:.4f}"),
            "ks_vs_gue_beta2": float(f"{ks_gue:.4f}"),
            "elapsed_sec": float(f"{elapsed:.1f}"),
        }
        results[name] = entry

        logger.info(f"  beta MLE:            {beta_mle:.4f}")
        logger.info(f"  beta KS-min:         {beta_ksmin:.4f}")
        logger.info(f"  beta bootstrap mean: {beta_mean:.4f}")
        logger.info(f"  beta 95% CI:         [{beta_lo:.4f}, {beta_hi:.4f}]")
        logger.info(f"  KS(fitted Brody):    {ks_fit:.4f}")
        logger.info(f"  KS(Poisson β=0):     {ks_poisson:.4f}")
        logger.info(f"  KS(GOE β=1):         {ks_goe:.4f}")
        logger.info(f"  KS(GUE β=2):         {ks_gue:.4f}")
        logger.info(f"  Elapsed:             {elapsed:.1f}s")

    # ── Save ───────────────────────────────────────────────────────────────────
    output_path = OUTPUT_DIR / "brody_fit_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to {output_path}")

    # ── Summary table ──────────────────────────────────────────────────────────
    logger.info(f"\n{'='*80}")
    logger.info(f"{'Group':<12} {'β_MLE':<8} {'β_mean':<8} {'95% CI':<18} {'KS(fit)':<8} {'KS(β=0)':<8} {'KS(β=1)':<8} {'KS(β=2)':<8}")
    logger.info(f"{'-'*80}")
    for name, r in results.items():
        ci = f"[{r['beta_95_ci_lower']}, {r['beta_95_ci_upper']}]"
        logger.info(f"{name:<12} {r['beta_mle']:<8} {r['beta_bootstrap_mean']:<8} {ci:<18} {r['ks_brody_fit']:<8} {r['ks_vs_poisson_beta0']:<8} {r['ks_vs_goe_beta1']:<8} {r['ks_vs_gue_beta2']:<8}")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    main()
