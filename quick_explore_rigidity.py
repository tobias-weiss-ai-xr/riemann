"""Quick explore: spectral rigidity results + zero spacing data structure"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

# Spectral rigidity results
with open("data/spectral_rigidity/spectral_rigidity_results.json") as f:
    d = json.load(f)

print("=== Spectral Rigidity Results ===")
for k in ["spacing_distribution", "spacing_d1", "spacing_d2",
           "ratio_distribution", "ratio_d1", "ratio_d2"]:
    if k in d:
        v = d[k]
        print(f"  {k}: N={v['N']:,}, mean={v['mean']:.4f}, "
              f"best={v['best_fit']}, KS_GUE={v['ks_gue_stat']:.4f}")

nv = d.get("number_variance", {})
if nv:
    print(f"\n  Number variance keys: {list(nv.keys())[:5]}")
    print(f"  Sample L vals: {nv['L_vals'][:5]}")
    print(f"  Sample Sigma2: {nv['Sigma2_observed'][:5]}")

meta = d.get("metadata", {})
print(f"\n  Metadata: {json.dumps(meta, indent=4)}")

# Zero spacing CSV
print("\n\n=== Zero Spacing CSV ===")
df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
print(f"  Shape: {df.shape}")
print(f"  Columns: {list(df.columns)[:20]}...")
print(f"  dim: {df['dim'].value_counts().sort_index().to_dict()}")
print(f"  analytic_rank: {df['analytic_rank'].value_counts().sort_index().to_dict()}")

# Check for P(r) features — per-form ratio statistics
print("\n  Computing per-form spacing ratios...")
zero_cols = [f"z{k}" for k in range(1, 11)]
valid = df.dropna(subset=zero_cols).copy()
zeros = valid[zero_cols].values  # (N, 10)
mean_sp = valid["mean_zero_spacing"].values

# Per-form unfolded spacings
spacings = np.diff(zeros, axis=1) / mean_sp[:, None]  # (N, 9)
ratios = spacings[:, 1:] / spacings[:, :-1]  # (N, 8)

# Per-form mean ratio <r> and std of ratios
import numpy as np
valid["mean_ratio"] = np.nanmean(ratios, axis=1)
valid["std_ratio"] = np.nanstd(ratios, axis=1)
valid["mean_spacing"] = np.nanmean(spacings, axis=1)
valid["std_spacing"] = np.nanstd(spacings, axis=1)

print(f"  mean_ratio overall: {valid['mean_ratio'].mean():.4f} +/- {valid['mean_ratio'].std():.4f}")
print(f"  mean_ratio dim=1: {valid[valid['dim']==1]['mean_ratio'].mean():.4f}")
print(f"  mean_ratio dim>=2: {valid[valid['dim']>=2]['mean_ratio'].mean():.4f}")
print(f"  mean_ratio rank=0: {valid[valid['analytic_rank']==0]['mean_ratio'].mean():.4f}")
print(f"  mean_ratio rank=1: {valid[valid['analytic_rank']==1]['mean_ratio'].mean():.4f}")

# Per-form KS analysis
from scipy import stats as sp_stats
from scipy.special import erf

def cdf_gue(s):
    return erf(2*s/np.sqrt(np.pi)) - (4*s/np.pi)*np.exp(-4*s**2/np.pi)

def cdf_goe(s):
    return 1 - np.exp(-np.pi*s**2/4)

print("\n=== Per-form KS analysis ===")
gue_ks = np.array([sp_stats.kstest(spacings[i], cdf_gue).statistic for i in range(len(spacings))])
goe_ks = np.array([sp_stats.kstest(spacings[i], cdf_goe).statistic for i in range(len(spacings))])
prefers_gue = (gue_ks < goe_ks).astype(int)
print(f"  Prefer GUE: {prefers_gue.sum()} ({prefers_gue.mean()*100:.1f}%)")
print(f"  Prefer GOE: {(1-prefers_gue).sum()} ({(1-prefers_gue).mean()*100:.1f}%)")
d1_mask = valid['dim']==1
d2_mask = valid['dim']>=2
print(f"  Dim=1 prefer GUE: {prefers_gue[d1_mask].mean()*100:.1f}%")
print(f"  Dim>=2 prefer GUE: {prefers_gue[d2_mask].mean()*100:.1f}%")

# Within dim>=2: can we predict GUE preference from traces?
print("\n=== Dim>=2: Trace features vs GUE preference ===")
d2 = valid[d2_mask].copy()
d2['prefers_gue'] = prefers_gue[d2_mask]
d2_gue = d2[d2['prefers_gue']==1]
d2_goe = d2[d2['prefers_gue']==0]
print(f"  dim>=2 forms that prefer GUE: {len(d2_gue)}")
print(f"  dim>=2 forms that prefer GOE: {len(d2_goe)}")
# Check dim distribution within each
print(f"  GUE-preferring dim dist: {d2_gue['dim'].value_counts().sort_index().head(10).to_dict()}")
print(f"  GOE-preferring dim dist: {d2_goe['dim'].value_counts().sort_index().head(10).to_dict()}")

# Brody-style: compute mean_ratio for each dim
print("\n=== mean_ratio by dimension ===")
from scipy.optimize import curve_fit
for dim in range(1, 11):
    subset = valid[valid['dim']==dim]
    r = subset['mean_ratio'].values
    r = r[(r > 0.01) & (r < 10)]  # filter extremes
    print(f"  dim={dim}: N={len(subset):,}, mean_r={np.mean(r):.4f}, median_r={np.median(r):.4f}")

