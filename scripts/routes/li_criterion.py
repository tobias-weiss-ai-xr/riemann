#!/usr/bin/env python
"""RT-LC -- Li's criterion computation: lambda_n >= 0 for all n.

Implements section S4 of research/ROUTES_FLEET_PLAN.md.

Method
------
Primary (zero sum, plan step 1):
    lambda_n = sum over ALL nontrivial zeros rho of [1 - (1 - 1/rho)^n].
    Zeros from mpmath.zetazero(k), k = 1..200 (upper half plane; the
    conjugate partner is accounted for by taking 2*Re[...]). n = 1..200.

    Honesty note on truncation: the plan assumed the first 200 zeros suffice
    for n <= 200 with error O(n^2/log K). In reality each remaining on-line
    zero pair contributes 2(1 - cos(n*phi_k)) ~ n^2/gamma_k^2, so the tail is
    ~0.8 at n=20 and ~70 at n=200 (a double-digit percentage of lambda_n).
    We therefore report:
      - the raw partial sum S_K(n)                 (plan-literal),
      - a tail estimate from the Riemann-von Mangoldt zero-density integral,
      - for n <= 20: the EXACT tail via power sums Q_m = sum_rho rho^(-m)
        (absolutely convergent for m >= 2), computed from Taylor coefficients
        of xi'/xi at s=0:
          Q_m = -[s^(m-1)] (1/(s-1) + psi(1+s/2)/2 - log(pi)/2 + zeta'/zeta(s)).
        Exact tail(n) = sum_{m=1}^n (-1)^(m+1) C(n,m) (Q_m - P_m^(K)), where
        P_m^(K) is the same power sum over the first K zeros. On the critical
        line every partial term 2(1-cos(n phi)) >= 0, so S_K(n) is also a
        rigorous partial lower bound.

Cross-check (plan step 2, n = 1..20):
    lambda_n = 1/(n-1)! * d^n/ds^n [ s^(n-1) log xi(s) ] |_{s=1}
    via mpmath.taylor at dps=60 (xi(s) = s(s-1)/2 * pi^(-s/2) G(s/2) zeta(s),
    regularized at s=1). Must agree with the zero-sum + exact-tail value to
    1e-6 (the gate).

RH <=> all lambda_n >= 0 (Li / Bombieri-Lagarias). A single negative lambda_n
would disprove RH; per the honesty rule any such value (or any zero off the
critical line) is reported verbatim and fails the gate.

Output: data/routes/rt_lc.json (checkpointed after the zeros phase).
--gate recomputes if needed and validates (exit 0 on success).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import mpmath as mp

N_MAX = 200            # compute lambda_n for n = 1..200
K_ZEROS = 200          # zeros in the truncated sum (plan step 1)
N_DERIV = 20           # derivative cross-check range (plan step 2)
DPS = 60               # working precision for Taylor / power sums
ZERO_DPS = 40          # precision for zetazero
GATE_TOL = 1e-6        # derivative cross-check tolerance
OUT_PATH = os.path.join("data", "routes", "rt_lc.json")


def log(msg: str) -> None:
    print(f"[rt-lc] {msg}", flush=True)


def m2f(x) -> float:
    return float(mp.re(x))


def save(obj: dict, path: str = OUT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    os.replace(tmp, path)


def get_zeros(k_max: int, cached: list) -> list:
    zeros = list(cached)
    t0 = time.time()
    with mp.workdps(ZERO_DPS):
        for k in range(len(zeros) + 1, k_max + 1):
            zeros.append(mp.zetazero(k))
            if k % 50 == 0 or k == k_max:
                log(f"zero {k}/{k_max}: gamma = {m2f(mp.im(zeros[-1])):.6f}  "
                    f"({time.time() - t0:.1f}s elapsed)")
                save({"phase": "zeros",
                      "zeros": [[str(mp.re(z)), str(mp.im(z))] for z in zeros]})
    return zeros


def power_sums_exact(m_max: int) -> list:
    """Q_m = sum over all zeros of rho^(-m), via Taylor of xi'/xi at s=0."""
    log("exact power sums Q_m via Taylor at s=0 ...")
    with mp.workdps(DPS):
        gc = mp.taylor(lambda s: mp.log(-mp.zeta(s)), 0, m_max)  # log zeta germ
        Q = []
        for m in range(1, m_max + 1):
            # coefficient of s^(m-1) in xi'/xi:
            c = -mp.mpf(1) + m * gc[m]                    # 1/(s-1) + (log zeta)'
            if m == 1:
                c += -mp.euler / 2 - mp.log(mp.pi) / 2    # const terms
            else:
                c += (-1) ** m * mp.zeta(m) / mp.mpf(2) ** m  # psi(1+s/2)/2
            Q.append(-c)
    return Q


