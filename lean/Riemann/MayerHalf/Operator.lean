/-
Copyright (c) 2026 Tobias Weiss. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
-/
import Riemann.MayerHalf.Algebra
import Mathlib.Analysis.PSeries
import Mathlib.Analysis.Normed.Operator.ContinuousLinearMap
import Mathlib.Topology.Algebra.InfiniteSum.Module
import Mathlib.Topology.Algebra.InfiniteSum.NatInt

/-!
# The Mayer transfer operator on the half-disc algebra

The **Mayer transfer operator** acts on the half-disc algebra `halfDiscAlgebra`
by summing over the Gauss-map inverse branches:

  `mayerOperatorCLM f = Σ' n, (gaussBranch n)² · (f ∘ gaussBranch n)`.

Each summand is a bounded continuous self-map of `C(↥halfDisc, ℂ)`
(`transferSummand`, `norm_transferSummand_le`), the series is summable in norm
(against the convergent weight series `mayerConstant = Σ' n, 1/(n+1)²`), and
the limit lands back in the closed complete subalgebra, giving a bounded
linear self-map `mayerOperatorCLM` with `‖mayerOperatorCLM f‖ ≤
mayerConstant · ‖f‖`.

This is the Riemann-hypothesis program's transfer-operator backbone; the
compactness of the tail (branches `n ≥ 1`) is the subject of the companion
modules (T3/T5).
-/

open Metric Set Filter Complex Topology
open scoped Classical

namespace Riemann

noncomputable section

/-! ### Interior points of the half-disc -/

/-- Interior points of the half-disc have positive real part. -/
theorem mem_interior_re_pos {z : ℂ} (hz : z ∈ interior halfDisc) : 0 < z.re := by
  obtain ⟨ε, hε0, hball⟩ := Metric.mem_nhds_iff.mp (IsOpen.mem_nhds isOpen_interior hz)
  have hw : z - (ε / 2 : ℝ) ∈ halfDisc := by
    refine interior_subset (hball ?_)
    rw [mem_ball, dist_eq_norm]
    have hsub : z - (ε / 2 : ℝ) - z = -((ε / 2 : ℝ) : ℂ) := by
      ring
    rw [hsub, norm_neg, Complex.norm_real, Real.norm_eq_abs, abs_of_pos (by linarith : (0 : ℝ) < ε / 2)]
    linarith
  have h1 : (0 : ℝ) ≤ (z - (ε / 2 : ℝ)).re := hw.2
  rw [sub_re, Complex.ofReal_re] at h1
  linarith

/-! ### The transfer summand -/

/-- The `n`-th summand of the Mayer operator: `(gaussBranch n)² · (f ∘ gaussBranch n)`
as a continuous function on the half-disc. -/
def transferSummand (n : ℕ) (f : C(↥halfDisc, ℂ)) : C(↥halfDisc, ℂ) where
  toFun := fun z => (gaussBranch n z.1) ^ 2 * f ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩
  continuous_toFun := by
    have hbranch : Continuous (fun z : ↥halfDisc => gaussBranch n z.1) := by
      have hbase : Continuous (fun z : ↥halfDisc => (n : ℂ) + 1 + z.1) :=
        continuous_const.add continuous_subtype_val
      exact hbase.inv₀ fun z => gaussBranch_ne_zero n z.1 z.2
    have hsq : Continuous (fun z : ↥halfDisc => (gaussBranch n z.1) ^ 2) :=
      hbranch.pow 2
    have hmk : Continuous (fun z : ↥halfDisc =>
        (⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ : ↥halfDisc)) :=
      Continuous.subtype_mk hbranch (fun z => branchMapsTo_halfDisc n z.2)
    exact hsq.mul (f.continuous.comp hmk)

/-- The norm of the `n`-th summand is bounded by `‖f‖ / ((n : ℝ) + 1)²`. -/
theorem norm_transferSummand_le (n : ℕ) (f : C(↥halfDisc, ℂ)) :
    ‖transferSummand n f‖ ≤ ‖f‖ / ((n : ℝ) + 1) ^ 2 := by
  rw [ContinuousMap.norm_le (transferSummand n f)
    (div_nonneg (norm_nonneg f) (by positivity))]
  intro z
  have hz : z.1 ∈ halfDisc := z.2
  have hnorm : ‖gaussBranch n z.1‖ ≤ 1 / ((n : ℝ) + 1) := branch_norm_le n z.1 hz
  have hposn : (0 : ℝ) < (n : ℝ) + 1 := by linarith [Nat.cast_nonneg (α := ℝ) n]
  have hsq : ‖(gaussBranch n z.1) ^ 2‖ ≤ (1 / ((n : ℝ) + 1)) ^ 2 := by
    rw [norm_pow]
    exact pow_le_pow_left₀ (norm_nonneg _) hnorm 2
  have hf : ‖f ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩‖ ≤ ‖f‖ :=
    ContinuousMap.norm_coe_le_norm f _
  have hmul :=
    (norm_mul_le ((gaussBranch n z.1) ^ 2) (f ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩))
  calc ‖(gaussBranch n z.1) ^ 2 * f ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩‖
      ≤ ‖(gaussBranch n z.1) ^ 2‖ * ‖f ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩‖ :=
        hmul
    _ ≤ (1 / ((n : ℝ) + 1)) ^ 2 * ‖f‖ := mul_le_mul hsq hf (norm_nonneg _) (by positivity)
    _ = ‖f‖ / ((n : ℝ) + 1) ^ 2 := by field_simp

