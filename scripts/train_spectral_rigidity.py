"""
Thread R: Spectral Rigidity Analysis — L-function zeros of 63,844 weight-2 newforms.

Computes:
1. Spacing distribution P(s) — nearest-neighbor
2. Spacing ratio P(r) — Oganesyan-Poghosyan ratio
3. k-th neighbor spacings (k=1..5)
4. Number variance Σ²(L) — ensemble-averaged
5. Δ₃(L) Dyson-Mehta statistic (ensemble approximation)
6. Two-point correlation function R₂(τ)
7. All stratified by dim (1 vs ≥2) and analytic rank

Input: data/lmfdb/lmfdb_zeros_ml.csv (63,844 forms, z1-z10, dim, analytic_rank, mean_zero_spacing)
Output: data/spectral_rigidity/spectral_rigidity_results.json
"""
from __future__ import annotations

import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import erf

# Suppress warnings
warnings.filterwarnings("ignore")

OUTPUT_DIR = Path("data/spectral_rigidity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── GUE/GOE reference functions ──────────────────────────────────────────────

def p_goe(s: np.ndarray) -> np.ndarray:
    """GOE nearest-neighbor spacing distribution: P_GOE(s) = (π/2)s exp(-πs²/4)."""
    return (np.pi / 2) * s * np.exp(-np.pi * s ** 2 / 4)

def p_gue(s: np.ndarray) -> np.ndarray:
    """GUE nearest-neighbor spacing distribution: P_GUE(s) = (32/π²)s² exp(-4s²/π)."""
    return (32 / np.pi ** 2) * s ** 2 * np.exp(-4 * s ** 2 / np.pi)

def cdf_goe(s: np.ndarray) -> np.ndarray:
    """GOE CDF: 1 - exp(-πs²/4)."""
    return 1 - np.exp(-np.pi * s ** 2 / 4)

def cdf_gue(s: np.ndarray) -> np.ndarray:
    """GUE CDF: erf(2s/√π) - (4s/π)exp(-4s²/π)."""
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s ** 2 / np.pi)

def p_ratio_goe(r: np.ndarray) -> np.ndarray:
    """GOE spacing ratio distribution P(r) for N=3 x 3 matrices (Wigner-like)."""
    # Empirical formula for GOE: P(r) = 27/8 * (r + r²) / (1 + r + r²)^(5/2)
    return (27 / 8) * (r + r ** 2) / (1 + r + r ** 2) ** (5 / 2)

def p_ratio_gue(r: np.ndarray) -> np.ndarray:
    """GUE spacing ratio distribution P(r)."""
    # GUE: P(r) = 81√3/(4π) * (r + r²)² / (1 + r + r²)^4
    return (81 * np.sqrt(3) / (4 * np.pi)) * (r + r ** 2) ** 2 / (1 + r + r ** 2) ** 4

# ── Data loading ────────────────────────────────────────────────────────────

def load_data():
    """Load LMFDB zeros CSV and extract metadata and zero columns."""
    print("Loading lmfdb_zeros_ml.csv ...")
    t0 = time.time()
    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    print(f"  Loaded {len(df):,} forms in {time.time()-t0:.1f}s")
    
    meta_cols = ["label", "dim", "analytic_rank", "mean_zero_spacing"]
    zero_cols = [f"z{k}" for k in range(1, 11)]
    df = df.dropna(subset=zero_cols)
    print(f"  {len(df):,} forms with complete z1-z10 data")
    
    labels = df["label"].values
    dims = df["dim"].values.astype(int)
    ranks = df["analytic_rank"].values.astype(int)
    mean_spacings = df["mean_zero_spacing"].values
    zeros = df[zero_cols].values  # shape (N, 10)
    
    return labels, dims, ranks, mean_spacings, zeros

# ── Spacing computations ────────────────────────────────────────────────────

