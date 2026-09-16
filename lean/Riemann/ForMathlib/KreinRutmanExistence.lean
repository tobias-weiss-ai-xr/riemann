/-
Staging copy for mathlib contribution — part of `lean/ForMathlib/` (see README.md).

This module is SELF-CONTAINED: it imports only mathlib and other ForMathlib
modules — no `Riemann.*` project code.  The `namespace Riemann` wrapper is a
placeholder retained from the project source; a mathlib PR will dissolve it
into the appropriate upstream namespaces.
-/

/-
Copyright (c) 2026 Tobias Weiss
Krein–Rutman dichotomy: superharmonic seeds forced onto exact eigenvectors.

This module closes the Krein–Rutman existence argument without touching
`Riemann.KreinRutman.kreinRutman_core` (which remains the single documented
admission of that file).  The route is the *resolvent blow-up*:

* the resolvents `(lam k • 1 - T)⁻¹` exist for every `lam k = rho + 1/(k+1)`
  (`GelfandPositive.resolvent_positivity_of_gt_spectralRadius`) and are positive;
* the seed domination `rho • w ≤ T w` propagates through the resolvent:
  `w ≤ (lam k - rho) • (lam k • 1 - T)⁻¹ w`, so the normalized resolvent orbit
  `z k = (lam k • 1 - T)⁻¹ w / ‖...‖` lives in the positive cone and navigates
  as `T (z k) = lam k • z k - c k • w` with residual `c k • w → 0`;
* compactness of `T` extracts a subsequence of `T (z k)` whose limit is a
  unit cone eigenvector at `rho` — no beta-stabilization machinery needed.

The domination seed `|v|` obtained from
`Riemann.KreinRutman.exists_eigenvector_with_domination` satisfies
`rho • |v| ≤ T |v|` on the cone, so `kreinRutman_core'` follows with *no
admission in this file*.
-/

import Riemann.ForMathlib.KreinRutman
import Riemann.ForMathlib.GelfandPositive

open scoped ContinuousMap NNReal Topology
open Filter
open Set

namespace Riemann

noncomputable section

set_option maxHeartbeats 5000000

/-- A pointwise-nonnegative function majorised by `g` has norm at most `‖g‖`. -/
theorem norm_le_of_nonneg_le {X : Type*} [TopologicalSpace X] [CompactSpace X] {f g : C(X, ℝ)}
    (hf : 0 ≤ f) (hfg : f ≤ g) : ‖f‖ ≤ ‖g‖ := by
  exact (f.norm_le (norm_nonneg (a := g))).mpr (fun x => by
    calc
      |f x| = f x := by exact abs_of_nonneg (hf x)
      _ ≤ g x := hfg x
      _ ≤ ‖g‖ := ContinuousMap.apply_le_norm g x)

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [Nonempty X]

/-- **Superharmonic seeds force exact positive eigenvectors (resolvent blow-up).**

If a nonzero cone vector `w` satisfies the domination inequality
`rho • w ≤ T w` (equivalently `T w ≥ rho • w`) for
`rho = (spectralRadius ℝ T).toReal`, then `T` has a nonzero eigenvector `f`
in the positive cone at eigenvalue `rho`.

*Proof sketch.*  For `lam k = rho + 1/(k+1)` the resolvents
`A k = (lam k • 1 - T)⁻¹` exist and are positive
(`resolvent_positivity_of_gt_spectralRadius`).  The domination transfers
through the resolvent: `w ≤ (lam k - rho) • A k w`, hence
`‖w‖ ≤ (lam k - rho) · ‖A k w‖`, so the normalized orbit
`z k = A k w / ‖A k w‖` satisfies `‖z k‖ = 1`, stays in the cone, and
navigates as `T (z k) = lam k • z k - c k • w` with residual
`c k = ‖A k w‖⁻¹ → 0`.  Compactness of `T` gives a subsequence with
`T (z (φ k)) → v`, and the navigation identity forces `z (φ k) → rho⁻¹ • v`,
a unit cone eigenvector at `rho`.