/-! ### Branches map the interior into the interior -/

/-- Every Gauss-map inverse branch maps the interior of the half-disc into
itself — for **all** `n`, including `n = 0`. -/
theorem branch_interior (n : ℕ) (z : ℂ) (hz : z ∈ interior halfDisc) :
    gaussBranch n z ∈ interior halfDisc := by
  obtain ⟨ε, hε0, hball⟩ := Metric.mem_nhds_iff.mp (IsOpen.mem_nhds isOpen_interior hz)
  have hzre := mem_interior_re_pos hz
  have hzne : z ≠ 0 := fun hc => by rw [hc] at hzre; simp at hzre
  have hzpos : (0 : ℝ) < ‖z‖ := norm_pos_iff.mpr hzne
  set δ : ℝ := ε / 2 / ‖z‖ with hδ
  have hδpos : 0 < δ := div_pos (by linarith) hzpos
  have hw2 : z + (δ : ℂ) • z ∈ halfDisc := by
    refine interior_subset (hball ?_)
    rw [mem_ball, dist_eq_norm]
    have hsub : z + (δ : ℂ) • z - z = (δ : ℂ) • z := by
      ring
    rw [hsub, norm_smul, Complex.norm_real, Real.norm_eq_abs,
      abs_of_pos hδpos, hδ]
    field_simp
    norm_num
  have haddsmul : z + (δ : ℂ) • z = ((1 + δ : ℝ) : ℂ) • z := by
    have hcast : ((1 + δ : ℝ) : ℂ) = (1 : ℂ) + (δ : ℂ) := by simp
    rw [hcast, add_smul, one_smul]
  have hmem := hw2.1
  rw [mem_closedBall_zero_iff] at hmem
  rw [haddsmul, norm_smul, Complex.norm_real, Real.norm_eq_abs,
    abs_of_pos (by linarith : (0 : ℝ) < 1 + δ)] at hmem
  have hz1 : ‖z‖ < 1 := by nlinarith
  have hden : (1 : ℝ) < ‖((n : ℂ) + 1 + z)‖ := by
    have hre : ((n : ℂ) + 1 + z).re = (n : ℝ) + 1 + z.re := by
      simp [Complex.add_re, Complex.natCast_re]
    have hge : ((n : ℂ) + 1 + z).re ≤ ‖((n : ℂ) + 1 + z)‖ := by
      have hab := abs_re_le_norm ((n : ℂ) + 1 + z)
      have hpos : (0 : ℝ) ≤ ((n : ℂ) + 1 + z).re := by rw [hre]; linarith
      rw [abs_of_nonneg hpos] at hab
      exact hab
    rw [hre] at hge
    linarith
  have hnorm_branch : ‖gaussBranch n z‖ < 1 := by
    have hgd : gaussBranch n z = ((n : ℂ) + 1 + z)⁻¹ := rfl
    rw [hgd, norm_inv]
    exact inv_lt_one_of_one_lt₀ hden
  exact mem_interior_halfDisc (mem_ball_zero_iff.mpr hnorm_branch)
    (branch_re_pos n z (interior_subset hz))

/-! ### Membership of the summands in the half-disc algebra -/

