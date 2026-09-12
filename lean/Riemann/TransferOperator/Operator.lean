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
import Mathlib.Analysis.SpecialFunctions.Pow.Continuity
import Mathlib.Topology.ContinuousMap.Algebra
import Mathlib.Topology.ContinuousMap.Compact
import Riemann.TransferOperator.GaussMap
import Riemann.TransferOperator.BasicProofs

/-!
# Transfer Operator

## Main Definitions

- `FunctionSpace`: C([0,1], ℂ) with sup norm
- `transferOperatorWeight s n x`: the branch weight (n+1+x)^{-2s}
- `transferOperatorSummand s f n x`: the partial sum (finite n), well-defined unconditionally
- `transferOperatorBounded s`: L_s as a continuous linear map (proven here)
- `inverseBranchCm n`, `transferOperatorWeightCm s n`, `transferOperatorSummandCm s f n`:
  the continuous-map (in x) versions of the summand, on which the M-test is run

## Main Theorems

- `transferOperatorBounded`: the bounded linear operator L_s, assembled from the
  uniformly convergent series (the M-test: `Summable` of the sup norms)
- `transferOperatorBounded_apply`: the pointwise action formula
- `transferOperator_uniform_convergence`: partial sums converge to L_s f in the
  sup norm (uniform convergence in x) — the analytic content of the compactness
  pursuit, which is mathematically false on C([0,1], ℂ); see the note below

## A note on compactness

The original compactness goal `IsCompactOperator (transferOperatorBounded s hs)` is
FALSE on `C([0,1], ℂ)` and is therefore replaced here by the true statement
`transferOperator_uniform_convergence`.

Reason: the n = 0 branch term `T₀ f (x) = (1+x)^{-2s} · f(1/(1+x))` already
maps the unit ball of C([0,1]) into a non-precompact set. Since
`x ↦ 1/(1+x)` is a homeomorphism [0,1] → [1/2,1], the family
`{x ↦ (1+x)^{-2s} sin(2π k/(1+x))}ₖ` (arising from fₖ(x) = sin(2π k x),
‖fₖ‖ = 1) consists of functions oscillating at frequency ~k near 0 with a
uniformly nonzero weight, hence has no uniformly convergent subsequence (it is
not equicontinuous). By Arzelà–Ascoli this contradicts relative compactness of
`L_s '' (ball 0 1)`, i.e. `IsCompactOperator` fails. (This is the well-known
phenomenon that Ruelle transfer operators are compact on holomorphic/Lipschitz
classes — e.g. Mayer's disc-algebra setting — but not on the plain continuous
functions.) The genuinely provable and useful content, uniform convergence of
the Ruelle series, is what `transferOperator_uniform_convergence` records.
-/

namespace Riemann.TransferOperator

noncomputable section

open Complex BigOperators
open scoped ContinuousMap Topology

/-- The unit interval [0,1] as a type. -/
abbrev UnitInterval := Set.Icc (0 : ℝ) 1

/-- The function space: C([0,1], ℂ) with sup norm. -/
abbrev FunctionSpace := C(UnitInterval, ℂ)

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

/-! ## Continuous-map summands (M-test scaffolding) -/

/-- The n-th inverse branch as a continuous self-map of [0,1]. -/
noncomputable def inverseBranchCm (n : ℕ) : C(UnitInterval, UnitInterval) :=
  ⟨fun x => ⟨inverseBranchN n (x : ℝ), mem_Icc_of_branch n x⟩, by
    refine Continuous.subtype_mk (p := fun r : ℝ => r ∈ Set.Icc (0 : ℝ) 1)
      (f := fun x : UnitInterval => inverseBranchN n (x : ℝ)) ?_
      (fun x => mem_Icc_of_branch n x)
    refine (inverseBranchN_continuous n).comp_continuous ?_ ?_
    · exact continuous_subtype_val
    · intro x
      exact x.2.1
  ⟩

