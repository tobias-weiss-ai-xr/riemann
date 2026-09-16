/-
Copyright (c) 2026 Tobias Weiss. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
-/
import Mathlib.Analysis.Complex.LocallyUniformLimit
import Mathlib.Analysis.Complex.Schwarz
import Mathlib.Topology.ContinuousMap.Algebra
import Mathlib.Topology.UniformSpace.LocallyUniformConvergence
import Mathlib.Topology.UniformSpace.UniformConvergence

/-!
# The half-disc algebra (Mayer analytic class, phase 2a)

The **half-disc** `halfDisc = closedBall 0 1 ∩ {Re z ≥ 0}` and the
**half-disc algebra** `halfDiscAlgebra` of continuous functions on it that
are holomorphic on its interior — a closed complete subalgebra of
`C(↥halfDisc, ℂ)` with the sup norm.

Why the half-disc rather than the full disc: the Gauss-map inverse branches
`z ↦ 1/(n+1+z)` map the closed half-disc into itself (all `n ≥ 0`) and, for
every `n ≥ 1`, *compactly* into its interior: the image lies in
`{‖w‖ ≤ 1/(n+1) ≤ 1/2, Re w > 0}` (`branch_norm_le`, `branch_re_pos`,
`branchMapsTo_interior`, `branch_image_ball_subset_interior`).  On this class
the Mayer transfer operator is a bounded self-map (phase 2b) and the branch
summands with `n ≥ 1` are compact operators (phase 2c).
See `research/FRONTIER.md` §3b.

## Main definitions and results

* `Riemann.halfDisc`: the closed half-disc, compact as a subspace of `ℂ`.
* `Riemann.toHalfHol`: view a continuous function on the half-disc as a plain
  function `ℂ → ℂ` (values on the half-disc, zero outside).
* `Riemann.halfDiscAlgebra`: the subalgebra of `C(↥halfDisc, ℂ)` whose
  elements are holomorphic on the interior of the half-disc.
* `Riemann.isClosed_halfDiscAlgebra`: closed in the sup norm — the
  Weierstrass theorem (`TendstoLocallyUniformlyOn.differentiableOn`).
* `Riemann.halfDiscAlgebra_complete`: hence a Banach space.
* `Riemann.norm_deriv_toHalfHol_le`: uniform Cauchy estimate — the derivative
  of an algebra element is bounded in terms of its norm and the distance of
  the point from the boundary; the equicontinuity input for Arzelà–Ascoli.
-/

open Metric Set Filter Complex Topology
open scoped Classical

namespace Riemann

noncomputable section

/-! ### The half-disc and its interior -/

/-- The closed right half-disc: `|z| ≤ 1` and `Re z ≥ 0`. -/
def halfDisc : Set ℂ := closedBall (0 : ℂ) 1 ∩ {z | 0 ≤ z.re}

theorem isClosed_setOf_re_ge (r : ℝ) : IsClosed {z : ℂ | r ≤ z.re} :=
  isClosed_Ici.preimage Complex.continuous_re

theorem isClosed_halfDisc : IsClosed halfDisc :=
  isClosed_closedBall.inter (isClosed_setOf_re_ge 0)

theorem isCompact_halfDisc : IsCompact halfDisc :=
  IsCompact.of_isClosed_subset (isCompact_closedBall (0 : ℂ) 1) isClosed_halfDisc
    inter_subset_left

instance : CompactSpace ↥halfDisc := isCompact_iff_compactSpace.mp isCompact_halfDisc

/-- Points of the open half-disc lie in the interior of the closed half-disc. -/
theorem mem_interior_halfDisc {z : ℂ} (hz : z ∈ ball (0 : ℂ) 1) (hre : 0 < z.re) :
    z ∈ interior halfDisc :=
  interior_maximal
    (fun (w : ℂ) (hw : w ∈ ball (0 : ℂ) 1 ∩ {z : ℂ | 0 < z.re}) =>
      mem_inter (mem_closedBall_zero_iff.mpr (mem_ball_zero_iff.mp hw.1).le)
        (le_of_lt (show 0 < w.re by exact hw.2)))
    (isOpen_ball.inter (isOpen_lt continuous_const Complex.continuous_re))
    ⟨hz, hre⟩

