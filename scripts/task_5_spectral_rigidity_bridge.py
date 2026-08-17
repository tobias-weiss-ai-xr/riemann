"""
Thread R Bridge: Trace Features → Spectral Rigidity Prediction

Connects Task 3 (zero spacing prediction) with Thread L/R (GUE/GOE spectral analysis).

Questions:
1. Can Hecke traces predict per-form GUE/GOE preference?
2. Which trace features correlate with GUE deviation?
3. Within dim>=2: can traces identify the 6% of forms that prefer GUE?

Targets (per form, from 10 zeros):
- mean_spacing_ratio: <r> from spacing ratios
- gue_ks_stat: KS distance from GUE CDF
- goe_ks_stat: KS distance from GOE CDF
- prefers_gue: binary (KS_GUE < KS_GOE)
- msd_ratio: mean/median spacing deviation from GUE expectation

Features:
- 100 Hecke traces (trace_1..trace_100)
- 6 scalars: level, dim, analytic_rank, root_number, char_order, mean_zero_spacing
"""
from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.special import erf
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, accuracy_score, f1_score, classification_report, roc_auc_score

warnings.filterwarnings("ignore")

OUTPUT_DIR = Path("data/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Reference distributions ────────────────────────────────────────────────

def cdf_gue(s):
    """GUE spacing CDF."""
    return erf(2 * s / np.sqrt(np.pi)) - (4 * s / np.pi) * np.exp(-4 * s**2 / np.pi)


def cdf_goe(s):
    """GOE spacing CDF: 1 - exp(-pi*s^2/4)."""
    return 1 - np.exp(-np.pi * s**2 / 4)


def compute_per_form_metrics(zeros, mean_spacings):
    """Compute per-form spectral rigidity metrics from 10 zeros.
    
    Returns dict of arrays, each shape (N,).
    """
    N = zeros.shape[0]
    
    # Unfolded spacings (9 per form)
    spacings = np.diff(zeros, axis=1) / mean_spacings[:, None]  # (N, 9)
    
    # Spacing ratios (8 per form)
    ratios = spacings[:, 1:] / spacings[:, :-1]  # (N, 8)
    
    # Filter extreme ratio values per form (but keep form-level stats)
    # Use median for robustness
    mean_ratio = np.nanmedian(ratios, axis=1)
    std_ratio = np.nanstd(ratios, axis=1)
    
    # Mean spacing stats
    mean_sp = np.mean(spacings, axis=1)
    std_sp = np.std(spacings, axis=1)
    skew_sp = sp_stats.skew(spacings, axis=1, nan_policy="omit")
    
    # KS statistics per form (against GUE and GOE)
    gue_ks = np.array([
        sp_stats.kstest(spacings[i], cdf_gue).statistic 
        for i in range(N)
    ])
    goe_ks = np.array([
        sp_stats.kstest(spacings[i], cdf_goe).statistic 
        for i in range(N)
    ])
    
    # Prefers GUE (1) or GOE (0)
    prefers_gue = (gue_ks < goe_ks).astype(np.int32)
    
    # GUE preference margin: negative = prefers GUE
    gue_margin = gue_ks - goe_ks
    
    # GUE deviation: how far from perfect GUE (0 = perfect GUE match)
    gue_deviation = gue_ks
    
    return {
        "mean_spacing": mean_sp,
        "std_spacing": std_sp,
        "skew_spacing": skew_sp,
        "mean_ratio": mean_ratio,
        "std_ratio": std_ratio,
        "gue_ks_stat": gue_ks,
        "goe_ks_stat": goe_ks,
        "prefers_gue": prefers_gue,
        "gue_margin": gue_margin,
        "gue_deviation": gue_deviation,
    }


def load_data():
    """Load LMFDB zeros CSV and extract features + labels."""
    print("Loading data/lmfdb/lmfdb_zeros_ml.csv ...")
    t0 = time.time()
    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    print(f"  Loaded {len(df):,} forms in {time.time()-t0:.1f}s")
    
    # Ensure complete zero data
    zero_cols = [f"z{k}" for k in range(1, 11)]
    df = df.dropna(subset=zero_cols).copy()
    print(f"  {len(df):,} forms with complete z1-z10 data")
    
    # Extract zeros
    zeros = df[zero_cols].values  # (N, 10)
    mean_zero_spacing = df["mean_zero_spacing"].values
    dims = df["dim"].values.astype(int)
    ranks = df["analytic_rank"].values.astype(int)
    
    # Extract trace features (100 traces per form)
    trace_cols = [f"trace_{k}" for k in range(1, 101)]
    traces = df[trace_cols].values  # (N, 100)
    
    # Extract scalar features
    scalar_features = ["level", "dim", "analytic_rank", "root_number", 
                       "char_order", "mean_zero_spacing"]
    scalars = df[scalar_features].values  # (N, 6)
    
    return df, zeros, mean_zero_spacing, dims, ranks, traces, scalars


def train_and_evaluate(X, y, task_name, model_type="regression"):
    """Train GB model and evaluate with train/val/test split.
    
    Returns dict of metrics.
    """
    # Stratified split for classification
    stratify = y if model_type == "classification" else None
    if model_type == "classification":
        # Handle potential class imbalance in stratification
        y_min = y.astype(int)
        X_tmp, X_test, y_tmp, y_test = train_test_split(
            X, y_min, test_size=0.2, random_state=42, stratify=y_min
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_tmp, y_tmp, test_size=0.125, random_state=42, stratify=y_tmp
        )
    else:
        X_tmp, X_test, y_tmp, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_tmp, y_tmp, test_size=0.125, random_state=42
        )
    
    # Scale features
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)
    X_test_s = scaler.transform(X_test)
    
    t0 = time.time()
    
    if model_type == "classification":
        model = GradientBoostingClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            subsample=0.8, random_state=42
        )
        model.fit(X_train_s, y_train)
        
        train_pred = model.predict(X_train_s)
        val_pred = model.predict(X_val_s)
        test_pred = model.predict(X_test_s)
        test_proba = model.predict_proba(X_test_s)[:, 1] if model.classes_[1] == 1 else model.predict_proba(X_test_s)[:, 0]
        
        metrics = {
            "train_acc": float(accuracy_score(y_train, train_pred)),
            "val_acc": float(accuracy_score(y_val, val_pred)),
            "test_acc": float(accuracy_score(y_test, test_pred)),
            "test_f1": float(f1_score(y_test, test_pred, average="weighted")),
            "test_f1_binary": float(f1_score(y_test, test_pred, average="binary")),
            "test_roc_auc": float(roc_auc_score(y_test, test_proba)),
            "n_train": int(len(X_train)),
            "n_val": int(len(X_val)),
            "n_test": int(len(X_test)),
        }
    else:
        model = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            subsample=0.8, random_state=42
        )
        model.fit(X_train_s, y_train)
        
        train_pred = model.predict(X_train_s)
        val_pred = model.predict(X_val_s)
        test_pred = model.predict(X_test_s)
        
        metrics = {
            "train_r2": float(r2_score(y_train, train_pred)),
            "val_r2": float(r2_score(y_val, val_pred)),
            "test_r2": float(r2_score(y_test, test_pred)),
            "test_mae": float(np.mean(np.abs(y_test - test_pred))),
            "n_train": int(len(X_train)),
            "n_val": int(len(X_val)),
            "n_test": int(len(X_test)),
        }
    
    metrics["time_s"] = float(time.time() - t0)
    metrics["task"] = task_name
    metrics["model_type"] = model_type
    metrics["n_features"] = X.shape[1]
    
    print(f"  [{task_name}] test metrics: ", end="")
    if model_type == "classification":
        print(f"acc={metrics['test_acc']:.4f}, f1={metrics['test_f1']:.4f}, "
              f"roc_auc={metrics['test_roc_auc']:.4f}, time={metrics['time_s']:.1f}s")
    else:
        print(f"r2={metrics['test_r2']:.4f}, mae={metrics['test_mae']:.4f}, "
              f"time={metrics['time_s']:.1f}s")
    
    return metrics


