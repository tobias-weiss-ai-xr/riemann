"""
Item 3: Height dependence — early vs late spacings repulsion.

Tests whether Brody β changes systematically from the first zero spacing
(z₂−z₁) to the last (z₁₀−z₉). If repulsion grows with height, this
implies the spectral statistics only approach GUE far from the central point.
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
N_SPACINGS = N_LEVELS - 1  # 9
N_BOOTSTRAP = 2000
OUTPUT_DIR = Path("data/spectral_rigidity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def brody_cdf(s, beta):
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    return 1 - np.exp(-a * s ** (beta + 1))


def neg_log_likelihood(beta, spacings):
    if beta < 0 or beta > 3:
        return 1e12
    s = spacings[(~np.isnan(spacings)) & (spacings > 0)]
    if len(s) < 3:
        return 1e12
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    log_lik = np.log(beta + 1) + np.log(a) + beta * np.log(s) - a * s ** (beta + 1)
    return -np.sum(log_lik)


def fit_brody_mle(spacings):
    s = spacings[(~np.isnan(spacings)) & (spacings > 0)]
    if len(s) < 3:
        return np.nan, np.nan, 0
    try:
        result = optimize.minimize_scalar(neg_log_likelihood, args=(s,), bounds=(0, 3), method="bounded")
        return result.x, stats.kstest(s, lambda x: brody_cdf(x, result.x))[0], len(s)
    except Exception:
        return np.nan, np.nan, 0


def bootstrap_ci(spacings, n_iter=N_BOOTSTRAP):
    s = spacings[(~np.isnan(spacings)) & (spacings > 0)]
    if len(s) < 10:
        return np.nan, np.nan, np.nan
    n = len(s)
    betas = []
    rng = np.random.default_rng(123 + abs(hash(str(len(s)))))
    for i in range(n_iter):
        boot_sample = rng.choice(s, size=n, replace=True)
        try:
            res = optimize.minimize_scalar(neg_log_likelihood, args=(boot_sample,), bounds=(0, 3), method="bounded")
            betas.append(res.x)
        except Exception:
            continue
    if len(betas) < 50:
        return np.nan, np.nan, np.nan
    betas = np.array(betas)
    return float(np.mean(betas)), float(np.percentile(betas, 2.5)), float(np.percentile(betas, 97.5))


def main():
    logger.info("Loading LMFDB data...")
    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    logger.info(f"Loaded {len(df)} forms")

    zero_cols = [f"z{k}" for k in range(1, N_LEVELS + 1)]
    df = df.dropna(subset=zero_cols)
    zeros = df[zero_cols].values  # (N, 10)
    spacings_raw = np.diff(zeros, axis=1)  # (N, 9)
    form_means = np.nanmean(spacings_raw, axis=1, keepdims=True)
    unfolded = spacings_raw / form_means  # (N, 9)

    dims = df["dim"].values.astype(int)

    # ── Per-spacing-index Brody fit ────────────────────────────────────────
    spacing_labels = [f"spacing_{i}" for i in range(1, N_SPACINGS + 1)]

    logger.info("Fitting Brody β per spacing index (full dataset)...")
    t0 = time.time()

    per_spacing = {}
    for idx in range(N_SPACINGS):
        vals = unfolded[:, idx]
        vals = vals[(~np.isnan(vals)) & (vals > 0) & (vals < 10)]
        beta_mle, ks_fit, n = fit_brody_mle(vals)
        beta_mean, beta_lo, beta_hi = bootstrap_ci(vals)

        ks_poisson = stats.kstest(vals, lambda x: brody_cdf(x, 0))[0]
        ks_goe = stats.kstest(vals, lambda x: brody_cdf(x, 1))[0]
        ks_gue = stats.kstest(vals, lambda x: brody_cdf(x, 2))[0]

        per_spacing[spacing_labels[idx]] = {
            "spacing_index": idx,
            "n_spacings": n,
            "beta_mle": float(f"{beta_mle:.4f}"),
            "beta_bootstrap_mean": float(f"{beta_mean:.4f}"),
            "beta_95_ci_lower": float(f"{beta_lo:.4f}"),
            "beta_95_ci_upper": float(f"{beta_hi:.4f}"),
            "ks_vs_poisson_0": float(f"{ks_poisson:.4f}"),
            "ks_vs_goe_1": float(f"{ks_goe:.4f}"),
            "ks_vs_gue_2": float(f"{ks_gue:.4f}"),
        }
        logger.info(f"  {spacing_labels[idx]:<12}: β={beta_mle:.4f} [{beta_lo:.4f},{beta_hi:.4f}]  "
                     f"n={n:,}  KS(0)={ks_poisson:.4f}  KS(1)={ks_goe:.4f}")

    # ── Per-spacing-index, split by dim_1 vs dim_ge2 ──────────────────────
    dim_groups = {"dim_1": dims == 1, "dim_ge2": dims >= 2}

    per_spacing_dim = {}
    for dname, dmask in dim_groups.items():
        logger.info(f"\nPer-spacing Brody fit for {dname}:")
        per_spacing_dim[dname] = {}
        for idx in range(N_SPACINGS):
            vals = unfolded[dmask, idx]
            vals = vals[(~np.isnan(vals)) & (vals > 0) & (vals < 10)]
            beta_mle, ks_fit, n = fit_brody_mle(vals)
            beta_mean, beta_lo, beta_hi = bootstrap_ci(vals)
            ks_poisson = stats.kstest(vals, lambda x: brody_cdf(x, 0))[0]
            ks_goe = stats.kstest(vals, lambda x: brody_cdf(x, 1))[0]
            per_spacing_dim[dname][spacing_labels[idx]] = {
                "n_spacings": n,
                "beta_mle": float(f"{beta_mle:.4f}"),
                "beta_bootstrap_mean": float(f"{beta_mean:.4f}"),
                "beta_95_ci_lower": float(f"{beta_lo:.4f}"),
                "beta_95_ci_upper": float(f"{beta_hi:.4f}"),
                "ks_vs_poisson_0": float(f"{ks_poisson:.4f}"),
                "ks_vs_goe_1": float(f"{ks_goe:.4f}"),
            }
            logger.info(f"  {spacing_labels[idx]:<12}: β={beta_mle:.4f} [{beta_lo:.4f},{beta_hi:.4f}]  n={n:,}")

    elapsed = time.time() - t0
    logger.info(f"Completed in {elapsed:.1f}s")

    # ── Pairwise tests: early spacings (1-3) vs late spacings (7-9) ──────────
    logger.info(f"\n{'='*60}")
    logger.info("Early vs late spacing comparison")
    for dname, dmask in dim_groups.items():
        early = unfolded[dmask, 0:3].ravel()
        late = unfolded[dmask, 6:9].ravel()
        early = early[(~np.isnan(early)) & (early > 0) & (early < 10)]
        late = late[(~np.isnan(late)) & (late > 0) & (late < 10)]
        beta_e, _, _ = fit_brody_mle(early)
        beta_l, _, _ = fit_brody_mle(late)
        ks_el = stats.ks_2samp(early, late)[0]
        try:
            u_stat, p_mann = stats.mannwhitneyu(early, late, alternative="two-sided")
        except ValueError:
            u_stat, p_mann = np.nan, np.nan
        per_spacing_dim[f"{dname}_early_vs_late"] = {
            "early_beta_mle": float(f"{beta_e:.4f}"),
            "late_beta_mle": float(f"{beta_l:.4f}"),
            "ks_early_vs_late": float(f"{ks_el:.4f}"),
            "mannwhitney_u": float(f"{u_stat:.1f}"),
            "mannwhitney_p": float(f"{p_mann:.6f}"),
        }
        logger.info(f"  {dname}: early β={beta_e:.4f}  late β={beta_l:.4f}  "
                     f"KS={ks_el:.4f}  MW p={p_mann:.6f}")

    results = {
        "per_spacing_full": per_spacing,
        "per_spacing_dim_split": per_spacing_dim,
    }

    output_path = OUTPUT_DIR / "item3_height_dependence_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