/-- A ball around a point of the open half-disc whose radius is bounded by
the point's distance to the half-disc boundary lies in the interior. -/
theorem ball_subset_interior_halfDisc {w : ℂ} {r : ℝ}
    (_hw : w ∈ ball (0 : ℂ) 1) (_hre : 0 < w.re) (hr : r ≤ min (1 - ‖w‖) w.re) :
    ball w r ⊆ interior halfDisc := by
  intro z hz
  obtain ⟨h1, h2⟩ := le_min_iff.mp hr
  have hdist : dist z w < r := mem_ball.mp hz
  have hdw : ‖z - w‖ < r := by rwa [dist_eq_norm] at hdist
  have htri : ‖z‖ ≤ ‖w‖ + ‖z - w‖ := by simpa using norm_add_le w (z - w)
  have hnorm : ‖z‖ < 1 := by linarith
  have habs := abs_re_le_norm (z - w)
  have hneg : -(‖z - w‖) ≤ (z - w).re := (abs_le.mp habs).1
  have hre' : (z - w).re = z.re - w.re := by rw [sub_re]
  have hre2 : 0 < z.re := by linarith
  exact mem_interior_halfDisc (mem_ball_zero_iff.mpr hnorm) hre2

/-! ### Gauss-map branch geometry on the half-disc -/

/-- The `n`-th Gauss-map inverse branch as a complex function. -/
def gaussBranch (n : ℕ) (z : ℂ) : ℂ := ((n : ℂ) + 1 + z)⁻¹

theorem gaussBranch_ne_zero (n : ℕ) (z : ℂ) (hz : z ∈ halfDisc) :
    (n : ℂ) + 1 + z ≠ 0 := by
  intro h0
  have hre : ((n : ℂ) + 1 + z).re = 0 := by rw [h0, Complex.zero_re]
  have hre' : (n : ℝ) + 1 + z.re = 0 := by
    rw [Complex.add_re, Complex.add_re, Complex.natCast_re, Complex.one_re] at hre
    exact hre
  have hz2 : 0 ≤ z.re := hz.2
  linarith

theorem branch_norm_le (n : ℕ) (z : ℂ) (hz : z ∈ halfDisc) :
    ‖gaussBranch n z‖ ≤ 1 / ((n : ℝ) + 1) := by
  have hwn : 0 < ‖(n : ℂ) + 1 + z‖ := by
    have h : ‖(n : ℂ) + 1 + z‖ ≠ 0 := fun hh =>
      gaussBranch_ne_zero n z hz (by rw [← norm_eq_zero]; exact hh)
    exact lt_of_le_of_ne (norm_nonneg _) (Ne.symm h)
  have hposn : (0 : ℝ) < (n : ℝ) + 1 := by linarith [Nat.cast_nonneg (α := ℝ) n]
  have hnormge : ((n : ℝ) + 1 : ℝ) ≤ ‖(n : ℂ) + 1 + z‖ := by
    have hre : ((n : ℂ) + 1 + z).re = (n : ℝ) + 1 + z.re := by
      rw [Complex.add_re, Complex.add_re, Complex.natCast_re, Complex.one_re]
    have h3 := abs_re_le_norm ((n : ℂ) + 1 + z)
    have hup : (n : ℝ) + 1 + z.re ≤ ‖(n : ℂ) + 1 + z‖ := by
      rw [← hre]
      exact (abs_le.mp h3).2
    have hzre : 0 ≤ z.re := hz.2
    linarith
  have hinv : ‖gaussBranch n z‖ = ‖(n : ℂ) + 1 + z‖⁻¹ := by
    rw [gaussBranch, norm_inv]
  rw [hinv, one_div]
  exact (inv_le_inv₀ hwn hposn).mpr hnormge

theorem branch_re_eq (n : ℕ) (z : ℂ) :
    (gaussBranch n z).re = ((n : ℝ) + 1 + z.re) / Complex.normSq ((n : ℂ) + 1 + z) := by
  rw [gaussBranch, Complex.inv_re, Complex.add_re, Complex.add_re,
    Complex.natCast_re, Complex.one_re]

theorem branch_re_pos (n : ℕ) (z : ℂ) (hz : z ∈ halfDisc) : 0 < (gaussBranch n z).re := by
  have hnz := gaussBranch_ne_zero n z hz
  have hz2 : 0 ≤ z.re := hz.2
  have hnum : 0 < (n : ℝ) + 1 + z.re := by
    linarith [hz2, Nat.cast_nonneg (α := ℝ) n]
  rw [branch_re_eq]
  exact div_pos hnum (normSq_pos.mpr hnz)

