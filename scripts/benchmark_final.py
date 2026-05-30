#!/usr/bin/env python3
"""
Final benchmark (4)+(5). All output flushed. XGBoost imported once at top.
LDA F1 computed manually to avoid classification_report edge cases.
"""
from __future__ import annotations

import json, time, sys, warnings
from collections import Counter, OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

INCREMENTAL_CSV = Path("data/lmfdb/lmfdb_incremental_ml.csv")
ZEROS_CSV = Path("data/lmfdb/lmfdb_zeros_ml.csv")
OUTPUT_DIR = Path("data/benchmarks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TRACE_COLS = [f"trace_{p}" for p in range(1, 101)]
ZERO_COLS = [f"z{i}" for i in range(1, 11)]
STAT_COLS = ["num_zeros", "mean_zero_spacing", "std_zero_spacing"]
RANDOM_SEED = 42

def compute_f1(y_true, y_pred, n_classes=3):
    """Weighted F1 avoiding sklearn edge cases."""
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[t, p] += 1
    precisions, recalls = [], []
    for c in range(n_classes):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precisions.append(prec)
        recalls.append(rec)
    f1s = []
    for c in range(n_classes):
        p, r = precisions[c], recalls[c]
        f1s.append(2 * p * r / (p + r) if (p + r) > 0 else 0.0)
    class_counts = np.bincount(y_true, minlength=n_classes)
    weighted = sum(f * c for f, c in zip(f1s, class_counts)) / class_counts.sum()
    return round(float(weighted), 4), {str(c): round(float(f), 4) for c, f in enumerate(f1s)}

def p(*args, **kwargs):
    print(*args, **kwargs, flush=True)

# ── (4) Competition ────────────────────────────────────────────────────────
def competition(df):
    p("\n(4) PCA+LDA on 200K traces (arXiv:2502.10360 style)")
    p(f"  Data: {len(df)} rows")
    t0 = time.time()

    y = np.where(df["analytic_rank"].values >= 2, 2, df["analytic_rank"].values)
    X = np.nan_to_num(df[TRACE_COLS].values.astype(np.float64), nan=0.0)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y)

    pca = PCA(n_components=50, random_state=RANDOM_SEED)
    X_tr_pca = pca.fit_transform(X_tr)
    X_te_pca = pca.transform(X_te)
    p_var = float(pca.explained_variance_ratio_.sum())
    p(f"  PCA(50): var={p_var:.4f}")

    # 2D centroid sep
    pca_2 = PCA(n_components=2, random_state=RANDOM_SEED)
    X_2d = pca_2.fit_transform(X_tr)
    sep = {}
    for r1, r2 in [(0, 1), (0, 2), (1, 2)]:
        c1 = X_2d[y_tr == r1].mean(0); c2 = X_2d[y_tr == r2].mean(0)
        sep[f"r{r1}_r{r2}"] = round(float(np.linalg.norm(c1 - c2)), 3)
    p(f"  Centroid sep (2D): {sep}")

    lda = LDA()
    lda.fit(X_tr_pca, y_tr)
    y_pred = lda.predict(X_te_pca)
    acc = float((y_pred == y_te).mean())
    w_f1, per_r = compute_f1(y_te, y_pred)

    p(f"  Acc={acc:.4f} F1={w_f1:.4f} per-rank={per_r}")
    p(f"  Pred dist: {dict(Counter(y_pred))}")
    p(f"  [{time.time()-t0:.1f}s]")
    return {"method": "PCA(50)+LDA", "n": int(len(y)),
            "pca_var": round(p_var, 4), "centroid_sep": sep,
            "accuracy": round(acc, 4), "weighted_f1": w_f1,
            "per_rank_f1": per_r, "elapsed_s": round(time.time()-t0, 1)}

