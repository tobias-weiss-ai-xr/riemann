/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Mathlib.Combinatorics.SimpleGraph.Basic
import Mathlib.Combinatorics.SimpleGraph.Cayley
import Mathlib.Combinatorics.SimpleGraph.Connectivity.Connected
import Mathlib.Combinatorics.SimpleGraph.Finite
import Mathlib.Data.ZMod.Basic
import Mathlib.Data.Matrix.Basic
import Mathlib.Data.Fintype.Card
import Mathlib.Data.Nat.PrimeFin
import Mathlib.FieldTheory.Finite.Basic
import Mathlib.GroupTheory.Index
import Mathlib.LinearAlgebra.Matrix.SpecialLinearGroup
import Mathlib.LinearAlgebra.Matrix.Determinant.Basic
import Mathlib.LinearAlgebra.Matrix.Adjugate
import Mathlib.LinearAlgebra.Matrix.GeneralLinearGroup.Card
import Mathlib.LinearAlgebra.Matrix.GeneralLinearGroup.Defs

open SimpleGraph
open Matrix
open SpecialLinearGroup

/-! # SL(2, F_p) Cayley Graphs

This file defines the Cayley graphs of `SL(2, F_p)` with respect to the
standard generators `S` and `R`, forming the foundation for spectral analysis
connected to the Riemann hypothesis.

## Main definitions

* `SL2Fp p` : the group `SL(2, ZMod p)`
* `SL2Fp.generators` : the standard generating set `{S, S⁻¹, R, R⁻¹}`
* `SL2Fp.cayleyGraph` : the Cayley graph of `SL(2, F_p)` with respect to `generators`
* `SL2Fp.groupOrder` : `|SL(2, F_p)| = p(p² - 1)`
* `SL2Fp.isFourRegular` : the Cayley graph is 4-regular
* `SL2Fp.isVertexTransitive` : the Cayley graph is vertex-transitive

## References

* Lubotzky, Phillips, Sarnak (1988). Ramanujan graphs. *Combinatorica* 8(3), 261-277.
* Pizer, A. (1990). Ramanujan graphs and Hecke operators. *Bull. AMS* 23(1), 127-137.
-/

namespace Riemann

open SpecialLinearGroup

/-- `SL(2, F_p)` — the group of 2×2 matrices over `ZMod p` with determinant 1. -/
abbrev SL2Fp (p : ℕ) [Fact (Nat.Prime p)] : Type :=
  SpecialLinearGroup (Fin 2) (ZMod p)

section SL2FpProperties

variable (p : ℕ) [Fact (Nat.Prime p)]

/-- The cardinality of `SL(2, F_p)` is `p(p² - 1)`. -/
theorem card_sl2fp : Fintype.card (SL2Fp p) = p * (p ^ 2 - 1) := by
  let G := GL (Fin 2) (ZMod p)
  let μ := (ZMod p)ˣ
  let φ : G →* μ := GeneralLinearGroup.det

  -- |GL(2,F_p)| = p(p-1)(p²-1) from Matrix.card_GL_field
  have hGL_card : Nat.card G = p * (p - 1) * (p ^ 2 - 1) := by
    have hp_prime : Nat.Prime p := Fact.out
    have hp_ge2 : 2 ≤ p := Nat.Prime.two_le hp_prime
    have hp_sq_sub_p : p ^ 2 - p = p * (p - 1) := by
      calc
        p ^ 2 - p = p * p - p := by simp [pow_two]
        _ = p * p - p * 1 := by simp
        _ = p * (p - 1) := by rw [← Nat.mul_sub_left_distrib]
    calc
      Nat.card G = ∏ i : Fin 2, ((Fintype.card (ZMod p) : ℕ) ^ 2 -
        (Fintype.card (ZMod p) : ℕ) ^ (i : ℕ)) :=
        Matrix.card_GL_field (n := 2) (𝔽 := ZMod p)
      _ = ((Fintype.card (ZMod p)) ^ 2 - (Fintype.card (ZMod p)) ^ (0 : ℕ)) *
          ((Fintype.card (ZMod p)) ^ 2 - (Fintype.card (ZMod p)) ^ (1 : ℕ)) := by
        simp
      _ = (p ^ 2 - 1) * (p ^ 2 - p) := by
        simp [ZMod.card]
      _ = (p ^ 2 - 1) * (p * (p - 1)) := by rw [hp_sq_sub_p]
      _ = p * (p - 1) * (p ^ 2 - 1) := by
        simp [mul_assoc, mul_comm]

  -- |(ZMod p)ˣ| = p - 1
  have hμ_card : Nat.card μ = p - 1 := by
    rw [Nat.card_eq_fintype_card, ZMod.card_units p]

  -- det is surjective
  have hφ_surj : Function.Surjective φ := GeneralLinearGroup.det_surjective

  -- ker(φ) ≅ SL(2,F_p) via toGL
  have hker_SL_card : Nat.card φ.ker = Nat.card (SL2Fp p) := by
    let f : φ.ker → SL2Fp p := λ g => ⟨(g : G).val, by
      have hφ1 : φ (g : G) = 1 := g.property
      have hdetval : (GeneralLinearGroup.det (g : G)).val = (1 : μ).val := congrArg Units.val hφ1
      simpa [GeneralLinearGroup.det, Units.val_one] using hdetval
    ⟩
    let finv : SL2Fp p → φ.ker := λ s => ⟨toGL s, by
      rw [MonoidHom.mem_ker, coeToGL_det s]⟩
    have h_left : ∀ g, finv (f g) = g := by
      intro g
      -- Matrix equality: toGL(f g) and (g : G) have the same underlying matrix
      have hmat : ((toGL (f g) : G).val) = ((g : G).val) := by
        calc
          ((toGL (f g) : G).val) = (f g).val := coe_GL_coe_matrix (f g)
          _ = (g : G).val := rfl
      -- G = GL(2,F_p) = Units of Matrix, so use Units.ext
      have hGL_eq : (toGL (f g) : G) = (g : G) := Units.ext hmat
      -- ker-level equality follows (finv (f g) has G-value toGL(f g))
      have h_val_eq : (finv (f g) : φ.ker).val = (g : φ.ker).val := calc
        (finv (f g) : φ.ker).val = (toGL (f g) : G) := rfl
        _ = (g : G) := hGL_eq
        _ = (g : φ.ker).val := rfl
      -- Apply Subtype.val_injective at the φ.ker Subtype
      exact Subtype.val_injective h_val_eq
    have h_right : ∀ s, f (finv s) = s := by
      intro s
      apply Subtype.ext
      simp [f, finv, coe_GL_coe_matrix]
    refine Nat.card_congr (Equiv.ofBijective f ⟨?_, λ s => ⟨finv s, h_right s⟩⟩)
    intro x y h
    apply Subtype.val_injective
    calc
      (x : G) = (finv (f x) : φ.ker).val := by
        have hx := h_left x; rw [hx]
      _ = (finv (f y) : φ.ker).val := by rw [h]
      _ = (y : G) := by
        have hy := h_left y; rw [hy]

  -- First isomorphism theorem: G/ker(φ) ≅ μ
  have h_quot_card : Nat.card (G ⧸ φ.ker) = Nat.card μ := by
    apply Nat.card_congr (QuotientGroup.quotientKerEquivOfSurjective φ hφ_surj).toEquiv

  -- Lagrange: |G| = |ker φ| * |G/ker φ|
  have h_lagrange : Nat.card G = Nat.card φ.ker * Nat.card (G ⧸ φ.ker) := by
    rw [Subgroup.card_eq_card_quotient_mul_card_subgroup φ.ker, mul_comm]

  -- Combine: |SL| * (p-1) = |G| = p(p-1)(p²-1)
  have h_combined : Nat.card (SL2Fp p) * (p - 1) = p * (p - 1) * (p ^ 2 - 1) := by
    calc
      Nat.card (SL2Fp p) * (p - 1) = Nat.card φ.ker * (p - 1) := by rw [hker_SL_card]
      _ = Nat.card φ.ker * Nat.card μ := by rw [hμ_card]
      _ = Nat.card φ.ker * Nat.card (G ⧸ φ.ker) := by rw [h_quot_card]
      _ = Nat.card G := by rw [h_lagrange]
      _ = p * (p - 1) * (p ^ 2 - 1) := hGL_card

  -- Since p ≥ 2 (prime), p-1 ≥ 1, so we can cancel
  have hp1_pos : 0 < p - 1 := by
    have hp_prime : Nat.Prime p := Fact.out
    have hp_ge_2 : 2 ≤ p := Nat.Prime.two_le hp_prime
    omega

  have h_card_nat : Nat.card (SL2Fp p) = p * (p ^ 2 - 1) := by
    have h_mul : Nat.card (SL2Fp p) * (p - 1) = (p * (p ^ 2 - 1)) * (p - 1) := by
      calc
        Nat.card (SL2Fp p) * (p - 1) = p * (p - 1) * (p ^ 2 - 1) := h_combined
        _ = (p * (p ^ 2 - 1)) * (p - 1) := by ring
    exact Nat.eq_of_mul_eq_mul_right hp1_pos h_mul

  -- Convert to Fintype.card
  rw [← Nat.card_eq_fintype_card, h_card_nat]