/-- The n-th branch weight as a continuous function of x ∈ [0,1]. -/
noncomputable def transferOperatorWeightCm (s : ℂ) (n : ℕ) : C(UnitInterval, ℂ) :=
  ⟨fun x => transferOperatorWeight s n (x : ℝ), by
    refine continuous_iff_continuousAt.mpr ?_
    intro x
    unfold transferOperatorWeight
    have hbr : Continuous fun x : UnitInterval => ((n : ℝ) + 1 + (x : ℝ) : ℝ) := by
      exact (continuous_const : Continuous fun _ : UnitInterval => ((n : ℝ) + 1 : ℝ)).add
        continuous_subtype_val
    have hb : Continuous fun x : UnitInterval => (((n : ℝ) + 1 + (x : ℝ) : ℝ) : ℂ) :=
      Complex.continuous_ofReal.comp hbr
    have hc : ContinuousAt
        (fun x : UnitInterval => (((n : ℝ) + 1 + (x : ℝ) : ℝ) : ℂ) ^ (-2 * s)) x := by
      refine ContinuousAt.cpow hb.continuousAt continuousAt_const ?_
      rw [Complex.mem_slitPlane_iff]
      left
      have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
      have hx0 : (0 : ℝ) ≤ (x : ℝ) := x.2.1
      have hz : (0 : ℝ) < (n : ℝ) + 1 + (x : ℝ) := by linarith
      simpa using hz
    exact hc
  ⟩

/-- The n-th summand as a continuous function of x (the M-test summand). -/
noncomputable def transferOperatorSummandCm (s : ℂ) (f : FunctionSpace) (n : ℕ) :
    FunctionSpace :=
  transferOperatorWeightCm s n * (f.comp (inverseBranchCm n))

/-- The pointwise value of the continuous-map summand agrees with the original. -/
theorem transferOperatorSummandCm_apply (s : ℂ) (f : FunctionSpace) (n : ℕ)
    (x : UnitInterval) :
    transferOperatorSummandCm s f n x = transferOperatorSummand s f n x := by
  unfold transferOperatorSummandCm transferOperatorWeightCm inverseBranchCm
  rfl

/-- Monotonicity of the weight in x: for x ∈ [0,1] the norm is dominated by its
value at x = 0 (analysis content of the uniform M-test bound). -/
theorem transferOperatorWeight_norm_mono (s : ℂ) (hs : 1 / 2 < s.re) (n : ℕ)
    (x : UnitInterval) :
    ‖transferOperatorWeight s n (x : ℝ)‖ ≤ ‖transferOperatorWeight s n 0‖ := by
  have hx0 : (0 : ℝ) ≤ (x : ℝ) := x.2.1
  have hpos : ∀ t : ℝ, 0 ≤ t → 0 < (n : ℝ) + 1 + t := fun t ht => by
    have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
    linarith
  have hnorm : ∀ t : ℝ, 0 ≤ t → ‖transferOperatorWeight s n t‖ =
      ((n : ℝ) + 1 + t) ^ (-2 * s.re) := by
    intro t ht
    rw [transferOperatorWeight, Complex.norm_cpow_eq_rpow_re_of_pos (hpos t ht)]
    congr 1
    simp
  rw [hnorm (x : ℝ) hx0, hnorm 0 (by norm_num)]
  have hmono := inverse_pow_monotone_x n (x : ℝ) (2 * s.re) hx0 (by linarith)
  rw [show (-(2 * s.re) : ℝ) = -2 * s.re by ring] at hmono
  simpa using hmono

/-- The sup norm of the n-th weight function is bounded by its value at 0. -/
theorem transferOperatorWeightCm_norm_le (s : ℂ) (hs : 1 / 2 < s.re) (n : ℕ) :
    ‖transferOperatorWeightCm s n‖ ≤ ‖transferOperatorWeight s n 0‖ := by
  exact (ContinuousMap.norm_le (transferOperatorWeightCm s n) (norm_nonneg _)).2 (by
    intro x
    simpa [transferOperatorWeightCm] using transferOperatorWeight_norm_mono s hs n x)

