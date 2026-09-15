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
3. *Upper bound via the positivity telescope* — `‖Tⁿ‖ = ‖Tⁿ1‖`
   (`norm_eq_apply_one_of_isPositive`), and the telescope identity
   `μᵏ • w1 = (Tᵏ)(w1) + Σ_{i<k} μ^{k-1-i} • Tⁱ1` with `w = (μ - T)⁻¹ ≥ 0`
   pointwise-dominates `‖Tᵏ‖ ≤ μ^{k+1} ‖w1‖` for every `μ > ρ`
   (`pow_norm_le_of_posresolvent`).  Hence
   `limsup (‖Tⁿ‖₊^{1/n}) ≤ μ` for all `μ > ρ`
   (`limsup_pow_nnnorm_le`), so `limsup ≤ ρ`
   (`gelfand_limsup_le_of_isPositive`).
4. *Assembly* — `gelfand_formula_of_isPositive` combines this upper bound
   with `spectralRadius_le_liminf_pow` via
   `tendsto_of_le_liminf_of_limsup_le`.
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

/-- **Gelfand formula, lower half (unconditional)**: for any `T` on `C(X, ℝ)`
the spectral radius is bounded by the `liminf` of the normalized power norms.
This is mathlib's `spectrum.spectralRadius_le_liminf_pow_nnnorm_pow_one_div`
(valid over any complete normed algebra, in particular over `ℝ`); the
corresponding `limsup` half is *false* over `ℝ` in general (the rotation
`T(x, y) = (-y, x)` has empty real spectrum but `‖Tⁿ‖^(1/n) → 1`), so for a
full real Gelfand formula positivity must enter — see the roadmap note on
`resolvent_positivity_of_gt_spectralRadius`. -/
theorem spectralRadius_le_liminf_pow (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) :
    spectralRadius ℝ T ≤
      Filter.atTop.liminf fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ) :=
  spectrum.spectralRadius_le_liminf_pow_nnnorm_pow_one_div ℝ T

/-! ## Gelfand's formula over ℝ, the upper bound -/

/-- `(x / n) → 0` along `atTop` in `ℝ`. -/
theorem tendsto_div_cast_atTop (x : ℝ) :
    Tendsto (fun n : ℕ => x / (n : ℝ)) atTop (nhds 0) := by
  have hinv : Tendsto (fun n : ℕ => ((n : ℝ)⁻¹)) atTop (nhds 0) :=
    tendsto_inv_atTop_zero (𝕜 := ℝ) |>.comp tendsto_natCast_atTop_atTop
  have h : (fun n : ℕ => x / (n : ℝ)) = fun n : ℕ => x * ((n : ℝ)⁻¹) := by
    funext n; field_simp
  rw [h]
  simpa [mul_zero] using hinv.const_mul x

/-- `(c^(1/n)) → 1` for `c > 0`. -/
theorem tendsto_rpow_one_div_atTop (c : ℝ) (hc : 0 < c) :
    Tendsto (fun n : ℕ => c ^ (1 / (n : ℝ))) atTop (nhds 1) := by
  have hz : Tendsto (fun n : ℕ => Real.log c / (n : ℝ)) atTop (nhds 0) :=
    tendsto_div_cast_atTop _
  have hexp : Tendsto (fun n : ℕ => Real.exp (Real.log c / (n : ℝ))) atTop
      (nhds (Real.exp 0)) := Real.continuous_exp.continuousAt.tendsto.comp hz
  have hform : (fun n : ℕ => c ^ (1 / (n : ℝ))) =ᶠ[atTop]
      (fun n : ℕ => Real.exp (Real.log c / (n : ℝ))) := by
    filter_upwards [Filter.eventually_gt_atTop 0] with n hn
    rw [Real.rpow_def_of_pos hc]
    congr 1
    field_simp
  simpa using Tendsto.congr' hform.symm hexp

