"""
Analyze the 6% GUE outliers within dim>=2 forms from Task 5 results.

Goal: Characterize which arithmetic properties distinguish the 1,748 dim>=2
forms that prefer GUE spacing over Poisson.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd
from pathlib import Path

# Load Task 5 results
results_path = Path("data/results/task_5_spectral_rigidity_bridge_results.json")
with open(results_path) as f:
    results = json.load(f)

# Load the full dataset
df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")

# Recompute per-form metrics to get the actual labels
from scipy import stats as sp_stats
from scipy.special import erf

def cdf_gue(s):
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s**2 / np.pi)

def cdf_goe(s):
    return 1 - np.exp(-np.pi * s**2 / 4)

# Extract zeros and compute spacings
zero_cols = [f"z{k}" for k in range(1, 11)]
zeros = df[zero_cols].values
mean_zero_spacing = df["mean_zero_spacing"].values

spacings = np.diff(zeros, axis=1) / mean_zero_spacing[:, None]

gue_ks = np.array([sp_stats.kstest(spacings[i], cdf_gue).statistic for i in range(len(df))])
goe_ks = np.array([sp_stats.kstest(spacings[i], cdf_goe).statistic for i in range(len(df))])

prefers_gue = (gue_ks < goe_ks).astype(bool)
dims = df["dim"].values.astype(int)

# Filter: dim >= 2
d2_mask = dims >= 2
d2_df = df[d2_mask].copy()
d2_df["prefers_gue"] = prefers_gue[d2_mask]

print(f"Total dim>=2 forms: {len(d2_df)}")
print(f"GUE preferrers: {d2_df['prefers_gue'].sum()} ({d2_df['prefers_gue'].mean()*100:.1f}%)")

# Separate into groups
gue_group = d2_df[d2_df["prefers_gue"]]
goe_group = d2_df[~d2_df["prefers_gue"]]

print(f"\nGUE group: {len(gue_group)}")
print(f"GOE group: {len(goe_group)}")

# ============================================================
# COMPARISON TABLE
# ============================================================
print("\n" + "="*70)
print("ARITHMETIC PROPERTIES: GUE outliers vs GOE majority (dim>=2)")
print("="*70)

features = ["level", "dim", "analytic_rank", "char_order", "mean_zero_spacing"]

print(f"\n{'Feature':<25} {'GUE (mean)':<15} {'GOE (mean)':<15} {'Ratio':<10} {'p-value':<10}")
print("-"*70)

for feat in features:
    gue_vals = gue_group[feat].values
    goe_vals = goe_group[feat].values
    
    gue_mean = np.mean(gue_vals)
    goe_mean = np.mean(goe_vals)
    
    if goe_mean != 0 and np.abs(goe_mean) > 1e-10:
        ratio = gue_mean / goe_mean
    else:
        ratio = float('inf') if gue_mean != 0 else 1.0
    
    # T-test
    if len(gue_vals) >= 2 and len(goe_vals) >= 2:
        try:
            _, pval = sp_stats.ttest_ind(gue_vals, goe_vals, equal_var=False)
        except:
            pval = float('nan')
    else:
        pval = float('nan')
    
    print(f"{feat:<25} {gue_mean:<15.4f} {goe_mean:<15.4f} {ratio:<10.3f} {pval:<10.4f}")

# Level distribution
print("\n" + "="*70)
print("LEVEL DISTRIBUTION")
print("="*70)

level_bins = [0, 100, 500, 1000, 5000, 10000, float('inf')]
level_labels = ["0-100", "100-500", "500-1K", "1K-5K", "5K-10K", "10K+"]

d2_df["level_bin"] = pd.cut(d2_df["level"], bins=level_bins, labels=level_labels, include_lowest=True)
level_counts = d2_df.groupby(["level_bin", "prefers_gue"]).size().unstack(fill_value=0)
level_counts["gue_pct"] = level_counts[True] / level_counts.sum(axis=1) * 100

print(level_counts)
print(f"\nOverall GUE percentage: {d2_df['prefers_gue'].mean()*100:.1f}%")

# Dimension distribution
print("\n" + "="*70)
print("DIMENSION DISTRIBUTION")
print("="*70)

dim_counts = d2_df.groupby(["dim", "prefers_gue"]).size().unstack(fill_value=0)
dim_counts["gue_pct"] = dim_counts[True] / dim_counts.sum(axis=1) * 100

print(dim_counts.head(15))  # Show first 15 dimensions
print(f"\nOverall GUE percentage: {d2_df['prefers_gue'].mean()*100:.1f}%")

# Analytic rank distribution
print("\n" + "="*70)
print("ANALYTIC RANK DISTRIBUTION")
print("="*70)

rank_counts = d2_df.groupby(["analytic_rank", "prefers_gue"]).size().unstack(fill_value=0)
rank_counts["gue_pct"] = rank_counts[True] / rank_counts.sum(axis=1) * 100

print(rank_counts)
print(f"\nOverall GUE percentage: {d2_df['prefers_gue'].mean()*100:.1f}%")

# CM form analysis
if "is_cm" in d2_df.columns:
    print("\n" + "="*70)
    print("CM FORM ANALYSIS")
    print("="*70)
    
    cm_counts = d2_df.groupby(["is_cm", "prefers_gue"]).size().unstack(fill_value=0)
    cm_counts["gue_pct"] = cm_counts[True] / cm_counts.sum(axis=1) * 100
    
    print(cm_counts)
    print(f"\nOverall GUE percentage: {d2_df['prefers_gue'].mean()*100:.1f}%")
else:
    print("\n'Note: is_cm column not available in dataset'")

# Top 10 smallest level GUE outliers
print("\n" + "="*70)
print("TOP 10 SMALLEST LEVEL GUE OUTLIERS (dim>=2)")
print("="*70)

smallest_gue = gue_group.nsmallest(10, "level")
print(smallest_gue[["level", "dim", "analytic_rank", "char_order"]])

# Top 10 smallest dimension GUE outliers
print("\n" + "="*70)
print("TOP 10 SMALLEST DIMENSION GUE OUTLIERS")
print("="*70)

# These are already dim>=2, so show smallest among them
smallest_dim_gue = gue_group.nsmallest(10, "dim")
print(smallest_dim_gue[["level", "dim", "analytic_rank", "char_order"]])

# Correlation analysis
print("\n" + "="*70)
print("CORRELATION WITH GUE PREFERENCE")
print("="*70)

correlations = {}
for feat in features + ["prefers_gue"]:
    if feat != "prefers_gue":
        corr, pval = sp_stats.pearsonr(d2_df[feat], d2_df["prefers_gue"])
        correlations[feat] = (corr, pval)

for feat, (corr, pval) in sorted(correlations.items(), key=lambda x: abs(x[1][0]), reverse=True):
    print(f"  {feat}: r={corr:.4f}, p={pval:.4e}")

# Save outliers for further analysis
output_dir = Path("data/results")
output_dir.mkdir(exist_ok=True)

# Save GUE outliers
outlier_path = output_dir / "gue_outliers_dim2.csv"
gue_group.to_csv(outlier_path, index=False)
print(f"\n\nSaved GUE outliers to: {outlier_path}")

# Save comparison
comparison = {
    "gue_group": {
        "count": int(len(gue_group)),
        "level_mean": float(gue_group["level"].mean()),
        "level_std": float(gue_group["level"].std()),
        "level_min": float(gue_group["level"].min()),
        "level_max": float(gue_group["level"].max()),
        "dim_mean": float(gue_group["dim"].mean()),
        "dim_std": float(gue_group["dim"].std()),
        "dim_min": int(gue_group["dim"].min()),
        "dim_max": int(gue_group["dim"].max()),
        "rank_mean": float(gue_group["analytic_rank"].mean()),
    },
    "goe_group": {
        "count": int(len(goe_group)),
        "level_mean": float(goe_group["level"].mean()),
        "level_std": float(goe_group["level"].std()),
        "level_min": float(goe_group["level"].min()),
        "level_max": float(goe_group["level"].max()),
        "dim_mean": float(goe_group["dim"].mean()),
        "dim_std": float(goe_group["dim"].std()),
        "dim_min": int(goe_group["dim"].min()),
        "dim_max": int(goe_group["dim"].max()),
        "rank_mean": float(goe_group["analytic_rank"].mean()),
    }
}

comparison_path = output_dir / "gue_outliers_comparison.json"
with open(comparison_path, "w") as f:
    json.dump(comparison, f, indent=2)

print(f"Saved comparison to: {comparison_path}")

# ============================================================
# LOGISTIC REGRESSION: What predicts GUE preference?
# ============================================================
print("\n" + "="*70)
print("LOGISTIC REGRESSION: PREDICTING GUE PREFERENCE FROM METADATA")
print("="*70)

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

# Prepare features
feature_cols = ["level", "dim", "analytic_rank", "char_order"]
X = d2_df[feature_cols].values
y = d2_df["prefers_gue"].values.astype(int)

# Fit logistic regression
pipe = make_pipeline(StandardScaler(), LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=1000))
pipe.fit(X, y)

# Get coefficients
scaler = pipe.named_steps["standardscaler"]
lr = pipe.named_steps["logisticregression"]

feature_means = scaler.mean_
feature_stds = scaler.scale_

print("\nLogistic regression coefficients (standardized):")
print(f"{'Feature':<20} {'Coef':<10} {'Odds Ratio':<12} {'p-value (approx)':<15}")
print("-"*60)

for i, feat in enumerate(feature_cols):
    coef = lr.coef_[0][i]
    odds_ratio = np.exp(coef)
    # Approximate p-value (Wald test) - simplified
    pval = "N/A"
    
    print(f"{feat:<20} {coef:<10.4f} {odds_ratio:<12.4f} {pval:<15}")

print(f"\nIntercept: {lr.intercept_[0]:.4f}")
print(f"Training accuracy: {pipe.score(X, y):.4f}")

# Confusion matrix
from sklearn.metrics import confusion_matrix, classification_report

y_pred = pipe.predict(X)
print(f"\nConfusion matrix:")
print(confusion_matrix(y, y_pred))
print(f"\nClassification report:")
print(classification_report(y, y_pred, target_names=["GOE", "GUE"]))
