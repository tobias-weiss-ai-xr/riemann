"""
Validate per-form Brody beta estimation by computing it for dim=1 forms
(true GUE population, pooled beta=1.88) vs dim>=2 forms.

If per-form beta with 9 spacings can recover beta~2 for dim=1,
then the dim>=2 "GUE outliers" truly have low beta (not a methodological artifact).
If it cannot, then the per-form beta is too noisy with 9 spacings to be informative.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.special import gamma, erf
from scipy.integrate import cumulative_trapezoid
from scipy.optimize import minimize_scalar
from pathlib import Path
import json


def brody_pdf(s: np.ndarray, beta: float) -> np.ndarray:
    if beta == 0:
        return np.exp(-s)
    c = (3 * beta + 1) / 2
    return (c / gamma(c)) * s**beta * np.exp(-c * s**2)


def brody_cdf(s: np.ndarray, beta: float) -> np.ndarray:
    s_arr = np.atleast_1d(s)
    grid = np.linspace(0, max(s_arr.max() * 1.5, 10), 500)
    pdf = brody_pdf(grid, beta)
    cdf_vals = cumulative_trapezoid(pdf, grid, initial=0)
    return np.interp(s_arr, grid, cdf_vals)


def cdf_gue(s):
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s**2 / np.pi)


def cdf_goe(s):
    return 1 - np.exp(-np.pi * s**2 / 4)


def fit_brody_beta(spacings: np.ndarray) -> tuple[float, float]:
    from scipy.optimize import minimize_scalar
    spacings = spacings[np.isfinite(spacings) & (spacings > 0)]
    if len(spacings) < 5:
        return float("nan"), float("nan")

    def neg_log_likelihood(beta):
        if beta < 0 or beta > 3:
            return 1e12
        a = np.exp((beta + 1) * np.log(gamma(float(beta + 2) / float(beta + 1))))
        log_lik = np.log(beta + 1) + np.log(a) + beta * np.log(spacings) - a * spacings**(beta + 1)
        return -np.sum(log_lik)

    result = minimize_scalar(neg_log_likelihood, bounds=(0, 3), method="bounded")
    beta_mle = float(result.x)
    ks = float(sp_stats.kstest(spacings, lambda x: brody_cdf(x, beta_mle)).statistic)
    return beta_mle, ks


def main():
    print("=" * 70)
    print("PER-FORM BRODY BETA VALIDATION")
    print("dim=1 (true GUE, pooled beta=1.88) vs dim>=2 (pooled beta=0.24)")
    print("=" * 70)

    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    zero_cols = [f"z{k}" for k in range(1, 11)]
    zeros = df[zero_cols].values
    mean_sp = df["mean_zero_spacing"].values
    spacings_all = np.diff(zeros, axis=1) / mean_sp[:, None]

    # Sample 500 from dim=1 and 500 from dim>=2
    d1_idx = np.where(df["dim"].values == 1)[0]
    d2_idx = np.where(df["dim"].values >= 2)[0]
    n_sample = min(500, len(d1_idx), len(d2_idx))

    rng = np.random.RandomState(42)
    d1_sample = rng.choice(d1_idx, n_sample, replace=False)
    d2_sample = rng.choice(d2_idx, n_sample, replace=False)

    print(f"\nSampling {n_sample} forms from each group...")

    d1_betas = []
    for i in d1_sample:
        beta, ks = fit_brody_beta(spacings_all[i])
        if not np.isnan(beta):
            d1_betas.append(beta)

    d2_betas = []
    for i in d2_sample:
        beta, ks = fit_brody_beta(spacings_all[i])
        if not np.isnan(beta):
            d2_betas.append(beta)

    d1_betas = np.array(d1_betas)
    d2_betas = np.array(d2_betas)

    print(f"\n  dim=1 (true GUE, pooled beta=1.88):")
    print(f"    n = {len(d1_betas)}")
    print(f"    mean beta = {np.mean(d1_betas):.3f} +/- {np.std(d1_betas):.3f}")
    print(f"    median beta = {np.median(d1_betas):.3f}")
    print(f"    beta > 1.0: {np.sum(d1_betas > 1.0)} / {len(d1_betas)} ({np.sum(d1_betas > 1.0)/len(d1_betas)*100:.1f}%)")
    print(f"    beta > 1.5: {np.sum(d1_betas > 1.5)} / {len(d1_betas)} ({np.sum(d1_betas > 1.5)/len(d1_betas)*100:.1f}%)")
    print(f"    beta > 1.8: {np.sum(d1_betas > 1.8)} / {len(d1_betas)} ({np.sum(d1_betas > 1.8)/len(d1_betas)*100:.1f}%)")
    print(f"    beta < 0.5: {np.sum(d1_betas < 0.5)} / {len(d1_betas)} ({np.sum(d1_betas < 0.5)/len(d1_betas)*100:.1f}%)")

    print(f"\n  dim>=2 (pooled beta=0.24):")
    print(f"    n = {len(d2_betas)}")
    print(f"    mean beta = {np.mean(d2_betas):.3f} +/- {np.std(d2_betas):.3f}")
    print(f"    median beta = {np.median(d2_betas):.3f}")
    print(f"    beta > 1.0: {np.sum(d2_betas > 1.0)} / {len(d2_betas)} ({np.sum(d2_betas > 1.0)/len(d2_betas)*100:.1f}%)")
    print(f"    beta > 1.5: {np.sum(d2_betas > 1.5)} / {len(d2_betas)} ({np.sum(d2_betas > 1.5)/len(d2_betas)*100:.1f}%)")
    print(f"    beta < 0.5: {np.sum(d2_betas < 0.5)} / {len(d2_betas)} ({np.sum(d2_betas < 0.5)/len(d2_betas)*100:.1f}%)")

    # Mann-Whitney U test
    u_stat, u_p = sp_stats.mannwhitneyu(d1_betas, d2_betas, alternative="greater")
    print(f"\n  Mann-Whitney U (dim=1 > dim>=2): U={u_stat:.0f}, p={u_p:.4e}")

    # Also compute KS test classification for the same samples
    print(f"\n  KS test classification (same samples):")
    d1_gue = 0
    for i in d1_sample:
        gue_ks = sp_stats.kstest(spacings_all[i], cdf_gue).statistic
        goe_ks = sp_stats.kstest(spacings_all[i], cdf_goe).statistic
        if gue_ks < goe_ks:
            d1_gue += 1
    d2_gue = 0
    for i in d2_sample:
        gue_ks = sp_stats.kstest(spacings_all[i], cdf_gue).statistic
        goe_ks = sp_stats.kstest(spacings_all[i], cdf_goe).statistic
        if gue_ks < goe_ks:
            d2_gue += 1

    print(f"    dim=1: {d1_gue}/{n_sample} ({d1_gue/n_sample*100:.1f}%) prefer GUE")
    print(f"    dim>=2: {d2_gue}/{n_sample} ({d2_gue/n_sample*100:.1f}%) prefer GUE")

    # Key comparison: among dim>=2 forms that prefer GUE, what is their beta?
    d2_gue_betas = []
    d2_goe_betas = []
    for i in d2_sample:
        gue_ks = sp_stats.kstest(spacings_all[i], cdf_gue).statistic
        goe_ks = sp_stats.kstest(spacings_all[i], cdf_goe).statistic
        beta, _ = fit_brody_beta(spacings_all[i])
        if not np.isnan(beta):
            if gue_ks < goe_ks:
                d2_gue_betas.append(beta)
            else:
                d2_goe_betas.append(beta)

    d2_gue_betas = np.array(d2_gue_betas)
    d2_goe_betas = np.array(d2_goe_betas)

    print(f"\n  dim>=2 GUE-preferring forms (KS test):")
    print(f"    n = {len(d2_gue_betas)}")
    print(f"    mean beta = {np.mean(d2_gue_betas):.3f} +/- {np.std(d2_gue_betas):.3f}")
    print(f"    median beta = {np.median(d2_gue_betas):.3f}")
    print(f"    beta > 1.0: {np.sum(d2_gue_betas > 1.0)} / {len(d2_gue_betas)} ({np.sum(d2_gue_betas > 1.0)/len(d2_gue_betas)*100:.1f}%)")

    print(f"\n  dim>=2 GOE-preferring forms (KS test):")
    print(f"    n = {len(d2_goe_betas)}")
    print(f"    mean beta = {np.mean(d2_goe_betas):.3f} +/- {np.std(d2_goe_betas):.3f}")
    print(f"    median beta = {np.median(d2_goe_betas):.3f}")

    # Summary
    print(f"\n  {'='*50}")
    print(f"  VALIDATION SUMMARY")
    print(f"  {'='*50}")
    print(f"  dim=1 per-form beta: {np.mean(d1_betas):.3f} (pooled: 1.88)")
    print(f"  dim>=2 per-form beta: {np.mean(d2_betas):.3f} (pooled: 0.24)")
    print(f"  dim=1 KS-GUE%: {d1_gue/n_sample*100:.1f}%")
    print(f"  dim>=2 KS-GUE%: {d2_gue/n_sample*100:.1f}%")
    print(f"  dim>=2 GUE-preferring per-form beta: {np.mean(d2_gue_betas):.3f}")

    if np.mean(d1_betas) > 1.0:
        print(f"\n  VERDICT: Per-form beta CAN distinguish GUE (dim=1 mean={np.mean(d1_betas):.2f})")
        print(f"  from Poisson (dim>=2 mean={np.mean(d2_betas):.2f}).")
        print(f"  The dim>=2 'GUE outliers' (beta={np.mean(d2_gue_betas):.2f}) are NOT truly GUE.")
    else:
        print(f"\n  VERDICT: Per-form beta with 9 spacings is too noisy to distinguish GUE from Poisson.")
        print(f"  dim=1 mean beta={np.mean(d1_betas):.2f} should be ~1.88 but is much lower.")
        print(f"  The per-form beta analysis is NOT reliable with 9 spacings.")

    # Save results
    results = {
        "dim1": {
            "n": len(d1_betas),
            "mean_beta": float(np.mean(d1_betas)),
            "std_beta": float(np.std(d1_betas)),
            "median_beta": float(np.median(d1_betas)),
            "pct_gt_1": float(np.sum(d1_betas > 1.0) / len(d1_betas) * 100),
            "pct_gt_1.5": float(np.sum(d1_betas > 1.5) / len(d1_betas) * 100),
            "ks_gue_pct": float(d1_gue / n_sample * 100),
        },
        "dim2": {
            "n": len(d2_betas),
            "mean_beta": float(np.mean(d2_betas)),
            "std_beta": float(np.std(d2_betas)),
            "median_beta": float(np.median(d2_betas)),
            "pct_gt_1": float(np.sum(d2_betas > 1.0) / len(d2_betas) * 100),
            "ks_gue_pct": float(d2_gue / n_sample * 100),
        },
        "dim2_gue_preferring": {
            "n": len(d2_gue_betas),
            "mean_beta": float(np.mean(d2_gue_betas)),
            "median_beta": float(np.median(d2_gue_betas)),
        },
        "dim2_goe_preferring": {
            "n": len(d2_goe_betas),
            "mean_beta": float(np.mean(d2_goe_betas)),
            "median_beta": float(np.median(d2_goe_betas)),
        },
        "mannwhitney_p": float(u_p),
    }
    with open("data/results/brody_beta_validation.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: data/results/brody_beta_validation.json")


if __name__ == "__main__":
    main()