/-- A positive operator on `C(X, ℝ)` attains its operator norm at `1`:
`‖A‖ = ‖A 1‖`. -/
theorem norm_eq_apply_one_of_isPositive {A : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hA : IsPositive A) :
    ‖A‖ = ‖A (1 : C(X, ℝ))‖ := by
  have h1 : ‖A (1 : C(X, ℝ))‖ ≤ ‖A‖ := by
    calc ‖A (1 : C(X, ℝ))‖ ≤ ‖A‖ * ‖(1 : C(X, ℝ))‖ :=
        ContinuousLinearMap.le_opNorm A _
      _ = ‖A‖ := by simp
  -- Pointwise domination: `|A f| ≤ A 1` for `‖f‖ ≤ 1`.
  have hbound : ∀ f : C(X, ℝ), ‖f‖ ≤ 1 → ‖A f‖ ≤ ‖A (1 : C(X, ℝ))‖ := by
    intro f hf
    have hfp : f ≤ 1 := by
      rw [ContinuousMap.le_def]
      intro x
      have hx := ((ContinuousMap.norm_le (f := f) (C := (1 : ℝ)) (C0 := zero_le_one)).mp hf) x
      rw [Real.norm_eq_abs, abs_le] at hx
      simp only [ContinuousMap.one_apply]
      linarith
    have hfn : -1 ≤ f := by
      rw [ContinuousMap.le_def]
      intro x
      have hx := ((ContinuousMap.norm_le (f := f) (C := (1 : ℝ)) (C0 := zero_le_one)).mp hf) x
      rw [Real.norm_eq_abs, abs_le] at hx
      show (-1 : ℝ) ≤ f x
      linarith
    have hAle : A f ≤ A 1 := hA.monotone hfp
    have hAge : A (-1) ≤ A f := hA.monotone hfn
    have habs : ∀ x : X, |A f x| ≤ A (1 : C(X, ℝ)) x :=
      fun x => abs_le.mpr ⟨by simpa using hAge x, hAle x⟩
    exact (ContinuousMap.norm_le (f := A f) (C := ‖A (1 : C(X, ℝ))‖)
      (C0 := norm_nonneg (A (1 : C(X, ℝ))))).mpr fun x => by
      rw [Real.norm_eq_abs]
      exact le_trans (habs x) (le_trans (le_abs_self (A (1 : C(X, ℝ)) x))
        ((A (1 : C(X, ℝ))).norm_coe_le_norm x))
  -- Rescale to unit norm and back.
  have hscale : ∀ f : C(X, ℝ), ‖A f‖ ≤ ‖A (1 : C(X, ℝ))‖ * ‖f‖ := by
    intro f
    by_cases hf0 : ‖f‖ = 0
    · have hfz : f = 0 := norm_eq_zero.mp hf0
      simp [hfz]
    · have hunit : ‖(‖f‖⁻¹ • f : C(X, ℝ))‖ ≤ 1 := by
        rw [norm_smul, Real.norm_eq_abs, abs_of_nonneg (by positivity : 0 ≤ ‖f‖⁻¹),
          inv_mul_cancel₀ hf0]
      have hposf : 0 < ‖f‖ := lt_of_le_of_ne (norm_nonneg f) (Ne.symm hf0)
      have hdom := hbound (‖f‖⁻¹ • f) hunit
      rw [map_smul, norm_smul, Real.norm_eq_abs,
        abs_of_nonneg (by positivity : 0 ≤ ‖f‖⁻¹)] at hdom
      have hstep := mul_le_mul_of_nonneg_left hdom (le_of_lt hposf)
      rw [← mul_assoc, mul_inv_cancel₀ (ne_of_gt hposf), one_mul,
        mul_comm ‖f‖ ‖A (1 : C(X, ℝ))‖] at hstep
      exact hstep
  exact le_antisymm
    (ContinuousLinearMap.opNorm_le_bound A (norm_nonneg (A (1 : C(X, ℝ)))) hscale) h1

