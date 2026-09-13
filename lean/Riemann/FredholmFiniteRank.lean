/-
Copyright (c) 2026 Tobias Weiss. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Tobias Weiss
-/

import Mathlib.LinearAlgebra.Determinant
import Mathlib.LinearAlgebra.Matrix.SchurComplement

/-!
# Finite-rank Fredholm determinant (seed of the infinite-dimension theory)

Infrastructure for the Fredholm determinant `det(1 - A)` on a finite-dimensional
module — the algebraic seed of the infinite-dimensional Fredholm determinant used
in the transfer-operator approach to ζ.

Main results:

* `Riemann.FredholmFiniteRank.det_one_sub_mul` — multiplicativity
  `det((1-f)(1-g)) = det(1-f) * det(1-g)`
* `Riemann.FredholmFiniteRank.det_one_sub_ne_zero_of_ker_eq_bot` —
  `(1-f)` injective → `det(1-f) ≠ 0` (over an integral domain)
* `Riemann.FredholmFiniteRank.det_one_sub_ne_zero_iff_bijective` —
  over a field: `det(1-f) ≠ 0 ↔ (1-f) bijective`
* `Riemann.FredholmFiniteRank.det_one_sub_smulRight` — the rank-one
  formula `det(1 - (x ↦ φ x • c)) = 1 - φ c`

Everything is elementary: multiplicativity is `LinearMap.det.map_mul`; the
vanishing criterion is mathlib's `LinearMap.det_eq_zero_iff_ker_ne_bot`; the
rank-one formula goes through the Weinstein–Aronszajn identity
(`Matrix.det_one_add_mul_comm`) and `LinearMap.det_toMatrix`.

Note: `det(1-f) ≠ 0 ↔ bijective` is a *field* statement — over a general
integral domain (e.g. `ℤ` with `f = 2•id`) injectivity does not imply
surjectivity, and we do not claim it.
-/

open LinearMap

namespace Riemann.FredholmFiniteRank

section Matrices
variable {R : Type*} [CommRing R]

/-- Rank-one matrix lemma via Weinstein–Aronszajn: `det(1 - col·row) = 1 - v ⬝ᵥ u`. -/
theorem det_one_sub_replicateCol_mul_replicateRow {m : Type*} [Fintype m] [DecidableEq m]
    {ι : Type*} [Unique ι] (u v : m → R) :
    Matrix.det (1 - Matrix.replicateCol ι u * Matrix.replicateRow ι v) = 1 - v ⬝ᵥ u := by
  have hkey : Matrix.replicateCol ι (-u) * Matrix.replicateRow ι v
      = -(Matrix.replicateCol ι u * Matrix.replicateRow ι v) := by
    ext i j
    simp [Matrix.mul_apply, Matrix.replicateCol_apply, Matrix.replicateRow_apply,
      Finset.sum_neg_distrib]
  rw [sub_eq_add_neg, ← hkey, Matrix.det_one_add_replicateCol_mul_replicateRow]
  simp [dotProduct]
  abel

end Matrices

section Endo
variable {R : Type*} [CommRing R] [IsDomain R]
variable {E : Type*} [AddCommGroup E] [Module R E] [Module.Free R E] [Module.Finite R E]

omit [IsDomain R] [Module.Free R E] [Module.Finite R E] in
/-- **RH-21 (1): multiplicativity.** `det((1-f)(1-g)) = det(1-f) · det(1-g)`. -/
theorem det_one_sub_mul (f g : E →ₗ[R] E) :
    LinearMap.det (((1 : E →ₗ[R] E) - f) * ((1 : E →ₗ[R] E) - g))
      = LinearMap.det ((1 : E →ₗ[R] E) - f) * LinearMap.det ((1 : E →ₗ[R] E) - g) :=
  LinearMap.det.map_mul _ _

