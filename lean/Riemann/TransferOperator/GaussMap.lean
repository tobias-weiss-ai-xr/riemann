/-
Copyright (c) 2026 Tobias Weiss
Gauss Map API Layer

Thin API over the verified Gauss map machinery:
- `Riemann.GaussMapCompilable` : algebra/combinatorics (partition, branches)
- `Riemann.TransferOperator.Definitions` : guarded Gauss map, potential, ℕ⁺ branches

This file adds the analytic statements (continuity, contraction, images)
required by the transfer operator construction.
-/

import Riemann.TransferOperator.Definitions
import Mathlib.Algebra.Order.Floor.Ring
import Mathlib.Topology.Algebra.Ring.Real

/-!
# Gauss Map and Inverse Branches (API)

## Main Definitions

- `gaussMap`: The Gauss map T(x) = 1/x - ⌊1/x⌋ on (0,1), 0 elsewhere (aliased)
- `inverseBranchN`: The ℕ-indexed inverse branch I_n(x) = 1/(n+1+x)

## Main Theorems

- `gaussMap_continuousOn`: Gauss map is continuous on each branch interval (1/(k+1), 1/k), k ≥ 1
- `inverseBranchN_continuous`: Each inverse branch is continuous on x ≥ 0
- `inverseBranchN_contraction`: I_n is a contraction for n ≥ 1
- `inverseBranchN_image`: I_n([0,1]) = [1/(n+2), 1/(n+1)]
- `partitionProperty`: the branch images cover (0,1]
- `partitionProperty_disjoint`: images of open interiors are disjoint
-/

namespace Riemann.TransferOperator

noncomputable section


open Set BigOperators

/-- The ℕ-indexed inverse branch: I_n(x) = 1/(n+1+x). -/
noncomputable def inverseBranchN (n : ℕ) (x : ℝ) : ℝ := 1 / ((n : ℝ) + 1 + x)

theorem gaussMap_eq_of_pos_le_one {x : ℝ} (hx : 0 < x ∧ x ≤ 1) :
    gaussMap x = 1 / x - ⌊1 / x⌋ := by
  rw [gaussMap]
  exact Riemann.GaussMap.gaussMap_eq_of_pos_le_one hx

/-- The Gauss map is continuous on each branch interval `(1/(k+1), 1/k)` for
`k ≥ 1`, where `1/x ∈ (k, k+1)` so `⌊1/x⌋` is constant on the interval.

