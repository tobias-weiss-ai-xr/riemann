"""
Simulation: finite-sample artifact from N=10 levels per sample.

Hypothesis: With only 10 unfolded levels per sample:
- r-statistic (adjacent spacing ratios) remains robust → Poisson-like ⟨r⟩
- Σ²(L) (interval counting variance) is unreliable due to rank deficiency → spuriously GOE-like

Generates synthetic Poisson and GOE spectra, applies the SAME pipeline as the real scripts,
and compares the joint r-vs-Σ² behavior.

Usage: python scripts/simulate_n10_artifact.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from loguru import logger

N_LEVELS = 10         # match z1-z10
N_SAMPLES = 10_000    # samples per ensemble
R_SEED = 42

# ── Reference values ────────────────────────────────────────────────────────
R_POISSON = 0.386
R_GOE = 0.536
R_GUE = 0.599

SIGMA2_GUE_COEFF = 1 / np.pi ** 2
SIGMA2_GOE_COEFF = 2 / np.pi ** 2
SIGMA2_CONST = 5 / 4 - 1 / np.pi ** 2  # for GUE; GOE uses -2/π² instead


# ── Level generation ────────────────────────────────────────────────────────

def generate_poisson_levels(n: int = N_LEVELS, rng: np.random.Generator | None = None) -> np.ndarray:
    """Generate N unfolded Poisson levels (uncorrelated)."""
    if rng is None:
        rng = np.random.default_rng()
    # Exponential spacings with mean 1 → unfolded Poisson process
    spacings = rng.exponential(scale=1.0, size=n)
    levels = np.cumsum(spacings)
    return levels - levels[0]  # shift to start at 0


def generate_goe_levels(n: int = N_LEVELS, rng: np.random.Generator | None = None) -> np.ndarray:
    """Generate N unfolded GOE levels from a random matrix."""
    if rng is None:
        rng = np.random.default_rng()
    # Build GOE matrix (symmetric, N(0,1) diag, N(0,0.5) off-diag)
    A = rng.normal(0, 1, size=(n, n))
    A = (A + A.T) / 2  # symmetrize
    # Off-diagonal variance should be 1/2 of diagonal
    # After symmetrization, off-diag are N(0, 1/√2) → var = 1/2 ✓
    eigenvalues = np.linalg.eigvalsh(A)
    return unfold_polynomial(np.sort(eigenvalues))


# ── Unfolding ───────────────────────────────────────────────────────────────

def unfold_polynomial(levels: np.ndarray, deg: int = 3) -> np.ndarray:
    """Unfold using polynomial fit (matches analyze_universality_per_lfunction.py)."""
    if len(levels) < deg + 1:
        return levels - levels[0]
    n = np.arange(1, len(levels) + 1, dtype=float)
    coeffs = np.polyfit(levels, n, deg=deg)
    unfolded = np.polyval(coeffs, levels)
    return unfolded


def unfold_mean_spacing(levels: np.ndarray) -> np.ndarray:
    """Simple mean-spacing unfolding (matches train_spectral_rigidity.py)."""
    mean_sp = np.mean(np.diff(levels))
    if mean_sp <= 0:
        return levels - levels[0]
    return levels / mean_sp


def compute_spacings(unfolded: np.ndarray) -> np.ndarray:
    """Get unfolded spacings."""
    sp = np.diff(unfolded)
    return sp[sp > 0]  # filter spurious zeros


# ── r-statistic ─────────────────────────────────────────────────────────────

def r_statistic(spacings: np.ndarray) -> float:
    """r_n = min(s_n, s_{n+1}) / max(s_n, s_{n+1})"""
    if len(spacings) < 3:
        return float("nan")
    r_vals = np.minimum(spacings[:-1], spacings[1:]) / np.maximum(
        spacings[:-1], spacings[1:]
    )
    valid = np.isfinite(r_vals)
    if not valid.any():
        return float("nan")
    return float(np.mean(r_vals[valid]))


# ── Number variance Σ²(L) ──────────────────────────────────────────────────

def compute_sigma2_single_form(unfolded: np.ndarray, L_vals: np.ndarray) -> list[float]:
    """Compute Σ²(L) for a single form's unfolded levels (non-overlapping windows)."""
    sigma2_vals = []
    for L in L_vals:
        max_u = unfolded[-1]
        n_starts = max(0, int(max_u / L))
        counts = []
        for s in range(n_starts):
            left = s * L
            right = (s + 1) * L
            count = np.sum((unfolded >= left) & (unfolded < right))
            counts.append(count)
        if len(counts) > 1:
            sigma2_vals.append(float(np.var(counts, ddof=1)))
        else:
            sigma2_vals.append(float("nan"))
    return sigma2_vals


