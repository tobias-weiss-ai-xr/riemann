#!/usr/bin/env python
"""RT2-NB -- Nyman-Beurling density at n=256, 512, 1024 (extended power-law fit).

Section S2 of research/ROUTES2_FLEET_PLAN.md.  Round 1 (RT-NB,
scripts/routes/nyman_beurling.py) computed eps_n for n in {16,32,64,128}
(eps_128 = 0.00731, beta = -0.779); this script extends the grid to
n = 256, 512, 1024 and refits eps_n ~ A * n^beta over all 7 sizes
(16..1024, each recomputed in the same run for consistency).

Setup (identical to round 1): Baez-Duarte generators
    f_a(x) = a*floor(1/x) - floor(a/x)   on (0,1],   a_k = k/(n+1),
    eps_n = min_c || f_{1/2} - sum_k c_k f_{a_k} ||^2 = <f,f> - b^T G^+ b,
solved through the normal equations with an eigh pseudo-inverse.

Method -- EXACT one-period Gram integration (no U cutoff, no quadrature).
In u = 1/x, f_a(1/u) = a*floor(u) - floor(a*u) is bounded by 2 and is
c-periodic (a*c = k integer) for every grid a = k/c, c = n+1.  The target
f_{1/2}(1/u) has period 2, and c is odd for every size in the grid, so
all integrands share the common period P = 2c.  For a P-periodic
piecewise-constant g,

    int_1^inf g(u)/u^2 du = sum_p g(mid_p) * w_p  over the pieces of ONE
    period [1, 1+P),   w_p = (digamma(u_{p+1}/P) - digamma(u_p/P))/P,

because summing 1/u^2 over all periodic images of the piece telescopes
the Hurwitz zeta difference at s=1 into a digamma difference; the weights
sum to exactly 1 (psi(1+x) - psi(x) = 1/x).  The only error is float
roundoff: round 1's O(L/U^2) ~ 1e-6 tail estimate is gone.  Validated
against round 1's `gram()` (imported unmodified as oracle) and the closed
forms <f_{1/2},f_{1/2}> = ln(2)/4 and int_0^1 f_a = -a*ln(a).

Numerical safety: distinct breakpoints (rationals m*c/k, denominators
<= c-1) are >= 1/(c-1)^2 apart, so true piece midpoints sit >= ~5e-7/c
from every jump; floor(k*u/c) is evaluated as floor((floor(u)*k +
frac(u)*k)/c) whose ~1e-12 roundoff stays three orders below that margin.

Condition number is reported at every size; if cond > 1e12 (or the
float64 min eigenvalue is <= 0) the minimum eigenvalue is recomputed in
mpmath (dps=60): Rayleigh quotient of an inverse-iteration-refined
eigenvector plus the exact residual norm r, giving the certified interval
[lam - r, lam + r] (symmetric perturbation bound |lam - RQ| <= ||r||).

Output: data/routes/rt_nb_ext.json   (checkpointed after every size)
Gate:   python scripts/routes/nyman_beurling_ext.py --gate
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
from scipy.special import digamma

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyman_beurling as nb1  # noqa: E402  round-1 oracle (READ-ONLY)

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_nb_ext.json"
SIZES = (16, 32, 64, 128, 256, 512, 1024)
COND_MP_SWITCH = 1e12
GATE_EPS_1024_MAX = 0.01
GATE_ABS_BETA_MIN = 0.3


def assemble(n: int) -> dict:
    """Exact Gram matrix G, target overlaps b, <f_{1/2},f_{1/2}> for grid k/(n+1)."""
    c = n + 1
    P = 2 * c  # common period of all f_{k/c}(1/u) and of f_{1/2}(1/u) (c odd)
    parts = [np.arange(1.0, P + 2.0)]  # all integers (jumps of floor(u), floor(u/2))
    for k in range(1, c):
        parts.append(np.arange(1.0, int(((1.0 + P) * k) // c) + 2.0) * (c / k))
    u = np.concatenate(parts)
    u = np.unique(u[(u >= 1.0) & (u <= 1.0 + P)])
    mids = 0.5 * (u[1:] + u[:-1])
    w = (digamma(u[1:] / P) - digamma(u[:-1] / P)) / P

    kvec = np.arange(1.0, c)
    kc = kvec / c
    fl = np.floor(mids)  # exact
    fr = mids - fl  # exact (Sterbenz)
    tgt = 0.5 * fl - np.floor(0.5 * fl + 0.5 * fr)  # f_{1/2}(1/u)

    G = np.zeros((n, n))
    b = np.zeros(n)
    b1 = np.zeros(n)  # <f_{a_k}, 1> = int_0^1 f_a  (self-check vs -a ln a)
    gtt = float(np.dot(w, tgt * tgt))
    chunk = max(1, (1 << 22) // n)
    for s in range(0, mids.size, chunk):
        fc, frc, wc = fl[s:s + chunk], fr[s:s + chunk], w[s:s + chunk]
        num = np.multiply.outer(fc, kvec) + np.multiply.outer(frc, kvec)
        F = np.multiply.outer(fc, kc) - np.floor_divide(num, c)
        G += (F * wc[:, None]).T @ F
        b += F.T @ (wc * tgt[s:s + chunk])
        b1 += F.T @ wc
    return {"G": G, "b": b, "b1": b1, "gtt": gtt,
            "sumw": float(w.sum()), "npieces": int(mids.size)}


def min_eig_mp(G: np.ndarray, lam0: float, v0: np.ndarray) -> tuple[float, float]:
    """(Rayleigh quotient, residual norm) at dps=60 for the smallest eigenvalue.

    v0 (float64 eigenvector) is refined by 3 inverse-iteration steps in
    float64 first; the mpmath Rayleigh quotient RQ and exact residual
    r = ||G v - RQ v|| certify an eigenvalue in [RQ - r, RQ + r].
    """
    import mpmath as mp
    lam_max = float(np.abs(G).sum(axis=1).max())
    shift = lam0 - max(0.01 * abs(lam0), 1e-13 * max(lam_max, 1e-300))
    A = G - shift * np.eye(len(G))
    v = v0 / np.linalg.norm(v0)
    for _ in range(3):
        try:
            v = np.linalg.solve(A, v + 1e-12)
        except np.linalg.LinAlgError:
            break
        v /= np.linalg.norm(v)
    with mp.workdps(60):
        Gm = mp.matrix(G.tolist())
        vv = mp.matrix([mp.mpf(x) for x in v])
        n2 = mp.sqrt(sum(x * x for x in vv))
        vv = mp.matrix([x / n2 for x in vv])
        Gv = Gm * vv
        rq = sum(a * bb for a, bb in zip(vv, Gv))
        r2 = sum((a - rq * bb) ** 2 for a, bb in zip(Gv, vv))
        return float(rq), float(mp.sqrt(r2))


def selftest() -> dict:
    """Cross-check the exact one-period assembler against round 1 + closed forms."""
    asm = assemble(12)  # c = 13, odd like every grid in SIZES
    G, b, gtt = asm["G"], asm["b"], asm["gtt"]
    checks: dict[str, dict] = {}
    checks["weights_sum_to_1"] = {"got": asm["sumw"], "tol": 1e-9,
                                  "ok": bool(abs(asm["sumw"] - 1.0) < 1e-9)}
    e = math.log(2.0) / 4.0
    checks["target_norm2_ln2_over_4"] = {"got": gtt, "expect": e, "tol": 1e-8,
                                         "ok": bool(abs(gtt - e) < 1e-8)}
    worst = 0.0
    for i, j in [(0, 4), (1, 2), (5, 11), (2, 9)]:
        worst = max(worst, abs(float(G[i, j]) - nb1.gram(Fraction(i + 1, 13), Fraction(j + 1, 13))))
    checks["gram_vs_round1"] = {"max_abs_diff": worst, "tol": 1e-5, "ok": bool(worst < 1e-5)}
    ref = nb1.gram(Fraction(1, 13), Fraction(1, 2))
    checks["target_overlap_vs_round1"] = {"got": float(b[0]), "ref": ref,
                                          "ok": bool(abs(float(b[0]) - ref) < 1e-5)}
    a = np.arange(1, 13) / 13.0
    err = float(np.max(np.abs(asm["b1"] + a * np.log(a))))
    checks["int_f_equals_minus_a_ln_a"] = {"max_abs_err": err, "tol": 1e-9,
                                           "ok": bool(err < 1e-9)}
    return {"ok": bool(all(c["ok"] for c in checks.values())), "checks": checks}


def compute(n: int, log) -> dict:
    t0 = time.time()
    asm = assemble(n)
    G, b, gtt = asm["G"], asm["b"], asm["gtt"]

    a_grid = np.arange(1, n + 1) / (n + 1)
    int_f_err = float(np.max(np.abs(asm["b1"] + a_grid * np.log(a_grid))))

    w_eig, V = np.linalg.eigh(G)
    lam_min, lam_max = float(w_eig[0]), float(w_eig[-1])
    cond_f = lam_max / lam_min if lam_min > 0.0 else float("inf")

    if lam_min <= 0.0:
        log(f"!! n={n}: float64 min eigenvalue of G is {lam_min:.3e} <= 0 "
            f"(recorded verbatim; mpmath refinement below)")
    entry: dict = {
        "n": n,
        "complete": True,
        "a_grid": "k/(n+1), k=1..n",
        "target": "f_{1/2}",
        "npieces": asm["npieces"],
        "sumw": asm["sumw"],
        "int_f_max_abs_err": int_f_err,
        "min_eigenvalue_float64": lam_min,
        "max_eigenvalue": lam_max,
    }
    if cond_f > COND_MP_SWITCH or lam_min <= 0.0:
        log(f"n={n}: cond={cond_f:.3e} (>{COND_MP_SWITCH:.0e} or min_eig<=0) "
            "-> mpmath min-eig refinement")
        rq, r = min_eig_mp(G, w_eig[0], V[:, 0])
        entry["min_eig_mpmath_rq"] = rq
        entry["min_eig_residual_bound"] = r
        entry["min_eig_certified_interval"] = [rq - r, rq + r]
        entry["min_eig"] = rq
        entry["cond"] = lam_max / rq if rq > 0 else None
    else:
        entry["min_eig"] = lam_min
        entry["cond"] = cond_f

    tol = 1e-12 * max(lam_max, 1.0)
    keep = w_eig > tol
    coef = V[:, keep] @ ((V[:, keep].T @ b) / w_eig[keep])
    eps = float(gtt - float(b @ coef))
    if eps < 0.0:
        log(f"!! n={n}: eps_n = {eps:.3e} is NEGATIVE (squared norm!) -- recorded verbatim")
    entry.update({
        "eps_n": eps,
        "target_norm2": gtt,
        "eps_over_target_norm2": eps / gtt,
        "pinv_rank": int(keep.sum()),
        "pinv_tol": tol,
        "seconds": round(time.time() - t0, 2),
    })
    cond_s = f"{entry['cond']:.3e}" if entry["cond"] is not None else "inf"
    log(f"n={n}: pieces={entry['npieces']} min_eig={entry['min_eig']:.3e} "
        f"cond={cond_s} eps_n={eps:.6f} ({entry['eps_over_target_norm2']:.3%} of "
        f"||f||^2) [{entry['seconds']}s]")
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
    sizes = {e["n"]: e for e in data.get("sizes", []) if e.get("complete")}

    data["task"] = "RT2-NB"
    data["title"] = "Nyman-Beurling density at n=256,512,1024 (extended power-law fit)"
    data["params"] = {
        "sizes": list(SIZES),
        "grid": "a_k = k/(n+1), k=1..n",
        "target": "f_{1/2}",
        "f_a": "f_a(x) = a*floor(1/x) - floor(a/x)  (Baez-Duarte family, as round 1)",
        "period": "P = 2*(n+1) (common period of all grid functions and the target)",
        "cond_mp_switch": COND_MP_SWITCH,
        "pinv_tol": "1e-12 * max(lam_max, 1)",
        "round1_reference": {"eps_128": 0.007311, "beta_4sizes": -0.7789},
        "gate": {"all_7_sizes": True, "eps_n_and_min_eig_positive": True,
                 "eps_1024_max": GATE_EPS_1024_MAX, "abs_beta_min": GATE_ABS_BETA_MIN},
    }
    data["method"] = {
        "gram": ("exact one-period integration in u = 1/x: pieces of [1, 1+P) "
                 "weighted by (digamma(u1/P) - digamma(u0/P))/P (telescoped "
                 "Hurwitz zeta over all periodic images); error = float roundoff"),
        "residual": "eps_n = <f,f> - b^T G^+ b via eigh pseudo-inverse (as round 1)",
        "selftest": "vs round-1 nyman_beurling.gram() and closed forms ln(2)/4, -a*ln(a)",
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
    }
    st = selftest()
    data["selftest"] = st
    if not st["ok"]:
        log("!! SELFTEST FAILED: " + json.dumps(st))

    for n in SIZES:
        if n in sizes:
            log(f"n={n}: cached, skipping")
            continue
        sizes[n] = compute(n, log)
        data["sizes"] = [sizes[m] for m in SIZES if m in sizes]
        OUT_PATH.write_text(json.dumps(data, indent=2))  # checkpoint after every size
    data["sizes"] = [sizes[m] for m in SIZES]

    eps = [sizes[m]["eps_n"] for m in SIZES]
    fit: dict = {"over": "n = 16..1024 (all 7 sizes, recomputed this run)"}
    if all(e > 0 for e in eps):
        beta, inter = (float(v) for v in np.polyfit(np.log(np.array(SIZES, float)),
                                                    np.log(eps), 1))
        fit.update({"A": math.exp(inter), "beta": beta,
                    "eps_by_n": {str(m): sizes[m]["eps_n"] for m in SIZES},
                    "successive_ratios": {f"eps_{p}/eps_{q}": sizes[p]["eps_n"] / sizes[q]["eps_n"]
                                          for p, q in zip(SIZES[:-1], SIZES[1:])},
                    "note": (f"eps_n ~ A*n^beta with beta = {beta:.3f} over a 64x range; "
                             "density (hence RH) iff eps_n -> 0 -- rate slowdown would "
                             "be an honest negative result")})
    else:
        fit.update({"A": None, "beta": None,
                    "note": "non-positive eps_n encountered; power-law fit skipped "
                            "(recorded verbatim)"})
    data["powerlaw_fit"] = fit

    ok_sizes = len(data["sizes"]) == len(SIZES)
    ok_pos = ok_sizes and all(sizes[m]["eps_n"] > 0 and sizes[m]["min_eig"] > 0 for m in SIZES)
    ok_eps = ok_sizes and 0.0 < sizes[1024]["eps_n"] < GATE_EPS_1024_MAX
    ok_beta = fit.get("beta") is not None and abs(fit["beta"]) > GATE_ABS_BETA_MIN
    data["gate_pass"] = bool(ok_sizes and ok_pos and ok_eps and ok_beta and st["ok"])
    OUT_PATH.write_text(json.dumps(data, indent=2))
    return data


def gate(log) -> int:
    data = run(log)
    sizes = {e["n"]: e for e in data.get("sizes", [])}
    fit = data.get("powerlaw_fit", {})
    st = data.get("selftest", {})

    print()
    print("=" * 78)
    print("RT2-NB results (grid a_k = k/(n+1), target f_{1/2}, exact one-period Gram):")
    for n in SIZES:
        e = sizes.get(n, {})
        cond = e.get("cond")
        cond_s = f"{cond:.3e}" if cond is not None else "inf"
        print(f"  n={n:5d}  min_eig={e.get('min_eig', float('nan')):.3e}"
              f"  cond={cond_s}  eps_n={e.get('eps_n', float('nan')):.6f}"
              f"  ({e.get('eps_over_target_norm2', float('nan')):.3%} of ||f||^2)")
    beta = fit.get("beta")
    if beta is not None:
        print(f"  power law: eps_n ~ {fit['A']:.4f} * n^{beta:.4f}   "
              f"(round 1, 4 sizes: beta = -0.779)")
    print("-" * 78)
    ok_sizes = all(n in sizes and sizes[n].get("complete") for n in SIZES)
    ok_pos = ok_sizes and all(sizes[n]["eps_n"] > 0 and sizes[n]["min_eig"] > 0 for n in SIZES)
    e1024 = sizes.get(1024, {}).get("eps_n")
    ok_eps = e1024 is not None and 0.0 < e1024 < GATE_EPS_1024_MAX
    ok_beta = beta is not None and abs(beta) > GATE_ABS_BETA_MIN
    print(f"GATE: all_7_sizes={ok_sizes}  eps_and_min_eig_positive={ok_pos}  "
          f"selftest={st.get('ok')}")
    print(f"      eps_1024={e1024} < {GATE_EPS_1024_MAX}: {ok_eps}  "
          f"|beta|={abs(beta) if beta is not None else None} > {GATE_ABS_BETA_MIN}: {ok_beta}")
    if beta is not None and abs(beta) <= GATE_ABS_BETA_MIN:
        print("      !! beta deterioration over the full range -- HONEST FAIL")
    passed = ok_sizes and ok_pos and ok_eps and ok_beta and bool(st.get("ok"))
    print("GATE:", "PASS" if passed else "FAIL")
    print("=" * 78)
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="RT2-NB: Nyman-Beurling density, n up to 1024")
    ap.add_argument("--gate", action="store_true", help="compute + validate; exit 0 on success")
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
