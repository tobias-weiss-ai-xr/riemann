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
* compact: `isCompactOperator_transferSummandCLM` — **not yet proven**; the
  remaining gap in the RH program.  What IS proven here: the image of the
  unit ball is *equicontinuous* (`equicontinuous_transferSummand`, via the
  interior-branch MVT route with `norm_deriv_toHalfHol_le` +
  `branch_image_ball_subset_interior`) and *pointwise bounded* by
  `norm_transferSummandCLM_le` — both Arzelà–Ascoli hypotheses except the
  pointwise-compactness one.  Closing it needs the *normal-families* fact
  that a pointwise cluster limit of uniformly bounded holomorphic maps is
  holomorphic (Montel / Vitali–Porter); mathlib has neither, so the final
  Ascoli closure is deferred to phase 3.  Until then T5 states the tail
  compactness conditionally on `∀ n > 0, IsCompactOperator (summandOp n)`
  (`isCompactOperator_mayerTail`, `MayerHalf.TailCompact`), which is exactly
  the shape the classical proof has.

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
        refine Continuous.congr (weightSqCM n * ((f : C(↥halfDisc, ℂ)).comp (branchCM n))).continuous
          (fun z => rfl)⟩
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

/-! ### Arzelà–Ascoli: equicontinuity of the transfer family -/

/-- The uniform interior margin radius `1 / (2 · (n+2)²)` — same for every branch image. -/
noncomputable def r₀ (n : ℕ) : ℝ := 1 / (2 * ((n : ℝ) + 2) ^ 2)

theorem r₀_pos (n : ℕ) : 0 < r₀ n := by
  unfold r₀
  positivity

theorem r₀_nonneg (n : ℕ) : 0 ≤ r₀ n := le_of_lt (r₀_pos n)

/-- A ball of radius `r₀` around the branch image stays in the interior. -/
theorem branch_image_ball_subset_interior_r₀ (n : ℕ) (hn : 0 < n) (z : ℂ) (hz : z ∈ halfDisc) :
    ball (gaussBranch n z) (r₀ n) ⊆ interior halfDisc := by
  simpa [r₀] using branch_image_ball_subset_interior n hn z hz

/-- The supremum norm of the squared Gauss branch is at most `1` on the whole half-disc. -/
theorem branch_sq_norm_le_one (n : ℕ) (z : ↥halfDisc) :
    ‖(gaussBranch n z.1 : ℂ) ^ 2‖ ≤ 1 := by
  have hb : ‖gaussBranch n z.1‖ ≤ 1 := by
    have h : ‖gaussBranch n z.1‖ ≤ 1 / ((n : ℝ) + 1) := branch_norm_le n z.1 z.property
    have hp : (0 : ℝ) < (n : ℝ) + 1 := by linarith [Nat.cast_nonneg (α := ℝ) n]
    exact le_trans h (by rw [one_div, inv_le_one₀ hp]; linarith [Nat.cast_nonneg (α := ℝ) n])
  calc
    ‖(gaussBranch n z.1 : ℂ) ^ 2‖ = ‖gaussBranch n z.1‖ ^ 2 := by rw [norm_pow]
    _ ≤ 1 ^ 2 := pow_le_pow_left₀ (norm_nonneg _) hb 2
    _ = 1 := by norm_num

