/-
Copyright (c) 2026 Tobias Weiss
Krein–Rutman theorem for compact positive operators on C(X, ℝ)

The classical Krein–Rutman theorem: a compact, positive operator
`T : C(X, ℝ) →L[ℝ] C(X, ℝ)` on the space of continuous real-valued functions
over a compact Hausdorff space `X`, with positive spectral radius, has the
spectral radius as a *positive* eigenvalue:

  ∃ f ≠ 0, (∀ x, 0 ≤ f x) ∧ T f = spectralRadius T • f.

Reference: Krein, M. G.; Rutman, M. A. (1948), "Linear operators leaving
invariant a cone in a Banach space", Amer. Math. Soc. Transl. 26, 199–377.

This file develops the cone-theoretic scaffolding on `C(X, ℝ)` (positive
cone, positive operators, and their elementary order-theoretic properties),
states the two main theorems (the eigenvalue form and the strong form with
geometric simplicity of the leading eigenspace), and supplies the analytic
heart as two documented admissions (TBD items), to be filled once mathlib
provides a Schauder/compact-operator fixed-point argument over the reals
(Gelfand's spectral-radius formula currently exists only over `ℂ`).
-/

import Mathlib.Analysis.Normed.Operator.Compact.Basic
import Mathlib.Topology.ContinuousMap.Compact
import Mathlib.Topology.ContinuousMap.Ordered
import Mathlib.Topology.CompactOpen
import Mathlib.Analysis.Normed.Algebra.Spectrum

open scoped ContinuousMap
open Set

namespace Riemann

noncomputable section

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [Nonempty X]

/-! ## The positive cone in C(X, ℝ) -/

/-- The positive cone in `C(X, ℝ)`: the functions that are nonnegative
everywhere. -/
def positiveCone : Set C(X, ℝ) := { f | ∀ x : X, 0 ≤ f x }

/-- A continuous real-valued function belongs to the positive cone iff it is
pointwise nonnegative. -/
@[simp]
theorem mem_positiveCone {f : C(X, ℝ)} : f ∈ positiveCone ↔ ∀ x, 0 ≤ f x :=
  Iff.rfl

/-- The positive cone is nonempty (it contains zero). -/
theorem positiveCone_nonempty : positiveCone (X := X).Nonempty :=
  ⟨0, by simp⟩

/-- The positive cone contains a nonzero element (the constant function 1,
where `X` is nonempty). -/
theorem positiveCone_ne_zero : ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 := by
  refine ⟨1, by simp, ?_⟩
  intro hz
  have hx : (1 : ℝ) = 0 := DFunLike.congr_fun hz (Classical.choice ‹Nonempty X›)
  norm_num at hx

/-- The positive cone is convex. -/
theorem convex_positiveCone : Convex ℝ (positiveCone (X := X)) := by
  intro x hx y hy a b ha hb hab
  rw [mem_positiveCone]
  intro z
  have hx' : 0 ≤ x z := hx z
  have hy' : 0 ≤ y z := hy z
  simpa [smul_eq_mul] using add_nonneg (mul_nonneg ha hx') (mul_nonneg hb hy')

/-- The positive cone is a pointed cone: if both `f` and `-f` are nonnegative
then `f = 0`. -/
theorem positiveCone_eq_zero {f : C(X, ℝ)} (hf : f ∈ positiveCone)
    (hneg : -f ∈ positiveCone) : f = 0 := by
  ext x
  have hfx : 0 ≤ f x := hf x
  have hnegx : f x ≤ 0 := by simpa using (hneg x : 0 ≤ (-f) x)
  exact le_antisymm hnegx hfx

/-- The positive cone is closed in `C(X, ℝ)`. -/
theorem isClosed_positiveCone : IsClosed (positiveCone (X := X)) := by
  -- positiveCone = ⋂ x, { f | 0 ≤ f x }, an intersection of closed fibres of
  -- the continuous evaluation maps
  have hset : positiveCone = ⋂ x : X, { f : C(X, ℝ) | 0 ≤ f x } := by
    ext f
    simp
  rw [hset]
  exact isClosed_iInter fun x => by
    exact isClosed_le continuous_const (continuous_eval_const x)

/-! ## Positive operators -/

/-- A continuous linear operator `T` on `C(X, ℝ)` is *positive* if it maps the
positive cone into itself. -/
def IsPositive (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) : Prop :=
  MapsTo T positiveCone positiveCone

/-- A positive operator sends a pointwise nonnegative function to a pointwise
nonnegative function. -/
theorem IsPositive.apply_nonneg {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {f : C(X, ℝ)} (hf : f ∈ positiveCone) : ∀ x : X, 0 ≤ T f x := (hT hf)

/-- Positive operators are monotone for the pointwise order. -/
theorem IsPositive.monotone {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {f g : C(X, ℝ)} (hfg : f ≤ g) : T f ≤ T g := by
  rw [ContinuousMap.le_def]
  intro x
  rw [← sub_nonneg]
  have hsub : g - f ∈ positiveCone := by
    rw [mem_positiveCone]
    intro y
    exact sub_nonneg.mpr ((ContinuousMap.le_def.mp hfg) y)
  have hTsub : T (g - f) ∈ positiveCone := hT hsub
  have h0 : 0 ≤ T (g - f) x := hTsub x
  rwa [map_sub] at h0

/-- The identity operator is positive. -/
theorem isPositive_id : IsPositive (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) := by
  intro f hf
  simpa using hf

/-- A nonnegative scalar multiple of a positive operator is positive. -/
theorem IsPositive.smul {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {c : ℝ} (hc : 0 ≤ c)
    (hT : IsPositive T) : IsPositive (c • T) := by
  intro f hf x
  simpa using mul_nonneg hc (hT.apply_nonneg hf x)

/-- The sum of two positive operators is positive. -/
theorem IsPositive.add {S T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hS : IsPositive S)
    (hT : IsPositive T) : IsPositive (S + T) := by
  intro f hf x
  simpa using add_nonneg (hS.apply_nonneg hf x) (hT.apply_nonneg hf x)

/-- The composition of two positive operators is positive. -/
theorem IsPositive.mul {S T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hS : IsPositive S)
    (hT : IsPositive T) : IsPositive (S * T) := by
  intro f hf
  simpa using hS (hT hf)

/-- All powers of a positive operator are positive. -/
theorem IsPositive.pow {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    (n : ℕ) : IsPositive (T ^ n) := by
  induction n with
  | zero =>
    intro f hf
    simpa using hf
  | succ k ih =>
    rw [pow_succ]
    exact ih.mul hT

/-- Strong positivity: a positive operator that sends every *nonzero* vector of
the positive cone to a strictly positive function (pointwise). -/
def IsStronglyPositive (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) : Prop :=
  ∀ f : C(X, ℝ), f ∈ positiveCone → f ≠ 0 → ∀ x : X, 0 < T f x

/-- A strongly positive operator is positive. -/
theorem IsStronglyPositive.toIsPositive {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hT : IsStronglyPositive T) : IsPositive T := by
  intro f hf x
  by_cases hzero : f = 0
  · subst hzero
    simp
  · exact le_of_lt (hT f hf hzero x)

/-! ## Spectral radius on C(X, ℝ) -/

/-- The spectral radius of a bounded operator on `C(X, ℝ)` is a finite real
number as soon as it is positive (it is bounded above by the operator norm). -/
theorem spectralRadius_pos_ne_top {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hρ : 0 < spectralRadius ℝ T) : spectralRadius ℝ T ≠ ⊤ :=
  ne_top_of_le_ne_top ENNReal.coe_ne_top (spectrum.spectralRadius_le_nnnorm (𝕜 := ℝ) T)

/-- If `0 < spectralRadius T` then its real value `(spectralRadius T).toReal`
is positive. -/
theorem spectralRadius_toReal_pos {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hρ : 0 < spectralRadius ℝ T) : 0 < (spectralRadius ℝ T).toReal :=
  ENNReal.toReal_pos (ne_of_gt hρ) (spectralRadius_pos_ne_top hρ)

/-! ## Krein–Rutman: the main theorems -/

/-- **Krein–Rutman theorem**, eigenvalue form.

A compact, positive operator `T` on `C(X, ℝ)` (for a compact Hausdorff `X`)
with positive spectral radius has the spectral radius as a positive
eigenvalue: there is a nonzero `f` with `0 ≤ f x` for all `x` and
`T f = (spectralRadius T).toReal • f`.

Proof route (analytic core, deferred): the full argument requires Gelfand's
spectral-radius formula `ρ(T) = lim ‖Tⁿ‖^(1/n)` over the real field (mathlib
currently has it only for complex Banach algebras), plus a compactness
cluster-point argument on the normalized orbit `Tⁿ f₀ / ‖Tⁿ f₀‖` of a fixed
nonzero `f₀` in the cone: positivity keeps the orbit in the cone, compactness
of `T` keeps it relatively compact, and the (positive by positivity) ratios of
successive norms converge to `ρ(T)` by Gelfand's formula, so the cluster point
`f` satisfies `T f = ρ(T) f`. -/
theorem kreinRutman {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f := by
  sorry

/-- **Krein–Rutman theorem**, strong form (geometric simplicity of the
leading eigenvalue).

If, in addition, `T` is strongly positive (it maps every nonzero vector of the
positive cone to a strictly positive function), then the spectral-radius
eigenvector is unique up to a positive scalar: every nonzero positive
eigenvector at the spectral radius lies in the ray spanned by a single
(automatically strictly positive) eigenfunction. -/
theorem kreinRutman_strong {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hTstr : IsStronglyPositive T)
    (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f ∧
      (∀ g : C(X, ℝ), g ∈ positiveCone → g ≠ 0 →
        T g = (spectralRadius ℝ T).toReal • g → ∃ c : ℝ, 0 < c ∧ g = c • f) := by
  sorry

end

end Riemann
