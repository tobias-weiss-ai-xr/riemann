"""
Deep analysis of Karlsson-Friedli spectral zeta on SL(2,F_p).

Computes:
1. Functional equation ratio R_p(s) = |ζ_p(1-s)/ζ_p(s)| at various Re(s)
2. Critical line test: how close to 1 is R_p(0.5+it)?
3. Off-critical analysis: does off-critical line ratio deviate more?
4. Slope analysis: derivative of R_p w.r.t. Re(s) near s=1/2
5. Convergence with p: polynomial fit of |R_p - 1| ~ p^{-α}
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from loguru import logger
from scipy import stats

DATA_DIR = Path(__file__).parent.parent / "data"
EIGEN_DIR = DATA_DIR / "eigenvalues"


def discover_primes() -> list[int]:
    primes = []
    for f in sorted(EIGEN_DIR.glob("sl2fp_p*_eigenvalues.npy")):
        stem = f.stem
        parts = stem.split("_p")
        if len(parts) >= 2:
            p_str = parts[1].split("_")[0]
            p = int(p_str)
            primes.append(p)
    return primes


def load_eigenvalues(prime: int) -> np.ndarray:
    path = EIGEN_DIR / f"sl2fp_p{prime}_eigenvalues.npy"
    return np.load(path)


def spectral_zeta(eigenvalues: np.ndarray, s_vals: np.ndarray, degree: int = 4) -> np.ndarray:
    """ζ_p(s) = Σ (degree - λ_i)^{-s/2} over non-trivial eigenvalues."""
    nontrivial = eigenvalues[np.abs(eigenvalues - degree) > 1e-8]
    mu = degree - nontrivial
    mu = mu[mu > 1e-10]
    zeta = np.zeros(len(s_vals), dtype=np.complex128)
    for i, s in enumerate(s_vals):
        zeta[i] = np.sum(mu ** (-s / 2.0))
    return zeta, len(mu)


def compute_functional_body(primes: list[int]) -> dict:
    """
    Compute the functional equation ratio R_p(s) = |ζ_p(1-s)/ζ_p(s)|
    across a grid of s values.
    """
    re_vals = np.linspace(0.1, 0.9, 41)
    im_vals = np.array([0.0, 0.5, 1.0, 2.0, 5.0, 10.0])

    results = {}
    for p in primes:
        ev = load_eigenvalues(p)
        nontrivial = np.sum(np.abs(ev - 4.0) > 1e-8)
        data = {"nontrivial_count": int(nontrivial), "ratios": {}}

        for im in im_vals:
            s_vals = re_vals + 1j * im
            zeta_s, _ = spectral_zeta(ev, s_vals)
            zeta_1ms, _ = spectral_zeta(ev, 1.0 - s_vals)

            ratios = np.abs(zeta_1ms / zeta_s)
            data["ratios"][f"im_{im}"] = {
                "re_vals": re_vals.tolist(),
                "ratios": ratios.tolist(),
                "min_ratio": float(np.min(ratios)),
                "max_ratio": float(np.max(ratios)),
                "ratio_at_05": float(ratios[np.argmin(np.abs(re_vals - 0.5))]),
            }

        results[p] = data

    return results


def analyze_critical_line(primes: list[int]) -> dict:
    """
    Analyze |ζ_p(1-s)/ζ_p(s)| precisely at Re(s)=0.5 across Im(s) range.
    """
    im_vals = np.linspace(0, 10, 201)
    s_vals = 0.5 + 1j * im_vals

    results = {}
    for p in primes:
        ev = load_eigenvalues(p)
        zeta_s, n_non = spectral_zeta(ev, s_vals)
        zeta_1ms, _ = spectral_zeta(ev, 1.0 - s_vals)

        ratios = np.abs(zeta_1ms / zeta_s)

        results[p] = {
            "num_eigenvalues": int(n_non),
            "im_vals": im_vals.tolist(),
            "ratios": ratios.tolist(),
            "mean_ratio": float(np.mean(ratios)),
            "std_ratio": float(np.std(ratios)),
            "min_ratio": float(np.min(ratios)),
            "max_ratio": float(np.max(ratios)),
            "ratio_log10_std": float(np.log10(np.std(ratios) + 1e-300)),
        }

    return results


def convergence_analysis(critical_data: dict) -> dict:
    """
    Fit |R_p - 1| ~ C * p^{-α} for the convergence analysis.
    Excludes small primes (p < 11) and truncated (p >= 71, only 20 eigenvalues).
    """
    primes = sorted(critical_data.keys())
    
    # Use only well-sampled primes (p < 71) and p > 5
    valid = [p for p in primes if 5 < p < 71]
    
    deviations = []
    for p in valid:
        ratios = np.array(critical_data[p]["ratios"])
        deviation = np.mean(np.abs(ratios - 1.0))
        deviations.append(deviation)
    
    # Fit log(deviation) = log(C) - α * log(p)
    log_p = np.log(valid)
    log_dev = np.log(np.maximum(deviations, 1e-300))
    
    if len(valid) >= 3:
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_p, log_dev)
    else:
        slope, intercept, r_value, p_value, std_err = 0, 0, 0, 0, 0
    
    return {
        "primes": valid,
        "deviations": deviations,
        "log_p": log_p.tolist(),
        "log_deviation": log_dev.tolist(),
        "alpha": float(slope),  # convergence exponent
        "intercept": float(intercept),
        "r_squared": float(r_value ** 2),
        "p_value": float(p_value),
        "std_err": float(std_err),
    }


def main():
    primes = discover_primes()
    logger.info(f"Analyzing {len(primes)} primes: {primes}")

    # 1. Functional equation body scan
    logger.info("Computing functional equation body scan...")
    body = compute_functional_body(primes)

    # 2. Critical line analysis (high resolution)
    logger.info("Computing critical line analysis...")
    critical = analyze_critical_line(primes)

    # 3. Convergence fit
    logger.info("Computing convergence analysis...")
    convergence = convergence_analysis(critical)

    # Print summary
    logger.info("=" * 70)
    logger.info("Exp 15: Karlsson-Friedli Spectral Zeta — Analysis Results")
    logger.info("=" * 70)

    # Critical line summary
    logger.info("\n--- Critical Line (Re(s)=0.5) ---")
    logger.info(f"{'p':>4s}  {'N':>5s}  {'mean|R|':>8s}  {'std|R|':>8s}  {'min|R|':>8s}  {'max|R|':>8s}")
    for p in sorted(critical.keys()):
        d = critical[p]
        logger.info(
            f"p={p:3d}  {d['num_eigenvalues']:5d}  "
            f"{d['mean_ratio']:8.4f}  {d['std_ratio']:8.4f}  "
            f"{d['min_ratio']:8.4f}  {d['max_ratio']:8.4f}"
        )

    # Convergence summary
    logger.info("\n--- Convergence Analysis ---")
    logger.info(f"Deviation ~ p^{convergence['alpha']:.4f}")
    logger.info(f"  R² = {convergence['r_squared']:.6f}")
    logger.info(f"  p-value = {convergence['p_value']:.6e}")
    logger.info(f"  std_err = {convergence['std_err']:.6f}")

    logger.info(f"\nConvergence data ({len(convergence['primes'])} primes):")
    for p, dev in zip(convergence["primes"], convergence["deviations"]):
        logger.info(f"  p={p:3d}: mean|R-1| = {dev:.6f}")

    # Save all results to JSON
    output_dir = DATA_DIR / "spectral_zeta_kf"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save critical data (convert numpy values)
    save_critical = {}
    for p, d in critical.items():
        save_critical[str(p)] = d

    all_results = {
        "body": {str(p): body[p] for p in body},
        "critical": save_critical,
        "convergence": convergence,
    }

    output_path = output_dir / "analysis_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info(f"Analysis saved to {output_path}")

    # Also save as NPZ for easier loading
    npz_path = output_dir / "critical_line_data.npz"
    npz_dict = {}
    for p in critical:
        npz_dict[f"p{p}_ratios"] = np.array(critical[p]["ratios"])
    npz_dict["primes"] = np.array(sorted(critical.keys()))
    npz_dict["im_vals"] = np.array(critical[primes[0]]["im_vals"])
    np.savez_compressed(npz_path, **npz_dict)
    logger.info(f"Critical line data saved to {npz_path}")

    logger.success("Analysis complete!")


if __name__ == "__main__":
    main()
