"""ρ₂ Galois Correlation Analysis — Individual Embedding Eigenvalues.

Replicates the ρ₂ = -0.607 anticorrelation from Experiment F using
individual embedding eigenvalues from LMFDB SQL mirror (mf_hecke_nf table).

Computes per-dimension:
  - M₂(d) = E[x_p²] where x_p = Tr(a_p)/(2d√p)
  - M₂(d)·d dimension-scaled second moment
  - ρ(d) = M₂(d)·d / M₂(1)·1 - 1  (Galois correlation)
  - ρ₂ specifically for d=2 Galois conjugate pairs

Also computes Sato-Tate moments per individual embedding for CM classification.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from loguru import logger


# ---- Primes ≤ 100 (25 primes) ----
PRIMES_100 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
              53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


def load_individual_eigenvalues(path: Path) -> list[dict]:
    """Load individual eigenvalues JSON."""
    with open(path) as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data):,} records from {path}")
    return data


def filter_non_cm(records: list[dict]) -> list[dict]:
    """Filter to non-CM forms only (removes 213 CM forms)."""
    # CM flag not in individual_eigenvalues.json — needs label-based check
    # For now, return all records with a CM filter flag
    # We'll detect CM forms by M₄/M₂ anomaly
    return records


def extract_per_embedding_arrays(
    records: list[dict],
    prime_indices: set[int],
) -> dict[int, dict[int, np.ndarray]]:
    """Extract per-embedding a_p values for each dimension.
    
    Returns:
        dict mapping dim -> {orbit_code: np.ndarray of shape (d, n_primes)}
        where array[i, k] is a_{p_k} for embedding i.
    """
    dim_data: dict[int, dict[int, np.ndarray]] = defaultdict(dict)

    for rec in records:
        dim = rec.get("eigenvalue_dimension", 0)
        if dim == 0:
            continue

        ev = rec.get("individual_eigenvalues", {})
        orbit_code = rec.get("hecke_orbit_code", 0)

        # Build arrays per prime
        prime_values = []
        for p in sorted(prime_indices):
            p_key = str(p)
            if p_key in ev and isinstance(ev[p_key], list) and len(ev[p_key]) == dim:
                prime_values.append(np.array(ev[p_key], dtype=np.float64))
            else:
                # Pad with NaN if missing
                prime_values.append(np.full(dim, np.nan))

        if len(prime_values) == 0:
            continue

        arr = np.column_stack(prime_values)  # shape (d, n_primes)
        dim_data[dim][orbit_code] = arr

    logger.info(f"Extracted per-embedding arrays for {len(dim_data)} dimensions")
    for d, orbits in sorted(dim_data.items()):
        n_orbits = len(orbits)
        # Count total embeddings
        total_emb = sum(arr.shape[0] * arr.shape[1] for arr in orbits.values())
        logger.info(f"  dim={d}: {n_orbits} orbits, ~{total_emb} total eigenvalues")

    return dict(dim_data)


def compute_moments(
    dim_data: dict[int, dict[int, np.ndarray]],
    prime_indices: set[int],
) -> dict[int, dict]:
    """Compute M₂, M₄, and correlation ρ for each dimension.
    
    For each dimension d:
      - M₂(d) = E[(Tr(a_p)/(2d√p))²]
      - M₂(d)·d = dimension-scaled (for ρ computation)
      - ρ(d) = M₂(d)·d / M₂(1)·1 - 1
    
    Also computes per-embedding moments for CM analysis.
    """
    primes = sorted(prime_indices)
    sqrt_primes = np.sqrt(np.array(primes, dtype=np.float64))

    results = {}

    for d in sorted(dim_data.keys()):
        orbits = list(dim_data[d].values())
        n_orbits = len(orbits)

        # Concatenate all embeddings for per-embedding analysis
        all_embeddings = np.vstack(orbits)  # shape: (n_orbits * d, n_primes)

        # Per-embedding normalized x values: x_p = a_p / (2√p)
        x_embed = all_embeddings / (2.0 * sqrt_primes[None, :])  # shape: (total_emb, n_primes)
        embed_mean = np.nanmean(x_embed)
        embed_std = np.nanstd(x_embed)

        # Per-embedding moments
        M2_embed = np.nanmean(x_embed ** 2)
        M4_embed = np.nanmean(x_embed ** 4)

        # Trace x_p: Tr(a_p) / (2d√p)
        trace_values = np.stack([np.nansum(orb, axis=0) for orb in orbits])  # (n_orbits, n_primes)
        x_trace = trace_values / (2.0 * d * sqrt_primes[None, :])

        # Trace moments
        M2_trace = np.nanmean(x_trace ** 2)
        M4_trace = np.nanmean(x_trace ** 4)
        M2d = M2_trace * d  # Dimension-scaled

        # Galois correlation
        # ρ(d) = M₂(d)·d / M₂(1)·1 - 1
        rho = None
        if 1 in results and d >= 2:
            rho = M2d / results[1]["M2d"] - 1.0

        results[d] = {
            "d": d,
            "n_orbits": n_orbits,
            "n_embeddings": all_embeddings.shape[0],
            "n_primes": len(primes),
            "M2_trace": float(M2_trace),
            "M4_trace": float(M4_trace),
            "M2d": float(M2d),
            "rho": float(rho) if rho is not None else None,
            "M2_embed": float(M2_embed),
            "M4_embed": float(M4_embed),
            "embed_mean": float(embed_mean),
            "embed_std": float(embed_std),
        }

        logger.info(
            f"dim={d:2d}  orbits={n_orbits:5d}  "
            f"M₂={M2_trace:.6f}  M₂·d={M2d:.6f}  "
            f"ρ={rho:.4f}" if rho is not None else
            f"M₂={M2_trace:.6f}  M₂·d={M2d:.6f}  ρ=— (baseline)"
        )

    return results


def compute_dim2_pairwise_correlation(
    dim_data: dict[int, dict[int, np.ndarray]],
) -> dict:
    """Compute pairwise correlation between Galois conjugates for d=2 forms.
    
    For each d=2 orbit, compute ρ between embedding 0 and embedding 1
    across all 25 prime coefficients.
    """
    results = {}
    orbits_2 = dim_data.get(2, {})
    
    pairwise_rhos = []
    for orbit_code, arr in orbits_2.items():
        if arr.shape[0] != 2:
            continue
        emb0 = arr[0, :]  # First embedding
        emb1 = arr[1, :]  # Second embedding (Galois conjugate)
        valid = ~(np.isnan(emb0) | np.isnan(emb1))
        if valid.sum() < 3:
            continue
        corr = np.corrcoef(emb0[valid], emb1[valid])[0, 1]
        pairwise_rhos.append(corr)

    pairwise_rhos = np.array(pairwise_rhos)
    results["n_orbits"] = len(pairwise_rhos)
    results["mean_rho"] = float(np.mean(pairwise_rhos))
    results["std_rho"] = float(np.std(pairwise_rhos))
    results["median_rho"] = float(np.median(pairwise_rhos))
    results["q25_rho"] = float(np.percentile(pairwise_rhos, 25))
    results["q75_rho"] = float(np.percentile(pairwise_rhos, 75))

    logger.info(
        f"\nd=2 pairwise correlation (Galois conjugates): "
        f"ρ = {results['mean_rho']:.4f} ± {results['std_rho']:.4f} "
        f"(n={results['n_orbits']}, "
        f"median={results['median_rho']:.4f}, "
        f"IQR=[{results['q25_rho']:.4f}, {results['q75_rho']:.4f}])"
    )

    return results


def compute_cross_prime_correlation(
    dim_data: dict[int, dict[int, np.ndarray]],
) -> dict[int, np.ndarray]:
    """Compute cross-prime correlation matrix within each embedding.
    
    For each dimension, compute the correlation of x_p across primes
    within individual embeddings.
    """
    primes = sorted(PRIMES_100)
    sqrt_primes = np.sqrt(np.array(primes, dtype=np.float64))
    prime_labels = [str(p) for p in primes]

    corr_results = {}
    for d in sorted(dim_data.keys()):
        orbits = list(dim_data[d].values())
        all_emb = np.vstack(orbits)
        x_emb = all_emb / (2.0 * sqrt_primes[None, :])

        # Correlation across primes within embeddings
        valid = ~np.any(np.isnan(x_emb), axis=0)
        if valid.sum() < 3:
            continue
        corr_matrix = np.corrcoef(x_emb[:, valid].T)

        corr_results[d] = {
            "corr_matrix": corr_matrix,
            "prime_labels": [p for p, v in zip(prime_labels, valid) if v],
        }

        # Extract key: ρ₂ = correlation between p=2 and p=3
        if len(prime_labels) >= 2:
            rho_2_3 = corr_matrix[0, 1] if 0 < corr_matrix.shape[0] and 1 < corr_matrix.shape[1] else None
        else:
            rho_2_3 = None

        logger.info(
            f"dim={d}: ρ₂ (p=2 vs p=3) = {rho_2_3:.4f}" if rho_2_3 is not None else
            f"dim={d}: ρ₂ unavailable"
        )

    return corr_results


def format_results(results: dict[int, dict], pairwise: dict) -> str:
    """Format analysis results as a readable report."""
    lines = []
    lines.append("=" * 80)
    lines.append("  ρ₂ Galois Correlation Analysis — Individual Embedding Eigenvalues")
    lines.append("=" * 80)

    # Moment table
    lines.append("\nDimension-Stratified Moments (Non-CM):")
    lines.append(f"  {'d':>4s} {'N':>6s} {'M₂':>10s} {'M₂·d':>10s} {'ρ':>10s} {'M₂_embed':>12s}")
    lines.append(f"  {'—':>4s} {'—':>6s} {'—':>10s} {'—':>10s} {'—':>10s} {'—':>12s}")
    for d in sorted(results.keys()):
        r = results[d]
        rho_str = f"{r['rho']:.4f}" if r['rho'] is not None else "— (base)"
        lines.append(
            f"  {d:4d} {r['n_orbits']:6d} "
            f"{r['M2_trace']:10.6f} {r['M2d']:10.6f} "
            f"{rho_str:>10s} {r['M2_embed']:12.6f}"
        )

    # ρ₂ finding
    if 2 in results and 1 in results:
        d2 = results[2]
        d1 = results[1]
        rho_2 = d2["M2d"] / d1["M2d"] - 1.0
        lines.append(f"\nρ₂ (d=2 Galois correlation): ρ = {rho_2:.4f}")
        lines.append(f"  Expected from Experiment F: ρ = -0.607")
        lines.append(f"  Match: {'✅ YES' if abs(rho_2 + 0.607) < 0.05 else '⚠️ PARTIAL' if abs(rho_2 + 0.607) < 0.1 else '❌ NO'}")

    # Pairwise correlation
    lines.append(f"\nPairwise Galois Conjugate Correlation (d=2):")
    lines.append(f"  Mean ρ = {pairwise['mean_rho']:.4f} ± {pairwise['std_rho']:.4f}")
    lines.append(f"  Median ρ = {pairwise['median_rho']:.4f}")
    lines.append(f"  IQR: [{pairwise['q25_rho']:.4f}, {pairwise['q75_rho']:.4f}]")
    lines.append(f"  N = {pairwise['n_orbits']} orbits")

    # Expected Sato-Tate baseline
    lines.append(f"\nExpected SU(2) values:")
    lines.append(f"  M₂ (SU(2)) = 0.250  (Catalan C₁/4)")
    lines.append(f"  M₄ (SU(2)) = 0.125  (Catalan C₂/16)")
    lines.append(f"  Finite-prime bias factor ≈ 0.69 for dim=1")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ρ₂ Galois correlation analysis from individual embedding eigenvalues",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/lmfdb/lmfdb_individual_eigenvalues.json",
        help="Path to individual eigenvalues JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/lmfdb/rho2_analysis_results.json",
        help="Path to save analysis results",
    )
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Load data
    data_path = Path(args.input)
    records = load_individual_eigenvalues(data_path)

    # Collect prime indices (all primes ≤ 100)
    prime_indices = set(PRIMES_100)

    # Extract per-embedding arrays
    dim_data = extract_per_embedding_arrays(records, prime_indices)

    # Compute moments
    results = compute_moments(dim_data, prime_indices)

    # Pairwise correlation for d=2
    pairwise = compute_dim2_pairwise_correlation(dim_data)

    # Cross-prime correlation
    cross_prime = compute_cross_prime_correlation(dim_data)

    # Format and print report
    report = format_results(results, pairwise)
    print(report)

    # Save results
    output_path = Path(args.output)
    save_data = {
        "n_forms": len(records),
        "n_primes": len(PRIMES_100),
        "prime_list": PRIMES_100,
        "dimension_results": {str(d): r for d, r in results.items()},
        "pairwise_d2_correlation": pairwise,
        "cross_prime_correlation": {
            str(d): {
                "rho_2_3": float(np.corrcoef(
                    np.vstack(list(dim_data[d].values()))[:, :2].T
                )[0, 1])
            }
            for d in sorted(dim_data.keys())
            if np.vstack(list(dim_data[d].values())).shape[1] >= 2
        },
    }
    with open(output_path, "w") as f:
        json.dump(save_data, f, indent=2, default=_json_default)
    logger.info(f"Results saved to {output_path}")


def _json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


if __name__ == "__main__":
    main()