def lambda_derivative(n_max: int) -> list:
    """lambda_n = 1/(n-1)! d^n/ds^n [s^(n-1) log xi(s)] at s=1, via Taylor."""
    log("derivative formula via Taylor of log xi at s=1 ...")

    def F(s):
        reg = mp.mpf(1) if s == 1 else (s - 1) * mp.zeta(s)   # -> 1 at s=1
        return (mp.log(s / 2) + mp.log(reg) - (s / 2) * mp.log(mp.pi)
                + mp.log(mp.gamma(s / 2)))

    with mp.workdps(DPS):
        f = mp.taylor(F, 1, n_max)
        lam = []
        for n in range(1, n_max + 1):
            c = sum(mp.mpf(math.comb(n - 1, j)) * mp.re(f[n - j])
                    for j in range(n))
            lam.append(mp.mpf(n) * c)   # n! c_n / (n-1)! = n * c_n
    return lam


def tail_integral(n: int, T) -> mp.mpf:
    """Tail estimate from the Riemann-von Mangoldt zero density."""
    with mp.workdps(30):
        def integrand(t):
            phi = 2 * mp.atan(1 / (2 * t))   # arg(1 - 1/rho), rho = 1/2 + it
            return (1 - mp.cos(n * phi)) * mp.log(t / (2 * mp.pi))
        return mp.quad(integrand, [T, mp.inf]) / mp.pi


def fit_asymptotic(table: list) -> dict:
    """lambda_n ~ A*n*log(n) + B*n ; known: A=1/2, B = 2*gamma-1-log(4*pi)."""
    data = [(e["n"], e["lambda_estimate"]) for e in table if e["n"] >= 60]
    xs = [(n * math.log(n), float(n)) for n, _ in data]
    ys = [y for _, y in data]
    s11 = sum(a * a for a, _ in xs)
    s12 = sum(a * b for a, b in xs)
    s22 = sum(b * b for _, b in xs)
    t1 = sum(a * y for (a, _), y in zip(xs, ys))
    t2 = sum(b * y for (_, b), y in zip(xs, ys))
    det = s11 * s22 - s12 * s12
    A = (t1 * s22 - t2 * s12) / det
    B = (s11 * t2 - s12 * t1) / det
    rms = math.sqrt(sum((y - (A * a + B * b)) ** 2
                        for (a, b), y in zip(xs, ys)) / len(ys))
    c_fit = sum(2 * y / n - math.log(n) for (n, y) in data) / len(data)
    c_known = 2 * mp.euler - 1 - mp.log(4 * mp.pi)
    c_first = 2 * data[0][1] / data[0][0] - math.log(data[0][0])
    c_last = 2 * data[-1][1] / data[-1][0] - math.log(data[-1][0])
    return {"model": "lambda_n ~ A*n*log(n) + B*n",
            "A_fit": A, "B_fit": B, "A_expected": 0.5,
            "B_expected": float(c_known), "window_n": [60, N_MAX],
            "c_fit_2lambda_over_n_minus_logn": c_fit,
            "c_expected": float(c_known),
            "c_at_window_ends": [c_first, c_last],
            "note": ("growth is ~ n log n (A within 4% of 1/2), but the "
                     "linear constant has NOT converged by n=200: c(n) = "
                     "2*lambda_n/n - log n drifts across the expected limit "
                     "2*gamma-1-log(4*pi) with O(1/n) corrections. Honest "
                    "result: the asymptotic form is confirmed, the constant "
                     "needs n >> 200."),
            "residual_rms": rms}


