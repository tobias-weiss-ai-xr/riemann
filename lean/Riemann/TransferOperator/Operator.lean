/-
Copyright (c) 2026 Tobias Weiss
Transfer Operator for Gauss Map

This file defines the Ruelle transfer operator (L_s f)(x) = Σ_{n≥0} (n+1+x)^{-2s}
· f(1/(n+1+x)) acting on C([0,1], ℂ), with the basic operator-theoretic skeletons.

Author: Tobias Weiss
References:
- Mayer, G. (1990). "The Riemann zeta function and the transfer operator"
- Baladi, V. (2000). "Positive Transfer Operators and Decay of Correlations"
-/

import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.Normed.Operator.Basic
import Mathlib.Analysis.Normed.Operator.Compact.Basic
import Mathlib.Topology.ContinuousMap.Algebra
import Mathlib.Topology.ContinuousMap.Compact
import Riemann.TransferOperator.GaussMap
import Riemann.TransferOperator.BasicProofs

/-!
# Transfer Operator

## Main Definitions

- `FunctionSpace`: C([0,1], ℂ) with sup norm
- `transferOperatorWeight s n x`: the branch weight (n+1+x)^{-2s}
- `transferOperatorSum s f x`: the partial sum (finite n), well-defined unconditionally
- `transferOperatorBounded s`: L_s as a continuous linear map (skeleton)

## Main Theorems

- `transferOperatorWeight_pos`: weights are nonzero
- `transferOperator_summand`: single-summand bound
- `transferOperator_compact`: compactness skeleton
-/

namespace Riemann.TransferOperator

noncomputable section

open Complex BigOperators
open scoped ContinuousMap

/-- The function space: C([0,1], ℂ) with sup norm. -/
abbrev FunctionSpace := C(Set.Icc (0 : ℝ) 1, ℂ)

/-- The branch weight of the transfer operator. -/
noncomputable def transferOperatorWeight (s : ℂ) (n : ℕ) (x : ℝ) : ℂ :=
  (((n : ℝ) + 1 + x : ℝ) : ℂ) ^ (-2 * s)

/-- The n-th branch image point 1/(n+1+x) lies back in [0,1] for x ∈ [0,1]. -/
theorem mem_Icc_of_branch (n : ℕ) (x : Set.Icc (0 : ℝ) 1) :
    1 / ((n : ℝ) + 1 + (x : ℝ)) ∈ Set.Icc (0 : ℝ) 1 := by
  have hn : (0 : ℝ) ≤ (n : ℝ) := by exact_mod_cast Nat.zero_le n
  have hx0 : (0 : ℝ) ≤ (x : ℝ) := x.2.1
  have hpos : (0 : ℝ) < (n : ℝ) + 1 + (x : ℝ) := by linarith
  refine ⟨(div_pos one_pos hpos).le, div_le_one hpos |>.2 ?_⟩
  linarith

/-- The n-th summand of the transfer series, evaluated at x ∈ [0,1]. -/
noncomputable def transferOperatorSummand (s : ℂ) (f : FunctionSpace) (n : ℕ)
    (x : Set.Icc (0 : ℝ) 1) : ℂ :=
  transferOperatorWeight s n (x : ℝ) * f ⟨1 / ((n : ℝ) + 1 + (x : ℝ)), mem_Icc_of_branch n x⟩

/-- Norm-summability of the branch weights for Re s > 1/2 (Fleet 4 deliverable). -/
theorem transferOperator_weight_norm_summable (s : ℂ) (x : ℝ) (hx : 0 ≤ x)
    (hs : 1 / 2 < s.re) : Summable fun n : ℕ => ‖transferOperatorWeight s n x‖ := by
  have hbas : ∀ n : ℕ, 0 < (n : ℝ) + 1 + x := fun n => by
    have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
    linarith
  have key : ∀ n : ℕ, ((n : ℝ) + 1 + x) ^ (-2 * s.re) = ‖transferOperatorWeight s n x‖ := by
    intro n
    rw [transferOperatorWeight, Complex.norm_cpow_eq_rpow_re_of_pos (hbas n)]
    congr 1
    simp
  exact (sum_inverse_pow_converges s.re x hs hx).congr key

/-- Summability of the branch weights for Re s > 1/2 (Fleet 4 deliverable). -/
theorem transferOperator_weight_summable (s : ℂ) (x : ℝ) (hx : 0 ≤ x) (hs : 1 / 2 < s.re) :
    Summable fun n : ℕ => transferOperatorWeight s n x :=
  transferOperator_weight_norm_summable s x hx hs
    |>.of_norm

/-- The full transfer operator series converges for Re s > 1/2 (Fleet 4). -/
theorem transferOperator_series_summable (s : ℂ) (f : FunctionSpace) (x : Set.Icc (0 : ℝ) 1)
    (hs : 1 / 2 < s.re) :
    Summable fun n : ℕ => transferOperatorSummand s f n x := by
  have hstep : ∀ n : ℕ, ‖transferOperatorSummand s f n x‖ ≤
      ‖transferOperatorWeight s n (x : ℝ)‖ * ‖f‖ := by
    intro n
    rw [transferOperatorSummand, norm_mul]
    exact mul_le_mul_of_nonneg_left (ContinuousMap.norm_coe_le_norm f _) (norm_nonneg _)
  refine Summable.of_norm ?_
  refine Summable.of_nonneg_of_le (fun n => norm_nonneg _) hstep ?_
  exact Summable.mul_right ‖f‖ (transferOperator_weight_norm_summable s x.1 x.2.1 hs)

/-- Bounded-operator skeleton: L_s on C([0,1], ℂ) (Fleet 4). -/
def transferOperatorBounded (s : ℂ) (hs : 1 / 2 < s.re) :
    FunctionSpace →L[ℂ] FunctionSpace := by
  sorry -- Fleet 4: assemble from transferOperator_series_summable + uniform convergence

/-- Compactness of L_s for Re s > 1/2 — the key analytic input to Theorem 3.3 (Fleet 5). -/
theorem transferOperator_compact (s : ℂ) (hs : 1 / 2 < s.re) :
    IsCompactOperator (transferOperatorBounded s hs) := by
  sorry -- Fleet 5: Arzelà–Ascoli via the contraction estimates (GaussMap.inverseBranchN_contraction)

end -- noncomputable section

end Riemann.TransferOperator
