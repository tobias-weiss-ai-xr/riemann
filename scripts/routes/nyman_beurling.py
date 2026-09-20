#!/usr/bin/env python
"""RT-NB -- Nyman-Beurling density test (Baez-Duarte f_a functions).

Section S3 of research/ROUTES_FLEET_PLAN.md.

Interpretation note (honesty): the plan's literal formula f_a(x) = {ax} - a*floor(x)
degenerates on (0,1) to f_a(x) = a*x (floor(x)=0 a.e., {ax}=ax), which gives a
rank-1 Gram matrix and a vacuous test. The family intended by the task title --
the Baez-Duarte / Nyman-Beurling generators -- is

    f_a(x) = {a/x} - a*{1/x}  =  a*floor(1/x) - floor(a/x),   0 < a <= 1,

piecewise constant, with exactly the kind of jump discontinuities the plan
describes (at x = 1/k and x = a/k; in the variable u = 1/x used below these
sit at u = k and u = k/a). Nyman-Beurling: span{f_a : 0 < a < 1} dense in
L^2(0,1) iff RH; Baez-Duarte (2003) tied the residual decay rate to RH.

Method (exact piecewise integration; replaces the plan's suggested 4096-node
quadrature, whose O(#jumps * h) error is ~0.1 per Gram entry at n=128 -- the
~10^3 jump discontinuities would swamp the signal): substitute u = 1/x. Then
f_a(1/u) = a*floor(u) - floor(a*u) is piecewise constant with breakpoints
u in Z and u = m/a, so

    <f_a, f_b> = int_1^U f_a(1/u) f_b(1/u) du/u^2    (exact piece sums:
                                                      v_p * (1/u_p - 1/u_{p+1}))
               + mu/U + O(L/U^2),

where mu is the exact mean of the periodic integrand over one period
L = lcm(den a, den b) (the integrand is L-periodic because a*L and b*L are
integers). Absolute error ~1e-6, five orders below the gate threshold.

Residual: eps_n = min_c ||f_{1/2} - sum_k c_k f_{a_k}||^2 with a_k = k/(n+1),
solved via the normal equations G c = b (G = Gram matrix of the grid, b_i =
<f_{a_i}, f_{1/2}>), giving eps_n = <f,f> - b^T c. Density iff eps_n -> 0.

Output: data/routes/rt_nyman_beurling.json  (checkpointed after every n)
Gate:   python scripts/routes/nyman_beurling.py --gate
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_nyman_beurling.json"
U = 8192.0  # u = 1/x integration cutoff; tail error ~ L/U^2 <= 1e-5
TARGET = Fraction(1, 2)
GRIDS = (16, 32, 64, 128)
GATE_EPS_128_MAX = 0.1


def f_u(a: float, u: np.ndarray) -> np.ndarray:
    """f_a evaluated at x = 1/u  (f_a(x) = a*floor(1/x) - floor(a/x))."""
    return a * np.floor(u) - np.floor(a * u)


def _pieces(a: float, b: float | None, lo: float, hi: float):
    """Sorted breakpoints of f_a(1/u) [and f_b(1/u)] in [lo, hi], and midpoints."""
    parts = [np.arange(math.floor(lo), math.ceil(hi) + 1, dtype=float)]
    for s in (a, b):
        if s is None:
            continue
        parts.append(np.arange(math.floor(s * lo), math.ceil(s * hi) + 1, dtype=float) / s)
    u = np.unique(np.clip(np.concatenate(parts), lo, hi))
    return u, 0.5 * (u[1:] + u[:-1])


def _sums(a: float, b: float | None, lo: float, hi: float) -> tuple[float, float]:
    """(int f_a f_b du/u^2, int f_a f_b du) over [lo, hi]; exact for the
    piecewise-constant integrand (values taken at piece midpoints)."""
    u, mids = _pieces(a, b, lo, hi)
    v = f_u(a, mids)
    if b is not None:
        v = v * f_u(b, mids)
    return float(np.dot(v, 1.0 / u[:-1] - 1.0 / u[1:])), float(np.dot(v, np.diff(u)))


def gram(fa: Fraction, fb: Fraction) -> float:
    """<f_a, f_b>_{L^2(0,1)}; exact up to the O(L/U^2) tail estimate."""
    a, b = float(fa), float(fb)
    body, _ = _sums(a, b, 1.0, U)
    L = float(math.lcm(fa.denominator, fb.denominator))
    _, period = _sums(a, b, U, U + L)
    return body + (period / L) / U


def int_f(fa: Fraction) -> float:
    """int_0^1 f_a(x) dx; exact value is -a*log(a) (Mellin transform at s=1)."""
    a = float(fa)
    body, _ = _sums(a, None, 1.0, U)
    L = float(fa.denominator)
    _, period = _sums(a, None, U, U + L)
    return body + (period / L) / U


def gram_xspace(fa: Fraction, fb: Fraction, delta: float = 1e-5) -> float:
    """Independent x-space piecewise integrator (self-test cross-check).

    f_a is piecewise constant between its breakpoints {1/m} and {a/m}; the
    integral over (0, delta) is dropped (bounded by delta since |f_a| <= 1).
    """
    a, b = float(fa), float(fb)
    n = int(round(1.0 / delta))
    parts = [1.0 / np.arange(1, n + 1, dtype=float)]
    for s in (a, b):
        parts.append(s / np.arange(1, int(s / delta) + 1, dtype=float))
    x = np.unique(np.concatenate(parts))
    mids = 0.5 * (x[1:] + x[:-1])
    v = f_u(a, 1.0 / mids) * f_u(b, 1.0 / mids)
    return float(np.dot(v, np.diff(x)))


def selftest() -> dict:
    """Exact known values + independent cross-check of the Gram integrator."""
    checks: dict[str, dict] = {}
    v = gram(Fraction(1, 1), Fraction(1, 1))
    checks["f1_is_zero"] = {"got": v, "expect": 0.0, "ok": abs(v) < 1e-9}
    v = gram(Fraction(1, 2), Fraction(1, 2))
    e = math.log(2.0) / 4.0  # f_{1/2} = 1/2 * chi_{odd k}, total length ln 2
    checks["norm2_f12"] = {"got": v, "expect": e, "ok": abs(v - e) < 1e-6}
    for r in (Fraction(1, 3), Fraction(5, 7)):
        got, exp = int_f(r), -float(r) * math.log(float(r))
        checks[f"int_f_{r.numerator}over{r.denominator}"] = {
            "got": got, "expect": exp, "ok": abs(got - exp) < 1e-6,
        }
    u_val = gram(Fraction(1, 2), Fraction(1, 3))
    x_val = gram_xspace(Fraction(1, 2), Fraction(1, 3))
    checks["u_vs_x_space"] = {
        "u_space": u_val, "x_space": x_val, "ok": abs(u_val - x_val) < 3e-5,
    }
    return {"ok": all(c["ok"] for c in checks.values()), "checks": checks}


def compute(n: int, log) -> dict:
    """Gram matrix, spectrum, and residual eps_n for grid a_k = k/(n+1)."""
    t0 = time.time()
    c = n + 1
    grid = [Fraction(k, c) for k in range(1, n + 1)]
    G = np.empty((n, n))
    for i, ai in enumerate(grid):
        for j in range(i, n):
            G[i, j] = G[j, i] = gram(ai, grid[j])
    b = np.array([gram(ai, TARGET) for ai in grid])
    gtt = gram(TARGET, TARGET)

    w, V = np.linalg.eigh(G)
    lam_min, lam_max = float(w[0]), float(w[-1])
    cond = lam_max / lam_min if lam_min > 0.0 else None
    if lam_min <= 0.0:
        log(f"!! n={n}: min eigenvalue of G is {lam_min:.3e} <= 0 (recorded verbatim)")
    tol = 1e-12 * max(lam_max, 1.0)
    keep = w > tol
    coef = V[:, keep] @ ((V[:, keep].T @ b) / w[keep])
    eps = float(gtt - float(b @ coef))
    if eps < 0.0:
        log(f"!! n={n}: eps_n = {eps:.3e} is negative (squared norm!) -- recorded verbatim")

    entry = {
        "n": n,
        "complete": True,
        "a_grid": "k/(n+1), k=1..n",
        "target": "f_{1/2}",
        "min_eigenvalue": lam_min,
        "max_eigenvalue": lam_max,
        "condition_number": cond,
        "pinv_rank": int(keep.sum()),
        "pinv_tol": tol,
        "eps_n": eps,
        "target_norm2": gtt,
        "eps_over_target_norm2": eps / gtt,
        "seconds": round(time.time() - t0, 2),
    }
    cond_s = f"{cond:.3e}" if cond is not None else "inf"
    log(
        f"n={n}: min_eig={lam_min:.3e} cond={cond_s} eps_n={eps:.6f} "
        f"({entry['eps_over_target_norm2']:.3%} of ||f_1/2||^2) [{entry['seconds']}s]"
    )
    return entry


def run(log) -> dict:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if OUT_PATH.exists():
        try:
            data = json.loads(OUT_PATH.read_text())
        except json.JSONDecodeError:
            log("!! existing JSON corrupt; recomputing from scratch")
            data = {}
    results = data.get("results", {})

    data["task"] = "RT-NB"
    data["title"] = "Nyman-Beurling density test (Baez-Duarte f_a functions)"
    data["method"] = {
        "f_a": "f_a(x) = {a/x} - a*{1/x} = a*floor(1/x) - floor(a/x), a in (0,1]",
        "interpretation_note": (
            "plan's literal formula {ax} - a*floor(x) degenerates to a*x on (0,1); "
            "classical Baez-Duarte family used instead (see module docstring)"
        ),
        "gram": (
            "exact piecewise-constant integration in u = 1/x on [1, U=8192] "
            "+ exact period-mean tail mu/U (absolute error ~1e-6)"
        ),
        "residual": (
            "eps_n = ||f_{1/2} - proj||^2 via normal equations G c = b, "
            "eigh pseudo-inverse (tol 1e-12 * lam_max)"
        ),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
    }
    st = selftest()
    data["selftest"] = st
    if not st["ok"]:
        log("!! SELFTEST FAILED: " + json.dumps(st))

    for n in GRIDS:
        if str(n) in results and results[str(n)].get("complete"):
            log(f"n={n}: cached, skipping")
            continue
        results[str(n)] = compute(n, log)
        data["results"] = results
        OUT_PATH.write_text(json.dumps(data, indent=2))  # checkpoint
    data["results"] = results

    eps = [results[str(n)]["eps_n"] for n in GRIDS]
    rate: dict = {"eps_by_n": {str(n): results[str(n)]["eps_n"] for n in GRIDS}}
    if all(e > 0 for e in eps):
        beta = float(np.polyfit(np.log(np.array(GRIDS, dtype=float)), np.log(eps), 1)[0])
        rate["power_law_exponent_beta"] = beta
        rate["successive_ratios"] = {
            f"eps_{a}/eps_{b}": results[str(a)]["eps_n"] / results[str(b)]["eps_n"]
            for a, b in zip(GRIDS[:-1], GRIDS[1:])
        }
        rate["note"] = (
            f"eps_n ~ A * n^beta with fitted slope beta = {beta:.3f} (negative = decay); "
            "density (hence RH) iff eps_n -> 0; Baez-Duarte: faster-than-power "
            "decay iff RH -- empirical rate is the goal"
        )
    else:
        rate["note"] = "non-positive eps encountered; power-law fit skipped (recorded verbatim)"
    data["rate"] = rate
    OUT_PATH.write_text(json.dumps(data, indent=2))
    return data


def gate(log) -> int:
    data = run(log)
    results = data.get("results", {})
    ok_json = OUT_PATH.exists()
    ok_entries = all(str(n) in results and results[str(n)].get("complete") for n in GRIDS)
    e128 = results.get("128", {}).get("eps_n")
    ok_eps = e128 is not None and 0.0 <= e128 < GATE_EPS_128_MAX
    ok_selftest = bool(data.get("selftest", {}).get("ok"))

    print()
    print("=" * 76)
    print("RT-NB results (grid a_k = k/(n+1), target f_{1/2}):")
    for n in GRIDS:
        e = results.get(str(n), {})
        cond = e.get("condition_number")
        cond_s = f"{cond:.3e}" if cond is not None else "inf"
        print(
            f"  n={n:4d}  min_eig={e.get('min_eigenvalue', float('nan')):.3e}"
            f"  cond={cond_s}  eps_n={e.get('eps_n', float('nan')):.6f}"
        )
    beta = data.get("rate", {}).get("power_law_exponent_beta")
    if beta is not None:
        print(f"  rate: log-log slope beta = {beta:.3f}  (eps_n ~ A * n^{beta:.3f})")
    print("-" * 76)
    print(
        f"GATE: json_exists={ok_json}  all_4_entries={ok_entries}  "
        f"selftest={ok_selftest}  eps_128={e128} < {GATE_EPS_128_MAX}: {ok_eps}"
    )
    passed = ok_json and ok_entries and ok_eps and ok_selftest
    print("GATE:", "PASS" if passed else "FAIL")
    print("=" * 76)
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="RT-NB: Nyman-Beurling density test")
    ap.add_argument("--gate", action="store_true", help="compute + validate; exit code 0 on success")
    ap.add_argument("--selftest", action="store_true", help="run self-tests only")
    args = ap.parse_args()
    if args.selftest:
        st = selftest()
        print(json.dumps(st, indent=2))
        return 0 if st["ok"] else 1
    if args.gate:
        return gate(print)
    run(print)
    return 0


if __name__ == "__main__":
    sys.exit(main())
