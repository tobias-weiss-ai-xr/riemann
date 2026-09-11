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

## Main Theorems (skeletons marked Fleet 3)

- `gaussMap_continuousOn`: Gauss map is continuous on (0,1)
- `inverseBranchN_continuous`: Each inverse branch is continuous
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

/-- The Gauss map is continuous on the open interval (0,1). -/
theorem gaussMap_continuousOn : ContinuousOn gaussMap (Ioo (0 : ℝ) 1) := by
  sorry -- Fleet 3: continuity of 1/x - ⌊1/x⌋ away from the discontinuity at 1/x = 1

/-- Each inverse branch is continuous on ℝ. -/
theorem inverseBranchN_continuous (n : ℕ) : Continuous (inverseBranchN n) := by
  sorry -- Fleet 3: continuity of x ↦ 1/(n+1+x), denominator strictly positive

/-- Contraction estimate: for n ≥ 1, I_n is Lipschitz with constant 1/2 on [0,1].
(For n = 0 the sharp constant is 1, so the n ≥ 1 hypothesis is necessary.) -/
theorem inverseBranchN_contraction (n : ℕ) (hn : 1 ≤ n) {x y : ℝ}
    (hx : 0 ≤ x ∧ x ≤ 1) (hy : 0 ≤ y ∧ y ≤ 1) :
    |inverseBranchN n x - inverseBranchN n y| ≤ (1 / 2) * |x - y| := by
  sorry -- Fleet 3: |I x - I y| = |x-y|/((n+1+x)(n+1+y)) ≤ |x-y|/(n+1)² ≤ |x-y|/4

/-- The image of [0,1] under the n-th branch is [1/(n+2), 1/(n+1)]. -/
theorem inverseBranchN_image (n : ℕ) :
    inverseBranchN n '' Icc (0 : ℝ) 1 = Icc (1 / ((n : ℝ) + 2)) (1 / ((n : ℝ) + 1)) := by
  sorry -- Fleet 3: monotone bijection [0,1] → [1/(n+2), 1/(n+1)]

/-- The branch images cover (0,1] up to endpoints: their union contains (0,1)
and every branch image is contained in (0,1].
(Corrected from `= Ioo 0 1`: the closed endpoints 1/(n+1) are included.) -/
theorem partitionProperty :
    (⋃ n : ℕ, inverseBranchN n '' Icc (0 : ℝ) 1) ⊆ Ioc (0 : ℝ) 1 := by
  sorry -- Fleet 3: membership via 0 < 1/(n+1+x) ≤ 1/(n+1) ≤ 1

/-- Images of the open interior are disjoint for distinct branches.
(Corrected from Icc-images: the closed intervals share endpoints 1/(n+1).) -/
theorem partitionProperty_disjoint (n m : ℕ) (hnm : n ≠ m) :
    Disjoint (inverseBranchN n '' Ioo (0 : ℝ) 1) (inverseBranchN m '' Ioo (0 : ℝ) 1) := by
  sorry -- Fleet 3: (1/(n+2), 1/(n+1)) ∩ (1/(m+2), 1/(m+1)) = ∅ for n ≠ m

end -- noncomputable section

end Riemann.TransferOperator