/-- Composition by a continuous map of the interval cannot increase the sup norm. -/
lemma continuousMap_comp_norm_le (f : FunctionSpace) (g : C(UnitInterval, UnitInterval)) :
    ‖f.comp g‖ ≤ ‖f‖ := by
  exact (ContinuousMap.norm_le (f.comp g) (norm_nonneg _)).2 (by
    intro x
    simpa using (ContinuousMap.norm_coe_le_norm f (g x) : ‖f (g x)‖ ≤ ‖f‖))

/-- The uniform (sup-norm) bound on each summand: ‖wₙ·(f∘Iₙ)‖ ≤ ‖wₙ(0)‖·‖f‖. -/
theorem transferOperatorSummandCm_norm_le (s : ℂ) (hs : 1 / 2 < s.re) (f : FunctionSpace)
    (n : ℕ) :
    ‖transferOperatorSummandCm s f n‖ ≤ ‖transferOperatorWeight s n 0‖ * ‖f‖ := by
  calc
    ‖transferOperatorSummandCm s f n‖
        = ‖transferOperatorWeightCm s n * (f.comp (inverseBranchCm n))‖ := rfl
    _ ≤ ‖transferOperatorWeightCm s n‖ * ‖f.comp (inverseBranchCm n)‖ := norm_mul_le _ _
    _ ≤ ‖transferOperatorWeightCm s n‖ * ‖f‖ :=
        mul_le_mul_of_nonneg_left (continuousMap_comp_norm_le f _) (norm_nonneg _)
    _ ≤ ‖transferOperatorWeight s n 0‖ * ‖f‖ :=
        mul_le_mul_of_nonneg_right (transferOperatorWeightCm_norm_le s hs n) (norm_nonneg _)

/-- The sup norms of the summands are summable (the M-test): for Re s > 1/2 the
series of `‖wₙ(0)‖·‖f‖` converges and dominates every summand. -/
theorem transferOperatorSummandCm_norm_summable (s : ℂ) (hs : 1 / 2 < s.re)
    (f : FunctionSpace) :
    Summable fun n : ℕ => ‖transferOperatorSummandCm s f n‖ :=
  Summable.of_nonneg_of_le (fun n => norm_nonneg _)
    (transferOperatorSummandCm_norm_le s hs f)
    (Summable.mul_right ‖f‖ (transferOperator_weight_norm_summable s 0 (by norm_num) hs))

/-- The summands themselves are summable as continuous maps (C([0,1], ℂ) is complete). -/
theorem transferOperatorSummandCm_summable (s : ℂ) (hs : 1 / 2 < s.re) (f : FunctionSpace) :
    Summable fun n : ℕ => transferOperatorSummandCm s f n :=
  (transferOperatorSummandCm_norm_summable s hs f).of_norm

/-- Bounded-operator construction: L_s on C([0,1], ℂ).