/-- Standard generator `S = [[0, -1], [1, 0]]` of `SL(2, F_p)`. -/
def generatorS : SL2Fp p :=
  ⟨!![0, -1; 1, 0], by
    rw [det_fin_two_of]
    ring
  ⟩

/-- Standard generator `R = [[1, 1], [0, 1]]` of `SL(2, F_p)`. -/
def generatorR : SL2Fp p :=
  ⟨!![1, 1; 0, 1], by
    rw [det_fin_two_of]
    ring
  ⟩

/-- The standard symmetric generating set `{S, S⁻¹, R, R⁻¹}` of `SL(2, F_p)`. -/
def generators : Set (SL2Fp p) :=
  {generatorS p, (generatorS p)⁻¹, generatorR p, (generatorR p)⁻¹}

/-- A set `s` is symmetric if it is closed under inverses. -/
def SetSymmetric (s : Set (SL2Fp p)) : Prop := ∀ g ∈ s, g⁻¹ ∈ s

/-- The generating set is symmetric (closed under inverses). -/
theorem generators_symmetric : SetSymmetric p (generators p) := by
  intro g hg
  simp [generators] at hg ⊢
  rcases hg with (hg|hg|hg|hg)
  · -- g = S → g⁻¹ = S⁻¹ ∈ generators
    rw [hg]
    exact Or.inr (Or.inl rfl)
  · -- g = S⁻¹ → g⁻¹ = S ∈ generators
    rw [hg, inv_inv]
    exact Or.inl rfl
  · -- g = R → g⁻¹ = R⁻¹ ∈ generators
    rw [hg]
    exact Or.inr (Or.inr (Or.inr rfl))
  · -- g = R⁻¹ → g⁻¹ = R ∈ generators
    rw [hg, inv_inv]
    exact Or.inr (Or.inr (Or.inl rfl))

