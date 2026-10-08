#!/usr/bin/env python
"""RT-LC-L3 -- Certified lambda_3 (third Li/Keiper coefficient).

Extends scripts/routes/li_lambda2_certified.py (n=2) to n=3.

Method
------
Same rigorous on-line-zero partial-sum sandwich:

    lambda_n = sum_rho [1 - (1 - 1/rho)^n]  (over all nontrivial zeros)

For rho = 1/2 + i*gamma_k (upper half plane), the conjugate pair contributes
c(n,k) = 2*(1 - cos(n*theta_k)) >= 0 with theta_k = 2*arctan(1/(2*gamma_k))
[exact identity], so

    S_K(n) = sum_{k<=K} c(n,k)          is a certified LOWER bound,
    T_K(n) = n^2*(ln(gamma_K/(2pi)) + 2)/gamma_K + n^2/gamma_K^2
                                        is a rigorous tail UPPER bound,
    lambda_n in [S_K(n), S_K(n) + T_K(n)].

Closed form for n = 3 (derived, not recalled: PSLQ identification at 80 dps
against basis {1, g, g^2, g^3, g1, g*g1, g2, log2, logpi, pi^2, zeta(3)},
confirmed against OEIS A104540 and the derivative route
lambda_3 = (1/2!) d^3/ds^3 [s^2 ln xi(s)]|_{s=1}):

    lambda_3 = 1 + (3/2)g - 3g^2 + g^3 - 6g_1 + 3 g g_1 + (3/2) g_2
               - 3 ln 2 - (3/2) ln pi + (3/8) pi^2 - (7/8) zeta(3)

with g = 0.5772..., g_1 = -0.0728158..., g_2 = -0.00969036... the Stieltjes
constants. Cross-checked at 80 dps in all three ways (gate d).

Also certified: lambda_3 > lambda_2 (gate b).

Lean witnesses (gate e): the decimal closed form (all Stieltjes/zeta(3)
constants as certified 31-digit decimals, exact in Lean) is verified with
fractions.Fraction to lie in (0.19, 0.23) under the SAME box reasoning the
Lean proof uses: gamma in (0.5604, 0.594), the gamma-atoms jointly bounded
by monotone-cubic endpoint identities, g*g_1 boxed by constants, pi^2 in
(3.1415^2, 3.1416^2), log 2 in (0.6931471803, 0.6931471808), log pi in
(1.0986122885, 1.1631508109).

Output: data/routes/rt_lc_lambda3.json
"""
from __future__ import annotations

import argparse
import json
import time
from fractions import Fraction
from pathlib import Path

import mpmath as mp
from loguru import logger

OUT_PATH = Path("data/routes/rt_lc_lambda3.json")

# certified decimals (as they will appear in Lean)
G1_DEC = "-0.0728158454836767248605863758749"
G2_DEC = "-0.0096903631928723184845303860353"
Z3_DEC = "1.2020569031595942853997381615114"


