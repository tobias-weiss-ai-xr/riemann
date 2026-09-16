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

/-- The Mayer transfer family is equicontinuous on the closed unit ball
(Arzelà–Ascoli hypothesis), via the factorisation `(T f) z = w(z)² · f(φ z)`. -/
theorem equicontinuous_transferSummand (n : ℕ) (hn : 0 < n) :
    Equicontinuous (fun (f : {g : halfDiscAlgebra // ‖g‖ ≤ 1}) (z : ↥halfDisc) =>
      (transferSummandCLM n f.1) z) := by
  intro z₀
  let C : ℝ := (2 * 1) / (r₀ n / 2)
  show EquicontinuousAt (fun f z => (transferSummandCLM n f.1) z) z₀
  -- modulus: |w(z₀)²-w(z)²| + C·‖φ z - φ z₀‖ (both → 0)
  let b : ↥halfDisc → ℝ := fun z =>
    ‖weightSqCM n z₀ - weightSqCM n z‖ +
      C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖
  have hb0 : Tendsto b (𝓝 z₀) (𝓝 0) := by
    unfold b
    have h₁ : Tendsto (fun z : ↥halfDisc => ‖weightSqCM n z₀ - weightSqCM n z‖) (𝓝 z₀) (𝓝 0) := by
      have hg : ContinuousAt (fun z : ↥halfDisc => weightSqCM n z₀ - weightSqCM n z) z₀ := by
        exact (continuous_const.sub (weightSqCM n).continuous).continuousAt
      have hgT : Tendsto (fun z : ↥halfDisc => weightSqCM n z₀ - weightSqCM n z) (𝓝 z₀) (𝓝 0) := by
        simpa using hg.tendsto
      simpa using hgT.norm
    have h₂ : Tendsto (fun z : ↥halfDisc => ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖)
        (𝓝 z₀) (𝓝 0) := by
      have hg : ContinuousAt (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ)) z₀ :=
        (continuous_branch_val n).continuousAt
      have hgT : Tendsto (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ) -
          (gaussBranch n z₀.1 : ℂ)) (𝓝 z₀) (𝓝 0) := by
        simpa using hg.tendsto
      simpa using hgT.norm
    simpa using (h₁.add (h₂.const_mul C))
  -- the eventual bound
  have hev : ∀ᶠ z in 𝓝 z₀, ∀ f : {g : halfDiscAlgebra // ‖g‖ ≤ 1},
      dist ((transferSummandCLM n f.1) z₀) ((transferSummandCLM n f.1) z) ≤ b z := by
    -- φ is continuous at z₀, so ‖φ z - φ z₀‖ < r₀/2 eventually
    have hclose_ev : ∀ᶠ z in 𝓝 z₀, dist (gaussBranch n z.1) (gaussBranch n z₀.1) < r₀ n / 2 := by
      have hb : ContinuousAt (fun z : ↥halfDisc => (gaussBranch n z.1 : ℂ)) z₀ :=
        (continuous_branch_val n).continuousAt
      exact (Metric.continuousAt_iff.1 hb) (r₀ n / 2) (by exact half_pos (r₀_pos n))
    filter_upwards [hclose_ev] with z hclose
    intro f hf
    let A : ↥halfDisc → ℂ := fun x => weightSqCM n x
    let G : ↥halfDisc → ℂ := fun x =>
      (f.1 : C(↥halfDisc, ℂ)) ⟨gaussBranch n x.1, branchMapsTo_halfDisc n x.property⟩
    -- expand (T f) x = A x * G x
    have hT (x : ↥halfDisc) :
        (transferSummandCLM n f.1) x = A x * G x := by
      unfold A G
      rw [transferSummandCLM_apply, weightSqCM_apply]
      ring
    -- bound ‖A z₀‖ ≤ 1
    have hA : ‖weightSqCM n z₀‖ ≤ 1 := branch_sq_norm_le_one n z₀
    -- bound ‖G z‖ ≤ 1
    have hG1 : ‖G z‖ ≤ 1 := by
      unfold G
      have h : ‖(f.1 : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, _⟩‖ ≤ ‖(f.1 : C(↥halfDisc, ℂ))‖ :=
        ContinuousMap.norm_coe_le_norm (f.1 : C(↥halfDisc, ℂ)) _
      have hbnd : ‖(f.1 : C(↥halfDisc, ℂ))‖ ≤ 1 := by
        simpa using f.property
      exact le_trans h hbnd
    -- Lipschitz bound on G
    have hGLip : ‖G z₀ - G z‖ ≤ C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := by
      unfold G C
      have hl := holFamily_lipschitz n hn (f.1 : C(↥halfDisc, ℂ)) f.1.property 1 (by simpa using f.property)
        z z₀ hclose
      -- hl : ‖f⟨bz⟩ - f⟨bz₀⟩‖ ≤ (2*1)/(r₀/2) * ‖bz - bz₀‖
      simpa [norm_sub_rev, one_mul] using hl
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
               -- ‖A z₀ * (G z₀ - G z)‖ ≤ ‖A z₀‖ * ‖G z₀ - G z‖ ≤ 1 * (C*‖φz - φz₀‖)
               -- ‖(A z₀ - A z) * G z‖ ≤ ‖A z₀ - A z‖ * ‖G z‖ ≤ ‖A z₀ - A z‖ * 1
               have h1 : ‖A z₀ * G z₀ - A z₀ * G z‖ ≤ C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := by
                 rw [← mul_sub]
                 calc
                   ‖A z₀ * (G z₀ - G z)‖ ≤ ‖A z₀‖ * ‖G z₀ - G z‖ := norm_mul_le _ _
                   _ ≤ 1 * ‖G z₀ - G z‖ := by
                     gcongr
                     exact hA
                   _ ≤ C * ‖(gaussBranch n z.1 : ℂ) - (gaussBranch n z₀.1 : ℂ)‖ := hGLip
               have h2 : ‖A z₀ * G z - A z * G z‖ ≤ ‖weightSqCM n z₀ - weightSqCM n z‖ := by
                 rw [← sub_mul]
                 calc
                   ‖(A z₀ - A z) * G z‖ ≤ ‖A z₀ - A z‖ * ‖G z‖ := norm_mul_le _ _
                   _ ≤ ‖A z₀ - A z‖ * 1 := by gcongr; exact hG1
                   _ = ‖weightSqCM n z₀ - weightSqCM n z‖ := by simp [A]
               linarith
    unfold b
    simpa using hdist
  exact Metric.equicontinuousAt_of_continuity_modulus b hb0
    (fun f z => (transferSummandCLM n f.1) z) hev

end

end Riemann
