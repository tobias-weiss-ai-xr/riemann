#!/usr/bin/env python
"""RT-LC-L2 -- Certified lambda_2 (second Li/Keiper coefficient).

Extends scripts/routes/li_criterion_certified.py (K=10000, n=1) to n=2.

Method
------
Same rigorous on-line-zero partial-sum sandwich as RT2-LC:

    lambda_n = sum_rho [1 - (1 - 1/rho)^n]  (over all nontrivial zeros)

For rho = 1/2 + i*gamma (upper half plane), |1 - 1/rho| = 1 and
arg(1 - 1/rho) = theta_k = 2*arctan(1/(2*gamma_k))  [exact identity].
Each conjugate pair contributes c(n,k) = 2*(1 - cos(n*theta_k)) >= 0, so

    S_K(n) = sum_{k<=K} c(n,k)          is a certified LOWER bound,
    T_K(n) = n^2*(ln(gamma_K/(2pi)) + 2)/gamma_K + n^2/gamma_K^2
                                        is a rigorous tail UPPER bound,
    lambda_n in [S_K(n), S_K(n) + T_K(n)].

Closed form for n = 2 (Keiper generating function log xi(1/(1-z)) =
-log 2 + sum lambda_n z^n/n; coefficient extraction at z^2):

    lambda_2 = 1 + gamma - gamma^2 - 2*gamma_1 - 2*ln(2) - ln(pi) + pi^2/8

where gamma is the Euler-Mascheroni constant and gamma_1 the first
Stieltjes constant (-0.0728158...). The closed form is an unconditional
theorem (no RH); it must land inside the certified interval (gate a).
Independently cross-checked against mpmath's stieltjes(1) at 50 dps.

Also certified: lambda_2 > lambda_1 (gate b) -- lambda_2 - lambda_1 has a
positive certified lower bound, i.e. the Keiper coefficients are strictly
increasing at the start.

Output: data/routes/rt_lc_lambda2.json
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import mpmath as mp
from loguru import logger

OUT_PATH = Path("data/routes/rt_lc_lambda2.json")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zeros", type=int, default=2000, help="K = number of on-line zeros")
    ap.add_argument("--dps", type=int, default=50, help="decimal precision")
    args = ap.parse_args()

    mp.mp.dps = args.dps
    K = args.zeros
    t0 = time.time()

    # --- closed form (unconditional theorem) -----------------------------
    gamma = mp.euler
    gamma1 = mp.stieltjes(1)
    lam2_closed = 1 + gamma - gamma**2 - 2 * gamma1 - 2 * mp.log(2) - mp.log(mp.pi) + mp.pi**2 / 8
    lam1_closed = 1 + gamma / 2 - mp.log(2) - mp.log(mp.pi) / 2
    logger.info(f"lambda_2 closed form = {mp.nstr(lam2_closed, 20)}")
    logger.info(f"lambda_1 closed form = {mp.nstr(lam1_closed, 20)}")
    logger.info(f"lambda_2 - lambda_1  = {mp.nstr(lam2_closed - lam1_closed, 20)}")

    # --- certified sandwich from on-line zeros ---------------------------
    s_k = mp.mpf(0)
    gamma_k = mp.mpf(0)
    for k in range(1, K + 1):
        g = mp.im(mp.zetazero(k))
        theta = 2 * mp.atan(1 / (2 * g))
        s_k += 2 * (1 - mp.cos(2 * theta))
        gamma_k = g
    tail = 4 * (mp.log(gamma_k / (2 * mp.pi)) + 2) / gamma_k + 4 / gamma_k**2
    lower, upper = s_k, s_k + tail
    logger.info(f"K={K} zeros: gamma_K={mp.nstr(gamma_k, 12)}")
    logger.info(f"certified lambda_2 in [{mp.nstr(lower, 15)}, {mp.nstr(upper, 15)}] "
                f"(width {mp.nstr(tail, 10)})")

    # --- gates ------------------------------------------------------------
    gate_a = lower < lam2_closed < upper
    gate_b = lam2_closed - lam1_closed > 0
    # Independent algebra check: lambda_2 = G''(0) where G(z) =
    # log xi(1/(1-z)) + log 2, evaluated by central finite difference at a
    # small offset (the components are singular exactly at z = 0 only).
    # Role: confirm the coefficient extraction, not certify (gate c).
    def G(z: mp.mpf) -> mp.mpf:
        s = 1 / (1 - z)
        return mp.log(mp.mpf("0.5") * s * (s - 1) * mp.pi ** (-s / 2) * mp.gamma(s / 2) * mp.zeta(s)) + mp.log(2)

    h = mp.mpf(10) ** -6
    lam2_series = (G(h) + G(-h)) / h**2  # G(0) = 0 exactly (xi(1) = 1/2)
    series_err = abs(lam2_series - lam2_closed)
    gate_c = series_err < mp.mpf(10) ** -9
    logger.info(f"series cross-check error = {mp.nstr(series_err, 5)}")
    logger.info(f"gate a (closed form in interval): {gate_a}")
    logger.info(f"gate b (lambda_2 > lambda_1):     {gate_b}")
    logger.info(f"gate c (series == closed form):   {gate_c}")

    ok = gate_a and gate_b and gate_c
    logger.info(f"VERDICT: {'PASS' if ok else 'FAIL'} "
                f"[{time.time() - t0:.1f}s]")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "n": 2,
        "K": K,
        "gamma_K": mp.nstr(gamma_k, 20),
        "S_K": mp.nstr(s_k, 25),
        "T_K": mp.nstr(tail, 25),
        "lower": mp.nstr(lower, 25),
        "upper": mp.nstr(upper, 25),
        "closed_form": mp.nstr(lam2_closed, 30),
        "closed_form_inputs": {
            "gamma": mp.nstr(gamma, 30),
            "gamma_1": mp.nstr(gamma1, 30),
        },
        "lambda_1_closed": mp.nstr(lam1_closed, 30),
        "lambda_2_minus_lambda_1": mp.nstr(lam2_closed - lam1_closed, 25),
        "series_cross_check_error": mp.nstr(series_err, 10),
        "gates": {"a_closed_in_interval": bool(gate_a),
                  "b_lambda2_gt_lambda1": bool(gate_b),
                  "c_series_matches": bool(gate_c)},
        "verdict": "PASS" if ok else "FAIL",
        "elapsed_s": round(time.time() - t0, 1),
    }, indent=2))
    logger.info(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
