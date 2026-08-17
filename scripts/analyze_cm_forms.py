"""
CM (Complex Multiplication) Forms Analysis

Hypothesis: The 6% GUE outliers in dim>=2 are predominantly CM forms.
CM forms are arithmetically closest to elliptic curves (dim=1), so they
may retain GUE statistics even at higher dimension.

This script:
1. Merges is_cm from the SQL dataset into the zeros dataset
2. Recomputes GUE/GOE preference via KS test
3. Analyzes CM vs non-CM within dim>=2 GUE outliers
4. Computes chi-square and Fisher's exact tests
5. Generates a summary table and figure
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats


def cdf_gue(s: np.ndarray) -> np.ndarray:
    """GUE (β=2) level spacing CDF."""
    from scipy.special import erf
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s**2 / np.pi)


def cdf_goe(s: np.ndarray) -> np.ndarray:
    """GOE (β=1) level spacing CDF."""
    return 1 - np.exp(-np.pi * s**2 / 4)


def main() -> None:
    print("=" * 70)
    print("CM FORMS ANALYSIS: Are GUE outliers in dim>=2 predominantly CM?")
    print("=" * 70)

    # -- 1. Load and merge data ------------------------------------------
    print("\n[1] Loading data...")
    df_zeros = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    df_sql = pd.read_csv("data/lmfdb/lmfdb_sql_weight2_ml.csv")

    print(f"  zeros dataset: {len(df_zeros)} forms")
    print(f"  sql dataset:   {len(df_sql)} forms")

    # Merge is_cm (and other metadata) from SQL into zeros
    cm_cols = ["label", "is_cm", "is_self_dual", "char_degree"]
    df = df_zeros.merge(df_sql[cm_cols], on="label", how="left")
    print(f"  merged:        {len(df)} forms")
    print(f"  is_cm available: {df['is_cm'].notna().sum()} / {len(df)}")
    print(f"  CM forms:      {int(df['is_cm'].sum())} ({df['is_cm'].mean()*100:.1f}%)")

    # -- 2. Recompute GUE/GOE preference --------------------------------
    print("\n[2] Computing GUE/GOE preference via KS test...")
    zero_cols = [f"z{k}" for k in range(1, 11)]
    zeros = df[zero_cols].values
    mean_zero_spacing = df["mean_zero_spacing"].values

    # Normalized spacings
    spacings = np.diff(zeros, axis=1) / mean_zero_spacing[:, None]

    # KS statistics
    gue_ks = np.array([
        sp_stats.kstest(spacings[i], cdf_gue).statistic
        for i in range(len(df))
    ])
    goe_ks = np.array([
        sp_stats.kstest(spacings[i], cdf_goe).statistic
        for i in range(len(df))
    ])

    prefers_gue = (gue_ks < goe_ks).astype(bool)
    df["prefers_gue"] = prefers_gue
    df["gue_ks"] = gue_ks
    df["goe_ks"] = goe_ks

    dims = df["dim"].values.astype(int)

    # -- 3. Split by dimension ------------------------------------------
    print("\n[3] Dimension split...")
    d1_mask = dims == 1
    d2_mask = dims >= 2

    d1_df = df[d1_mask].copy()
    d2_df = df[d2_mask].copy()

    print(f"  dim=1:  {len(d1_df)} forms, {d1_df['prefers_gue'].sum()} GUE ({d1_df['prefers_gue'].mean()*100:.1f}%)")
    print(f"  dim>=2: {len(d2_df)} forms, {d2_df['prefers_gue'].sum()} GUE ({d2_df['prefers_gue'].mean()*100:.1f}%)")

    # -- 4. CM analysis within dim>=2 -----------------------------------
    print("\n" + "=" * 70)
    print("[4] CM ANALYSIS WITHIN dim>=2")
    print("=" * 70)

    # Drop rows with missing is_cm
    d2_cm = d2_df.dropna(subset=["is_cm"]).copy()
    d2_cm["is_cm"] = d2_cm["is_cm"].astype(int)

    print(f"\n  dim>=2 with is_cm: {len(d2_cm)} forms")
    print(f"  CM forms:      {int(d2_cm['is_cm'].sum())} ({d2_cm['is_cm'].mean()*100:.1f}%)")
    print(f"  non-CM forms:   {int((1-d2_cm['is_cm']).sum())} ({(1-d2_cm['is_cm']).mean()*100:.1f}%)")

    # Contingency table: is_cm × prefers_gue
    contingency = pd.crosstab(d2_cm["is_cm"], d2_cm["prefers_gue"])
    print(f"\n  Contingency table (is_cm × prefers_gue):")
    print(f"                   GUE     GOE    Total")
    for cm_val in [0, 1]:
        if cm_val in contingency.index:
            gue = int(contingency.loc[cm_val, True]) if True in contingency.columns else 0
            goe = int(contingency.loc[cm_val, False]) if False in contingency.columns else 0
            label = "CM    " if cm_val == 1 else "non-CM"
            print(f"  {label}        {gue:>6}  {goe:>6}  {gue+goe:>6}")

    # Key statistics
    cm_gue = int(d2_cm[d2_cm["is_cm"] == 1]["prefers_gue"].sum()) if (d2_cm["is_cm"] == 1).any() else 0
    cm_total = int((d2_cm["is_cm"] == 1).sum())
    noncm_gue = int(d2_cm[d2_cm["is_cm"] == 0]["prefers_gue"].sum()) if (d2_cm["is_cm"] == 0).any() else 0
    noncm_total = int((d2_cm["is_cm"] == 0).sum())
    total_gue = cm_gue + noncm_gue

    cm_gue_pct = cm_gue / cm_total * 100 if cm_total > 0 else 0
    noncm_gue_pct = noncm_gue / noncm_total * 100 if noncm_total > 0 else 0
    cm_fraction_of_gue = cm_gue / total_gue * 100 if total_gue > 0 else 0

    print(f"\n  KEY STATISTICS:")
    print(f"  -------------------------------------------------")
    print(f"  CM forms preferring GUE:       {cm_gue:>5} / {cm_total:>5} ({cm_gue_pct:.1f}%)")
    print(f"  non-CM forms preferring GUE:   {noncm_gue:>5} / {noncm_total:>5} ({noncm_gue_pct:.1f}%)")
    print(f"  CM fraction of all GUE outliers: {cm_gue:>5} / {total_gue:>5} ({cm_fraction_of_gue:.1f}%)")
    print(f"  Overall GUE rate (dim>=2):      {total_gue:>5} / {len(d2_cm):>5} ({total_gue/len(d2_cm)*100:.1f}%)")

    # -- 5. Statistical tests -------------------------------------------
    print("\n" + "=" * 70)
    print("[5] STATISTICAL TESTS")
    print("=" * 70)

    # Chi-square test
    if cm_total > 0 and noncm_total > 0:
        chi2, chi2_p, dof, expected = sp_stats.chi2_contingency(contingency.values)
        print(f"\n  Chi-square test:")
        print(f"    chi2 = {chi2:.2f}, dof = {dof}, p = {chi2_p:.4e}")

        # Fisher's exact test (more reliable for small counts)
        odds_ratio, fisher_p = sp_stats.fisher_exact(contingency.values)
        print(f"\n  Fisher's exact test:")
        print(f"    odds ratio = {odds_ratio:.4f}, p = {fisher_p:.4e}")

        # Effect size (Cramér's V)
        n = contingency.values.sum()
        cramers_v = np.sqrt(chi2 / (n * (min(contingency.shape) - 1)))
        print(f"\n  Cramér's V (effect size): {cramers_v:.4f}")

    # -- 6. CM analysis within dim=1 (for comparison) ------------------
    print("\n" + "=" * 70)
    print("[6] CM ANALYSIS WITHIN dim=1 (comparison)")
    print("=" * 70)

    d1_cm = d1_df.dropna(subset=["is_cm"]).copy()
    d1_cm["is_cm"] = d1_cm["is_cm"].astype(int)

    if len(d1_cm) > 0 and (d1_cm["is_cm"] == 1).any():
        d1_cm_gue = int(d1_cm[d1_cm["is_cm"] == 1]["prefers_gue"].sum())
        d1_cm_total = int((d1_cm["is_cm"] == 1).sum())
        d1_noncm_gue = int(d1_cm[d1_cm["is_cm"] == 0]["prefers_gue"].sum())
        d1_noncm_total = int((d1_cm["is_cm"] == 0).sum())

        print(f"\n  dim=1 CM forms preferring GUE:    {d1_cm_gue:>5} / {d1_cm_total:>5} ({d1_cm_gue/d1_cm_total*100:.1f}%)")
        print(f"  dim=1 non-CM forms preferring GUE: {d1_noncm_gue:>5} / {d1_noncm_total:>5} ({d1_noncm_gue/d1_noncm_total*100:.1f}%)")
    else:
        print(f"\n  dim=1: {len(d1_cm)} forms, {(d1_cm['is_cm']==1).sum() if len(d1_cm)>0 else 0} CM forms")
        print(f"  (dim=1 forms are all elliptic curves; CM analysis less relevant)")

    # -- 7. Per-dimension CM breakdown ----------------------------------
    print("\n" + "=" * 70)
    print("[7] PER-DIMENSION CM BREAKDOWN (dim>=2)")
    print("=" * 70)

    print(f"\n  {'dim':<6} {'total':<8} {'CM':<8} {'non-CM':<8} {'GUE(CM)':<10} {'GUE(non-CM)':<14} {'CM%':<8}")
    print("  " + "-" * 64)

    for dim_val in sorted(d2_cm["dim"].unique()):
        dim_df = d2_cm[d2_cm["dim"] == dim_val]
        n_total = len(dim_df)
        n_cm = int((dim_df["is_cm"] == 1).sum())
        n_noncm = n_total - n_cm
        gue_cm = int(dim_df[dim_df["is_cm"] == 1]["prefers_gue"].sum()) if n_cm > 0 else 0
        gue_noncm = int(dim_df[dim_df["is_cm"] == 0]["prefers_gue"].sum()) if n_noncm > 0 else 0
        cm_pct = n_cm / n_total * 100 if n_total > 0 else 0
        gue_cm_pct = f"{gue_cm}/{n_cm} ({gue_cm/n_cm*100:.1f}%)" if n_cm > 0 else "—"
        gue_noncm_pct = f"{gue_noncm}/{n_noncm} ({gue_noncm/n_noncm*100:.1f}%)" if n_noncm > 0 else "—"
        print(f"  {dim_val:<6} {n_total:<8} {n_cm:<8} {n_noncm:<8} {gue_cm_pct:<10} {gue_noncm_pct:<14} {cm_pct:<8.1f}")

    # -- 8. Summary verdict --------------------------------------------
    print("\n" + "=" * 70)
    print("[8] SUMMARY")
    print("=" * 70)

    enrichment = (cm_gue_pct / (total_gue / len(d2_cm) * 100)) if total_gue > 0 else 0
    print(f"\n  CM forms are {enrichment:.2f}× more likely to be GUE outliers than the baseline")
    print(f"  CM fraction of GUE outliers: {cm_fraction_of_gue:.1f}%")
    print(f"  CM fraction of all dim>=2:   {cm_total/len(d2_cm)*100:.1f}%")

    if cm_fraction_of_gue > 50:
        verdict = "CONFIRMED: Majority of GUE outliers are CM forms"
    elif cm_fraction_of_gue > cm_total / len(d2_cm) * 100 * 2:
        verdict = "PARTIALLY CONFIRMED: CM forms are enriched in GUE outliers"
    elif fisher_p < 0.05:
        verdict = "WEAK: CM forms show statistically significant but small enrichment"
    else:
        verdict = "REJECTED: CM forms do not explain GUE outliers"

    print(f"\n  VERDICT: {verdict}")

    # -- 9. Save results ------------------------------------------------
    output_dir = Path("data/results")
    output_dir.mkdir(exist_ok=True)

    results = {
        "total_dim_ge2": int(len(d2_cm)),
        "cm_forms": cm_total,
        "non_cm_forms": noncm_total,
        "cm_gue": cm_gue,
        "non_cm_gue": noncm_gue,
        "total_gue": total_gue,
        "cm_gue_pct": round(cm_gue_pct, 2),
        "non_cm_gue_pct": round(noncm_gue_pct, 2),
        "cm_fraction_of_gue": round(cm_fraction_of_gue, 2),
        "chi2": round(float(chi2), 4),
        "chi2_p": float(chi2_p),
        "odds_ratio": round(float(odds_ratio), 4),
        "fisher_p": float(fisher_p),
        "cramers_v": round(float(cramers_v), 4),
        "verdict": verdict,
    }

    output_path = output_dir / "cm_forms_analysis.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_path}")

    # -- 10. Save merged dataset with is_cm + prefers_gue ---------------
    merged_path = output_dir / "cm_merged_dim2.csv"
    d2_cm[["label", "level", "dim", "analytic_rank", "is_cm", "prefers_gue", "gue_ks", "goe_ks"]].to_csv(merged_path, index=False)
    print(f"  Merged dim>=2 data saved to: {merged_path}")

    # -- 11. Figure: CM vs non-CM GUE rate by dimension ----------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: GUE rate by dimension, CM vs non-CM
    dims_list = sorted(d2_cm["dim"].unique())
    cm_rates = []
    noncm_rates = []
    for d in dims_list:
        dim_df = d2_cm[d2_cm["dim"] == d]
        cm_sub = dim_df[dim_df["is_cm"] == 1]
        noncm_sub = dim_df[dim_df["is_cm"] == 0]
        cm_rates.append(cm_sub["prefers_gue"].mean() * 100 if len(cm_sub) > 0 else 0)
        noncm_rates.append(noncm_sub["prefers_gue"].mean() * 100 if len(noncm_sub) > 0 else 0)

    ax = axes[0]
    width = 0.35
    x = np.arange(len(dims_list))
    ax.bar(x - width/2, cm_rates, width, label="CM", color="#d62728", alpha=0.8)
    ax.bar(x + width/2, noncm_rates, width, label="non-CM", color="#1f77b4", alpha=0.8)
    ax.set_xlabel("Dimension")
    ax.set_ylabel("GUE preference (%)")
    ax.set_title("GUE preference by dimension: CM vs non-CM")
    ax.set_xticks(x)
    ax.set_xticklabels(dims_list)
    ax.legend()
    ax.set_ylim(0, max(max(cm_rates), max(noncm_rates)) * 1.3)

    # Right: Contingency table heatmap
    ax = axes[1]
    cm_table = np.array([[noncm_gue, noncm_total - noncm_gue],
                         [cm_gue, cm_total - cm_gue]])
    im = ax.imshow(cm_table, cmap="YlOrRd", aspect="auto")
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["GUE", "GOE"])
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["non-CM", "CM"])
    ax.set_title("Contingency table (dim>=2)")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm_table[i, j]), ha="center", va="center", fontsize=14, fontweight="bold")
    plt.colorbar(im, ax=ax, label="count")

    plt.tight_layout()
    fig_path = "papers/cm_forms_analysis.png"
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Figure saved to: {fig_path}")


if __name__ == "__main__":
    main()