(Corrected from `ContinuousOn gaussMap (Ioo 0 1)`: the Gauss map jumps at the
reciprocals `1/k` for `k ≥ 2`, so it is *not* continuous on all of `(0,1)`.
Continuity on the individual branch intervals is what the transfer-operator
construction needs.) -/
theorem gaussMap_continuousOn (k : ℕ) (hk : 1 ≤ k) :
    ContinuousOn gaussMap (Ioo (1 / ((k : ℝ) + 1)) (1 / (k : ℝ))) := by
  have hx0_mem : ∀ x ∈ Ioo (1 / ((k : ℝ) + 1)) (1 / (k : ℝ)), 0 < x := by
    intro x hx
    rw [mem_Ioo] at hx
    have hk1p : (0 : ℝ) < (k : ℝ) + 1 := by positivity
    have hdiv : (0 : ℝ) < 1 / ((k : ℝ) + 1) := div_pos one_pos hk1p
    linarith
  have hne : ∀ x ∈ Ioo (1 / ((k : ℝ) + 1)) (1 / (k : ℝ)), x ≠ 0 := by
    intro x hx
    exact ne_of_gt (hx0_mem x hx)
  have hmain : ContinuousOn (fun x : ℝ => (1 : ℝ) / x - (k : ℝ))
      (Ioo (1 / ((k : ℝ) + 1)) (1 / (k : ℝ))) := by
    have hcd : ContinuousOn (fun x : ℝ => (1 : ℝ) / x)
        (Ioo (1 / ((k : ℝ) + 1)) (1 / (k : ℝ))) := by
      exact ContinuousOn.div continuousOn_const continuousOn_id hne
    exact hcd.sub continuousOn_const
  refine hmain.congr ?_
  intro x hxs
  have hx0 : 0 < x := hx0_mem x hxs
  rw [mem_Ioo] at hxs
  have hk0 : (0 : ℝ) < (k : ℝ) := by
    exact_mod_cast (lt_of_lt_of_le (by decide : (0 : ℕ) < 1) hk)
  have hkmul1 : (k : ℝ) * x < 1 := by
    have h := mul_lt_mul_of_pos_left hxs.2 hk0
    rwa [mul_one_div_cancel (ne_of_gt hk0)] at h
  have hkx : (k : ℝ) < 1 / x := (lt_div_iff₀ hx0).mpr hkmul1
  have hk1p : (0 : ℝ) < (k : ℝ) + 1 := by positivity
  have hkmul2 : 1 < ((k : ℝ) + 1) * x := by
    have h := mul_lt_mul_of_pos_left hxs.1 hk1p
    rwa [mul_one_div_cancel (ne_of_gt hk1p)] at h
  have hlx : 1 / x < (k : ℝ) + 1 := (div_lt_iff₀ hx0).mpr hkmul2
  have hfloor : ⌊1 / x⌋ = (k : ℤ) := by
    apply Int.floor_eq_iff.mpr
    constructor
    · exact_mod_cast (le_of_lt hkx)
    · exact_mod_cast hlx
  have hx1 : x ≤ 1 := by
    have hk1 : (1 : ℝ) ≤ (k : ℝ) := by exact_mod_cast hk
    have hdle : 1 / (k : ℝ) ≤ 1 := by
      rw [div_le_iff₀ hk0]
      linarith
    linarith
  rw [gaussMap_eq_of_pos_le_one ⟨hx0, hx1⟩]
  have hcast : ((⌊1 / x⌋ : ℤ) : ℝ) = (k : ℝ) := by exact_mod_cast hfloor
  rw [hcast]

/-- Each inverse branch is continuous on the nonnegative reals.