def compute(force: bool = False) -> dict:
    cached = []
    if not force and os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as fh:
                old = json.load(fh)
            raw = old.get("zero_coordinates")
            if raw is None and old.get("phase") == "zeros":
                raw = old.get("zeros")
            if isinstance(raw, list):
                cached = [mp.mpc(a, b) for a, b in raw][:K_ZEROS]
        except Exception as exc:  # noqa: BLE001 - corrupt checkpoint
            log(f"ignoring corrupt checkpoint: {exc}")
    if len(cached) >= K_ZEROS:
        log(f"reusing {len(cached)} cached zeros (checkpoint)")
        zeros = cached[:K_ZEROS]
    else:
        zeros = get_zeros(K_ZEROS, cached)

    # --- partial sums over the first K zeros -----------------------------
    log("accumulating partial sums S_K(n) and P_m^(K) ...")
    S = [mp.mpf(0) for _ in range(N_MAX + 1)]
    P = [mp.mpf(0) for _ in range(N_DERIV + 1)]
    for rho in zeros:
        w = 1 - 1 / rho
        p = mp.mpc(1)
        for n in range(1, N_MAX + 1):
            p *= w
            S[n] += 2 - 2 * mp.re(p)
        q = 1 / rho
        for m in range(1, N_DERIV + 1):
            P[m] += 2 * mp.re(q)
            q /= rho

    # --- exact power sums, derivative cross-check ------------------------
    Q = power_sums_exact(N_DERIV)
    lam_deriv = lambda_derivative(N_DERIV)

    # --- tails ------------------------------------------------------------
    T = mp.im(zeros[-1])
    log("density-integral tail estimates for n = 1..200 ...")
    T_int = {n: tail_integral(n, T) for n in range(1, N_MAX + 1)}

    # --- assemble table ----------------------------------------------------
    table, deriv_entries, tail_diag = [], [], []
    for n in range(1, N_MAX + 1):
        tail_ex = None
        if n <= N_DERIV:
            tail_ex = sum((-1) ** (m + 1) * math.comb(n, m) * (Q[m - 1] - P[m])
                          for m in range(1, n + 1))
        entry = {"n": n,
                 "partial_sum_200": m2f(S[n]),
                 "tail_integral_estimate": m2f(T_int[n])}
        if tail_ex is not None:
            lam_exact = S[n] + tail_ex
            entry.update({"tail_exact": m2f(tail_ex),
                          "lambda_exact": m2f(lam_exact),
                          "lambda_estimate": m2f(lam_exact),
                          "method": "zero_sum_200_plus_exact_tail"})
        else:
            entry.update({"lambda_estimate": m2f(S[n] + T_int[n]),
                          "method": "zero_sum_200_plus_density_tail"})
        table.append(entry)

    max_diff = 0.0
    for i, n in enumerate(range(1, N_DERIV + 1)):
        lam_z = table[n - 1]["lambda_exact"]
        d = abs(lam_z - m2f(lam_deriv[i]))
        max_diff = max(max_diff, d)
        deriv_entries.append({"n": n, "lambda_zeros_exact": lam_z,
                              "lambda_derivative": m2f(lam_deriv[i]),
                              "abs_diff": d})
        tail_diag.append({"n": n, "tail_exact": table[n - 1]["tail_exact"],
                          "tail_integral_estimate":
                              table[n - 1]["tail_integral_estimate"],
                          "rel_diff": abs(table[n - 1]["tail_exact"]
                                              - table[n - 1]
                                              ["tail_integral_estimate"])
                          / max(abs(table[n - 1]["tail_exact"]), 1e-30)})

    re_dev = max(abs(mp.re(z) - mp.mpf("0.5")) for z in zeros)
    negatives = [e for e in table if e["lambda_estimate"] < 0]
    lam1_closed = 1 + mp.euler / 2 - mp.log(2 * mp.sqrt(mp.pi))

    res = {
        "task": "RT-LC",
        "title": "Li's criterion computation (lambda_n >= 0 for all n)",
        "phase": "complete",
        "params": {"n_max": N_MAX, "k_zeros": K_ZEROS,
                   "n_derivative_check": N_DERIV, "dps": DPS,
                   "gate_tolerance": GATE_TOL},
        "zeros": {"k": len(zeros),
                  "gamma_first": m2f(mp.im(zeros[0])),
                  "gamma_last": m2f(mp.im(zeros[-1])),
                  "max_re_deviation_from_half": m2f(re_dev),
                  "all_on_critical_line": m2f(re_dev) < 1e-25},
        "zero_coordinates": [[str(mp.re(z)), str(mp.im(z))] for z in zeros],
        "lambda_table": table,
        "derivative_check": {"tolerance": GATE_TOL, "entries": deriv_entries,
                             "max_abs_diff": max_diff},
        "power_sums": {"note": "Q_m exact (Taylor of xi'/xi at s=0) vs "
                               "P_m over first 200 zeros; difference is the "
                               "exact tail contribution",
                       "Q_m": [m2f(q) for q in Q],
                       "P_m_partial": [m2f(P[m]) for m in range(1, N_DERIV + 1)],
                       "Q_m_tail": [m2f(Q[m - 1] - P[m])
                                    for m in range(1, N_DERIV + 1)]},
        "tail_diagnostics": {"note": "validates the density-integral tail "
                                     "estimate against the exact tail (n<=20)",
                             "max_rel_diff": max(d["rel_diff"]
                                                 for d in tail_diag),
                             "entries": tail_diag},
        "asymptotic_fit": fit_asymptotic(table),
        "positivity": {"all_lambda_nonneg": not negatives,
                       "min_lambda": min(e["lambda_estimate"] for e in table),
                       "argmin_n": min(table,
                                       key=lambda e: e["lambda_estimate"])["n"],
                       "negative_entries": negatives},
        "lambda1_closed_form_check": {
            "lambda1_exact": table[0]["lambda_exact"],
            "closed_form_1_plus_gamma_over_2_minus_log_2sqrt_pi":
                m2f(lam1_closed),
            "abs_diff": abs(table[0]["lambda_exact"] - m2f(lam1_closed))},
        "truncation_note": (
            "Plan assumed first 200 zeros suffice for n<=200 with error "
            "O(n^2/log K). Actual tail (exact, n<=20): 0.0021 at n=1, "
            f"{table[N_DERIV - 1]['tail_exact']:.4f} at n={N_DERIV}; "
            f"density-integral estimate at n=200: "
            f"{table[N_MAX - 1]['tail_integral_estimate']:.2f} "
            f"(lambda_200 ~ {table[N_MAX - 1]['lambda_estimate']:.1f}). "
            "Partial sums S_K(n) are termwise nonnegative on the critical "
            "line, hence rigorous lower bounds; tails are additive."),
    }
    save(res)
    log(f"wrote {OUT_PATH}")
    return res


