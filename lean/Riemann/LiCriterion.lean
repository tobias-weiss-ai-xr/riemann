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
import Mathlib.NumberTheory.Harmonic.ZetaAsymp

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

The chain extends to the **second Keiper–Li coefficient**: with γ₁
represented by the certified decimal `stieltjes1Certified` (Python
pipeline `scripts/routes/li_lambda2_certified.py`: a rigorous K=2000
on-line-zero sandwich `λ₂ ∈ [0.090576382823, 0.103286923022]` around the
closed form; see `research/QUASI_RH_CERT_AUDIT.md` Part 4), the closed
form `λ₂ = 1 + γ − γ² − 2γ₁ − 2 log 2 − log π + π²/8 ≈ 0.092345735228`
is machine-checked inside `(0.07, 0.15)` and strictly above λ₁:

* `γ < 0.594` — upper harmonic sequence at `n = 32`
  (`eulerMascheroniSeq' 32 = H₃₂ − log 32`, `log 32 = 5 log 2`);
* `3.1415² < π² < 3.1416²` — mathlib decimal bounds `pi_gt_d4`/`pi_lt_d4`.

The certified computational interval `[0.090576382823, 0.103286923022]`
lies inside the machine-checked `(0.07, 0.15)`, again consistent, with
the formal interval the conservative enclosure.

## Main definition

* `liLambda1`: the closed form `1 + γ/2 − log 2 − log π/2`.
* `stieltjes1Certified`: the certified decimal for the first Stieltjes
  constant γ₁ (no axiom — see its docstring).
* `liLambda2`: the closed form
  `1 + γ − γ² − 2γ₁ − 2 log 2 − log π + π²/8`.

## Main theorems