/-- Every branch maps the half-disc into the half-disc. -/
theorem branchMapsTo_halfDisc (n : ℕ) : MapsTo (gaussBranch n) halfDisc halfDisc :=
  fun z hz => by
    have hposn : (0 : ℝ) < (n : ℝ) + 1 := by linarith [Nat.cast_nonneg (α := ℝ) n]
    have hnr : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
    have hnorm := branch_norm_le n z hz
    have hone : ‖gaussBranch n z‖ ≤ 1 := le_trans hnorm (by
      rw [one_div, inv_le_one₀ hposn]
      linarith)
    exact ⟨mem_closedBall_zero_iff.mpr hone, le_of_lt (branch_re_pos n z hz)⟩

/-- Branches with `n ≥ 1` map the half-disc *compactly* into the interior. -/
theorem branchMapsTo_interior (n : ℕ) (hn : 0 < n) :
    MapsTo (gaussBranch n) halfDisc (interior halfDisc) := fun z hz => by
  have hposn : (0 : ℝ) < (n : ℝ) + 1 := by linarith [Nat.cast_nonneg (α := ℝ) n]
  have hnr : (1 : ℝ) ≤ (n : ℝ) := by exact_mod_cast (Nat.succ_le_of_lt hn)
  have hnorm := branch_norm_le n z hz
  have hlt1 : ‖gaussBranch n z‖ < 1 := lt_of_le_of_lt hnorm (by
    rw [one_div, inv_lt_one₀ hposn]
    linarith)
  exact mem_interior_halfDisc (mem_ball_zero_iff.mpr hlt1) (branch_re_pos n z hz)

