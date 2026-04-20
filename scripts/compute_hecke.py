"""
Compute Hecke eigenvalues of weight-2 newforms at prime levels using PARI/GP via cypari2.

Outputs:
    data/hecke/p{prime}_hecke.npz   — Hecke eigenvalues a_1..a_n for each cusp form
    data/hecke/manifest.json         — summary of all computed primes

Usage:
    python compute_hecke.py                          # All primes with dim>0
    python compute_hecke.py --primes 11,37           # Specific primes
    python compute_hecke.py --n-eigenvalues 50       # Fewer eigenvalues
    python compute_hecke.py --verbose                # Debug output
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from cypari2 import Pari
from loguru import logger

# Primes where dim S_2(Gamma_0(p)) > 0
PRIMES_WITH_FORMS = [11, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]

# All small primes (including those with dim=0, for Eisenstein series)
ALL_SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]

EPSILON = 1e-10


def setup_logging(verbose: bool = False) -> None:
    """Configure loguru."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        lambda msg: print(msg, end=""),
        level=level,
        format="{time:HH:mm:ss} | {level:<7} | {message}",
    )


def _eval_polmod_to_float(pari: Pari, coeff) -> float:
    """Evaluate a PARI Mod(poly, minpoly) at its largest real root.

    Uses numpy for root-finding and polynomial evaluation.
    PARI Vec gives [a_d, a_{d-1}, ..., a_0]; numerator is LEFT-padded to
    match modulus degree (not right-padded).
    """
    typ = str(pari("type(%s)" % coeff)).strip()
    if typ != "t_POLMOD":
        return float(pari("real(%s)" % coeff))

    # Extract modulus polynomial coefficients [a_d, ..., a_0]
    modulus_pari = pari("component(%s, 1)" % coeff)
    mod_vec = pari("Vec(%s)" % modulus_pari)
    mod_degree = len(mod_vec) - 1
    mod_coeffs = [float(x) for x in mod_vec]

    # Find real roots
    roots = np.roots(mod_coeffs)
    real_roots = [r.real for r in roots if abs(r.imag) < 1e-8]
    if not real_roots:
        raise ValueError("No real roots found for modulus")
    rmax = max(real_roots)

    # Extract numerator
    numer_pari = pari("lift(%s)" % coeff)
    numer_type = str(pari("type(%s)" % numer_pari)).strip()

    if numer_type == "t_INT":
        return float(numer_pari)
    elif numer_type == "t_POL":
        numer_vec = pari("Vec(%s)" % numer_pari)
        numer_degree = len(numer_vec) - 1
        # LEFT-pad with zeros to match modulus degree
        padding = mod_degree - numer_degree
        padded = [0.0] * padding + [float(x) for x in numer_vec]
        return float(np.polyval(padded, rmax))
    else:
        return float(pari("eval(%s)" % numer_pari))


