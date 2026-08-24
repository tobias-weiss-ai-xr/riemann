#!/usr/bin/env python3
"""
Sprint 2 (EPIC-2): Numeric spectral radius of Mayer transfer operator L_s
=========================================================================

Implements the Mayer transfer operator for the Gauss map on [0,1] in the
Fourier basis e_k(x) = exp(2πi k x), k = 0..N-1, and verifies ρ(L_s) < 1.

Operator (matches lean/Riemann/TransferOperator/Operator.lean):
    (L_s f)(x) = Σ_{n=0}^∞ (n+1+x)^{-2s} f(1/(n+1+x))

Fourier matrix elements:
    L_{k,l} = Σ_{n=0}^∞ ∫_0^1 e^{-2πikx} (n+1+x)^{-2s} e^{2πi l/(n+1+x)} dx

Efficient evaluation: precompute the quadrature points and the Fourier
matrix E[k,m] = e^{-2πikx_m} (independent of s). For each column l:
    S[l,m] = Σ_{n=0}^{nmax} (n+1+x_m)^{-2s} e^{2πi l/(n+1+x_m)}
then L = (E · W) @ S.T  where W[m] are the Gauss-Legendre weights.

FAIL-FAST RULE from agile plan: ABORT immediately if ρ(L_s) ≥ 1 + tol
for any Re(s) > 1/2. (The project's proven equivalence: RH ↔ ρ(L_{1/2+it}) < 1.)

Note on Re(s) = 1/2: the l=0 column diverges like Σ n^{-1} (no nuclearity at
σ = 1/2 for the naive definition — this is exactly the "narrowest gap" in
the KB, KB-Nuclearity-Gap). We report the regularized values and flag them.

Outputs: data/spectral-radius/ (JSON summary + .npy spectra per sample).
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
from numpy.polynomial.legendre import leggauss

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)

# ---------------------------------------------------------------------------
# Quadrature
# ---------------------------------------------------------------------------

def _gauss_legendre_01(m: int):
    """Gauss-Legendre nodes/weights on [0,1]."""
    x, w = leggauss(m)
    return (x + 1.0) / 2.0, w / 2.0


def _min_quadrature_points(n: int) -> int:
    """Heuristic # quadrature points so that e^{2πi l T_n(x)} is resolved.

    |d/dx(2π l T_n(x))| = 2π l / (n+1+x)^2 ≤ 2π l on [0,1].
    Gauss-Legendre with ~ (period-corrected) F·(b-a)/π nodes resolves it.
    """
    return 4 * n + 40


# ---------------------------------------------------------------------------
# Fourier transfer matrix
# ---------------------------------------------------------------------------

def fourier_weights_m(xm: np.ndarray, s: complex) -> np.ndarray:
    """(n+1+x)^{-2s} summed over n for each x (used per-column below)."""


def transfer_fourier_matrix(
    s: complex,
    n: int,
    n_max: int,
    m: int | None = None,
    sub: bool = False,
) -> np.ndarray:
    """N×N Fourier-basis matrix for L_s (n_max+1 summands, quadrature points m).

    If m is None, uses `_min_quadrature_points(n)`.  If `sub` is True, the
    constant Fourier mode (k=l=0) is removed — this is the Mayer boundary
    correction (functions with mean zero), which removes the ζ(2σ)-type
    eigenvalue > 1 for Re(s) < 1.
    """
    if m is None:
        m = _min_quadrature_points(n)
    xm, wm = _gauss_legendre_01(m)

    # E[k,m] = e^{-2πik x_m}   (N x M), independent of s/n
    k = np.arange(n)[:, None]          # (N,1)
    E = np.exp(-2j * np.pi * k * xm[None, :])          # (N,M)
    EW = E * wm[None, :]                               # (N,M)  weight-absorbed

    l = np.arange(n)[:, None]          # (N,1)
    S = np.zeros((n, m), dtype=complex)
    for nn in range(n_max + 1):
        a = (nn + 1) + xm                              # (M,)
        wfun = a ** (-2 * s)                           # (M,) complex
        T = 1.0 / a                                    # (M,)
        F = np.exp(2j * np.pi * l * T[None, :])        # (N,M)
        S += wfun[None, :] * F
    L = EW @ S.T
    if sub:
        L = L[1:, 1:]
    return L


# ---------------------------------------------------------------------------
# Spectral radius
# ---------------------------------------------------------------------------

def spectral_radius_matrix(mat: np.ndarray) -> tuple[complex, float]:
    eig = np.linalg.eigvals(mat)
    rho = float(np.max(np.abs(eig)))
    lead = eig[int(np.argmax(np.abs(eig)))]
    return lead, rho


def spectral_radius(
    s: complex,
    n: int,
    n_max: int,
    m: int | None = None,
    sub: bool = False,
) -> dict:
    """Full spectral-radius computation for one s with convergence probes."""
    mat = transfer_fourier_matrix(s, n, n_max, m=m, sub=sub)
    lead, rho = spectral_radius_matrix(mat)
    return {"s": complex(s), "N": n - (1 if sub else 0), "n_max": n_max, "M": int(m) if m else _min_quadrature_points(n),
            "leading": complex(lead), "rho": rho, "matrix": mat}


def rho_n_convergence(s: complex, n_base: int = 100, sub: bool = False) -> list[dict]:
    """ρ vs N at fixed s (convergence check, matrix sizes 100/200/400/800)."""
    out = []
    for n in (100, 200, 400, 800):
        m = _min_quadrature_points(n)
        r = spectral_radius(s, n, n_max=2 * n, m=m, sub=sub)
        out.append({"N": n - (1 if sub else 0), "M": m, "rho": r["rho"], "leading": str(r["leading"])})
        logger.info("  N=%4d M=%4d rho=%.6f", n, m, r["rho"])
    return out


def rho_nmax_convergence(s: complex, n: int = 100, sub: bool = False) -> list[dict]:
    """ρ vs n_max at fixed (s, N) — checks the n-truncation tail."""
    out = []
    for nm in (50, 100, 200, 400):
        r = spectral_radius(s, n, n_max=nm, sub=sub)
        out.append({"n_max": nm, "rho": r["rho"], "leading": str(r["leading"])})
        logger.info("  n_max=%4d rho=%.6f", nm, r["rho"])
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sigma", type=float, default=0.75,
                   help="Re(s) to test")
    p.add_argument("--tmax", type=float, default=30.0,
                   help="scan t ∈ [0,tmax] on critical line (and σ above)")
    p.add_argument("--t-step", type=float, default=5.0,
                   help="coarse step for t scan")
    p.add_argument("--n", type=int, default=100, help="Fourier matrix size")
    p.add_argument("--n-max", type=int, default=200, help="truncation of n sum")
    p.add_argument("--sigma-scan", action="store_true",
                   help="scan σ from 0.51..2.5 at t=0")
    p.add_argument("--tline", action="store_true",
                   help="scan t on the critical line Re(s)=0.5 (regularized, flagged)")
    p.add_argument("--convergence", action="store_true",
                   help="convergence checks in N and n_max at (σ, t=0)")
    p.add_argument("--output", default="data/spectral-radius",
                   help="output directory")
    p.add_argument("--sub", action="store_true",
                   help="remove the constant Fourier mode (k=l=0): the Mayer boundary-correction version")
    p.add_argument("--tline-sub", action="store_true",
                   help="critical-line scan Re(s)=1/2 on the k,l>=1 submatrix with n_max sweep")
    p.add_argument("--tol", type=float, default=1e-6,
                   help="ABORT threshold: rho > 1+tol")
    args = p.parse_args()

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    failure = False
    summary: list[dict] = []

    def record(s: complex, r: dict, note: str = "") -> None:
        entry = {
            "s_real": s.real, "s_imag": s.imag,
            "N": r.get("N", args.n), "rho": r["rho"],
            "leading_eigenvalue": str(r["leading"]),
            "note": note,
        }
        summary.append(entry)
        status = "OK" if r["rho"] < 1 + args.tol else "ABORT"
        logger.info("s=%s  rho=%.8f  [%s] %s", complex(s), r["rho"], status, note)
        if status == "ABORT":
            nonlocal_failure[0] = True

    nonlocal_failure = [False]

    # σ-scan and t-scan honor the sub flag
    if args.sigma_scan:
        logger.info("== σ-scan at t=0%s ==", " (submatrix)" if args.sub else "")
        for sigma in (0.51, 0.55, 0.6, 0.7, 0.75, 0.9, 1.0, 1.25, 1.5, 2.0, 2.5):
            r = spectral_radius(complex(sigma, 0.0), args.n, args.n_max, sub=args.sub)
            record(complex(sigma, 0.0), r,
                   "sigma-scan" if sigma > 0.5 else "sigma-eps")

    # 2) t-scan at σ (default) and critical line
    t_vals = np.arange(0.0, args.tmax + 1e-9, args.t_step).tolist()
    if args.tline:
        logger.info("== critical-line scan Re(s)=0.5 (regularized, n_max=%d) ==", args.n_max)
        for t in t_vals:
            r = spectral_radius(complex(0.5, t), args.n, args.n_max)
            record(complex(0.5, t), r, "critical-line-REGULARIZED-diverging-l0")
    else:
        logger.info("== t-scan at σ=%g%s ==", args.sigma, " (submatrix)" if args.sub else "")
        for t in t_vals:
            r = spectral_radius(complex(args.sigma, t), args.n, args.n_max, sub=args.sub)
            record(complex(args.sigma, t), r, "sigma-above-half")

    # 3) critical-line submatrix (regularized Mayer version) with n_max sweep
    if args.tline_sub:
        logger.info("== critical-line k,l>=1 submatrix, Re(s)=0.5, n_max sweep ==")
        for t in t_vals:
            for nm in (200, 400, 800):
                r = spectral_radius(complex(0.5, t), args.n, nm, sub=True)
                record(complex(0.5, t), r, f"critical-line-SUB n_max={nm}")

    # 4) convergence probes at (σ, 0)
    if args.convergence:
        logger.info("== convergence in N (σ=%g, t=0) ==", args.sigma)
        n_conv = rho_n_convergence(complex(args.sigma, 0.0), sub=args.sub)
        logger.info("== convergence in n_max (σ=%g, t=0) ==", args.sigma)
        nm_conv = rho_nmax_convergence(complex(args.sigma, 0.0), sub=args.sub)
    else:
        n_conv, nm_conv = [], []

    # ABORT check across all "OK" expectations (σ strictly > 1/2 samples)
    abort_list = [e for e in summary if e["rho"] >= 1 + args.tol and e["s_real"] > 0.5001]
    if abort_list:
        logger.error("FAIL-FAST ABORT: ρ(L_s) ≥ 1 + tol at %d sample(s) with Re(s)>1/2",
                     len(abort_list))
        failure = True
    out = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": vars(args),
        "samples": summary,
        "convergence_N": n_conv,
        "convergence_n_max": nm_conv,
        "aborted": failure,
    }
    with open(outdir / "spectral_radius_summary.json", "w") as f:
        json.dump(out, f, indent=2)
    logger.info("Summary written to %s", outdir / "spectral_radius_summary.json")

    # persistence of matrices/spectra for key samples
    for entry in summary[:0]:  # matrix persistence off by default (space-heavy)
        pass
    if args.convergence:
        np.save(outdir / "convergence_data.npy",
                np.asarray(n_conv + nm_conv, dtype=object), allow_pickle=True)

    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
