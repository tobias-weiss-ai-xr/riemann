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

Here we give a fully rigorous, machine-checked **certified interval** for
the closed form, using only certified bounds from mathlib:

* **lower bound** `0.0054 < λ₁` (so in particular `0 < λ₁`):
  * `γ > 0.5604` — via the harmonic sequence `eulerMascheroniSeq 29 = H₂₉ − log 30`
    and the sharp bound `log 30 < log 2 + log 3 + log 5`;
  * `log 2 < 0.6931471808` — `log_two_lt_d9`;
  * `log π < 1.1631508109` — via `π < 16/5` and `log(16/5) = 4 log 2 − log 5`.
* **upper bound** `λ₁ < 91/1000`:
  * `γ < 2/3` — `eulerMascheroniConstant_lt_two_thirds`;
  * `log 2 > 0.6931471803` — `log_two_gt_d9`;
  * `log π > 1.0986122885` — via `3 < π` and `log_three_gt_d9`.

The certified computational interval from the first 10 000 zeros,
`[0.022961009777, 0.023908617943]` (`data/routes/rt_lc_exact.json`),
lies inside the machine-checked `(0.0054, 0.091)` — so the two
certificates are consistent, with the formal interval a conservative
enclosure of the numerical one.

## Main definition

* `liLambda1`: the closed form `1 + γ/2 − log 2 − log π/2`.

## Main theorems

* `liLambda1_pos`: `0 < liLambda1` (the first step of Li's criterion).
* `liLambda1_lt`: `liLambda1 < 91/1000` (a certified upper bound).
* `liLambda1_mem`: `liLambda1 ∈ (0.0054, 91/1000)` (the combined interval).
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

/-- `0.5604 < γ` : a certified lower bound on the Euler–Mascheroni constant,
from the harmonic sequence at `n = 29` (since `eulerMascheroniSeq n < γ`).
`n + 1 = 30 = 2·3·5` is 5-smooth, so `log 30` decomposes into sharply
bounded logs. -/
lemma eulerMascheroni_gt_05604 : (0.5604 : ℝ) < eulerMascheroniConstant := by
  have h1 : eulerMascheroniSeq 29 < eulerMascheroniConstant :=
    eulerMascheroniSeq_lt_eulerMascheroniConstant 29
  have hlog : log (30 : ℝ) < 0.6931471808 + 1.0986122888 + 1.6094379126 := by
    have h30 : log (30:ℝ) = log 2 + log 3 + log 5 := by
      have h1 : log ((2:ℝ) * (3 * 5)) = log 2 + log (3 * 5) := by
        apply log_mul <;> norm_num
      have h2 : log ((3:ℝ) * 5) = log 3 + log 5 := by
        apply log_mul <;> norm_num
      rw [show (30:ℝ) = (2:ℝ) * (3 * 5) by norm_num, h1, h2]
      ring
    rw [h30]
    have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
    have hl3 : log 3 < 1.0986122888 := log_three_lt_d9
    have hl5 : log 5 < 1.6094379126 := log_five_lt_d9
    linarith
  have hd : eulerMascheroniSeq 29 = (harmonic 29 : ℝ) - log (30:ℝ) := by
    unfold eulerMascheroniSeq
    norm_num
  rw [hd] at h1
  have hv : (harmonic 29 : ℝ) = (9227046511387 / 2329089562800 : ℚ) := by norm_num
  rw [hv] at h1
  have hl : (9227046511387 / 2329089562800 : ℝ) - log (30 : ℝ) > 0.5604 := by
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
    linarith [eulerMascheroni_gt_05604]
  have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
  have hlp : log Real.pi / 2 < 1.1631508109 / 2 := by
    linarith [logPi_lt]
  have h_combined : 1 + (0.552 : ℝ) / 2 - 0.6931471808 - 1.1631508109 / 2 > 0 := by
    norm_num
  linarith

/-- A sharper certified lower bound: `0.0054 < λ₁`. -/
theorem liLambda1_gt_0054 : 0.0054 < liLambda1 := by
  unfold liLambda1
  have hg : (0.5604 : ℝ) / 2 < eulerMascheroniConstant / 2 := by
    linarith [eulerMascheroni_gt_05604]
  have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
  have hlp : log Real.pi / 2 < 1.1631508109 / 2 := by
    linarith [logPi_lt]
  have h_combined :
      1 + (0.5604 : ℝ) / 2 - 0.6931471808 - 1.1631508109 / 2 > 0.0054 := by
    norm_num
  linarith

/-- `1.0986122885 < log π` : a lower bound on `log π`, from `3 < π`. -/
lemma logPi_gt : 1.0986122885 < log (Real.pi) := by
  -- 3 < π, so log 3 < log π; and log 3 > 1.0986122885
  have hmono : log (3 : ℝ) < log Real.pi := log_lt_log (by norm_num) Real.pi_gt_three
  have h3 : 1.0986122885 < log (3 : ℝ) := log_three_gt_d9
  exact lt_trans h3 hmono

/-- λ₁ < 91/1000 : a certified upper bound on the first Li coefficient, from
`γ < 2/3`, `log 2 > 0.6931471803`, and `log π > 1.0986122885`. -/
theorem liLambda1_lt : liLambda1 < 91 / 1000 := by
  unfold liLambda1
  have hg : eulerMascheroniConstant / 2 < (2 / 3 : ℝ) / 2 := by
    linarith [eulerMascheroniConstant_lt_two_thirds]
  have hl2 : -log 2 < -0.6931471803 := by linarith [log_two_gt_d9]
  have hlp : -(log Real.pi / 2) < -(1.0986122885 / 2) := by
    linarith [logPi_gt]
  have h_combined :
      1 + (2 / 3 : ℝ) / 2 - 0.6931471803 - 1.0986122885 / 2 < 91 / 1000 := by
    norm_num
  linarith

/-- The first Li coefficient lies in the open interval `(0.0012, 91/1000)`:
a certified two-sided enclosure consistent with the computational interval
`[0.022961009777, 0.023908617943]` computed over the first 10 000 zeros. -/
theorem liLambda1_mem : 0.0054 < liLambda1 ∧ liLambda1 < 91 / 1000 := by
  constructor
  · exact liLambda1_gt_0054
  · exact liLambda1_lt

end Riemann