def compute_cusp_forms(pari: Pari, N: int, n_eigenvalues: int) -> list[dict]:
    """
    Compute Hecke eigenvalues for all eigenforms in S_2(Gamma_0(N)).

    Uses mfeigenbasis (NOT mfbasis) to get actual Hecke eigenforms.
    For non-rational forms, evaluates polmod coefficients at the largest real
    root of the minimal polynomial.

    Returns list of dicts:
        {
            "eigenvalues": np.ndarray of shape (n_eigenvalues,),
            "field_degree": int,  # 1 = Q, 2 = quadratic, etc.
            "is_rational": bool,
            "minpoly_coeffs": list[float] or None,
        }
    """
    dim = int(pari("mfdim([%d,2], 1)" % N))
    logger.debug(f"  dim S_2(Gamma_0({N})) = {dim}")

    if dim == 0:
        return []

    # Use mfeigenbasis to get actual eigenforms
    # This returns Galois conjugates grouped, so number of forms may be < dim
    cmd = "my(mf=mfinit([%d,2],1));my(E=mfeigenbasis(mf));" % N
    cmd += "[mfcoefs(E[k],%d) | k<-[1..#E]]" % n_eigenvalues
    all_coeffs = pari(cmd)

    num_eigenforms = len(all_coeffs)
    logger.debug(f"  mfeigenbasis returned {num_eigenforms} eigenform(s) (dim={dim})")

    forms = []
    for k in range(num_eigenforms):
        coeffs = all_coeffs[k]
        a1_raw = coeffs[1]

        # Check if a_1 is rational or polmod
        try:
            a1_str = str(pari("type(%s)" % a1_raw)).strip()
            is_polmod = "POLMOD" in a1_str
        except Exception:
            is_polmod = False

        if is_polmod:
            # Extract minimal polynomial info
            field_degree = int(pari("poldegree(component(%s, 1))" % a1_raw))

            # Evaluate all coefficients at the largest real root of the modulus
            eigenvalues = []
            for n in range(1, n_eigenvalues + 1):
                c = coeffs[n]
                try:
                    val = _eval_polmod_to_float(pari, c)
                except Exception as e:
                    logger.warning(f"    n={n}: evaluation failed ({e}), using 0")
                    val = 0.0
                eigenvalues.append(val)

            eigenvalues = np.array(eigenvalues)

            # Normalize by a_1
            a1_val = eigenvalues[0]
            if abs(a1_val) > EPSILON:
                eigenvalues = eigenvalues / a1_val
            else:
                logger.warning(f"  Form {k + 1}: a_1={a1_val:.2e}, skipping")
                continue

            logger.debug(
                f"  Form {k + 1}: field degree {field_degree}, "
                f"a_1={a1_val:.6f}, a_2={eigenvalues[1]:.4f}"
            )

            forms.append(
                {
                    "eigenvalues": eigenvalues,
                    "field_degree": field_degree,
                    "is_rational": False,
                    "minpoly_coeffs": [
                        float(x) for x in pari("Vec(component(%s, 1))" % a1_raw)
                    ],
                }
            )
        else:
            # Rational eigenform — straightforward
            a1 = float(a1_raw)
            if abs(a1) < EPSILON:
                logger.warning(f"  Form {k + 1}: a_1={a1:.2e}, skipping")
                continue

            eigenvalues = np.array(
                [float(coeffs[n]) / a1 for n in range(1, n_eigenvalues + 1)]
            )

            forms.append(
                {
                    "eigenvalues": eigenvalues,
                    "field_degree": 1,
                    "is_rational": True,
                    "minpoly_coeffs": None,
                }
            )

            logger.debug(
                f"  Form {k + 1}: rational, a_1={a1:.6f}, "
                f"a=[{','.join(f'{x:.0f}' for x in eigenvalues[:5])},...]"
            )

    logger.debug(f"  Kept {len(forms)} eigenform(s)")
    return forms


def compute_eisenstein(pari: Pari, N: int, n_eigenvalues: int) -> np.ndarray | None:
    """
    Compute eigenvalues of the Eisenstein series in S_2^Eis(Gamma_0(N)).

    Returns eigenvalue array or None if Eisenstein subspace is empty.
    """
    dim_eis = int(pari("mfdim([%d,2], 2)" % N))
    logger.debug(f"  dim E_2(Gamma_0({N})) = {dim_eis}")

    if dim_eis == 0:
        return None

    # Get first Eisenstein basis vector coefficients
    cmd = f"my(mf=mfinit([{N},2],2));my(B=mfbasis(mf));mfcoefs(B[1],{n_eigenvalues})"
    coeffs = pari(cmd)
    a1 = float(coeffs[1])

    if abs(a1) < EPSILON:
        logger.debug(f"  Eisenstein a_1={a1:.2e}, skipping")
        return None

    eigenvalues = np.array([float(coeffs[n]) / a1 for n in range(1, n_eigenvalues + 1)])
    return eigenvalues