/-- The generating set does not contain the identity. -/
theorem generators_not_id : (1 : SL2Fp p) ∉ generators p := by
  have hS_ne_one : generatorS p ≠ 1 := by
    intro h
    have hM : (generatorS p).val = (1 : SL2Fp p).val := congrArg Subtype.val h
    have h00_S : (generatorS p).val 0 0 = (0 : ZMod p) := by
      simp [generatorS]
    have h00_1 : (1 : SL2Fp p).val 0 0 = (1 : ZMod p) := by
      simp
    have hzero_one : (0 : ZMod p) = (1 : ZMod p) := by
      calc
        (0 : ZMod p) = (generatorS p).val 0 0 := by symm; exact h00_S
        _ = (1 : SL2Fp p).val 0 0 := by rw [hM]
        _ = (1 : ZMod p) := h00_1
    have h0_ne_1 : (0 : ZMod p) ≠ (1 : ZMod p) := by
      apply zero_ne_one
    exact h0_ne_1 hzero_one
  have hR_ne_one : generatorR p ≠ 1 := by
    intro h
    have hM : (generatorR p).val = (1 : SL2Fp p).val := congrArg Subtype.val h
    have h01_R : (generatorR p).val 0 1 = (1 : ZMod p) := by
      simp [generatorR]
    have h01_1 : (1 : SL2Fp p).val 0 1 = (0 : ZMod p) := by
      simp
    have h_one_zero : (1 : ZMod p) = (0 : ZMod p) := by
      calc
        (1 : ZMod p) = (generatorR p).val 0 1 := by symm; exact h01_R
        _ = (1 : SL2Fp p).val 0 1 := by rw [hM]
        _ = (0 : ZMod p) := h01_1
    have h0_ne_1 : (0 : ZMod p) ≠ (1 : ZMod p) := by
      apply zero_ne_one
    exact h0_ne_1 h_one_zero.symm
  intro hmem
  simp [generators, Set.mem_insert_iff, Set.mem_singleton_iff] at hmem
  rcases hmem with (hmem|hmem|hmem|hmem)
  · exact hS_ne_one hmem.symm
  · apply hS_ne_one
    calc
      generatorS p = ((generatorS p)⁻¹)⁻¹ := by simp
      _ = 1⁻¹ := by
        rw [hmem]
        simp
      _ = 1 := by simp
  · exact hR_ne_one hmem.symm
  · apply hR_ne_one
    calc
      generatorR p = ((generatorR p)⁻¹)⁻¹ := by simp
      _ = 1⁻¹ := by
        rw [hmem]
        simp
      _ = 1 := by simp

/-- A graph is vertex-transitive if its automorphism group acts transitively
on the vertices. For a Cayley graph, left multiplication by any group element
gives an automorphism, establishing vertex-transitivity. -/
def VertexTransitiveGraph (G : SimpleGraph (SL2Fp p)) : Prop :=
  ∀ (v w : SL2Fp p), ∃ (f : G →g G), f v = w

/-- The Cayley graph of `SL(2, F_p)` with respect to the standard generating set.
This is a 4-regular, vertex-transitive graph with |V| = p(p² - 1). -/
abbrev cayleyGraph : SimpleGraph (SL2Fp p) :=
  SimpleGraph.mulCayley (generators p)

/-- The Cayley graph is locally finite since SL(2,F_p) is a finite group. -/
noncomputable instance : (cayleyGraph p).LocallyFinite :=
  fun _ => Fintype.ofFinite _