/-- **Uniform local Lipschitz bound.** The holomorphic half-disc-algebra family is
`(2M)/(r₀/2)`-Lipschitz on the ball of radius `r₀/2` around any branch image. -/
theorem holFamily_lipschitz (n : ℕ) (hn : 0 < n) (f : C(↥halfDisc, ℂ)) (hf : f ∈ halfDiscAlgebra)
    (M : ℝ) (hM : ‖f‖ ≤ M) (z z₀ : ↥halfDisc)
    (hclose : dist (gaussBranch n z.1) (gaussBranch n z₀.1) < r₀ n / 2) :
    ‖(f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ -
      (f : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1, branchMapsTo_halfDisc n z₀.property⟩‖
      ≤ (2 * M) / (r₀ n / 2) * ‖gaussBranch n z.1 - gaussBranch n z₀.1‖ := by
  -- K a small convex ball in the interior
  let s : Set ℂ := ball (gaussBranch n z₀.1) (r₀ n / 2)
  have hhalfr : (r₀ n / 2) ≤ r₀ n := by linarith [r₀_nonneg n]
  have hsub : s ⊆ interior halfDisc := by
    intro x hx
    exact branch_image_ball_subset_interior_r₀ n hn z₀.1 z₀.property
      (ball_subset_ball hhalfr hx)
  -- differentiability at every point of the ball
  have hdiff : ∀ x ∈ s, DifferentiableAt ℂ (toHalfHol f) x := by
    intro x hx
    have hd : DifferentiableOn ℂ (toHalfHol f) (interior halfDisc) :=
      (mem_halfDiscAlgebra f).mp hf
    exact hd.differentiableAt (isOpen_interior.mem_nhds (hsub hx))
  -- derivative bound via the Cauchy estimate
  have hbound : ∀ x ∈ s, ‖deriv (toHalfHol f) x‖ ≤ (2 * M) / (r₀ n / 2) := by
    intro x hx
    refine norm_deriv_toHalfHol_le f hf M hM x (r₀ n / 2) (by exact half_pos (r₀_pos n)) ?_
    intro y hy
    refine branch_image_ball_subset_interior_r₀ n hn z₀.1 z₀.property ?_
    have hy' : dist y x < r₀ n / 2 := by simpa [mem_ball] using hy
    have hx' : dist x (gaussBranch n z₀.1) < r₀ n / 2 := by simpa [s, mem_ball] using hx
    rw [mem_ball]
    linarith [dist_triangle y x (gaussBranch n z₀.1), hy', hx']
  -- the two endpoints
  have hxs : gaussBranch n z₀.1 ∈ s := by
    dsimp [s]
    rw [mem_ball, dist_self]
    exact half_pos (r₀_pos n)
  have hys : gaussBranch n z.1 ∈ s := by
    dsimp [s]
    rw [mem_ball]
    exact hclose
  -- mean value theorem on the convex ball
  have hMVT := Convex.norm_image_sub_le_of_norm_deriv_le (𝕜 := ℂ) hdiff hbound (convex_ball _ _) hxs hys
  -- rewrite `toHalfHol` values to the `ContinuousMap` values
  rw [toHalfHol_apply f (gaussBranch n z.1) (branchMapsTo_halfDisc n z.property),
      toHalfHol_apply f (gaussBranch n z₀.1) (branchMapsTo_halfDisc n z₀.property)] at hMVT
  exact hMVT

set_option maxHeartbeats 4000000 in
/-- The Mayer transfer family is equicontinuous on the closed unit ball
(Arzelà–Ascoli hypothesis), via the factorisation `(T f) z = w(z)² · f(φ z)`. -/
theorem equicontinuous_transferSummand (n : ℕ) (hn : 0 < n) :
    Equicontinuous (fun (f : {g : halfDiscAlgebra // ‖g‖ ≤ 1}) (z : ↥halfDisc) =>
      (transferSummandCLM n f.1) z) := by
  intro z₀
  let C : ℝ := (2 * 1) / (r₀ n / 2)
  set b : ↥halfDisc → ℝ := fun z =>
    ‖weightSqCM n z₀ - weightSqCM n z‖ +
      C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ with hb_def
  have hb0 : Tendsto b (𝓝 z₀) (𝓝 0) := by
    unfold b
    have h₁ : Tendsto (fun z : ↥halfDisc => ‖weightSqCM n z₀ - weightSqCM n z‖)
        (𝓝 z₀) (𝓝 0) := by
      have hg : ContinuousAt (fun z : ↥halfDisc => weightSqCM n z₀ - weightSqCM n z) z₀ := by
        exact (continuous_const.sub (weightSqCM n).continuous).continuousAt
      have hgT : Tendsto (fun z : ↥halfDisc => weightSqCM n z₀ - weightSqCM n z) (𝓝 z₀) (𝓝 0) := by
        simpa using hg.tendsto
      simpa using hgT.norm
    have h₂ : Tendsto (fun z : ↥halfDisc => ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖)
        (𝓝 z₀) (𝓝 0) := by
      have hgT : Tendsto (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ) -
          (gaussBranch n z₀.1 : ℂ)) (𝓝 z₀) (𝓝 0) := by
        have h0 : Tendsto (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ)) (𝓝 z₀)
            (𝓝 (gaussBranch n z₀.1 : ℂ)) := (continuous_branch_val n).continuousAt.tendsto
        simpa using h0.sub_const (gaussBranch n z₀.1 : ℂ)
      simpa using hgT.norm
    simpa using (h₁.add (h₂.const_mul C))
  have hev : ∀ᶠ z in 𝓝 z₀, ∀ f : {g : halfDiscAlgebra // ‖g‖ ≤ 1},
      dist ((transferSummandCLM n f.1) z₀) ((transferSummandCLM n f.1) z) ≤ b z := by
    have hclose_ev : ∀ᶠ z in 𝓝 z₀, dist (gaussBranch n z.1) (gaussBranch n z₀.1) < r₀ n / 2 := by
      have h2c : ContinuousAt (fun z : ↥halfDisc => dist (gaussBranch n z.1) (gaussBranch n z₀.1)) z₀ :=
        ((continuous_branch_val n).dist continuous_const).continuousAt
      have h2t : Tendsto (fun z : ↥halfDisc => dist (gaussBranch n z.1) (gaussBranch n z₀.1))
          (𝓝 z₀) (𝓝 0) := by
        simpa using h2c.tendsto
      exact h2t.eventually (gt_mem_nhds (half_pos (r₀_pos n)))
    filter_upwards [hclose_ev] with z hclose
    intro f
    -- hoist the coercion once: `g` is the continuous map underlying `f.1`
    set g : C(↥halfDisc, ℂ) := (f.1 : C(↥halfDisc, ℂ)) with hg_def
    have hgB : ‖g‖ ≤ 1 := f.property
    let A : ↥halfDisc → ℂ := fun x => weightSqCM n x
    let G : ↥halfDisc → ℂ := fun x =>
      g ⟨gaussBranch n x.1, branchMapsTo_halfDisc n x.property⟩
    -- expand (T f) x = A x * G x
    have hT (x : ↥halfDisc) :
        (transferSummandCLM n f.1) x = A x * G x := by
      rw [transferSummandCLM_apply]
      simp only [A, G, weightSqCM_apply]
      ring
    -- bound ‖A z₀‖ ≤ 1
    have hA : ‖weightSqCM n z₀‖ ≤ 1 := branch_sq_norm_le_one n z₀
    -- bound ‖G z‖ ≤ 1
    have hG1 : ‖G z‖ ≤ 1 :=
      (ContinuousMap.norm_coe_le_norm g
        (⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩ : ↥halfDisc)).trans hgB
    -- Lipschitz bound on G
    have hGLip : ‖G z₀ - G z‖ ≤ C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := by
      have hl := holFamily_lipschitz n hn g f.1.property 1 hgB z z₀ hclose
      -- hl : ‖g⟨bz⟩ - g⟨bz₀⟩‖ ≤ (2*1)/(r₀/2) * ‖bz - bz₀‖
      show ‖g ⟨gaussBranch n z₀.1, branchMapsTo_halfDisc n z₀.property⟩ -
          g ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.property⟩‖
          ≤ (2 * 1) / (r₀ n / 2) * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖
      rw [norm_sub_rev]
      exact hl
    -- assemble
    have hdist : dist ((transferSummandCLM n f.1) z₀) ((transferSummandCLM n f.1) z) ≤
        ‖weightSqCM n z₀ - weightSqCM n z‖ + C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := by
      rw [hT z₀, hT z]
      rw [dist_eq_norm]
      -- ‖A z₀ G z₀ - A z G z‖
      calc
        ‖A z₀ * G z₀ - A z * G z‖
            ≤ ‖A z₀ * G z₀ - A z₀ * G z‖ + ‖A z₀ * G z - A z * G z‖ := by
              rw [← sub_add_sub_cancel]
              exact norm_add_le _ _
        _ ≤ ‖weightSqCM n z₀ - weightSqCM n z‖ + C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := by
               have h1 : ‖A z₀ * G z₀ - A z₀ * G z‖ ≤ C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := by
                 have h0 := norm_mul_le (A z₀) (G z₀ - G z)
                 rw [mul_sub] at h0
                 exact h0.trans ((mul_le_mul_of_nonneg_right hA (norm_nonneg _)).trans
                   (by rw [one_mul]; exact hGLip))
               have h2 : ‖A z₀ * G z - A z * G z‖ ≤ ‖weightSqCM n z₀ - weightSqCM n z‖ := by
                 have h0 := norm_mul_le (A z₀ - A z) (G z)
                 rw [sub_mul] at h0
                 exact h0.trans ((mul_le_mul_of_nonneg_left hG1 (norm_nonneg _)).trans
                   (by rw [mul_one]))
               linarith
    exact hdist
  -- final assembly
  rw [Metric.equicontinuousAt_iff_right]
  intro ε hε0
  filter_upwards [hb0 (Iio_mem_nhds hε0), hev] with x hx₁ hxf
  intro f
  exact (hxf f).trans_lt hx₁
end

/-! ### The compactness of a summand, modulo the normal-families input -/

/-- **Surgical Montel reduction** (RH-41): if the pointwise image of the
transfer family on the closed unit ball is relatively compact in the product
topology of `↥halfDisc → ℂ` — the one normal-families fact (Montel /
Vitali–Porter: pointwise cluster limits of uniformly bounded holomorphic maps
are holomorphic) that mathlib lacks — then Arzelà–Ascoli upgrades it to
compactness in the sup norm, and the summand `transferSummandCLM n` is a
compact operator.

Everything except the hypothesis `hrc` is unconditional: equicontinuity is
`equicontinuous_transferSummand`, and the unit ball maps into the image by
construction.  Discharging `hrc` for all `n ≥ 1` is the phase-3 frontier. -/
theorem isCompactOperator_transferSummandCLM_of_pointwiseRelCompact (n : ℕ) (hn : 0 < n)
    (hrc : IsCompact (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ))) :
    IsCompactOperator (transferSummandCLM n) := by
  have heq : Equicontinuous
      (fun i : ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} =>
        transferSummandCLM n f.1) '' univ) =>
        ((i.1 : C(↥halfDisc, ℂ)) : ↥halfDisc → ℂ)) := by
    intro z₀
    rw [Metric.equicontinuousAt_iff_right]
    intro ε hε
    have hδ := Metric.equicontinuousAt_iff_right.mp
      (equicontinuous_transferSummand n hn z₀) ε hε
    filter_upwards [hδ] with y hy i
    obtain ⟨g, hg⟩ := i
    show dist (g z₀) (g y) < ε
    obtain ⟨f, -, rfl⟩ := hg
    exact hy f
  refine ⟨_, ArzelaAscoli.isCompact_of_equicontinuous _ hrc heq, ?_⟩
  refine Filter.mem_of_superset (Metric.ball_mem_nhds 0 one_pos) ?_
  intro f hf
  exact ⟨⟨f, le_of_lt (mem_ball_zero_iff.mp hf)⟩, mem_univ _, rfl⟩

