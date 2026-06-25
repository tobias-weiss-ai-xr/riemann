"""Experiment X: Connes-van Suijlekom spectral triple for L(s,f).

Extends the CvS ζ(s) construction to modular form L-functions.
The restricted Euler product for L(s,f) = ∏_p (1 - a_p p^{-s} + p^{-2s})^{-1}
uses the a_p coefficients from mf_hecke_cc.

PROTOTYPE: Simplified diagonal operator. Full CvS construction requires:
1. Prolate spheroidal wave function (PSWF) basis
2. Weil quadratic form QW_λ
3. Rank-1 perturbation of D_log

Reference: Connes (2025) arXiv:2511.22755 'Zeta Spectral Triples'
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import psycopg2
from loguru import logger

# Connection to LMFDB SQL mirror
LMFDB_CONN = dict(
    host="devmirror.lmfdb.xyz",
    port=5432,
    dbname="lmfdb",
    user="lmfdb",
    password="lmfdb",
)

# First 30 primes
PRIMES_30 = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
    53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113,
]


def fetch_ap_coefficients(label: str, n_primes: int = 30) -> dict:
    """Fetch a_p coefficients for a specific newform from mf_hecke_cc.

    For dim=1 forms, there is one embedding. Returns dict {p: a_p}.

    mf_hecke_cc stores an_normalized = a_n / sqrt(n) (NOT Sato-Tate normalized
    despite column name). So a_n = an_normalized[n-1] * sqrt(n).

    Label format in mf_hecke_cc includes embedding suffix: '11.2.a.a.1.1'
    We accept both '11.2.a.a' (orbit) and '11.2.a.a.1.1' (embedding).
    """
    primes = PRIMES_30[:n_primes]

    with psycopg2.connect(**LMFDB_CONN) as conn:
        with conn.cursor() as cur:
            # Try exact match first, then prefix match (orbit → first embedding)
            cur.execute(
                "SELECT an_normalized FROM mf_hecke_cc WHERE label = %s",
                (label,),
            )
            row = cur.fetchone()
            if row is None:
                # Try with embedding suffix for dim=1
                cur.execute(
                    "SELECT an_normalized FROM mf_hecke_cc WHERE label LIKE %s "
                    "ORDER BY label LIMIT 1",
                    (f"{label}.1.1",),
                )
                row = cur.fetchone()
            if row is None:
                # Try any prefix match
                cur.execute(
                    "SELECT an_normalized FROM mf_hecke_cc WHERE label LIKE %s "
                    "ORDER BY label LIMIT 1",
                    (f"{label}%%",),
                )
                row = cur.fetchone()

    if row is None:
        raise ValueError(f"No data for {label}")

    an_norm = row[0]  # list of [real, imag]
    a_p = {}
    for p in primes:
        idx = p - 1  # 0-indexed: an_norm[p-1] gives a_p/sqrt(p)
        if idx < len(an_norm):
            a_p[p] = an_norm[idx][0] * np.sqrt(p)  # real part, denormalize
        else:
            a_p[p] = 0.0
    return a_p


def fetch_lfunction_zeros(label: str, n_zeros: int = 20) -> list:
    """Fetch actual L-function zeros from LMFDB lfunc_zeros table."""
    # LMFDB label convention: newform 11.2.a.a → L-function 11-2.0.1
    # The lfunc_zeros table stores zeros as JSON array
    with psycopg2.connect(**LMFDB_CONN) as conn:
        with conn.cursor() as cur:
            # Try multiple label formats
            for lfunc_label in [
                label,  # try as-is first
                label.replace(".a.", ".0.1."),
            ]:
                cur.execute(
                    """
                    SELECT zeros FROM lfunc_lfunctions
                    WHERE label LIKE %s
                    ORDER BY degree
                    LIMIT 1
                    """,
                    (f"{label.split('.')[0]}%",),
                )
                row = cur.fetchone()
                if row is not None:
                    break

    if row is None:
        logger.warning(f"No L-function zeros found for {label}")
        return []

    zeros_raw = row[0]
    if isinstance(zeros_raw, str):
        zeros = json.loads(zeros_raw)
    else:
        zeros = list(zeros_raw)

    # zeros are typically stored as imaginary parts, sorted
    return [float(z) for z in zeros[:n_zeros]]


def build_lfunction_operator_diagonal(a_p: dict, N: int = 100, T: float = 50.0) -> tuple:
    """Build simplified diagonal CvS operator for L(s,f).

    The local factor at prime p is: L_p(s) = 1 / (1 - a_p p^{-s} + p^{-2s})

    For the spectral triple, we discretize s = 1/2 + it on [0, T] with N points.
    The operator diagonal stores log|L(1/2+it, f)|.

    Returns (operator, t_grid).
    """
    primes = sorted(a_p.keys())
    t_grid = np.linspace(0.01, T, N)  # avoid t=0 (singularities)

    diag = np.zeros(N)
    for i, t in enumerate(t_grid):
        log_L = 0.0
        s = 0.5 + 1j * t
        for p in primes:
            # Local factor: 1 - a_p * p^{-s} + p^{-2s}
            local = 1 - a_p[p] * p ** (-s) + p ** (-2 * s)
            log_L += -np.log(np.abs(local) + 1e-30)
        diag[i] = log_L

    operator = np.diag(diag)
    return operator, t_grid


def compute_zeros_from_diagonal(operator: np.ndarray, t_grid: np.ndarray,
                                  n_zeros: int = 20) -> np.ndarray:
    """Extract approximate zeros from diagonal operator.

    The zeros of L(s,f) correspond to points where log|L| → -∞.
    On the discretized grid, these are local minima of the diagonal.
    """
    diag = np.diag(operator)
    # Find local minima (zeros correspond to dips in |L|)
    zeros = []
    for i in range(1, len(diag) - 1):
        if diag[i] < diag[i - 1] and diag[i] < diag[i + 1]:
            # Local minimum — interpolate for better accuracy
            t0, t1, t2 = t_grid[i - 1], t_grid[i], t_grid[i + 1]
            d0, d1, d2 = diag[i - 1], diag[i], diag[i + 1]
            # Parabolic interpolation
            denom = (d0 - 2 * d1 + d2)
            if denom != 0:
                offset = 0.5 * (d0 - d2) / denom
                t_min = t1 + offset * (t2 - t0) / 2
            else:
                t_min = t1
            zeros.append(t_min)

    zeros = np.sort(zeros)[:n_zeros]
    return zeros


def build_xi_weil_form(a_p: dict, N: int = 100, T: float = 50.0,
                        lambda_param: float = 0.5) -> np.ndarray:
    """Build Weil quadratic form matrix QW_λ for L(s,f).

    This is a MORE FAITHFUL CvS construction than pure diagonal.
    The Weil quadratic form is:

    QW_λ(s) = Σ_p Σ_k λ^{k/2} [a_p^k / (p^{ks/2} + p^{-ks/2})]

    For λ=0.5 (CvS default for ζ), this captures cross-prime interactions.
    """
    primes = sorted(a_p.keys())
    t_grid = np.linspace(0.01, T, N)
    n = len(t_grid)

    # Build matrix: QW[i,j] = sum over primes of phase correlations
    matrix = np.zeros((n, n))

    for p in primes:
        ap = a_p[p]
        # Phase factor for prime p
        for i in range(n):
            for j in range(n):
                ti, tj = t_grid[i], t_grid[j]
                # Cross-correlation term
                phase_i = np.exp(1j * ti * np.log(p))
                phase_j = np.exp(1j * tj * np.log(p))
                # Simplified Weil kernel
                kernel = (ap * phase_i * np.conj(phase_j)).real / np.sqrt(p)
                matrix[i, j] += kernel * lambda_param

    return matrix


def run_cvs_analysis(label: str, N: int = 100, T: float = 50.0,
                      method: str = "diagonal") -> dict:
    """Run full CvS analysis for a single newform."""
    # Fetch coefficients
    a_p = fetch_ap_coefficients(label, n_primes=13)  # primes ≤ 41 per CvS
    logger.info(f"Fetched {len(a_p)} a_p coefficients for {label}")
    logger.info(f"  a_2={a_p.get(2, 0):.4f}, a_3={a_p.get(3, 0):.4f}, "
                f"a_5={a_p.get(5, 0):.4f}")

    # Build operator
    if method == "diagonal":
        operator, t_grid = build_lfunction_operator_diagonal(a_p, N=N, T=T)
        approx_zeros = compute_zeros_from_diagonal(operator, t_grid, n_zeros=20)
    elif method == "weil":
        matrix = build_xi_weil_form(a_p, N=N, T=T)
        eigenvalues = np.linalg.eigvalsh(matrix)
        approx_zeros = np.sort(np.abs(eigenvalues))[:20]
        t_grid = np.linspace(0.01, T, N)
    else:
        raise ValueError(f"Unknown method: {method}")

    logger.info(f"Method={method}: {len(approx_zeros)} approximate zeros")

    # Fetch actual zeros for comparison
    try:
        true_zeros = fetch_lfunction_zeros(label, n_zeros=20)
    except Exception as e:
        logger.warning(f"Could not fetch true zeros: {e}")
        true_zeros = []

    # Compute errors
    errors = []
    matched = []
    for i, tz in enumerate(true_zeros[:len(approx_zeros)]):
        az = approx_zeros[i]
        err = abs(az - tz)
        errors.append(err)
        matched.append({"k": i + 1, "true": tz, "approx": float(az),
                          "error": float(err)})

    mean_err = float(np.mean(errors)) if errors else float("inf")
    median_err = float(np.median(errors)) if errors else float("inf")

    result = {
        "label": label,
        "method": method,
        "N": N,
        "T": T,
        "a_p": {str(k): float(v) for k, v in a_p.items()},
        "n_primes": len(a_p),
        "approximate_zeros": approx_zeros.tolist(),
        "true_zeros": true_zeros,
        "matched_pairs": matched,
        "mean_error": mean_err,
        "median_error": median_err,
        "max_error": float(max(errors)) if errors else float("inf"),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="CvS L-function spectral triple")
    parser.add_argument("--label", default="11.2.a.a",
                        help="LMFDB newform label (dim=1 for prototype)")
    parser.add_argument("--N", type=int, default=100, help="Grid size")
    parser.add_argument("--T", type=float, default=50.0,
                        help="Upper t range (search for zeros in [0, T])")
    parser.add_argument("--method", default="diagonal",
                        choices=["diagonal", "weil"],
                        help="Construction method")
    parser.add_argument("--output", default="/workspace/data/cvs_lfunction/")
    parser.add_argument("--test-forms", action="store_true",
                        help="Test on multiple dim=1 forms")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.test_forms:
        # Test on multiple well-known dim=1 forms
        test_labels = [
            "11.2.a.a",   # smallest conductor elliptic curve
            "14.2.a.a",   # conductor 14
            "15.2.a.a",   # conductor 15
            "17.2.a.a",   # conductor 17
            "19.2.a.a",   # conductor 19
            "37.2.a.a",   # conductor 37 (rank 1)
        ]
        all_results = []
        for label in test_labels:
            logger.info(f"\n{'='*60}\nProcessing {label}\n{'='*60}")
            try:
                result = run_cvs_analysis(label, N=args.N, T=args.T,
                                          method=args.method)
                all_results.append(result)
                print(f"\n{label}: mean_err={result['mean_error']:.4e}, "
                      f"n_true={len(result['true_zeros'])}")
            except Exception as e:
                logger.error(f"Failed for {label}: {e}")
                all_results.append({"label": label, "error": str(e)})

        output_file = output_dir / f"cvs_lfunc_multi_N{args.N}_{args.method}.json"
        with open(output_file, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nSaved {len(all_results)} results to {output_file}")

    else:
        result = run_cvs_analysis(args.label, N=args.N, T=args.T,
                                   method=args.method)
        output_file = output_dir / f"cvs_lfunc_{args.label.replace('.', '_')}_N{args.N}_{args.method}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\n=== CvS L-function Zeros for {args.label} ===")
        print(f"Method: {args.method}, N={args.N}, T={args.T}")
        print(f"Primes used: {len(result['a_p'])}")
        print(f"Approximate zeros (first 10): "
              f"{[f'{z:.4f}' for z in result['approximate_zeros'][:10]]}")
        if result["true_zeros"]:
            print(f"True zeros (first 10):       "
                  f"{[f'{z:.4f}' for z in result['true_zeros'][:10]]}")
            print(f"\nMean error: {result['mean_error']:.4e}")
            print(f"Median error: {result['median_error']:.4e}")
        print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()