The hypothesis `rho = spectralRadius ℝ T` is *necessary*: take
`T(x, y) = (x + y, y)` (positive, compact) with seed `w = (0, 1)`
and `rho = 1/2`; the domination `rho • w ≤ T w` holds, yet `T`'s only
eigenvalue is `1`, so no cone eigenvector at `1/2` exists. -/
theorem exists_positive_eigenvector_of_superharmonic {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T) {rho : ℝ} (hrho : 0 < rho)
    (hr : rho = (spectralRadius ℝ T).toReal)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : rho • w ≤ T w) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧ T f = rho • f := by
  -- the resolvent levels lam k = rho + 1/(k+1) decrease to rho
  let lam : ℕ → ℝ := fun k => rho + 1 / ((k : ℝ) + 1)
  have hlamdef : ∀ k : ℕ, lam k = rho + 1 / ((k : ℝ) + 1) := fun k => rfl
  have hlampos : ∀ k : ℕ, 0 < lam k - rho := by
    intro k; rw [hlamdef k]
    linarith [(by positivity : (0:ℝ) < 1 / (((k:ℕ):ℝ) + 1))]
  have hone : Filter.Tendsto (fun k : ℕ => (1:ℝ) / (((k:ℕ):ℝ) + 1)) Filter.atTop (𝓝 0) := by
    rw [Metric.tendsto_atTop]
    intro ε hε
    obtain ⟨N, hN⟩ := exists_nat_gt ((1:ℝ)/ε)
    refine ⟨N, fun k hk => ?_⟩
    have hkle : ((k:ℕ):ℝ) + 1 ≥ ((N:ℕ):ℝ) + 1 := by exact_mod_cast (Nat.succ_le_succ hk)
    have hNpos : (0:ℝ) < ((N:ℕ):ℝ) + 1 := by positivity
    have hgt : (1:ℝ) / ε < ((N:ℕ):ℝ) + 1 := by linarith
    have h1 : (1:ℝ) / (((N:ℕ):ℝ) + 1) < ε := by
      rw [div_lt_iff₀ hNpos]
      have hmul := mul_lt_mul_of_pos_right hgt hε
      rw [div_mul_cancel₀ (1:ℝ) (ne_of_gt hε), mul_comm] at hmul
      exact hmul
    rw [Real.dist_eq, sub_zero, abs_of_nonneg (by positivity : (0:ℝ) ≤ 1 / (((k:ℕ):ℝ) + 1))]
    calc (1:ℝ) / (((k:ℕ):ℝ) + 1) ≤ (1:ℝ) / (((N:ℕ):ℝ) + 1) :=
        one_div_le_one_div_of_le (by positivity) hkle
      _ < ε := h1
  have hspec : ∀ k : ℕ, (spectralRadius ℝ T).toReal < lam k := by
    intro k; rw [hlamdef k, hr]
    linarith [(by positivity : (0:ℝ) < 1 / (((k:ℕ):ℝ) + 1))]
  -- resolvents exist and are positive
  have hres : ∀ k : ℕ, (lam k : ℝ) ∈ resolventSet ℝ T ∧
      IsPositive (Ring.inverse ((lam k : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) :=
    fun k => resolvent_positivity_of_gt_spectralRadius hTpos (hspec k)
  set M : ℕ → (C(X, ℝ) →L[ℝ] C(X, ℝ)) :=
    fun k => (lam k : ℝ) • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T with hMdef
  set A : ℕ → (C(X, ℝ) →L[ℝ] C(X, ℝ)) := fun k => Ring.inverse (M k) with hAdef
  have hApos : ∀ k : ℕ, IsPositive (A k) := fun k => (hres k).2
  have hu : ∀ k : ℕ, IsUnit (M k) := by
    intro k
    show IsUnit (algebraMap ℝ (C(X, ℝ) →L[ℝ] C(X, ℝ)) (lam k) - T)
    exact (hres k).1
  have hAMA : ∀ k : ℕ, M k * A k = 1 := fun k => Ring.mul_inverse_cancel _ (hu k)
  have hAM : ∀ k : ℕ, A k * M k = 1 := fun k => Ring.inverse_mul_cancel _ (hu k)
  -- navigation: T (A k g) = lam k • A k g - g
  have hnav : ∀ (k : ℕ) (g : C(X, ℝ)), T (A k g) = lam k • A k g - g := by
    intro k g
    have h1 : (M k * A k) g = (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) g := by
      rw [hAMA k, ContinuousLinearMap.one_apply]
    simp only [ContinuousLinearMap.mul_apply, hMdef, ContinuousLinearMap.sub_apply,
      ContinuousLinearMap.smul_apply, ContinuousLinearMap.one_apply] at h1
    rw [sub_eq_iff_eq_add] at h1
    rw [h1]
    abel
  -- the domination transfers to the resolvent: w ≤ (lam k - rho) • A k w
  have hwle : ∀ k : ℕ, w ≤ (lam k - rho) • A k w := by
    intro k
    have hMw : M k w ≤ (lam k - rho) • w := by
      rw [hMdef, ContinuousMap.le_def]
      intro x
      simp only [ContinuousMap.coe_sub, ContinuousMap.coe_smul, Pi.sub_apply, Pi.smul_apply,
        ContinuousMap.coe_one, ContinuousMap.one_apply, smul_eq_mul]
      have hd : rho * w x ≤ (T w) x := by
        have hx := ContinuousMap.le_def.mp hdom x
        simpa [ContinuousMap.coe_smul, Pi.smul_apply, smul_eq_mul] using hx
      calc lam k * w x - (T w) x ≤ lam k * w x - rho * w x := by linarith
        _ = (lam k - rho) * w x := by ring
    have hstep1 : A k (M k w) = w := by
      have h := congrArg (fun F : C(X, ℝ) →L[ℝ] C(X, ℝ) => F w) (hAM k)
      simpa [ContinuousLinearMap.mul_apply, ContinuousLinearMap.one_apply] using h
    have hmono : A k (M k w) ≤ (lam k - rho) • A k w := by
      have h := IsPositive.monotone (hApos k) hMw
      rwa [map_smul] at h
    rwa [hstep1] at hmono
  -- norm bounds
  have hwpos : 0 < ‖w‖ := norm_pos_iff.mpr hw0
  have hwnorm : ∀ k : ℕ, ‖w‖ ≤ (lam k - rho) * ‖A k w‖ := by
    intro k
    have h0w : (0 : C(X, ℝ)) ≤ w := by
      rw [ContinuousMap.le_def]
      intro x
      exact mem_positiveCone.mp hw x
    have h := norm_le_of_nonneg_le h0w (hwle k)
    rwa [norm_smul, Real.norm_eq_abs, abs_of_pos (hlampos k)] at h
  have hAWpos : ∀ k : ℕ, 0 < ‖A k w‖ := by
    intro k
    have h := hwnorm k
    have h2 : ‖w‖ / (lam k - rho) ≤ ‖A k w‖ := by
      rw [div_le_iff₀ (hlampos k), mul_comm]
      exact h
    have h1 : (0:ℝ) < ‖w‖ / (lam k - rho) := div_pos hwpos (hlampos k)
    exact lt_of_lt_of_le h1 h2
  -- the normalized resolvent orbit z k = A k w / ‖A k w‖
  set c : ℕ → ℝ := fun k => (‖A k w‖)⁻¹ with hcdef
  set z : ℕ → C(X, ℝ) := fun k => c k • A k w with hzdef
  have hcpos : ∀ k : ℕ, 0 < c k := fun k => by rw [hcdef]; exact inv_pos.mpr (hAWpos k)
  have hznorm : ∀ k : ℕ, ‖z k‖ = 1 := by
    intro k
    rw [hzdef, norm_smul, Real.norm_eq_abs, abs_of_pos (hcpos k), hcdef]
    exact inv_mul_cancel₀ (ne_of_gt (hAWpos k))
  have hAwc : ∀ k : ℕ, A k w ∈ positiveCone := fun k => (hres k).2 hw
  have hzcone : ∀ k : ℕ, z k ∈ positiveCone := by
    intro k
    rw [mem_positiveCone]
    intro x
    have hcx := mem_positiveCone.mp (hAwc k) x
    rw [hzdef]
    simp only [ContinuousMap.coe_smul, Pi.smul_apply, smul_eq_mul]
    exact mul_nonneg (le_of_lt (hcpos k)) hcx
  -- navigation for z: T (z k) = lam k • z k - c k • w
  have hznav : ∀ k : ℕ, T (z k) = lam k • z k - c k • w := by
    intro k
    have hAw := hnav k w
    rw [hzdef, map_smul, hAw, smul_sub, smul_smul, smul_smul, mul_comm (c k) (lam k)]
  -- compactness: T (z k) lies in a compact set, extract a convergent subsequence
  have hK : IsCompact (closure (T '' Metric.closedBall 0 1)) :=
    hTcomp.isCompact_closure_image_closedBall 1
  have hTzin : ∀ k : ℕ, T (z k) ∈ closure (T '' Metric.closedBall 0 1) :=
    fun k => subset_closure (mem_image_of_mem T (by
      rw [Metric.mem_closedBall, dist_eq_norm, sub_zero, hznorm k]))
  obtain ⟨v, -, φ, hφmono, hvlim⟩ := IsCompact.tendsto_subseq hK hTzin
  have hφge : ∀ k : ℕ, k ≤ φ k := by
    intro k
    induction k with
    | zero => exact Nat.zero_le _
    | succ n ih =>
        exact Nat.succ_le_of_lt (Nat.lt_of_le_of_lt ih (hφmono (Nat.lt_succ_self n)))
  -- scalar limits
  have hzero : Filter.Tendsto (fun k => lam (φ k) - rho) Filter.atTop (𝓝 0) := by
    have h2 : Filter.Tendsto (fun k => 1 / (((φ k : ℕ):ℝ) + 1)) Filter.atTop (𝓝 0) := by
      refine squeeze_zero (fun k => by positivity) (fun k => ?_) hone
      apply one_div_le_one_div_of_le (by positivity)
      exact_mod_cast Nat.succ_le_succ (hφge k)
    have hcongr : ∀ k : ℕ, 1 / (((φ k : ℕ):ℝ) + 1) = lam (φ k) - rho := by
      intro k
      rw [hlamdef]
      ring
    exact Filter.Tendsto.congr hcongr h2
  have hlamφ : Filter.Tendsto (fun k => lam (φ k)) Filter.atTop (𝓝 rho) := by
    have hadd : Filter.Tendsto (fun k => (lam (φ k) - rho) + rho) Filter.atTop (𝓝 (0 + rho)) :=
      hzero.add (tendsto_const_nhds (x := rho))
    rw [zero_add] at hadd
    have hcongr : ∀ k : ℕ, (lam (φ k) - rho) + rho = lam (φ k) := by
      intro k; ring
    exact Filter.Tendsto.congr hcongr hadd
  -- the residual c (φ k) • w → 0
  have hcz : Filter.Tendsto (fun k => c (φ k) • w) Filter.atTop (𝓝 0) := by
    rw [tendsto_iff_dist_tendsto_zero]
    have hnorm : ∀ k : ℕ, ‖c (φ k) • w‖ = c (φ k) * ‖w‖ := by
      intro k; rw [norm_smul, Real.norm_eq_abs, abs_of_pos (hcpos _)]
    have hbound : ∀ k : ℕ, c (φ k) * ‖w‖ ≤ (1:ℝ) / (((k:ℕ):ℝ) + 1) := by
      intro k
      have h := hwnorm (φ k)
      have hre := inv_mul_cancel₀ (hAWpos (φ k)).ne'
      have hstep : c (φ k) * ‖w‖ ≤ lam (φ k) - rho := by
        rw [hcdef]
        have hscale := mul_le_mul_of_nonneg_left h (inv_nonneg.mpr (norm_nonneg (A (φ k) w)))
        calc (‖A (φ k) w‖)⁻¹ * ‖w‖ ≤
            (‖A (φ k) w‖)⁻¹ * ((lam (φ k) - rho) * ‖A (φ k) w‖) := hscale
          _ = (lam (φ k) - rho) * ((‖A (φ k) w‖)⁻¹ * ‖A (φ k) w‖) := by ring
          _ = lam (φ k) - rho := by rw [hre, mul_one]
      have h2 : lam (φ k) - rho ≤ (1:ℝ) / (((k:ℕ):ℝ) + 1) := by
        rw [hlamdef]
        have hmid : (1:ℝ) / (((φ k : ℕ):ℝ) + 1) ≤ 1 / (((k:ℕ):ℝ) + 1) := by
          apply one_div_le_one_div_of_le (by positivity)
          exact_mod_cast Nat.succ_le_succ (hφge k)
        calc rho + 1 / (((φ k : ℕ):ℝ) + 1) - rho = 1 / (((φ k : ℕ):ℝ) + 1) := by ring
          _ ≤ 1 / (((k:ℕ):ℝ) + 1) := hmid
      exact hstep.trans h2
    refine squeeze_zero (fun k => by positivity) (fun k => ?_) hone
    show dist (c (φ k) • w) 0 ≤ 1 / (((k:ℕ):ℝ) + 1)
    rw [dist_zero_right, hnorm k]
    exact hbound k
  -- the subsequence limit is a cone eigenvector at rho
  have hzlim : Filter.Tendsto (fun k => z (φ k)) Filter.atTop (𝓝 ((rho:ℝ)⁻¹ • v)) := by
    have hlamne : ∀ k : ℕ, (lam (φ k) : ℝ) ≠ 0 := by
      intro k
      have hpos : 0 < lam (φ k) := by
        have := hlampos (φ k)
        rw [hlamdef] at this
        linarith [(by positivity : (0:ℝ) < 1 / (((φ k : ℕ):ℝ) + 1))]
      exact ne_of_gt hpos
    have hrew : ∀ k : ℕ, z (φ k) = (lam (φ k))⁻¹ • (T (z (φ k)) + c (φ k) • w) := by
      intro k
      have h := hznav (φ k)
      rw [eq_sub_iff_add_eq] at h
      calc z (φ k) = (lam (φ k))⁻¹ • (lam (φ k) • z (φ k)) := by
            rw [inv_smul_smul₀ (hlamne k)]
        _ = (lam (φ k))⁻¹ • (T (z (φ k)) + c (φ k) • w) := by rw [h]
    have hinv : Filter.Tendsto (fun k => (lam (φ k))⁻¹) Filter.atTop (𝓝 (rho⁻¹)) :=
      Filter.Tendsto.inv₀ hlamφ (ne_of_gt hrho)
    have hsum : Filter.Tendsto (fun k => T (z (φ k)) + c (φ k) • w) Filter.atTop (𝓝 (v + 0)) :=
      hvlim.add hcz
    have hs : Filter.Tendsto (fun k => (lam (φ k))⁻¹ • (T (z (φ k)) + c (φ k) • w))
        Filter.atTop (𝓝 ((rho:ℝ)⁻¹ • v)) := by
      simpa only [add_zero] using Filter.Tendsto.smul hinv hsum
    have hsmul : Filter.Tendsto (fun k => (lam (φ k))⁻¹ • (T (z (φ k)) + c (φ k) • w))
        Filter.atTop (𝓝 ((rho:ℝ)⁻¹ • v)) := by
      simpa only [add_zero] using Filter.Tendsto.smul hinv hsum
    have hcongr : ∀ k : ℕ, (lam (φ k))⁻¹ • (T (z (φ k)) + c (φ k) • w) = z (φ k) := by
      intro k
      exact (hrew k).symm
    exact Filter.Tendsto.congr hcongr hsmul
  have hfT : T ((rho:ℝ)⁻¹ • v) = v := by
    have h1 : Filter.Tendsto (fun k => T (z (φ k))) Filter.atTop (𝓝 (T ((rho:ℝ)⁻¹ • v))) :=
      (T.continuous.tendsto _).comp hzlim
    exact tendsto_nhds_unique h1 hvlim
  have hfeq : rho • ((rho:ℝ)⁻¹ • v) = v := by
    have hA : Filter.Tendsto (fun k => lam (φ k) • z (φ k)) Filter.atTop
        (𝓝 (rho • ((rho:ℝ)⁻¹ • v))) :=
      Filter.Tendsto.smul hlamφ hzlim
    have hcong : ∀ k : ℕ, lam (φ k) • z (φ k) = T (z (φ k)) + c (φ k) • w := by
      intro k
      have h := hznav (φ k)
      rw [eq_sub_iff_add_eq] at h
      exact h.symm
    have hadd2 : Filter.Tendsto (fun k => T (z (φ k)) + c (φ k) • w) Filter.atTop (𝓝 (v + 0)) :=
      hvlim.add hcz
    have hcongrB : ∀ k : ℕ, T (z (φ k)) + c (φ k) • w = lam (φ k) • z (φ k) := by
      intro k
      exact (hcong k).symm
    have hB : Filter.Tendsto (fun k => lam (φ k) • z (φ k)) Filter.atTop (𝓝 (v + 0)) :=
      Filter.Tendsto.congr hcongrB hadd2
    rw [add_zero] at hB
    exact tendsto_nhds_unique hA hB
  refine ⟨(rho:ℝ)⁻¹ • v, ?_, ?_, ?_⟩
  · exact isClosed_positiveCone.mem_of_tendsto hzlim
      (Filter.Eventually.of_forall fun k => hzcone _)
  · have hnormf : ‖((rho:ℝ)⁻¹ • v)‖ = 1 := by
      have h1 : Filter.Tendsto (fun k => ‖z (φ k)‖) Filter.atTop (𝓝 ‖((rho:ℝ)⁻¹ • v)‖) :=
        (continuous_norm.tendsto _).comp hzlim
      have hcongrN : ∀ k : ℕ, ‖z (φ k)‖ = (1:ℝ) := by
        intro k
        exact hznorm (φ k)
      have h2 : Filter.Tendsto (fun k : ℕ => (1:ℝ)) Filter.atTop (𝓝 ‖((rho:ℝ)⁻¹ • v)‖) :=
        Filter.Tendsto.congr hcongrN h1
      exact tendsto_nhds_unique h2 (tendsto_const_nhds (x := 1))
    intro hzero
    rw [hzero] at hnormf
    simp at hnormf
  · rw [hfT, hfeq]

/-- **Krein–Rutman core (proved here, no admission).**

A compact, positive operator `T` on `C(X, ℝ)` with positive spectral radius
has a nonzero positive eigenfunction at the spectral radius.

The seed comes from `Riemann.KreinRutman.exists_eigenvector_with_domination`:
it produces a nonzero (possibly sign-changing) eigenvector `v` at eigenvalue
`μ` with `|μ| = ρ` together with the pointwise domination

    ρ · |v(x)| ≤ (T |v|)(x)   for all x.

Setting `w := |v|` puts the nonzero modulus of `v` on the positive cone (in
the cone, and nonzero since `v ≠ 0`), the pointwise domination converts to
the vector inequality `rho • w ≤ T w` (`ContinuousMap.le_def`), and the
dichotomy `exists_positive_eigenvector_of_superharmonic` turns that seed into
the desired positive eigenvector at `rho`. -/
theorem kreinRutman_core' {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f := by
  let ρr : ℝ := (spectralRadius ℝ T).toReal
  have hρr : 0 < ρr := by
    simpa [ρr] using spectralRadius_toReal_pos hρ
  obtain ⟨v, hv0, μ, hμρ, hTv, hvdom⟩ :=
    exists_eigenvector_with_domination (T := T) hTpos hTcomp hρ
  let w : C(X, ℝ) := |v|
  have hwcon : w ∈ positiveCone := by
    simpa [w] using (absCm_pos hv0).1
  have hwne : w ≠ 0 := by
    simpa [w] using (absCm_pos hv0).2
  have hdom' : ρr • w ≤ T w := by
    rw [ContinuousMap.le_def]
    intro x
    change ρr * |v x| ≤ (T w) x
    simpa [ρr, smul_eq_mul] using hvdom x
  simpa [ρr] using
    exists_positive_eigenvector_of_superharmonic hTpos hTcomp hρr rfl hwne hwcon hdom'

/-! ## Krein–Rutman: the main theorems -/

/-- **Krein–Rutman theorem**, eigenvalue form.

A compact, positive operator `T` on `C(X, ℝ)` (for a compact Hausdorff `X`)
with positive spectral radius has the spectral radius as a positive
eigenvalue: there is a nonzero `f` with `0 ≤ f x` for all `x` and
`T f = (spectralRadius T).toReal • f`.

This is `kreinRutman_core'` above (proved modulo the file's single
documented admission, the β-stabilization gap);
the scaffold already proved in this file (real spectral value `|μ| = ρ(T)`
via the Fredholm alternative, the positivity transfer `T |f| ≥ ρ(T) |f|`)
lies on the direct road to closing that admission and is retained as
infrastructure for the next step. -/
theorem kreinRutman {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f :=
  kreinRutman_core' hTpos hTcomp hρ

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