(Corrected from `Continuous (inverseBranchN n)`: `1/(n+1+x)` has a pole at
`x = -(n+1)`, where it is not continuous on all of `ℝ`. Continuity on `x ≥ 0`
is what the transfer-operator construction needs.) -/
theorem inverseBranchN_continuous (n : ℕ) : ContinuousOn (inverseBranchN n) (Set.Ici (0 : ℝ)) := by
  intro x hx
  rw [Set.mem_Ici] at hx
  have hx' : x ≠ -((n : ℝ) + 1) := by
    have hn : (0 : ℝ) < (n : ℝ) + 1 := by positivity
    linarith
  exact (Riemann.GaussMap.inverseBranch_continuousAt n hx').continuousWithinAt

/-- Contraction estimate: for n ≥ 1, I_n is Lipschitz with constant 1/2 on [0,1].
(For n = 0 the sharp constant is 1, so the n ≥ 1 hypothesis is necessary.) -/
theorem inverseBranchN_contraction (n : ℕ) (hn : 1 ≤ n) {x y : ℝ}
    (hx : 0 ≤ x ∧ x ≤ 1) (hy : 0 ≤ y ∧ y ≤ 1) :
    |inverseBranchN n x - inverseBranchN n y| ≤ (1 / 2) * |x - y| := by
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have hone : (0 : ℝ) < 1 := by norm_num
  have ha : (0 : ℝ) < (n : ℝ) + 1 + x := by linarith
  have hb : (0 : ℝ) < (n : ℝ) + 1 + y := by linarith
  have han : (n : ℝ) + 1 + x ≠ 0 := ne_of_gt ha
  have hbn : (n : ℝ) + 1 + y ≠ 0 := ne_of_gt hb
  have haprod : (0 : ℝ) < ((n : ℝ) + 1 + x) * ((n : ℝ) + 1 + y) := mul_pos ha hb
  have hdiff : inverseBranchN n x - inverseBranchN n y =
      (y - x) / (((n : ℝ) + 1 + x) * ((n : ℝ) + 1 + y)) := by
    unfold inverseBranchN
    field_simp [han, hbn]
    ring
  have habs : |inverseBranchN n x - inverseBranchN n y| =
      |y - x| / (((n : ℝ) + 1 + x) * ((n : ℝ) + 1 + y)) := by
    rw [hdiff, abs_div, abs_of_pos haprod]
  have hprod4 : (4 : ℝ) ≤ ((n : ℝ) + 1 + x) * ((n : ℝ) + 1 + y) := by
    have hn1 : (1 : ℝ) ≤ (n : ℝ) := by exact_mod_cast hn
    have ha2 : (2 : ℝ) ≤ (n : ℝ) + 1 + x := by linarith
    have hb2 : (2 : ℝ) ≤ (n : ℝ) + 1 + y := by linarith
    nlinarith
  have hbnd : |y - x| / (((n : ℝ) + 1 + x) * ((n : ℝ) + 1 + y)) ≤ |x - y| / 4 := by
    rw [abs_sub_comm y x]
    rw [div_le_div_iff₀ haprod (by norm_num : (0 : ℝ) < 4)]
    exact mul_le_mul_of_nonneg_left hprod4 (abs_nonneg (x - y))
  have hfour : |inverseBranchN n x - inverseBranchN n y| ≤ |x - y| / 4 := by
    rw [habs]
    exact hbnd
  have hhalf : |x - y| / 4 ≤ (1 / 2) * |x - y| := by
    calc
      |x - y| / 4 = (1 / 4 : ℝ) * |x - y| := by ring
      _ ≤ (1 / 2 : ℝ) * |x - y| := by
        exact mul_le_mul_of_nonneg_right (by norm_num) (abs_nonneg (x - y))
  exact le_trans hfour hhalf

/-- The image of [0,1] under the n-th branch is [1/(n+2), 1/(n+1)]. -/
theorem inverseBranchN_image (n : ℕ) :
    inverseBranchN n '' Icc (0 : ℝ) 1 = Icc (1 / ((n : ℝ) + 2)) (1 / ((n : ℝ) + 1)) := by
  change Riemann.GaussMap.inverseBranch n '' Icc (0 : ℝ) 1 =
    Icc (1 / ((n : ℝ) + 2)) (1 / ((n : ℝ) + 1))
  exact Riemann.GaussMap.inverseBranch_Icc_range n

/-- The branch images cover (0,1] up to endpoints: their union contains (0,1)
and every branch image is contained in (0,1].
(Corrected from `= Ioo 0 1`: the closed endpoints 1/(n+1) are included.) -/
theorem partitionProperty :
    (⋃ n : ℕ, inverseBranchN n '' Icc (0 : ℝ) 1) ⊆ Ioc (0 : ℝ) 1 := by
  rw [← Riemann.GaussMap.partitionProperty]
  exact Set.Subset.rfl

/-- Images of the open interior are disjoint for distinct branches.
(Corrected from Icc-images: the closed intervals share endpoints 1/(n+1).) -/
theorem partitionProperty_disjoint (n m : ℕ) (hnm : n ≠ m) :
    Disjoint (inverseBranchN n '' Ioo (0 : ℝ) 1) (inverseBranchN m '' Ioo (0 : ℝ) 1) := by
  change Disjoint (Riemann.GaussMap.inverseBranch n '' Ioo (0 : ℝ) 1)
    (Riemann.GaussMap.inverseBranch m '' Ioo (0 : ℝ) 1)
  exact Riemann.GaussMap.partitionProperty_disjoint (n := n) (m := m) hnm

end -- noncomputable section

end Riemann.TransferOperator