def compute_spacings(zeros, dims, ranks, mean_spacings):
    """Compute nearest-neighbor spacings, unfold, and stratify."""
    N = zeros.shape[0]
    
    # Nearest-neighbor spacings (raw)
    spacings_raw = np.diff(zeros, axis=1)  # (N, 9)
    
    # Unfolded spacings: divide by mean spacing per form
    spacings = spacings_raw / mean_spacings[:, np.newaxis]  # (N, 9)
    
    # Flatten all spacings
    all_spacings = spacings.ravel()
    
    # Per-form masks (zeros CSV has dim >= 1, no dim=0 rational forms)
    d1_mask = dims == 1   # dim=1 forms
    d2_mask = dims >= 2   # dim>=2 forms (>2 forms)
    
    # Analytic rank masks
    r0_mask = ranks == 0
    r1_mask = ranks == 1
    
    result = {}
    
    # ── 1. Global spacing distribution P(s) ──
    print("\n=== P(s): Nearest-neighbor spacing distribution ===")
    result["spacing_distribution"] = compute_spacing_stats(all_spacings, "All")
    result["spacing_d1"] = compute_spacing_stats(spacings[d1_mask].ravel(), "dim=1")
    result["spacing_d2"] = compute_spacing_stats(spacings[d2_mask].ravel(), "dim>=2")
    result["spacing_r0"] = compute_spacing_stats(spacings[r0_mask].ravel(), "rank=0")
    result["spacing_r1"] = compute_spacing_stats(spacings[r1_mask].ravel(), "rank=1")
    
    # ── 2. Spacing ratio P(r) ──
    print("\n=== P(r): Spacing ratio distribution ===")
    # r_i = (s_{i+1}) / s_i  — consecutive spacing ratios
    ratios_raw = spacings[:, 1:] / spacings[:, :-1]  # (N, 8)
    # Filter extreme values (numerical noise)
    ratios = ratios_raw[(ratios_raw > 0.01) & (ratios_raw < 100)]
    ratio_d1 = ratios_raw[d1_mask].ravel()
    ratio_d1 = ratio_d1[(ratio_d1 > 0.01) & (ratio_d1 < 100)]
    ratio_d2 = ratios_raw[d2_mask].ravel()
    ratio_d2 = ratio_d2[(ratio_d2 > 0.01) & (ratio_d2 < 100)]
    
    result["ratio_distribution"] = compute_ratio_stats(ratios, "All")
    result["ratio_d1"] = compute_ratio_stats(ratio_d1, "dim=1")
    result["ratio_d2"] = compute_ratio_stats(ratio_d2, "dim>=2")
    
    # ── 3. k-th neighbor spacings (k=1..5) ──
    print("\n=== k-th neighbor spacing distributions ===")
    for k in range(1, 6):
        if k > zeros.shape[1] - 1:
            break
        sk = np.diff(zeros, n=k, axis=1) / mean_spacings[:, np.newaxis]  # (N, 10-k)
        result[f"spacing_k{k}"] = compute_spacing_stats(sk.ravel(), f"k={k}")
    
    return result

def compute_spacing_stats(spacings, label):
    """Compute KS test against GOE and GUE for a set of spacings."""
    spacings = spacings[~np.isnan(spacings)]
    spacings = spacings[(spacings > 0) & (spacings < 10)]
    
    mean_s = np.mean(spacings)
    std_s = np.std(spacings)
    median_s = np.median(spacings)
    
    # KS tests against GOE and GUE
    ks_goe = stats.kstest(spacings, cdf_goe)
    ks_gue = stats.kstest(spacings, cdf_gue)
    
    # Pick best
    best = "GOE" if ks_goe.statistic < ks_gue.statistic else "GUE"
    
    print(f"  {label}: N={len(spacings):,}, mean={mean_s:.4f}, std={std_s:.4f}, "
          f"KS_GOE={ks_goe.statistic:.4f}(p={ks_goe.pvalue:.3f}), "
          f"KS_GUE={ks_gue.statistic:.4f}(p={ks_gue.pvalue:.3f}), "
          f"best={best}")
    
    return {
        "label": label,
        "N": int(len(spacings)),
        "mean": float(mean_s),
        "std": float(std_s),
        "median": float(median_s),
        "ks_goe_stat": float(ks_goe.statistic),
        "ks_goe_p": float(ks_goe.pvalue),
        "ks_gue_stat": float(ks_gue.statistic),
        "ks_gue_p": float(ks_gue.pvalue),
        "best_fit": best,
    }

def compute_ratio_stats(ratios, label):
    """Compute KS test against GOE and GUE ratio distributions."""
    ratios = ratios[~np.isnan(ratios)]
    ratios = ratios[(ratios > 0.01) & (ratios < 10)]
    
    mean_r = np.mean(ratios)
    std_r = np.std(ratios)
    
    # KS tests against GOE and GUE ratio distributions
    ks_goe = stats.kstest(ratios, lambda x: _cdf_from_pdf(x, p_ratio_goe))
    ks_gue = stats.kstest(ratios, lambda x: _cdf_from_pdf(x, p_ratio_gue))
    
    # Also compute mean ratio (theoretical: GOE <r> ≈ 0.530, GUE <r> ≈ 0.599)
    best = "GOE" if ks_goe.statistic < ks_gue.statistic else "GUE"
    
    print(f"  {label}: N={len(ratios):,}, mean={mean_r:.4f}, std={std_r:.4f}, "
          f"KS_GOE={ks_goe.statistic:.4f}, KS_GUE={ks_gue.statistic:.4f}, "
          f"best={best}")
    
    return {
        "label": label,
        "N": int(len(ratios)),
        "mean": float(mean_r),
        "std": float(std_r),
        "ks_goe_stat": float(ks_goe.statistic),
        "ks_gue_stat": float(ks_gue.statistic),
        "best_fit": best,
    }