def compute_ensemble_sigma2(unfolded_all: np.ndarray, L_vals: np.ndarray) -> np.ndarray:
    """
    Compute ensemble-averaged Σ²(L), matching train_spectral_rigidity.py.
    
    unfolded_all: shape (N_samples, N_levels)
    """
    N = unfolded_all.shape[0]
    sigma2_vals = np.full(len(L_vals), np.nan)

    for j, L in enumerate(L_vals):
        all_counts = []
        for i in range(N):
            u = unfolded_all[i]
            max_u = u[-1]
            n_starts = max(0, int(max_u / L))
            for s in range(n_starts):
                left = s * L
                right = (s + 1) * L
                count = np.sum((u >= left) & (u < right))
                all_counts.append(count)

        if len(all_counts) > 1:
            sigma2_vals[j] = float(np.var(all_counts, ddof=1))

    return sigma2_vals


# ── Main simulation ─────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(R_SEED)
    L_vals = np.linspace(0.5, 6.0, 24)

    results = {}

    for ensemble_name, generator in [
        ("Poisson (uncorrelated)", generate_poisson_levels),
        ("GOE (Wigner-Dyson)", generate_goe_levels),
    ]:
        logger.info(f"Generating {N_SAMPLES} {ensemble_name} samples...")

        # Storage per sample
        r_vals_poly = []   # r-stat with polynomial unfolding
        r_vals_mean = []   # r-stat with mean-spacing unfolding
        sigma2_poly = []   # Σ² per form with poly unfolding
        sigma2_mean = []   # Σ² per form with mean unfolding

        for i in range(N_SAMPLES):
            levels = generator(rng=rng)

            # Unfold both ways
            unfolded_poly = unfold_polynomial(levels)
            unfolded_mean = unfold_mean_spacing(levels)

            # Spacings
            sp_poly = compute_spacings(unfolded_poly)
            sp_mean = compute_spacings(unfolded_mean)

            # r-statistic
            r_vals_poly.append(r_statistic(sp_poly))
            r_vals_mean.append(r_statistic(sp_mean))

            # Per-form Σ² (for distribution analysis)
            sigma2_poly.append(compute_sigma2_single_form(unfolded_poly, L_vals))
            sigma2_mean.append(compute_sigma2_single_form(unfolded_mean, L_vals))

        # ── r-statistic results ──
        r_poly_arr = np.array(r_vals_poly)
        r_poly_arr = r_poly_arr[np.isfinite(r_poly_arr)]
        r_mean_arr = np.array(r_vals_mean)
        r_mean_arr = r_mean_arr[np.isfinite(r_mean_arr)]

        # ── Ensemble Σ²(L) ──
        unfolded_poly_all = np.array([
            unfold_polynomial(generator(rng=rng))
            for _ in range(N_SAMPLES)
        ])
        unfolded_mean_all = np.array([
            unfold_mean_spacing(generator(rng=rng))
            for _ in range(N_SAMPLES)
        ])

        sigma2_ensemble_poly = compute_ensemble_sigma2(unfolded_poly_all, L_vals)
        sigma2_ensemble_mean = compute_ensemble_sigma2(unfolded_mean_all, L_vals)

        # Reference curves
        sigma2_gue = SIGMA2_GUE_COEFF * np.log(2 * np.pi * L_vals) + SIGMA2_CONST
        sigma2_goe = SIGMA2_GOE_COEFF * np.log(2 * np.pi * L_vals) + SIGMA2_CONST

        # Store
        key = ensemble_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        results[key] = {
            "ensemble": ensemble_name,
            "n_samples": N_SAMPLES,
            "n_levels": N_LEVELS,
            "r_statistics": {
                "poly_unfold": {
                    "mean": float(np.mean(r_poly_arr)),
                    "std": float(np.std(r_poly_arr)),
                    "median": float(np.median(r_poly_arr)),
                    "q25": float(np.percentile(r_poly_arr, 25)),
                    "q75": float(np.percentile(r_poly_arr, 75)),
                    "reference_poisson": R_POISSON,
                    "reference_goe": R_GOE,
                    "deviation_from_poisson_sigma": float(
                        (np.mean(r_poly_arr) - R_POISSON) / (np.std(r_poly_arr) / np.sqrt(len(r_poly_arr)))
                    ),
                },
                "mean_unfold": {
                    "mean": float(np.mean(r_mean_arr)),
                    "std": float(np.std(r_mean_arr)),
                    "median": float(np.median(r_mean_arr)),
                    "q25": float(np.percentile(r_mean_arr, 25)),
                    "q75": float(np.percentile(r_mean_arr, 75)),
                },
            },
            "sigma2": {
                "L_vals": L_vals.tolist(),
                "poly_unfold": sigma2_ensemble_poly.tolist(),
                "mean_unfold": sigma2_ensemble_mean.tolist(),
                "GOE_ref": sigma2_goe.tolist(),
                "GUE_ref": sigma2_gue.tolist(),
                # Deviation from GOE at L=2 (typical tight-binding range)
                "chi2_vs_goe": {
                    "poly": float(np.nansum(
                        ((np.array(sigma2_ensemble_poly) - np.array(sigma2_goe)) ** 2)
                        / np.array(sigma2_goe)
                    )),
                    "mean": float(np.nansum(
                        ((np.array(sigma2_ensemble_mean) - np.array(sigma2_goe)) ** 2)
                        / np.array(sigma2_goe)
                    )),
                },
            },
            # Per-form sigma2 distribution (at each L)
            "sigma2_per_form": {
                str(round(L, 2)): {
                    "mean": float(np.nanmean([s[j] for s in sigma2_poly])),
                    "median": float(np.nanmedian([s[j] for s in sigma2_poly])),
                    "std": float(np.nanstd([s[j] for s in sigma2_poly])),
                    "fraction_nan": float(
                        np.mean([np.isnan(s[j]) for s in sigma2_poly])
                    ),
                }
                for j, L in enumerate(L_vals)
            },
        }

        # Print summary
        print(f"\n{'='*60}")
        print(f"  {ensemble_name} — N={N_LEVELS} levels, {N_SAMPLES} samples")
        print(f"{'='*60}")
        
        print(f"\n  r-statistic (polynomial unfold):")
        print(f"    ⟨r⟩ = {np.mean(r_poly_arr):.4f} ± {np.std(r_poly_arr):.4f}")
        print(f"    Median r = {np.median(r_poly_arr):.4f}")
        print(f"    Reference: Poisson={R_POISSON}, GOE={R_GOE}, GUE={R_GUE}")
        z = (np.mean(r_poly_arr) - R_POISSON) / (np.std(r_poly_arr) / np.sqrt(len(r_poly_arr)))
        print(f"    Deviation from Poisson: {z:.1f}σ")
        
        print(f"\n  Σ²(L) ensemble (mean unfold):")
        for j, L in enumerate(L_vals):
            if j % 4 == 0:
                goe_ref = sigma2_goe[j]
                obs = sigma2_ensemble_mean[j]
                print(f"    L={L:.1f}: Σ²_obs={obs:.3f}, Σ²_GOE={goe_ref:.3f}, diff={obs-goe_ref:+.3f}")

        print(f"\n  Σ²(L) ensemble (poly unfold):")
        for j, L in enumerate(L_vals):
            if j % 4 == 0:
                goe_ref = sigma2_goe[j]
                obs = sigma2_ensemble_poly[j]
                print(f"    L={L:.1f}: Σ²_obs={obs:.3f}, Σ²_GOE={goe_ref:.3f}, diff={obs-goe_ref:+.3f}")

    # ── Compare: joint r-vs-Σ² behavior ──
    print(f"\n{'='*60}")
    print(f"  COMPARISON: Joint r-vs-Σ² signatures")
    print(f"{'='*60}")
    
    for key, data in results.items():
        r_val = data["r_statistics"]["poly_unfold"]["mean"]
        sigma2_L2_mean = data["sigma2"]["mean_unfold"][
            np.argmin(np.abs(np.array(data["sigma2"]["L_vals"]) - 2.0))
        ]
        sigma2_L2_poly = data["sigma2"]["poly_unfold"][
            np.argmin(np.abs(np.array(data["sigma2"]["L_vals"]) - 2.0))
        ]
        print(f"\n  {data['ensemble']}:")
        print(f"    ⟨r⟩ = {r_val:.4f}  (ref: Poisson={R_POISSON}, GOE={R_GOE})")
        print(f"    Σ²(L=2) mean-unfold = {sigma2_L2_mean:.3f}  (ref: GOE={SIGMA2_GOE_COEFF * np.log(4*np.pi) + SIGMA2_CONST:.3f})")
        print(f"    Σ²(L=2) poly-unfold = {sigma2_L2_poly:.3f}")
        # Classification
        r_class = "Poisson" if abs(r_val - R_POISSON) < abs(r_val - R_GOE) else "GOE"
        print(f"    → r-statistic says: {r_class}")
        print(f"    → Σ²(L) verdict: check vs GOE reference curve")

    # Save
    output_dir = Path("data/simulation_artifact")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "n10_artifact_simulation.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