/-- Each Mayer summand of an algebra element is again in the algebra: the
summand is holomorphic on the interior by the chain rule. -/
theorem transferSummandMem (n : ℕ) (f : halfDiscAlgebra) :
    transferSummand n (f : C(↥halfDisc, ℂ)) ∈ halfDiscAlgebra := by
  rw [mem_halfDiscAlgebra]
  have hfe := (mem_halfDiscAlgebra _).mp f.property
  have hv : DifferentiableOn ℂ (gaussBranch n) (interior halfDisc) := by
    intro w hw
    have hgd : gaussBranch n = fun w : ℂ => ((n : ℂ) + 1 + w)⁻¹ := rfl
    rw [hgd]
    have hre : (0 : ℝ) < ((n : ℂ) + 1 + w).re := by
      have h1 := mem_interior_re_pos hw
      simp only [Complex.add_re, Complex.natCast_re, Complex.one_re]
      linarith
    have hne : ((n : ℂ) + 1 + w) ≠ 0 := fun hc => by rw [hc] at hre; simp at hre
    have hd : DifferentiableAt ℂ (fun w : ℂ => (n : ℂ) + 1 + w) w := by fun_prop
    exact (DifferentiableAt.inv hd hne).differentiableWithinAt
  have hcomp : DifferentiableOn ℂ
      (toHalfHol (f : C(↥halfDisc, ℂ)) ∘ gaussBranch n) (interior halfDisc) :=
    hfe.comp hv (fun w hw => branch_interior n w hw)
  refine DifferentiableOn.congr (hv.pow 2 |>.mul hcomp) fun w hw => ?_
  simp only [Pi.mul_apply, Function.comp_apply]
  rw [toHalfHol_apply _ w (interior_subset hw),
    toHalfHol_apply _ (gaussBranch n w) (branchMapsTo_halfDisc n (interior_subset hw))]
  rfl

/-! ### Norm summability and the Mayer constant -/

/-- The Mayer weight series `Σ' n, 1/(n+1)²` converges. -/
theorem summable_mayerWeights : Summable fun n : ℕ => 1 / ((n : ℝ) + 1) ^ 2 := by
  have h : (1 : ℕ) < 2 := by norm_num
  have key := (summable_nat_add_iff (f := fun n : ℕ => 1 / (n : ℝ) ^ 2) 1).mpr
    (Real.summable_one_div_nat_pow.mpr h)
  simpa [Nat.cast_add] using key

/-- The summand norms are summable: `‖T_n f‖ ≤ ‖f‖/(n+1)²`. -/
theorem summable_transferSummand_norm (f : C(↥halfDisc, ℂ)) :
    Summable fun n : ℕ => ‖transferSummand n f‖ := by
  have hw : Summable fun n : ℕ => ‖f‖ / ((n : ℝ) + 1) ^ 2 := by
    have hfun : (fun n : ℕ => ‖f‖ / ((n : ℝ) + 1) ^ 2)
        = fun n : ℕ => ‖f‖ * (1 / ((n : ℝ) + 1) ^ 2) := by
      funext n; ring
    rw [hfun]
    exact Summable.const_smul ‖f‖ summable_mayerWeights
  exact Summable.of_nonneg_of_le (fun n => norm_nonneg _)
    (fun n => norm_transferSummand_le n f) hw

/-- The Mayer constant `Σ' n, 1/(n+1)² = π²/6`. -/
noncomputable def mayerConstant : ℝ := ∑' n : ℕ, 1 / ((n : ℝ) + 1) ^ 2

/-- The Mayer series of an algebra element converges back into the algebra
(the subalgebra is sequentially closed in `C(↥halfDisc, ℂ)`). -/
theorem mayerSum_mem (f : halfDiscAlgebra) :
    (∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ))) ∈ halfDiscAlgebra := by
  have hhasSum : HasSum (fun n : ℕ => transferSummand n (f : C(↥halfDisc, ℂ)))
      (∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ))) :=
    (Summable.of_norm (summable_transferSummand_norm _)).hasSum
  have htend := hhasSum.tendsto_sum_nat
  have pmem : ∀ k : ℕ,
      (∑ i ∈ Finset.range k, transferSummand i (f : C(↥halfDisc, ℂ))) ∈ halfDiscAlgebra := by
    intro k
    induction k with
    | zero => simp only [Finset.range_zero, Finset.sum_empty]; exact zero_mem halfDiscAlgebra
    | succ k ih =>
      rw [Finset.sum_range_succ]
      exact Subalgebra.add_mem _ ih (transferSummandMem k f)
  exact isSeqClosed_halfDiscAlgebra pmem htend

/-- Norm bound for the Mayer series: `‖Σ' T_n f‖ ≤ mayerConstant · ‖f‖`. -/
theorem norm_mayerSum_le (f : halfDiscAlgebra) :
    ‖∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ))‖
      ≤ mayerConstant * ‖(f : C(↥halfDisc, ℂ))‖ := by
  have h1 : ‖∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ))‖
      ≤ ∑' n : ℕ, ‖transferSummand n (f : C(↥halfDisc, ℂ))‖ :=
    norm_tsum_le_tsum_norm (summable_transferSummand_norm _)
  have h2 : Summable fun n : ℕ => ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 := by
    have hfun : (fun n : ℕ => ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2)
        = fun n : ℕ => ‖(f : C(↥halfDisc, ℂ))‖ * (1 / ((n : ℝ) + 1) ^ 2) := by
      funext n; ring
    rw [hfun]
    exact Summable.const_smul ‖(f : C(↥halfDisc, ℂ))‖ summable_mayerWeights
  have h3 : ∑' n : ℕ, ‖transferSummand n (f : C(↥halfDisc, ℂ))‖
      ≤ ∑' n : ℕ, ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 :=
    Summable.tsum_le_tsum (fun n => norm_transferSummand_le n _)
      (summable_transferSummand_norm _) h2
  have h4 : ∑' n : ℕ, ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2
      = ‖(f : C(↥halfDisc, ℂ))‖ * mayerConstant := by
    simp only [div_eq_mul_inv, tsum_mul_left]
    simp only [mayerConstant, one_div]
  refine h1.trans (h3.trans ?_)
  rw [h4, mul_comm]

