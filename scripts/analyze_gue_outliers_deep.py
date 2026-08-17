"""
Deep characterization of GUE outliers in dim>=2 (non-CM forms).

The CM analysis showed CM explains only 1.1% of GUE outliers. This script
investigates what distinguishes the 1,729 non-CM GUE outliers from the
27,384 non-CM GOE majority.

Analyses:
1. Root number (sign of functional equation) x GUE preference
2. Level threshold analysis (binned)
3. Dimension x level interaction
4. Per-form Brody beta estimation
5. Analytic rank x GUE preference
6. Trace statistics (mean, std, max_abs) vs GUE preference
7. Logistic regression: which features best predict GUE preference?
8. Nearest-neighbor spacing ratio analysis
"""
from __future__ import annotations

import json
from pathlib import Path
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.special import erf
from scipy.optimize import minimize_scalar


# ── Brody distribution ────────────────────────────────────────────────

def brody_pdf(s: np.ndarray, beta: float) -> np.ndarray:
    """Brody distribution PDF."""
    if beta == 0:
        return np.exp(-s)
    from scipy.special import gamma
    c = (3 * beta + 1) / 2
    return (c / gamma(c)) * s**beta * np.exp(-c * s**2)


def brody_cdf(s: np.ndarray, beta: float) -> np.ndarray:
    """Brody distribution CDF via numerical integration."""
    from scipy.integrate import cumulative_trapezoid
    s_arr = np.atleast_1d(s)
    grid = np.linspace(0, max(s_arr.max() * 1.5, 10), 500)
    pdf = brody_pdf(grid, beta)
    cdf_vals = cumulative_trapezoid(pdf, grid, initial=0)
    return np.interp(s_arr, grid, cdf_vals)


def cdf_gue(s: np.ndarray) -> np.ndarray:
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s**2 / np.pi)


def cdf_goe(s: np.ndarray) -> np.ndarray:
    return 1 - np.exp(-np.pi * s**2 / 4)


def fit_brody_beta(spacings: np.ndarray) -> tuple[float, float]:
    """Fit Brody beta via KS minimization. Returns (beta, ks_stat)."""
    spacings = spacings[np.isfinite(spacings) & (spacings > 0)]
    if len(spacings) < 5:
        return float("nan"), float("nan")

    def ks_stat(beta: float) -> float:
        if beta < 0 or beta > 4:
            return 1e10
        try:
            result = sp_stats.kstest(spacings, lambda x: brody_cdf(x, beta))
            return float(result.statistic)
        except Exception:
            return 1e10

    # Grid search
    betas = np.linspace(0, 3, 31)
    ks_vals = [ks_stat(b) for b in betas]
    best_idx = int(np.argmin(ks_vals))
    best_beta = float(betas[best_idx])

    # Refine around best
    lo = max(0.0, best_beta - 0.1)
    hi = min(3.0, best_beta + 0.1)
    betas_fine = np.linspace(lo, hi, 21)
    ks_vals_fine = [ks_stat(b) for b in betas_fine]
    best_idx = int(np.argmin(ks_vals_fine))
    best_beta = float(betas_fine[best_idx])

    return best_beta, float(ks_vals_fine[best_idx])