def run_bridge_experiment():
    """Main experiment: trace features → spectral rigidity prediction."""
    t_start = time.time()
    results = {}
    
    # 1. Load data
    df, zeros, mean_spacing, dims, ranks, traces, scalars = load_data()
    N = len(df)
    
    # 2. Compute per-form spectral metrics
    print("\n=== Computing per-form spectral rigidity metrics ===")
    t0 = time.time()
    metrics = compute_per_form_metrics(zeros, mean_spacing)
    print(f"  Computed in {time.time()-t0:.1f}s")
    for k, v in metrics.items():
        print(f"  {k}: mean={np.mean(v):.4f}, std={np.std(v):.4f}")
    
    results["per_form_metrics_summary"] = {
        k: {
            "mean": float(np.mean(v)),
            "std": float(np.std(v)),
            "min": float(np.min(v)),
            "max": float(np.max(v)),
            "median": float(np.median(v)),
        }
        for k, v in metrics.items()
    }
    
    # ── Experiment A: Full dataset prediction ──
    print("\n" + "="*60)
    print("Experiment A: Full dataset (N={:,})".format(N))
    print("="*60)
    
    # A1: Mean spacing regression (reproduce Task 3 baseline)
    print("\n--- A1: mean_spacing regression ---")
    results["A1_mean_spacing"] = train_and_evaluate(
        traces, metrics["mean_spacing"], "mean_spacing (traces)", "regression"
    )
    results["A1_mean_spacing_scalars"] = train_and_evaluate(
        scalars, metrics["mean_spacing"], "mean_spacing (scalars)", "regression"
    )
    
    # A2: Std spacing regression (reproduce Task 3's R²=0.91)
    print("\n--- A2: std_spacing regression ---")
    results["A2_std_spacing_traces"] = train_and_evaluate(
        traces, metrics["std_spacing"], "std_spacing (traces)", "regression"
    )
    results["A2_std_spacing_scalars"] = train_and_evaluate(
        scalars, metrics["std_spacing"], "std_spacing (scalars)", "regression"
    )
    results["A2_std_spacing_both"] = train_and_evaluate(
        np.hstack([traces, scalars]), metrics["std_spacing"], 
        "std_spacing (both)", "regression"
    )
    
    # A3: GUE KS deviation regression (NEW)
    # Can traces predict how GUE-like the spacing distribution is?
    print("\n--- A3: gue_ks_stat regression ---")
    results["A3_gue_ks_traces"] = train_and_evaluate(
        traces, metrics["gue_ks_stat"], "gue_ks_stat (traces)", "regression"
    )
    results["A3_gue_ks_scalars"] = train_and_evaluate(
        scalars, metrics["gue_ks_stat"], "gue_ks_stat (scalars)", "regression"
    )
    
    # A4: GUE preference classification
    print("\n--- A4: prefers_gue classification ---")
    results["A4_prefers_gue_traces"] = train_and_evaluate(
        traces, metrics["prefers_gue"], "prefers_gue (traces)", "classification"
    )
    results["A4_prefers_gue_scalars"] = train_and_evaluate(
        scalars, metrics["prefers_gue"], "prefers_gue (scalars)", "classification"
    )
    results["A4_prefers_gue_both"] = train_and_evaluate(
        np.hstack([traces, scalars]), metrics["prefers_gue"], 
        "prefers_gue (both)", "classification"
    )
    
    # ── Experiment B: Within dim≥2 (the hard case) ──
    print("\n" + "="*60)
    print("Experiment B: Within dim>=2 (N={:,})".format(np.sum(dims >= 2)))
    print("="*60)
    
    d2_mask = dims >= 2
    traces_d2 = traces[d2_mask]
    scalars_d2 = scalars[d2_mask]
    
    # B1: GUE preference within dim>=2
    print("\n--- B1: prefers_gue within dim>=2 ---")
    y_d2 = metrics["prefers_gue"][d2_mask]
    gue_d2 = y_d2.sum()
    goe_d2 = len(y_d2) - gue_d2
    print(f"  Class balance: GUE={gue_d2} ({gue_d2/len(y_d2)*100:.1f}%), "
          f"GOE={goe_d2} ({goe_d2/len(y_d2)*100:.1f}%)")
    
    if gue_d2 >= 100:  # Need minimum class for meaningful training
        results["B1_prefers_gue_d2_traces"] = train_and_evaluate(
            traces_d2, y_d2, "prefers_gue (dim>=2, traces)", "classification"
        )
        results["B1_prefers_gue_d2_scalars"] = train_and_evaluate(
            scalars_d2, y_d2, "prefers_gue (dim>=2, scalars)", "classification"
        )
        results["B1_prefers_gue_d2_both"] = train_and_evaluate(
            np.hstack([traces_d2, scalars_d2]), y_d2, 
            "prefers_gue (dim>=2, both)", "classification"
        )
    
    # B2: GUE deviation within dim>=2
    print("\n--- B2: gue_deviation within dim>=2 ---")
    results["B2_gue_dev_d2_traces"] = train_and_evaluate(
        traces_d2, metrics["gue_deviation"][d2_mask], 
        "gue_deviation (dim>=2, traces)", "regression"
    )
    results["B2_gue_dev_d2_scalars"] = train_and_evaluate(
        scalars_d2, metrics["gue_deviation"][d2_mask], 
        "gue_deviation (dim>=2, scalars)", "regression"
    )
    
    # ── Experiment C: Rank analysis ──
    print("\n" + "="*60)
    print("Experiment C: Rank-stratified spacing analysis")
    print("="*60)
    
    for rank_val in [0, 1, 2]:
        r_mask = ranks == rank_val
        n_r = r_mask.sum()
        if n_r < 100:
            continue
        r_gue_frac = metrics["prefers_gue"][r_mask].mean()
        r_mean_sp = metrics["mean_spacing"][r_mask].mean()
        r_std_sp = metrics["std_spacing"][r_mask].mean()
        results[f"C_rank_{rank_val}"] = {
            "n_forms": int(n_r),
            "gue_preference_fraction": float(r_gue_frac),
            "mean_spacing": float(r_mean_sp),
            "std_spacing": float(r_std_sp),
        }
        print(f"  Rank={rank_val}: N={n_r:,}, GUE_pref={r_gue_frac:.3f}, "
              f"mean_sp={r_mean_sp:.4f}, std_sp={r_std_sp:.4f}")
    
    # ── Save ──
    total = time.time() - t_start
    results["metadata"] = {
        "n_forms": N,
        "n_d1": int(np.sum(dims == 1)),
        "n_d2": int(np.sum(dims >= 2)),
        "total_time_s": float(total),
        "n_trace_features": 100,
        "n_scalar_features": 6,
    }
    
    output_path = OUTPUT_DIR / "task_5_spectral_rigidity_bridge_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print(f"Bridge experiment complete in {total:.0f}s")
    print(f"Output: {output_path}")
    
    # ── Summary print ──
    print("\n=== Summary ===")
    def get_v(k):
        v = results.get(k, {})
        if isinstance(v, dict):
            return v.get("test_r2") if v.get("model_type") == "regression" else v.get("test_acc")
        return None
    
    print(f"mean_spacing (traces): {get_v('A1_mean_spacing'):.4f}")
    print(f"std_spacing (traces): {get_v('A2_std_spacing_traces'):.4f}")
    print(f"std_spacing (scalars): {get_v('A2_std_spacing_scalars'):.4f}")
    print(f"std_spacing (both): {get_v('A2_std_spacing_both'):.4f}")
    print(f"gue_ks (traces): {get_v('A3_gue_ks_traces'):.4f}")
    print(f"gue_ks (scalars): {get_v('A3_gue_ks_scalars'):.4f}")
    print(f"prefers_gue (traces): {get_v('A4_prefers_gue_traces'):.4f}")
    print(f"prefers_gue (scalars): {get_v('A4_prefers_gue_scalars'):.4f}")
    print(f"prefers_gue (both): {get_v('A4_prefers_gue_both'):.4f}")
    
    if "B1_prefers_gue_d2_traces" in results:
        print(f"dim>=2 prefers_gue (traces): {get_v('B1_prefers_gue_d2_traces'):.4f}")
    if "B1_prefers_gue_d2_both" in results:
        print(f"dim>=2 prefers_gue (both): {get_v('B1_prefers_gue_d2_both'):.4f}")


if __name__ == "__main__":
    run_bridge_experiment()