/-! ### The Mayer operator -/

/-- The Mayer operator as a linear map on the half-disc algebra. -/
def mayerOperatorL : halfDiscAlgebra →ₗ[ℂ] halfDiscAlgebra where
  toFun f := ⟨∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ)), mayerSum_mem f⟩
  map_add' a b := by
    have hab : ∀ n : ℕ, transferSummand n ((a + b : halfDiscAlgebra) : C(↥halfDisc, ℂ))
        = transferSummand n (a : C(↥halfDisc, ℂ)) + transferSummand n (b : C(↥halfDisc, ℂ)) := by
      intro n
      ext z
      change (gaussBranch n z.1) ^ 2 *
        ((a + b : halfDiscAlgebra) : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ =
        (gaussBranch n z.1) ^ 2 * (a : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ +
        (gaussBranch n z.1) ^ 2 * (b : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩
      simp
      ring
    refine Subtype.ext ?_
    have hfun : (fun n : ℕ => transferSummand n ((a + b : halfDiscAlgebra) : C(↥halfDisc, ℂ)))
        = fun n : ℕ => transferSummand n (a : C(↥halfDisc, ℂ))
            + transferSummand n (b : C(↥halfDisc, ℂ)) := funext hab
    show (∑' n : ℕ, transferSummand n ((a + b : halfDiscAlgebra) : C(↥halfDisc, ℂ))) =
        (∑' n : ℕ, transferSummand n (a : C(↥halfDisc, ℂ)) +
          ∑' n : ℕ, transferSummand n (b : C(↥halfDisc, ℂ)))
    rw [hfun]
    exact (HasSum.add ((Summable.of_norm (summable_transferSummand_norm _)).hasSum)
      ((Summable.of_norm (summable_transferSummand_norm _)).hasSum)).tsum_eq
  map_smul' c a := by
    have hca : ∀ n : ℕ, transferSummand n ((c • a : halfDiscAlgebra) : C(↥halfDisc, ℂ))
        = c • transferSummand n (a : C(↥halfDisc, ℂ)) := by
      intro n
      ext z
      change (gaussBranch n z.1) ^ 2 *
        ((c • a : halfDiscAlgebra) : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ =
        c • ((gaussBranch n z.1) ^ 2 * (a : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩)
      simp
      ring
    refine Subtype.ext ?_
    have hfun : (fun n : ℕ => transferSummand n ((c • a : halfDiscAlgebra) : C(↥halfDisc, ℂ)))
        = fun n : ℕ => c • transferSummand n (a : C(↥halfDisc, ℂ)) := funext hca
    show (∑' n : ℕ, transferSummand n ((c • a : halfDiscAlgebra) : C(↥halfDisc, ℂ))) =
        (c • ∑' n : ℕ, transferSummand n (a : C(↥halfDisc, ℂ)))
    rw [hfun]
    exact Summable.tsum_const_smul c (Summable.of_norm (summable_transferSummand_norm _))

/-- The **Mayer transfer operator** on the half-disc algebra: the norm-convergent
sum over all Gauss-map inverse branches, with `‖mayerOperatorCLM f‖ ≤
mayerConstant · ‖f‖`. -/
noncomputable def mayerOperatorCLM : halfDiscAlgebra →L[ℂ] halfDiscAlgebra :=
  mayerOperatorL.mkContinuous mayerConstant (by
    intro f
    have h1 : ‖mayerOperatorL f‖
        = ‖∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ))‖ := rfl
    have h2 : ‖f‖ = ‖(f : C(↥halfDisc, ℂ))‖ := rfl
    rw [h1, h2]
    exact norm_mayerSum_le f)

/-- The operator-norm bound of the Mayer operator. -/
theorem norm_mayerOperatorCLM_le (f : halfDiscAlgebra) :
    ‖mayerOperatorCLM f‖ ≤ mayerConstant * ‖f‖ := by
  have h1 : ‖mayerOperatorCLM f‖
      = ‖∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ))‖ := rfl
  have h2 : ‖f‖ = ‖(f : C(↥halfDisc, ℂ))‖ := rfl
  rw [h1, h2]
  exact norm_mayerSum_le f

end

end Riemann