def validate_eigenvalues(
    prime: int,
    forms: list[dict],
    eisenstein: np.ndarray | None,
) -> list[str]:
    """Validate computed eigenvalues against known values. Returns list of warnings."""
    warnings = []

    for i, form in enumerate(forms):
        ev = form["eigenvalues"]

        # Deligne bound check at prime indices (only for eigenforms!)
        small_primes = [
            2,
            3,
            5,
            7,
            11,
            13,
            17,
            19,
            23,
            29,
            31,
            37,
            41,
            43,
            47,
            53,
            59,
            61,
            67,
            71,
            73,
            79,
            83,
            89,
            97,
        ]
        for p in small_primes:
            if p - 1 < len(ev):
                bound = 2.0 * (p**0.5)
                if abs(ev[p - 1]) > bound + 1e-6:
                    warnings.append(
                        f"N={prime} form {i + 1} ("
                        f"{'rational' if form['is_rational'] else 'deg=' + str(form['field_degree'])}"
                        f"): |a_{p}|={abs(ev[p - 1]):.6f} > "
                        f"2*sqrt({p})={bound:.6f} (Deligne bound violated)"
                    )

    # Check known values for p=11 (dim=1, rational, a=[1,-2,-1,2,1,2,-2,0,-2,-2,...])
    if prime == 11 and len(forms) >= 1:
        ev = forms[0]["eigenvalues"]
        expected = [1.0, -2.0, -1.0, 2.0, 1.0, 2.0, -2.0, 0.0, -2.0, -2.0]
        for j, exp_val in enumerate(expected):
            if j < len(ev) and abs(ev[j] - exp_val) > 1e-6:
                warnings.append(
                    f"N=11 form 1: a_{j + 1}={ev[j]:.6f}, expected {exp_val}"
                )

    return warnings


def compute_prime(
    pari: Pari,
    prime: int,
    n_eigenvalues: int,
) -> tuple[list[dict], np.ndarray | None, int, int]:
    """
    Compute Hecke eigenvalues for all eigenforms at a given prime level.

    Returns:
        (cusp_forms, eisenstein, dim_cusp, dim_eis)
        cusp_forms is a list of dicts with keys:
            eigenvalues, field_degree, is_rational, minpoly_coeffs
    """
    logger.info(f"Computing N={prime}...")
    t0 = time.time()

    dim_cusp = int(pari("mfdim([%d,2], 1)" % prime))
    dim_eis = int(pari("mfdim([%d,2], 2)" % prime))
    logger.debug(f"  dim_cusp={dim_cusp}, dim_eis={dim_eis}")

    cusp_forms = compute_cusp_forms(pari, prime, n_eigenvalues)
    eisenstein = compute_eisenstein(pari, prime, n_eigenvalues) if dim_eis > 0 else None

    elapsed = time.time() - t0
    logger.info(
        f"  N={prime}: {len(cusp_forms)} eigenform(s), "
        f"eisenstein={'yes' if eisenstein is not None else 'no'}, "
        f"{elapsed:.2f}s"
    )

    return cusp_forms, eisenstein, dim_cusp, dim_eis


