"""
Item 1: Sub-split dim_ge2 into dim=2, dim=3, dim=4+ and fit Brody to each.

This extends the pooled dim_ge2 result by checking whether the
near-Poisson (β≈0.24) behavior is uniform across dimension subgroups
or shows a gradient from dim=2 → dim=4+.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats, optimize
from scipy.special import gamma as gamma_func

N_LEVELS = 10
N_BOOTSTRAP = 2000
OUTPUT_DIR = Path("data/spectral_rigidity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def brody_cdf(s, beta):
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    return 1 - np.exp(-a * s ** (beta + 1))


def neg_log_likelihood(beta, spacings):
    if beta < 0 or beta > 3:
        return 1e12
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    log_lik = np.log(beta + 1) + np.log(a) + beta * np.log(spacings) - a * spacings ** (beta + 1)
    return -np.sum(log_lik)


def fit_brody_mle(spacings):
    s = spacings[np.isfinite(spacings) & (spacings > 0)]
    result = optimize.minimize_scalar(neg_log_likelihood, args=(s,), bounds=(0, 3), method="bounded")
    beta_mle = result.x
    ks = stats.kstest(s, lambda x: brody_cdf(x, beta_mle))[0]
    return beta_mle, ks, len(s)


def bootstrap_ci(spacings, n_iter=N_BOOTSTRAP):
    s = spacings[np.isfinite(spacings) & (spacings > 0)]
    n = len(s)
    betas = []
    rng = np.random.default_rng(42)
    for i in range(n_iter):
        boot_sample = rng.choice(s, size=n, replace=True)
        try:
            res = optimize.minimize_scalar(neg_log_likelihood, args=(boot_sample,), bounds=(0, 3), method="bounded")
            betas.append(res.x)
        except Exception:
            continue
    betas = np.array(betas)
    return float(np.mean(betas)), float(np.percentile(betas, 2.5)), float(np.percentile(betas, 97.5))


def main():
    logger.info("Loading LMFDB data...")
    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    logger.info(f"Loaded {len(df)} forms")

    zero_cols = [f"z{k}" for k in range(1, N_LEVELS + 1)]
    df = df.dropna(subset=zero_cols)
    zeros = df[zero_cols].values
    spacings_raw = np.diff(zeros, axis=1)
    form_means = np.nanmean(spacings_raw, axis=1, keepdims=True)
    unfolded = spacings_raw / form_means

    dims = df["dim"].values.astype(int)

    groups = {
        "dim_1": dims == 1,
        "dim_2": dims == 2,
        "dim_3": dims == 3,
        "dim_4": dims == 4,
        "dim_5plus": dims >= 5,
    }

    results = {}
    for name, mask in groups.items():
        group_spacings = unfolded[mask][np.isfinite(unfolded[mask])]
        group_spacings = group_spacings[(~np.isnan(group_spacings)) & (group_spacings > 0) & (group_spacings < 10)]
        n_forms = int(mask.sum())
        logger.info(f"\n{'='*60}")
        logger.info(f"Fitting Brody to: {name} ({n_forms} forms, {len(group_spacings):,} spacings)")

        t0 = time.time()
        beta_mle, ks_fit, n = fit_brody_mle(group_spacings)
        beta_mean, beta_lo, beta_hi = bootstrap_ci(group_spacings)
        elapsed = time.time() - t0

        ks_poisson = stats.kstest(group_spacings, lambda x: brody_cdf(x, 0))[0]
        ks_goe = stats.kstest(group_spacings, lambda x: brody_cdf(x, 1))[0]
        ks_gue = stats.kstest(group_spacings, lambda x: brody_cdf(x, 2))[0]

        entry = {
            "group": name,
            "n_forms": n_forms,
            "n_spacings": n,
            "beta_mle": float(f"{beta_mle:.4f}"),
            "beta_bootstrap_mean": float(f"{beta_mean:.4f}"),
            "beta_95_ci_lower": float(f"{beta_lo:.4f}"),
            "beta_95_ci_upper": float(f"{beta_hi:.4f}"),
            "ks_brody_fit": float(f"{ks_fit:.4f}"),
            "ks_vs_poisson_beta0": float(f"{ks_poisson:.4f}"),
            "ks_vs_goe_beta1": float(f"{ks_goe:.4f}"),
            "ks_vs_gue_beta2": float(f"{ks_gue:.4f}"),
            "elapsed_sec": float(f"{elapsed:.1f}"),
        }
        results[name] = entry

        logger.info(f"  β MLE:     {beta_mle:.4f}")
        logger.info(f"  β bootstrap: {beta_mean:.4f}  [{beta_lo:.4f}, {beta_hi:.4f}]")
        logger.info(f"  KS vs β=0: {ks_poisson:.4f}   β=1: {ks_goe:.4f}   β=2: {ks_gue:.4f}")

    output_path = OUTPUT_DIR / "item1_dim_split_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to {output_path}")

    logger.info(f"\n{'='*80}")
    logger.info(f"{'Group':<12} {'N forms':<8} {'N spc':<8} {'β MLE':<8} {'β CI':<18} {'KS(β=0)':<8} {'KS(β=1)':<8}")
    logger.info(f"{'-'*80}")
    for name, r in results.items():
        ci = f"[{r['beta_95_ci_lower']}, {r['beta_95_ci_upper']}]"
        logger.info(f"{name:<12} {r['n_forms']:<8} {r['n_spacings']:<8} {r['beta_mle']:<8} {ci:<18} {r['ks_vs_poisson_beta0']:<8} {r['ks_vs_goe_beta1']:<8}")


if __name__ == "__main__":
    main()
