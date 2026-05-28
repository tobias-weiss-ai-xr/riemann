"""
Graph Spectral Zeta Function Implementation
============================================

Implements the Karlsson-Murugan graph spectral zeta function approach for
connecting Cayley graph Laplacians to Riemann zeta function spectral properties.

Reference: Karlsson & Murugan (2024-2025) on approximate functional equations
via discrete circles.

Key theorem: For graphs satisfying certain regularity conditions, the spectral
zeta function ζ_G(s) approximates ζ(s) with error bounds controlled by graph
parameters.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
from pathlib import Path
from loguru import logger
import argparse
import json
from typing import Tuple, List, Dict, Optional


class SpectralZetaComputer:
    """Compute graph spectral zeta functions and approximate ζ(s) zeros."""

    def __init__(self, graph_data_path: str):
        """
        Initialize with path to graph eigenvalues.

        Args:
            graph_data_path: Path to directory with .pt files containing eigenvalues
        """
        self.graph_data_path = Path(graph_data_path)
        self.eigenvalues_db = self._load_eigenvalues()

    def _load_eigenvalues(self) -> Dict[int, np.ndarray]:
        """Load precomputed eigenvalues for all graphs."""
        eigenvalues = {}

# Load from data/eigenvalues/ directory
        eigen_path = Path("data/eigenvalues")
        if eigen_path.exists():
            for file in eigen_path.glob("*.npy"):
                # Extract prime number from filename
                # Expected format: sl2fp_p2_eigenvalues.npy, sl2fp_p3_eigenvalues.npy, etc.
                try:
                    # Format: sl2fp_p<N>_eigenvalues
                    stem_parts = file.stem.split("_")
                    if len(stem_parts) >= 3 and stem_parts[1].startswith("p"):
                        prime_str = stem_parts[1][1:]  # Remove 'p' prefix
                        prime = int(prime_str)
                        eig_vals = np.load(file)
                        eigenvalues[prime] = eig_vals
                        logger.debug(f"Loaded eigenvalues for p={prime}: {len(eig_vals)} values")
                    else:
                        logger.warning(f"Could not parse prime from {file.name}: unexpected format")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse prime from {file.name}: {e}")

        logger.info(f"Loaded eigenvalues for {len(eigenvalues)} primes: {sorted(eigenvalues.keys())}")
        return eigenvalues

    def compute_spectral_zeta(self, eigenvalues: np.ndarray, t: float,
                               num_terms: Optional[int] = None) -> float:
        """
        Compute spectral zeta function ζ_G(s) for complex s = ½ + it.

        For spectral zeta function:
        ζ_G(s) = Σ_i (λ_i / λ₁)^{-s}

        where λ₁ is the leading eigenvalue. This normalization ensures
        convergence and aligns with discrete circle approximations.

        Args:
            eigenvalues: Sorted Laplacian eigenvalues (λ_1 ≥ λ_2 ≥ ... ≥ 0)
            t: Imaginary component (s = ½ + it)
            num_terms: Number of terms to use (None = all)

        Returns:
            Complex value ζ_G(½ + it)
        """
        if len(eigenvalues) == 0:
            raise ValueError("No eigenvalues provided")

        # Normalize by leading eigenvalue (spectral radius)
        lambda_1 = eigenvalues[0]
        if lambda_1 == 0:
            raise ValueError("Leading eigenvalue is zero")

        normalized_eigs = eigenvalues / lambda_1

        # Use specified number of terms or all
        if num_terms is None:
            evs = normalized_eigs
        else:
            evs = normalized_eigs[:num_terms]

        # Exponentiate: -s = -1/2 - it
        s = complex(0.5, t)
        evs_pow_neg_s = evs ** (-s)

        # Sum all terms
        zeta_g = np.sum(evs_pow_neg_s)

        return zeta_g

    def find_zeros_on_critical_line(self, eigenvalues: np.ndarray, t_range: Tuple[float, float],
                                    num_points: int = 1000, tolerance: float = 1e-6,
                                    num_terms: Optional[int] = None) -> List[Tuple[float, float]]:
        """
        Find approximate zeros of ζ_G(s) on critical line Re(s) = ½.

        Uses sign changes in the real part to locate zero crossings.

        Args:
            eigenvalues: Laplacian eigenvalues
            t_range: Range of t values to search (t_min, t_max)
            num_points: Number of evaluation points
            tolerance: Distance from critical line to consider a match
            num_terms: Number of eigenvalue terms to use

        Returns:
            List of (t, |ζ_G|) tuples for detected zeros
        """
        t_min, t_max = t_range
        t_values = np.linspace(t_min, t_max, num_points)

        # Compute spectral zeta for all t values
        zeta_values = []
        for t in t_values:
            try:
                zeta_g = self.compute_spectral_zeta(eigenvalues, t, num_terms=num_terms)
                zeta_values.append(zeta_g)
            except Exception as e:
                logger.warning(f"Failed to compute ζ_G at t={t}: {e}")
                zeta_values.append(complex(np.inf, np.inf))

        zeta_values = np.array(zeta_values)

        # Find zero crossings in real part
        zeros = []
        for i in range(len(t_values) - 1):
            real_i = zeta_values[i].real
            real_ip1 = zeta_values[i + 1].real

            # Check for sign change (crossing zero)
            if np.sign(real_i) != np.sign(real_ip1):
                # Linear interpolation to find t where Real(ζ_G) = 0
                t_crossing = t_values[i] - real_i * (t_values[i + 1] - t_values[i]) / (real_ip1 - real_i)

                # Compute exact value at crossing
                zeta_at_crossing = self.compute_spectral_zeta(eigenvalues, t_crossing,
                                                              num_terms=num_terms)

                # Check magnitude
                magnitude = abs(zeta_at_crossing)

                zeros.append((t_crossing, magnitude))

        return zeros

    def compute_approximation_error(self, eigenvalues: np.ndarray,
                                      true_zeros: List[float],
                                      num_terms: Optional[int] = None) -> Dict[str, float]:
        """
        Compute approximation error metrics.

        Compares detected zeros with actual ζ(s) zeros.

        Args:
            eigenvalues: Laplacian eigenvalues
            true_zeros: List of t values for actual ζ(s) zeros on critical line
            num_terms: Number of eigenvalue terms to use

        Returns:
            Dictionary with error metrics
        """
        # First few zeros of ζ(s) (imaginary parts)
        if not true_zeros:
            # Use known first few zeros as fallback
            true_zeros = [14.134725142, 21.022039639, 25.010857580,
                         30.424876126, 32.935061588]

        # Search range covering known zeros
        t_min = min(true_zeros) - 5
        t_max = max(true_zeros) + 5

        detected = self.find_zeros_on_critical_line(eigenvalues, (t_min, t_max),
                                                    num_points=2000, num_terms=num_terms)
        detected_ts = [t for t, _ in detected]

        # Match detected zeros to true zeros (find closest true zero for each detected)
        errors = []
        matched_pairs = []

        for true_t in true_zeros:
            if len(detected_ts) == 0:
                errors.append(abs(true_t))  # No detection
                continue

            # Find closest detected zero
            detected_ts_array = np.array(detected_ts)
            closest_idx = np.argmin(np.abs(detected_ts_array - true_t))
            closest_t = detected_ts_array[closest_idx]
            error = abs(closest_t - true_t)

            errors.append(error)
            matched_pairs.append((true_t, closest_t, error))

        # Compute metrics
        mean_error = np.mean(errors) if errors else np.inf
        max_error = np.max(errors) if errors else np.inf
        median_error = np.median(errors) if errors else np.inf

        return {
            "mean_error": float(mean_error),
            "max_error": float(max_error),
            "median_error": float(median_error),
            "detected_count": len(detected_ts),
            "true_count": len(true_zeros),
            "matched_pairs": matched_pairs
        }

    def analyze_graph_sequence(self, primes: Optional[List[int]] = None,
                                num_terms_list: Optional[List[int]] = None) -> Dict:
        """
        Analyze approximation quality across graph sequence.

        Args:
            primes: List of primes to analyze (default: all available)
            num_terms_list: List of num_terms values to test (default: [None])

        Returns:
            Analysis results
        """
        if primes is None:
            primes = sorted(self.eigenvalues_db.keys())

        if num_terms_list is None:
            num_terms_list = [None]

        results = {}
        for prime in primes:
            if prime not in self.eigenvalues_db:
                logger.warning(f"No eigenvalues for p={prime}")
                continue

            eigenvalues = self.eigenvalues_db[prime]
            logger.info(f"Analyzing p={prime}: {len(eigenvalues)} eigenvalues")

            prime_results = {}
            for num_terms in num_terms_list:
                logger.info(f"  Testing with {num_terms} terms")

                # Compute approximation error for first 10 zeros
                first_ten_zeros = [14.134725142, 21.022039639, 25.010857580,
                                  30.424876126, 32.935061588, 37.586178159,
                                  40.918719021, 43.327073281, 48.005150881,
                                  49.773832477]

                errors = self.compute_approximation_error(eigenvalues, first_ten_zeros,
                                                         num_terms=num_terms)

                key = f"terms_{num_terms}" if num_terms else "terms_all"
                prime_results[key] = errors

            results[prime] = prime_results

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Graph spectral zeta function analysis for RH"
    )
    parser.add_argument("--data-path", type=str, default="data/",
                        help="Path to graph data")
    parser.add_argument("--primes", type=str, default="2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61",
                        help="Comma-separated list of primes to analyze")
    parser.add_argument("--output", type=str, default="data/spectral_zeta_results.json",
                        help="Output path for results")
    parser.add_argument("--num-terms", type=int, nargs='+', default=None,
                        help="Specific numbers of eigenvalue terms to test")
    parser.add_argument("--t-min", type=float, default=10.0,
                        help="Minimum t value for zero search")
    parser.add_argument("--t-max", type=float, default=60.0,
                        help="Maximum t value for zero search")

    args = parser.parse_args()

    # Parse primes
    primes = [int(p) for p in args.primes.split(",")]

    # Initialize computer
    computer = SpectralZetaComputer(args.data_path)

    # Analyze each prime
    all_results = {}
    for prime in primes:
        if prime not in computer.eigenvalues_db:
            logger.warning(f"Skipping p={prime}: no eigenvalues available")
            continue

        eigenvalues = computer.eigenvalues_db[prime]
        logger.info(f"\n{'='*60}")
        logger.info(f"Analyzing SL(2,F_{prime}) with {len(eigenvalues)} eigenvalues")
        logger.info(f"{'='*60}")

        prime_results = {}

        # Find zeros with full spectrum
        logger.info(f"\nSearching for zeros in t=[{args.t_min}, {args.t_max}]")
        zeros = computer.find_zeros_on_critical_line(eigenvalues, (args.t_min, args.t_max),
                                                      num_points=5000)
        logger.info(f"Detected {len(zeros)} zeros")

        if zeros:
            t_values = [t for t, mag in zeros]
            magnitudes = [mag for t, mag in zeros]

            logger.info("\nDetected zeros (t, |ζ_G|):")
            for t, mag in zeros[:10]:  # Show first 10
                logger.info(f"  t = {t:12.6f}, |ζ_G| = {mag:10.6e}")

            prime_results["zeros_detected"] = [{"t": t, "magnitude": mag} for t, mag in zeros]

        # Test with different num_terms values if specified
        if args.num_terms:
            logger.info(f"\nTesting with different num_terms values: {args.num_terms}")

            first_ten_zeros = [14.134725142, 21.022039639, 25.010857580,
                              30.424876126, 32.935061588, 37.586178159,
                              40.918719021, 43.327073281, 48.005150881,
                              49.773832477]

            for num_terms in args.num_terms:
                errors = computer.compute_approximation_error(eigenvalues, first_ten_zeros,
                                                             num_terms=num_terms)
                logger.info(f"\n  num_terms={num_terms}:")
                logger.info(f"    Detected count: {errors['detected_count']}")
                logger.info(f"    Mean error: {errors['mean_error']:.6f}")
                logger.info(f"    Median error: {errors['median_error']:.6f}")

                prime_results[f"num_terms_{num_terms}"] = errors

        all_results[f"p_{prime}"] = prime_results

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)

    logger.info(f"\nResults saved to {output_path}")
    logger.info("\nDONE!")


if __name__ == "__main__":
    main()