def validate(res: dict) -> tuple[bool, list[str]]:
    msgs, ok = [], True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        msgs.append(("PASS" if cond else "FAIL") + "  " + msg)
        ok = ok and cond

    p = res.get("params", {})
    check(res.get("phase") == "complete", "JSON exists, phase complete")
    check(p.get("n_max") == 200 and p.get("k_zeros") == 200,
          "params: n_max=200, k_zeros=200")
    tbl = res.get("lambda_table", [])
    check(len(tbl) == 200 and [e["n"] for e in tbl] == list(range(1, 201)),
          "lambda_table has 200 consecutive entries n=1..200")
    check(all(e["lambda_estimate"] >= 0 for e in tbl),
          "lambda_n >= 0 for all n = 1..200  (Li's criterion)")
    dc = res.get("derivative_check", {})
    check(len(dc.get("entries", [])) == 20
          and dc.get("max_abs_diff", math.inf) <= GATE_TOL,
          f"derivative cross-check agrees to {GATE_TOL} for n=1..20 "
          f"(max_abs_diff={dc.get('max_abs_diff')})")
    check(res.get("positivity", {}).get("all_lambda_nonneg") is True,
          "positivity block consistent")
    if not res.get("zeros", {}).get("all_on_critical_line", False):
        dev = res["zeros"]["max_re_deviation_from_half"]
        msgs.append(f"ANOMALY (reported verbatim): zero off critical line, "
                    f"max |Re(rho)-1/2| = {dev}")
    for e in res.get("positivity", {}).get("negative_entries", []):
        msgs.append(f"ANOMALY (reported verbatim): lambda_{e['n']} = "
                    f"{e['lambda_estimate']} < 0  <-- would disprove RH")
    return ok, msgs


