/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Analysis.SpecialFunctions.Pow.Complex
import Mathlib.Topology.Algebra.Ring.Real
import Mathlib.Algebra.Order.Floor.Ring
import Mathlib.Analysis.PSeries
import Riemann.TransferOperator.Definitions

/-!
# Basic Analytic Facts for the Transfer Operator

Foundational analytic facts used throughout the transfer operator development:
summability of branch weights, growth of the potential, and basic interval facts.

The Gauss map and inverse branch API lives in `Riemann.TransferOperator.Definitions`
(algebraic/combinatorial parts in `Riemann.GaussMapCompilable`); this file only
carries the analysis.
-/

open Set Real

namespace Riemann.TransferOperator

-- ============================================================================
-- SECTION 3: Sum Convergence (for Nuclear Operator)
-- ============================================================================

/-- Sum of (n + 1 + x)^{-2σ} converges for σ > 1/2, x ≥ 0.

Comparison route: (n+1+x)^{-2σ} ≤ (n+1)^{-2σ} ≤ n^{-2σ} (antitone in base for
negative exponent), and `Real.summable_nat_rpow` handles the p-series. The tail
comparison (n+1 vs n) needs a shift lemma not yet in this skeleton. -/
theorem sum_inverse_pow_converges (σ : ℝ) (x : ℝ) (hσ : σ > 1 / 2) (hx : 0 ≤ x) :
    Summable fun n : ℕ => ((n : ℝ) + 1 + x) ^ (-2 * σ : ℝ) := by
  sorry -- Fleet 3: p-series (`Real.summable_nat_rpow`, p = 2σ > 1) + base-shift comparison

/-- For σ > 1/2 and x ∈ [0,1], the partial sums are uniformly bounded. -/
theorem sum_inverse_pow_bounded (σ : ℝ) (x : ℝ) (hσ : σ > 1 / 2) (hx1 : 0 ≤ x) (hx2 : x ≤ 1) :
    ∃ M : ℝ, ∀ n : ℕ, ∑ i ∈ Finset.range n, ((i : ℝ) + 1 + x) ^ (-2 * σ : ℝ) ≤ M := by
  sorry -- Fleet 3: boundedness of partial sums of a summable nonneg series

-- ============================================================================
-- SECTION 4: Real-valued Functions and Their Properties
-- ============================================================================

/-- For x > 0, log|x| = log x. -/
theorem log_abs_of_pos (x : ℝ) (hx : 0 < x) : Real.log |x| = Real.log x := by
  rw [abs_of_pos hx]

/-- For x ∈ (0,1), log x < 0. -/
theorem log_neg_on_zero_one (x : ℝ) (hx1 : 0 < x) (hx2 : x < 1) : Real.log x < 0 := by
  exact Real.log_neg hx1 hx2

-- ============================================================================
-- SECTION 5: Complex Numbers and Exponentials
-- ============================================================================

/-- For real a > 0 and complex s, a^s is well-defined (nonzero). -/
theorem rpow_complex_defined (a : ℝ) (s : ℂ) (ha : 0 < a) :
    ((a : ℂ)) ^ s ≠ 0 := by
  exact (Complex.cpow_ne_zero_iff).2 (Or.inl (Complex.ofReal_ne_zero.2 (ne_of_gt ha)))

/-- Absolute value of complex power: ‖a^s‖ = a^{Re(s)} for a > 0. -/
theorem complex_rpow_abs (a : ℝ) (s : ℂ) (ha : 0 < a) :
    ‖((a : ℂ)) ^ s‖ = (a : ℝ) ^ (s.re : ℝ) := by
  sorry -- Fleet 3: polar decomposition of complex power

/-- For a > 0 and real σ, ‖a^σ‖ = a^σ. -/
theorem complex_rpow_abs_of_real (a : ℝ) (σ : ℝ) (ha : 0 < a) (hσ : 0 < σ) :
    ‖((a : ℂ) ^ (↑σ : ℂ))‖ = a ^ σ := by
  sorry -- Fleet 3: specialization of the above to real exponents

