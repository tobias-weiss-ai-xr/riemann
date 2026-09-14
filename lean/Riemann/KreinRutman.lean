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
import Mathlib.Analysis.SpecificLimits.Normed
import Mathlib.Analysis.Normed.Ring.Units
import Riemann.RealGelfand

open scoped ContinuousMap ENNReal NNReal Topology
open Filter
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

/-! ## Resolvent (Neumann series) and resolvent positivity -/

-- The operator ring `C(X, ℝ) →L[ℝ] C(X, ℝ)` is a normed ring with respect to
-- the operator norm.  mathlib ships the `NormedRing`/`NormedAddCommGroup`
-- instances for continuous-linear endomorphism spaces in an `@[expose]`
-- section that instance search does not pick up here, so we assemble them
-- (locally) from the always-available `SeminormedRing` / separation data.
local instance normedAddCommGroup_end :
    NormedAddCommGroup (C(X, ℝ) →L[ℝ] C(X, ℝ)) :=
  NormedAddCommGroup.ofSeparation (fun f => (ContinuousLinearMap.opNorm_zero_iff (f := f)).mp)

local instance normedRing_end : NormedRing (C(X, ℝ) →L[ℝ] C(X, ℝ)) :=
  { (inferInstance : SeminormedRing (C(X, ℝ) →L[ℝ] C(X, ℝ))) with
    toMetricSpace := (inferInstance : NormedAddCommGroup (C(X, ℝ) →L[ℝ] C(X, ℝ))).toMetricSpace }

/-- Point evaluation at `x : X` as a continuous linear functional on
`C(X, ℝ)`. -/
def resolvent_eval (x : X) : C(X, ℝ) →L[ℝ] ℝ :=
  { toFun := fun g => g x
    map_add' := by intro g h; rfl
    map_smul' := by intro c g; rfl
    cont := continuous_eval_const x }

/-- Scalar multiplication commutes with composition on the left:
`(a • A) * B = a • (A * B)`. -/
lemma resolvent_smul_mul_assoc (a : ℝ) (A B : C(X, ℝ) →L[ℝ] C(X, ℝ)) :
    (a • A) * B = a • (A * B) := by
  ext f x
  rfl

/-- Scalar multiplication commutes with composition on the right:
`A * (a • B) = a • (A * B)`. -/
lemma resolvent_mul_smul_assoc (a : ℝ) (A B : C(X, ℝ) →L[ℝ] C(X, ℝ)) :
    A * (a • B) = a • (A * B) := by
  ext f x
  change (A (a • (B f))) x = (a • (A (B f))) x
  rw [map_smul]

/-- Scalar powers in the operator ring: `(a • A)^n = a^n • A^n`. -/
lemma resolvent_smul_pow (a : ℝ) (A : C(X, ℝ) →L[ℝ] C(X, ℝ)) (n : ℕ) :
    (a • A) ^ n = a ^ n • A ^ n := by
  induction n with
  | zero => simp
  | succ k ih =>
    rw [pow_succ, ih, pow_succ]
    calc
      (a ^ k • A ^ k) * (a • A) = a ^ k • (A ^ k * (a • A)) :=
        resolvent_smul_mul_assoc (a ^ k) (A ^ k) (a • A)
      _ = a ^ k • (a • (A ^ k * A)) := by rw [resolvent_mul_smul_assoc]
      _ = (a ^ k * a) • (A ^ k * A) := by rw [smul_smul]
      _ = a ^ (k + 1) • A ^ (k + 1) := by
        rw [← pow_succ (a := a) (n := k)]
        rw [← pow_succ (a := A) (n := k)]

/-- `Ring.inverse` rescaling: for a nonzero scalar `a` and a unit `x`,
`Ring.inverse (a • x) = a⁻¹ • Ring.inverse x`. -/
lemma resolvent_inverse_smul (a : ℝ) (ha : a ≠ 0)
    (x : C(X, ℝ) →L[ℝ] C(X, ℝ)) (hx : IsUnit x) :
    Ring.inverse (a • x) = (a⁻¹ : ℝ) • Ring.inverse x := by
  let u : (C(X, ℝ) →L[ℝ] C(X, ℝ))ˣ :=
    ⟨a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)), (a⁻¹ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)),
      by
        calc
          (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) * ((a⁻¹ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)))
              = (a⁻¹ : ℝ) • ((a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) * (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) :=
                  by rw [resolvent_mul_smul_assoc]
          _ = (a⁻¹ : ℝ) • (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) := by rw [mul_one]
          _ = (a⁻¹ * a) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) := smul_smul _ _ _
          _ = (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) := by rw [inv_mul_cancel₀ ha, one_smul],
      by
        calc
          ((a⁻¹ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) * (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)))
              = (a⁻¹ : ℝ) • ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) * (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)))) :=
                  by rw [resolvent_smul_mul_assoc]
          _ = (a⁻¹ : ℝ) • (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) := by rw [one_mul]
          _ = (a⁻¹ * a) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) := smul_smul _ _ _
          _ = (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) := by rw [inv_mul_cancel₀ ha, one_smul]⟩
  have hu : IsUnit (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) := ⟨u, rfl⟩
  have hainv : Ring.inverse (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) =
      (a⁻¹ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) := by
    rw [Ring.inverse_unit (u := u)]
    rfl
  calc
    Ring.inverse (a • x) = Ring.inverse ((a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) * x) := by
      have hstep : a • x = (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) * x := by
        rw [resolvent_smul_mul_assoc a (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) x]
        rw [one_mul]
      rw [hstep]
    _ = Ring.inverse x * Ring.inverse (a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) := by
      exact Ring.inverse_mul (a := a • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))) (b := x) (Or.inl hu)
    _ = (a⁻¹ : ℝ) • Ring.inverse x := by
      rw [hainv]
      simpa [resolvent_mul_smul_assoc]

