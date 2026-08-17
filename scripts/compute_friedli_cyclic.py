"""
Direction A: Friedli constant for cyclic groups Z/nZ (control experiment).

Goal: Compute the Friedli derivative d(log R)/dσ at σ = 0.5 for cyclic Cayley
graphs Z/nZ (cycle graphs C_n). Show that it converges to 0 as n → ∞,
confirming that the SL(2,F_p) value ~1.1367 is a non-abelian invariant.

Background:
  - Friedli–Karlsson (2017) proved that for Z/nZ:
      ζ_{Z/nZ}(s) = n^{-2s} ζ(2s) + ζ_Z(s) + O(n^{-1})
    where ζ_Z(s) = 2 · (2π)^{-s} ζ(s).
  - The functional equation s ↔ 1-s holds in the limit n → ∞, so
    the derivative d(log R)/dσ at σ = 0.5 should vanish as n → ∞.
  - For SL(2,F_p), we found the limit ≈ 1.1367 (Exp 15b).

Method:
  1. Generate cycle graph Laplacian eigenvalues: μ_j = 4 sin²(πj/n)
     (degree 2: adjacency λ_j = 2 cos(2πj/n), Laplacian μ_j = 2 - λ_j)
  2. Compute ζ_n(s) = Σ_{j=1}^{n-1} μ_j^{-s/2} on a fine σ-grid at Im(s) = 0
  3. Compute ratio R_n(σ) = |ζ_n(1-σ) / ζ_n(σ)|
  4. Compute d(log R)/dσ at σ = 0.5 via central differences
  5. Show d(log R)/dσ → 0 as n → ∞

Usage:
    python scripts/compute_friedli_cyclic.py
    python scripts/compute_friedli_cyclic.py --n-max 10000 --plot

Output:
    data/friedli_cyclic/ — CSV of slopes, plot of convergence
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from loguru import logger

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "friedli_cyclic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cycle_laplacian_eigenvalues(n: int) -> np.ndarray:
    """
    Compute Laplacian eigenvalues of the cycle graph C_n (degree 2).

    Adjacency eigenvalues: λ_j = 2 cos(2πj/n),  j = 0, ..., n-1
    Laplacian eigenvalues: μ_j = 2 - λ_j = 4 sin²(πj/n)

    Returns sorted non-zero Laplacian eigenvalues (ascending).
    """
    j = np.arange(1, n)  # exclude j=0 (zero eigenvalue)
    # num. stable: compute sin² directly
    mu = 4.0 * np.sin(np.pi * j / n) ** 2
    return np.sort(mu)


def spectral_zeta_cyclic(mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """
    Compute ζ_n(σ) = Σ μ_j^{-σ/2} for real σ on the critical strip.

    Uses Im(s) = 0 (real axis) — the Friedli ratio is well-defined here.
    """
    zeta = np.zeros_like(sigma, dtype=np.float64)
    for i, s in enumerate(sigma):
        zeta[i] = np.sum(mu ** (-s / 2.0))
    return zeta


def friedli_ratio(zeta: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """
    R_n(σ) = |ζ_n(1-σ) / ζ_n(σ)| for real σ.

    For s = σ + 0i, we have 1-s = (1-σ) + 0i.
    """
    zeta_1ms = np.interp(1.0 - sigma, sigma, zeta)
    return np.abs(zeta_1ms / zeta)


def compute_friedli_slope(
    n: int, sigma_range: tuple[float, float] = (0.0, 1.0), n_steps: int = 1001
) -> dict:
    """
    Compute the Friedli derivative d(log R)/dσ at σ = 0.5 for cycle graph C_n.

    Returns dict with slope, n, eigenvalues used, and convergence diagnostics.
    """
    sigma = np.linspace(sigma_range[0], sigma_range[1], n_steps)
    mu = cycle_laplacian_eigenvalues(n)

    zeta = spectral_zeta_cyclic(mu, sigma)
    ratio = friedli_ratio(zeta, sigma)

    ds = sigma[1] - sigma[0]
    log_ratio = np.log(ratio + 1e-300)

    idx_05 = np.argmin(np.abs(sigma - 0.5))

    # Central difference: f'(x) ≈ (f(x+h) - f(x-h)) / 2h
    slope = (log_ratio[idx_05 + 1] - log_ratio[idx_05 - 1]) / (2.0 * ds)

    return {
        "n": n,
        "slope": float(slope),
        "num_eigenvalues": len(mu),
        "mu_min": float(mu[0]),
        "mu_max": float(mu[-1]),
        "mu_mean": float(np.mean(mu)),
        "zeta_at_05": float(zeta[idx_05]),
        "ratio_at_05": float(ratio[idx_05]),
        "sigma": sigma,
        "ratio": ratio,
        "log_ratio": log_ratio,
        "mu": mu,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Direction A: Friedli constant for cyclic groups Z/nZ"
    )
    parser.add_argument(
        "--n-min", type=int, default=10, help="Minimum n (default: 10)"
    )
    parser.add_argument(
        "--n-max", type=int, default=100_000, help="Maximum n (default: 100000)"
    )
    parser.add_argument(
        "--n-steps", type=int, default=30, help="Number of n values (default: 30)"
    )
    parser.add_argument(
        "--sigma-steps", type=int, default=1001,
        help="σ grid resolution (default: 1001)"
    )
    parser.add_argument(
        "--plot", action="store_true", default=True,
        help="Generate convergence plots (default: True)"
    )
    parser.add_argument(
        "--no-plot", action="store_false", dest="plot"
    )
    args = parser.parse_args()

    n_values = np.geomspace(args.n_min, args.n_max, args.n_steps, dtype=int)
    n_values = np.unique(n_values)
    logger.info(
        f"Computing Friedli slopes for {len(n_values)} n values: "
        f"{n_values[0]} .. {n_values[-1]}"
    )

    results = []
    for i, n in enumerate(n_values):
        res = compute_friedli_slope(
            int(n), sigma_range=(0.0, 1.0), n_steps=args.sigma_steps
        )
        results.append(res)
        logger.info(
            f"[{i + 1}/{len(n_values)}] n={n:8d}  "
            f"slope={res['slope']:.8f}  "
            f"μ_min={res['mu_min']:.6e}  "
            f"μ_mean={res['mu_mean']:.6f}"
        )

    csv_path = OUTPUT_DIR / "friedli_cyclic_slopes.csv"
    with open(csv_path, "w") as f:
        f.write("n,slope,num_eigenvalues,mu_min,mu_max,mu_mean,zeta_at_05,ratio_at_05\n")
        for r in results:
            f.write(
                f"{r['n']},{r['slope']:.12e},{r['num_eigenvalues']},"
                f"{r['mu_min']:.12e},{r['mu_max']:.12e},{r['mu_mean']:.12e},"
                f"{r['zeta_at_05']:.12e},{r['ratio_at_05']:.12e}\n"
            )
    logger.success(f"Slopes saved to {csv_path}")

    # Power-law fit: slope ~ C · n^{-α}
    ns = np.array([r["n"] for r in results], dtype=float)
    slopes = np.array([r["slope"] for r in results])
    log_ns = np.log(ns)
    log_slopes = np.log(np.abs(slopes) + 1e-300)

    A = np.vstack([log_ns, np.ones_like(log_ns)]).T
    coeffs, residuals, rank, sval = np.linalg.lstsq(A, log_slopes, rcond=None)
    alpha, log_C = coeffs
    C = np.exp(log_C)

    log_slopes_pred = A @ coeffs
    ss_res = np.sum((log_slopes - log_slopes_pred) ** 2)
    ss_tot = np.sum((log_slopes - np.mean(log_slopes)) ** 2)
    r2 = 1.0 - ss_res / ss_tot

    logger.info("=" * 60)
    logger.info("Friedli Derivative Convergence — Power-Law Fit")
    logger.info("=" * 60)
    logger.info(f"  Model:        |slope| = {C:.6f} · n^({alpha:.6f})")
    logger.info(f"  Exponent α:   {alpha:.6f}")
    logger.info(f"  R² (log-log): {r2:.6f}")
    logger.info(f"  Asymptotic:   slope → 0 {'✅' if alpha < 0 else '❌'}")
    logger.info(f"  SL(2,F_p) target: 1.1367 (non-abelian invariant)")

    if args.plot:
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        # Plot 1: Ratio R_n(σ) vs σ for selected n
        ax = axes[0]
        selected = np.linspace(0, len(results) - 1, min(8, len(results)), dtype=int)
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(selected)))
        for idx, color in zip(selected, colors):
            r = results[idx]
            ax.plot(r["sigma"], r["ratio"], color=color, label=f"n={r['n']}")
        ax.axvline(x=0.5, color="red", linestyle="--", alpha=0.5, label="σ=0.5")
        ax.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5)
        ax.set_xlabel("σ = Re(s)")
        ax.set_ylabel("R_n(σ) = |ζ(1-σ) / ζ(σ)|")
        ax.set_title("Z/nZ: Friedli Ratio R_n(σ)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # Plot 2: Slope convergence (log-log)
        ax = axes[1]
        ax.loglog(ns, np.abs(slopes), "o-", color="steelblue", label="Computed")
        ax.loglog(
            ns,
            np.exp(alpha * log_ns + log_C),
            "--",
            color="crimson",
            label=f"Fit: |slope| ∝ n^{{{alpha:.3f}}}",
        )
        ax.axhline(
            y=1.1367, color="green", linestyle="--", alpha=0.7,
            label=f"SL(2,F_p) limit = 1.1367"
        )
        ax.set_xlabel("n (graph size)")
        ax.set_ylabel("|d(log R)/dσ| at σ=0.5")
        ax.set_title("Z/nZ: Friedli Derivative → 0 (log-log)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 3: Linear-scale slope vs n (zoomed for small n)
        ax = axes[2]
        ax.semilogx(ns, slopes, "o-", color="steelblue")
        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax.axhline(
            y=1.1367, color="green", linestyle="--", alpha=0.7,
            label="SL(2,F_p) limit = 1.1367"
        )
        ax.set_xlabel("n (graph size)")
        ax.set_ylabel("d(log R)/dσ at σ=0.5")
        ax.set_title("Z/nZ: Friedli Derivative (signed)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = OUTPUT_DIR / "friedli_cyclic_convergence.png"
        plt.savefig(plot_path, dpi=150, bbox_inches="tight")
        logger.success(f"Plot saved to {plot_path}")
        plt.close()

    logger.success("Done! Direction A complete.")


if __name__ == "__main__":
    main()