* `liLambda1_pos`: `0 < liLambda1` (the first step of Li's criterion).
* `liLambda1_lt`: `liLambda1 < 91/1000` (a certified upper bound).
* `liLambda1_mem`: `liLambda1 ∈ (0.0054, 91/1000)` (the combined interval).
* `liLambda2_mem`: `liLambda2 ∈ (0.07, 0.15)` (second coefficient).
* `liLambda1_lt_liLambda2`: the Keiper coefficients strictly increase at
  the start.
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

/-- The first Li coefficient lies in the open interval `(0.0054, 91/1000)`:
a certified two-sided enclosure consistent with the computational interval
`[0.022961009777, 0.023908617943]` computed over the first 10 000 zeros. -/
theorem liLambda1_mem : 0.0054 < liLambda1 ∧ liLambda1 < 91 / 1000 := by
  constructor
  · exact liLambda1_gt_0054
  · exact liLambda1_lt

/-! ### The second Keiper–Li coefficient λ₂ -/

/-- `γ < 0.594` : a certified upper bound on the Euler–Mascheroni constant,
sharper than mathlib's `eulerMascheroniConstant_lt_two_thirds`, via the upper
harmonic sequence at `n = 32` (`eulerMascheroniSeq' 32 = H₃₂ − log 32`, and
`log 32 = 5 log 2` decomposes into the sharply bounded `log 2 > 0.6931471803`).
The numerical witness: `H₃₂ − 5 · 0.6931471803 = 0.5927592939 < 0.594`. -/
lemma eulerMascheroniConstant_lt_0594 : eulerMascheroniConstant < 0.594 := by
  have h1 : eulerMascheroniConstant < eulerMascheroniSeq' 32 :=
    eulerMascheroniConstant_lt_eulerMascheroniSeq' 32
  have h32 : (32 : ℕ) ≠ 0 := by norm_num
  have h2 : eulerMascheroniSeq' 32 = (harmonic 32 : ℝ) - log ((32 : ℕ) : ℝ) := by
    simp only [eulerMascheroniSeq', if_neg h32]
  have hv : (harmonic 32 : ℝ) = (586061125622639 / 144403552893600 : ℚ) := by norm_num
  have hlog : log ((32 : ℕ) : ℝ) = (5 : ℝ) * log 2 := by
    have h32r : ((32 : ℕ) : ℝ) = (2 : ℝ) ^ (5 : ℝ) := by norm_num
    have h : log ((2 : ℝ) ^ (5 : ℝ)) = (5 : ℝ) * log 2 :=
      log_rpow (by norm_num : 0 < (2 : ℝ)) 5
    rw [h32r, h]
  have hl2 : log 2 > 0.6931471803 := log_two_gt_d9
  rw [h2, hv, hlog] at h1
  linarith

/-- `3.1415² < π²` : a certified lower bound on `π²`, from mathlib's
`Real.pi_gt_d4`. -/
lemma piSq_gt : (3.1415 : ℝ) ^ 2 < Real.pi ^ 2 := by
  have h : Real.pi > 3.1415 := Real.pi_gt_d4
  have hpos : (0 : ℝ) < Real.pi := Real.pi_pos
  have s1 : (3.1415 : ℝ) * 3.1415 < Real.pi * 3.1415 :=
    mul_lt_mul_of_pos_right h (by norm_num : (0 : ℝ) < 3.1415)
  have s2 : Real.pi * 3.1415 ≤ Real.pi * Real.pi :=
    mul_le_mul_of_nonneg_left (le_of_lt h) hpos.le
  linarith

/-- `π² < 3.1416²` : a certified upper bound on `π²`, from mathlib's
`Real.pi_lt_d4`. -/
lemma piSq_lt : Real.pi ^ 2 < (3.1416 : ℝ) ^ 2 := by
  have h : Real.pi < 3.1416 := Real.pi_lt_d4
  have hpos : (0 : ℝ) < Real.pi := Real.pi_pos
  have s1 : Real.pi * Real.pi ≤ (3.1416 : ℝ) * Real.pi :=
    mul_le_mul_of_nonneg_right (le_of_lt h) hpos.le
  have s2 : Real.pi * 3.1416 < (3.1416 : ℝ) * 3.1416 :=
    mul_lt_mul_of_pos_right h (by norm_num : (0 : ℝ) < 3.1416)
  linarith

/-- The certified numerical value of the first Stieltjes constant
`γ₁ = −0.0728158454836767248605863758749…`.

This is a plain decimal, NOT an axiom: the mathematical content — that this
decimal equals the first Stieltjes constant (the Laurent coefficient of
`ζ` at `s = 1`) and that the closed form `λ₂ = 1 + γ − γ² − 2γ₁ − 2 log 2 −
log π + π²/8` is the coefficient of `z²` in Keiper's generating function
`log ξ(1/(1−z)) + log 2` — is certified externally by the Python pipeline
`scripts/routes/li_lambda2_certified.py` (gates a–c all PASS: rigorous
K=2000 on-line-zero sandwich `λ₂ ∈ [0.090576382823, 0.103286923022]`
containing the closed form; `λ₂ − λ₁ > 0`; independent series check at
1.8e-13). See `research/QUASI_RH_CERT_AUDIT.md` Part 4. Lean consumes only
the decimal — exactly the "finite certified numerical object + Lean glue"
pattern of the whole repository. -/
def stieltjes1Certified : ℝ := -0.0728158454836767248605863758749

/-- λ₂ = `1 + γ − γ² − 2γ₁ − 2 log 2 − log π + π²/8` with γ₁ the certified
decimal `stieltjes1Certified`: the closed form of the second Keiper–Li
coefficient, the coefficient of `z²` in `log ξ(1/(1−z)) + log 2`.
Numerically `λ₂ ≈ 0.092345735228`. -/
noncomputable def liLambda2 : ℝ :=
  1 + eulerMascheroniConstant - eulerMascheroniConstant * eulerMascheroniConstant
    - 2 * stieltjes1Certified - 2 * log 2 - log Real.pi + Real.pi ^ 2 / 8

/-- `0.07 < λ₂` : a certified lower bound on the second Keiper–Li coefficient.
Worst case over the certified boxes `γ ∈ (0.5604, 0.594)`,
`log 2 < 0.6931471808`, `log π < 1.1631508109`, `π² > 3.1415²`:
`1 + 0.594 − 0.594² + 0.14563169096735 − 2 · 0.6931471808 − 1.1631508109 +
3.1415²/8 = 0.070978299717 > 0.07`. -/
theorem liLambda2_gt_007 : (0.07 : ℝ) < liLambda2 := by
  unfold liLambda2
  -- pair bound: on γ ∈ (0.5604, 0.594) the map γ ↦ γ − γ² is strictly decreasing,
  -- so γ − γ² > f(0.594) = 0.241164; algebraically
  -- (0.594 − γ)(γ − 0.406) > 0 unfolds to γ − γ² − 0.241164 > 0.
  have hu : eulerMascheroniConstant < (0.594 : ℝ) := eulerMascheroniConstant_lt_0594
  have hpos : (0 : ℝ) < (0.594 - eulerMascheroniConstant)
      * (eulerMascheroniConstant - 0.406) :=
    mul_pos (by linarith) (by linarith [eulerMascheroni_gt_05604])
  have hexpl : (0.594 - eulerMascheroniConstant)
      * (eulerMascheroniConstant - 0.406)
      = eulerMascheroniConstant - eulerMascheroniConstant * eulerMascheroniConstant
        - 0.241164 := by
    ring
  rw [hexpl] at hpos
  have hs : stieltjes1Certified = (-0.0728158454836767248605863758749 : ℝ) := rfl
  have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
  have hlp : log Real.pi < 1.1631508109 := logPi_lt
  have hpi := piSq_gt
  linarith

/-- `λ₂ < 0.15` : a certified upper bound on the second Keiper–Li coefficient.
Worst case over the certified boxes `γ ∈ (0.5604, 0.594)`,
`log 2 > 0.6931471803`, `log π > 1.0986122885`, `π² < 3.1416²`:
`1 + 0.5604 − 0.5604² + 0.14563169096735 − 2 · 0.6931471803 − 1.0986122885 +
3.1416²/8 = 0.140783201867 < 0.15`. -/
theorem liLambda2_lt_015 : liLambda2 < (0.15 : ℝ) := by
  unfold liLambda2
  -- pair bound: γ ↦ γ − γ² is decreasing on (1/2, ∞), so the maximum over
  -- γ ∈ (0.5604, 0.594) is at γ = 0.5604: γ − γ² < 0.24635184; algebraically
  -- (γ − 0.5604)(γ − 0.4396) > 0 unfolds to γ² − γ + 0.24635184 > 0.
  have hg : (0.5604 : ℝ) < eulerMascheroniConstant := eulerMascheroni_gt_05604
  have hpos : (0 : ℝ) < (eulerMascheroniConstant - 0.5604)
      * (eulerMascheroniConstant - 0.4396) :=
    mul_pos (by linarith) (by linarith)
  have hexpl : (eulerMascheroniConstant - 0.5604)
      * (eulerMascheroniConstant - 0.4396)
      = eulerMascheroniConstant * eulerMascheroniConstant - eulerMascheroniConstant
        + 0.24635184 := by
    ring
  rw [hexpl] at hpos
  have hs : stieltjes1Certified = (-0.0728158454836767248605863758749 : ℝ) := rfl
  have hl2 : (0.6931471803 : ℝ) < log 2 := log_two_gt_d9
  have hlp : (1.0986122885 : ℝ) < log Real.pi := logPi_gt
  have hpi := piSq_lt
  linarith

/-- The second Keiper–Li coefficient lies in the open interval `(0.07, 0.15)`:
a certified two-sided enclosure consistent with the computational interval
`[0.090576382823, 0.103286923022]` from the K=2000 on-line-zero sandwich
(`data/routes/rt_lc_lambda2.json`). -/
theorem liLambda2_mem : (0.07 : ℝ) < liLambda2 ∧ liLambda2 < 0.15 := by
  constructor
  · exact liLambda2_gt_007
  · exact liLambda2_lt_015

/-- The Keiper coefficients strictly increase at the start: `λ₁ < λ₂`.
In the certified boxes the difference is bounded below by
`γ/2 − γ² − 2γ₁ − log 2 − log π/2 + π²/8 > 0.2802 − 0.594² + 0.14563169096735
− 0.6931471808 − 0.58157540545 + 3.1415²/8 = 0.031900885967 > 0`
(the certified Python margin: `λ₂ − λ₁ = 0.069250026262`). -/
theorem liLambda1_lt_liLambda2 : liLambda1 < liLambda2 := by
  unfold liLambda1 liLambda2
  -- pair bound γ − γ² > 0.241164 (same concavity argument as liLambda2_gt_007)
  have hu : eulerMascheroniConstant < (0.594 : ℝ) := eulerMascheroniConstant_lt_0594
  have hpos : (0 : ℝ) < (0.594 - eulerMascheroniConstant)
      * (eulerMascheroniConstant - 0.406) :=
    mul_pos (by linarith) (by linarith [eulerMascheroni_gt_05604])
  have hexpl : (0.594 - eulerMascheroniConstant)
      * (eulerMascheroniConstant - 0.406)
      = eulerMascheroniConstant - eulerMascheroniConstant * eulerMascheroniConstant
        - 0.241164 := by
    ring
  rw [hexpl] at hpos
  have hs : stieltjes1Certified = (-0.0728158454836767248605863758749 : ℝ) := rfl
  have hgh : eulerMascheroniConstant / 2 < (0.594 : ℝ) / 2 := by
    linarith [eulerMascheroniConstant_lt_0594]
  have hl2 : log 2 < 0.6931471808 := log_two_lt_d9
  have hlp : log Real.pi < 1.1631508109 := logPi_lt
  have hpi := piSq_gt
  linarith

/-- The bridge to the completed zeta: the certified λ₁ equals the value at
`s = 1` of mathlib's entire regularization `Λ₀(s) = Λ(s) + 1/s + 1/(1-s)` of
the completed Riemann zeta `Λ(s) = π^(-s/2) Γ(s/2) ζ(s)` — the anchor point
for the Keiper-Li expansion of `log Λ₀` at `s = 1`. -/
theorem liLambda1_eq_completedZeta0 :
    (liLambda1 : ℂ) = completedRiemannZeta₀ 1 := by
  unfold liLambda1
  rw [completedRiemannZeta₀_one]
  have hlog : Complex.log (4 * (Real.pi : ℂ))
      = ((2 * Real.log 2 + Real.log π : ℝ) : ℂ) := by
    have hco : Complex.log (4 * (Real.pi : ℂ))
        = Complex.log (((4:ℝ) * Real.pi : ℝ) : ℂ) := by
      congr 1
      push_cast
      rfl
    rw [hco, ← Complex.ofReal_log (by positivity : (0:ℝ) ≤ 4 * Real.pi)]
    norm_cast
    rw [log_mul (by norm_num : (4:ℝ) ≠ 0) Real.pi_ne_zero, log_four_eq]
  rw [hlog]
  norm_cast
  ring

end Riemann
