/-
Copyright (c) 2026 Tobias Weiss
Gelfand's formula over ℝ for positive operators on C(X, ℝ)

Mathlib's Gelfand formula (`pow_nnnorm_pow_one_div_tendsto_nhds_spectralRadius`)
holds only over ℂ.  This file proves the real form for *positive* operators
`T : C(X, ℝ) →L[ℝ] C(X, ℝ)`:

  lim ‖Tⁿ‖^(1/n) = ρ(T)   (spectralRadius ℝ T, the ℝ-spectral radius),

by an elementary argument that avoids the complexification:

1. *Resolvent positivity* — `(λ - T)⁻¹` is a positive operator for every
   `λ > ρ(T)`.  Above `‖T‖` this is the Neumann series
   (`Riemann.KreinRutman.resolvent_neumann_series`); below `‖T‖` we run
   the classical "clopen" argument: the set of resolvent levels with positive
   resolvent is open in ℝ (rescale a positive resolvent by a small positive
   geometric factor) and closed in `(ρ, ∞)` (the resolvent is norm-continuous
   on the resolvent set, and the positive cone is closed), so by connectedness
   of `Ioi ρ` it is all of `(ρ, ∞)`.
2. *Partial-sum domination* — with `(λ - T)⁻¹ ≥ 0`, expanding
   `(λ - T)(Σ_{n ≤ M} λ^{-n-1} • Tⁿ) = 1 - λ^{-M-1} • T^{M+1}` shows each
   Neumann partial sum is pointwise dominated by the resolvent.
3. *Fixed-pair growth* — for `L := limsup ‖Tⁿ‖^{1/n} > ρ` we build ONE fixed
   pair `x₀ ∈ positiveCone`, `φ₀ ≥ 0` with `limsup φ₀(Tⁿx₀)^{1/n} ≥ L - ε`
   (thin a near-sup-norm subsequence with `nₖ ≥ k²`, then average with
   `x₀ = Σ 2⁻ᵏ xₖ`, `φ₀ = Σ 2⁻ᵏ δ_{tₖ}` — positivity makes both averages see
   every term).
4. *Contradiction* — by (2) the scalar series `Σ φ₀(Tⁿx₀) λ'⁻ⁿ⁻¹` converges at
   any `λ' ∈ (ρ, L)`, so its terms tend to 0, forcing
   `limsup φ₀(Tⁿx₀)^{1/n} ≤ λ' < L`.  Hence `limsup ‖Tⁿ‖^{1/n} ≤ ρ`.
5. *Lower bound* — `ρ = sup{|μ| : μ ∈ σ_ℝ(T)}` is attained (the spectrum of a
   bounded operator is compact; if `σ_ℝ(T) = ∅` then `ρ = 0`), every nonzero
   spectral value of a compact operator is an eigenvalue, and an eigenvector
   gives `‖Tⁿ‖ ≥ ρⁿ`.

Together with `Riemann.KreinRutman.resolvent_neumann_series_at_radius` this
unblocks the resolvent route to Krein–Rutman over the real field.
-/

import Riemann.KreinRutman

open scoped NNReal ENNReal Topology
open ContinuousMap Filter Set

namespace Riemann

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [Nonempty X]

-- Cone-side lemmas only need the pointwise order; the linter flags the
-- section variables they inherit without using.
set_option linter.unusedSectionVars false
set_option maxHeartbeats 1000000

/-! ## Elementary positivity helpers -/

/-- The positive cone is closed under positively weighted infinite sums of
functions (absolute convergence in the sup norm). -/
theorem positiveCone_tsum {g : ℕ → C(X, ℝ)} (w : ℕ → ℝ) (hw : ∀ k, 0 ≤ w k)
    (hg : ∀ k, g k ∈ positiveCone) (hsum : Summable fun k => w k • g k) :
    ∑' k, w k • g k ∈ positiveCone := by
  intro x
  rw [← ContinuousMap.tsum_apply hsum x]
  refine tsum_nonneg fun k => ?_
  simp only [ContinuousMap.coe_smul, Pi.smul_apply, smul_eq_mul]
  exact mul_nonneg (hw k) (hg k x)

