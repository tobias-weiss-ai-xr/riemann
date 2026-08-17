/-
Copyright (c) 2026 Tobias Weiss
Gauss Map for Continued Fractions

This file defines the Gauss map and its basic properties:
- The Gauss map: T(x) = 1/x - ⌊1/x⌋
- Inverse branches: I_n(x) = 1/(n+x)
- Basic properties such as contraction, measure preservation, etc.

Author: Tobias Weiss
References:
- Mayer, G. (1990). "The Riemann zeta function and the transfer operator"
- Baladi, V. (2000). "Positive Transfer Operators and Decay of Correlations"
-/

import Mathlib.Data.Real.BigOperators
import Mathlib.Data.Nat.Floor
import Mathlib.Analysis.SpecialFunctions.Pow.Complex
import Mathlib.MeasureTheory.Function.ConditionalExpect
import Mathlib.MeasureTheory.Measure.Haar

/-!
# Gauss Map and Inverse Branches

This module defines the Gauss map used in the continued fraction expansion and the
inverse branches needed for the transfer operator definition.

## Main Definitions

- `gaussMap`: The Gauss map T(x) = 1/x - ⌊1/x⌋
- `inverseBranch`: The inverse branch I_n(x) = 1/(n+1+x)

## Main Theorems

- `gaussMap_continuousOn`: Gauss map is continuous on (0,1]
- `inverseBranch_continuous`: Each inverse branch is continuous on [0,1]
- `inverseBranch_contraction`: I_n is a contraction with Lipschitz constant ≤ 1/2
- `partitionProperty`: The intervals I_n([0,1]) partition (0,1]

-/

namespace Riemann.TransferOperator

noncomputable section

open Real BigOperators Set Filter

/-- The Gauss map T: (0,1] → [0,1) defined by T(x) = 1/x - ⌊1/x⌋ -/
def gaussMap : ℝ → ℝ
  | 0 => 0
  | x =>
    if 0 < x ≤ 1 then
      (1 / x) - ⌊1 / x⌋
    else
      0

notation "T" => gaussMap

/-- The n-th inverse branch of the Gauss map: I_n(x) = 1/(n+1+x) -/
noncomputable def inverseBranch (n : ℕ) : ℝ → ℝ :=
  fun x => 1 / (n + 1 + x)

notation "I" n fun x => inverseBranch n x

theorem gaussMap_eq (x : ℝ) (hx : 0 < x ∧ x ≤ 1) :
    gaussMap x = (1 / x) - ⌊(1 / x)⌋ := by
  unfold gaussMap
  simp [hx]

@[aesop safe 80%]
theorem gaussMap_nonneg (x : ℝ) : 0 ≤ gaussMap x := by
  by_cases hx : 0 < x ∧ x ≤ 1
  · rw [gaussMap_eq x hx]
    have : 0 ≤ 1 / x - ⌊(1 / x)⌋
    apply sub_nonneg.2
    exact Nat.floor_le (one_div_pos.2 hx.1)
    sorry
  · unfold gaussMap
    simp [hx]

@[aesop safe 80%]
theorem gaussMap_le_one (x : ℝ) : gaussMap x ≤ 1 := by
  sorry

theorem gaussMap_continuousOn : ContinuousOn gaussMap ((0 : ℝ)..1) := by
  sorry

theorem inverseBranch_continuous (n : ℕ) : Continuous (inverseBranch n) := by
  sorry

theorem inverseBranch_contraction (n : ℕ) {x y : ℝ} (hx : 0 ≤ x ∧ x ≤ 1) (hy : 0 ≤ y ∧ y ≤ 1) :
    |inverseBranch n x - inverseBranch n y| ≤ (1 / 2) * |x - y| := by
  sorry

theorem inverseBranch_image (n : ℕ) :
    inverseBranch n '' [0, 1] = Icc (1 / (n + 2)) (1 / (n + 1)) := by
  sorry

theorem partitionProperty :
    (⋃ n : ℕ, inverseBranch n '' [0, 1]) = Ioo 0 1 := by
  sorry

theorem partitionProperty_disjoint (n m : ℕ) (hnm : n ≠ m) :
    Disjoint (inverseBranch n '' [0, 1]) (inverseBranch m '' [0, 1]) := by
  sorry

end TransferOperator

end Riemann
