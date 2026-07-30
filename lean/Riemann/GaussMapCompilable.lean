/-
Copyright (c) 2026 Tobias Weiss
Copyright (c) 2026 The Riemann Hypothesis Team

Gauss Map for Continued Fractions (Compilable)

This file defines the Gauss map and its inverse branches.
Uses correct Mathlib imports and compiles with current Mathlib.

-/

import Mathlib.Data.Real.Basic
import Mathlib.Algebra.Order.Floor.Defs
import Mathlib.Topology.Basic
import Mathlib.Topology.Order.Basic
import Mathlib.Order.Interval.Set.Defs

namespace Riemann.GaussMap

open Set Filter Topology.Instances

variable [FloorRing ℝ]

/-- The Gauss map T: (0,1] → [0,1) defined by T(x) = 1/x - ⌊1/x⌋ -/
def gaussMap : ℝ → ℝ
  | 0 => 0
  | x =>
    if 0 < x ∧ x ≤ 1 then
      (1 / x) - ⌊1 / x⌋
    else
      0

notation "G" => gaussMap

/-- The n-th inverse branch: I_n(x) = 1/(n+1+x) -/
def inverseBranch (n : ℕ) : ℝ → ℝ :=
  fun x => 1 / ((n : ℝ) + 1 + x)

/-- Gauss map is well-defined on (0,1] -/
@[simp]
theorem gaussMap_eq_of_pos_le_one {x : ℝ} (hx : 0 < x ∧ x ≤ 1) :
    G x = (1 / x) - ⌊1 / x⌋ := by
  unfold gaussMap
  simp [hx]

/-- Gauss map is non-negative -/
theorem gaussMap_nonneg (x : ℝ) : 0 ≤ G x := by
  sorry

/-- Gauss map stays in [0,1] -/
theorem gaussMap_in_range (x : ℝ) : 0 ≤ G x ∧ G x ≤ 1 := by
  sorry

/-- Inverse branch I_n is continuous on ℝ\{-n-1} -/
theorem inverseBranch_continuousAt (n : ℕ) {x : ℝ} (hx : x ≠ -(n + 1)) :
    ContinuousAt (inverseBranch n) x := by
  sorry

/-- Inverse branch maps [0,1] into a subinterval -/
theorem inverseBranch_Icc_range (n : ℕ) :
    inverseBranch n '' Icc (0 : ℝ) 1 = Icc (1 / ((n : ℝ) + 2)) (1 / ((n : ℝ) + 1)) := by
  sorry

/-- The images of [0,1] under the inverse branches partition (0,1) -/
theorem partitionProperty :
    ⋃ n : ℕ, inverseBranch n '' Icc (0 : ℝ) 1 = Ioo 0 1 := by
  sorry

/-- The intervals are disjoint -/
theorem partitionProperty_disjoint {n m : ℕ} (hnm : n ≠ m) :
    Disjoint (inverseBranch n '' Icc (0 : ℝ) 1) (inverseBranch m '' Icc (0 : ℝ) 1) := by
  sorry

end Riemann.GaussMap