`(L_s f)(x) = ∑' n, wₙ(x)·f(Iₙ(x))`, assembled via the M-test
(`transferOperatorSummandCm_norm_summable`) and `LinearMap.mkContinuous`,
with operator norm ≤ `∑' n, ‖wₙ(0)‖`. -/
noncomputable def transferOperatorBounded (s : ℂ) (hs : 1 / 2 < s.re) :
    FunctionSpace →L[ℂ] FunctionSpace := by
  have hsum : ∀ f : FunctionSpace, Summable fun n : ℕ => transferOperatorSummandCm s f n :=
    fun f => transferOperatorSummandCm_summable s hs f
  have hnorm : ∀ f : FunctionSpace, Summable fun n : ℕ => ‖transferOperatorSummandCm s f n‖ :=
    fun f => transferOperatorSummandCm_norm_summable s hs f
  let op (f : FunctionSpace) : FunctionSpace := ∑' n : ℕ, transferOperatorSummandCm s f n
  have hold : ∀ f : FunctionSpace, ‖op f‖ ≤ (∑' n : ℕ, ‖transferOperatorWeight s n 0‖) * ‖f‖ := by
    intro f
    calc
      ‖op f‖ ≤ ∑' n : ℕ, ‖transferOperatorSummandCm s f n‖ := norm_tsum_le_tsum_norm (hnorm f)
      _ ≤ ∑' n : ℕ, ‖transferOperatorWeight s n 0‖ * ‖f‖ :=
          (hnorm f).tsum_le_tsum (transferOperatorSummandCm_norm_le s hs f)
            (Summable.mul_right ‖f‖ (transferOperator_weight_norm_summable s 0 (by norm_num) hs))
      _ = (∑' n : ℕ, ‖transferOperatorWeight s n 0‖) * ‖f‖ :=
          (transferOperator_weight_norm_summable s 0 (by norm_num) hs).tsum_mul_right ‖f‖
  let lin : FunctionSpace →ₗ[ℂ] FunctionSpace :=
  { toFun := op
    map_add' := by
      intro f g
      unfold op
      rw [← (hsum f).tsum_add (hsum g)]
      apply tsum_congr
      intro n
      ext x
      unfold transferOperatorSummandCm
      simp [mul_add]
    map_smul' := by
      intro a f
      ext x
      unfold op
      change (∑' n : ℕ, transferOperatorSummandCm s (a • f) n) x =
        (a • (∑' n : ℕ, transferOperatorSummandCm s f n)) x
      rw [← ContinuousMap.tsum_apply (hsum (a • f)) x]
      rw [show (a • (∑' n : ℕ, transferOperatorSummandCm s f n)) x =
          a • ((∑' n : ℕ, transferOperatorSummandCm s f n) x) by simp [smul_eq_mul]]
      rw [← ContinuousMap.tsum_apply (hsum f) x]
      calc
        (∑' n : ℕ, (transferOperatorSummandCm s (a • f) n) x)
            = ∑' n : ℕ, a * (transferOperatorSummandCm s f n) x := by
              apply tsum_congr
              intro n
              unfold transferOperatorSummandCm
              simp [smul_eq_mul, mul_comm, mul_left_comm]
        _ = a * (∑' n : ℕ, (transferOperatorSummandCm s f n) x) := by
              rw [tsum_mul_left]
        _ = a • (∑' n : ℕ, (transferOperatorSummandCm s f n) x) := by
              simp [smul_eq_mul]
  }
  exact LinearMap.mkContinuous lin (∑' n : ℕ, ‖transferOperatorWeight s n 0‖) hold

/-- `L_s f` is the infinite sum of the continuous-map summands (tsum equation). -/
theorem transferOperatorBounded_tsum (s : ℂ) (hs : 1 / 2 < s.re) (f : FunctionSpace) :
    (∑' n : ℕ, transferOperatorSummandCm s f n) = transferOperatorBounded s hs f := by
  simp [transferOperatorBounded]

/-- Pointwise action formula: `(L_s f)(x) = ∑' n, transferOperatorSummand s f n x`. -/
theorem transferOperatorBounded_apply (s : ℂ) (hs : 1 / 2 < s.re) (f : FunctionSpace)
    (x : UnitInterval) :
    transferOperatorBounded s hs f x = ∑' n : ℕ, transferOperatorSummand s f n x := by
  rw [← transferOperatorBounded_tsum s hs f]
  rw [← ContinuousMap.tsum_apply (transferOperatorSummandCm_summable s hs f) x]
  apply tsum_congr
  intro n
  exact transferOperatorSummandCm_apply s f n x

/-- Uniform convergence of the Ruelle series: the partial sums
`∑ i < N, wᵢ·(f∘Iᵢ)` converge to `L_s f` in the sup norm of C([0,1], ℂ),
uniformly in x.

This *is* the analytic content that a compactness claim was meant to capture
(see the module docstring: `IsCompactOperator` fails on `C([0,1], ℂ)`, so the
corrected statement records the guaranteed convergence instead). -/
theorem transferOperator_uniform_convergence (s : ℂ) (hs : 1 / 2 < s.re)
    (f : FunctionSpace) :
    Filter.Tendsto (fun N : ℕ => ∑ i ∈ Finset.range N, transferOperatorSummandCm s f i)
      Filter.atTop (𝓝 (transferOperatorBounded s hs f)) := by
  rw [← transferOperatorBounded_tsum s hs f]
  exact (transferOperatorSummandCm_summable s hs f).hasSum.tendsto_sum_nat

end -- noncomputable section

end Riemann.TransferOperator