/-- Quantitative compactness: for `n ≥ 1`, a ball of radius `1/(2·(n+2)²)`
around any branch image lies in the interior of the half-disc — the z-free
margin for the uniform Cauchy estimate. -/
theorem branch_image_ball_subset_interior (n : ℕ) (hn : 0 < n) (z : ℂ)
    (hz : z ∈ halfDisc) :
    ball (gaussBranch n z) (1 / (2 * ((n : ℝ) + 2) ^ 2)) ⊆ interior halfDisc := by
  have hzn : ‖z‖ ≤ 1 := mem_closedBall_zero_iff.mp hz.1
  have hwnorm : ‖gaussBranch n z‖ ≤ 1 / ((n : ℝ) + 1) := branch_norm_le n z hz
  have htr : ‖((n : ℂ) + 1 + z : ℂ)‖ ≤ (n : ℝ) + 2 := by
    have h1 : ‖((n : ℂ) + 1 + z : ℂ)‖ ≤ ‖((n : ℂ) + 1 : ℂ)‖ + ‖z‖ := norm_add_le _ _
    have h2 : ‖((n : ℂ) + 1 : ℂ)‖ ≤ (n : ℝ) + 1 := by
      have h2a : ‖((n : ℂ) + 1 : ℂ)‖ ≤ ‖(n : ℂ)‖ + ‖(1 : ℂ)‖ := norm_add_le _ _
      rw [Complex.norm_natCast n, norm_one] at h2a
      linarith [Nat.cast_nonneg (α := ℝ) n]
    have h3 : ‖z‖ ≤ 1 := hzn
    linarith
  have hnsq : Complex.normSq ((n : ℂ) + 1 + z) ≤ ((n : ℝ) + 2) ^ 2 := by
    rw [Complex.normSq_eq_norm_sq]
    exact pow_le_pow_left₀ (norm_nonneg _) htr 2
  have hposn : (0 : ℝ) < (n : ℝ) + 1 := by linarith [Nat.cast_nonneg (α := ℝ) n]
  have hnr : (1 : ℝ) ≤ (n : ℝ) := by exact_mod_cast (Nat.succ_le_of_lt hn)
  have hz2 : 0 ≤ z.re := hz.2
  have hcp : (0 : ℝ) < ((n : ℝ) + 2) ^ 2 := by positivity
  have h2c : (0 : ℝ) < 2 * ((n : ℝ) + 2) ^ 2 := by positivity
  have hp1 : (0 : ℝ) < (n : ℝ) + 1 := by linarith
  have h12 : (1 : ℝ) ≤ (n : ℝ) + 2 := by linarith
  have hn1 : (1 : ℝ) ≤ (n : ℝ) := by exact_mod_cast (Nat.succ_le_of_lt hn)
  have hc1 : (1 : ℝ) ≤ ((n : ℝ) + 2) ^ 2 := one_le_pow₀ h12
  have hwnz : (n : ℂ) + 1 + z ≠ 0 := gaussBranch_ne_zero n z hz
  have hwnorm : ‖gaussBranch n z‖ ≤ 1 / ((n : ℝ) + 1) := branch_norm_le n z hz
  have hball : gaussBranch n z ∈ ball (0 : ℂ) 1 := by
    refine mem_ball_zero_iff.mpr (lt_of_le_of_lt hwnorm ?_)
    rw [one_div, inv_lt_one₀ hposn]
    linarith
  have hnumP : (0 : ℝ) < (n : ℝ) + 1 + z.re := by linarith
  have hnumL : (n : ℝ) + 1 ≤ (n : ℝ) + 1 + z.re := by linarith
  have hsqP : (0 : ℝ) < Complex.normSq ((n : ℂ) + 1 + z) :=
    normSq_pos.mpr hwnz
  have hre : ((n : ℝ) + 1) / ((n : ℝ) + 2) ^ 2 ≤ (gaussBranch n z).re := by
    rw [branch_re_eq]
    calc ((n : ℝ) + 1) / ((n : ℝ) + 2) ^ 2
        ≤ ((n : ℝ) + 1 + z.re) / ((n : ℝ) + 2) ^ 2 :=
          (div_le_div_iff_of_pos_right hcp).mpr hnumL
      _ ≤ ((n : ℝ) + 1 + z.re) / Complex.normSq ((n : ℂ) + 1 + z) :=
          (div_le_div_iff_of_pos_left hnumP hcp hsqP).mpr hnsq
  have key : (1 : ℝ) / (2 * ((n : ℝ) + 2) ^ 2) ≤ 1 - 1 / ((n : ℝ) + 1) := by
    have half2 : (1 : ℝ) / (2 * ((n : ℝ) + 2) ^ 2) ≤ (1 : ℝ) / 2 :=
      (div_le_div_iff_of_pos_left zero_lt_one h2c (by positivity)).mpr
        (by linarith [hc1])
    have halfn : (1 : ℝ) / 2 ≤ (n : ℝ) / ((n : ℝ) + 1) :=
      (div_le_div_iff₀ (by positivity) hp1).mpr (by linarith)
    have eq1 : (n : ℝ) / ((n : ℝ) + 1) = 1 - 1 / ((n : ℝ) + 1) := by
      field_simp
      ring
    rw [← eq1]
    exact le_trans half2 halfn
  have side1 : (1 : ℝ) / (2 * ((n : ℝ) + 2) ^ 2) ≤ 1 - ‖gaussBranch n z‖ :=
    le_trans key (by linarith)
  have mid : (1 : ℝ) / (2 * ((n : ℝ) + 2) ^ 2) ≤ (1 : ℝ) / ((n : ℝ) + 2) ^ 2 :=
    (div_le_div_iff_of_pos_left zero_lt_one h2c hcp).mpr (by linarith)
  have strict : (1 : ℝ) / ((n : ℝ) + 2) ^ 2 < ((n : ℝ) + 1) / ((n : ℝ) + 2) ^ 2 :=
    (div_lt_div_iff_of_pos_right hcp).mpr (by linarith)
  have side2 : (1 : ℝ) / (2 * ((n : ℝ) + 2) ^ 2) < (gaussBranch n z).re :=
    lt_of_le_of_lt mid (lt_of_lt_of_le strict hre)
  exact ball_subset_interior_halfDisc hball (branch_re_pos n z hz)
    (le_min side1 side2.le)

/-! ### Extension by zero and the half-disc algebra -/

/-- View a continuous function on the half-disc as a plain complex function
on `ℂ`: values on the half-disc, zero outside. -/
def toHalfHol (f : C(↥halfDisc, ℂ)) : ℂ → ℂ := fun z =>
  if h : z ∈ halfDisc then f ⟨z, h⟩ else 0

