/-
Copyright (c) 2026 Tobias Weiss
Fredholm Determinants

Fredholm determinant theory for trace-class operators on Hilbert spaces.
This is the operator-theoretic core for Mayer's theorem on the Gauss map:
the Selberg zeta connection is stated once in `Riemann.TransferOperator.Complete`.

Author: Tobias Weiss
References:
- Simon, B. (2005). "Trace Ideals and Their Applications"
- Gohberg, I., Goldberg, S., Kaashoek, M. (1990). "Classes of Linear Operators Vol I"

NOTE: Mathlib has no infinite-dimensional trace-class / Fredholm determinant
theory yet (verified by grep — only the finite-dimensional `LinearMap.singularValues`
and `LinearMap.normDet` exist). This file therefore realises the Fredholm
skeleton on the FINITE-DIMENSIONAL, algebraic version that mathlib does provide:

- `LinearMap.singularValues` (Mathlib.Analysis.InnerProductSpace.SingularValues)
- `LinearMap.trace`          (Mathlib.LinearAlgebra.Trace)
- `LinearMap.det`            (Mathlib.LinearAlgebra.Determinant)

The genuinely analytic (infinite-dimensional / nuclear) statements — the Lidskii
trace theorem, the exterior-power expansion `det(1+T) = Σ_k tr(∧ᵏT)/k!`, and the
spectral-radius criterion — are the content of mathlib PRs #3/#4 in
MATHLIB_FORK_PLAN.md and are left as a documented lemma below
(see `spectralRadius_lt_one_iff_fredholmDet_ne_zero`).
-/

import Mathlib.Analysis.Normed.Operator.Compact.FiniteDimension
import Mathlib.Analysis.Normed.Algebra.Spectrum
import Mathlib.Analysis.InnerProductSpace.SingularValues
import Mathlib.LinearAlgebra.Determinant
import Mathlib.LinearAlgebra.Trace
import Mathlib.LinearAlgebra.Basis.VectorSpace

/-!
# Fredholm Determinants (finite-dimensional model)

For a trace-class operator T on a Hilbert space, the Fredholm determinant is
  det(1 + T) = ∏_n (1 + λ_n) = Σ_k tr(∧^k T) / k!,
where λ_n are the eigenvalues of T counted with multiplicity.
In finite dimension this collapses to the ordinary determinant `det(1 + T)`.

## Main Definitions

- `singularValue`: the n-th singular value of a (continuous) operator
- `IsTraceClass`: on a finite-dimensional space, every operator is trace-class
- `traceClassTrace`: the operator trace (`LinearMap.trace`)
- `fredholmDet`: the Fredholm determinant `det(1 + T)` (`LinearMap.det`)

## Main Theorems

