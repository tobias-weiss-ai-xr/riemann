/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.Normed.Module.Basic
import Mathlib.Topology.Algebra.Ring.Real
import Mathlib.Data.Real.Basic
import Mathlib.Algebra.Order.Floor.Ring
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Riemann.GaussMapCompilable

/-!
# Basic Definitions for Transfer Operator Proof

This file defines the fundamental mathematical objects needed for the
transfer operator proof of the Riemann Hypothesis.

## Main Definitions

* `Interval.zeroOne`: The unit interval [0,1]
* `gaussMap`: The Gauss map g: [0,1) → [0,1) (alias for `Riemann.GaussMapCompilable.gaussMap`)
* `inverseBranch`: The inverse branches g_n(x) = 1/(n+x) for n ≥ 1
* `potential`: The potential function φ_s(x) = -2s log|x|
* `discretization`: The uniform grid of N+1 points in [0,1]
-/

open Set

namespace Riemann.TransferOperator

-- ============================================================================
-- SECTION 1: Basic Spaces and Notation
-- ============================================================================

/-- The closed unit interval [0,1] as a type synonym for clarity. -/
def Interval.zeroOne := Set.Icc (0 : ℝ) 1

/-- The open unit interval (0,1). -/
def Interval.zeroOne_open := Set.Ioo (0 : ℝ) 1

/-- The half-open unit interval [0,1). -/
def Interval.zeroOne_closed_open := Set.Ico (0 : ℝ) 1

-- ============================================================================
-- SECTION 2: Gauss Map (alias to the verified `Riemann.GaussMap`)
-- ============================================================================

/-- The Gauss map g: [0,1) → [0,1).

For x ∈ (0,1), g(x) = 1/x - floor(1/x). For x = 0, g(0) = 0 by convention.
This is an alias for the verified development in `Riemann.GaussMapCompilable`. -/
noncomputable def gaussMap : ℝ → ℝ := Riemann.GaussMap.gaussMap

-- ============================================================================
-- SECTION 3: Properties of the Gauss Map
-- ============================================================================

namespace GaussMap

variable {x : ℝ}

/-- The Gauss map at zero. -/
theorem at_zero : gaussMap 0 = 0 := by
  simp [gaussMap, Riemann.GaussMap.gaussMap]

/-- The Gauss map for 0 < x < 1. -/
theorem apply (hx₁ : 0 < x) (hx₂ : x < 1) :
    gaussMap x = (1 / x) - ⌊1 / x⌋ := by
  rw [gaussMap]
  exact Riemann.GaussMap.gaussMap_eq_of_pos_le_one ⟨hx₁, hx₂.le⟩