# ── (5) Engineered Features ────────────────────────────────────────────────
def engineered(df):
    p("\n(5) Engineered features (no data leak) — arXiv:2504.19451 style")
    p(f"  Data: {len(df)} rows")
    t0 = time.time()

    y = np.where(df["analytic_rank"].values >= 2, 2, df["analytic_rank"].values)

    zv = [c for c in ZERO_COLS if c in df.columns]
    sv = [c for c in STAT_COLS if c in df.columns]
    ev = [c for c in ["root_number"] if c in df.columns]
    p(f"  Features: {len(TRACE_COLS)} traces + {len(zv)} zeros + {len(sv)} stats + {len(ev)} extra")

    sets = OrderedDict([
        ("A: 100 traces only", TRACE_COLS),
        ("B: traces + 10 zeros", TRACE_COLS + zv),
        ("C: traces + zero stats", TRACE_COLS + sv),
        ("D: All: traces+zeros+stats+root_number", TRACE_COLS + zv + sv + ev),
        ("E: zeros + stats only", zv + sv),
        ("F: zeros + stats + root_number", zv + sv + ev),
        ("G: traces + root_number", TRACE_COLS + ev),
    ])

    results = {}
    for sname, cols in sets.items():
        X = np.nan_to_num(df[cols].values.astype(np.float64), nan=0.0)
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y)

        rf = RandomForestClassifier(n_estimators=100, max_depth=20, random_state=RANDOM_SEED, n_jobs=-1)
        rf.fit(X_tr, y_tr)
        rf_pred = rf.predict(X_te)
        rf_acc = float((rf_pred == y_te).mean())
        rf_f1, rf_per = compute_f1(y_te, rf_pred)

        top_k = min(6, len(cols))
        imp = sorted(zip(cols, rf.feature_importances_), key=lambda x: -x[1])[:top_k]

        p(f"  {sname:44s} RF acc={rf_acc:.4f} f1={rf_f1:.4f}", end="")
        if sname == "D: All: traces+zeros+stats+root_number":
            p(f"  top={[(c,f'{v:.3f}') for c,v in imp[:4]]}")
        else:
            p()

        results[sname] = {"n_features": len(cols), "rf_accuracy": round(rf_acc, 4),
                          "rf_weighted_f1": rf_f1, "per_rank_f1_rf": rf_per,
                          "top_features_rf": [(c, round(float(v), 4)) for c, v in imp]}

    p(f"  [{time.time()-t0:.1f}s]")
    return {"results": results, "elapsed_s": round(time.time()-t0, 1)}

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    p("="*70)
    p("BENCHMARK: (4) arXiv:2502.10360 + (5) arXiv:2504.19451")
    p("="*70)

    all_results = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    df200k = pd.read_csv(INCREMENTAL_CSV)
    p(f"\n200K CSV: {df200k.shape}")
    all_results["(4) competition"] = competition(df200k)

    dfzeros = pd.read_csv(ZEROS_CSV)
    p(f"\nZeros CSV: {dfzeros.shape}")
    all_results["(5) engineered"] = engineered(dfzeros)

    # Summary
    c4 = all_results["(4) competition"]
    e5 = all_results["(5) engineered"]
    best = max(e5["results"].items(), key=lambda x: x[1]["rf_weighted_f1"])

    p("\n" + "="*70)
    p("SUMMARY")
    p("="*70)
    p(f"(4) PCA+LDA 200K:    Acc={c4['accuracy']:.4f} F1={c4['weighted_f1']:.4f}")
    p(f"    Competition ref:  ~0.81 F1 (248K rational L-functions)")
    p(f"    Delta:            {c4['weighted_f1']-0.81:+.4f}")
    p(f"(5) Engineered best:  F1={best[1]['rf_weighted_f1']:.4f} ({best[0]})")
    p(f"    Top features:     {best[1]['top_features_rf'][:5]}")
    p(f"Our GAT (63K, z1 reg): R²=0.731 (different task)")

    with open(OUTPUT_DIR / "benchmark_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    p(f"\nSaved to {OUTPUT_DIR/'benchmark_results.json'}")
    p("DONE.")

if __name__ == "__main__":
    main()