def save_results(
    prime: int,
    cusp_forms: list[dict],
    eisenstein: np.ndarray | None,
    dim_cusp: int,
    dim_eis: int,
    output_dir: Path,
) -> dict:
    """Save computed eigenvalues to .npz file and return manifest entry."""
    output_dir.mkdir(parents=True, exist_ok=True)

    num_forms = len(cusp_forms)
    n_eig = len(cusp_forms[0]["eigenvalues"]) if num_forms > 0 else 0

    if num_forms > 0:
        eigenvalues = np.array(
            [f["eigenvalues"] for f in cusp_forms]
        )  # (num_forms, n_eig)
        field_degrees = np.array(
            [f["field_degree"] for f in cusp_forms], dtype=np.int64
        )
        is_rational = np.array([f["is_rational"] for f in cusp_forms], dtype=bool)
    else:
        eigenvalues = np.zeros((0, n_eig), dtype=np.float64)
        field_degrees = np.array([], dtype=np.int64)
        is_rational = np.array([], dtype=bool)

    out_path = output_dir / f"p{prime}_hecke.npz"
    np.savez(
        out_path,
        eigenvalues=eigenvalues,
        num_forms=np.int64(num_forms),
        dim_cuspforms=np.int64(dim_cusp),
        dim_eisenstein=np.int64(dim_eis),
        field_degrees=field_degrees,
        is_rational=is_rational,
    )

    if eisenstein is not None:
        eis_path = output_dir / f"p{prime}_eisenstein.npy"
        np.save(eis_path, eisenstein)

    # Validate
    warnings = validate_eigenvalues(prime, cusp_forms, eisenstein)
    for w in warnings:
        logger.warning(f"  {w}")

    # First few eigenvalues for logging
    preview = {}
    for i, form in enumerate(cusp_forms):
        ev = form["eigenvalues"]
        tag = "Q" if form["is_rational"] else f"Q({form['field_degree']})"
        preview[f"form_{i + 1}_{tag}"] = [round(float(x), 4) for x in ev[:5]]
    if eisenstein is not None:
        preview["eisenstein"] = [round(float(x), 4) for x in eisenstein[:5]]

    manifest_entry = {
        "prime": prime,
        "num_eigenforms": num_forms,
        "dim_cuspforms": dim_cusp,
        "dim_eisenstein": dim_eis,
        "n_eigenvalues": n_eig,
        "has_eisenstein_file": eisenstein is not None,
        "preview": preview,
        "forms": [
            {
                "index": i,
                "field_degree": f["field_degree"],
                "is_rational": f["is_rational"],
                "a2": round(float(f["eigenvalues"][1]), 6) if n_eig >= 2 else None,
            }
            for i, f in enumerate(cusp_forms)
        ],
    }

    if warnings:
        manifest_entry["warnings"] = warnings

    return manifest_entry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute Hecke eigenvalues of weight-2 newforms"
    )
    parser.add_argument(
        "--n-eigenvalues",
        type=int,
        default=100,
        help="Number of eigenvalues to compute (default: 100)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/workspace/data/hecke/",
        help="Output directory",
    )
    parser.add_argument(
        "--primes",
        type=str,
        default=None,
        help="Comma-separated primes to compute (default: all with dim>0)",
    )
    parser.add_argument(
        "--include-zero-dim",
        action="store_true",
        help="Also compute for primes with dim=0 (Eisenstein only)",
    )
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which primes to compute
    if args.primes:
        primes = [int(p.strip()) for p in args.primes.split(",")]
    elif args.include_zero_dim:
        primes = ALL_SMALL_PRIMES
    else:
        primes = PRIMES_WITH_FORMS

    logger.info(f"Computing Hecke eigenvalues for {len(primes)} primes: {primes}")
    logger.info(f"n_eigenvalues={args.n_eigenvalues}, output_dir={output_dir}")

    pari = Pari()
    logger.info("PARI/GP initialized via cypari2")

    manifest = {
        "description": "Hecke eigenvalues of weight-2 newforms S_2(Gamma_0(p))",
        "n_eigenvalues": args.n_eigenvalues,
        "primes_computed": [],
    }

    total_t0 = time.time()

    for prime in primes:
        cusp_forms, eisenstein, dim_cusp, dim_eis = compute_prime(
            pari, prime, args.n_eigenvalues
        )
        entry = save_results(
            prime, cusp_forms, eisenstein, dim_cusp, dim_eis, output_dir
        )
        manifest["primes_computed"].append(entry)

    total_elapsed = time.time() - total_t0
    logger.info(f"Done. Total time: {total_elapsed:.2f}s")

    # Save manifest
    manifest["total_time_seconds"] = round(total_elapsed, 2)
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {manifest_path}")


if __name__ == "__main__":
    main()