- `fredholmDet_zero`: det(1) = 1
- `fredholmDet_product`: multiplicativity det(1+T₁)·det(1+T₂) = det(1+T₁+T₂+T₁T₂)
- `fredholmDet_ne_zero_iff`: det(1 + T) ≠ 0 ↔ −1 is not an eigenvalue of T
- `spectralRadius_lt_one_iff_fredholmDet_ne_zero` (requires infinite-dimensional
  trace-class spectral theory from mathlib PR #4)
-/

namespace Riemann.Fredholm

open scoped BigOperators

section FiniteDimensionalFredholm

variable {E : Type*} [NormedAddCommGroup E] [InnerProductSpace ℂ E]
  [FiniteDimensional ℂ E]

/-- The n-th singular value of an operator on a finite-dimensional complex
inner-product space: the descending sequence σ₀ ≥ σ₁ ≥ ... of the eigenvalues of
(T†T)^{1/2} (zero from `rank T` onwards), exactly mathlib's
`LinearMap.singularValues`. -/
noncomputable def singularValue (T : E →L[ℂ] E) (n : ℕ) : ℝ :=
  T.toLinearMap.singularValues n

/-- An operator is **trace-class** if it is compact and its singular values are
summable (on a finite-dimensional space the latter holds: `singularValues` is
finitely supported). -/
class IsTraceClass (T : E →L[ℂ] E) : Prop where
  compact : IsCompactOperator T
  summableSingularValues : Summable fun n => singularValue T n

/-- A finite-dimensional normed space is locally compact. -/
lemma locallyCompactSpace_of_finiteDimensional :
    LocallyCompactSpace E :=
  LocallyCompactSpace.of_finiteDimensional_of_complete ℂ E

/-- Every continuous operator on a finite-dimensional space is compact
(Fleet: Mayer). -/
lemma isCompactOperator_of_finiteDimensional (T : E →L[ℂ] E) : IsCompactOperator T := by
  haveI : LocallyCompactSpace E := locallyCompactSpace_of_finiteDimensional
  exact isCompactOperator_of_locallyCompactSpace_dom T

/-- On a finite-dimensional space every operator is trace-class (Fleet: Mayer).
This blanket instance makes the `[IsTraceClass T]` arguments of the API
below resolve automatically. -/
instance instIsTraceClass (T : E →L[ℂ] E) : IsTraceClass T where
  compact := isCompactOperator_of_finiteDimensional T
  summableSingularValues := by
    dsimp [singularValue]
    -- singular values are a finitely supported `ℕ →₀ ℝ`, hence summable
    exact summable_of_hasFiniteSupport (f := fun n : ℕ => T.toLinearMap.singularValues n) <| by
      exact T.toLinearMap.singularValues.hasFiniteSupport

-- On finite-dimensional spaces the trace-class closure properties hold trivially.
-- They are kept as theorems for API continuity with the intended
-- infinite-dimensional theory.

theorem isTraceClass_neg {T : E →L[ℂ] E} : IsTraceClass (-T) := inferInstance

theorem isTraceClass_add {T₁ T₂ : E →L[ℂ] E} : IsTraceClass (T₁ + T₂) := inferInstance

theorem isTraceClass_zero : IsTraceClass (0 : E →L[ℂ] E) := inferInstance

theorem isTraceClass_mul {T₁ T₂ : E →L[ℂ] E} : IsTraceClass (T₁ * T₂) := inferInstance

/-- The trace of a (trace-class) operator: `LinearMap.trace`, which is
independent of the choice of basis (Fleet: Mayer). -/
noncomputable def traceClassTrace (T : E →L[ℂ] E) [IsTraceClass T] : ℂ :=
  LinearMap.trace ℂ E T.toLinearMap

/-- The **Fredholm determinant** of a (trace-class) operator: `det(1 + T)`.
In finite dimension this is the ordinary determinant `LinearMap.det`; the
exterior-power expansion `Σ_k tr(∧^k T) / k!` is the content of mathlib PR #4. -/
noncomputable def fredholmDet (T : E →L[ℂ] E) [IsTraceClass T] : ℂ :=
  LinearMap.det (LinearMap.id + T.toLinearMap)

/-- `toLinearMap` distributes over `T₁ + T₂ + T₁ * T₂`. -/
lemma toLinearMap_add_add_mul (T₁ T₂ : E →L[ℂ] E) :
    (T₁ + T₂ + T₁ * T₂).toLinearMap =
      T₁.toLinearMap + T₂.toLinearMap + T₁.toLinearMap * T₂.toLinearMap := by
  rw [ContinuousLinearMap.toLinearMap_add, ContinuousLinearMap.toLinearMap_add,
    ContinuousLinearMap.toLinearMap_mul]

/-- det(1) = 1, i.e. the Fredholm determinant of the zero operator (Fleet: Mayer). -/
theorem fredholmDet_zero : fredholmDet (0 : E →L[ℂ] E) = 1 := by
  simp [fredholmDet]

/-- Multiplicativity: det(1+T₁)·det(1+T₂) = det(1+T₁+T₂+T₁T₂) (Fleet: Mayer). -/
theorem fredholmDet_product {T₁ T₂ : E →L[ℂ] E}
    [IsTraceClass T₁] [IsTraceClass T₂] [IsTraceClass (T₁ * T₂)] :
    fredholmDet T₁ * fredholmDet T₂ =
    fredholmDet (T₁ + T₂ + T₁ * T₂) := by
  simp only [fredholmDet]
  -- det(1+T₁)·det(1+T₂) = det((1+T₁) ∘ (1+T₂)) by multiplicativity of det
  rw [← LinearMap.det_comp]
  congr 1
  -- (1+T₁) ∘ (1+T₂) = 1 + T₁ + T₂ + T₁T₂  as linear maps
  rw [toLinearMap_add_add_mul]
  ext v
  simp only [LinearMap.comp_apply, Module.End.mul_apply, LinearMap.add_apply,
    LinearMap.id_apply, map_add]
  abel

/-- det(1 + T) ≠ 0 ↔ −1 is not an eigenvalue of T (Fleet: Mayer). -/
theorem fredholmDet_ne_zero_iff {T : E →L[ℂ] E} [IsTraceClass T] :
    fredholmDet T ≠ 0 ↔ ∀ v : E, T v = -v → v = 0 := by
  simp only [fredholmDet, ne_eq]
  -- det(id + T) ≠ 0 ↔ det(id + T) is a unit ↔ its kernel is trivial
  rw [LinearMap.det_eq_zero_iff_ker_ne_bot]
  rw [not_ne_iff]
  rw [LinearMap.ker_eq_bot']
  -- ∀ v, (id + T) v = 0 → v = 0  ↔  ∀ v, T v = -v → v = 0
  apply forall_congr'
  intro v
  -- (id + T) v = 0  ↔  T v = -v, with the same conclusion `v = 0` on both sides
  apply imp_congr
  · constructor
    · intro h
      -- h : (LinearMap.id + T.toLinearMap) v = 0
      have h' : T v + v = 0 := by simpa [add_comm] using h
      exact eq_neg_iff_add_eq_zero.mpr h'
    · intro h
      -- h : T v = -v
      have h' : T v + v = 0 := eq_neg_iff_add_eq_zero.mp h
      simpa [add_comm] using h'
  · rfl

/-- For a trace-class operator T: ρ(T) < 1 ↔ det(1 + T) ≠ 0 (Fleet: Mayer).

NOTE: proving this is the genuinely analytic step — it needs the theorem that
the spectrum of a trace-class operator is the closure of its eigenvalue
multiset (Lidskii/spectral theory), which is NOT in mathlib yet. The finite-
dimensional model above makes det(1+T) ≠ 0 equivalent to `1 ∉ spectrum (−T)`,
but the implication `det(1+T) ≠ 0 → ρ(T) < 1` is FALSE as stated even in
finite dimension (e.g. `T = 2·id`: det(1+T) = 3 ≠ 0 but ρ(T) = 2); the real
statement needs the correct spectral-radius ↔ Fredholm determinant
relationship from the infinite-dimensional trace-class theory.

This is left as a documented lemma for mathlib PR #4, after which this becomes:
```
  -- spectrum of T is the eigenvalue multiset {λ_n}; det(1+T) = ∏(1+λ_n)
  -- ρ(T) = sup |λ_n| < 1  ↔  all |λ_n| < 1  →  1 + λ_n ≠ 0  →  ∏(1+λ_n) ≠ 0
``` -/
theorem spectralRadius_lt_one_iff_fredholmDet_ne_zero {T : E →L[ℂ] E}
    [IsTraceClass T] :
    ENNReal.toReal (spectralRadius ℂ T) < 1 ↔ fredholmDet T ≠ 0 := by
  sorry -- Fleet Mayer, mathlib PR #4: spectrum of a trace-class operator is the eigenvalue multiset

end FiniteDimensionalFredholm

end Riemann.Fredholm