theorem toHalfHol_apply (f : C(↥halfDisc, ℂ)) (z : ℂ) (hz : z ∈ halfDisc) :
    toHalfHol f z = f ⟨z, hz⟩ := by
  unfold toHalfHol
  exact dif_pos hz

theorem toHalfHol_apply_of_not_mem (f : C(↥halfDisc, ℂ)) (hz : z ∉ halfDisc) :
    toHalfHol f z = 0 := by
  unfold toHalfHol
  exact dif_neg hz

theorem toHalfHol_add (a b : C(↥halfDisc, ℂ)) (w : ℂ) (hw : w ∈ halfDisc) :
    toHalfHol (a + b) w = (toHalfHol a + toHalfHol b) w := by
  rw [toHalfHol_apply (a + b) w hw, ContinuousMap.coe_add]
  simp only [Pi.add_apply, toHalfHol_apply a w hw, toHalfHol_apply b w hw]

theorem toHalfHol_mul (a b : C(↥halfDisc, ℂ)) (w : ℂ) (hw : w ∈ halfDisc) :
    toHalfHol (a * b) w = (toHalfHol a * toHalfHol b) w := by
  rw [toHalfHol_apply (a * b) w hw, ContinuousMap.coe_mul]
  simp only [Pi.mul_apply, toHalfHol_apply a w hw, toHalfHol_apply b w hw]

theorem toHalfHol_const (c : ℂ) (w : ℂ) (hw : w ∈ halfDisc) :
    toHalfHol (algebraMap ℂ C(↥halfDisc, ℂ) c) w = c := by
  rw [toHalfHol_apply _ w hw]
  simp

/-- The half-disc algebra: continuous functions on the half-disc that are
holomorphic on its interior. -/
def halfDiscAlgebra : Subalgebra ℂ C(↥halfDisc, ℂ) where
  carrier := {f | DifferentiableOn ℂ (toHalfHol f) (interior halfDisc)}
  add_mem' {a b} ha hb := by
    refine DifferentiableOn.congr (ha.add hb) fun w hw => ?_
    exact toHalfHol_add a b w (interior_subset hw)
  mul_mem' {a b} ha hb := by
    refine DifferentiableOn.congr (ha.mul hb) fun w hw => ?_
    exact toHalfHol_mul a b w (interior_subset hw)
  algebraMap_mem' c := by
    refine DifferentiableOn.congr (differentiableOn_const c) fun w hw => ?_
    exact toHalfHol_const c w (interior_subset hw)
  zero_mem' := by
    refine DifferentiableOn.congr (differentiableOn_const (0 : ℂ)) fun w hw => ?_
    have := toHalfHol_const 0 w (interior_subset hw)
    rwa [map_zero] at this
  one_mem' := by
    refine DifferentiableOn.congr (differentiableOn_const (1 : ℂ)) fun w hw => ?_
    have := toHalfHol_const 1 w (interior_subset hw)
    rwa [map_one] at this

theorem mem_halfDiscAlgebra (f : C(↥halfDisc, ℂ)) :
    f ∈ halfDiscAlgebra ↔ DifferentiableOn ℂ (toHalfHol f) (interior halfDisc) :=
  ⟨fun h => h, fun h => h⟩

/-- Uniform limits in `C(↥halfDisc)` restrict to uniformly convergent
sequences of the holomorphic extensions, on the half-disc. -/
theorem tendstoUniformlyOn_toHalfHol {u : ℕ → C(↥halfDisc, ℂ)}
    {x : C(↥halfDisc, ℂ)} (hu : Tendsto u atTop (𝓝 x)) :
    TendstoUniformlyOn (fun n => toHalfHol (u n)) (toHalfHol x) atTop halfDisc := by
  rw [tendstoUniformlyOn_iff]
  intro ε hε
  obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp hu ε hε)
  refine Filter.Eventually.mono (Filter.eventually_ge_atTop N) fun n hn => ?_
  intro w hw
  have hdist : dist (u n) x < ε := hN n hn
  rw [toHalfHol_apply x w hw, toHalfHol_apply (u n) w hw, dist_eq_norm]
  calc ‖x ⟨w, hw⟩ - u n ⟨w, hw⟩‖ = ‖(u n - x) ⟨w, hw⟩‖ := by
        rw [ContinuousMap.sub_apply, norm_sub_rev]
    _ ≤ ‖u n - x‖ := ContinuousMap.norm_coe_le_norm _ _
    _ = dist (u n) x := (dist_eq_norm (u n) x).symm
    _ < ε := hdist

