# NB-16K Post-Analysis: the εₙ "Power Law" Is Really n⁻¹ × Logarithm

**Date**: 2026-10-09 · **Data**: certified chain `rt_nb_4k.json` + `rt_nb_8k.json` +
`rt_nb_16k.json` (11 sizes, n = 16 … 16384, verify + selftest clean at 8K/16K)
**Script**: `scripts/_nb16k_drift.py` (temp, gitignored)

---

## 1. The headline number was hiding the structure

The 16K gate line reported the 11-point fit

    εₙ ≈ 0.4516 · n^−0.8614

Fitting a pure power to a power-with-logarithmic-correction **biases the
exponent**. Weighting all 11 points on log-scale and comparing nested models:

| model | form | rms (ln) | AIC |
|---|---|---:|---:|
| M1 pure power | εₙ = A·n^(−β) | 5.6e-2 | −59.3 |
| **M2 power × log** | εₙ = A·n^(−b)·(ln n)^(+d) | **4.8e-3** | **−111.4** |
| M3 log-linear/n | εₙ = (a + b·ln n)/n | 0.9% rel | — |

M2 beats M1 by **ΔAIC = 52** — decisive — with

    εₙ ≈ 0.2566 · n^(−1.0078 ± 0.0045) · (ln n)^(+0.840 ± 0.025)

The leading exponent is **statistically indistinguishable from exactly 1**
(t = 1.7); the logarithmic factor sits in the *numerator*. M3 agrees:
n·εₙ ≈ 0.121 + 0.169·ln n (rises 0.589 → 1.604 across the chain,
near-linearly in ln n).

**Reading**: over 1024× in n the NB density on the grid aₖ = k/(n+1) decays
like **n⁻¹ × (ln n)^+0.84** — not like n^−0.86. Local exponent of this law:
κ(n) = b − d/ln n = 1.0078 − 0.840/ln n, i.e. 0.76 at n = 32 rising to 0.92
at n = 16384 — matching the measured local exponents (0.726 → 0.928). The
"accelerating β" is the arithmetic log factor thinning out relative to n⁻¹.

## 2. Local exponents (successive doublings)

κₙ = −log₂(εₙ/ε₂ₙ):

    0.726, 0.793, 0.814, 0.864, 0.850, 0.892, 0.881, 0.917, 0.891, 0.928

Rising, noisy (±0.02), asymptoting toward ≈ 0.93 over the last pair — exactly
what n⁻¹(ln n)^−0.84 predicts locally (−log₂(εₙ/ε₂ₙ) → 1 − d/ln n → 0.88 at
n = 16K).

## 3. Secondary scalings (from min_eig / cond, all 11 sizes)

| quantity | measured law | stability |
|---|---|---|
| λ_min(Gₙ) | ≈ 0.150 · n^(−1.034 ± 0.007) | rock-stable, all 10 doublings |
| cond(Gₙ) | ≈ n^(2.03) | stable |
| εₙ/λ_min | 3.8 → 13.3, growth rate decaying (local exponent −0.30 → −0.10) | slowing |

λ_min's exponent is the cleanest invariant in the whole chain — a
conjecture-shaped target: **λ_min(G_n) ≍ n^−1.03** for the discrete NB
Gramian. Note εₙ decays *slower* than λ_min (the minimizer of the Rayleigh
quotient is not a pure bottom-eigenvector; the affine constraint matters).

## 4. Falsifiable predictions (for a future NB-32K)

| model | ε₃₂₇₆₈ | ε₆₅₅₃₆ |
|---|---:|---:|
| M1 (pure power) | 5.82e-5 | 3.21e-5 |
| M2 (n⁻¹ × log) | 5.16e-5 | 2.71e-5 |
| M3 (log-linear/n) | 5.74e-5 | 3.05e-5 |

The pure-power prediction is already disfavored; a 32K point landing below
~5.4e-5 kills M1 outright. (32K is blocked on the O(n³) assembler — ~3 d
phase 1 + ~40 h K-matrix at current rates; the quasi-polynomial floor
structure of K(i,j) is the analytic opening for an O(n²·polylog) assembly.)

## 5. Honest interpretation

- Baez–Duarte (2003) needs only εₙ → 0; **no criterion involves the rate**.
  This note characterizes the rate, it proves nothing about RH.
- n⁻¹ is the natural continuum truncation scale for a density on [0,1] with
  effective resolution n; the log factor is the arithmetic correction
  (breakpoints are ~0.61·c² rationals, effective degrees of freedom ~ n).
  A zero-statistics reading (Müntz/co-Poisson kernel, Burnol; inner-product
  formulas, Juncos 2011) is *consistent* but not derived here.
- Double precision at cond 2e8 leaves ~8 significant digits of headroom
  (λ_min 7.3e-6 vs machine-limited ~2e-8 relative) — the log-scale fits are
  safe.
- Single grid scheme (aₖ = k/(n+1)); other Baez–Duarte dilations (dyadic rₖ)
  may show different constants, same structural test applies.

**Bottom line**: quote εₙ ≈ 0.257·n⁻¹·(ln n)^+0.84 (or equivalently
n·εₙ ≈ 0.121 + 0.169·ln n), not β = −0.8614. The chain's "acceleration" is
the log factor, and the next doubling should land at ε₃₂ₖ ≈ 5.2–5.8e-5.

---
*Correction (2026-10-09, same day): an earlier version of this note printed
the log factor with the wrong sign — (ln n)^−0.84 instead of +0.84. The
certified-rational containment check written for the Lean module
(`Riemann/NymanBeurling.lean`) caught it: the flipped model is 5× off at
n = 16. The AIC table, prediction table, and κ(n) = b − d/ln n reading were
always computed with the correct sign and are unchanged.*