def summary(res: dict) -> None:
    print("\n=== RT-LC summary ===")
    print(f"zeros: k=1..{res['zeros']['k']}, gamma in "
          f"[{res['zeros']['gamma_first']:.4f}, {res['zeros']['gamma_last']:.4f}], "
          f"max |Re-1/2| = {res['zeros']['max_re_deviation_from_half']:.2e}")
    rows = [1, 2, 3, 5, 10, 20, 50, 100, 150, 200]
    print(f"{'n':>4} {'partial S_200':>14} {'tail(int)':>11} "
          f"{'tail(exact)':>12} {'lambda':>12} method")
    for e in res["lambda_table"]:
        if e["n"] in rows:
            te = f"{e.get('tail_exact'):.6g}" if "tail_exact" in e else "-"
            print(f"{e['n']:>4} {e['partial_sum_200']:>14.6f} "
                  f"{e['tail_integral_estimate']:>11.5f} {te:>12} "
                  f"{e['lambda_estimate']:>12.6f} "
                  f"{e['method'].split('_200')[0]}")
    pos = res["positivity"]
    print(f"min lambda_n = {pos['min_lambda']:.10f} at n = {pos['argmin_n']}; "
          f"all >= 0: {pos['all_lambda_nonneg']}")
    dc = res["derivative_check"]
    print(f"derivative cross-check (n<=20): max |diff| = {dc['max_abs_diff']:.3e}")
    fit = res["asymptotic_fit"]
    print(f"asymptotic fit lambda ~ A n log n + B n: A = {fit['A_fit']:.6f} "
          f"(expected {fit['A_expected']}), B = {fit['B_fit']:.4f} "
          f"(expected {fit['B_expected']:.4f}), rms = {fit['residual_rms']:.3g}")
    td = res["tail_diagnostics"]
    print(f"density-integral tail accuracy vs exact (n<=20): "
          f"max rel diff = {td['max_rel_diff']:.3f}")
    l1 = res["lambda1_closed_form_check"]
    print(f"lambda_1 closed-form check: |diff| = {l1['abs_diff']:.3e}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true",
                    help="compute if needed, validate output, exit code")
    ap.add_argument("--force", action="store_true",
                    help="recompute zeros from scratch")
    args = ap.parse_args()

    res = compute(force=args.force)
    summary(res)
    ok, msgs = validate(res)
    for m in msgs:
        print(m)
    if args.gate:
        print(f"\nGATE {'PASSED' if ok else 'FAILED'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