/-- The scaled operator `rT = a⁻¹ • T` has norm `< 1` whenever `‖T‖ < a` and
`0 < a`. -/
lemma resolvent_scaled_norm_lt_one {a : ℝ} (ha : 0 < a)
    (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) (hT : ‖T‖ < a) :
    ‖(a⁻¹ : ℝ) • T‖ < 1 := by
  have hle : ‖(a⁻¹ : ℝ) • T‖ ≤ ‖(a⁻¹ : ℝ)‖ * ‖T‖ :=
    ContinuousLinearMap.opNorm_smul_le (a⁻¹) T
  have hlt : ‖(a⁻¹ : ℝ)‖ * ‖T‖ < 1 := by
    rw [Real.norm_eq_abs, abs_inv, abs_of_pos ha]
    calc
      a⁻¹ * ‖T‖ < a⁻¹ * a := mul_lt_mul_of_pos_left hT (inv_pos.mpr ha)
      _ = 1 := by rw [inv_mul_cancel₀ (ne_of_gt ha)]
  exact lt_of_le_of_lt hle hlt

/-- The resolvent at `lam` rescales onto the resolvent at `1` for the scaled
operator `rT = lam⁻¹ • T`:
`Ring.inverse (lam • 1 - T) = lam⁻¹ • Ring.inverse (1 - rT)`. -/
lemma resolvent_scaling {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {lam : ℝ} (hlam : lam ≠ 0)
    (rT : C(X, ℝ) →L[ℝ] C(X, ℝ)) (hrT : rT = (lam⁻¹ : ℝ) • T)
    (hrT1 : ‖rT‖ < 1) :
    Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
      (lam⁻¹ : ℝ) • Ring.inverse (1 - rT) := by
  have huRT : IsUnit (1 - rT) := isUnit_one_sub_of_norm_lt_one hrT1
  have hM : lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T = lam • (1 - rT) := by
    have hsmul : lam • ((lam⁻¹ : ℝ) • T) = T := by
      rw [smul_smul]
      rw [mul_inv_cancel₀ hlam, one_smul]
    rw [← hsmul]
    rw [← smul_sub]
    rw [hrT]
  calc
    Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
        Ring.inverse (lam • (1 - rT)) := by rw [hM]
    _ = (lam⁻¹ : ℝ) • Ring.inverse (1 - rT) :=
      resolvent_inverse_smul lam hlam (1 - rT) huRT

/-- **Neumann (geometric) series identity for the resolvent**: whenever
`0 < lam` and `‖T‖ < lam`, the resolvent `(lam • 1 - T)⁻¹` (in `C(X, ℝ) →L[ℝ] C(X, ℝ)`
with `Ring.inverse`) equals the convergent geometric series
`Σₙ (lam⁻¹)ⁿ⁺¹ · Tⁿ`, i.e. `Tⁿ / lamⁿ⁺¹` in the scalar sense. -/
theorem resolvent_neumann_series {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {lam : ℝ}
    (hlam : 0 < lam) (hT : ‖T‖ < lam) :
    HasSum (fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n)
      (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  let rT : C(X, ℝ) →L[ℝ] C(X, ℝ) := (lam⁻¹ : ℝ) • T
  have hrT1 : ‖rT‖ < 1 := by
    simpa [rT] using resolvent_scaled_norm_lt_one hlam T hT
  have hgeom : HasSum (fun n : ℕ => rT ^ n) (Ring.inverse (1 - rT)) :=
    hasSum_geom_series_inverse rT hrT1
  have hsum : HasSum (fun n : ℕ => (lam⁻¹ : ℝ) • rT ^ n)
      ((lam⁻¹ : ℝ) • Ring.inverse (1 - rT)) :=
    HasSum.const_smul (lam⁻¹ : ℝ) hgeom
  -- the summands agree: (lam⁻¹)ⁿ⁺¹ • Tⁿ = (lam⁻¹) • rTⁿ
  have hflat : (fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n) =
      fun n : ℕ => (lam⁻¹ : ℝ) • rT ^ n := by
    funext n
    calc
      (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n = ((lam⁻¹ : ℝ) * (lam⁻¹ : ℝ) ^ n) • T ^ n := by
        rw [pow_succ']
      _ = (lam⁻¹ : ℝ) • ((lam⁻¹ : ℝ) ^ n • T ^ n) :=
        (smul_smul (lam⁻¹ : ℝ) ((lam⁻¹ : ℝ) ^ n) (T ^ n)).symm
      _ = (lam⁻¹ : ℝ) • (rT ^ n) := by rw [resolvent_smul_pow]
  have hsum' : HasSum (fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n)
      ((lam⁻¹ : ℝ) • Ring.inverse (1 - rT)) := by
    rw [hflat]
    exact hsum
  have hres : Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
      (lam⁻¹ : ℝ) • Ring.inverse (1 - rT) :=
    resolvent_scaling (ne_of_gt hlam) rT (by simp [rT]) hrT1
  simpa [hres] using hsum'

/-- **Resolvent positivity at the norm**: if `T` is a positive operator,
`0 < lam` and `‖T‖ < lam`, then the resolvent `Ring.inverse (lam • 1 - T)` is
well-defined (the Neumann series of `resolvent_neumann_series` converges) and
is itself a positive operator.  This is the positivity half of the
Krein–Rutman strategy: resolvents of positive operators at positive levels
outside the spectrum are positive. -/
theorem resolvent_positivity_at_norm {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) {lam : ℝ} (hlam : 0 < lam) (hT : ‖T‖ < lam) :
    IsPositive (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  let rT : C(X, ℝ) →L[ℝ] C(X, ℝ) := (lam⁻¹ : ℝ) • T
  have hrT1 : ‖rT‖ < 1 := by
    simpa [rT] using resolvent_scaled_norm_lt_one hlam T hT
  have hgeom : HasSum (fun n : ℕ => rT ^ n) (Ring.inverse (1 - rT)) :=
    hasSum_geom_series_inverse rT hrT1
  -- scaled powers are positive: rTⁿ = (lam⁻¹)ⁿ • Tⁿ with lam⁻¹ ≥ 0
  have hpos : ∀ n : ℕ, IsPositive (rT ^ n) := by
    intro n
    rw [resolvent_smul_pow]
    exact IsPositive.smul (pow_nonneg (inv_nonneg.mpr (le_of_lt hlam)) n) (hTpos.pow n)
  -- the (Neumann) infinite sum of positive operators is positive
  have hinvpos : IsPositive (Ring.inverse (1 - rT)) := by
    intro g hg
    rw [mem_positiveCone]
    intro x
    have htsum : Ring.inverse (1 - rT) = ∑' n : ℕ, rT ^ n := hgeom.tsum_eq.symm
    have hs : Summable (fun n : ℕ => rT ^ n) := hgeom.summable
    have hs_app : Summable (fun n : ℕ => (rT ^ n) g) := by
      let φ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
        ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
      simpa [φ] using (ContinuousLinearMap.summable φ hs)
    have happ : (Ring.inverse (1 - rT)) g = ∑' n : ℕ, (rT ^ n) g := by
      calc
        (Ring.inverse (1 - rT)) g = (∑' n : ℕ, rT ^ n) g := by rw [htsum]
        _ = ∑' n : ℕ, (rT ^ n) g := by
          let φ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
            ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
          have hmap := ContinuousLinearMap.map_tsum (φ := φ) hs
          simpa [φ] using hmap
    have hx : ((Ring.inverse (1 - rT)) g) x = ∑' n : ℕ, (((rT ^ n) g) x) := by
      calc
        ((Ring.inverse (1 - rT)) g) x = (∑' n : ℕ, (rT ^ n) g) x := by rw [happ]
        _ = ∑' n : ℕ, (((rT ^ n) g) x) := by
          have hmap := ContinuousLinearMap.map_tsum (φ := resolvent_eval x) hs_app
          simpa [resolvent_eval] using hmap
    have hterm : ∀ n : ℕ, 0 ≤ (((rT ^ n) g) x) := by
      intro n
      exact (IsPositive.apply_nonneg (hpos n) hg) x
    rw [hx]
    exact tsum_nonneg hterm
  -- rescale back by lam⁻¹ ≥ 0
  have hres : Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
      (lam⁻¹ : ℝ) • Ring.inverse (1 - rT) := by
    exact resolvent_scaling (ne_of_gt hlam) rT (by simp [rT]) hrT1
  rw [hres]
  exact IsPositive.smul (inv_nonneg.mpr (le_of_lt hlam)) hinvpos

/-! ## Resolvent at the spectral radius (beyond the operator norm)

The Neumann series and positivity results of `resolvent_neumann_series` and
`resolvent_positivity_at_norm` hold not just for `lam > ‖T‖` but for every
`lam` strictly above the spectral radius `(spectralRadius ℝ T).toReal`.  The
bounded-orbit estimate `eventually_pow_norm_le` below upgrades the operator-norm
hypothesis to the spectral-radius one; it is stated in hypothesis form because the
general-real Gelfand formula `lim ‖T^n‖^(1/n) = ρ(T)` is FALSE over `ℝ` (see
`Riemann.RealGelfand.counterexampleRotation`; it holds over `ℂ` via mathlib's own
Gelfand formula). -/

/-- **Bounded orbit estimate** (practical form of Gelfand's formula over `ℝ`):
assuming the real Gelfand formula (hypothesis `hg`), for every `eps > 0` there is a
constant `C > 0` such that `‖T^n‖ ≤ C * ((spectralRadius ℝ T).toReal + eps) ^ n` for
all `n`.  The proof converts the `ℝ≥0∞`-valued tendsto into the eventual norm bound
`‖T^n‖ ≤ b^n` (for `b := (spectralRadius ℝ T).toReal + eps > 0`) — raising the
`(1/n)`-power inequality to the `n`-th power with `ENNReal.rpow_mul`, and using that
`spectralRadius ℝ T < ⊤` (it is bounded by `‖T‖`); the finitely many early terms are
absorbed into `C` (a finite `Finset.sup'` of the norms `‖T^i‖`). -/
theorem eventually_pow_norm_le_of_gelfand {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hg : Tendsto (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) atTop
      (𝓝 (spectralRadius ℝ T)))
    {eps : ℝ} (heps : 0 < eps) :
    ∃ C : ℝ, 0 < C ∧ ∀ n : ℕ, ‖T ^ n‖ ≤ C * ((spectralRadius ℝ T).toReal + eps) ^ n := by
  let b : ℝ := (spectralRadius ℝ T).toReal + eps
  let δ : ℝ≥0∞ := ENNReal.ofReal b
  have hb : 0 < b := by
    dsimp [b]
    linarith [heps, ENNReal.toReal_nonneg (a := spectralRadius ℝ T)]
  have hρ_ne_top : (spectralRadius ℝ T) ≠ (⊤ : ℝ≥0∞) := by
    exact ne_top_of_le_ne_top ENNReal.coe_ne_top (spectrum.spectralRadius_le_nnnorm (𝕜 := ℝ) T)
  have hρ_lt_δ : (spectralRadius ℝ T) < δ := by
    have hρ_ofReal : ENNReal.ofReal (spectralRadius ℝ T).toReal = (spectralRadius ℝ T) :=
      ENNReal.ofReal_toReal hρ_ne_top
    rw [← hρ_ofReal]
    dsimp [δ, b]
    exact (ENNReal.ofReal_lt_ofReal_iff (by linarith : 0 < (spectralRadius ℝ T).toReal + eps)).2 (by linarith)
  -- the tendsto gives, for the neighbourhood `Iio δ` of the spectral radius, an eventual bound
  have hδnh : Set.Iio δ ∈ 𝓝 (spectralRadius ℝ T) :=
    IsOpen.mem_nhds (isOpen_Iio (a := δ)) (mem_Iio.mpr hρ_lt_δ)
  have hgel : ∀ᶠ (n : ℕ) in atTop, (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ)) ≤ δ := by
    filter_upwards [hg hδnh] with n hn using le_of_lt hn
  -- ... which, raised to the n-th power for n ≥ 1, gives the eventual real bound
  have hev : ∃ n0 : ℕ, 1 ≤ n0 ∧ ∀ n : ℕ, n0 ≤ n → ‖T ^ n‖ ≤ b ^ n := by
    have hgel1 : ∀ᶠ (n : ℕ) in atTop,
        (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ)) ≤ δ ∧ 1 ≤ n :=
      hgel.and (eventually_atTop.2 ⟨1, fun n hn => hn⟩)
    obtain ⟨N, hN⟩ := eventually_atTop.mp hgel1
    refine ⟨max N 1, le_max_right N 1, fun n hn => ?_⟩
    have hn1N : N ≤ n := le_trans (le_max_left N 1) hn
    have hn1 : 1 ≤ n := (hN n hn1N).2
    have hpow : (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ)) ≤ δ := (hN n hn1N).1
    have hleft : ((‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) ^ (n : ℝ) = ‖T ^ n‖₊ := by
      rw [← ENNReal.rpow_mul]
      rw [show (1 / (n : ℝ)) * (n : ℝ) = 1 by
        exact div_mul_cancel₀ (1 : ℝ) (by exact_mod_cast (ne_of_gt hn1))]
      rw [ENNReal.rpow_one]
    have hle' : ((‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) ^ (n : ℝ) ≤ δ ^ (n : ℝ) :=
      ENNReal.rpow_le_rpow hpow (by exact_mod_cast Nat.zero_le n)
    have hle : (‖T ^ n‖₊ : ℝ≥0∞) ≤ δ ^ (n : ℝ) := hleft ▸ hle'
    have hright : δ ^ (n : ℝ) = δ ^ n := by
      rw [ENNReal.rpow_natCast]
    have hbound : (‖T ^ n‖₊ : ℝ≥0∞) ≤ δ ^ n := by
      simpa [hright] using hle
    have hδ_rewrite : δ ^ n = ENNReal.ofReal (b ^ n) := by
      dsimp [δ]
      rw [← ENNReal.ofReal_pow hb.le]
    have hreal : ‖T ^ n‖ ≤ b ^ n := by
      have hle2 : (‖T ^ n‖₊ : ℝ≥0∞) ≤ ENNReal.ofReal (b ^ n) := by
        simpa [hδ_rewrite] using hbound
      have hconv := (ENNReal.le_ofReal_iff_toReal_le
        (a := (‖T ^ n‖₊ : ℝ≥0∞)) (b := b ^ n)
        (by exact ENNReal.coe_ne_top : (‖T ^ n‖₊ : ℝ≥0∞) ≠ ⊤)
        (pow_nonneg hb.le n)).mp hle2
      simpa using hconv
    exact hreal
  -- absorb the finitely many early terms into a single constant C (a finite sup')
  obtain ⟨n0, hn0ge1, hn0⟩ := hev
  let s : Finset ℕ := Finset.range n0
  have hs_ne : s.Nonempty := (Finset.nonempty_range_iff).2 (by omega)
  let M : ℝ := s.sup' hs_ne (fun i : ℕ => ‖T ^ i‖)
  have hM1 : 1 ≤ M := by
    have h0 : (0 : ℕ) ∈ s := by
      dsimp [s]
      exact Finset.mem_range.mpr (by omega)
    have hle0 : ‖T ^ 0‖ ≤ M :=
      Finset.le_sup' (s := s) (f := fun i : ℕ => ‖T ^ i‖) (b := (0 : ℕ)) h0
    have hnorm : (1 : ℝ) ≤ ‖T ^ 0‖ := by simp
    exact le_trans hnorm hle0
  have hM0 : 0 ≤ M := le_trans zero_le_one hM1
  have hMle : ∀ i : ℕ, i ∈ s → ‖T ^ i‖ ≤ M := fun i hi =>
    Finset.le_sup' (s := s) (f := fun j : ℕ => ‖T ^ j‖) (b := i) hi
  by_cases hb1 : b ≤ 1
  · -- 0 < b ≤ 1: take C := M / b^n0
    let C : ℝ := M / b ^ n0
    have hC0 : 0 < C := by
      dsimp [C]
      exact div_pos (lt_of_lt_of_le zero_lt_one hM1) (pow_pos hb n0)
    refine ⟨C, hC0, fun n => ?_⟩
    by_cases hn : n < n0
    · have hnMem : n ∈ s := by
        dsimp [s]
        exact Finset.mem_range.mpr hn
      have hMleN : ‖T ^ n‖ ≤ M := hMle n hnMem
      have hbn0_le : b ^ n0 ≤ b ^ n := pow_le_pow_of_le_one hb.le hb1 (le_of_lt hn)
      have hbdiv : 1 ≤ b ^ n / b ^ n0 := (one_le_div₀ (by positivity : 0 < b ^ n0)).2 hbn0_le
      have hmain : M ≤ C * b ^ n := by
        rw [show C * b ^ n = M * (b ^ n / b ^ n0) by
          dsimp [C]
          field_simp [show b ^ n0 ≠ 0 by positivity]]
        have hmul : M ≤ M * (b ^ n / b ^ n0) := by
          simpa using (mul_le_mul_of_nonneg_left hbdiv (le_of_lt (lt_of_lt_of_le zero_lt_one hM1)))
        exact hmul
      exact le_trans hMleN hmain
    · have hlate : ‖T ^ n‖ ≤ b ^ n := hn0 n (le_of_not_gt hn)
      have hbn0_le1 : b ^ n0 ≤ (1 : ℝ) := by
        simpa using pow_le_pow_of_le_one hb.le hb1 (Nat.zero_le n0)
      have hbndM : b ^ n0 ≤ M := le_trans hbn0_le1 hM1
      have hCge : (1 : ℝ) ≤ C := by
        dsimp [C]
        exact (one_le_div₀ (by positivity : 0 < b ^ n0)).2 hbndM
      have hCle : b ^ n ≤ C * b ^ n := by
        simpa using (mul_le_mul_of_nonneg_right hCge (pow_nonneg hb.le n))
      exact le_trans hlate hCle
  · -- 1 < b: take C := M
    have h1b : 1 < b := lt_of_not_ge hb1
    refine ⟨M, lt_of_lt_of_le zero_lt_one hM1, fun n => ?_⟩
    by_cases hn : n < n0
    · have hnMem : n ∈ s := by
        dsimp [s]
        exact Finset.mem_range.mpr hn
      have hMleN : ‖T ^ n‖ ≤ M := hMle n hnMem
      have hb_ge : (1 : ℝ) ≤ b ^ n := one_le_pow₀ h1b.le
      have hmain : M ≤ M * b ^ n := by
        simpa using (mul_le_mul_of_nonneg_left hb_ge hM0)
      exact le_trans hMleN hmain
    · have hlate : ‖T ^ n‖ ≤ b ^ n := hn0 n (le_of_not_gt hn)
      have hCle : b ^ n ≤ M * b ^ n := by
        simpa using (mul_le_mul_of_nonneg_right hM1 (pow_nonneg hb.le n))
      exact le_trans hlate hCle

/-- **Bounded orbit estimate** (hypothesis form): assuming the real Gelfand formula
(hypothesis `hg`, i.e. `‖T^n‖₊ ^ (1/n) → ρ(T)`), for every `eps > 0` there is a
constant `C > 0` such that `‖T^n‖ ≤ C * ((spectralRadius ℝ T).toReal + eps) ^ n` for
all `n`.  This is the bounded-orbit estimate on which the whole resolvent-positivity
route at the spectral radius rests; the hypothesis `hg` is necessary because the
general-real Gelfand upper bound is false (see `RealGelfand.counterexampleRotation`). -/
theorem eventually_pow_norm_le {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hg : Tendsto (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) atTop
      (𝓝 (spectralRadius ℝ T)))
    (eps : ℝ) (heps : 0 < eps) :
    ∃ C : ℝ, 0 < C ∧ ∀ n : ℕ, ‖T ^ n‖ ≤ C * ((spectralRadius ℝ T).toReal + eps) ^ n := by
  exact eventually_pow_norm_le_of_gelfand hg heps



/-- **Neumann (geometric) series identity for the resolvent at the spectral
radius**: assuming the real Gelfand formula (hypothesis `hg`), whenever `0 < lam` and
the spectral radius satisfies
`(spectralRadius ℝ T).toReal < lam`, the resolvent `(lam • 1 - T)⁻¹` equals the
convergent geometric series `Σₙ (lam⁻¹)ⁿ⁺¹ · Tⁿ`, i.e. `Tⁿ / lamⁿ⁺¹` in the scalar
sense.  The convergence (at `lam` strictly above `ρ(T)`, not just above `‖T‖`) rests
on the bounded-orbit estimate `eventually_pow_norm_le`. -/
theorem resolvent_neumann_series_at_radius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hg : Tendsto (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) atTop
      (𝓝 (spectralRadius ℝ T)))
    {lam : ℝ}
    (hlam : 0 < lam) (hrho : (spectralRadius ℝ T).toReal < lam) :
    HasSum (fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n)
      (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  obtain ⟨g, hg_ρ, hg_lam : g < lam⟩ := exists_between hrho
  have hg0 : 0 < g := lt_of_le_of_lt ENNReal.toReal_nonneg hg_ρ
  let eps : ℝ := g - (spectralRadius ℝ T).toReal
  have heps : 0 < eps := sub_pos.mpr hg_ρ
  have hg_eq : (spectralRadius ℝ T).toReal + eps = g := by
    dsimp [eps]
    ring
  obtain ⟨C, hC, hCbound⟩ :=
    eventually_pow_norm_le (T := T) hg eps (by simpa [eps] using heps)
  have hCbound' : ∀ n : ℕ, ‖T ^ n‖ ≤ C * g ^ n := by
    intro n
    simpa [hg_eq] using hCbound n
  let q : ℝ := g / lam
  have hq0 : 0 ≤ q := by
    dsimp [q]
    exact div_nonneg hg0.le hlam.le
  have hq1 : q < 1 := by
    dsimp [q]
    exact (div_lt_one hlam).2 hg_lam
  let a : ℕ → C(X, ℝ) →L[ℝ] C(X, ℝ) :=
    fun n => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n
  -- termwise norm bound: ‖a n‖ ≤ (C / lam) * q^n (geometric tail)
  have hterm : ∀ n : ℕ, ‖a n‖ ≤ (C / lam) * q ^ n := by
    intro n
    have hlamnn : 0 ≤ (lam⁻¹ : ℝ) ^ (n + 1) :=
      pow_nonneg (inv_nonneg.mpr hlam.le) (n + 1)
    calc
      ‖a n‖ ≤ ‖(lam⁻¹ : ℝ) ^ (n + 1)‖ * ‖T ^ n‖ := by
        dsimp [a]
        exact ContinuousLinearMap.opNorm_smul_le ((lam⁻¹ : ℝ) ^ (n + 1)) (T ^ n)
      _ = (lam⁻¹ : ℝ) ^ (n + 1) * ‖T ^ n‖ := by
        rw [Real.norm_eq_abs, abs_of_nonneg hlamnn]
      _ ≤ (lam⁻¹ : ℝ) ^ (n + 1) * (C * g ^ n) := by
        exact mul_le_mul_of_nonneg_left (hCbound' n) hlamnn
      _ = (C / lam) * q ^ n := by
        dsimp [q]
        field_simp [show lam ≠ 0 by exact ne_of_gt hlam]
        ring_nf
        rw [mul_inv_cancel₀ (ne_of_gt hlam), one_mul]
  -- the bounding geometric series is summable (q < 1)
  have hgeo : Summable (fun n : ℕ => q ^ n) :=
    summable_geometric_of_norm_lt_one (x := q)
      (by simpa [Real.norm_eq_abs, abs_of_nonneg hq0] using hq1)
  have hnorm : Summable (fun n : ℕ => (C / lam) * q ^ n) := by
    simpa [smul_eq_mul] using (Summable.const_smul (C / lam) hgeo)
  have hsum_a : Summable a :=
    Summable.of_norm_bounded (f := a)
      (g := fun n : ℕ => (C / lam) * q ^ n) hnorm hterm
  -- rescale to rT := lam⁻¹ • T: a n = (lam⁻¹) • rT^n
  let rT : C(X, ℝ) →L[ℝ] C(X, ℝ) := (lam⁻¹ : ℝ) • T
  let R : C(X, ℝ) →L[ℝ] C(X, ℝ) := ∑' n : ℕ, rT ^ n
  have hflat : (fun n : ℕ => (lam⁻¹ : ℝ) • rT ^ n) =
      fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n := by
    funext n
    calc
      (lam⁻¹ : ℝ) • rT ^ n = (lam⁻¹ : ℝ) • ((lam⁻¹ : ℝ) ^ n • T ^ n) := by
        rw [resolvent_smul_pow]
      _ = ((lam⁻¹ : ℝ) * (lam⁻¹ : ℝ) ^ n) • T ^ n :=
        smul_smul (lam⁻¹ : ℝ) ((lam⁻¹ : ℝ) ^ n) (T ^ n)
      _ = (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n := by rw [pow_succ']
  have hsum_rT : Summable (fun n : ℕ => rT ^ n) := by
    have hs : Summable (fun n : ℕ => (lam⁻¹ : ℝ) • rT ^ n) :=
      hsum_a.congr (fun n => (congr_fun hflat n).symm)
    simpa [smul_smul, mul_inv_cancel₀ (ne_of_gt hlam)]
      using (Summable.const_smul lam hs)
  have hR_sum : HasSum (fun n : ℕ => rT ^ n) R := hsum_rT.hasSum
  -- the geometric identity (1 - rT) * Σ rT^n = 1 via limits of partial sums
  let s : ℕ → C(X, ℝ) →L[ℝ] C(X, ℝ) :=
    fun n => (Finset.range n).sum (fun k : ℕ => rT ^ k)
  have hS : Tendsto s atTop (𝓝 R) := hR_sum.tendsto_sum_nat
  have htel : ∀ n : ℕ, (1 - rT) * s n = 1 - rT ^ n := by
    intro n
    exact mul_neg_geom_sum rT n
  have htel' : ∀ n : ℕ, s n * (1 - rT) = 1 - rT ^ n := by
    intro n
    exact geom_sum_mul_neg rT n
  -- rT^n → 0 geometrically (rate q < 1) via the bounded-orbit estimate
  have hpow0 : Tendsto (fun n : ℕ => rT ^ n) atTop (𝓝 0) := by
    have hqt : Tendsto (fun n : ℕ => C * q ^ n) atTop (𝓝 0) := by
      simpa using (tendsto_pow_atTop_nhds_zero_of_lt_one hq0 hq1).const_mul C
    have hsq : Tendsto (fun n : ℕ => ‖rT ^ n‖) atTop (𝓝 0) :=
      squeeze_zero (fun n => norm_nonneg (rT ^ n)) (fun n => by
        calc
          ‖rT ^ n‖ = ‖(lam⁻¹ : ℝ) ^ n • T ^ n‖ := by rw [resolvent_smul_pow]
          _ ≤ ‖(lam⁻¹ : ℝ) ^ n‖ * ‖T ^ n‖ := by
            exact ContinuousLinearMap.opNorm_smul_le ((lam⁻¹ : ℝ) ^ n) (T ^ n)
          _ = (lam⁻¹ : ℝ) ^ n * ‖T ^ n‖ := by
            rw [Real.norm_eq_abs, abs_of_nonneg (pow_nonneg (inv_nonneg.mpr hlam.le) n)]
          _ ≤ (lam⁻¹ : ℝ) ^ n * (C * g ^ n) := by
            exact mul_le_mul_of_nonneg_left (hCbound' n)
              (pow_nonneg (inv_nonneg.mpr hlam.le) n)
          _ = C * q ^ n := by
            dsimp [q]
            field_simp [show lam ≠ 0 by exact ne_of_gt hlam]
            ring_nf) hqt
    exact (tendsto_zero_iff_norm_tendsto_zero
      (E := C(X, ℝ) →L[ℝ] C(X, ℝ)) (f := fun n : ℕ => rT ^ n) (a := atTop)).2
        (by simpa using hsq)
  -- left-multiplication by (1 - rT) is continuous (norm transfer)
  have hL : Tendsto (fun n : ℕ => (1 - rT) * s n) atTop (𝓝 ((1 - rT) * R)) := by
    have hS0 : Tendsto (fun n : ℕ => ‖s n - R‖) atTop (𝓝 0) :=
      (tendsto_iff_norm_sub_tendsto_zero
        (E := C(X, ℝ) →L[ℝ] C(X, ℝ)) (f := fun n : ℕ => s n) (a := atTop) (b := R)).1 hS
    have hcnst : Tendsto (fun n : ℕ => ‖1 - rT‖ * ‖s n - R‖) atTop (𝓝 0) := by
      simpa using (hS0.const_mul (‖1 - rT‖ : ℝ))
    have hsq : Tendsto (fun n : ℕ => ‖(1 - rT) * s n - (1 - rT) * R‖) atTop (𝓝 0) :=
      squeeze_zero (fun n => norm_nonneg ((1 - rT) * s n - (1 - rT) * R)) (fun n => by
        calc
          ‖(1 - rT) * s n - (1 - rT) * R‖ = ‖(1 - rT) * (s n - R)‖ := by rw [mul_sub]
          _ ≤ ‖1 - rT‖ * ‖s n - R‖ := norm_mul_le (1 - rT) (s n - R)) hcnst
    exact (tendsto_iff_norm_sub_tendsto_zero
      (E := C(X, ℝ) →L[ℝ] C(X, ℝ)) (f := fun n : ℕ => (1 - rT) * s n) (a := atTop)
        (b := (1 - rT) * R)).2 hsq
  -- right-multiplication by (1 - rT) is continuous
  have hR' : Tendsto (fun n : ℕ => s n * (1 - rT)) atTop (𝓝 (R * (1 - rT))) := by
    have hS0 : Tendsto (fun n : ℕ => ‖s n - R‖) atTop (𝓝 0) :=
      (tendsto_iff_norm_sub_tendsto_zero
        (E := C(X, ℝ) →L[ℝ] C(X, ℝ)) (f := fun n : ℕ => s n) (a := atTop) (b := R)).1 hS
    have hcnst : Tendsto (fun n : ℕ => ‖s n - R‖ * ‖1 - rT‖) atTop (𝓝 0) := by
      simpa using (hS0.mul_const (‖1 - rT‖ : ℝ))
    have hsq : Tendsto (fun n : ℕ => ‖s n * (1 - rT) - R * (1 - rT)‖) atTop (𝓝 0) :=
      squeeze_zero (fun n => norm_nonneg (s n * (1 - rT) - R * (1 - rT))) (fun n => by
        calc
          ‖s n * (1 - rT) - R * (1 - rT)‖ = ‖(s n - R) * (1 - rT)‖ := by rw [sub_mul]
          _ ≤ ‖s n - R‖ * ‖1 - rT‖ := norm_mul_le (s n - R) (1 - rT)) hcnst
    exact (tendsto_iff_norm_sub_tendsto_zero
      (E := C(X, ℝ) →L[ℝ] C(X, ℝ)) (f := fun n : ℕ => s n * (1 - rT)) (a := atTop)
        (b := R * (1 - rT))).2 hsq
  -- pass to the limit in the telescoping identities
  have hL1 : Tendsto (fun n : ℕ => (1 - rT) * s n) atTop (𝓝 1) := by
    have h1 : Tendsto (fun n : ℕ => 1 - rT ^ n) atTop (𝓝 (1 - 0)) :=
      tendsto_const_nhds.sub hpow0
    simpa [htel] using h1
  have hR2 : Tendsto (fun n : ℕ => s n * (1 - rT)) atTop (𝓝 1) := by
    have h1 : Tendsto (fun n : ℕ => 1 - rT ^ n) atTop (𝓝 (1 - 0)) :=
      tendsto_const_nhds.sub hpow0
    simpa [htel'] using h1
  have hLR : (1 - rT) * R = 1 := tendsto_nhds_unique hL hL1
  have hRL : R * (1 - rT) = 1 := tendsto_nhds_unique hR' hR2
  -- Ring.inverse (1 - rT) = R by the two-sided-inverse characterization
  let u : (C(X, ℝ) →L[ℝ] C(X, ℝ))ˣ := ⟨1 - rT, R, hLR, hRL⟩
  have hu : IsUnit (1 - rT) := ⟨u, rfl⟩
  have hRinv : Ring.inverse (1 - rT) = R := by
    rw [Ring.inverse_unit (u := u)]
    rfl
  -- scale back to lam: Ring.inverse (lam • 1 - T) = lam⁻¹ • R
  have hM : lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T = lam • (1 - rT) := by
    have hsmul : lam • ((lam⁻¹ : ℝ) • T) = T := by
      rw [smul_smul]
      rw [mul_inv_cancel₀ (ne_of_gt hlam), one_smul]
    rw [smul_sub]
    simp [rT, hsmul]
  have hres : Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
      (lam⁻¹ : ℝ) • Ring.inverse (1 - rT) := by
    calc
      Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
          Ring.inverse (lam • (1 - rT)) := by rw [hM]
      _ = (lam⁻¹ : ℝ) • Ring.inverse (1 - rT) :=
        resolvent_inverse_smul lam (ne_of_gt hlam) (1 - rT) hu
  -- the a-series sums to lam⁻¹ • R
  have hsumA : HasSum a ((lam⁻¹ : ℝ) • R) := by
    have hsc : HasSum (fun n : ℕ => (lam⁻¹ : ℝ) • rT ^ n) ((lam⁻¹ : ℝ) • R) :=
      HasSum.const_smul (lam⁻¹ : ℝ) hR_sum
    convert hsc using 1
    exact hflat.symm
  rw [hres, hRinv]
  exact hsumA

/-- **Resolvent positivity at the spectral radius**: assuming the real Gelfand formula
(hypothesis `hg`), if `T` is a positive operator,
`0 < lam` and `(spectralRadius ℝ T).toReal < lam`, then the resolvent
`Ring.inverse (lam • 1 - T)` is well-defined (its Neumann series
`resolvent_neumann_series_at_radius` converges above `ρ(T)`, not just above `‖T‖`)
and is itself a positive operator.  This is the positivity half of the
Krein–Rutman strategy beyond the operator norm: resolvents of positive operators at
positive levels outside the spectrum are positive. -/
theorem resolvent_positivity_at_radius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hg : Tendsto (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) atTop
      (𝓝 (spectralRadius ℝ T)))
    (hTpos : IsPositive T) {lam : ℝ} (hlam : 0 < lam)
    (hrho : (spectralRadius ℝ T).toReal < lam) :
    IsPositive (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  -- the Neumann series converges at the radius and equals the inverse
  have hsum : HasSum (fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n)
      (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) :=
    resolvent_neumann_series_at_radius (T := T) hg hlam hrho
  let a : ℕ → C(X, ℝ) →L[ℝ] C(X, ℝ) :=
    fun n => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n
  have htsum : Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) =
      ∑' n : ℕ, a n := hsum.tsum_eq.symm
  have hs : Summable a := hsum.summable
  -- each summand is a positive operator: (lam⁻¹)ⁿ⁺¹ ≥ 0 and Tⁿ positive
  have hpos : ∀ n : ℕ, IsPositive (a n) := by
    intro n
    dsimp [a]
    exact IsPositive.smul
      (pow_nonneg (inv_nonneg.mpr (le_of_lt hlam)) (n + 1)) (hTpos.pow n)
  -- the infinite sum of positive operators is positive
  intro g hg
  rw [mem_positiveCone]
  intro x
  have hs_app : Summable (fun n : ℕ => (a n) g) := by
    let φ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
      ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
    simpa [φ] using (ContinuousLinearMap.summable φ hs)
  have happ : (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) g =
      ∑' n : ℕ, (a n) g := by
    calc
      (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) g =
          (∑' n : ℕ, a n) g := by rw [htsum]
      _ = ∑' n : ℕ, (a n) g := by
        let φ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
          ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
        have hmap := ContinuousLinearMap.map_tsum (φ := φ) hs
        simpa [φ] using hmap
  have hx : ((Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) g) x =
      ∑' n : ℕ, (((a n) g) x) := by
    calc
      ((Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) g) x =
          (∑' n : ℕ, (a n) g) x := by rw [happ]
      _ = ∑' n : ℕ, (((a n) g) x) := by
        have hmap := ContinuousLinearMap.map_tsum (φ := resolvent_eval x) hs_app
        simpa [resolvent_eval] using hmap
  have hterm : ∀ n : ℕ, 0 ≤ (((a n) g) x) := by
    intro n
    exact (IsPositive.apply_nonneg (hpos n) hg) x
  rw [hx]
  exact tsum_nonneg hterm
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
2. *Resolvent (Neumann) positivity at the radius*: for `lam > ρ(T)` represent
   `(lam − T)⁻¹ = Σₙ Tⁿ / lamⁿ⁺¹` (needs the convergence-radius argument at the
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

/-- **Spectral-radius eigenvector with domination**:
For a compact, positive operator `T` with `0 < ρ(T)`, there exists a
nonzero vector `v` (real, not necessarily positive) and a real eigenvalue
`μ` with `|μ| = ρ(T)` such that `T v = μ • v` and the pointwise domination
`ρ(T) · |v(x)| ≤ (T |v|)(x)` holds for all `x`.

This lemma combines `mem_spectrum_abs_eq_spectralRadius`,
`hasEigenvalue_of_mem_spectrum_ne_zero`, and `positive_abs_ge` into a
single statement that is the starting point of the Gelfand orbit proof
strategy for Krein–Rutman.  It provides a nonzero `|v|` on the cone with
`T |v| ≥ ρ(T) |v|`, which can then be normalized and passed to the limit
along the orbit `Tⁿ e` for any cone vector `e`.

The lemma does not claim `v` itself is positive — that's exactly what
`kreinRutman_core` aims to prove.  This intermediate result is a true,
fully verified lemma and serves as infrastructure for the frontier.
-/
theorem exists_eigenvector_with_domination {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T)
    (hρ : 0 < spectralRadius ℝ T) :
    ∃ v : C(X, ℝ), v ≠ 0 ∧ ∃ μ : ℝ,
      |μ| = (spectralRadius ℝ T).toReal ∧ T v = μ • v ∧
      ∀ x : X, (spectralRadius ℝ T).toReal * |v x| ≤ (T |v|) x := by
  -- spectral value lemma gives μ with |μ| = ρ(T) in spectrum
  obtain ⟨μ, hμσ, hμ0, hμρ⟩ := mem_spectrum_abs_eq_spectralRadius (T := T) hρ
  -- Fredholm alternative gives eigenvector v for μ ≠ 0
  have hμ0' : μ ≠ 0 := by simpa [hμρ] using hμ0
  have hμeig : Module.End.HasEigenvalue (T : Module.End ℝ (C(X, ℝ))) μ :=
    hasEigenvalue_of_mem_spectrum_ne_zero hTcomp hμ0' hμσ
  -- Use the eigenvector given by HasEigenvalue
  obtain ⟨v, hv⟩ := hμeig.exists_hasEigenvector
  -- hv : f.HasEigenvector μ v is a conjunction: v ∈ eigenspace ∧ v ≠ 0
  have hvT : T v = μ • v := by
    exact Module.End.HasEigenvector.apply_eq_smul (f := (T : Module.End ℝ (C(X, ℝ)))) (μ := μ)
      (x := v) hv
  have hv0 : v ≠ 0 := hv.2
  -- positivity transfer gives the domination
  refine ⟨v, hv0, μ, hμρ, hvT, fun x => ?_⟩
  rw [← hμρ]
  exact positive_abs_ge hTpos hvT x

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
