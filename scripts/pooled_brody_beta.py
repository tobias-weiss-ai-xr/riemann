"""
Pooled Brody beta for GUE outliers vs GOE majority in dim>=2.

The per-form Brody beta with 9 spacings is unreliable (dim=1 per-form beta=0.43
vs pooled beta=1.88). This script pools ALL spacings from each group to get
a reliable beta estimate.

If the pooled GUE outliers have beta close to 2, they are genuinely GUE.
If they have beta close to 0.24 (same as all dim>=2), they are NOT genuinely GUE.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.special import gamma, erf
from scipy.integrate import cumulative_trapezoid
from pathlib import Path


def brody_pdf(s, beta):
    """Brody PDF: P(s) = (beta+1) * a * s^beta * exp(-a * s^(beta+1))."""
    a = np.exp((beta + 1) * np.log(gamma(float(beta + 2) / float(beta + 1))))
    return (beta + 1) * a * s**beta * np.exp(-a * s**(beta + 1))


def brody_cdf(s, beta):
    """Brody CDF: F(s) = 1 - exp(-a * s^(beta+1))."""
    a = np.exp((beta + 1) * np.log(gamma(float(beta + 2) / float(beta + 1))))
    return 1 - np.exp(-a * s**(beta + 1))


def cdf_gue(s):
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s**2 / np.pi)


def cdf_goe(s):
    return 1 - np.exp(-np.pi * s**2 / 4)


def fit_brody_beta_pooled(spacings, label=""):
    """Fit Brody beta to a pooled set of spacings via MLE."""
    from scipy.optimize import minimize_scalar
    spacings = spacings[np.isfinite(spacings) & (spacings > 0)]
    if len(spacings) < 10:
        return float("nan"), float("nan")

    def neg_log_likelihood(beta):
        if beta < 0 or beta > 3:
            return 1e12
        a = np.exp((beta + 1) * np.log(gamma(float(beta + 2) / float(beta + 1))))
        log_lik = np.log(beta + 1) + np.log(a) + beta * np.log(spacings) - a * spacings**(beta + 1)
        return -np.sum(log_lik)

    result = minimize_scalar(neg_log_likelihood, bounds=(0, 3), method="bounded")
    beta_mle = float(result.x)

    # KS stat against fitted CDF
    ks = float(sp_stats.kstest(spacings, lambda x: brody_cdf(x, beta_mle)).statistic)

    return beta_mle, ks


def main():
    print("=" * 70)
    print("POOLED BRODY BETA: GUE outliers vs GOE majority (dim>=2)")
    print("=" * 70)

    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    zero_cols = [f"z{k}" for k in range(1, 11)]
    zeros = df[zero_cols].values
    mean_sp = df["mean_zero_spacing"].values
    spacings_all = np.diff(zeros, axis=1) / mean_sp[:, None]

    # Classify
    gue_ks = np.array([sp_stats.kstest(spacings_all[i], cdf_gue).statistic for i in range(len(df))])
    goe_ks = np.array([sp_stats.kstest(spacings_all[i], cdf_goe).statistic for i in range(len(df))])
    prefers_gue = gue_ks < goe_ks

    dims = df["dim"].values.astype(int)

    # dim=1 (reference: pooled beta should be ~1.88)
    d1_spacings = spacings_all[dims == 1].flatten()
    d1_beta, d1_ks = fit_brody_beta_pooled(d1_spacings, "dim=1")

    # dim>=2 all
    d2_spacings = spacings_all[dims >= 2].flatten()
    d2_beta, d2_ks = fit_brody_beta_pooled(d2_spacings, "dim>=2")

    # dim>=2 GUE outliers (pooled)
    d2_gue_mask = (dims >= 2) & prefers_gue
    d2_gue_spacings = spacings_all[d2_gue_mask].flatten()
    d2_gue_beta, d2_gue_ks = fit_brody_beta_pooled(d2_gue_spacings, "dim>=2 GUE")

    # dim>=2 GOE majority (pooled)
    d2_goe_mask = (dims >= 2) & ~prefers_gue
    d2_goe_spacings = spacings_all[d2_goe_mask].flatten()
    d2_goe_beta, d2_goe_ks = fit_brody_beta_pooled(d2_goe_spacings, "dim>=2 GOE")

    # dim>=2 non-CM GUE outliers (pooled)
    df_sql = pd.read_csv("data/lmfdb/lmfdb_sql_weight2_ml.csv", usecols=["label", "is_cm"])
    df["is_cm"] = df["label"].map(df_sql.set_index("label")["is_cm"])
    d2_noncm_gue_mask = (dims >= 2) & prefers_gue & (df["is_cm"] == 0)
    d2_noncm_gue_spacings = spacings_all[d2_noncm_gue_mask].flatten()
    d2_noncm_gue_beta, d2_noncm_gue_ks = fit_brody_beta_pooled(d2_noncm_gue_spacings, "dim>=2 non-CM GUE")

    print(f"\n  {'Group':<30} {'n_forms':<10} {'n_spacings':<12} {'beta':<8} {'KS':<8}")
    print("  " + "-" * 68)
    for label, sp, beta, ks, n_forms in [
        ("dim=1 (all)", d1_spacings, d1_beta, d1_ks, int((dims == 1).sum())),
        ("dim>=2 (all)", d2_spacings, d2_beta, d2_ks, int((dims >= 2).sum())),
        ("dim>=2 GUE outliers", d2_gue_spacings, d2_gue_beta, d2_gue_ks, int(d2_gue_mask.sum())),
        ("dim>=2 GOE majority", d2_goe_spacings, d2_goe_beta, d2_goe_ks, int(d2_goe_mask.sum())),
        ("dim>=2 non-CM GUE", d2_noncm_gue_spacings, d2_noncm_gue_beta, d2_noncm_gue_ks, int(d2_noncm_gue_mask.sum())),
    ]:
        print(f"  {label:<30} {n_forms:<10} {len(sp):<12} {beta:<8.3f} {ks:<8.4f}")

    print(f"\n  {'='*50}")
    print(f"  INTERPRETATION")
    print(f"  {'='*50}")

    if d2_gue_beta > 1.5:
        verdict = "GUE outliers ARE genuinely GUE (pooled beta close to 2)"
    elif d2_gue_beta > 1.0:
        verdict = "GUE outliers are intermediate (beta between GOE and GUE)"
    elif d2_gue_beta > 0.5:
        verdict = "GUE outliers are weakly repulsive (beta between Poisson and GOE)"
    else:
        verdict = "GUE outliers are Poisson-like (beta close to 0, NOT GUE)"

    print(f"\n  Pooled beta for dim>=2 GUE outliers: {d2_gue_beta:.3f}")
    print(f"  Pooled beta for dim>=2 GOE majority: {d2_goe_beta:.3f}")
    print(f"  Pooled beta for dim=1 (reference):   {d1_beta:.3f}")
    print(f"\n  VERDICT: {verdict}")

    if d2_gue_beta > d2_beta + 0.1:
        print(f"\n  The GUE outliers have HIGHER beta than the dim>=2 average ({d2_gue_beta:.3f} vs {d2_beta:.3f})")
        print(f"  This suggests a real subpopulation with more level repulsion.")
    elif abs(d2_gue_beta - d2_beta) < 0.05:
        print(f"\n  The GUE outliers have SIMILAR beta to the dim>=2 average ({d2_gue_beta:.3f} vs {d2_beta:.3f})")
        print(f"  This suggests the KS test classification is noisy, not a real subpopulation.")
    else:
        print(f"\n  The GUE outliers have slightly higher beta ({d2_gue_beta:.3f} vs {d2_beta:.3f})")

    # Also compute beta for dim=2,3,4,5+ GUE outliers separately
    print(f"\n  {'='*50}")
    print(f"  POOLED BETA BY DIMENSION (GUE outliers only)")
    print(f"  {'='*50}")
    print(f"\n  {'dim':<6} {'n_forms':<10} {'n_spacings':<12} {'beta':<8} {'KS':<8}")
    print("  " + "-" * 44)
    for dim_val in [2, 3, 4, 5]:
        mask = (dims == dim_val) & prefers_gue
        sp = spacings_all[mask].flatten()
        if len(sp) < 10:
            continue
        beta, ks = fit_brody_beta_pooled(sp)
        print(f"  {dim_val:<6} {int(mask.sum()):<10} {len(sp):<12} {beta:<8.3f} {ks:<8.4f}")

    # dim 5+
    mask = (dims >= 5) & prefers_gue
    sp = spacings_all[mask].flatten()
    beta, ks = fit_brody_beta_pooled(sp)
    print(f"  {'5+':<6} {int(mask.sum()):<10} {len(sp):<12} {beta:<8.3f} {ks:<8.4f}")

    # Save
    results = {
        "dim1_all": {"beta": d1_beta, "ks": d1_ks, "n_spacings": len(d1_spacings)},
        "dim2_all": {"beta": d2_beta, "ks": d2_ks, "n_spacings": len(d2_spacings)},
        "dim2_gue_outliers": {"beta": d2_gue_beta, "ks": d2_gue_ks, "n_spacings": len(d2_gue_spacings)},
        "dim2_goe_majority": {"beta": d2_goe_beta, "ks": d2_goe_ks, "n_spacings": len(d2_goe_spacings)},
        "dim2_noncm_gue": {"beta": d2_noncm_gue_beta, "ks": d2_noncm_gue_ks, "n_spacings": len(d2_noncm_gue_spacings)},
        "verdict": verdict,
    }
    with open("data/results/pooled_brody_beta.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: data/results/pooled_brody_beta.json")


if __name__ == "__main__":
    main()