theorem isFourRegular (hp2 : p ≠ 2) : (cayleyGraph p).IsRegularOfDegree 4 := by
  intro v
  -- generators as a Finset for cardinality computations
  let gensFinset : Finset (SL2Fp p) :=
    {generatorS p, (generatorS p)⁻¹, generatorR p, (generatorR p)⁻¹}
  have hgens_card : gensFinset.card = 4 := by
    -- Lemma: for p ≠ 2, -1 ≠ 1 in ZMod p
    have h_neg_one_ne_one : (-1 : ZMod p) ≠ (1 : ZMod p) := by
      intro h_eq
      apply hp2
      have h2_zero : (2 : ZMod p) = 0 := by
        calc
          (2 : ZMod p) = (1 : ZMod p) + (1 : ZMod p) := by norm_num
          _ = (-1 : ZMod p) + (1 : ZMod p) := by rw [h_eq]
          _ = 0 := by ring
      have hp_dvd_2 : p ∣ 2 :=
        (CharP.cast_eq_zero_iff (ZMod p) p 2).mp h2_zero
      -- Since 2 is prime and p ∣ 2, we must have p = 2
      have hp_prime : Nat.Prime p := Fact.out
      have hp_cases : p = 1 ∨ p = 2 :=
        (Nat.prime_two : Nat.Prime 2).eq_one_or_self_of_dvd p hp_dvd_2
      rcases hp_cases with (h_one | h_two)
      · -- p = 1, but p is prime (contradiction) — so we can prove p = 2
        have h_not_prime_one : ¬Nat.Prime 1 := by decide
        exact (h_not_prime_one (h_one ▸ hp_prime)).elim
      · -- p = 2, we needed exactly this
        exact h_two
    
    -- Matrix entries of inverses computed via the adjugate formula.
    -- S = [[0,-1],[1,0]], so S⁻¹ = adj(S) = [[0,1],[-1,0]].
    -- R = [[1,1],[0,1]], so R⁻¹ = adj(R) = [[1,-1],[0,1]].
    have hSinv_01 : ((generatorS p)⁻¹).val 0 1 = (1 : ZMod p) := by
      simp [generatorS, adjugate_fin_two]
    have hRinv_01 : ((generatorR p)⁻¹).val 0 1 = (-1 : ZMod p) := by
      simp [generatorR, adjugate_fin_two]
    
    -- All 6 pairwise distinctness proofs
    have hS_ne_Sinv : generatorS p ≠ (generatorS p)⁻¹ := by
      intro h_eq
      have h01 : (generatorS p).val 0 1 = ((generatorS p)⁻¹).val 0 1 :=
        congrArg (fun x : SL2Fp p => x.val 0 1) h_eq
      have hS01 : (generatorS p).val 0 1 = (-1 : ZMod p) := by simp [generatorS]
      rw [hS01, hSinv_01] at h01
      exact h_neg_one_ne_one h01
    
    have hR_ne_Rinv : generatorR p ≠ (generatorR p)⁻¹ := by
      intro h_eq
      have h01 : (generatorR p).val 0 1 = ((generatorR p)⁻¹).val 0 1 :=
        congrArg (fun x : SL2Fp p => x.val 0 1) h_eq
      have hR01 : (generatorR p).val 0 1 = (1 : ZMod p) := by simp [generatorR]
      rw [hR01, hRinv_01] at h01
      exact h_neg_one_ne_one h01.symm
    
    have hS_ne_R : generatorS p ≠ generatorR p := by
      intro h_eq
      have h00 : (generatorS p).val 0 0 = (generatorR p).val 0 0 :=
        congrArg (fun x : SL2Fp p => x.val 0 0) h_eq
      have hS00 : (generatorS p).val 0 0 = (0 : ZMod p) := by simp [generatorS]
      have hR00 : (generatorR p).val 0 0 = (1 : ZMod p) := by simp [generatorR]
      rw [hS00, hR00] at h00
      exact zero_ne_one h00
    
    have hS_ne_Rinv : generatorS p ≠ (generatorR p)⁻¹ := by
      intro h_eq
      have h00 : (generatorS p).val 0 0 = ((generatorR p)⁻¹).val 0 0 :=
        congrArg (fun x : SL2Fp p => x.val 0 0) h_eq
      have hS00 : (generatorS p).val 0 0 = (0 : ZMod p) := by simp [generatorS]
      have hRinv00 : ((generatorR p)⁻¹).val 0 0 = (1 : ZMod p) := by
        simp [generatorR, adjugate_fin_two]
      rw [hS00, hRinv00] at h00
      exact zero_ne_one h00
    
    have hSinv_ne_R : (generatorS p)⁻¹ ≠ generatorR p := by
      intro h_eq
      have h00 : ((generatorS p)⁻¹).val 0 0 = (generatorR p).val 0 0 :=
        congrArg (fun x : SL2Fp p => x.val 0 0) h_eq
      have hSinv00 : ((generatorS p)⁻¹).val 0 0 = (0 : ZMod p) := by
        simp [generatorS, adjugate_fin_two]
      have hR00 : (generatorR p).val 0 0 = (1 : ZMod p) := by simp [generatorR]
      rw [hSinv00, hR00] at h00
      exact zero_ne_one h00
    
    have hSinv_ne_Rinv : (generatorS p)⁻¹ ≠ (generatorR p)⁻¹ := by
      intro h_eq
      have h00 : ((generatorS p)⁻¹).val 0 0 = ((generatorR p)⁻¹).val 0 0 :=
        congrArg (fun x : SL2Fp p => x.val 0 0) h_eq
      have hSinv00 : ((generatorS p)⁻¹).val 0 0 = (0 : ZMod p) := by
        simp [generatorS, adjugate_fin_two]
      have hRinv00 : ((generatorR p)⁻¹).val 0 0 = (1 : ZMod p) := by
        simp [generatorR, adjugate_fin_two]
      rw [hSinv00, hRinv00] at h00
      exact zero_ne_one h00
    
    -- With all 6 pairwise distinctness, the Finset has cardinal 4
    simp [gensFinset, hS_ne_Sinv, hR_ne_Rinv, hS_ne_R, hS_ne_Rinv, hSinv_ne_R, hSinv_ne_Rinv]
  have hgens_set : (gensFinset : Set (SL2Fp p)) = generators p := by
    ext g; simp [gensFinset, generators]
  -- The neighborFinset of v equals the image of generators under left multiplication
  have h_neighbor : (cayleyGraph p).neighborFinset v = gensFinset.image (v * ·) := by
    ext w
    constructor
    · intro hw
      rw [mem_neighborFinset] at hw
      rw [mulCayley_adj'] at hw
      rcases hw with ⟨h_ne, h_ex⟩
      rcases h_ex with ⟨g, hg, (h_eq | h_eq_rev)⟩
      · -- w = v * g
        apply Finset.mem_image.mpr
        refine ⟨g, ?_, h_eq⟩
        have hg_set : g ∈ (gensFinset : Set (SL2Fp p)) := by
          rw [hgens_set]; exact hg
        exact Finset.mem_coe.mp hg_set
      · -- v = w * g  →  w = v * g⁻¹
        have hg_inv : g⁻¹ ∈ generators p := generators_symmetric p g hg
        apply Finset.mem_image.mpr
        refine ⟨g⁻¹, ?_, ?_⟩
        · -- show g⁻¹ ∈ gensFinset
          have hg_inv_set : g⁻¹ ∈ (gensFinset : Set (SL2Fp p)) := by
            rw [hgens_set]; exact hg_inv
          exact Finset.mem_coe.mp hg_inv_set
        · calc
            v * g⁻¹ = (w * g) * g⁻¹ := by rw [h_eq_rev]
            _ = w * (g * g⁻¹) := by simp [mul_assoc]
            _ = w := by simp
    · intro hw
      rcases Finset.mem_image.1 hw with ⟨g, hg, h_eq⟩
      have hg_gen : g ∈ generators p := by
        simpa [hgens_set] using Finset.mem_coe.mpr hg
      have h_ne : v ≠ v * g := by
        intro h_eq_v
        have hg_one : g = 1 :=
          mul_left_cancel (calc
            v * g = v := h_eq_v.symm
            _ = v * 1 := by simp)
        exact generators_not_id p (hg_one ▸ hg_gen)
      have h_ne_w : v ≠ w := by
        intro h_eq_vw
        apply h_ne
        calc
          v = w := h_eq_vw
          _ = v * g := h_eq.symm
      rw [mem_neighborFinset, mulCayley_adj']
      refine ⟨h_ne_w, g, hg_gen, Or.inl h_eq⟩
  -- Compute degree
  calc
    (cayleyGraph p).degree v = Finset.card ((cayleyGraph p).neighborFinset v) := by
      rw [← card_neighborFinset_eq_degree]
    _ = Finset.card (gensFinset.image (v * ·)) := by rw [h_neighbor]
    _ = Finset.card gensFinset :=
      Finset.card_image_of_injective gensFinset (mul_right_injective v)
    _ = 4 := hgens_card

/-- Left multiplication by any group element `g` is a graph homomorphism
from the Cayley graph to itself. -/
def leftMulHom (g : SL2Fp p) : cayleyGraph p →g cayleyGraph p :=
  { toFun := fun u => g * u
    map_rel' := by
      intro u v hadj
      rw [mulCayley_adj' (generators p)] at hadj ⊢
      rcases hadj with ⟨h_ne, h⟩
      refine ⟨by
        -- if g*u = g*v, then u = v, contradiction
        intro h_eq
        apply h_ne
        exact mul_right_injective g h_eq, ?_⟩
      rcases h with ⟨gen, hgen, (h_eq | h_eq)⟩
      · -- u * gen = v
        refine ⟨gen, hgen, Or.inl ?_⟩
        calc
          (g * u) * gen = g * (u * gen) := by simp [mul_assoc]
          _ = g * v := by rw [h_eq]
      · -- u = v * gen
        refine ⟨gen, hgen, Or.inr ?_⟩
        calc
          g * u = g * (v * gen) := by rw [h_eq]
          _ = (g * v) * gen := by simp [mul_assoc] }

/-- The Cayley graph is vertex-transitive. -/
theorem isVertexTransitive : VertexTransitiveGraph p (cayleyGraph p) := by
  intro v w
  -- left multiplication by w * v⁻¹ sends v to w
  refine ⟨leftMulHom (g := w * v⁻¹), ?_⟩
  simp [leftMulHom]

/-- The set of vertices reachable from the identity forms a subgroup of SL(2,F_p).

Proof:
- Contains 1 (reflexivity of reachability).
- Closed under multiplication: if `Reachable 1 x` and `Reachable 1 y`, then
  `leftMulHom p x` is an automorphism (by `leftMulHom` and `Reachable.map`),
  giving `Reachable x (x*y)`. Composing `1 → x → x*y` yields `Reachable 1 (x*y)`.
- Closed under inverses: the reverse walk `Reachable x 1` (from symmetry),
  mapped through `leftMulHom p (x⁻¹)`, gives `Reachable 1 (x⁻¹)`. -/
def reachableFromOneSubgroup : Subgroup (SL2Fp p) where
  carrier := {g | (cayleyGraph p).Reachable (1 : SL2Fp p) g}
  one_mem' := Reachable.refl (G := cayleyGraph p) (u := (1 : SL2Fp p))
  mul_mem' := by
    intro x y hx hy
    -- leftMulHom p x maps 1→x and y→x*y; apply Reachable.map
    have h_f_walk : (cayleyGraph p).Reachable
        (leftMulHom p x (1 : SL2Fp p))
        (leftMulHom p x y) :=
      Reachable.map (leftMulHom p x) hy
    have h_1 : leftMulHom p x (1 : SL2Fp p) = x := by simp [leftMulHom]
    have h_y : leftMulHom p x y = x * y := by simp [leftMulHom]
    rw [h_1, h_y] at h_f_walk
    exact hx.trans h_f_walk
  inv_mem' := by
    intro x hx
    have hx_symm : (cayleyGraph p).Reachable x (1 : SL2Fp p) := hx.symm
    -- leftMulHom p (x⁻¹) maps x→1 and 1→x⁻¹
    have h_f_walk : (cayleyGraph p).Reachable
        (leftMulHom p (x⁻¹ : SL2Fp p) x)
        (leftMulHom p (x⁻¹ : SL2Fp p) (1 : SL2Fp p)) :=
      Reachable.map (leftMulHom p (x⁻¹)) hx_symm
    have h_x : leftMulHom p (x⁻¹ : SL2Fp p) x = 1 := by simp [leftMulHom]
    have h_1 : leftMulHom p (x⁻¹ : SL2Fp p) (1 : SL2Fp p) = x⁻¹ := by simp [leftMulHom]
    rw [h_x, h_1] at h_f_walk
    exact h_f_walk

/-- For the Cayley graph, each generator is adjacent to the identity,
hence reachable from it. -/
lemma generator_in_reachableFromOne (x : SL2Fp p) (hx : x ∈ generators p) :
    x ∈ reachableFromOneSubgroup p := by
  have h_one_notin : (1 : SL2Fp p) ∉ generators p := generators_not_id p
  have hx_not_one : x ≠ 1 := by
    intro h_eq
    apply h_one_notin
    rwa [← h_eq]
  have h_adj : (cayleyGraph p).Adj (1 : SL2Fp p) x := by
    rw [mulCayley_adj' (generators p)]
    refine ⟨Ne.symm hx_not_one, ?_⟩
    use x
    exact ⟨hx, Or.inl (by simp)⟩
  exact h_adj.reachable

/-- The Cayley graph is connected.

Proof: The set of reachable-from-1 vertices forms a subgroup
(`reachableFromOneSubgroup`). Since each generator is reachable from 1,
the subgroup generated by the generators is contained in this subgroup.
S and R generate SL(2,F_p) (a standard group-theoretic fact), so the
subgroup is the whole group. By vertex-transitivity, any two vertices
are connected via 1 (using symmetry of `Reachable`). -/
theorem isConnected : (cayleyGraph p).Connected := by
  -- Show the generators are contained in the reachable-from-1 subgroup
  have h_gens_in_reachable : (generators p : Set (SL2Fp p)) ⊆
      (reachableFromOneSubgroup p : Set (SL2Fp p)) :=
    generator_in_reachableFromOne p
  -- The subgroup generated by the generators is contained in reachableFromOneSubgroup.
  -- Since generators generate the full group, reachableFromOneSubgroup = ⊤.
  have h_subgroup : Subgroup.closure (generators p : Set (SL2Fp p)) ≤
      reachableFromOneSubgroup p :=
    (Subgroup.closure_le (k := generators p) (K := reachableFromOneSubgroup p)).mpr
      h_gens_in_reachable
  have h_full : Subgroup.closure (generators p : Set (SL2Fp p)) = ⊤ := by
    let H := Subgroup.closure (generators p : Set (SL2Fp p))
    have hS : generatorS p ∈ H :=
      Subgroup.subset_closure (by simp [generators])
    have hR : generatorR p ∈ H :=
      Subgroup.subset_closure (by simp [generators])
    have hSinv : (generatorS p)⁻¹ ∈ H := H.inv_mem hS
    have hRpow (k : ℕ) : (generatorR p) ^ k ∈ H := H.pow_mem hR k
    -- Matrix entries of R^k
    have hRpow_val (k : ℕ) : ((generatorR p) ^ k).val = !![1, (k : ZMod p); 0, 1] := by
      induction k with
      | zero =>
        simp [generatorR, coe_one, Matrix.one_fin_two]
      | succ k ih =>
        have hstep : ((generatorR p) ^ (k+1)).val = !![1, (↑(k+1) : ZMod p); 0, 1] := by
          calc
            ((generatorR p) ^ (k+1)).val = (((generatorR p) ^ k) * (generatorR p)).val := by
              rw [pow_succ]
            _ = ((generatorR p) ^ k).val * (generatorR p).val := by simp
            _ = !![1, (k : ZMod p); 0, 1] * !![1, 1; 0, 1] := by rw [ih, generatorR]
            _ = !![1, (↑k + 1 : ZMod p); 0, 1] := by
              rw [Matrix.mul_fin_two]; simp [add_comm]
            _ = !![1, (↑(k+1) : ZMod p); 0, 1] := by simp
        exact hstep
    -- Lemma: (t.val : ZMod p) = t
    have h_val_cast (t : ZMod p) : (t.val : ZMod p) = t := by
      simpa using ZMod.nat_cast_zmod_val t
    -- Inverse of generatorS
    have hSinv_val : ((generatorS p)⁻¹).val = !![0, 1; -1, 0] := by
      have := SL2_inv_expl (generatorS p)
      simpa [generatorS] using congrArg Subtype.val this
    -- Diagonal matrices diag(t, t⁻¹) are in H
    have h_diag (t : ZMod p) (ht : t ≠ 0) :
        (⟨!![t, 0; 0, t⁻¹], by
          rw [det_fin_two_of]; have h_mul : t * t⁻¹ = 1 := mul_inv_cancel₀ ht; simp [h_mul]⟩ : SL2Fp p) ∈ H := by
      set n := t.val with hn_def
      set m := (t⁻¹).val with hm_def
      have hn_val : (n : ZMod p) = t := by
        rw [hn_def, h_val_cast]
      have hm_val : (m : ZMod p) = t⁻¹ := by
        rw [hm_def, h_val_cast]
      have h_prod : (generatorS p)⁻¹ * (generatorR p) ^ m * (generatorS p) *
          (generatorR p) ^ n * (generatorS p) * (generatorR p) ^ m ∈ H := by
        repeat' apply H.mul_mem
        · exact hSinv
        · exact hRpow m
        · exact hS
        · exact hRpow n
        · exact hS
        · exact hRpow m
      -- Show this product equals the diagonal matrix
      have h_eq_val : ((generatorS p)⁻¹ * (generatorR p) ^ m * (generatorS p) *
          (generatorR p) ^ n * (generatorS p) * (generatorR p) ^ m).val = !![t, 0; 0, t⁻¹] := by
        calc
          ((generatorS p)⁻¹ * (generatorR p) ^ m * (generatorS p) *
            (generatorR p) ^ n * (generatorS p) * (generatorR p) ^ m).val
              = ((generatorS p)⁻¹).val * ((generatorR p) ^ m).val * (generatorS p).val *
                ((generatorR p) ^ n).val * (generatorS p).val * ((generatorR p) ^ m).val := by
            simp [coe_mul]
          _ = !![0, 1; -1, 0] * !![1, (m : ZMod p); 0, 1] * !![0, -1; 1, 0] *
              !![1, (n : ZMod p); 0, 1] * !![0, -1; 1, 0] * !![1, (m : ZMod p); 0, 1] := by
            simp [generatorS, hRpow_val, hSinv_val]
          _ = !![0, 1; -1, 0] * !![1, t⁻¹; 0, 1] * !![0, -1; 1, 0] *
              !![1, t; 0, 1] * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1] := by
            simp [hn_val, hm_val]
          _ = !![t, 0; 0, t⁻¹] := by
            calc
              !![0, 1; -1, 0] * !![1, t⁻¹; 0, 1] * !![0, -1; 1, 0] *
                !![1, t; 0, 1] * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1]
                  = ((!![0, 1; -1, 0] * !![1, t⁻¹; 0, 1]) * !![0, -1; 1, 0]) *
                    !![1, t; 0, 1] * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1] := by ring
              _ = (!![0, 1; -1, -t⁻¹] * !![0, -1; 1, 0]) *
                    !![1, t; 0, 1] * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1] := by
                rw [Matrix.mul_fin_two]; simp
              _ = !![1, 0; -t⁻¹, 1] *
                    !![1, t; 0, 1] * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1] := by
                rw [Matrix.mul_fin_two]; simp
              _ = (!![1, 0; -t⁻¹, 1] * !![1, t; 0, 1]) * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1] := by ring
              _ = !![1, t; -t⁻¹, -t⁻¹*t + 1] * !![0, -1; 1, 0] * !![1, t⁻¹; 0, 1] := by
                rw [Matrix.mul_fin_two]; simp
              _ = (!![1, t; -t⁻¹, -t⁻¹*t + 1] * !![0, -1; 1, 0]) * !![1, t⁻¹; 0, 1] := by ring
              _ = !![t, -1; -t⁻¹*t + 1, t⁻¹] * !![1, t⁻¹; 0, 1] := by
                rw [Matrix.mul_fin_two]; simp
              _ = !![t, t*t⁻¹ - 1; -t⁻¹*t + 1, (-t⁻¹*t + 1)*t⁻¹ + t⁻¹] := by
                rw [Matrix.mul_fin_two]
                simp [mul_comm, add_comm, sub_eq_add_neg]
              _ = !![t, 0; 0, t⁻¹] := by
                have h_mul : t * t⁻¹ = 1 := mul_inv_cancel₀ ht
                have h_mul' : t⁻¹ * t = 1 := by rw [mul_comm, h_mul]
                ext <;> simp [h_mul, h_mul', mul_comm, add_comm]
      have h_eq : ((generatorS p)⁻¹ * (generatorR p) ^ m * (generatorS p) *
          (generatorR p) ^ n * (generatorS p) * (generatorR p) ^ m : SL2Fp p) =
          (⟨!![t, 0; 0, t⁻¹], by
            rw [det_fin_two_of]; have h_mul : t * t⁻¹ = 1 := mul_inv_cancel₀ ht; simp [h_mul]⟩ : SL2Fp p) :=
        Subtype.ext h_eq_val
      rw [h_eq] at h_prod
      exact h_prod
    -- Now show every SL(2,F_p) matrix is in H via Gauss-Jordan reduction
    apply (Subgroup.eq_top_iff' (H := H)).mpr
    intro g
    induction g using Matrix.SpecialLinearGroup.fin_two_induction with
    | h a b c d hdet =>
      have had : a * d - b * c = 1 := hdet
      by_cases hc : c = 0
      · -- Case c = 0: then ad = 1, so d = a⁻¹ and a ≠ 0
        have ha0 : a ≠ 0 := by
          intro ha0
          have : a * d = 0 := by simp [ha0]
          have hzero : a * d - b * c = 0 := by simp [hc, this]
          rw [hzero] at had
          exact zero_ne_one had
        have ha_mul_ad : a * d = 1 := by
          calc
            a * d = a * d - b * c := by simp [hc]
            _ = 1 := had
        have ha_inv_mul : a⁻¹ * a = 1 := by
          calc
            a⁻¹ * a = a * a⁻¹ := mul_comm _ _
            _ = 1 := mul_inv_cancel₀ ha0
        have hd : d = a⁻¹ := by
          calc
            d = 1 * d := by simp
            _ = (a⁻¹ * a) * d := by simp [ha_inv_mul]
            _ = a⁻¹ * (a * d) := by ring
            _ = a⁻¹ * 1 := by rw [ha_mul_ad]
            _ = a⁻¹ := by simp
        -- A = [[a, b], [0, a⁻¹]]. Right-multiply by R^(-b*a⁻¹) to get diag(a, a⁻¹)
        let A_diag : SL2Fp p := ⟨!![a, 0; 0, a⁻¹], by
          rw [det_fin_two_of]; have ha_mul : a * a⁻¹ = 1 := mul_inv_cancel₀ ha0; simp [ha_mul]⟩
        have hA_eq_val : (⟨!![a, b; 0, a⁻¹], by
            rw [det_fin_two_of]; have ha_mul : a * a⁻¹ = 1 := mul_inv_cancel₀ ha0; simp [ha_mul]⟩ : SL2Fp p).val =
            (A_diag * (generatorR p) ^ ((b * a⁻¹).val : ℕ)).val := by
          calc
            (⟨!![a, b; 0, a⁻¹], by
                rw [det_fin_two_of]; have ha_mul : a * a⁻¹ = 1 := mul_inv_cancel₀ ha0; simp [ha_mul]⟩ : SL2Fp p).val
                = !![a, b; 0, a⁻¹] := rfl
            _ = A_diag.val * ((generatorR p) ^ ((b * a⁻¹).val : ℕ)).val := by
              calc
                !![a, b; 0, a⁻¹] = !![a, 0; 0, a⁻¹] * !![1, b*a⁻¹; 0, 1] := by
                  rw [Matrix.mul_fin_two]
                  have ha_mul' : a * a⁻¹ = 1 := mul_inv_cancel₀ ha0
                  have h_eq : a * (b * a⁻¹) = b := by
                    calc
                      a * (b * a⁻¹) = (a * b) * a⁻¹ := by simp [mul_assoc]
                      _ = (b * a) * a⁻¹ := by rw [mul_comm a b]
                      _ = b * (a * a⁻¹) := by simp [mul_assoc]
                      _ = b * 1 := by rw [ha_mul']
                      _ = b := by simp
                  simp [ha_mul', h_eq]
                _ = A_diag.val * ((generatorR p) ^ ((b * a⁻¹).val : ℕ)).val := by
                  simp [A_diag, hRpow_val ((b * a⁻¹).val), h_val_cast (b * a⁻¹)]
            _ = (A_diag * (generatorR p) ^ ((b * a⁻¹).val : ℕ)).val := by simp
        have hA_eq : (⟨!![a, b; 0, a⁻¹], by
            rw [det_fin_two_of]; have ha_mul : a * a⁻¹ = 1 := mul_inv_cancel₀ ha0; simp [ha_mul]⟩ : SL2Fp p) =
            A_diag * (generatorR p) ^ ((b * a⁻¹).val : ℕ) :=
          Subtype.ext hA_eq_val
        have hA_target : (⟨!![a, b; c, d], by rwa [det_fin_two_of]⟩ : SL2Fp p) =
            (⟨!![a, b; 0, a⁻¹], by
              rw [det_fin_two_of]; have ha_mul : a * a⁻¹ = 1 := mul_inv_cancel₀ ha0; simp [ha_mul]⟩ : SL2Fp p) := by
          ext; simp [hc, hd]
        rw [hA_target, hA_eq]
        exact H.mul_mem (h_diag a ha0) (hRpow ((b * a⁻¹).val : ℕ))
      · -- Case c ≠ 0: use Bruhat decomposition R^x * D * S * R^y = A
        have hc0 : c ≠ 0 := hc
        have hc_inv : c⁻¹ ≠ 0 := inv_ne_zero hc0
        -- Set x = a*c⁻¹, y = d*c⁻¹, D = diag(c⁻¹, c)
        set x := a * c⁻¹ with hx_def
        set y := d * c⁻¹ with hy_def
        have h_c_inv_mul : c⁻¹ * c = 1 := by
          calc
            c⁻¹ * c = c * c⁻¹ := mul_comm _ _
            _ = 1 := mul_inv_cancel₀ hc0
        have hD_det : det !![c⁻¹, 0; 0, c] = 1 := by
          rw [det_fin_two_of]
          simp [h_c_inv_mul]
        let D : SL2Fp p := ⟨!![c⁻¹, 0; 0, c], hD_det⟩
        have hA_expr : (⟨!![a, b; c, d], by rwa [det_fin_two_of]⟩ : SL2Fp p) =
            (generatorR p) ^ (x.val : ℕ) * D * (generatorS p) * (generatorR p) ^ (y.val : ℕ) := by
          apply Subtype.ext
          calc
            (⟨!![a, b; c, d], by rwa [det_fin_two_of]⟩ : SL2Fp p).val = !![a, b; c, d] := rfl
            _ = !![1, a * c⁻¹; 0, 1] * !![c⁻¹, 0; 0, c] * !![0, -1; 1, 0] * !![1, d * c⁻¹; 0, 1] :=
              (calc
                !![1, a * c⁻¹; 0, 1] * !![c⁻¹, 0; 0, c] * !![0, -1; 1, 0] * !![1, d * c⁻¹; 0, 1]
                    = ((!![1, a*c⁻¹; 0, 1] * !![c⁻¹, 0; 0, c]) * !![0, -1; 1, 0]) *
                      !![1, d*c⁻¹; 0, 1] := by ring
                _ = (!![c⁻¹, a*c⁻¹*c; 0, c] * !![0, -1; 1, 0]) *
                      !![1, d*c⁻¹; 0, 1] := by
                  rw [Matrix.mul_fin_two]; simp
                _ = !![a*c⁻¹*c, -c⁻¹; c, 0] * !![1, d*c⁻¹; 0, 1] := by
                  rw [Matrix.mul_fin_two]; simp
                _ = !![a*c⁻¹*c, a*c⁻¹*c*d*c⁻¹ - c⁻¹; c, c*d*c⁻¹] := by
                  rw [Matrix.mul_fin_two]; simp [mul_assoc, h_c_inv_mul, sub_eq_add_neg]
                _ = !![a, b; c, d] := by
                  ext i j <;> fin_cases i <;> fin_cases j
                  · -- (0,0): a*c⁻¹*c = a
                    calc
                      a*c⁻¹*c = a*(c⁻¹*c) := by simp [mul_assoc]
                      _ = a*1 := by rw [h_c_inv_mul]
                      _ = a := by simp
                  · -- (0,1): a*c⁻¹*c*d*c⁻¹ - c⁻¹ = b
                    calc
                      a*c⁻¹*c*d*c⁻¹ - c⁻¹ = (a*(c⁻¹*c))*d*c⁻¹ - c⁻¹ := by simp [mul_assoc]
                      _ = (a*1)*d*c⁻¹ - c⁻¹ := by rw [h_c_inv_mul]
                      _ = a*d*c⁻¹ - c⁻¹ := by simp
                      _ = (a*d)*c⁻¹ - 1*c⁻¹ := by simp
                      _ = (a*d - 1)*c⁻¹ := by rw [sub_mul]
                      _ = (b*c)*c⁻¹ := by
                        have had_eq : a*d - 1 = b*c := by
                          calc
                            a*d - 1 = (a*d - b*c) + b*c - 1 := by ring
                            _ = 1 + b*c - 1 := by rw [had]
                            _ = b*c := by ring
                        rw [had_eq]
                      _ = b*(c*c⁻¹) := by simp [mul_assoc]
                      _ = b*1 := by rw [mul_inv_cancel₀ hc0]
                      _ = b := by simp
                  · -- (1,0): c = c
                    rfl
                  · -- (1,1): c*d*c⁻¹ = d
                    calc
                      c*d*c⁻¹ = d*c*c⁻¹ := by rw [mul_comm c d]
                      _ = d*(c*c⁻¹) := by simp [mul_assoc]
                      _ = d*1 := by rw [mul_inv_cancel₀ hc0]
                      _ = d := by simp
              ).symm
            _ = !![1, (x.val : ZMod p); 0, 1] * !![c⁻¹, 0; 0, c] *
                !![0, -1; 1, 0] * !![1, (y.val : ZMod p); 0, 1] := by
              simp [hx_def, hy_def, h_val_cast]
            _ = ((generatorR p) ^ (x.val : ℕ)).val * D.val * (generatorS p).val *
                ((generatorR p) ^ (y.val : ℕ)).val := by
              rw [hRpow_val (x.val), hRpow_val (y.val)]
              simp [D, generatorS]
            _ = ((generatorR p) ^ (x.val : ℕ) * D * (generatorS p) * (generatorR p) ^ (y.val : ℕ)).val := by
              simp [coe_mul]
        rw [hA_expr]
        repeat' apply Subgroup.mul_mem
        · exact hRpow (x.val)
        · have hD_mem : D ∈ H := by
            have h_diag' := h_diag c⁻¹ hc_inv
            have h_eq : D = (⟨!![c⁻¹, 0; 0, (c⁻¹)⁻¹], by
              calc
                det !![c⁻¹, 0; 0, (c⁻¹)⁻¹] = c⁻¹ * (c⁻¹)⁻¹ - 0 * 0 := by
                  rw [det_fin_two_of]
                _ = c⁻¹ * c := by simp [inv_inv]
                _ = 1 := h_c_inv_mul
              ⟩ : SL2Fp p) := by
              apply Subtype.ext
              simp [D, inv_inv]
            rw [h_eq]
            exact h_diag'
          exact hD_mem
        · exact hS
        · exact hRpow (y.val)
  have h_all_reachable : ∀ g : SL2Fp p, (cayleyGraph p).Reachable (1 : SL2Fp p) g := by
    intro g
    have hg_top : g ∈ (⊤ : Subgroup (SL2Fp p)) := Subgroup.mem_top g
    have hg_mem : g ∈ reachableFromOneSubgroup p :=
      h_subgroup (by rw [h_full]; exact hg_top)
    exact hg_mem
  -- By vertex-transitivity and symmetry of Reachable, any two vertices connect via 1.
  refine ⟨fun u v => ?_⟩
  have h1v : (cayleyGraph p).Reachable (1 : SL2Fp p) v := h_all_reachable v
  have hu1 : (cayleyGraph p).Reachable u (1 : SL2Fp p) :=
    (h_all_reachable u).symm
  exact hu1.trans h1v

end SL2FpProperties

end Riemann