/-- **Weierstrass theorem for the half-disc algebra.** The half-disc algebra
is sequentially closed in `C(↥halfDisc)`: uniform limits of holomorphic
functions on the interior are holomorphic
(`TendstoLocallyUniformlyOn.differentiableOn`). -/
theorem isSeqClosed_halfDiscAlgebra :
    IsSeqClosed (halfDiscAlgebra : Set C(↥halfDisc, ℂ)) := by
  intro u p hu hx
  refine (mem_halfDiscAlgebra p).mpr ?_
  have hunif := tendstoUniformlyOn_toHalfHol hx
  have hunifBall : TendstoUniformlyOn (fun n => toHalfHol (u n)) (toHalfHol p) atTop
      (interior halfDisc) := hunif.mono interior_subset
  exact TendstoLocallyUniformlyOn.differentiableOn hunifBall.tendstoLocallyUniformlyOn
    (Eventually.of_forall fun n => (mem_halfDiscAlgebra (u n)).mp (hu n))
    isOpen_interior

/-- The half-disc algebra is closed in `C(↥halfDisc)`. -/
theorem isClosed_halfDiscAlgebra : IsClosed (halfDiscAlgebra : Set C(↥halfDisc, ℂ)) :=
  isSeqClosed_iff_isClosed.mp isSeqClosed_halfDiscAlgebra

/-- **The half-disc algebra is a Banach space.** -/
instance halfDiscAlgebra_complete : CompleteSpace halfDiscAlgebra := by
  rw [completeSpace_iff_isComplete_univ, Subtype.isComplete_iff]
  have himg : ((↑) '' (univ : Set halfDiscAlgebra)) =
      (halfDiscAlgebra : Set C(↥halfDisc, ℂ)) := by
    ext y
    constructor
    · rintro ⟨y', -, rfl⟩
      exact SetLike.mem_coe.mpr y'.2
    · intro hy
      exact ⟨⟨y, hy⟩, mem_univ _, rfl⟩
  rw [himg]
  exact isClosed_halfDiscAlgebra.isComplete

/-! ### The uniform Cauchy estimate -/

/-- **Uniform Cauchy estimate on the half-disc algebra.** If a ball of radius
`R` around `w` lies in the interior of the half-disc, then the derivative of
the holomorphic extension of any algebra element at `w` is bounded by twice
its sup norm over `R` — the equicontinuity input for Arzelà–Ascoli. -/
theorem norm_deriv_toHalfHol_le (f : C(↥halfDisc, ℂ)) (hf : f ∈ halfDiscAlgebra)
    (M : ℝ) (hM : ‖f‖ ≤ M) (w : ℂ) (R : ℝ) (hR : 0 < R)
    (hsub : ball w R ⊆ interior halfDisc) :
    ‖deriv (toHalfHol f) w‖ ≤ 2 * M / R := by
  have hder : ‖deriv (toHalfHol f) w‖ ≤ (2 * M) / R := by
    refine Complex.norm_deriv_le_div_of_mapsTo_ball
      (((mem_halfDiscAlgebra f).mp hf).mono hsub) ?_ hR
    intro z hz
    have hzK : z ∈ halfDisc := interior_subset (hsub hz)
    have hwK : w ∈ halfDisc := interior_subset (hsub (mem_ball_self hR))
    refine mem_closedBall.mpr ?_
    rw [dist_eq_norm]
    have hz' : ‖toHalfHol f z‖ ≤ M := by
      rw [toHalfHol_apply f z hzK]
      exact le_trans (ContinuousMap.norm_coe_le_norm f ⟨z, hzK⟩) hM
    have hw' : ‖toHalfHol f w‖ ≤ M := by
      rw [toHalfHol_apply f w hwK]
      exact le_trans (ContinuousMap.norm_coe_le_norm f ⟨w, hwK⟩) hM
    have htri : ‖toHalfHol f z - toHalfHol f w‖ ≤ ‖toHalfHol f z‖ + ‖toHalfHol f w‖ :=
      norm_sub_le _ _
    linarith
  exact hder

end

end Riemann