def main() -> None:
    print("=" * 70)
    print("DEEP CHARACTERIZATION OF GUE OUTLIERS IN dim>=2 (non-CM)")
    print("=" * 70)

    # ── 1. Load and merge data ─────────────────────────────────────────
    print("\n[1] Loading data...")
    df_zeros = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    df_sql = pd.read_csv("data/lmfdb/lmfdb_sql_weight2_ml.csv",
                         usecols=["label", "is_cm", "is_self_dual", "char_degree",
                                  "analytic_conductor", "Nk2", "trace_mean", "trace_std", "trace_max_abs"])

    df = df_zeros.merge(df_sql, on="label", how="left")
    print(f"  Merged: {len(df)} forms")

    # ── 2. Compute GUE/GOE preference ──────────────────────────────────
    print("\n[2] Computing GUE/GOE preference...")
    zero_cols = [f"z{k}" for k in range(1, 11)]
    zeros = df[zero_cols].values
    mean_sp = df["mean_zero_spacing"].values
    spacings = np.diff(zeros, axis=1) / mean_sp[:, None]

    gue_ks = np.array([sp_stats.kstest(spacings[i], cdf_gue).statistic for i in range(len(df))])
    goe_ks = np.array([sp_stats.kstest(spacings[i], cdf_goe).statistic for i in range(len(df))])
    df["prefers_gue"] = (gue_ks < goe_ks)
    df["gue_ks"] = gue_ks
    df["goe_ks"] = goe_ks

    # Filter to dim>=2, non-CM
    d2 = df[(df["dim"] >= 2) & (df["is_cm"] == 0)].copy()
    gue = d2[d2["prefers_gue"]]
    goe = d2[~d2["prefers_gue"]]
    print(f"  dim>=2 non-CM: {len(d2)} (GUE: {len(gue)}, GOE: {len(goe)})")

    results = {}

    # ── 3. Root number analysis ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[3] ROOT NUMBER ANALYSIS")
    print("=" * 70)
    print("  (Root number = sign of functional equation: +1=even, -1=odd)")

    rn_crosstab = pd.crosstab(d2["root_number"], d2["prefers_gue"])
    print(f"\n  {'Root #':<10} {'GUE':<8} {'GOE':<8} {'Total':<8} {'GUE%':<8}")
    print("  " + "-" * 42)
    for rn in sorted(d2["root_number"].unique()):
        sub = d2[d2["root_number"] == rn]
        g = int(sub["prefers_gue"].sum())
        total = len(sub)
        print(f"  {int(rn):<10} {g:<8} {total-g:<8} {total:<8} {g/total*100:.1f}%")

    chi2_rn, p_rn, _, _ = sp_stats.chi2_contingency(rn_crosstab.values)
    or_rn, p_fisher_rn = sp_stats.fisher_exact(rn_crosstab.values)
    print(f"\n  Chi-square: chi2={chi2_rn:.2f}, p={p_rn:.4e}")
    print(f"  Fisher: OR={or_rn:.4f}, p={p_fisher_rn:.4e}")
    results["root_number"] = {"chi2": float(chi2_rn), "p": float(p_rn), "OR": float(or_rn)}

    # ── 4. Level threshold analysis ────────────────────────────────────
    print("\n" + "=" * 70)
    print("[4] LEVEL THRESHOLD ANALYSIS")
    print("=" * 70)

    level_bins = [0, 50, 100, 200, 500, 1000, 2000, 5000, 10000, float("inf")]
    level_labels = ["<50", "50-100", "100-200", "200-500", "500-1K", "1K-2K", "2K-5K", "5K-10K", "10K+"]
    d2["level_bin"] = pd.cut(d2["level"], bins=level_bins, labels=level_labels, include_lowest=True)

    print(f"\n  {'Level':<12} {'GUE':<8} {'GOE':<8} {'Total':<8} {'GUE%':<8}")
    print("  " + "-" * 44)
    level_gue_pct = []
    for label in level_labels:
        sub = d2[d2["level_bin"] == label]
        if len(sub) == 0:
            continue
        g = int(sub["prefers_gue"].sum())
        total = len(sub)
        pct = g / total * 100
        level_gue_pct.append((label, pct, g, total))
        print(f"  {label:<12} {g:<8} {total-g:<8} {total:<8} {pct:.1f}%")

    results["level_threshold"] = [{"level": l, "gue_pct": p, "gue": g, "total": t} for l, p, g, t in level_gue_pct]

    # ── 5. Dimension x level interaction ───────────────────────────────
    print("\n" + "=" * 70)
    print("[5] DIMENSION x LEVEL INTERACTION")
    print("=" * 70)

    print(f"\n  {'dim':<6} {'mean_level(GUE)':<18} {'mean_level(GOE)':<18} {'ratio':<8}")
    print("  " + "-" * 50)
    for dim_val in sorted(d2["dim"].unique())[:10]:
        g_sub = gue[gue["dim"] == dim_val]
        go_sub = goe[goe["dim"] == dim_val]
        if len(g_sub) > 0 and len(go_sub) > 0:
            ml_g = g_sub["level"].mean()
            ml_go = go_sub["level"].mean()
            ratio = ml_g / ml_go if ml_go > 0 else float("nan")
            print(f"  {dim_val:<6} {ml_g:<18.1f} {ml_go:<18.1f} {ratio:<8.3f}")

    # ── 6. Per-form Brody beta ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[6] PER-FORM BRODY BETA")
    print("=" * 70)

    # Sample: compute beta for first 500 GUE and 500 GOE (KS minimization is slow)
    n_sample = min(500, len(gue))
    gue_sample = gue.head(n_sample).copy()
    goe_sample = goe.head(n_sample).copy()

    print(f"  Computing Brody beta for {len(gue_sample)} GUE + {len(goe_sample)} GOE forms...")

    gue_betas = []
    for idx, row in gue_sample.iterrows():
        z = np.array([row[f"z{k}"] for k in range(1, 11)])
        ms = row["mean_zero_spacing"]
        sp = np.diff(z) / ms
        beta, ks = fit_brody_beta(sp)
        gue_betas.append(beta)
    gue_betas = np.array([b for b in gue_betas if not np.isnan(b)])

    goe_betas = []
    for idx, row in goe_sample.iterrows():
        z = np.array([row[f"z{k}"] for k in range(1, 11)])
        ms = row["mean_zero_spacing"]
        sp = np.diff(z) / ms
        beta, ks = fit_brody_beta(sp)
        goe_betas.append(beta)
    goe_betas = np.array([b for b in goe_betas if not np.isnan(b)])

    print(f"\n  GUE outliers (n={len(gue_betas)}):")
    print(f"    mean beta = {np.mean(gue_betas):.3f} +/- {np.std(gue_betas):.3f}")
    print(f"    median beta = {np.median(gue_betas):.3f}")
    print(f"    beta > 1.5: {np.sum(gue_betas > 1.5)} / {len(gue_betas)} ({np.sum(gue_betas > 1.5)/len(gue_betas)*100:.1f}%)")
    print(f"    beta > 1.8: {np.sum(gue_betas > 1.8)} / {len(gue_betas)} ({np.sum(gue_betas > 1.8)/len(gue_betas)*100:.1f}%)")

    print(f"\n  GOE majority (n={len(goe_betas)}):")
    print(f"    mean beta = {np.mean(goe_betas):.3f} +/- {np.std(goe_betas):.3f}")
    print(f"    median beta = {np.median(goe_betas):.3f}")
    print(f"    beta < 0.5: {np.sum(goe_betas < 0.5)} / {len(goe_betas)} ({np.sum(goe_betas < 0.5)/len(goe_betas)*100:.1f}%)")

    # Mann-Whitney U test
    u_stat, u_p = sp_stats.mannwhitneyu(gue_betas, goe_betas, alternative="greater")
    print(f"\n  Mann-Whitney U (GUE > GOE): U={u_stat:.0f}, p={u_p:.4e}")

    results["brody_beta"] = {
        "gue_mean": float(np.mean(gue_betas)),
        "gue_median": float(np.median(gue_betas)),
        "gue_std": float(np.std(gue_betas)),
        "goe_mean": float(np.mean(goe_betas)),
        "goe_median": float(np.median(goe_betas)),
        "goe_std": float(np.std(goe_betas)),
        "mannwhitney_p": float(u_p),
    }

    # ── 7. Analytic rank analysis ──────────────────────────────────────
    print("\n" + "=" * 70)
    print("[7] ANALYTIC RANK ANALYSIS")
    print("=" * 70)

    print(f"\n  {'rank':<8} {'GUE':<8} {'GOE':<8} {'Total':<8} {'GUE%':<8}")
    print("  " + "-" * 40)
    for rank in sorted(d2["analytic_rank"].unique()):
        sub = d2[d2["analytic_rank"] == rank]
        g = int(sub["prefers_gue"].sum())
        total = len(sub)
        print(f"  {int(rank):<8} {g:<8} {total-g:<8} {total:<8} {g/total*100:.1f}%")

    # ── 8. Trace statistics ────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[8] TRACE STATISTICS")
    print("=" * 70)

    trace_features = ["trace_mean", "trace_std", "trace_max_abs"]
    print(f"\n  {'Feature':<18} {'GUE(mean)':<12} {'GOE(mean)':<12} {'ratio':<8} {'p-value':<12}")
    print("  " + "-" * 58)
    for feat in trace_features:
        if feat in d2.columns:
            g_vals = gue[feat].dropna().values
            go_vals = goe[feat].dropna().values
            if len(g_vals) > 0 and len(go_vals) > 0:
                g_mean = np.mean(g_vals)
                go_mean = np.mean(go_vals)
                ratio = g_mean / go_mean if go_mean != 0 else float("inf")
                _, pval = sp_stats.mannwhitneyu(g_vals, go_vals, alternative="two-sided")
                print(f"  {feat:<18} {g_mean:<12.4f} {go_mean:<12.4f} {ratio:<8.3f} {pval:<12.4e}")
                results[f"trace_{feat}"] = {"gue_mean": float(g_mean), "goe_mean": float(go_mean), "p": float(pval)}

    # ── 9. Logistic regression ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[9] LOGISTIC REGRESSION: Predicting GUE preference")
    print("=" * 70)

    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score

    features = ["dim", "level", "analytic_rank", "root_number", "analytic_conductor", "Nk2"]
    # Add trace_mean if available (trace_std and trace_max_abs are all NaN in the data)
    if "trace_mean" in d2.columns and d2["trace_mean"].notna().sum() > 0:
        features.append("trace_mean")

    X = d2[features].dropna()
    y = d2.loc[X.index, "prefers_gue"].astype(int)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    lr = LogisticRegression(max_iter=1000, class_weight="balanced")
    scores = cross_val_score(lr, X_scaled, y, cv=5, scoring="roc_auc")
    lr.fit(X_scaled, y)

    print(f"\n  Features: {features}")
    print(f"  5-fold CV AUC: {scores.mean():.3f} +/- {scores.std():.3f}")
    print(f"\n  Coefficients (standardized):")
    for feat, coef in sorted(zip(features, lr.coef_[0]), key=lambda x: abs(x[1]), reverse=True):
        print(f"    {feat:<20} {coef:+.4f}")

    results["logistic_regression"] = {
        "features": features,
        "cv_auc_mean": float(scores.mean()),
        "cv_auc_std": float(scores.std()),
        "coefficients": {f: float(c) for f, c in zip(features, lr.coef_[0])},
    }

    # ── 10. Nearest-neighbor spacing ratio ─────────────────────────────
    print("\n" + "=" * 70)
    print("[10] NEAREST-NEIGHBOR SPACING RATIO (level repulsion)")
    print("=" * 70)

    # Ratio of consecutive spacings: s_{n+1}/s_n
    # GUE has strong repulsion (ratio tends to be large), Poisson has none
    def spacing_ratios(zeros_row, mean_sp):
        z = np.array([zeros_row[f"z{k}"] for k in range(1, 11)])
        sp = np.diff(z) / mean_sp
        ratios = sp[1:] / sp[:-1]
        return ratios[ratios > 0]

    gue_ratios = []
    for _, row in gue.iterrows():
        r = spacing_ratios(row, row["mean_zero_spacing"])
        gue_ratios.extend(r)
    goe_ratios = []
    for _, row in goe.iterrows():
        r = spacing_ratios(row, row["mean_zero_spacing"])
        goe_ratios.extend(r)

    gue_ratios = np.array(gue_ratios)
    goe_ratios = np.array(goe_ratios)

    # For GUE, the ratio distribution has a peak near 1 (repulsion)
    # For Poisson, the ratio distribution is broader
    gue_small_ratio = np.mean(gue_ratios < 0.5) * 100
    goe_small_ratio = np.mean(goe_ratios < 0.5) * 100
    print(f"\n  GUE outliers: mean ratio = {np.mean(gue_ratios):.3f}, % ratios < 0.5 = {gue_small_ratio:.1f}%")
    print(f"  GOE majority: mean ratio = {np.mean(goe_ratios):.3f}, % ratios < 0.5 = {goe_small_ratio:.1f}%")
    print(f"  (Low ratios indicate weak repulsion; GUE should have fewer small ratios)")

    u_stat, u_p = sp_stats.mannwhitneyu(gue_ratios, goe_ratios, alternative="two-sided")
    print(f"  Mann-Whitney U: p={u_p:.4e}")

    results["spacing_ratios"] = {
        "gue_mean": float(np.mean(gue_ratios)),
        "goe_mean": float(np.mean(goe_ratios)),
        "gue_pct_small": float(gue_small_ratio),
        "goe_pct_small": float(goe_small_ratio),
        "p": float(u_p),
    }

    # ── 11. Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[11] SUMMARY")
    print("=" * 70)

    # Find the strongest predictor
    coefs = dict(zip(features, lr.coef_[0]))
    strongest = max(coefs, key=lambda k: abs(coefs[k]))
    print(f"\n  Strongest predictor of GUE preference: {strongest} (coef={coefs[strongest]:+.4f})")
    print(f"  Logistic regression AUC: {scores.mean():.3f}")
    print(f"\n  Root number: chi2={chi2_rn:.2f}, p={p_rn:.4e}, OR={or_rn:.3f}")
    print(f"  Brody beta: GUE={np.mean(gue_betas):.3f}, GOE={np.mean(goe_betas):.3f} (p={u_p:.4e})")
    print(f"  Spacing ratios: GUE={np.mean(gue_ratios):.3f}, GOE={np.mean(goe_ratios):.3f}")

    # ── 12. Save results ───────────────────────────────────────────────
    output_dir = Path("data/results")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "gue_outlier_deep_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: data/results/gue_outlier_deep_analysis.json")

    # ── 13. Figures ────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    # (a) Level threshold
    ax = axes[0, 0]
    labels_l = [x[0] for x in level_gue_pct]
    pcts_l = [x[1] for x in level_gue_pct]
    ax.bar(range(len(pcts_l)), pcts_l, color="#1f77b4", alpha=0.8)
    ax.set_xticks(range(len(labels_l)))
    ax.set_xticklabels(labels_l, rotation=45, ha="right")
    ax.set_ylabel("GUE preference (%)")
    ax.set_title("(a) GUE% by conductor level (dim>=2, non-CM)")
    ax.axhline(y=6.0, color="red", linestyle="--", alpha=0.5, label="baseline 6%")
    ax.legend()

    # (b) Root number
    ax = axes[0, 1]
    rn_labels = [int(rn) for rn in sorted(d2["root_number"].unique())]
    rn_gue = []
    rn_goe = []
    for rn in rn_labels:
        sub = d2[d2["root_number"] == rn]
        g = int(sub["prefers_gue"].sum())
        rn_gue.append(g)
        rn_goe.append(len(sub) - g)
    ax.bar([f"+1", f"-1"], [g/total*100 for g, total in zip(rn_gue, [rn_gue[i]+rn_goe[i] for i in range(len(rn_gue))])], color=["#2ca02c", "#d62728"], alpha=0.8)
    ax.set_ylabel("GUE preference (%)")
    ax.set_title("(b) GUE% by root number")

    # (c) Brody beta histogram
    ax = axes[0, 2]
    ax.hist(gue_betas, bins=30, alpha=0.6, label=f"GUE (mean={np.mean(gue_betas):.2f})", color="#1f77b4", density=True)
    ax.hist(goe_betas, bins=30, alpha=0.6, label=f"GOE (mean={np.mean(goe_betas):.2f})", color="#ff7f0e", density=True)
    ax.axvline(x=2.0, color="red", linestyle="--", alpha=0.5, label="GUE beta=2")
    ax.axvline(x=0.0, color="gray", linestyle="--", alpha=0.5, label="Poisson beta=0")
    ax.set_xlabel("Brody beta")
    ax.set_ylabel("Density")
    ax.set_title("(c) Per-form Brody beta distribution")
    ax.legend(fontsize=8)

    # (d) Dimension x GUE%
    ax = axes[1, 0]
    dims = sorted(d2["dim"].unique())[:10]
    dim_gue_pct = []
    for d in dims:
        sub = d2[d2["dim"] == d]
        dim_gue_pct.append(sub["prefers_gue"].mean() * 100)
    ax.bar(range(len(dims)), dim_gue_pct, color="#9467bd", alpha=0.8)
    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels(dims)
    ax.set_xlabel("Dimension")
    ax.set_ylabel("GUE preference (%)")
    ax.set_title("(d) GUE% by dimension (non-CM, dim>=2)")
    ax.axhline(y=6.0, color="red", linestyle="--", alpha=0.5)

    # (e) Logistic regression coefficients
    ax = axes[1, 1]
    sorted_coefs = sorted(zip(features, lr.coef_[0]), key=lambda x: abs(x[1]), reverse=True)
    feat_names = [x[0] for x in sorted_coefs]
    coef_vals = [x[1] for x in sorted_coefs]
    colors = ["#2ca02c" if c > 0 else "#d62728" for c in coef_vals]
    ax.barh(range(len(feat_names)), coef_vals, color=colors, alpha=0.8)
    ax.set_yticks(range(len(feat_names)))
    ax.set_yticklabels(feat_names, fontsize=8)
    ax.set_xlabel("Coefficient (standardized)")
    ax.set_title(f"(e) Logistic regression (AUC={scores.mean():.3f})")

    # (f) Spacing ratio histogram
    ax = axes[1, 2]
    ax.hist(gue_ratios, bins=50, alpha=0.6, label=f"GUE (mean={np.mean(gue_ratios):.2f})", color="#1f77b4", density=True)
    ax.hist(goe_ratios, bins=50, alpha=0.6, label=f"GOE (mean={np.mean(goe_ratios):.2f})", color="#ff7f0e", density=True)
    ax.set_xlabel("Spacing ratio s_{n+1}/s_n")
    ax.set_ylabel("Density")
    ax.set_title("(f) Nearest-neighbor spacing ratio")
    ax.legend(fontsize=8)
    ax.set_xlim(0, 5)

    plt.tight_layout()
    fig_path = "papers/gue_outlier_deep_analysis.png"
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Figure saved to: {fig_path}")


if __name__ == "__main__":
    main()
