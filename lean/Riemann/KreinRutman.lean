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
proves a batch of genuine infrastructure over the real field (the spectral
value lemma `|μ| = ρ(T)`, the Fredholm alternative over ℝ, the positivity
transfer `T |f| ≥ ρ |f|`), and then proves both forms of the Krein–Rutman
theorem *modulo a single documented analytic admission* —
`kreinRutman_core`, the classical existence of a positive spectral-radius
eigenvector.  That existence statement is the true frontier; see its
docstring for the counterexample that rules out the sharper "collapse"
version, and for the three routes that would close it.

The weak theorem (`kreinRutman`) is exactly `kreinRutman_core`.  The strong
theorem (`kreinRutman_strong`, geometric simplicity) is *fully proved* from
`kreinRutman` plus strong positivity: strong positivity forces every positive
spectral-radius eigenvector to be strictly positive, and the extreme-value
theorem on the compact space `X` yields the uniqueness up to a positive
scalar (the ratio `g / f₀` attains its minimum).
-/

import Mathlib.Analysis.Normed.Operator.Compact.Basic
import Mathlib.Analysis.Normed.Operator.Compact.FredholmAlternative
import Mathlib.LinearAlgebra.Eigenspace.Basic
import Mathlib.Topology.ContinuousMap.Compact
import Mathlib.Topology.ContinuousMap.Ordered
import Mathlib.Topology.CompactOpen
import Mathlib.Analysis.Normed.Algebra.Spectrum
import Mathlib.Topology.Order.Compact

open scoped ContinuousMap ENNReal NNReal
open Set

namespace Riemann

noncomputable section

set_option maxHeartbeats 5000000

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

/-! ## The spectral-value lemma over ℝ -/

/-- A positive spectral radius makes the (real) spectrum nonempty: the
supremum in the definition `spectralRadius ℝ T = ⨆ k ∈ σ(T), ‖k‖₊` cannot be
positive over the empty set. -/
theorem spectrum_nonempty_of_pos_spectralRadius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hρ : 0 < spectralRadius ℝ T) : (spectrum ℝ T).Nonempty := by
  by_contra h
  have hset : spectrum ℝ T = ∅ := Set.not_nonempty_iff_eq_empty.mp h
  have : spectralRadius ℝ T = 0 := by simp [spectralRadius, hset]
  exact (ne_of_gt hρ) this

/-- Some element `μ = ±ρ(T)` of the real spectrum attains the spectral radius:
`μ ∈ σ(T)`, `μ ≠ 0`, and `|μ| = (spectralRadius ℝ T).toReal`. -/
theorem mem_spectrum_abs_eq_spectralRadius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hρ : 0 < spectralRadius ℝ T) :
    ∃ μ : ℝ, μ ∈ spectrum ℝ T ∧ μ ≠ 0 ∧ |μ| = (spectralRadius ℝ T).toReal := by
  have hσ : (spectrum ℝ T).Nonempty := spectrum_nonempty_of_pos_spectralRadius hρ
  obtain ⟨μ, hμσ, hμρ⟩ :=
    spectrum.exists_nnnorm_eq_spectralRadius_of_nonempty (𝕜 := ℝ) (a := T) hσ
  have hμ0 : μ ≠ 0 := by
    intro hz
    have hzabs : (‖μ‖₊ : ℝ≥0∞) = 0 := by simp [hz]
    rw [hzabs] at hμρ
    exact (ne_of_gt hρ) hμρ.symm
  refine ⟨μ, hμσ, hμ0, ?_⟩
  -- `(spectralRadius ℝ T).toReal` equals `‖μ‖₊ = |μ|`
  have hρreal : |μ| = (spectralRadius ℝ T).toReal := by
    rw [← hμρ]
    rw [ENNReal.coe_toReal]
    symm
    exact Real.norm_eq_abs μ
  exact hρreal

/-- **Fredholm alternative over ℝ**: for a compact `T`, every nonzero element
of the real spectrum is a genuine eigenvalue. -/
theorem hasEigenvalue_of_mem_spectrum_ne_zero {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTcomp : IsCompactOperator T) {μ : ℝ} (hμ0 : μ ≠ 0) (hμσ : μ ∈ spectrum ℝ T) :
    Module.End.HasEigenvalue (T : Module.End ℝ (C(X, ℝ))) μ :=
  (IsCompactOperator.hasEigenvalue_iff_mem_spectrum hTcomp hμ0).2 hμσ

/-- The pointwise modulus of a real-valued continuous function is nonnegative
and vanishes nowhere if the function is nonzero. -/
theorem absCm_pos {f : C(X, ℝ)} (hf : f ≠ 0) : |f| ∈ positiveCone ∧ |f| ≠ 0 := by
  constructor
  · rw [mem_positiveCone]
    intro x
    exact abs_nonneg (f x)
  · intro hg
    apply hf
    ext x
    have hgx : (|f|) x = 0 := DFunLike.congr_fun hg x
    exact abs_eq_zero.mp hgx

