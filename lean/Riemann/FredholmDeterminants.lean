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

NOTE: Mathlib has no trace-class / Fredholm determinant theory yet (verified by
grep — only finite-dimensional `singularValues` for `LinearMap.normDet`). This
file is the blueprint for Mathlib PRs #3/#4 in MATHLIB_FORK_PLAN.md.
-/

import Mathlib.Analysis.Normed.Operator.Basic
import Mathlib.Analysis.Normed.Operator.Compact.Basic
import Mathlib.Analysis.Normed.Algebra.Spectrum

/-!
# Fredholm Determinants

For a trace-class operator T on a Hilbert space, the Fredholm determinant is
  det(1 + T) = ∏_n (1 + λ_n) = Σ_k tr(∧^k T) / k!,

where λ_n are the eigenvalues of T counted with multiplicity.

## Main Definitions

- `singularValue`: the n-th singular value of a compact operator (Fleet: Mayer)
- `IsTraceClass`: summable singular values
- `traceClassTrace`: the operator trace (Fleet: Mayer)
- `fredholmDet`: the Fredholm determinant (Fleet: Mayer)

## Main Theorems (all Fleet: Mayer)

- `fredholmDet_zero`: det(1) = 1
- `fredholmDet_product`: multiplicativity
- `fredholmDet_ne_zero_iff`: det(1 − T) ≠ 0 ↔ 1 ∉ spectrum T
- `spectralRadius_lt_one_iff_fredholmDet_ne_zero`
-/

namespace Riemann.Fredholm

open scoped BigOperators

variable {E : Type*} [NormedAddCommGroup E] [NormedSpace ℂ E]

/-- The n-th singular value of a compact operator (Fleet: Mayer).

(ponytail: sorry-valued placeholder; real def needs Hilbert-space structure
`√‖T†T e_n‖` over eigenvalues of the positive operator T†T, plus the
Hilbert-Schmidt API. Upgrade path: Mathlib PR #3.) -/
noncomputable def singularValue {E : Type*} [NormedAddCommGroup E]
    [NormedSpace ℂ E] (T : E →L[ℂ] E) (_n : ℕ) : ℝ :=
  sorry -- Fleet Mayer: eigenvalues of (T†T)^{1/2} in decreasing order

/-- A compact operator is **trace-class** if its singular values are summable. -/
class IsTraceClass {E : Type*} [NormedAddCommGroup E] [NormedSpace ℂ E]
    (T : E →L[ℂ] E) : Prop where
  compact : IsCompactOperator T
  summableSingularValues : Summable (fun n => singularValue T n)

/-- Fredholm determinant closure: trace-class operators form a vector space
(Fleet: Mayer; Mathlib PR #3 material). -/
instance instNegIsTraceClass {T : E →L[ℂ] E} [hT : IsTraceClass T] : IsTraceClass (-T) where
  compact := IsCompactOperator.neg hT.compact
  summableSingularValues := by
    sorry -- Fleet Mayer: s_n(−T) = s_n(T)

instance instAddIsTraceClass {T₁ T₂ : E →L[ℂ] E} [h₁ : IsTraceClass T₁] [h₂ : IsTraceClass T₂] :
    IsTraceClass (T₁ + T₂) where
  compact := IsCompactOperator.add h₁.compact h₂.compact
  summableSingularValues := by
    sorry -- Fleet Mayer: s_n(T₁+T₂) ≤ s_n(T₁) + s_n(T₂)

/-- The trace of a trace-class operator: tr(T) = Σ ⟨e_n, T e_n⟩
for any orthonormal basis (Fleet: Mayer). -/
noncomputable def traceClassTrace {E : Type*} [NormedAddCommGroup E]
    [NormedSpace ℂ E] (T : E →L[ℂ] E) [IsTraceClass T] : ℂ :=
  sorry -- Fleet Mayer: basis-independent sum over an ONB

/-- The **Fredholm determinant** of a trace-class operator:
det(1 + T) = Σ_{k≥0} tr(∧^k T) / k! (Fleet: Mayer). -/
noncomputable def fredholmDet {E : Type*} [NormedAddCommGroup E]
    [NormedSpace ℂ E] (T : E →L[ℂ] E) [IsTraceClass T] : ℂ :=
  sorry -- Fleet Mayer: exterior-power trace expansion

section BasicProperties

variable {E : Type*} [NormedAddCommGroup E] [NormedSpace ℂ E]

instance : IsTraceClass (0 : E →L[ℂ] E) where
  compact := by
    sorry -- Fleet Mayer: 0 is trivially compact
  summableSingularValues := by
    sorry -- Fleet Mayer: all singular values vanish

/-- Trace-class closure under multiplication with a trace-class factor (Fleet: Mayer). -/
instance instMulIsTraceClass {T₁ T₂ : E →L[ℂ] E} [h₁ : IsTraceClass T₁] [h₂ : IsTraceClass T₂] :
    IsTraceClass (T₁ * T₂) where
  compact := IsCompactOperator.clm_comp h₂.compact T₁
  summableSingularValues := by
    sorry -- Fleet Mayer: s_n(T₁T₂) ≤ ‖T₂‖ s_n(T₁)

/-- det(1) = 1, i.e. the Fredholm determinant of the zero operator (Fleet: Mayer). -/
theorem fredholmDet_zero : fredholmDet (0 : E →L[ℂ] E) = 1 := by
  sorry -- Fleet Mayer: exterior powers of 0 vanish from k ≥ 1

/-- Multiplicativity: det(1+T₁)·det(1+T₂) = det(1+T₁+T₂+T₁T₂) (Fleet: Mayer). -/
theorem fredholmDet_product {T₁ T₂ : E →L[ℂ] E}
    [IsTraceClass T₁] [IsTraceClass T₂] [IsTraceClass (T₁ * T₂)] :
    fredholmDet T₁ * fredholmDet T₂ =
    fredholmDet (T₁ + T₂ + T₁ * T₂) := by
  sorry -- Fleet Mayer: standard composition identity

/-- det(1 + T) ≠ 0 ↔ −1 is not an eigenvalue of T (Fleet: Mayer). -/
theorem fredholmDet_ne_zero_iff {T : E →L[ℂ] E} [IsTraceClass T] :
    fredholmDet T ≠ 0 ↔ ∀ v : E, T v = -v → v = 0 := by
  sorry -- Fleet Mayer: determinant vanishes iff −1 is an eigenvalue

/-- For a trace-class operator T: ρ(T) < 1 ↔ det(1 + T) ≠ 0 (Fleet: Mayer). -/
theorem spectralRadius_lt_one_iff_fredholmDet_ne_zero {T : E →L[ℂ] E}
    [IsTraceClass T] :
    ENNReal.toReal (spectralRadius ℂ T) < 1 ↔ fredholmDet T ≠ 0 := by
  sorry -- Fleet Mayer: spectrum of trace-class operator is the eigenvalue multiset

end BasicProperties

end Riemann.Fredholm
