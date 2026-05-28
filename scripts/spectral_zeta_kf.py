"""
Exp 15: Karlsson-Friedli spectral zeta on SL(2,F_p) Cayley graphs.

For 4-regular Cayley graphs of SL(2,F_p), compute the spectral zeta function:

    ζ_p(s) = Σ_{i: λ_i ≠ 4} (4 - λ_i)^{-s/2}

where {λ_i} are adjacency eigenvalues (sorted descending, λ_0 = 4 = degree).

Karlsson-Friedli (Tohoku Math J 2017) showed:
- For cyclic Z/nZ: ζ_{Z/nZ}(s) = n^{-2s} ζ(2s) + ζ_Z(s) + O(n^{-1})
- RH is equivalent to an asymptotic functional equation s ↔ 1-s

Here we compute ζ_p(s) for non-abelian Cayley graphs and study:
1. The spectral zeta function across primes
2. Convergence of |ζ_p(s)| as p → ∞
3. Functional equation ratio |ζ_p(s) / ζ_p(1-s)| across the critical strip
4. Whether critical-line behavior emerges with increasing p

Usage:
    python scripts/spectral_zeta_kf.py --all        # All primes
    python scripts/spectral_zeta_kf.py --primes 2,3,5,7
    python scripts/spectral_zeta_kf.py --plot       # Generate plots
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from loguru import logger

DATA_DIR = Path(__file__).parent.parent / "data"
EIGEN_DIR = DATA_DIR / "eigenvalues"
OUTPUT_DIR = DATA_DIR / "spectral_zeta_kf"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def discover_primes() -> list[int]:
    """Find all primes with eigenvalue files."""
    primes = []
    for f in sorted(EIGEN_DIR.glob("sl2fp_p*_eigenvalues.npy")):
        # stem is like "sl2fp_p11_eigenvalues", extract between "_p" and "_eigenvalues"
        stem = f.stem
        parts = stem.split("_p")
        if len(parts) >= 2:
            p_str = parts[1].split("_")[0]
            p = int(p_str)
            primes.append(p)
    return primes


def load_eigenvalues(prime: int) -> np.ndarray:
    """Load adjacency eigenvalues for a given prime."""
    path = EIGEN_DIR / f"sl2fp_p{prime}_eigenvalues.npy"
    if not path.exists():
        raise FileNotFoundError(f"No eigenvalues for p={prime}")
    return np.load(path)


def spectral_zeta(eigenvalues: np.ndarray, s_vals: np.ndarray, degree: int = 4) -> np.ndarray:
    """
    Compute ζ_p(s) = Σ (degree - λ_i)^{-s/2} for non-trivial eigenvalues.

    Args:
        eigenvalues: adjacency eigenvalues (sorted descending, λ_0 = degree)
        s_vals: array of complex s values
        degree: graph degree (default 4 for SL(2,F_p) with 4 generators)

    Returns:
        ζ_p(s) for each s in s_vals
    """
    # Exclude trivial eigenvalue λ = degree (which gives Laplacian μ = 0)
    nontrivial = eigenvalues[np.abs(eigenvalues - degree) > 1e-8]

    # Laplacian eigenvalues: μ_i = degree - λ_i
    mu = degree - nontrivial

    # Remove any μ close to 0 (numerical safety)
    mu = mu[mu > 1e-10]

    zeta = np.zeros(len(s_vals), dtype=np.complex128)
    for i, s in enumerate(s_vals):
        # ζ(s) = Σ μ_i^{-s/2}
        zeta[i] = np.sum(mu ** (-s / 2.0))

    return zeta


def compute_zeta_grid(
    primes: list[int],
    re_range: tuple[float, float, int] = (0.0, 1.0, 101),
    im_range: tuple[float, float, int] = (0.0, 10.0, 51),
) -> dict:
    """
    Compute spectral zeta on a grid in the critical strip for each prime.

    Returns:
        dict: {prime: {"s_re": ..., "s_im": ..., "log_zeta": ..., "zeta": ...}}
    """
    re_vals = np.linspace(*re_range)
    im_vals = np.linspace(*im_range)
    s_re, s_im = np.meshgrid(re_vals, im_vals, indexing="ij")
    s_flat = s_re.ravel() + 1j * s_im.ravel()

    results = {}
    for p in primes:
        ev = load_eigenvalues(p)
        zeta = spectral_zeta(ev, s_flat)

        results[p] = {
            "s_re": re_vals,
            "s_im": im_vals,
            "zeta": zeta.reshape(len(re_vals), len(im_vals)),
            "log_zeta": np.log(np.abs(zeta.reshape(len(re_vals), len(im_vals))) + 1e-300),
            "num_ev": len(ev),
            "num_nontrivial": np.sum(np.abs(ev - 4.0) > 1e-8),
        }

        nz = results[p]["num_nontrivial"]
        logger.info(f"p={p}: {nz} non-trivial eigenvalues, |ζ(0.5+0i)|={np.abs(zeta[0]):.4f}")

    return results


def compute_functional_ratio(
    results: dict, s_re: float = 0.5
) -> dict:
    """
    Compute R_p(s) = |ζ_p(1-s) / ζ_p(s)| at fixed Re(s) across primes.

    Returns:
        dict: {prime: {"im_vals": ..., "ratio": ...}}
    """
    data = {}
    for p, res in results.items():
        im_vals = res["s_im"]
        zeta = res["zeta"]

        # Find indices for given Re(s)
        re_idx = np.argmin(np.abs(res["s_re"] - s_re))
        s_mirror_re_idx = np.argmin(np.abs(res["s_re"] - (1.0 - s_re)))

        # R(s) = |ζ(1-s) / ζ(s)|
        zeta_s = zeta[re_idx, :]
        zeta_1ms = zeta[s_mirror_re_idx, :]

        ratio = np.abs(zeta_1ms / (zeta_s + 1e-300))

        data[p] = {
            "im_vals": im_vals,
            "ratio": ratio,
            "log_ratio": np.log(ratio + 1e-300),
        }

    return data


def plot_zeta_heatmaps(results: dict, output_dir: Path, max_primes: int = 9) -> None:
    """Plot |ζ_p(s)| heatmaps across critical strip for selected primes."""
    primes = sorted(results.keys())
    n = min(len(primes), max_primes)
    selected = np.linspace(0, len(primes) - 1, n, dtype=int)

    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.ravel()

    for i, idx in enumerate(selected):
        p = primes[idx]
        res = results[p]
        im = axes[i].pcolormesh(
            res["s_re"], res["s_im"], res["log_zeta"].T,
            shading="auto", cmap="viridis"
        )
        axes[i].set_title(f"SL(2,F_{p}) — log|ζ(s)| (n={results[p]['num_nontrivial']})")
        axes[i].set_xlabel("Re(s)")
        axes[i].set_ylabel("Im(s)")
        plt.colorbar(im, ax=axes[i], label="log|ζ|")

    plt.tight_layout()
    path = output_dir / "zeta_heatmaps.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    logger.info(f"Heatmaps saved to {path}")
    plt.close()


def plot_functional_equation(
    ratio_data: dict, output_dir: Path
) -> None:
    """Plot functional equation ratio |ζ_p(1-s) / ζ_p(s)| at Re(s) = 0.5."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    primes = sorted(ratio_data.keys())
    colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(primes)))

    for p, color in zip(primes, colors):
        d = ratio_data[p]
        ax.semilogy(
            d["im_vals"], d["ratio"],
            color=color, alpha=0.7, label=f"p={p}"
        )

    ax.axhline(y=1.0, color="red", linestyle="--", alpha=0.5, label="ratio=1 (critical line)")
    ax.set_xlabel("Im(s)")
    ax.set_ylabel("|ζ(1-s) / ζ(s)|")
    ax.set_title("Functional Equation Ratio at Re(s) = 0.5")
    ax.legend(loc="upper right", ncol=2, fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = output_dir / "functional_ratio.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    logger.info(f"Functional ratio plot saved to {path}")
    plt.close()


def plot_ratio_convergence(ratio_data: dict, output_dir: Path) -> None:
    """Plot how |ζ_p(1-s)/ζ_p(s)| -> 1 as p increases."""
    primes = sorted(ratio_data.keys())

    # Measure deviation from 1 at various Im(s)
    im_targets = [0.0, 1.0, 2.0, 5.0, 10.0]
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    for im_t in im_targets:
        deviations = []
        for p in primes:
            d = ratio_data[p]
            idx = np.argmin(np.abs(d["im_vals"] - im_t))
            deviations.append(np.abs(d["ratio"][idx] - 1.0))

        ax.loglog(primes, deviations, "o-", label=f"Im(s)={im_t}")

    ax.set_xlabel("p (prime index)")
    ax.set_ylabel("|ratio - 1| (deviation from critical line)")
    ax.set_title("Convergence of Functional Equation Ratio to 1")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = output_dir / "ratio_convergence.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    logger.info(f"Convergence plot saved to {path}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Exp 15: Karlsson-Friedli spectral zeta on SL(2,F_p)"
    )
    parser.add_argument("--all", action="store_true", help="All primes")
    parser.add_argument("--primes", type=str, help="Specific primes, e.g. '2,3,5,7'")
    parser.add_argument("--plot", action="store_true", help="Generate plots")
    parser.add_argument(
        "--im-max", type=float, default=10.0, help="Max imaginary part"
    )
    parser.add_argument(
        "--im-steps", type=int, default=101, help="Imaginary grid steps"
    )
    args = parser.parse_args()

    if args.all:
        primes = discover_primes()
    elif args.primes:
        primes = [int(p.strip()) for p in args.primes.split(",")]
    else:
        primes = discover_primes()

    logger.info(f"Computing spectral zeta for {len(primes)} primes: {primes}")

    # Compute ζ_p(s) on a grid in the critical strip
    results = compute_zeta_grid(
        primes,
        re_range=(0.0, 1.0, 51),
        im_range=(0.0, args.im_max, args.im_steps),
    )

    # Save raw results
    output_file = OUTPUT_DIR / "zeta_results.npz"
    save_dict = {}
    for p, res in results.items():
        save_dict[f"p{p}_zeta"] = res["zeta"]
    save_dict["primes"] = np.array(primes)
    save_dict["s_re"] = results[primes[0]]["s_re"]
    save_dict["s_im"] = results[primes[0]]["s_im"]
    np.savez_compressed(output_file, **save_dict)
    logger.info(f"Results saved to {output_file}")

    # Compute functional equation ratio
    ratio_data = compute_functional_ratio(results, s_re=0.5)

    # Save ratio data
    ratio_file = OUTPUT_DIR / "functional_ratio.npz"
    ratio_save = {}
    for p, d in ratio_data.items():
        ratio_save[f"p{p}_ratio"] = d["ratio"]
    ratio_save["primes"] = np.array(primes)
    ratio_save["im_vals"] = ratio_data[primes[0]]["im_vals"]
    np.savez_compressed(ratio_file, **ratio_save)
    logger.info(f"Ratio data saved to {ratio_file}")

    if args.plot:
        plot_zeta_heatmaps(results, OUTPUT_DIR)
        plot_functional_equation(ratio_data, OUTPUT_DIR)
        plot_ratio_convergence(ratio_data, OUTPUT_DIR)

    # Print summary
    logger.info("=" * 60)
    logger.info("Exp 15: Karlsson-Friedli Spectral Zeta Summary")
    logger.info("=" * 60)
    for p in primes:
        ev = load_eigenvalues(p)
        nontrivial = np.sum(np.abs(ev - 4.0) > 1e-8)
        zeta_05 = results[p]["zeta"][25, 0]  # Re(s)=0.5, Im(s)=0
        logger.info(f"  p={p:3d}: {nontrivial:4d} eigenvalues, ζ(0.5)={zeta_05:.6f}")

    logger.success("Done!")


if __name__ == "__main__":
    main()