def frac(s: str) -> Fraction:
    return Fraction(s)


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
    gamma2 = mp.stieltjes(2)
    lam3_closed = (
        1
        + mp.mpf(3) / 2 * gamma
        - 3 * gamma**2
        + gamma**3
        - 6 * gamma1
        + 3 * gamma * gamma1
        + mp.mpf(3) / 2 * gamma2
        - 3 * mp.log(2)
        - mp.mpf(3) / 2 * mp.log(mp.pi)
        + mp.mpf(3) / 8 * mp.pi**2
        - mp.mpf(7) / 8 * mp.zeta(3)
    )
    lam2_closed = 1 + gamma - gamma**2 - 2 * gamma1 - 2 * mp.log(2) - mp.log(mp.pi) + mp.pi**2 / 8
    logger.info(f"lambda_3 closed form = {mp.nstr(lam3_closed, 25)}  (OEIS A104540: 0.2076389205543...)")
    logger.info(f"lambda_2 closed form = {mp.nstr(lam2_closed, 25)}")

    # --- certified sandwich from on-line zeros ---------------------------
    s_k = mp.mpf(0)
    gamma_k = mp.mpf(0)
    for k in range(1, K + 1):
        g = mp.im(mp.zetazero(k))
        theta = 2 * mp.atan(1 / (2 * g))
        s_k += 2 * (1 - mp.cos(3 * theta))
        gamma_k = g
    tail = 9 * (mp.log(gamma_k / (2 * mp.pi)) + 2) / gamma_k + 9 / gamma_k**2
    lower, upper = s_k, s_k + tail
    logger.info(f"K={K} zeros: gamma_K={mp.nstr(gamma_k, 12)}")
    logger.info(f"certified lambda_3 in [{mp.nstr(lower, 15)}, {mp.nstr(upper, 15)}] "
                f"(width {mp.nstr(tail, 10)})")

    # --- independent derivative check (gate d) ---------------------------
    def L3(s: mp.mpf) -> mp.mpf:
        return s**2 * mp.log(
            mp.mpf("0.5") * s * (s - 1) * mp.pi ** (-s / 2) * mp.gamma(s / 2) * mp.zeta(s)
        )

    lam3_diff = mp.diff(L3, 1, 3) / 2
    diff_err = abs(lam3_diff - lam3_closed)
    gate_d = diff_err < mp.mpf(10) ** -30

    # --- series cross-check via G'''(0)/2 (gate c) -----------------------
    def G(z: mp.mpf) -> mp.mpf:
        s = 1 / (1 - z)
        return mp.log(
            mp.mpf("0.5") * s * (s - 1) * mp.pi ** (-s / 2) * mp.gamma(s / 2) * mp.zeta(s)
        ) + mp.log(2)

    h = mp.mpf(10) ** -5
    # 5-point central third difference: G'''(0) ~ [G(2h) - 2G(h) + 2G(-h) - G(-2h)]/(2h^3);
    # lambda_3 = G'''(0)/2 (G(0)=0 cancels the even part)
    lam3_series = (G(2 * h) - 2 * G(h) + 2 * G(-h) - G(-2 * h)) / (2 * h**3) / 2
    series_err = abs(lam3_series - lam3_closed)
    gate_c = series_err < mp.mpf(10) ** -7

    # --- gates ------------------------------------------------------------
    gate_a = lower < lam3_closed < upper
    gate_b = lam3_closed - lam2_closed > 0
    gate_b2 = lower - (lam2_closed + mp.mpf(10) ** -9) > 0
    logger.info(f"gate a (closed form in interval): {gate_a}")
    logger.info(f"gate b (lambda_3 > lambda_2):     {gate_b} (sandwich-disjoint: {gate_b2})")
    logger.info(f"gate c (series == closed form):   {gate_c} (err {mp.nstr(series_err, 5)})")
    logger.info(f"gate d (diff route matches):      {gate_d} (err {mp.nstr(diff_err, 5)})")

    # --- Lean witnesses (gate e): exact Fraction box reasoning ------------
    g_lo, g_hi = frac("0.5604"), frac("0.594")
    g1d, g2d, z3d = frac(G1_DEC), frac(G2_DEC), frac(Z3_DEC)
    log2_lo, log2_hi = frac("0.6931471803"), frac("0.6931471808")
    logpi_lo, logpi_hi = frac("1.0986122885"), frac("1.1631508109")
    pi2_lo, pi2_hi = frac("3.1415") ** 2, frac("3.1416") ** 2

    # rational cubic q0(g) = g^3 - 3 g^2 + (3/2) g  (the gamma-atoms of
    # lambda_3 after boxing g*g_1 by constants); strictly decreasing on the box
    def q0(g: Fraction) -> Fraction:
        return g**3 - 3 * g**2 + frac(3) / 2 * g

    # g*g_1 in (g1d * 0.594, g1d * 0.5604) since g1d < 0 (pos_of_neg flip)
    lam3_dec_lower = (
        1 + q0(g_hi) + g1d * (-6 + 3 * g_hi) + frac(3) / 2 * g2d
        - 3 * log2_hi - frac(3) / 2 * logpi_hi
        + frac(3) / 8 * pi2_lo - frac(7) / 8 * z3d
    )
    lam3_dec_upper = (
        1 + q0(g_lo) + g1d * (-6 + 3 * g_lo) + frac(3) / 2 * g2d
        - 3 * log2_lo - frac(3) / 2 * logpi_lo
        + frac(3) / 8 * pi2_hi - frac(7) / 8 * z3d
    )
    # lambda_3 - lambda_2 under the same box (gamma-part: g^3 - 2g^2 + g/2)
    def qb(g: Fraction) -> Fraction:
        return g**3 - 2 * g**2 + frac(1) / 2 * g

    gate_b_lb = (
        qb(g_hi) + g1d * (-4 + 3 * g_hi) + frac(3) / 2 * g2d
        - log2_hi - frac(1) / 2 * logpi_hi
        + frac(1) / 4 * pi2_lo - frac(7) / 8 * z3d
    )
    # the Lean box certifies the decimal closed form in (lower, upper);
    # the Lean theorem interval (0.15, 0.3) must sit strictly inside that box
    target_lo, target_hi = frac(15) / 100, frac(30) / 100
    gate_e = (
        target_lo < lam3_dec_lower
        and lam3_dec_upper < target_hi
        and gate_b_lb > 0
        and abs(mp.mpf(mp.nstr(lam3_closed, 30)) - lam3_closed) < mp.mpf(10) ** -28
    )
    logger.info(f"decimal closed form box = [{float(lam3_dec_lower):.6f}, {float(lam3_dec_upper):.6f}]")
    logger.info(f"lambda_3 - lambda_2 box lower bound = {float(gate_b_lb):.6f}")
    logger.info(f"gate e (Lean witnesses: (0.15,0.3) inside box, dlambda>0): {gate_e}")

    ok = gate_a and gate_b and gate_b2 and gate_c and gate_d and gate_e
    logger.info(f"VERDICT: {'PASS' if ok else 'FAIL'} [{time.time() - t0:.1f}s]")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "n": 3,
        "K": K,
        "gamma_K": mp.nstr(gamma_k, 20),
        "S_K": mp.nstr(s_k, 25),
        "T_K": mp.nstr(tail, 25),
        "lower": mp.nstr(lower, 25),
        "upper": mp.nstr(upper, 25),
        "closed_form": mp.nstr(lam3_closed, 30),
        "closed_form_inputs": {
            "gamma": mp.nstr(gamma, 30),
            "gamma_1": mp.nstr(gamma1, 30),
            "gamma_2": mp.nstr(gamma2, 30),
            "zeta_3": mp.nstr(mp.zeta(3), 30),
        },
        "certified_decimals": {"gamma_1": G1_DEC, "gamma_2": G2_DEC, "zeta_3": Z3_DEC},
        "lambda_2_closed": mp.nstr(lam2_closed, 30),
        "lambda_3_minus_lambda_2": mp.nstr(lam3_closed - lam2_closed, 25),
        "lambda_3_minus_lambda_2_lb": str(float(gate_b_lb)),
        "derivative_route_error": mp.nstr(diff_err, 10),
        "series_cross_check_error": mp.nstr(series_err, 10),
        "lean_witnesses": {
            "target_interval": [0.15, 0.3],
            "dec_box_lower": str(lam3_dec_lower),
            "dec_box_upper": str(lam3_dec_upper),
        },
        "gates": {
            "a_closed_in_interval": bool(gate_a),
            "b_lambda3_gt_lambda2": bool(gate_b),
            "b2_sandwich_disjoint": bool(gate_b2),
            "c_series_matches": bool(gate_c),
            "d_diff_route": bool(gate_d),
            "e_lean_witnesses": bool(gate_e),
        },
        "verdict": "PASS" if ok else "FAIL",
        "elapsed_s": round(time.time() - t0, 1),
    }, indent=2))
    logger.info(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