/-- **Positivity transfer**: for a positive operator with eigenvector `f` at
eigenvalue `μ`, the modulus `|f|` satisfies the pointwise domination
`|μ| · |f| ≤ T |f|`.  This is the standard inequality
`|T f| ≤ T |f|` for positive operators on a lattice. -/
theorem positive_abs_ge {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {f : C(X, ℝ)} {μ : ℝ} (hfT : T f = μ • f) (x : X) :
    |μ| * |f x| ≤ (T |f|) x := by
  -- |f| ≥ f and |f| ≥ -f pointwise, so positivity gives T|f| ≥ ±T f.
  have h1 : 0 ≤ (T |f|) x - (T f) x := by
    have hm : |f| - f ∈ positiveCone := by
      rw [mem_positiveCone]
      intro y
      apply sub_nonneg.mpr
      exact le_abs_self (f y)
    have hmT : 0 ≤ T (|f| - f) x := hT.apply_nonneg hm x
    rwa [map_sub] at hmT
  have h2 : 0 ≤ (T |f|) x + (T f) x := by
    have hm : |f| + f ∈ positiveCone := by
      rw [mem_positiveCone]
      intro y
      have hle : -(f y) ≤ |f y| := by
        simpa [abs_neg] using le_abs_self (-(f y))
      change 0 ≤ |f y| + f y
      rw [← sub_neg_eq_add]
      exact sub_nonneg.mpr hle
    have hmT : 0 ≤ T (|f| + f) x := hT.apply_nonneg hm x
    rwa [map_add] at hmT
  have habs : |(T f) x| ≤ (T |f|) x := by
    apply abs_le.mpr
    constructor
    · linarith
    · linarith
  -- |μ| · |f x| = |(T f) x|, since T f = μ • f pointwise
  have happ : (T f) x = μ * f x := by
    rw [hfT]
    rfl
  have hμf : |μ * f x| = |(T f) x| := by rw [happ]
  calc
    |μ| * |f x| = |μ * f x| := (abs_mul μ (f x)).symm
    _ = |(T f) x| := hμf
    _ ≤ (T |f|) x := habs

/-! ## The Krein–Rutman core (the true, single documented frontier) -/

/-- **Krein–Rutman core (admitted — the single documented frontier)**:

> A compact, positive operator `T` on `C(X, ℝ)` with positive spectral radius
> has a nonzero positive eigenfunction at the spectral radius:
> `∃ f ∈ positiveCone, f ≠ 0, T f = ρ(T) • f`.

This existence statement *is* the classical Krein–Rutman theorem and the
honest frontier of this file.  Nothing weaker is enough, and nothing
stronger is true in general.  In particular, earlier drafts admitted the
sharper **collapse lemma**

  `ρ(T) • f ≤ T f  on the cone  ⟹  T f = ρ(T) • f`

which is **FALSE as stated**.  Counterexample inside `C(X, ℝ)`: take `X` a
two-point space, so `C(X, ℝ) ≅ ℝ²`, and `T` the matrix `[[2, 1], [0, 2]]`
(positive, finite-rank hence compact, `ρ(T) = 2 > 0`).  For `f = (0, 1)`
(nonzero, in the cone) we have `T f = (1, 2) ≥ 2 • (0, 1) = ρ(T) • f`
strictly, yet `T f ≠ ρ(T) • f`.  So strict domination cannot be ruled out
from positivity and compactness alone — which is exactly why the strong
positivity hypothesis in `kreinRutman_strong` is load-bearing (there the
collapse is *proved*, not admitted).

Three routes would close `kreinRutman_core`; all are currently blocked in
mathlib over the real field:

1. *Gelfand's formula over ℝ*: show `lim ‖Tⁿ‖^(1/n) = ρ(T)` (the limit
   formula `spectrum.pow_nnnorm_pow_one_div_tendsto_nhds_spectralRadius`
   exists only over `ℂ`), then normalize `Tⁿ e` along a cone vector and
   extract a positive cluster-point eigenvector from compactness of `T`.
2. *Resolvent (Neumann) positivity at the radius*: for `λ > ρ(T)` represent
   `(λ − T)⁻¹ = Σₙ Tⁿ / λⁿ⁺¹` (needs the convergence-radius argument at the
   spectral radius, not just at `‖T‖`), get the resolvent positive, then run
   the classical two-sided domination argument.
3. *Complexification*: extend `T` to `C(X, ℂ) →L[ℂ] C(X, ℂ)`, transfer the
   spectral radius, and descend the resulting eigenvector; needs the
   spectral-radius/spectrum identity between a real operator and its
   complexification, which mathlib has not yet assembled.

