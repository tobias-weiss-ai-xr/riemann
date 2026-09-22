/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Mathlib.Analysis.Complex.ExponentialBounds
import Mathlib.Analysis.Real.Pi.Bounds
import Mathlib.NumberTheory.Harmonic.EulerMascheroni
import Mathlib.NumberTheory.Harmonic.GammaDeriv
import Mathlib.Analysis.SpecialFunctions.Log.Deriv
import Mathlib.Analysis.SpecialFunctions.Log.Monotone

open Real

/-! # Li's Criterion: Positivity of the First Li Coefficient

This file formalizes the first step of **Li's criterion** for the
Riemann hypothesis. Li proved that RH is equivalent to the positivity of
every coefficient `λ_n` in the expansion

`log ζ(s) = ∑ₙ λₙ n⁻ˢ`  (near `s = +∞`).

The first coefficient has the classical closed form

`λ₁ = 1 + γ/2 − log 2 − log π/2`

where `γ` is the Euler–Mascheroni constant. Numerically
`λ₁ ≈ 0.023095708966`, and the positivity of the whole sequence
(equivalent to RH) is verified computationally over the first 10 000 zeros
in `data/routes/rt_lc_exact.json` (see `research/JOINT_EVIDENCE.md`).

Here we give a fully rigorous, machine-checked proof that the closed form
is positive, using only certified bounds from mathlib:

* `γ > 0.552` — via the harmonic sequence `eulerMascheroniSeq 19 = H₁₉ − log 20`
  and the sharp bound `log 20 < 2 log 2 + log 5`.
* `log 2 < 0.6931471808` — `log_two_lt_d9`
* `log π < 1.1631508109` — via `π < 16/5` and `log(16/5) = 4 log 2 − log 5`.

## Main definition

* `liLambda1`: the closed form `1 + γ/2 − log 2 − log π/2`.

## Main theorem

* `liLambda1_pos`: `0 < liLambda1`.
-/

namespace Riemann

/-- `log (16/5) < 1.1631508109` : an upper bound on `log π`, from `π < 16/5`. -/
lemma logPi_lt : log (Real.pi) < 1.1631508109 := by
  -- π < 3.15 < 16/5, so log π < log (16/5) = 4 log 2 - log 5
  have hpi : Real.pi < (16 : ℝ) / 5 := by
    have h1 : Real.pi < 3.15 := Real.pi_lt_d2
    exact lt_trans h1 (by norm_num : (3.15 : ℝ) < (16 : ℝ) / 5)
  have hmono : log Real.pi < log ((16 : ℝ) / 5) := log_lt_log Real.pi_pos hpi
  have hdiv : log ((16 : ℝ) / 5) < 1.1631508109 := by
    have hd : log ((16:ℝ) / 5) = log (16:ℝ) - log 5 :=
      log_div (by norm_num : (16:ℝ) ≠ 0) (by norm_num : (5:ℝ) ≠ 0)
    rw [hd]
    have hr : log (16 : ℝ) = 4 * log 2 := by
      have hr' : log ((2 : ℝ) ^ (4 : ℝ)) = (4 : ℝ) * log 2 :=
        log_rpow (by norm_num : 0 < (2:ℝ)) 4
      norm_num at hr'
      exact hr'
    rw [hr]
    have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
    have hl5 : log 5 > 1.6094379123 := log_five_gt_d9
    linarith
  exact lt_trans hmono hdiv

/-- `0.552 < γ` : a certified lower bound on the Euler–Mascheroni constant,
from the harmonic sequence at `n = 19` (since `eulerMascheroniSeq n < γ`). -/
lemma eulerMascheroni_gt_0552 : (0.552 : ℝ) < eulerMascheroniConstant := by
  have h1 : eulerMascheroniSeq 19 < eulerMascheroniConstant :=
    eulerMascheroniSeq_lt_eulerMascheroniConstant 19
  have hlog : log (20 : ℝ) < 2 * 0.6931471808 + 1.6094379126 := by
    have h20 : log (20:ℝ) = 2 * log 2 + log 5 := by
      have h1 : log ((2:ℝ) * (2 * 5)) = log 2 + log (2 * 5) := by
        apply log_mul <;> norm_num
      have h2 : log ((2:ℝ) * 5) = log 2 + log 5 := by
        apply log_mul <;> norm_num
      rw [show (20:ℝ) = (2:ℝ) * (2 * 5) by norm_num, h1, h2]
      ring
    rw [h20]
    have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
    have hl5 : log 5 < 1.6094379126 := log_five_lt_d9
    linarith
  have hd : eulerMascheroniSeq 19 = (harmonic 19 : ℝ) - log (20:ℝ) := by
    unfold eulerMascheroniSeq
    norm_num
  rw [hd] at h1
  have hv : (harmonic 19 : ℝ) = (275295799 / 77597520 : ℚ) := by norm_num
  rw [hv] at h1
  have hl : (275295799 / 77597520 : ℝ) - log (20 : ℝ) > 0.552 := by
    linarith [hlog]
  linarith

/-- λ₁ = 1 + γ/2 − log 2 − log π/2 : the closed form for the first Li coefficient. -/
noncomputable def liLambda1 : ℝ :=
  1 + eulerMascheroniConstant / 2 - log 2 - log Real.pi / 2

/-- The first Li coefficient is positive:
`0 < 1 + γ/2 − log 2 − log π/2` (the first step of Li's criterion). -/
theorem liLambda1_pos : 0 < liLambda1 := by
  unfold liLambda1
  have hg : (0.552 : ℝ) / 2 < eulerMascheroniConstant / 2 := by
    linarith [eulerMascheroni_gt_0552]
  have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
  have hlp : log Real.pi / 2 < 1.1631508109 / 2 := by
    linarith [logPi_lt]
  have h_combined : 1 + (0.552 : ℝ) / 2 - 0.6931471808 - 1.1631508109 / 2 > 0 := by
    norm_num
  linarith

end Riemann