/-- The branch is injective on the half-disc: a Möbius map (translation +
inversion) followed by the injective inversion. -/
theorem gaussBranch_injective (n : ℕ) :
    Function.Injective (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ)) :=
  (inv_injective (G := ℂ)).comp
    (fun z₁ z₂ (h : (n : ℂ) + 1 + z₁.1 = (n : ℂ) + 1 + z₂.1) =>
      Subtype.ext (add_left_cancel (G := ℂ) h))

/-- **Elementary half of Vitali–Porter** (no complex analysis needed): a
pointwise limit of the transfer family `fₖ ∘ gaussBranch n` with uniformly
bounded `‖fₖ‖ ≤ 1` is *continuous*.  Via `holFamily_lipschitz` the family is
equi-Lipschitz along the branch image, and an ε/3 argument transports
pointwise convergence to continuity of the limit.  The holomorphy of the
limit — the genuine Vitali–Porter wall — is not needed for this. -/
theorem continuous_pointwiseLimit_branch (n : ℕ) (hn : 0 < n)
    (f : ℕ → halfDiscAlgebra) (hf : ∀ k, ‖f k‖ ≤ 1)
    (G : ↥halfDisc → ℂ)
    (hpt : ∀ z : ↥halfDisc, Tendsto
      (fun k => (f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩)
      atTop (𝓝 (G z))) :
    Continuous G := by
  refine Metric.continuous_iff.mpr fun z₀ ε hε => ?_
  have hCpos : 0 < 2 / (r₀ n / 2) := div_pos (by norm_num) (half_pos (r₀_pos n))
  have h3 : 0 < ε / 3 := by linarith
  have hρpos : 0 < min (r₀ n / 2) (ε / (3 * (2 / (r₀ n / 2)))) :=
    lt_min (half_pos (r₀_pos n)) (div_pos hε (mul_pos (by norm_num) hCpos))
  have hφcont : ContinuousAt (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ)) z₀ :=
    (continuous_branch_val n).continuousAt
  obtain ⟨δ, hδpos, hδ⟩ := Metric.continuousAt_iff.mp hφcont _ hρpos
  refine ⟨δ, hδpos, fun z hz => ?_⟩
  have hφlt : dist (gaussBranch n z.1) (gaussBranch n z₀.1)
      < min (r₀ n / 2) (ε / (3 * (2 / (r₀ n / 2)))) := hδ hz
  -- k-uniform Lipschitz along the branch image
  have hLip : ∀ k, ‖(f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ -
      (f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1, branchMapsTo_halfDisc n z₀.2⟩‖
      ≤ 2 / (r₀ n / 2) * dist (gaussBranch n z.1) (gaussBranch n z₀.1) := by
    intro k
    have hl := holFamily_lipschitz n hn (f k : C(↥halfDisc, ℂ)) (f k).property 1 (hf k)
      z z₀ (lt_of_lt_of_le hφlt (min_le_left _ _))
    rw [dist_eq_norm]
    norm_num at hl ⊢
    exact hl
  obtain ⟨N₁, hN₁⟩ := Metric.tendsto_atTop.mp (hpt z₀) (ε / 3) h3
  obtain ⟨N₂, hN₂⟩ := Metric.tendsto_atTop.mp (hpt z) (ε / 3) h3
  set k := max N₁ N₂ with hk
  have h2 : dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1,
      branchMapsTo_halfDisc n z₀.2⟩) (G z₀) < ε / 3 := hN₁ k (le_max_left _ _)
  have h1 : dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) (G z) < ε / 3 := hN₂ k (le_max_right _ _)
  have h3' : dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1,
      branchMapsTo_halfDisc n z₀.2⟩) < ε / 3 := by
    rw [dist_eq_norm]
    calc ‖(f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ -
        (f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1, branchMapsTo_halfDisc n z₀.2⟩‖
        ≤ 2 / (r₀ n / 2) * dist (gaussBranch n z.1) (gaussBranch n z₀.1) := hLip k
      _ < 2 / (r₀ n / 2) * min (r₀ n / 2) (ε / (3 * (2 / (r₀ n / 2)))) :=
        (mul_lt_mul_of_pos_left (a := (2 / (r₀ n / 2))) hφlt hCpos)
      _ ≤ ε / 3 := by
        have h4 : (2:ℝ) / (r₀ n / 2) * (ε / (3 * (2 / (r₀ n / 2)))) = ε / 3 := by
          field_simp
          exact mul_inv_cancel₀ (ne_of_gt (r₀_pos n))
        calc (2 / (r₀ n / 2)) * min (r₀ n / 2) (ε / (3 * (2 / (r₀ n / 2))))
            ≤ (2 / (r₀ n / 2)) * (ε / (3 * (2 / (r₀ n / 2)))) :=
              mul_le_mul_of_nonneg_left (min_le_right _ _) hCpos.le
          _ = ε / 3 := h4
  have e1 : dist (G z) (G z₀) ≤ dist (G z) ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) + dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) (G z₀) := dist_triangle _ _ _
  have e2 : dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) (G z₀) ≤ dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1,
      branchMapsTo_halfDisc n z₀.2⟩) + dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z₀.1,
      branchMapsTo_halfDisc n z₀.2⟩) (G z₀) := dist_triangle _ _ _
  have h1s : dist (G z) ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) = dist ((f k : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1,
      branchMapsTo_halfDisc n z.2⟩) (G z) := dist_comm _ _
  linarith [h1s]

/-- **Generic compactness lemma (uniform equicontinuity)**: an equicontinuous
family on a compact metric space is uniformly equicontinuous -- the finite
subcover / radius-min over the compact. -/
theorem exists_delta_uniform_equicontinuous {X : Type*} [MetricSpace X] [CompactSpace X]
    {ι : Type*} {α : Type*} [PseudoMetricSpace α] (F : ι → X → α) (hF : Equicontinuous F)
    {ε : ℝ} (hε : 0 < ε) :
    ∃ δ > 0, ∀ x y : X, dist x y < δ → ∀ i, dist (F i x) (F i y) < ε := by
  have h2 : 0 < ε / 2 := by linarith
  have hpoint : ∀ x : X, ∃ d > 0, ∀ y, dist y x < d → ∀ i, dist (F i x) (F i y) < ε / 2 :=
    fun x => Metric.equicontinuousAt_iff.mp (hF x) (ε / 2) h2
  choose! δ₀ hδ₀ hball using hpoint
  obtain ⟨t, ht⟩ := isCompact_univ.elim_finite_subcover
    (fun x : X => ball x (δ₀ x / 2)) (fun x => isOpen_ball)
    (fun z _ => Set.mem_iUnion.mpr ⟨z, mem_ball_self (by linarith [hδ₀ z])⟩)
  rcases t.eq_empty_or_nonempty with hempty | hne
  · refine ⟨1, one_pos, fun x y _ _ => ?_⟩
    rw [hempty] at ht
    simp at ht
    exact ht.elim x
  · have hδpos : 0 < t.inf' hne (fun x => δ₀ x / 2) :=
      (Finset.lt_inf'_iff hne).2 fun c hc => by linarith [hδ₀ c]
    refine ⟨t.inf' hne (fun x => δ₀ x / 2), hδpos, fun x y hxy i => ?_⟩
    have hx : x ∈ ⋃ z ∈ t, ball z (δ₀ z / 2) := ht (mem_univ x)
    obtain ⟨c, hc, hcx⟩ := Set.mem_iUnion₂.mp hx
    have h1 : t.inf' hne (fun x => δ₀ x / 2) ≤ δ₀ c / 2 := by
      by_contra hcon
      have hlow := (Finset.lt_inf'_iff hne).mp (not_le.mp hcon) c hc
      linarith
    have hdcx : dist x c < δ₀ c / 2 := mem_ball.mp hcx
    have hdcy : dist y c < δ₀ c := by
      have htri := dist_triangle y x c
      have hsym : dist y x = dist x y := dist_comm y x
      linarith
    have e1 := hball c x (by linarith [hdcx, hδ₀ c]) i
    have e2 := hball c y hdcy i
    calc dist (F i x) (F i y) ≤ dist (F i x) (F i c) + dist (F i c) (F i y) :=
        dist_triangle _ _ _
      _ < ε := by rw [dist_comm (F i x) (F i c)]; linarith

/-- **Generic compactness lemma (uniform convergence)**: on a compact metric
space, uniform equicontinuity (e.g. from the previous lemma) plus pointwise
convergence on a dense sequence plus continuity of the limit implies uniform
convergence -- the classical ε/3 + total-boundedness + finite-max argument. -/
theorem tendstoUniformly_of_tendstoOn_dense {X : Type*} [MetricSpace X] [CompactSpace X]
    {α : Type*} [PseudoMetricSpace α]
    (F : ℕ → X → α) (g : X → α) (D : ℕ → X)
    (hD : DenseRange D)
    (hFD : ∀ j, Tendsto (fun k => F k (D j)) atTop (𝓝 (g (D j))))
    (hg : Continuous g)
    (huni : ∀ ε > 0, ∃ δ > 0, ∀ x y : X, dist x y < δ → ∀ k, dist (F k x) (F k y) < ε) :
    TendstoUniformly F g atTop := by
  rw [Metric.tendstoUniformly_iff]
  intro ε hε
  have h3 : 0 < ε / 3 := by linarith
  obtain ⟨δ, hδ, hδball⟩ := huni (ε / 3) h3
  obtain ⟨δg, hδg, hδgball⟩ := Metric.uniformContinuous_iff.mp
    (CompactSpace.uniformContinuous_of_continuous hg) (ε / 3) h3
  have hρpos : 0 < min (δ / 2) (δg / 2) := lt_min (by linarith) (by linarith)
  have hTB : TotallyBounded (univ : Set X) := isCompact_univ.totallyBounded
  obtain ⟨t, htf, hcover⟩ := (Metric.totallyBounded_iff.mp hTB)
    (min (δ / 2) (δg / 2)) hρpos
  have hdens : ∀ y : X, ∃ j, y ∈ t → dist (D j) y < min (δ / 2) (δg / 2) := by
    intro y
    by_cases hy : y ∈ t
    · have hballne : (ball y (min (δ / 2) (δg / 2)) ∩ range D).Nonempty :=
        (dense_iff_inter_open.mp hD) _ isOpen_ball ⟨y, mem_ball_self hρpos⟩
      obtain ⟨d, hd, ⟨j, rfl⟩⟩ := hballne
      exact ⟨j, fun _ => mem_ball.mp hd⟩
    · exact ⟨0, fun h => absurd h hy⟩
  choose j hj using hdens
  have hN : ∀ y : X, ∃ N, y ∈ t → ∀ k ≥ N, dist (F k (D (j y))) (g (D (j y))) < ε / 3 := by
    intro y
    by_cases hy : y ∈ t
    · simpa [hy, dist_comm] using Metric.tendsto_atTop.mp (hFD (j y)) (ε / 3) h3
    · exact ⟨0, fun h => absurd h hy⟩
  choose N hN using hN
  set N₀ : ℕ := (htf.toFinset.image N).sup id with hN₀
  have hev : ∀ᶠ k in atTop, ∀ x, dist (g x) (F k x) < ε := by
    refine Filter.eventually_atTop.mpr ⟨N₀, fun k hkN x => ?_⟩
    obtain ⟨y, hy, hyx⟩ := Set.mem_iUnion₂.mp (hcover (mem_univ x))
    have hxy : dist x y < min (δ / 2) (δg / 2) := mem_ball.mp hyx
    have hmin1 : min (δ / 2) (δg / 2) ≤ δ / 2 := min_le_left _ _
    have hmin2 : min (δ / 2) (δg / 2) ≤ δg / 2 := min_le_right _ _
    have hxyN : dist x y < δ := by linarith
    have hxyg : dist x y < δg := by linarith
    have hyk : N y ≤ k :=
      Nat.le_trans (Finset.le_sup (f := id)
        (Finset.mem_image.mpr ⟨y, htf.mem_toFinset.mpr hy, rfl⟩)) hkN
    have hdmid : dist (D (j y)) y < min (δ / 2) (δg / 2) := hj y hy
    have hxdg : dist x (D (j y)) < δg := by
      have htri := dist_triangle x y (D (j y))
      rw [dist_comm y (D (j y))] at htri
      have hdhalf : δg / 2 < δg := by linarith
      linarith
    have hxdF : dist (D (j y)) x < δ := by
      have htri := dist_triangle (D (j y)) y x
      rw [dist_comm y x] at htri
      have hdhalf : δ / 2 < δ := by linarith
      linarith
    have hga : dist (g x) (g (D (j y))) < ε / 3 := hδgball hxdg
    have hmid : dist (g (D (j y))) (F k (D (j y))) < ε / 3 := by
      rw [dist_comm (g (D (j y))) (F k (D (j y)))]
      exact hN y hy k hyk
    have hFc : dist (F k (D (j y))) (F k x) < ε / 3 := hδball (D (j y)) x hxdF k
    have htri1 : dist (g x) (F k x) ≤ dist (g x) (g (D (j y))) +
        dist (g (D (j y))) (F k x) := dist_triangle (g x) (g (D (j y))) (F k x)
    have htri2 : dist (g (D (j y))) (F k x) ≤ dist (g (D (j y))) (F k (D (j y))) +
        dist (F k (D (j y))) (F k x) := dist_triangle (g (D (j y))) (F k (D (j y))) (F k x)
    linarith
  exact hev

/-- **Tychonoff half of the Montel reduction** (unconditional): the pointwise
closure of the unit-ball transfer image is compact in the product topology --
it lives in the product of `closedBall 0 (1/(n+1)^2)` by
`norm_transferSummandCLM_le`. -/
theorem isCompact_piClosure_transferImage (n : ℕ) :
    IsCompact (closure (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ))) := by
  have hbnd : ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ)
      ⊆ univ.pi (fun _ : ↥halfDisc => closedBall (0 : ℂ) (1 / ((n : ℝ) + 1) ^ 2)) := by
    rintro G ⟨g, hg, rfl⟩ z -
    obtain ⟨f, -, rfl⟩ := hg
    have h1 : ‖(transferSummandCLM n f.1) z‖ ≤ ‖transferSummandCLM n f.1‖ :=
      ContinuousMap.norm_coe_le_norm _ z
    have h2 := norm_transferSummandCLM_le n f.1
    refine mem_closedBall.mpr ?_
    rw [dist_zero_right]
    exact le_trans h1 (le_trans h2 (by gcongr; exact f.property))
  have hs : IsCompact (univ.pi fun _ : ↥halfDisc =>
      closedBall (0 : ℂ) (1 / ((n : ℝ) + 1) ^ 2)) :=
    isCompact_univ_pi fun _ => isCompact_closedBall 0 (1 / ((n : ℝ) + 1) ^ 2)
  have hc : closure (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ)) ⊆
      univ.pi (fun _ : ↥halfDisc => closedBall (0 : ℂ) (1 / ((n : ℝ) + 1) ^ 2)) :=
    closure_minimal hbnd (isClosed_set_pi fun _ _ => isClosed_closedBall)
  exact IsCompact.of_isClosed_subset hs isClosed_closure hc

/-- **The final frontier packaging**: pi-closedness of the transfer image --
the pure Vitali-Porter statement, *no topology left in the hypothesis* --
gives the compact operator.  `hclosed` says: every pointwise limit of maps
`f ↦ (gaussBranch n)² · (f ∘ gaussBranch n)` with `‖f‖ ≤ 1` is a continuous
function.  Proving it (for all `n ≥ 1`) is the phase-3 research milestone. -/
theorem isCompactOperator_transferSummandCLM_of_piClosed (n : ℕ) (hn : 0 < n)
    (hclosed : IsClosed (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ))) :
    IsCompactOperator (transferSummandCLM n) :=
  isCompactOperator_transferSummandCLM_of_pointwiseRelCompact n hn
    (IsCompact.of_isClosed_subset (isCompact_piClosure_transferImage n) hclosed
      subset_closure)

end Riemann