Until then: `kreinRutman` below is exactly `kreinRutman_core` (one
admission), and `kreinRutman_strong` is proved from `kreinRutman` plus the
strong-positivity machinery with *no further admissions*. -/
theorem kreinRutman_core {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f := by
  sorry

/-! ## Krein–Rutman: the main theorems -/

/-- **Krein–Rutman theorem**, eigenvalue form.

A compact, positive operator `T` on `C(X, ℝ)` (for a compact Hausdorff `X`)
with positive spectral radius has the spectral radius as a positive
eigenvalue: there is a nonzero `f` with `0 ≤ f x` for all `x` and
`T f = (spectralRadius T).toReal • f`.

This is exactly `kreinRutman_core` — the single documented admission above;
the scaffold already proved in this file (real spectral value `|μ| = ρ(T)`
via the Fredholm alternative, the positivity transfer `T |f| ≥ ρ(T) |f|`)
lies on the direct road to closing that admission and is retained as
infrastructure for the next step. -/
theorem kreinRutman {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f :=
  kreinRutman_core hTpos hTcomp hρ

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
  let ρr : ℝ := (spectralRadius ℝ T).toReal
  -- the weak form provides the starting eigenfunction f₀
  obtain ⟨f₀, hf₀cone, hf₀ne, hf₀⟩ := kreinRutman hTpos hTcomp hρ
  have hρr : 0 < ρr := by simpa [ρr] using spectralRadius_toReal_pos hρ
  -- strong positivity makes f₀ strictly positive pointwise
  have hf₀pos : ∀ x : X, 0 < f₀ x := by
    intro x
    have hpos : 0 < (T f₀) x := hTstr f₀ hf₀cone hf₀ne x
    rw [hf₀] at hpos
    exact pos_of_mul_pos_right (by simpa [ρr, smul_eq_mul] using hpos) (le_of_lt hρr)
  refine ⟨f₀, hf₀cone, hf₀ne, hf₀, ?_⟩
  intro g hgcone hgne hgEq
  -- g is also strictly positive pointwise
  have hgpos : ∀ x : X, 0 < g x := by
    intro x
    have hpos : 0 < (T g) x := hTstr g hgcone hgne x
    rw [hgEq] at hpos
    exact pos_of_mul_pos_right (by simpa [ρr, smul_eq_mul] using hpos) (le_of_lt hρr)
  -- the ratio g / f₀ is well-defined and attains its minimum at some x₀
  have hcont : Continuous (fun x : X => g x / f₀ x) := by
    exact Continuous.div (ContinuousMap.continuous g) (ContinuousMap.continuous f₀)
      (fun x => ne_of_gt (hf₀pos x))
  have hne_univ : (Set.univ : Set X).Nonempty := ⟨Classical.choice ‹Nonempty X›, trivial⟩
  obtain ⟨x₀, _, hm⟩ :=
    (isCompact_univ.exists_isMinOn (s := Set.univ) hne_univ hcont.continuousOn)
  have hc_le : ∀ x : X, g x₀ / f₀ x₀ ≤ g x / f₀ x := by
    intro x
    exact (Filter.eventually_principal.mp hm) x (by trivial)
  let c : ℝ := g x₀ / f₀ x₀
  -- h := g - c • f₀ is in the cone and vanishes at x₀
  have hc_mul : ∀ x : X, c * f₀ x ≤ g x := by
    intro x
    have hmul := mul_le_mul_of_nonneg_right (hc_le x) (le_of_lt (hf₀pos x))
    have hsim : (g x / f₀ x) * f₀ x = g x := div_mul_cancel₀ (g x) (ne_of_gt (hf₀pos x))
    simpa [hsim] using hmul
  have hcon : g - c • f₀ ∈ positiveCone := by
    rw [mem_positiveCone]
    intro x
    simpa [smul_eq_mul] using sub_nonneg.mpr (hc_mul x)
  have hx0 : (g - c • f₀) x₀ = 0 := by
    change g x₀ - c * f₀ x₀ = 0
    rw [show c = g x₀ / f₀ x₀ by rfl]
    rw [div_mul_cancel₀ (g x₀) (ne_of_gt (hf₀pos x₀))]
    rw [sub_self]
  -- h is an eigenvector at ρ(T)
  have hTh : T (g - c • f₀) = ρr • (g - c • f₀) := by
    have h1 : T (g - c • f₀) = T g - c • T f₀ := by simp [map_sub, map_smul]
    have h2 : T g - c • T f₀ = ρr • g - c • (ρr • f₀) := by
      rw [hgEq, hf₀]
    have h3 : ρr • g - c • (ρr • f₀) = ρr • (g - c • f₀) := by
      ext x
      simp only [smul_sub, sub_smul, smul_smul, smul_eq_mul, mul_assoc, mul_comm, mul_left_comm]
    exact h1.trans (h2.trans h3)
  -- if h were nonzero, strong positivity forces T h > 0, contradicting T h = 0 at x₀
  have hcoef : g - c • f₀ = 0 := by
    by_contra hne
    have hpos : 0 < (T (g - c • f₀)) x₀ :=
      hTstr (g - c • f₀) hcon hne x₀
    have hzero : (T (g - c • f₀)) x₀ = 0 := by
      rw [hTh]
      change ρr * (g - c • f₀) x₀ = 0
      rw [hx0]
      simp
    linarith
  -- so g = c • f₀
  have hg_eq : g = c • f₀ := by
    ext x
    have hz : g x - c * f₀ x = 0 := by
      simpa [smul_eq_mul] using DFunLike.congr_fun hcoef x
    simpa [smul_eq_mul] using sub_eq_zero.mp hz
  exact ⟨c, div_pos (hgpos x₀) (hf₀pos x₀), hg_eq⟩

end

end Riemann