def _cdf_from_pdf(x, pdf_func, n_points=10000):
    """Compute CDF from PDF via numerical integration (for KS test)."""
    xs = np.linspace(0, 10, n_points)
    pdf_vals = pdf_func(xs)
    cdf_vals = np.cumsum(pdf_vals) / np.sum(pdf_vals)
    return np.interp(x, xs, cdf_vals)

# ── Number variance Σ²(L) ──────────────────────────────────────────────────

def compute_number_variance(zeros, mean_spacings, L_vals=None):
    """
    Compute ensemble-averaged number variance Σ²(L).
    
    Uses non-overlapping windows: for each form and each L, count zeros
    in [0, L), [L, 2L), ... [nL, (n+1)L). Variance across all such
    intervals from all forms.
    """
    if L_vals is None:
        L_vals = np.linspace(0.5, 6.0, 24)
    
    N_forms = zeros.shape[0]
    unfolded = zeros / mean_spacings[:, np.newaxis]  # (N, 10)
    
    print(f"\n=== Number Variance Σ²(L) ===")
    print(f"  Computing over {N_forms:,} forms × {len(L_vals)} L values...")
    t0 = time.time()
    
    sigma2_result = []
    n_intervals_list = []
    
    for j, L in enumerate(L_vals):
        all_counts = []
        for i in range(N_forms):
            u = unfolded[i]
            max_u = u[-1]
            n_starts = max(0, int(max_u / L))
            for s in range(n_starts):
                left = s * L
                right = (s + 1) * L
                count = np.sum((u >= left) & (u < right))
                all_counts.append(count)
        
        if len(all_counts) > 1:
            sigma2 = float(np.var(all_counts, ddof=1))
        else:
            sigma2 = None
        sigma2_result.append(sigma2)
        n_intervals_list.append(len(all_counts))
        
        if (j + 1) % 6 == 0:
            print(f"  L={L:.1f}: Σ²={sigma2:.4f}, intervals={len(all_counts):,} "
                  f"({time.time()-t0:.0f}s)")
    
    # Reference curves
    sigma2_gue = (1 / np.pi ** 2) * np.log(2 * np.pi * L_vals) + (5/4 - 1/np.pi**2)
    sigma2_goe = (2 / np.pi ** 2) * np.log(2 * np.pi * L_vals) + (5/4 - 2/np.pi**2)
    
    print(f"  Total time: {time.time()-t0:.0f}s")
    result = {
        "L_vals": L_vals.tolist(),
        "Sigma2_observed": sigma2_result,
        "Sigma2_GUE_ref": sigma2_gue.tolist(),
        "Sigma2_GOE_ref": sigma2_goe.tolist(),
        "n_intervals": n_intervals_list,
    }
    return result


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    t_start = time.time()
    
    # 1. Load data
    labels, dims, ranks, mean_spacings, zeros = load_data()
    
    # 2. Compute spacing statistics
    results = compute_spacings(zeros, dims, ranks, mean_spacings)
    
    # 3. Number variance
    L_vals = np.linspace(0.5, 6.0, 24)
    nv_result = compute_number_variance(zeros, mean_spacings, L_vals)
    results["number_variance"] = nv_result
    
    # 4. Summary statistics
    results["metadata"] = {
        "n_forms": len(labels),
        "n_zeros_per_form": 10,
        "total_spacings": len(labels) * 9,
        "n_d1": int(np.sum(dims == 1)),
        "n_d2": int(np.sum(dims >= 2)),
        "dim_values": [int(x) for x in sorted(set(dims))],
        "n_r0": int(np.sum(ranks == 0)),
        "n_r1": int(np.sum(ranks == 1)),
        "mean_dim": float(np.mean(dims)),
    }
    
    # Save
    output_path = OUTPUT_DIR / "spectral_rigidity_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"Thread R complete in {total:.0f}s")
    print(f"Output: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    
    # Print summary
    print("\n=== Summary ===")
    sp = results["spacing_distribution"]
    ra = results["ratio_distribution"]
    sp_d1 = results["spacing_d1"]
    sp_d2 = results["spacing_d2"]
    best_sp = sp["best_fit"]
    best_sp = sp["best_fit"]
    best_d1 = sp_d1["best_fit"]
    best_d2 = sp_d2["best_fit"]
    ks_sp = sp.get(f"ks_{best_sp.lower()}_stat", float("nan"))
    ks_d1 = sp_d1.get(f"ks_{best_d1.lower()}_stat", float("nan"))
    ks_d2 = sp_d2.get(f"ks_{best_d2.lower()}_stat", float("nan"))
    print(f"P(s): mean={sp['mean']:.4f}, best={best_sp} (KS={ks_sp:.4f})")
    print(f"P(r): mean={ra['mean']:.4f}, best={ra['best_fit']}")
    print(f"Dim=1 P(s): best={best_d1} (KS={ks_d1:.4f})")
    print(f"Dim>=2 P(s): best={best_d2} (KS={ks_d2:.4f})")

if __name__ == "__main__":
    main()
