/-
Copyright (c) 2026 Tobias Weiss

Gauss map for continued fractions and its inverse branches.

The Gauss map `T : (0,1] → [0,1)`, `T x = 1/x - ⌊1/x⌋`, generates the regular
continued-fraction expansion. Its inverse branches `Iₙ x = 1/(n+1+x)` map the
unit interval onto the partition intervals `[1/(n+2), 1/(n+1)]`; these form a
generating partition of `(0,1]`, the combinatorial backbone of the transfer
operator approach to the Selberg zeta function (Mayer's model).
-/

import Mathlib.Topology.Algebra.Ring.Real
import Mathlib.Algebra.Order.Floor.Ring

namespace Riemann.GaussMap

open Set

/-! ### Definitions -/

/-- The Gauss map `T x = 1/x - ⌊1/x⌋` on `(0,1]`, extended by `0` elsewhere. -/
noncomputable def gaussMap (x : ℝ) : ℝ :=
  if 0 < x ∧ x ≤ 1 then (1 / x) - ⌊1 / x⌋ else 0

/-- The `n`-th inverse branch of the Gauss map: `Iₙ x = 1/(n+1+x)`. -/
noncomputable def inverseBranch (n : ℕ) : ℝ → ℝ :=
  fun x => 1 / ((n : ℝ) + 1 + x)

/-! ### Basic properties of the Gauss map -/

/-- On `(0,1]` the Gauss map is the fractional part of `1/x`. -/
theorem gaussMap_eq_of_pos_le_one {x : ℝ} (hx : 0 < x ∧ x ≤ 1) :
    gaussMap x = (1 / x) - ⌊1 / x⌋ := by
  unfold gaussMap
  rw [if_pos hx]

/-- The Gauss map is nonnegative. -/
theorem gaussMap_nonneg (x : ℝ) : 0 ≤ gaussMap x := by
  unfold gaussMap
  split
  · exact Int.fract_nonneg _
  · rfl

/-- The Gauss map takes values in `[0,1]`. -/
theorem gaussMap_in_range (x : ℝ) : 0 ≤ gaussMap x ∧ gaussMap x ≤ 1 := by
  unfold gaussMap
  split
  · exact ⟨Int.fract_nonneg _, Int.fract_lt_one _ |>.le⟩
  · exact ⟨le_refl 0, zero_le_one⟩

/-! ### Continuity of the inverse branches -/

/-- Each inverse branch is continuous away from its pole `x = -(n+1)`. -/
theorem inverseBranch_continuousAt (n : ℕ) {x : ℝ} (hx : x ≠ -((n : ℝ) + 1)) :
    ContinuousAt (inverseBranch n) x := by
  have hne : ((n : ℝ) + 1 + x) ≠ 0 := by
    intro h
    apply hx
    linarith
  have hcont : ContinuousAt (fun y : ℝ => ((n : ℝ) + 1) + y) x :=
    continuousAt_const.add continuousAt_id
  have hfun : inverseBranch n = fun y => ((n : ℝ) + 1 + y)⁻¹ := by
    funext y
    simp [inverseBranch]
  rw [hfun]
  exact ContinuousAt.inv₀ hcont hne

/-! ### The branch partition -/

/-- The inverse branch maps `[0,1]` onto `[1/(n+2), 1/(n+1)]`. -/
theorem inverseBranch_Icc_range (n : ℕ) :
    inverseBranch n '' Icc (0 : ℝ) 1 = Icc (1 / ((n : ℝ) + 2)) (1 / ((n : ℝ) + 1)) := by
  have hp1 : (0 : ℝ) < (n : ℝ) + 1 := by positivity
  have hp2 : (0 : ℝ) < (n : ℝ) + 2 := by positivity
  ext y
  constructor
  · rintro ⟨x, hx, rfl⟩
    rw [mem_Icc] at hx ⊢
    have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
    have hpx : (0 : ℝ) < (n : ℝ) + 1 + x := by linarith
    exact ⟨(div_le_div_iff₀ hp2 hpx).2 (by linarith),
      (div_le_div_iff₀ hpx hp1).2 (by linarith)⟩
  · rintro ⟨hy0, hy1⟩
    have hypos : (0 : ℝ) < y := lt_of_lt_of_le (div_pos one_pos hp2) hy0
    refine ⟨1 / y - ((n : ℝ) + 1), ?_, ?_⟩
    · rw [mem_Icc]
      constructor
      · -- `0 ≤ 1/y - (n+1)` reduces to `(n+1) * y ≤ 1`
        rw [sub_nonneg, le_div_iff₀ hypos]
        exact (mul_le_mul_of_nonneg_left hy1 hp1.le).trans (mul_one_div_cancel (ne_of_gt hp1)).le
      · -- `1/y - (n+1) ≤ 1` reduces to `1 ≤ (n+2) * y`
        have key2 : (1 : ℝ) ≤ ((n : ℝ) + 1 + 1) * y := by
          have h22 : ((n : ℝ) + 1 + 1) = (n : ℝ) + 2 := by ring
          rw [h22]
          have h := mul_le_mul_of_nonneg_left hy0 hp2.le
          rwa [mul_one_div_cancel (ne_of_gt hp2)] at h
        rw [sub_le_iff_le_add', div_le_iff₀ hypos]
        exact key2
    · -- the witness maps back to `y`
      have hden : (n : ℝ) + 1 + (1 / y - ((n : ℝ) + 1)) = 1 / y := by ring
      simp only [inverseBranch]
      rw [hden, one_div_one_div]

/-- The closed branch images cover `(0,1]`:
`⋃ n, Iₙ '' [0,1] = (0,1]`. -/
theorem partitionProperty :
    ⋃ n : ℕ, inverseBranch n '' Icc (0 : ℝ) 1 = Ioc (0 : ℝ) 1 := by
  ext y
  simp only [mem_iUnion, mem_image, mem_Ioc]
  constructor
  · rintro ⟨n, x, ⟨hx0, hx1⟩, rfl⟩
    simp only [inverseBranch]
    have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
    have hpx : (0 : ℝ) < (n : ℝ) + 1 + x := by linarith
    exact ⟨div_pos one_pos hpx, by rw [div_le_one hpx]; linarith⟩
  · rintro ⟨hy0, hy1⟩
    -- pick `n = ⌊1/y⌋₊ - 1`: then `n+1 = ⌊1/y⌋₊ ≤ 1/y ≤ ⌊1/y⌋₊ + 1 = n+2`
    have hu1 : (1 : ℝ) ≤ 1 / y := (one_le_div hy0).2 hy1
    have hk1 : 1 ≤ ⌊1 / y⌋₊ := (Nat.one_le_floor_iff _).2 hu1
    have hkle : ((⌊1 / y⌋₊ : ℕ) : ℝ) ≤ 1 / y := Nat.floor_le (one_div_pos.2 hy0).le
    have hklt : 1 / y < ((⌊1 / y⌋₊ : ℕ) : ℝ) + 1 := Nat.lt_floor_add_one _
    have hrn1 : (((⌊1 / y⌋₊ - 1 : ℕ) : ℝ)) + 1 = ((⌊1 / y⌋₊ : ℕ) : ℝ) := by
      have hk0 : ⌊1 / y⌋₊ ≠ 0 := by omega
      have h := congrArg (Nat.cast (R := ℝ)) (Nat.sub_one_add_one hk0)
      rwa [Nat.cast_add_one] at h
    refine ⟨⌊1 / y⌋₊ - 1, 1 / y - (((⌊1 / y⌋₊ - 1 : ℕ) : ℝ) + 1), ⟨by linarith, by linarith⟩,
      ?_⟩
    have hden : ((⌊1 / y⌋₊ : ℕ) : ℝ) + (1 / y - ((⌊1 / y⌋₊ : ℕ) : ℝ)) = 1 / y := by ring
    simp only [inverseBranch]
    rw [hrn1, hden, one_div_one_div]

/-- The images of the open unit interval under distinct inverse branches are
disjoint. (The closed branch images overlap at their endpoints — e.g. `1/2`
lies in both `I₀ '' [0,1]` and `I₁ '' [0,1]` — so disjointness is stated for
the interiors; equivalently, the half-open images `[1/(n+2), 1/(n+1))` form a
genuine partition of `(0,1)`.) -/
theorem partitionProperty_disjoint {n m : ℕ} (hnm : n ≠ m) :
    Disjoint (inverseBranch n '' Ioo (0 : ℝ) 1) (inverseBranch m '' Ioo (0 : ℝ) 1) := by
  rw [Set.disjoint_iff_inter_eq_empty, Set.eq_empty_iff_forall_notMem]
  rintro y ⟨⟨x, hx, hxe⟩, z, hz, hze⟩
  rw [mem_Ioo] at hx hz
  have heq : inverseBranch n x = inverseBranch m z := hxe.trans hze.symm
  simp only [inverseBranch] at heq
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have hmm : (0 : ℝ) ≤ (m : ℝ) := Nat.cast_nonneg m
  have hA : ((n : ℝ) + 1 + x) ≠ 0 := by linarith
  have hB : ((m : ℝ) + 1 + z) ≠ 0 := by linarith
  field_simp at heq
  rcases lt_or_gt_of_ne hnm with h | h
  · have hnm1 : ((n : ℝ)) + 1 ≤ (m : ℝ) := by exact_mod_cast Nat.succ_le_of_lt h
    linarith
  · have hnm1 : ((m : ℝ)) + 1 ≤ (n : ℝ) := by exact_mod_cast Nat.succ_le_of_lt h
    linarith

end Riemann.GaussMap