/-- For a > 1 and σ > 0, a^{-σ} < 1.
(Corrected from `1 ≤ a`: at a = 1 the value equals exactly 1.) -/
theorem rpow_neg_lt_one (a : ℝ) (σ : ℝ) (ha : 1 < a) (hσ : 0 < σ) :
    a ^ (-σ : ℝ) < 1 := by
  have hap : (0 : ℝ) < a := by linarith
  have hpos : (0 : ℝ) < (a : ℝ) ^ σ := Real.rpow_pos_of_pos hap σ
  rw [Real.rpow_neg (by linarith), inv_eq_one_div, one_div_lt hpos one_pos, one_div_one]
  exact Real.one_lt_rpow ha hσ
/-- For a ≥ 1 and σ > 0, a^{-σ} is decreasing (antitone) in σ.
(Corrected from `Monotone` — a^(-σ) strictly decreases for a > 1.) -/
theorem rpow_neg_decreasing (a : ℝ) (ha : 1 ≤ a) :
    Antitone fun σ : ℝ => a ^ (-σ : ℝ) := by
  intro σ₁ σ₂ hσ
  by_cases h1 : a = 1
  · simp [h1]
  · have hgt : (1 : ℝ) < a := lt_of_le_of_ne ha (Ne.symm h1)
    have hkey : (a : ℝ) ^ (-σ₂ : ℝ) ≤ a ^ (-σ₁ : ℝ) := by
      refine Real.rpow_le_rpow_left_iff hgt |>.2 ?_
      linarith
    exact hkey

-- ============================================================================
-- SECTION 6: Key Bounds for Spectral Radius
-- ============================================================================

/-- For n ≥ 0, x ≥ 0, σ > 0: (n + 1 + x)^{-σ} ≤ (n + 1)^{-σ}
(bigger base, negative exponent → smaller value). -/
lemma inverse_pow_monotone_x (n : ℕ) (x : ℝ) (σ : ℝ) (hx : 0 ≤ x) (hσ : 0 < σ) :
    ((n : ℝ) + 1 + x) ^ (-σ : ℝ) ≤ ((n : ℝ) + 1) ^ (-σ : ℝ) := by
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have h1 : (0 : ℝ) ≤ (n : ℝ) + 1 := by linarith
  have h2 : (0 : ℝ) ≤ (n : ℝ) + 1 + x := by linarith
  rw [Real.rpow_neg h1, Real.rpow_neg h2,
    inv_le_inv₀ (Real.rpow_pos_of_pos (by linarith) _) (Real.rpow_pos_of_pos (by linarith) _)]
  exact Real.rpow_le_rpow h1 (by linarith) (le_of_lt hσ)

/-- For σ > 1, the partial sums of (n+1)^{-σ} are uniformly bounded. -/
theorem sum_bound_for_sigma_gt_one (σ : ℝ) (hσ : 1 < σ) :
    ∃ M : ℝ, ∀ n : ℕ, ∑ i ∈ Finset.range n, ((i : ℝ) + 1) ^ (-σ : ℝ) ≤ M := by
  sorry -- Fleet 3: `Real.summable_nat_rpow` + partial-sum boundedness

-- ============================================================================
-- SECTION 7: Basic Facts About the Unit Interval
-- ============================================================================

/-- 0 ∈ [0,1]. -/
theorem zero_in_Icc : (0 : ℝ) ∈ Icc (0 : ℝ) 1 := by simp

/-- 1 ∈ [0,1]. -/
theorem one_in_Icc : (1 : ℝ) ∈ Icc (0 : ℝ) 1 := by simp

/-- Membership in [0,1] unfolds to two inequalities. -/
theorem mem_Icc_zero_one (x : ℝ) (hx : x ∈ Icc (0 : ℝ) 1) : 0 ≤ x ∧ x ≤ 1 := by
  simpa using hx

end Riemann.TransferOperator