/-- Powers commute with scalar multiplication: `Tⁿ (c • f) = c • Tⁿ f`. -/
theorem pow_map_smul {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (c : ℝ) (f : C(X, ℝ)) (k : ℕ) :
    (T ^ k) (c • f) = c • (T ^ k) f := by
  induction k generalizing f with
  | zero => simp
  | succ k ih =>
    rw [pow_succ, ContinuousLinearMap.mul_apply, map_smul, ih (T f),
      ← ContinuousLinearMap.mul_apply, ← pow_succ]

/-- The resolvent telescope: if `w` is a right inverse of `μ • 1 - T` with
`μ > 0`, then `μ^k • w 1` splits into the `k`-th orbit term plus the scaled
partial sums of the constant-one orbit. -/
theorem resolvent_telescope {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {μ : ℝ} (hμ : 0 < μ)
    (w : C(X, ℝ) →L[ℝ] C(X, ℝ)) (hw : (μ • 1 - T) * w = 1) (k : ℕ) :
    (μ ^ k) • w (1 : C(X, ℝ))
        = (T ^ k) (w (1 : C(X, ℝ)))
          + ∑ i ∈ Finset.range k, (μ ^ (k - 1 - i)) • (T ^ i) (1 : C(X, ℝ)) := by
  have hbasic : μ • w (1 : C(X, ℝ)) = T (w (1 : C(X, ℝ))) + 1 := by
    have h1 : ((μ • 1 - T) * w) (1 : C(X, ℝ)) = (1 : C(X, ℝ)) := by rw [hw]; rfl
    have h2 := eq_add_of_sub_eq h1
    rw [add_comm] at h2
    exact h2
  induction k with
  | zero => simp
  | succ k ih =>
    have hscale : ∀ i : ℕ, i ∈ Finset.range k →
        μ • (μ ^ (k - 1 - i)) • (T ^ i) (1 : C(X, ℝ))
          = (μ ^ (k - i)) • (T ^ i) (1 : C(X, ℝ)) := by
      intro i hi
      have hlt : i < k := Finset.mem_range.mp hi
      have hexp : k - i = (k - 1 - i) + 1 := by omega
      rw [hexp, smul_smul, ← pow_succ']
    have hTk : (T ^ k) (T (w (1 : C(X, ℝ)))) = (T ^ (k + 1)) (w (1 : C(X, ℝ))) := by
      rw [pow_succ, ContinuousLinearMap.mul_apply]
    rw [Nat.add_sub_cancel, pow_succ, ← smul_smul, smul_comm, ih, smul_add,
      Finset.smul_sum,
      Finset.sum_congr rfl (fun i hi => hscale i hi),
      ← pow_map_smul μ (w (1 : C(X, ℝ))) k, hbasic, map_add, hTk,
      Finset.sum_range_succ, Nat.sub_self, pow_zero, one_smul]
    abel

/-- Partial-sum domination: if `w` is a positive right inverse of `μ • 1 - T`
(`μ > 0`), then the scaled partial orbit sums of `1` are pointwise dominated by
`μ^k • w 1`. -/
theorem partial_sum_le_of_posresolvent {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) {μ : ℝ} (hμ : 0 < μ) {w : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hw : (μ • 1 - T) * w = 1) (hwpos : IsPositive w) (k : ℕ) :
    ∑ i ∈ Finset.range k, (μ ^ (k - 1 - i)) • (T ^ i) (1 : C(X, ℝ))
      ≤ (μ ^ k) • w (1 : C(X, ℝ)) := by
  have hident := resolvent_telescope hμ w hw k
  have hw1c : w (1 : C(X, ℝ)) ∈ positiveCone := hwpos (fun _ => by exact zero_le_one)
  have hTk1c : (T ^ k) (w (1 : C(X, ℝ))) ∈ positiveCone := (hTpos.pow' k) hw1c
  have hTk1pt : ∀ x : X, 0 ≤ ((T ^ k) (w (1 : C(X, ℝ)))) x := hTk1c
  have hpt : ∀ x : X, (∑ i ∈ Finset.range k, (μ ^ (k - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x
      ≤ ((μ ^ k) • w (1 : C(X, ℝ))) x := by
    intro x
    have hpt := DFunLike.congr_fun hident x
    simp only [smul_eq_mul, ContinuousMap.add_apply, ContinuousMap.smul_apply,
      Finset.sum_apply] at hpt
    simp only [smul_eq_mul, ContinuousMap.smul_apply, Finset.sum_apply]
    linarith [hTk1pt x]
  exact hpt

/-- The Gelfand-type norm bound for positive operators: if `μ > 0` admits a
positive right inverse `w` of `μ • 1 - T`, then `‖Tⁿ‖ ≤ μ^(n+1) * ‖w 1‖` for
every `n`. -/
theorem pow_norm_le_of_posresolvent {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) {μ : ℝ} (hμ : 0 < μ) {w : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hw : (μ • 1 - T) * w = 1) (hwpos : IsPositive w) (n : ℕ) :
    ‖T ^ n‖ ≤ μ ^ (n + 1) * ‖w (1 : C(X, ℝ))‖ := by
  have hsum := partial_sum_le_of_posresolvent hTpos hμ hw hwpos (n + 1)
  have hsingle : (μ ^ (n + 1 - 1 - n)) • (T ^ n) (1 : C(X, ℝ))
      ≤ ∑ i ∈ Finset.range (n + 1), (μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ)) := by
    intro x
    show ((μ ^ (n + 1 - 1 - n)) • (T ^ n) (1 : C(X, ℝ))) x
      ≤ (∑ i ∈ Finset.range (n + 1), (μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x
    have hge : ∀ i ∈ Finset.range (n + 1),
        0 ≤ ((μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x := fun i _ =>
      smul_nonneg (pow_nonneg hμ.le _)
        (((hTpos.pow' i) (fun _ => by exact zero_le_one)) x)
    have hflat : (∑ i ∈ Finset.range (n + 1),
          (μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x
        = ∑ i ∈ Finset.range (n + 1), ((μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x :=
      map_sum (resolvent_eval x) _ _
    rw [hflat]
    calc ((μ ^ (n + 1 - 1 - n)) • (T ^ n) (1 : C(X, ℝ))) x
        ≤ ((μ ^ (n + 1 - 1 - n)) • (T ^ n) (1 : C(X, ℝ))) x := le_refl _
      _ ≤ ∑ i ∈ Finset.range (n + 1), ((μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x :=
        Finset.single_le_sum (f := fun i => ((μ ^ (n + 1 - 1 - i)) • (T ^ i) (1 : C(X, ℝ))) x)
          hge (Finset.mem_range.mpr (Nat.lt_succ_self n))
  have hexp : n + 1 - 1 - n = 0 := by omega
  rw [hexp, pow_zero, one_smul] at hsingle
  have hw1c : w (1 : C(X, ℝ)) ∈ positiveCone := hwpos (fun _ => by exact zero_le_one)
  have hcone : (T ^ n) (1 : C(X, ℝ)) ∈ positiveCone :=
    (hTpos.pow' n) (fun _ => by exact zero_le_one)
  calc ‖T ^ n‖ = ‖(T ^ n) (1 : C(X, ℝ))‖ :=
      norm_eq_apply_one_of_isPositive (hTpos.pow' n)
    _ ≤ ‖(μ ^ (n + 1)) • w (1 : C(X, ℝ))‖ := norm_mono_of_cone hcone (hsingle.trans hsum)
    _ = μ ^ (n + 1) * ‖w (1 : C(X, ℝ))‖ := by
      rw [norm_smul, Real.norm_eq_abs, abs_of_nonneg (pow_nonneg hμ.le _)]

/-- The per-`μ` limsup bound: if `μ > 0` exceeds the real spectral radius, then
positivity of `T` forces `limsup ‖Tⁿ‖₊^(1/n) ≤ μ`. -/
theorem limsup_pow_nnnorm_le {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    {μ : ℝ} (hμ : 0 < μ) (hμr : (spectralRadius ℝ T).toReal < μ) :
    Filter.limsup (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ)) Filter.atTop
      ≤ ENNReal.ofReal μ := by
  obtain ⟨hmem, hwpos⟩ := resolvent_positivity_of_gt_spectralRadius hTpos hμr
  have hunit : IsUnit (μ • 1 - T) := hmem
  have hw : (μ • 1 - T) * Ring.inverse (μ • 1 - T) = 1 := Ring.mul_inverse_cancel _ hunit
  have hbnd : ∀ n : ℕ,
      ‖T ^ n‖ ≤ μ ^ (n + 1) * ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖ :=
    pow_norm_le_of_posresolvent hTpos hμ hw hwpos
  by_cases hC : ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖ = 0
  · exfalso
    have h0 := hbnd 0
    rw [hC, mul_zero] at h0
    have h1z : ‖T ^ 0‖ = 0 := le_antisymm h0 (norm_nonneg (T ^ 0))
    have hT0 : T ^ 0 = 0 := (norm_eq_zero (a := T ^ 0)).mp h1z
    rw [pow_zero] at hT0
    exact one_ne_zero hT0
  · have hCpos : 0 < ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖ :=
      lt_of_le_of_ne (norm_nonneg _) (Ne.symm hC)
    have hμt : Tendsto (fun n : ℕ => μ ^ ((n + 1 : ℝ) / n)) Filter.atTop (𝓝 μ) := by
      have hbase := (tendsto_rpow_one_div_atTop μ hμ).const_mul μ
      rw [mul_one] at hbase
      have hexp : (fun n : ℕ => μ ^ ((n + 1 : ℝ) / n))
          =ᶠ[Filter.atTop] fun n : ℕ => μ * μ ^ (1 / n : ℝ) := by
        filter_upwards [Filter.eventually_ne_atTop 0] with n hn
        have hrw : (n + 1 : ℝ) / n = 1 + (1 / (n : ℝ)) := by field_simp
        rw [hrw, Real.rpow_add hμ, Real.rpow_one]
      exact Filter.Tendsto.congr' hexp.symm hbase
    have hCt : Tendsto (fun n : ℕ =>
        (‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖ ^ (1 / n : ℝ))) Filter.atTop (𝓝 1) :=
      tendsto_rpow_one_div_atTop _ hCpos
    have hg : Tendsto
        (fun n : ℕ => ((μ ^ ((n + 1 : ℕ) : ℝ) * ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖)
          ^ (1 / (n : ℝ)))) Filter.atTop (𝓝 μ) := by
      have hsplit : ∀ n : ℕ,
          ((μ ^ ((n + 1 : ℕ) : ℝ) * ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖)
            ^ (1 / (n : ℝ)))
            = μ ^ ((n + 1 : ℝ) / n)
              * (‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖ ^ (1 / (n : ℝ))) := by
        intro n
        rw [Real.mul_rpow (Real.rpow_nonneg hμ.le ((n + 1 : ℕ) : ℝ)) (norm_nonneg _)]
        congr 1
        rw [← Real.rpow_mul (le_of_lt hμ) ((n + 1 : ℕ) : ℝ) (1 / (n : ℝ))]
        congr 1
        cases n with
        | zero => norm_num
        | succ m => push_cast; field_simp
      have h2 := hμt.mul hCt
      rw [mul_one] at h2
      exact Tendsto.congr' (Eventually.of_forall fun n => (hsplit n).symm) h2
    have hpw : ∀ n : ℕ, (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))
        ≤ ENNReal.ofReal ((μ ^ ((n + 1 : ℕ) : ℝ)
          * ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖) ^ (1 / (n : ℝ))) := by
      intro n
      have hcast : ((‖T ^ n‖₊ : ℝ≥0) : ℝ≥0∞) = ENNReal.ofReal ‖T ^ n‖ :=
        ENNReal.coe_nnreal_eq _
      have hfirst := hbnd n
      rw [← Real.rpow_natCast] at hfirst
      rw [hcast, ENNReal.ofReal_rpow_of_nonneg (norm_nonneg (T ^ n)) (by positivity)]
      exact ENNReal.ofReal_le_ofReal
        (Real.rpow_le_rpow (norm_nonneg (T ^ n)) hfirst (by positivity))
    have hvo : Tendsto (fun n : ℕ => ENNReal.ofReal
        (((μ ^ ((n + 1 : ℕ) : ℝ) * ‖(Ring.inverse (μ • 1 - T)) (1 : C(X, ℝ))‖)
          ^ (1 / (n : ℝ))))) Filter.atTop (𝓝 (ENNReal.ofReal μ)) :=
      ((ENNReal.continuous_ofReal).tendsto μ).comp hg
    refine le_trans (limsup_le_limsup (Filter.Eventually.of_forall hpw)) ?_
    rw [Filter.Tendsto.limsup_eq hvo]

/-- Gelfand's formula, upper bound over `ℝ` for positive operators: the `limsup`
half of the real Gelfand formula. -/
theorem gelfand_limsup_le_of_isPositive {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T) :
    Filter.limsup (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ)) Filter.atTop
      ≤ spectralRadius ℝ T := by
  by_cases hr_top : spectralRadius ℝ T = ⊤
  · rw [hr_top]; exact le_top
  · by_contra hcon
    rw [← ENNReal.ofReal_toReal hr_top] at hcon
    obtain ⟨y, hyc, hyl⟩ := exists_between (not_le.mp hcon)
    have hyfin : y ≠ ⊤ := fun h1 => absurd (h1 ▸ hyl) (not_lt.2 le_top)
    have hyr : (spectralRadius ℝ T).toReal < y.toReal :=
      (ENNReal.toReal_lt_toReal hr_top hyfin).mpr (by
        rw [← ENNReal.ofReal_toReal hr_top]
        exact hyc)
    have hbound := limsup_pow_nnnorm_le hTpos
      (lt_of_le_of_lt (b := (spectralRadius ℝ T).toReal) (c := y.toReal)
        ENNReal.toReal_nonneg hyr) hyr
    exact absurd (le_trans hbound (ENNReal.ofReal_toReal hyfin).le)
      (not_le.mpr hyl)

/-- **Gelfand's formula over `ℝ` for positive operators.** -/
theorem gelfand_formula_of_isPositive {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T) :
    Tendsto (fun n : ℕ => ((‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ))) Filter.atTop
      (𝓝 (spectralRadius ℝ T)) :=
  tendsto_of_le_liminf_of_limsup_le (spectralRadius_le_liminf_pow T)
    (gelfand_limsup_le_of_isPositive hTpos)

end Riemann