/-- An absolutely summable series of positive operators has positive sum. -/
theorem isPositive_tsum {T : ℕ → (C(X, ℝ) →L[ℝ] C(X, ℝ))}
    (hT : ∀ n, IsPositive (T n)) (hsum : Summable T) :
    IsPositive (∑' n, T n) := by
  intro g hg
  have hs_app : Summable fun n : ℕ => (T n) g := by
    let φ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
      ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
    simpa [φ] using ContinuousLinearMap.summable φ hsum
  have happ : (∑' n : ℕ, T n) g = ∑' n : ℕ, (T n) g := by
    let φ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
      ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
    have hmap := ContinuousLinearMap.map_tsum (φ := φ) hsum
    simpa [φ] using hmap
  have hpos : ∀ n : ℕ, ∀ x : X, 0 ≤ (T n) g x := by
    intro n
    exact IsPositive.apply_nonneg (hT n) hg
  intro x
  rw [happ, ← ContinuousMap.tsum_apply hs_app x]
  exact tsum_nonneg fun n => hpos n x

/-- The composition of positive operators is positive. -/
theorem IsPositive.mul' {A B : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hA : IsPositive A)
    (hB : IsPositive B) : IsPositive (A * B) :=
  fun _g hg => hA (hB hg)

/-- Powers of positive operators are positive. -/
theorem IsPositive.pow' {A : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hA : IsPositive A) (n : ℕ) :
    IsPositive (A ^ n) := by
  induction n with
  | zero => intro g hg; simpa using hg
  | succ k ih =>
    rw [pow_succ]
    exact ih.mul' hA

/-- Sup-norm monotonicity on the cone: `0 ≤ f ≤ g` forces `‖f‖ ≤ ‖g‖`. -/
theorem norm_mono_of_cone {f g : C(X, ℝ)} (hf : f ∈ positiveCone) (hfg : f ≤ g) :
    ‖f‖ ≤ ‖g‖ := by
  have hfn : ∀ x : X, 0 ≤ f x := hf
  refine (ContinuousMap.norm_le f (norm_nonneg g)).2 fun x => ?_
  rw [Real.norm_eq_abs, abs_of_nonneg (hfn x)]
  exact le_trans (hfg x)
    (le_trans (le_abs_self (g x)) (ContinuousMap.norm_coe_le_norm g x))

/-- Scalar-power identity for CLMs: `(s • A) ^ i = s ^ i • A ^ i` (mathlib's
`smul_pow` needs `IsScalarTower ℝ A A`, which the CLM-instance graph lacks). -/
theorem smul_pow' (s : ℝ) (A : C(X, ℝ) →L[ℝ] C(X, ℝ)) (i : ℕ) :
    ((s • A) ^ i) = ((s ^ i : ℝ)) • (A ^ i) := by
  induction i with
  | zero => simp
  | succ n ih =>
    have h1 : (s • A) ^ (n + 1) = (s • A) ^ n * (s • A) := pow_succ (s • A) n
    have h2 : s ^ (n + 1) = s ^ n * s := pow_succ s n
    have h3 : A ^ (n + 1) = A ^ n * A := pow_succ A n
    rw [h1, ih, resolvent_smul_mul_assoc, resolvent_mul_smul_assoc,
      smul_smul, h2, h3]

/-- Finite sums of cone elements stay in the cone. -/
theorem positiveCone_sum_range {f : ℕ → C(X, ℝ)} (n : ℕ)
    (hf : ∀ i ∈ Finset.range n, f i ∈ positiveCone) :
    (∑ i ∈ Finset.range n, f i) ∈ positiveCone := by
  induction n with
  | zero => intro x; simp
  | succ m ih =>
    rw [Finset.sum_range_succ, mem_positiveCone]
    intro x
    rw [ContinuousMap.add_apply]
    exact add_nonneg
      ((ih fun i hi =>
        hf i (Finset.mem_range.mpr (Nat.lt_succ_of_lt (Finset.mem_range.mp hi)))) x)
      ((hf m (Finset.mem_range.mpr m.lt_succ_self)) x)

/-! ## Resolvent positivity -/

/-- Nonnegative scalar multiples of positive operators are positive. -/
theorem IsPositive.smul' {c : ℝ} (hc : 0 ≤ c) {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hT : IsPositive T) : IsPositive (c • T) := by
  intro g hg
  rw [mem_positiveCone]
  intro x
  simp only [_root_.smul_apply, ContinuousMap.coe_smul, Pi.smul_apply,
    smul_eq_mul]
  exact mul_nonneg hc (hT hg x)

/-- Bridge: `Ring.inverse` is continuous at a unit, stated with the
`ContinuousLinearMap.monoidWithZero` instance (mathlib's
`NormedRing.inverse_continuousAt` is stated with the `NormedRing.toRing`
instance path, which the unifier does not identify automatically). -/
theorem ringInverse_continuousAt' (u : (C(X, ℝ) →L[ℝ] C(X, ℝ))ˣ) :
    ContinuousAt (@Ring.inverse (C(X, ℝ) →L[ℝ] C(X, ℝ)) ContinuousLinearMap.monoidWithZero)
      (u : C(X, ℝ) →L[ℝ] C(X, ℝ)) :=
  (NormedRing.inverse_continuousAt
    (R := C(X, ℝ) →L[ℝ] C(X, ℝ)) u).congr
    (Filter.Eventually.of_forall fun _x => rfl)

/-- For `0 < μ` and `‖T‖ < μ`, `μ • 1 - T` is a unit, i.e. `μ ∈ ρ(T)`.

Note: `spectrum.mem_resolventSet_of_norm_lt` is unusable here because
`C(X, ℝ) →L[ℝ] C(X, ℝ)` does not carry a `NormedRing` instance in mathlib
(only the `OpNormClass`-based structures); we therefore build the unit by
hand, rescaling onto `1 - μ⁻¹ • T` exactly as in KreinRutman's resolvent
block. -/
theorem isUnit_of_gt_norm {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {μ : ℝ} (hpos : 0 < μ)
    (hμ : ‖T‖ < μ) : IsUnit ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) := by
  have hx1 : ‖((μ⁻¹ : ℝ) • T)‖ < 1 := resolvent_scaled_norm_lt_one hpos T hμ
  have hab : ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T)
      * ∑' i : ℕ, ((μ⁻¹ : ℝ) • T) ^ i = 1 := mul_neg_geom_series ((μ⁻¹ : ℝ) • T) hx1
  have hba : (∑' i : ℕ, ((μ⁻¹ : ℝ) • T) ^ i)
      * ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T) = 1 :=
    geom_series_mul_neg ((μ⁻¹ : ℝ) • T) hx1
  have hxunit : IsUnit ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T) :=
    ⟨⟨_, _, hab, hba⟩, rfl⟩
  have hinvx : Ring.inverse ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T)
      * ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T) = 1 :=
    Ring.inverse_mul_cancel _ hxunit
  have hinvx2 : ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T)
      * Ring.inverse ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T) = 1 := by
    rw [Ring.inverse_of_isUnit hxunit]
    simpa using Units.mul_inv_cancel hxunit.unit
  have hresc : (μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T
      = (μ : ℝ) • ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T) := by
    rw [smul_sub, smul_smul, mul_inv_cancel₀ hpos.ne', one_smul]
  refine ⟨⟨(μ : ℝ) • ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T),
    (μ⁻¹ : ℝ) • Ring.inverse ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (μ⁻¹ : ℝ) • T), ?_, ?_⟩,
    by rw [hresc]⟩
  · rw [resolvent_smul_mul_assoc, resolvent_mul_smul_assoc, smul_smul,
      mul_inv_cancel₀ hpos.ne', one_smul, hinvx2]
  · rw [resolvent_smul_mul_assoc, resolvent_mul_smul_assoc, smul_smul,
      inv_mul_cancel₀ hpos.ne', one_smul, hinvx]

/-- **Resolvent positivity above the norm**: for `μ > ‖T‖` the resolvent exists
and is a positive operator. -/
theorem resolvent_positivity_above_norm {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) {μ : ℝ} (hμ : ‖T‖ < μ) :
    μ ∈ resolventSet ℝ T ∧
      IsPositive (Ring.inverse ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  have hpos : 0 < μ := lt_of_le_of_lt (norm_nonneg T) hμ
  have huμ : IsUnit ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) := isUnit_of_gt_norm hpos hμ
  refine ⟨by simpa only [resolventSet, Set.mem_ofPred_eq,
    Algebra.algebraMap_eq_smul_one] using huμ, ?_⟩
  have hterm : ∀ n : ℕ, IsPositive ((μ⁻¹ : ℝ) ^ (n + 1) • T ^ n) := fun n =>
    IsPositive.smul' (pow_nonneg (inv_nonneg.mpr (le_of_lt hpos)) _) (hTpos.pow' n)
  have hser := Riemann.resolvent_neumann_series hpos hμ
  rw [← hser.tsum_eq]
  exact isPositive_tsum hterm hser.summable

/-- **Open-step lemma**: if the resolvent at `lam` exists and is positive, then the
same holds on a whole interval `(lam - δ, lam]` (excluding levels ≤ 0), where
`δ = ‖(lam-T)⁻¹‖⁻¹`.  This is the elementary core: rescale the positive resolvent
by `1 - (lam-μ)•(lam-T)⁻¹`, a small perturbation whose inverse is a positive
geometric series. -/
theorem resolvent_positivity_open_step {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    {lam : ℝ} (hlamres : lam ∈ resolventSet ℝ T)
    (hlampos : IsPositive (Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T))) :
    ∃ δ > 0, ∀ μ : ℝ, lam - δ < μ → μ ≤ lam →
      μ ∈ resolventSet ℝ T ∧
        IsPositive (Ring.inverse ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  have hu : IsUnit ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) := by
    show IsUnit (algebraMap ℝ (C(X, ℝ) →L[ℝ] C(X, ℝ)) lam - T)
    exact hlamres
  set A := Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) with hAdef
  have hAA1 : A * ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) = 1 :=
    Ring.inverse_mul_cancel _ hu
  have hA1 : ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) * A = 1 := by
    rw [hAdef, Ring.inverse_of_isUnit hu]
    simpa using Units.inv_mul_cancel hu.unit
  have hAnorm : 0 < ‖A‖ := by
    by_contra h0
    have hA0 : ‖A‖ = 0 := le_antisymm (le_of_not_gt h0) (norm_nonneg A)
    have hAf0 : ∀ f : C(X, ℝ), A f = 0 := by
      intro f
      have hle : ‖A f‖ ≤ 0 := by
        calc ‖A f‖ ≤ ‖A‖ * ‖f‖ := ContinuousLinearMap.le_opNorm A f
          _ = 0 := by rw [hA0, zero_mul]
      exact norm_eq_zero.mp (le_antisymm hle (norm_nonneg _))
    have hAzero : A = 0 := ContinuousLinearMap.ext hAf0
    rw [hAzero, zero_mul] at hAA1
    exact zero_ne_one hAA1
  refine ⟨‖A‖⁻¹, inv_pos.mpr hAnorm, ?_⟩
  intro μ hμlt hμle
  set s := lam - μ with hsdef
  have hs : 0 ≤ s := by linarith
  have hsmul : ‖(s : ℝ) • A‖ < 1 := by
    rw [hAdef]
    refine lt_of_le_of_lt (ContinuousLinearMap.opNorm_smul_le _ _) ?_
    rw [Real.norm_eq_abs, abs_of_nonneg hs]
    calc s * ‖A‖ < ‖A‖⁻¹ * ‖A‖ := mul_lt_mul_of_pos_right (by linarith : s < ‖A‖⁻¹) hAnorm
      _ = 1 := inv_mul_cancel₀ (ne_of_gt hAnorm)
  set B := Ring.inverse ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - s • A) with hBdef
  have hgeo : HasSum (fun i : ℕ => (s • A) ^ i) B :=
    hasSum_geom_series_inverse (s • A) hsmul
  have hBunit : IsUnit ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - s • A) :=
    ⟨⟨_, _, mul_neg_geom_series (s • A) hsmul, geom_series_mul_neg (s • A) hsmul⟩, rfl⟩
  -- the product factorization `μ•1 - T = (lam•1-T) * (1 - s•A)`
  have hprod : ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)
        * ((1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - s • A)
      = (μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T := by
    have hscal : ((lam - s : ℝ)) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))
        = (lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - (s : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) :=
      sub_smul lam s (1 : C(X, ℝ) →L[ℝ] C(X, ℝ))
    rw [mul_sub, mul_one, resolvent_mul_smul_assoc, hA1, sub_right_comm,
      ← hscal, hsdef, sub_sub_cancel]
  have hμunit : IsUnit ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) := by
    have huv : ((hu.unit * hBunit.unit : Units
        (C(X, ℝ) →L[ℝ] C(X, ℝ)))) = ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) := by
      rw [Units.val_mul]
      exact hprod
    exact huv ▸ (hu.unit * hBunit.unit).isUnit
  have hinvprod : Ring.inverse ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)
      = B * A := by
    rw [← hprod, Ring.inverse_mul (Or.inr hBunit), hBdef, hAdef]
  refine ⟨by simpa only [resolventSet, Set.mem_ofPred_eq,
    Algebra.algebraMap_eq_smul_one] using hμunit, ?_⟩
  rw [hinvprod]
  intro g hg
  have hconeAg : A g ∈ positiveCone := hlampos hg
  have htermφ : ∀ i : ℕ, ((s • A) ^ i) (A g) ∈ positiveCone := by
    intro i
    rw [smul_pow' s A i, mem_positiveCone]
    intro x
    have hxcone : 0 ≤ (A ^ i) (A g) x := (hlampos.pow' i).apply_nonneg hconeAg x
    have hpt : ((s ^ i : ℝ) • (A ^ i)) (A g) x = (s ^ i : ℝ) * (A ^ i) (A g) x := rfl
    rw [hpt]
    exact mul_nonneg (pow_nonneg hs i) hxcone
  rw [mem_positiveCone]
  intro x
  rw [ContinuousLinearMap.mul_apply]
  have hpart : Filter.Tendsto
      (fun n : ℕ => ∑ i ∈ Finset.range n, ((s • A) ^ i) (A g))
      Filter.atTop (𝓝 (B (A g))) := by
    have hms : ∀ n : ℕ, (ContinuousLinearMap.apply ℝ (C(X, ℝ)) (A g))
        (∑ i ∈ Finset.range n, (s • A) ^ i)
        = ∑ i ∈ Finset.range n, ((s • A) ^ i) (A g) := fun n => by
      rw [map_sum]
      exact Finset.sum_congr rfl (fun i _ => rfl)
    rw [← funext hms]
    exact ((ContinuousLinearMap.apply ℝ (C(X, ℝ)) (A g)).continuous.tendsto B).comp
      hgeo.tendsto_sum_nat
  have hmem : B (A g) ∈ positiveCone := by
    refine isClosed_positiveCone.mem_of_tendsto hpart ?_
    refine Filter.eventually_atTop.mpr ⟨0, fun n _ => ?_⟩
    exact positiveCone_sum_range n (fun i _ => htermφ i)
  exact hmem x

/-- **Closure lemma**: a norm-limit of positive resolvents at converging
resolvent levels keeps positivity. -/
theorem resolvent_positivity_closed {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    {ν : ℕ → ℝ} {lam : ℝ} (hν : Filter.Tendsto ν Filter.atTop (𝓝 lam))
    (hpos : ∀ n, ν n ∈ resolventSet ℝ T ∧
      IsPositive (Ring.inverse (((ν n) : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)))
    (hlamres : lam ∈ resolventSet ℝ T) :
    IsPositive (Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  have hu : IsUnit ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T) := by
    show IsUnit (algebraMap ℝ (C(X, ℝ) →L[ℝ] C(X, ℝ)) lam - T)
    exact hlamres
  have hcomp : Continuous fun z : ℝ => (z : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T := by
    continuity
  have h1 : Filter.Tendsto (fun n => ((ν n : ℝ)) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)
      Filter.atTop (𝓝 ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) :=
    (hcomp.tendsto lam).comp hν
  have h2 : Filter.Tendsto
      (fun n => Ring.inverse (((ν n : ℝ)) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T))
      Filter.atTop
      (𝓝 (Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T))) :=
    (Filter.Tendsto.comp (ringInverse_continuousAt' hu.unit).tendsto h1)
  intro g hg
  let ψ : (C(X, ℝ) →L[ℝ] C(X, ℝ)) →L[ℝ] C(X, ℝ) :=
    ContinuousLinearMap.apply ℝ (C(X, ℝ)) g
  have hconv : Filter.Tendsto
      (fun n => (Ring.inverse (((ν n : ℝ)) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) g)
      Filter.atTop (𝓝 ((Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) g)) :=
    (ψ.continuous.tendsto
      (Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T))).comp h2
  exact (isClosed_positiveCone (X := X)).mem_of_tendsto hconv
    (Filter.Eventually.of_forall fun n => (hpos n).2 hg)

/-- **sInf walk**: for positive `T`, every real level above the spectral radius
lies in the resolvent set, with positive resolvent. This removes the
`hg` hypothesis from `resolvent_positivity_at_radius` in the regime
`spectralRadius < lam`. -/
theorem resolvent_positivity_of_gt_spectralRadius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) {lam : ℝ}
    (hlam : (spectralRadius ℝ T).toReal < lam) :
    lam ∈ resolventSet ℝ T ∧
      IsPositive (Ring.inverse ((lam : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  set r := (spectralRadius ℝ T).toReal with hrdef
  have hlam₀norm : ‖T‖ < max lam (max ‖T‖ (r + 1) + 1) := by
    refine lt_of_lt_of_le ?_ (le_max_right lam (max ‖T‖ (r + 1) + 1))
    calc ‖T‖ ≤ max ‖T‖ (r + 1) := le_max_left _ _
      _ < max ‖T‖ (r + 1) + 1 := by linarith
  set lam₀ := max lam (max ‖T‖ (r + 1) + 1) with hlam₀def
  set W : Set ℝ := {ν : ℝ | r ≤ ν ∧ ν ≤ lam₀ ∧ ∀ μ : ℝ, ν ≤ μ → μ ≤ lam₀ →
    μ ∈ resolventSet ℝ T ∧
      IsPositive (Ring.inverse ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T))} with hWdef
  have hlamle : lam ≤ lam₀ := le_max_left _ _
  have hW0 : lam₀ ∈ W := by
    have hlm₀ : max ‖T‖ (r + 1) + 1 ≤ lam₀ := by
      rw [hlam₀def]; exact le_max_right lam (max ‖T‖ (r + 1) + 1)
    refine ⟨le_trans (le_add_of_nonneg_right zero_le_one : r ≤ r + 1)
      (le_trans (le_max_right ‖T‖ (r + 1))
        (le_trans (le_add_of_nonneg_right zero_le_one) hlm₀)), le_refl _,
      fun μ hμ₁ hμ₂ => ?_⟩
    have hμ0 : μ = lam₀ := le_antisymm hμ₂ hμ₁
    subst hμ0
    exact resolvent_positivity_above_norm hTpos hlam₀norm
  have hbdd : BddBelow W := ⟨r, fun _ hν => hν.1⟩
  set θ := sInf W with hθdef
  have hθle : θ ≤ lam₀ := csInf_le hbdd hW0
  have hθr : r ≤ θ := le_csInf ⟨lam₀, hW0⟩ fun ν hν => hν.1
  -- the levels of `W` accumulate at `θ`
  obtain ⟨ν, hνW⟩ : ∃ ν : ℕ → ℝ, ∀ k, ν k ∈ W ∧ ν k < θ + 1 / ((k : ℝ) + 1) := by
    have hgen : ∀ k : ℕ, ∃ a ∈ W, a < θ + 1 / (((k : ℕ) : ℝ) + 1) := fun k =>
      (csInf_lt_iff hbdd ⟨lam₀, hW0⟩).mp
        (by rw [hθdef]; exact lt_add_of_le_of_pos (le_refl _) (by positivity))
    refine ⟨fun k => Classical.choose (hgen k), fun k => Classical.choose_spec (hgen k)⟩
  have hwk : ∀ k, θ ≤ ν k ∧ ν k < θ + 1 / ((k : ℝ) + 1) := fun k =>
    ⟨csInf_le hbdd ((hνW k).1), (hνW k).2⟩
  have hνtend : Filter.Tendsto ν Filter.atTop (𝓝 θ) := by
    rw [Metric.tendsto_atTop]
    intro ε hε
    obtain ⟨N, hN⟩ := exists_nat_gt ((1 : ℝ) / ε)
    rw [div_lt_iff₀ hε] at hN
    have h1 : (1 : ℝ) / ((N : ℕ) + 1) < ε := by
      rw [div_lt_iff₀ (by positivity : (0:ℝ) < ((N : ℕ) : ℝ) + 1)]
      have hring : ε * (((N : ℕ) : ℝ) + 1) = (N : ℝ) * ε + ε := by ring
      linarith [hring, hN]
    refine ⟨N, fun k hk => ?_⟩
    have hge : N ≤ k := hk
    have hθleν : θ ≤ ν k := (hwk k).1
    have hlt2 : ν k - θ < 1 / ((k : ℝ) + 1) := by linarith [hwk k]
    calc dist (ν k) θ = |ν k - θ| := Real.dist_eq _ _
      _ = ν k - θ := abs_of_nonneg (by linarith)
      _ < 1 / ((k : ℝ) + 1) := hlt2
      _ ≤ 1 / ((N : ℝ) + 1) :=
        one_div_le_one_div_of_le (by positivity)
          (by exact_mod_cast (by omega : (N:ℕ) + 1 ≤ k + 1))
      _ < ε := h1
  -- the walk: `θ ≤ r` by contradiction; if `r < θ` then `θ` is a positive resolvent
  -- level, and the open step at `θ` reaches strictly below `θ` — contradicting minimality
  have hθle_r : θ ≤ r := by
    by_contra hcon
    have hlt : r < θ := lt_of_not_ge hcon
    have hθpos : 0 < θ := lt_of_le_of_lt ENNReal.toReal_nonneg hlt
    have htop : spectralRadius ℝ T ≠ ⊤ :=
      ne_of_lt (lt_of_le_of_lt (@spectrum.spectralRadius_le_nnnorm ℝ _ _ _ _ _ _ T)
        ENNReal.coe_lt_top)
    have hcoe : (spectralRadius ℝ T).toNNReal
        = Real.toNNReal (spectralRadius ℝ T).toReal := by
      ext; exact (ENNReal.coe_toNNReal_eq_toReal _).trans
        (Real.coe_toNNReal _ ENNReal.toReal_nonneg).symm
    have hθres : θ ∈ resolventSet ℝ T := by
      refine spectrum.mem_resolventSet_of_spectralRadius_lt (k := θ) ?_
      rw [← ENNReal.coe_toNNReal htop, ENNReal.coe_lt_coe, hcoe,
        ← Real.toNNReal_eq_nnnorm_of_nonneg hθpos.le]
      exact (Real.toNNReal_lt_toNNReal_iff (r := (spectralRadius ℝ T).toReal) hθpos).mpr
        (show (spectralRadius ℝ T).toReal < θ from by rw [← hrdef]; exact hlt)
    have hθP : IsPositive (Ring.inverse ((θ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) :=
      resolvent_positivity_closed hνtend (fun n =>
        ((hνW n).1).2.2 (ν n) (le_refl _) ((hνW n).1).2.1) hθres
    -- the open step at `θ` reaches strictly below `θ`
    obtain ⟨δ, hδ, hstep⟩ := resolvent_positivity_open_step hθres hθP
    set μ' := (max r (θ - δ) + θ) / 2 with hμ'def
    have h2 : (0:ℝ) < 2 := by norm_num
    have hSlt : max r (θ - δ) < θ := max_lt hlt (by linarith)
    have hμ'lt : μ' < θ := by
      rw [div_lt_iff₀ h2, mul_two]; linarith
    have hμ'gt : max r (θ - δ) < μ' := by
      rw [lt_div_iff₀ h2, mul_two]; linarith
    have hμ'r : r < μ' := lt_of_le_of_lt (le_max_left r (θ - δ)) hμ'gt
    have hθδlt : θ - δ < μ' := lt_of_le_of_lt (le_max_right r (θ - δ)) hμ'gt
    have hμ'W : μ' ∈ W := by
      refine ⟨le_of_lt hμ'r, le_of_lt (lt_of_lt_of_le hμ'lt hθle), ?_⟩
      intro a hale hale₀
      rcases le_or_gt a θ with ha | ha
      · exact hstep a (lt_of_lt_of_le hθδlt hale) ha
      · obtain ⟨b, hbW, hblt⟩ := (csInf_lt_iff hbdd ⟨lam₀, hW0⟩).mp
          (lt_of_le_of_lt hθdef.symm.le ha)
        exact hbW.2.2 a (le_of_lt hblt) hale₀
    exact absurd (lt_of_le_of_lt (csInf_le hbdd hμ'W) hμ'lt) (by linarith)
  -- `W`'s third component propagates `P` upward: since `sInf W = r`, every level
  -- above `r` sits above some `ν' ∈ W`, hence has positive resolvent
  have hθeqr : θ = r := le_antisymm hθle_r hθr
  have hmain : ∀ μ : ℝ, r < μ → μ ≤ lam₀ →
      μ ∈ resolventSet ℝ T ∧
        IsPositive (Ring.inverse ((μ : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
    intro μ hμr hμl₀
    obtain ⟨ν', hν'W, hν'lt⟩ :=
      (csInf_lt_iff (a := μ) hbdd ⟨lam₀, hW0⟩).mp
        (by rw [← hθdef, hθeqr]; exact hμr)
    exact hν'W.2.2 μ (le_of_lt hν'lt) hμl₀
  exact hmain lam hlam hlamle

end Riemann
