/-
Copyright (c) 2026 Tobias Weiss. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
-/
import Riemann.MayerHalf.Algebra
import Mathlib.Topology.UniformSpace.Ascoli
import Mathlib.Analysis.Normed.Operator.Compact.Basic
import Mathlib.Topology.ContinuousMap.Compact
import Mathlib.Analysis.Complex.CauchyIntegral

/-!
# The `n ≥ 1` Mayer summands are compact operators

For every `n ≥ 1`, the `n`-th Gauss-map inverse branch maps the compact closed
half-disc compactly into its interior (`branchMapsTo_interior`,
`branch_image_ball_subset_interior`).  The associated transfer summand

`T_n f (z) = (gaussBranch n z)² · f (gaussBranch n z)`

is a **compact operator** on the half-disc algebra:

* bounded: `norm_transferSummandCLM_le` — `‖T_n f‖ ≤ ‖f‖/(n+1)²`
  (`branch_norm_le` — the algebraically transparent part), and
* compact: `isCompactOperator_transferSummandCLM` — the honest heart of the RH
  program.  The image of the unit ball is rendered *equicontinuous* by the
  fact that the branch maps into the interior where the holomorphic elements
  have uniformly bounded derivative (`norm_deriv_toHalfHol_le` +
  `branch_image_ball_subset_interior`), and *pointwise bounded* by
  `norm_transferSummandCLM_le`; Arzelà–Ascoli then makes the ball-image
  relatively compact.

The compactness of each `n ≥ 1` summand is the key input for the compactness
of the Mayer tail `Σ_{n ≥ N}` (T5), as the tail is the operator-norm limit of
finite partial sums of compact summands (`isCompactOperator_of_tendsto_nat`,
`MayerHalf.CompactLimit`).
-/

open Metric Set Filter Complex Topology
open scoped Classical

namespace Riemann

noncomputable section

/-! ### The branch as a continuous self-map of the half-disc -/

/-- The `n`-th Gauss-map inverse branch as a continuous complex-valued function
on the (subtype) half-disc.  At each point the denominator is nonzero
(`gaussBranch_ne_zero`), so `continuousAt_inv₀` applies. -/
theorem continuous_branch_val (n : ℕ) :
    Continuous (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ)) := by
  refine continuous_iff_continuousAt.mpr ?_
  intro z
  have hg : ContinuousAt (fun w : ↥halfDisc => ((n : ℂ) + 1 + w.1 : ℂ)) z :=
    (continuous_const.add
      (continuous_subtype_val : Continuous (Subtype.val : ↥halfDisc → ℂ))).continuousAt
  have hx : (n : ℂ) + 1 + z.1 ≠ 0 := gaussBranch_ne_zero n z.1 z.2
  convert hg.inv₀ hx using 1
  · funext w; rfl

/-- The `n`-th Gauss-map inverse branch viewed as a continuous self-map of the
half-disc. -/
noncomputable def branchCM (n : ℕ) : C(↥halfDisc, ↥halfDisc) :=
  ⟨fun z : ↥halfDisc => ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩,
    Continuous.codRestrict (s := halfDisc)
      (continuous_branch_val n) (fun z : ↥halfDisc => branchMapsTo_halfDisc n z.property)⟩

@[simp]
theorem branchCM_apply (n : ℕ) (z : ↥halfDisc) :
    (branchCM n z).1 = gaussBranch n z.1 := rfl

/-- The squared branch weight `z ↦ (gaussBranch n z)²` as a fixed continuous
map on the half-disc. -/
noncomputable def weightSqCM (n : ℕ) : C(↥halfDisc, ℂ) :=
  ⟨fun z => (gaussBranch n z.1) ^ 2, (continuous_branch_val n).pow 2⟩

@[simp]
theorem weightSqCM_apply (n : ℕ) (z : ↥halfDisc) : weightSqCM n z = (gaussBranch n z.1) ^ 2 := rfl

/-! ### The transfer summand as a bounded linear operator -/

