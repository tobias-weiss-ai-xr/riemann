"""
Item 2: Per-form Brody β distribution.

Fits Brody β to each individual form's 9 spacings,
then examines the distribution of β estimates.
Hypothesis: dim_1 forms should cluster near β≈1.88,
dim_ge2 forms near β≈0.24 — bimodal distribution.
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
OUTPUT_DIR = Path("data/spectral_rigidity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def neg_log_likelihood_per_form(beta, spacings):
    """Neg log-likelihood for a single form (9 spacings)."""
    if beta < 0 or beta > 3:
        return 1e12
    s = spacings[(~np.isnan(spacings)) & (spacings > 0)]
    if len(s) < 3:
        return 1e12
    a = np.exp((beta + 1) * np.log(gamma_func((beta + 2) / (beta + 1))))
    log_lik = np.log(beta + 1) + np.log(a) + beta * np.log(s) - a * s ** (beta + 1)
    return -np.sum(log_lik)


def fit_brody_form(form_spacings):
    """Fit Brody β to a single form's 9 spacings. Returns β or NaN if failed."""
    s = form_spacings[(~np.isnan(form_spacings)) & (form_spacings > 0)]
    if len(s) < 3:
        return np.nan
    try:
        result = optimize.minimize_scalar(neg_log_likelihood_per_form, args=(s,), bounds=(0, 3), method="bounded")
        return result.x
    except Exception:
        return np.nan


def main():
    logger.info("Loading LMFDB data...")
    df = pd.read_csv("data/lmfdb/lmfdb_zeros_ml.csv")
    logger.info(f"Loaded {len(df)} forms")

    zero_cols = [f"z{k}" for k in range(1, N_LEVELS + 1)]
    df = df.dropna(subset=zero_cols)
    zeros = df[zero_cols].values  # (N, 10)
    spacings_raw = np.diff(zeros, axis=1)  # (N, 9)
    form_means = np.nanmean(spacings_raw, axis=1, keepdims=True)
    unfolded = spacings_raw / form_means

    dims = df["dim"].values.astype(int)
    N = len(df)

    logger.info(f"Fitting Brody β to each of {N} forms (9 spacings each)...")
    t0 = time.time()

    betas = np.full(N, np.nan)
    batch_size = 5000
    for start in range(0, N, batch_size):
        end = min(start + batch_size, N)
        batch = unfolded[start:end]
        for i in range(len(batch)):
            betas[start + i] = fit_brody_form(batch[i])
        logger.info(f"  Processed {end}/{N} forms ({end/N*100:.0f}%)")

    elapsed = time.time() - t0
    n_valid = int(np.sum(~np.isnan(betas)))
    logger.info(f"Completed {n_valid}/{N} forms in {elapsed:.1f}s")

    # ── Results per dimension group ────────────────────────────────────────────
    dim_labels = {1: "dim_1", 2: "dim_2", 3: "dim_3", 4: "dim_4"}
    results = {}
    all_mask = ~np.isnan(betas)

    for dim_val, label in dim_labels.items():
        mask = all_mask & (dims == dim_val)
        b = betas[mask]
        if len(b) == 0:
            continue
        hist, edges = np.histogram(b, bins=40, range=(0, 3))
        bin_centers = (edges[:-1] + edges[1:]) / 2
        results[label] = {
            "n_forms": int(mask.sum()),
            "beta_mean": float(np.mean(b)),
            "beta_median": float(np.median(b)),
            "beta_std": float(np.std(b)),
            "beta_q25": float(np.percentile(b, 25)),
            "beta_q75": float(np.percentile(b, 75)),
            "fraction_below_0_5": float(np.mean(b < 0.5)),
            "fraction_above_1_5": float(np.mean(b > 1.5)),
            "fraction_between_0_5_and_1_5": float(np.mean((b >= 0.5) & (b <= 1.5))),
            "histogram": {"bin_centers": [float(f"{x:.3f}") for x in bin_centers],
                          "counts": [int(c) for c in hist]},
        }
        logger.info(f"  {label}: n={len(b):,}  β_mean={np.mean(b):.4f}±{np.std(b):.4f}  "
                     f"med={np.median(b):.4f}  <0.5={np.mean(b<0.5):.3f}  >1.5={np.mean(b>1.5):.3f}")

    # dim_ge2 aggregate
    mask_ge2 = all_mask & (dims >= 2)
    b_ge2 = betas[mask_ge2]
    hist, edges = np.histogram(b_ge2, bins=40, range=(0, 3))
    bin_centers = (edges[:-1] + edges[1:]) / 2
    results["dim_ge2"] = {
        "n_forms": int(mask_ge2.sum()),
        "beta_mean": float(np.mean(b_ge2)),
        "beta_median": float(np.median(b_ge2)),
        "beta_std": float(np.std(b_ge2)),
        "beta_q25": float(np.percentile(b_ge2, 25)),
        "beta_q75": float(np.percentile(b_ge2, 75)),
        "fraction_below_0_5": float(np.mean(b_ge2 < 0.5)),
        "fraction_above_1_5": float(np.mean(b_ge2 > 1.5)),
        "fraction_between_0_5_and_1_5": float(np.mean((b_ge2 >= 0.5) & (b_ge2 <= 1.5))),
        "histogram": {"bin_centers": [float(f"{x:.3f}") for x in bin_centers],
                      "counts": [int(c) for c in hist]},
    }

    # all forms
    b_all = betas[all_mask]
    hist, edges = np.histogram(b_all, bins=40, range=(0, 3))
    bin_centers = (edges[:-1] + edges[1:]) / 2
    results["all"] = {
        "n_forms": int(all_mask.sum()),
        "beta_mean": float(np.mean(b_all)),
        "beta_median": float(np.median(b_all)),
        "beta_std": float(np.std(b_all)),
        "beta_q25": float(np.percentile(b_all, 25)),
        "beta_q75": float(np.percentile(b_all, 75)),
        "fraction_below_0_5": float(np.mean(b_all < 0.5)),
        "fraction_above_1_5": float(np.mean(b_all > 1.5)),
        "fraction_between_0_5_and_1_5": float(np.mean((b_all >= 0.5) & (b_all <= 1.5))),
        "histogram": {"bin_centers": [float(f"{x:.3f}") for x in bin_centers],
                      "counts": [int(c) for c in hist]},
    }

    output_path = OUTPUT_DIR / "item2_per_form_beta_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {output_path}")

    # Save raw betas (lightweight: just float values + dim labels)
    raw = {
        "betas": [float(f"{b:.4f}") for b in betas[all_mask]],
        "dims": [int(d) for d in dims[all_mask]],
        "labels": [str(l) for l in df["label"].values[all_mask]],
    }
    raw_path = OUTPUT_DIR / "item2_raw_betas.json"
    with open(raw_path, "w") as f:
        json.dump(raw, f, indent=2)
    logger.info(f"Raw betas saved to {raw_path}")


if __name__ == "__main__":
    main()