/-- The Gauss map maps [0,1) into [0,1). -/
theorem maps_to_zeroOne (hx₁ : 0 ≤ x) (hx₂ : x < 1) :
    gaussMap x ∈ Interval.zeroOne_closed_open := by
  by_cases hx0 : x = 0
  · rw [hx0, at_zero]
    exact ⟨le_refl 0, zero_lt_one⟩
  · have hx' : 0 < x := lt_of_le_of_ne hx₁ (Ne.symm hx0)
    rw [apply hx' hx₂]
    exact ⟨Int.fract_nonneg _, Int.fract_lt_one _⟩

end GaussMap

-- ============================================================================
-- SECTION 4: Inverse Branches
-- ============================================================================

/-- The inverse branches of the Gauss map: g_n(x) = 1/(n + x) for n ≥ 1.

Each g_n is a contraction mapping from [0,1] to (0,1/n] ⊆ [0,1]. -/
noncomputable def inverseBranch (n : ℕ+) : ℝ → ℝ :=
  fun x => 1 / ((n : ℝ) + x)

namespace InverseBranch

variable {n : ℕ+} {x y : ℝ}

/-- The inverse branch maps [0,1] into (0, 1/n]. -/
theorem maps_to_Icc (hx : 0 ≤ x ∧ x ≤ 1) :
    0 < inverseBranch n x ∧ inverseBranch n x ≤ 1 / (n : ℝ) := by
  have hn : (0 : ℝ) < (n : ℝ) := by exact_mod_cast n.pos
  refine ⟨div_pos one_pos (by linarith), ?_⟩
  rw [inverseBranch]
  exact (div_le_div_iff₀ (by linarith) hn).2 (by linarith)

/-- The derivative of the inverse branch: g_n'(x) = -1/(n+x)². -/
theorem deriv_eq (hx : x ≠ -↑n) :
    deriv (inverseBranch n) x = -1 / ((n : ℝ) + x) ^ 2 := by
  have hn : (0 : ℝ) < (n : ℝ) := by exact_mod_cast n.pos
  have hne : ((n : ℝ) + x) ≠ 0 := by
    intro h
    apply hx
    linarith
  have hfun : inverseBranch n = fun y => ((n : ℝ) + y)⁻¹ := by
    funext y
    simp [inverseBranch]
  have hd : DifferentiableAt ℝ (fun y : ℝ => (n : ℝ) + y) x :=
    (differentiableAt_const _).add differentiableAt_id
  rw [hfun, deriv_fun_inv'' hd hne, deriv_const_add_id]

/-- The contraction estimate: |g_n'(x)| < 1 on the interior x > 0.
(Corrected from the original `0 ≤ x`: at n = 1, x = 0 the derivative
equals exactly 1, so strict inequality needs the interior.) -/
theorem abs_deriv_lt_one (hx : 0 < x) :
    |deriv (inverseBranch n) x| < 1 := by
  have hx2 : x ≠ -↑n := by
    intro h
    linarith
  rw [deriv_eq hx2]
  -- -1/(n+x)² < 0, so |·| = 1/(n+x)²
  have hpos : (0 : ℝ) < (n : ℝ) + x := by
    have hn : (0 : ℝ) < (n : ℝ) := by exact_mod_cast n.pos
    linarith
  have hsquare : (0 : ℝ) < ((n : ℝ) + x) ^ 2 := sq_pos_of_pos hpos
  have hpos1 : (0 : ℝ) < 1 / ((n : ℝ) + x) ^ 2 := div_pos one_pos hsquare
  have habs : |-(1 : ℝ) / ((n : ℝ) + x) ^ 2| = 1 / ((n : ℝ) + x) ^ 2 := by
    rw [neg_div, abs_neg, abs_of_pos hpos1]
  rw [habs]
  -- 1/(n+x)² < 1 since (n+x)² > 1
  have hgt : (1 : ℝ) < ((n : ℝ) + x) ^ 2 := by
    have hn1 : (1 : ℝ) ≤ (n : ℝ) := by
      obtain ⟨k, hk⟩ := n
      exact_mod_cast hk
    have hsum : (1 : ℝ) < (n : ℝ) + x := by linarith
    nlinarith
  rwa [div_lt_one hsquare]

end InverseBranch

-- ============================================================================
-- SECTION 5: Potential Function
-- ============================================================================

/-- The potential function φ_s: (0,1] → ℂ for the Gauss map.

For the Riemann zeta connection, we use φ_s(x) = -2s · log|x|.
This potential arises from the connection to the zeta function via
the Euler product formula. -/
noncomputable def potential (s : ℂ) (x : ℝ) : ℂ := -2 * s * Real.log |x|

namespace Potential

variable {s : ℂ} {x : ℝ}

/-- The potential vanishes at x = 1. -/
theorem at_one : potential s 1 = 0 := by
  simp [potential]

/-- The potential is real-valued for real s and positive x. -/
theorem real_valued (hs : s.im = 0) (_hx : x > 0) :
    (potential s x).im = 0 := by
  have hs' : s = ((s.re : ℝ) : ℂ) := by
    rw [← Complex.re_add_im s, hs]
    simp
  rw [potential, hs']
  simp [Complex.mul_im]

/-- The potential is analytic in s for fixed x > 0. -/
theorem analytic_in_s (hx : x > 0) :
    ContDiff ℂ (⊤ : ℕ∞) (fun s : ℂ => potential s x) := by
  sorry -- Fleet 4: differentiability of s ↦ -2s·log|x| in s (affine in s!)

end Potential

-- ============================================================================
-- SECTION 6: Discretization of the Unit Interval
-- ============================================================================

/-- Uniform discretization of [0,1] into N+1 points k/N. -/
noncomputable def discretization (N : ℕ) : Finset ℝ :=
  (Finset.range (N + 1)).image fun k : ℕ => (k : ℝ) / (N : ℝ)

end Riemann.TransferOperator