/-- **RH-21 (4): eigenvalue criterion.** If `1` is not an eigenvalue of `f`
(`(1-f)` injective), then `det(1-f) ≠ 0`. -/
theorem det_one_sub_ne_zero_of_ker_eq_bot (f : E →ₗ[R] E)
    (h : ∀ x, ((1 : E →ₗ[R] E) - f) x = 0 → x = 0) :
    LinearMap.det ((1 : E →ₗ[R] E) - f) ≠ 0 := by
  intro h0
  rw [LinearMap.det_eq_zero_iff_ker_ne_bot] at h0
  exact h0 (LinearMap.ker_eq_bot'.mpr h)

omit [IsDomain R] [Module.Free R E] [Module.Finite R E] in
/-- **RH-21 (3): rank-one formula.** For the rank-one operator `x ↦ φ x • c`,
`det(1 - A) = 1 - φ c`. -/
theorem det_one_sub_smulRight {n : ℕ} (b : Module.Basis (Fin n) R E) (φ : E →ₗ[R] R) (c : E) :
    LinearMap.det ((1 : E →ₗ[R] E) - φ.smulRight c) = 1 - φ c := by
  have hM : LinearMap.toMatrix b b (φ.smulRight c)
      = Matrix.replicateCol Unit (fun i => b.repr c i) * Matrix.replicateRow Unit (fun j => φ (b j)) := by
    ext i j
    simp [LinearMap.toMatrix_apply, LinearMap.smulRight_apply,
      map_smul, Matrix.mul_apply, Matrix.replicateCol_apply, Matrix.replicateRow_apply,
      Finset.univ_unique, mul_comm]
  have hsub : LinearMap.toMatrix b b ((1 : E →ₗ[R] E) - φ.smulRight c)
      = 1 - Matrix.replicateCol Unit (fun i => b.repr c i) * Matrix.replicateRow Unit (fun j => φ (b j)) := by
    ext i j
    by_cases hji : j = i
    · subst hji
      simp [LinearMap.toMatrix_apply, LinearMap.smulRight_apply,
        map_smul, Matrix.mul_apply, Matrix.replicateCol_apply, Matrix.replicateRow_apply,
        Finset.univ_unique, Matrix.one_apply_eq, mul_comm]
    · have hij : i ≠ j := fun h => hji h.symm
      simp [LinearMap.toMatrix_apply, LinearMap.smulRight_apply,
        map_smul, Matrix.mul_apply, Matrix.replicateCol_apply, Matrix.replicateRow_apply,
        Finset.univ_unique, mul_comm,
        Matrix.one_apply_ne hij, Finsupp.single_eq_of_ne hij]
  have hc : φ c = ∑ j, φ (b j) * b.repr c j := by
    have hsum := Module.Basis.sum_repr b c
    calc φ c = φ (∑ i, (b.repr c i) • b i) := by congr 1; rw [hsum]
      _ = ∑ i, φ ((b.repr c i) • b i) := map_sum φ _ _
      _ = ∑ i, (b.repr c i) • φ (b i) := by simp [map_smul]
      _ = ∑ j, φ (b j) * b.repr c j := by
          simp [smul_eq_mul, mul_comm]
  rw [← LinearMap.det_toMatrix b, hsub,
    det_one_sub_replicateCol_mul_replicateRow (m := Fin n) (ι := Unit)]
  simp only [dotProduct]
  rw [hc]

end Endo

section Field
variable {K : Type*} [Field K]
variable {V : Type*} [AddCommGroup V] [Module K V] [FiniteDimensional K V]

/-- **RH-21 (2): bijectivity criterion (over a field).**
`det(1-f) ≠ 0 ↔ (1-f) bijective`. -/
theorem det_one_sub_ne_zero_iff_bijective (f : V →ₗ[K] V) :
    LinearMap.det ((1 : V →ₗ[K] V) - f) ≠ 0 ↔ Function.Bijective ⇑((1 : V →ₗ[K] V) - f) := by
  constructor
  · intro h
    have hker : LinearMap.ker ((1 : V →ₗ[K] V) - f) = ⊥ :=
      Classical.byContradiction fun hn => h (LinearMap.det_eq_zero_iff_ker_ne_bot.mpr hn)
    have hzero : ∀ x, ((1 : V →ₗ[K] V) - f) x = 0 → x = 0 :=
      LinearMap.ker_eq_bot'.mp hker
    have hinj : Function.Injective ⇑((1 : V →ₗ[K] V) - f) := fun x y hxy =>
      sub_eq_zero.mp (hzero (x - y) (by rw [map_sub, hxy, sub_self]))
    exact ⟨hinj, LinearMap.injective_iff_surjective.mp hinj⟩
  · intro h
    have hinj : Function.Injective ⇑((1 : V →ₗ[K] V) - f) := h.1
    by_contra h0
    rw [LinearMap.det_eq_zero_iff_ker_ne_bot] at h0
    exact h0 (LinearMap.ker_eq_bot'.mpr fun x hx =>
      hinj (by rw [hx, map_zero]))

end Field

end Riemann.FredholmFiniteRank
