#!/usr/bin/env python3
"""RT-B2 -- Bonanno-style Mayer matrix in a shifted-Legendre basis.

Independent cross-check of the Nystrom-collocation spectrum (section S2 of
research/ROUTES_FLEET_PLAN.md): the transfer operator

    (L_s f)(x) = sum_{k>=0} (k+1+x)^{-2s} f(1/(k+1+x))

is Galerkin-projected onto the orthonormal shifted-Legendre basis on (0,1),
P_n(x) = sqrt(2n+1) * L_n(2x-1):

    M[i,j] = int_0^1 P_i(x) sum_{k=0}^{nmax} (k+1+x)^{-2s} P_j(1/(k+1+x)) dx

computed with Gauss-Legendre quadrature and k-chunking. If the eigenvalue-1
margin m(s) = min_j |1 - lambda_j| from this polynomial basis agrees with the
collocation margin, the gap is not a collocation artifact.

Quadrature resolution: the weight (k+1+x)^{-2s} oscillates ~ Im(s)/pi cycles
over (0,1) for k=0, so N_quad must scale with Im(s). Convergence-verified:
N_quad = max(512, ceil(t)) equals the N_quad = 2*t result to ~1e-12 in the
matrix entries at t = 1100.574 (while a fixed N_quad = 512 is NOT converged
there: m changes 0.201 -> 0.261).

Cross-check: scripts/nystrom_collocation.margin / leading_pair at n=384 with
the same nmax (plus an n=512 secondary reference -- exp19p uses N=512 for
t > 500). Gate: all 12 (N, s) entries present AND |m_poly - m_nystrom|
<= 5e-2 at N=384 for every s point. Any disagreement is reported verbatim
and fails the gate (honesty rule).

Output: data/routes/rt_b2.json, checkpointed after each s point.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np
from numpy.polynomial.legendre import leggauss

sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nystrom_collocation import leading_pair, margin  # noqa: E402

N_LIST = [64, 128, 256, 384]                                  # basis sizes
S_POINTS = [0.51 + 1100.574j, 0.52 + 1100.574j, 0.55 + 124.2568j]
NMAX = 8000                     # k-truncation (matches exp19p resolution)
K_CHUNK = 100                   # k-chunk for the assembly
NYSTROM_N = 384                 # collocation size for the cross-check
NYSTROM_N2 = 512                # secondary reference (exp19p res. for t>500)
NYSTROM_CHUNK = 64              # memory guard: (64, 384, 384) temporaries
GATE_TOL = 5e-2                 # poly-vs-nystrom margin agreement at N=384
OUT_PATH = os.path.join("data", "routes", "rt_b2.json")


def log(msg: str) -> None:
    print(f"[rt-b2] {msg}", flush=True)


def s_key(s: complex) -> str:
    return f"{s.real:.4g}+{s.imag:.4g}j"


def n_quad_for(s: complex) -> int:
    """Gauss-Legendre node count: resolve the ~Im(s)/pi fastest oscillations."""
    return max(512, math.ceil(abs(s.imag)))


def shifted_legendre(u: np.ndarray, n: int) -> np.ndarray:
    """Orthonormal shifted Legendre P_m(u) = sqrt(2m+1) L_m(2u-1), m = 0..n-1.

    Returns array (len(u), n). u in (0,1); three-term recurrence is stable
    there (|L_m| <= 1 on [-1,1]).
    """
    v = 2.0 * u - 1.0
    out = np.empty((u.size, n))
    lm1 = np.ones_like(v)
    out[:, 0] = 1.0
    if n > 1:
        out[:, 1] = v
    l = v
    for m in range(1, n - 1):
        lp1 = ((2 * m + 1) * v * l - m * lm1) / (m + 1)
        out[:, m + 1] = lp1
        lm1, l = l, lp1
    out *= np.sqrt(2.0 * np.arange(n) + 1.0)
    return out


def bonanno_matrix(s: complex, n: int, n_quad: int, nmax: int = NMAX,
                   chunk: int = K_CHUNK) -> np.ndarray:
    """Galerkin matrix M[i,j] = <P_i, L_s P_j> in the shifted-Legendre basis."""
    xq, wq = leggauss(n_quad)
    xq = 0.5 * xq + 0.5
    wq = 0.5 * wq
    phi = shifted_legendre(xq, n)                       # (n_quad, n) real
    g = np.zeros((n_quad, n), dtype=complex)            # sum_k wf * P_j(1/(k+1+x))
    for c0 in range(0, nmax + 1, chunk):
        ks = np.arange(c0, min(c0 + chunk, nmax + 1))
        a = (ks[:, None] + 1) + xq[None, :]            # (c, q) real
        wf = a ** (-2.0 * s)                            # (c, q) complex
        y = (1.0 / a).ravel()                           # real preimages
        phiy = shifted_legendre(y, n).reshape(a.shape[0], n_quad, n)
        g += np.einsum("cq,cqn->qn", wf, phiy, optimize=True)
    return phi.T @ (wq[:, None] * g)                    # (n, n) complex


def spectrum(mat: np.ndarray) -> dict:
    """m(s), |lambda1|, |lambda2| of a Galerkin/collocation matrix."""
    ev = np.linalg.eigvals(mat)
    o = np.argsort(-np.abs(ev))
    return {
        "margin": float(np.min(np.abs(ev - 1.0))),
        "abs_lambda1": float(abs(ev[o[0]])),
        "abs_lambda2": float(abs(ev[o[1]])),
    }


def load_ckpt() -> dict:
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return {"task": "RT-B2", "params": {
        "basis": "orthonormal shifted Legendre on (0,1)",
        "N_list": N_LIST, "s_points": [s_key(s) for s in S_POINTS],
        "n_quad_rule": "max(512, ceil(Im s))",
        "nmax": NMAX, "k_chunk": K_CHUNK,
        "nystrom": {"n": NYSTROM_N, "n_secondary": NYSTROM_N2,
                    "nmax": NMAX, "chunk": NYSTROM_CHUNK},
        "gate_tol_at_N384": GATE_TOL,
    }, "points": []}


def save(ckpt: dict) -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ckpt, fh, indent=1)
    os.replace(tmp, OUT_PATH)


def compute() -> dict:
    """Fill the checkpoint point by point (resume-safe)."""
    ckpt = load_ckpt()
    done = {p["s"] for p in ckpt["points"]}
    for s in S_POINTS:
        if s_key(s) in done:
            log(f"s = {s}: already done, skipping")
            continue
        t0 = time.time()
        nq = n_quad_for(s)
        rec = {
            "s": s_key(s), "re": s.real, "im": s.imag, "n_quad": nq,
            "nystrom": {"n": NYSTROM_N,
                        "margin": margin(s, NYSTROM_N, NMAX, chunk=NYSTROM_CHUNK),
                        "abs_lambda1": None, "abs_lambda2": None},
            "nystrom_secondary": {"n": NYSTROM_N2},
            "poly": [],
        }
        rec["nystrom"]["abs_lambda1"], rec["nystrom"]["abs_lambda2"] = leading_pair(
            s, NYSTROM_N, NMAX, chunk=NYSTROM_CHUNK)
        l1, l2 = leading_pair(s, NYSTROM_N2, NMAX, chunk=NYSTROM_CHUNK)
        rec["nystrom_secondary"].update(
            margin=margin(s, NYSTROM_N2, NMAX, chunk=NYSTROM_CHUNK),
            abs_lambda1=l1, abs_lambda2=l2)
        # One assembly at N=384, sliced: M_N = M_full[:N,:N] exactly (same
        # quadrature and nested basis).
        m_full = bonanno_matrix(s, max(N_LIST), nq)
        for n in N_LIST:
            sp = spectrum(m_full[:n, :n])
            sp["N"] = n
            rec["poly"].append(sp)
            log(f"  s={s_key(s)} N={n:3d} Q={nq}  m={sp['margin']:.6f}  "
                f"|l1|={sp['abs_lambda1']:.6f}  |l2|={sp['abs_lambda2']:.6f}")
        nys = rec["nystrom"]
        log(f"s = {s}: nystrom(384) m={nys['margin']:.6f} "
            f"|l1|={nys['abs_lambda1']:.6f} |l2|={nys['abs_lambda2']:.6f}")
        nys2 = rec["nystrom_secondary"]
        log(f"s = {s}: nystrom(512) m={nys2['margin']:.6f} "
            f"|l1|={nys2['abs_lambda1']:.6f} |l2|={nys2['abs_lambda2']:.6f}")
        d384 = abs(rec["poly"][-1]["margin"] - nys["margin"])
        log(f"s = {s}: |m_poly - m_nystrom| at N=384 = {d384:.3e} "
            f"({'OK' if d384 <= GATE_TOL else 'MISMATCH beyond ' + str(GATE_TOL)})")
        ckpt["points"].append(rec)
        save(ckpt)
        log(f"s = {s}: checkpointed ({time.time() - t0:.1f}s)")
    return ckpt


def validate(ckpt: dict) -> tuple[bool, list[str]]:
    errs = []
    pts = ckpt.get("points", [])
    if len(pts) != len(S_POINTS):
        errs.append(f"expected {len(S_POINTS)} s points, found {len(pts)}")
    for p in pts:
        if len(p["poly"]) != len(N_LIST):
            errs.append(f"s={p['s']}: expected {len(N_LIST)} N entries")
        poly384 = next((e for e in p["poly"] if e["N"] == 384), None)
        if poly384 is None:
            errs.append(f"s={p['s']}: missing N=384 entry")
            continue
        d = abs(poly384["margin"] - p["nystrom"]["margin"])
        if d > GATE_TOL:
            errs.append(f"s={p['s']}: |m_poly-m_nystrom| = {d:.4f} > {GATE_TOL}")
    return (not errs), errs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", action="store_true",
                    help="compute (if needed) and validate the output JSON")
    args = ap.parse_args()

    ckpt = compute()
    ok, errs = validate(ckpt)

    print(f"\nMargin table (poly basis, m(s) = min|1-lambda|):")
    print(f"{'s':>20s} " + " ".join(f"N={n:<6d}" for n in N_LIST)
          + "  nyst384  nyst512")
    for p in sorted(ckpt["points"], key=lambda q: (q["re"], q["im"])):
        row = " ".join(f"{e['margin']:<9.6f}" for e in p["poly"])
        print(f"{p['s']:>20s} {row}  {p['nystrom']['margin']:.6f}  "
              f"{p['nystrom_secondary']['margin']:.6f}")

    if args.gate:
        if ok:
            print(f"\nGATE PASS: 12/12 entries, poly/nystrom agreement "
                  f"<= {GATE_TOL} at N=384 for all s points")
        else:
            print("\nGATE FAIL (reported verbatim per honesty rule):")
            for e in errs:
                print(f"  - {e}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