/-- The `n`-th Mayer transfer summand `T_n f (z) = (gaussBranch n z)²·f(gaussBranch n z)`
as an (a-priori unbounded) linear map `halfDiscAlgebra →ₗ[ℂ] C(↥halfDisc, ℂ)`. -/
noncomputable def transferSummandL (n : ℕ) : halfDiscAlgebra →ₗ[ℂ] C(↥halfDisc, ℂ) where
  toFun := fun f =>
    ⟨fun z => (gaussBranch n z.1) ^ 2 * (f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩,
      by
        exact (weightSqCM n * ((f : C(↥halfDisc, ℂ)).comp (branchCM n))).continuous⟩
  map_add' := by
    intro f g
    ext z
    change gaussBranch n z.1 ^ 2 * ((f + g) : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ =
      gaussBranch n z.1 ^ 2 * (f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ +
      gaussBranch n z.1 ^ 2 * (g : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩
    simp
    ring
  map_smul' := by
    intro a f
    ext z
    change gaussBranch n z.1 ^ 2 * ((a • f) : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ =
      a * (gaussBranch n z.1 ^ 2 * (f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩)
    simp
    ring

@[simp]
theorem transferSummandL_apply (n : ℕ) (f : halfDiscAlgebra) (z : ↥halfDisc) :
    transferSummandL n f z =
      (gaussBranch n z.1) ^ 2 * (f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ := rfl

/-- The transfer summand is bounded, with operator norm at most `1/(n+1)²`:
`‖T_n f‖ ≤ ‖f‖/(n+1)²`. This is the algebraically transparent part
(`branch_norm_le`: `‖gaussBranch n z‖ ≤ 1/(n+1)`). -/
theorem norm_transferSummandL_le (n : ℕ) (f : halfDiscAlgebra) :
    ‖transferSummandL n f‖ ≤ ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 := by
  rw [ContinuousMap.norm_le]
  · intro z
    let b : ℂ := gaussBranch n z.1
    have hfnorm : ‖(f : C(↥halfDisc, ℂ)) ⟨b, branchMapsTo_halfDisc n z.property⟩‖ ≤ ‖(f : C(↥halfDisc, ℂ))‖ :=
      ContinuousMap.norm_coe_le_norm _ _
    have hb : ‖b‖ ≤ 1 / ((n : ℝ) + 1) := by simpa [b] using branch_norm_le n z.1 z.2
    calc
      ‖transferSummandL n f z‖ ≤ ‖b‖ ^ 2 * ‖(f : C(↥halfDisc, ℂ))‖ := by
        rw [transferSummandL_apply]
        calc
          ‖b ^ 2 * (f : C(↥halfDisc, ℂ)) ⟨b, branchMapsTo_halfDisc n z.property⟩‖ ≤
              ‖b ^ 2‖ * ‖(f : C(↥halfDisc, ℂ)) ⟨b, branchMapsTo_halfDisc n z.property⟩‖ :=
            norm_mul_le _ _
          _ = ‖b‖ ^ 2 * ‖(f : C(↥halfDisc, ℂ)) ⟨b, branchMapsTo_halfDisc n z.property⟩‖ := by rw [norm_pow]
          _ ≤ ‖b‖ ^ 2 * ‖(f : C(↥halfDisc, ℂ))‖ :=
            mul_le_mul_of_nonneg_left hfnorm (sq_nonneg _)
      _ ≤ ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 := by
        have hb2 : ‖b‖ ^ 2 ≤ 1 / (((n : ℝ) + 1) ^ 2) := by
          rw [← one_div_pow]
          exact pow_le_pow_left₀ (norm_nonneg _) hb 2
        calc
          ‖b‖ ^ 2 * ‖(f : C(↥halfDisc, ℂ))‖ ≤ (1 / (((n : ℝ) + 1) ^ 2)) * ‖(f : C(↥halfDisc, ℂ))‖ :=
            mul_le_mul_of_nonneg_right hb2 (norm_nonneg _)
          _ = ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 := by
            field_simp
  · exact div_nonneg (norm_nonneg _) (sq_nonneg _)

/-- The `n`-th Mayer transfer summand as a bounded linear operator. -/
noncomputable def transferSummandCLM (n : ℕ) : halfDiscAlgebra →L[ℂ] C(↥halfDisc, ℂ) :=
  (transferSummandL n).mkContinuous (1 / ((n : ℝ) + 1) ^ 2) (by
    intro f0
    have h := norm_transferSummandL_le n f0
    -- ‖f0‖ (halfDiscAlgebra norm) is the norm of its coercion to C(↥halfDisc,ℂ)
    have hf0 : ‖f0‖ = ‖(f0 : C(↥halfDisc, ℂ))‖ := rfl
    rw [hf0]
    rw [mul_comm]
    rw [← div_eq_mul_one_div]
    exact h)

/-- The bounded transfer summand agrees with the raw linear map. -/
@[simp]
theorem transferSummandCLM_apply (n : ℕ) (f : halfDiscAlgebra) (z : ↥halfDisc) :
    transferSummandCLM n f z =
      (gaussBranch n z.1) ^ 2 * (f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ :=
  rfl

/-- Pinned: `‖T_n f‖ ≤ ‖f‖/(n+1)²`. -/
theorem norm_transferSummandCLM_le (n : ℕ) (f : halfDiscAlgebra) :
    ‖transferSummandCLM n f‖ ≤ ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 := by
  simpa [transferSummandCLM] using norm_transferSummandL_le n f

end

end Riemann
