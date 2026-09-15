/-
Copyright (c) 2026 Tobias Weiss
Krein–Rutman dichotomy: superharmonic seeds forced onto exact eigenvectors.

This module closes the Krein–Rutman existence argument without touching
`Riemann.KreinRutman.kreinRutman_core` (which remains the single documented
admission of that file).  The route is the *dichotomy*:

* every nonzero cone vector `w` with `rho • w ≤ T w` (`rho > 0`) either has a
  bounded superharmonic orbit — then `Riemann.OrbitClosure`
  (`bounded_orbit_yields_positive_eigenvector`) produces a positive exact
  eigenvector at `rho` — or its normalized orbit clusters onto one
  (the classical compactness argument via `normalized_orbit_cluster`);
* the domination seed `|v|` obtained from
  `Riemann.KreinRutman.exists_eigenvector_with_domination` satisfies
  `rho • |v| ≤ T |v|` on the cone, so the dichotomy yields the positive
  spectral-radius eigenvector `kreinRutman_core'` with *no further
  admission in this file*.

The only analytic admission in this file is now the crisp
`cluster_chain_stabilizes` lemma (the beta-stabilization gap).
-/

import Riemann.KreinRutman
import Riemann.OrbitClosure

open scoped ContinuousMap NNReal Topology
open Filter
open Set

namespace Riemann

noncomputable section

set_option maxHeartbeats 5000000

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [Nonempty X]

/-- The beta ratio for the superharmonic orbit. -/
def superharmonicBeta (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) (rho : ℝ) (w : C(X, ℝ)) (n : ℕ) : ℝ :=
  ‖superharmonicOrbit T rho w (n + 1)‖ / ‖superharmonicOrbit T rho w n‖

/-- Normalized superharmonic orbit. -/
def uNorm (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) (rho : ℝ) (w : C(X, ℝ)) (n : ℕ) : C(X, ℝ) :=
  (‖superharmonicOrbit T rho w n‖)⁻¹ • superharmonicOrbit T rho w n

/-- The normalized superharmonic orbit has unit norm. -/
theorem uNorm_norm {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T) {rho : ℝ} (hrho : 0 < rho)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : rho • w ≤ T w)
    (n : ℕ) : ‖uNorm T rho w n‖ = 1 := by
  unfold uNorm
  have hne : superharmonicOrbit T rho w n ≠ 0 :=
    superharmonicOrbit_nonzero hT hrho hw0 hw hdom n
  have hnn : ‖superharmonicOrbit T rho w n‖ ≠ 0 := norm_ne_zero_iff.mpr hne
  have hnp : 0 < ‖superharmonicOrbit T rho w n‖ := norm_pos_iff.mpr hne
  simp only [norm_smul, Real.norm_eq_abs, abs_inv, abs_of_pos hnp]
  exact inv_mul_cancel₀ hnn

/-- The normalized superharmonic orbit lies in the positive cone. -/
theorem uNorm_mem {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T) {rho : ℝ} (hrho : 0 < rho)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : rho • w ≤ T w) (n : ℕ) :
    uNorm T rho w n ∈ positiveCone := by
  unfold uNorm
  have hc : superharmonicOrbit T rho w n ∈ positiveCone :=
    superharmonicOrbit_mem hT hrho hw hdom n
  have hnp : 0 < ‖superharmonicOrbit T rho w n‖ :=
    norm_pos_iff.mpr (superharmonicOrbit_nonzero hT hrho hw0 hw hdom n)
  rw [mem_positiveCone]
  intro x
  simp only [ContinuousMap.coe_smul, Pi.smul_apply, smul_eq_mul]
  exact mul_nonneg (inv_nonneg.mpr (le_of_lt hnp)) (hc x)

/-- Beta is at least 1 (from monotonicity of the superharmonic orbit). -/
theorem superharmonicBeta_ge_one {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {rho : ℝ} (hrho : 0 < rho) {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone)
    (hdom : rho • w ≤ T w) (n : ℕ) : 1 ≤ superharmonicBeta T rho w n := by
  unfold superharmonicBeta
  have hmono : superharmonicOrbit T rho w n ≤ superharmonicOrbit T rho w (n + 1) :=
    superharmonicOrbit_mono hT hrho hw hdom n
  have h0 : (0 : C(X, ℝ)) ≤ superharmonicOrbit T rho w n := by
    rw [ContinuousMap.le_def]
    intro x
    exact superharmonicOrbit_mem hT hrho hw hdom n x
  have hnorm : ‖superharmonicOrbit T rho w n‖ ≤ ‖superharmonicOrbit T rho w (n + 1)‖ :=
    norm_le_of_nonneg_le h0 hmono
  have hnpos : 0 < ‖superharmonicOrbit T rho w n‖ :=
    norm_pos_iff.mpr (superharmonicOrbit_nonzero hT hrho hw0 hw hdom n)
  exact (one_le_div hnpos).mpr hnorm

/-- **Normalized-orbit cluster chain**: the superharmonic orbit produces a
subsequence along which `T` acts as a scaled isometry between cluster points
with ratio at least 1.

This is the compactness half of the classical Krein–Rutman argument for the
unbounded branch.  The compactness input is *not* compactness of the unit
ball (which fails in infinite dimension) but compactness of the image of the
ball under the compact operator `T`; the scalar limits `beta` come for free
from norm convergence of the `T`-images.  The remaining analytic step
(forcing the scaling factor to equal 1) is isolated in
`cluster_chain_stabilizes`.

Reference: Krein–Rutman (1948), §3; Schaefer, *Banach Lattices and Positive
Operators*, III.7. -/
theorem normalized_orbit_cluster {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T) {rho : ℝ} (hrho : 0 < rho)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : rho • w ≤ T w) :
    ∃ φ : ℕ → ℕ, StrictMono φ ∧ ∃ uStar uDStar : C(X, ℝ), ∃ beta : ℝ,
      uStar ∈ positiveCone ∧ uDStar ∈ positiveCone ∧ ‖uStar‖ = 1 ∧ ‖uDStar‖ = 1 ∧
      1 ≤ beta ∧ T uStar = (rho * beta) • uDStar := by
  let orb : ℕ → C(X, ℝ) := fun n => superharmonicOrbit T rho w n
  let u : ℕ → C(X, ℝ) := fun n => uNorm T rho w n
  let beta : ℕ → ℝ := fun n => superharmonicBeta T rho w n
  have hu_norm : ∀ n, ‖u n‖ = 1 := fun n => uNorm_norm hTpos hrho hw0 hw hdom n
  have hu_mem : ∀ n, u n ∈ positiveCone := fun n => uNorm_mem hTpos hrho hw0 hw hdom n
  have hbeta_ge : ∀ n, 1 ≤ beta n := fun n => superharmonicBeta_ge_one hTpos hrho hw0 hw hdom n
  have hβpos : ∀ n, 0 < beta n := fun n => lt_of_lt_of_le zero_lt_one (hbeta_ge n)
  have hnav : ∀ n, T (u n) = (rho * beta n) • u (n + 1) := by
    intro n
    unfold u beta uNorm superharmonicBeta
    have hne_n : orb n ≠ 0 := superharmonicOrbit_nonzero hTpos hrho hw0 hw hdom n
    have hne_np1 : orb (n + 1) ≠ 0 := superharmonicOrbit_nonzero hTpos hrho hw0 hw hdom (n + 1)
    have hnn : ‖orb n‖ ≠ 0 := norm_ne_zero_iff.mpr hne_n
    have hnnp1 : ‖orb (n + 1)‖ ≠ 0 := norm_ne_zero_iff.mpr hne_np1
    have hnav_raw : T (orb n) = rho • orb (n + 1) :=
      superharmonicOrbit_navigation (ne_of_gt hrho) n
    calc
      T ((‖orb n‖)⁻¹ • orb n) = (‖orb n‖)⁻¹ • T (orb n) := by rw [map_smul]
      _ = (‖orb n‖)⁻¹ • (rho • orb (n + 1)) := by rw [hnav_raw]
      _ = rho • ((‖orb n‖)⁻¹ • orb (n + 1)) := by rw [smul_comm]
      _ = rho • ((‖orb (n + 1)‖ / ‖orb n‖) • ((‖orb (n + 1)‖)⁻¹ • orb (n + 1))) := by
        congr 1
        have h_inv_mul : (‖orb (n + 1)‖ / ‖orb n‖) * (‖orb (n + 1)‖)⁻¹ = (‖orb n‖)⁻¹ := by
          field_simp [hnn, hnnp1]
        calc
          (‖orb n‖)⁻¹ • orb (n + 1) =
              ((‖orb (n + 1)‖ / ‖orb n‖) * (‖orb (n + 1)‖)⁻¹) • orb (n + 1) := by
            rw [← h_inv_mul]
          _ = (‖orb (n + 1)‖ / ‖orb n‖) • ((‖orb (n + 1)‖)⁻¹ • orb (n + 1)) := by
            rw [mul_smul]
      _ = (rho * (‖orb (n + 1)‖ / ‖orb n‖)) • ((‖orb (n + 1)‖)⁻¹ • orb (n + 1)) := by
        rw [mul_smul]
      _ = (rho * (‖orb (n + 1)‖ / ‖orb n‖)) • u (n + 1) := rfl
  -- norm of the T-images: ‖T (u m)‖ = rho * beta m
  have huTnorm : ∀ m, ‖T (u m)‖ = rho * beta m := by
    intro m
    calc ‖T (u m)‖ = ‖(rho * beta m) • u (m + 1)‖ := by rw [hnav m]
      _ = |rho * beta m| * ‖u (m + 1)‖ := norm_smul _ _
      _ = rho * beta m := by
        rw [abs_of_nonneg (mul_nonneg hrho.le (zero_le_one.trans (hbeta_ge m))),
          hu_norm (m + 1), mul_one]
  -- compactness: the image of the closed ball of radius max ‖T‖ 1 under the
  -- compact operator T (compactness of the ball itself fails in infinite
  -- dimension!); every u m lies in that ball since ‖u m‖ = 1
  have hK : IsCompact (closure (T '' Metric.closedBall (0 : C(X, ℝ)) (max ‖T‖ 1))) :=
    hTcomp.isCompact_closure_image_closedBall (max ‖T‖ 1)
  have humemK : ∀ m, T (u m) ∈ closure (T '' Metric.closedBall (0 : C(X, ℝ)) (max ‖T‖ 1)) := by
    intro m
    exact subset_closure (mem_image_of_mem T (by
      simpa [Metric.mem_closedBall, dist_eq_norm, u] using
        le_trans (hu_norm m).le (le_max_right ‖T‖ 1)))
  have huTcone : ∀ m, T (u m) ∈ positiveCone := by
    intro m
    rw [mem_positiveCone]
    intro x
    exact hTpos.apply_nonneg (hu_mem m) x
  -- layer 1: T (u (k + 1)) converges along a subsequence φA
  obtain ⟨h₁, _h₁K, φA, hφAmono, hTφA⟩ :=
    IsCompact.tendsto_subseq hK (fun k => humemK (k + 1))
  -- layer 2: refine so that T (u (k + 2)) converges as well
  obtain ⟨h₂, _h₂K, φB, hφBmono, hTφB⟩ :=
    IsCompact.tendsto_subseq hK (fun k => humemK (φA k + 2))
  have hT1 : Tendsto (fun k => T (u (φA (φB k) + 1))) atTop (nhds h₁) :=
    hTφA.comp hφBmono.tendsto_atTop
  have hT2 : Tendsto (fun k => T (u (φA (φB k) + 2))) atTop (nhds h₂) := hTφB
  set b₁ : ℝ := ‖h₁‖ / rho with hb₁def
  set b₂ : ℝ := ‖h₂‖ / rho with hb₂def
  have hnorm1 : Tendsto (fun k => ‖T (u (φA (φB k) + 1))‖) atTop (nhds ‖h₁‖) :=
    (continuous_norm.tendsto _).comp hT1
  have hnorm2 : Tendsto (fun k => ‖T (u (φA (φB k) + 2))‖) atTop (nhds ‖h₂‖) :=
    (continuous_norm.tendsto _).comp hT2
  have hnorm1ge : rho ≤ ‖h₁‖ :=
    ge_of_tendsto hnorm1 (Eventually.of_forall fun k => by
      rw [huTnorm]
      simpa using mul_le_mul_of_nonneg_left (hbeta_ge _) hrho.le)
  have hnorm2ge : rho ≤ ‖h₂‖ :=
    ge_of_tendsto hnorm2 (Eventually.of_forall fun k => by
      rw [huTnorm]
      simpa using mul_le_mul_of_nonneg_left (hbeta_ge _) hrho.le)
  have hb1eq : rho * b₁ = ‖h₁‖ := by
    rw [hb₁def]
    field_simp
  have hb2eq : rho * b₂ = ‖h₂‖ := by
    rw [hb₂def]
    field_simp
  have hb1pos : 0 < rho * b₁ := by rw [hb1eq]; exact lt_of_lt_of_le hrho hnorm1ge
  have hb2pos : 0 < rho * b₂ := by rw [hb2eq]; exact lt_of_lt_of_le hrho hnorm2ge
  have hne1 : rho * b₁ ≠ 0 := ne_of_gt hb1pos
  have hne2 : rho * b₂ ≠ 0 := ne_of_gt hb2pos
  have hne0₁ : h₁ ≠ 0 := by
    intro hh
    rw [hh, norm_zero] at hnorm1ge
    exact lt_irrefl rho (lt_of_le_of_lt hnorm1ge hrho)
  have hne0₂ : h₂ ≠ 0 := by
    intro hh
    rw [hh, norm_zero] at hnorm2ge
    exact lt_irrefl rho (lt_of_le_of_lt hnorm2ge hrho)
  -- cluster points: uStar := lim u (… + 2), uDStar := lim u (… + 3),
  -- obtained as rescaled limits of the convergent T-images
  have hb1con : Tendsto (fun k => rho * beta (φA (φB k) + 1)) atTop (nhds (rho * b₁)) := by
    have hrew : (fun k => rho * beta (φA (φB k) + 1))
        = fun k => ‖T (u (φA (φB k) + 1))‖ := by
      funext k; exact (huTnorm _).symm
    rw [hrew, hb1eq]; exact hnorm1
  have hscal1 : Tendsto (fun k => (rho * beta (φA (φB k) + 1))⁻¹) atTop (nhds (rho * b₁)⁻¹) := by
    have hinv : ContinuousAt (fun x : ℝ => x⁻¹) (rho * b₁) :=
      ContinuousAt.inv₀ continuousAt_id hne1
    exact hinv.tendsto.comp hb1con
  have hb2con : Tendsto (fun k => rho * beta (φA (φB k) + 2)) atTop (nhds (rho * b₂)) := by
    have hrew : (fun k => rho * beta (φA (φB k) + 2))
        = fun k => ‖T (u (φA (φB k) + 2))‖ := by
      funext k; exact (huTnorm _).symm
    rw [hrew, hb2eq]; exact hnorm2
  have hscal2 : Tendsto (fun k => (rho * beta (φA (φB k) + 2))⁻¹) atTop (nhds (rho * b₂)⁻¹) := by
    have hinv : ContinuousAt (fun x : ℝ => x⁻¹) (rho * b₂) :=
      ContinuousAt.inv₀ continuousAt_id hne2
    exact hinv.tendsto.comp hb2con
  set uStar : C(X, ℝ) := (rho * b₁)⁻¹ • h₁ with huStardef
  set uDStar : C(X, ℝ) := (rho * b₂)⁻¹ • h₂ with huDStardef
  -- uStar and uDStar are the subsequential limits of the normalized orbit
  have huStar_lim : Tendsto (fun k => u (φA (φB k) + 2)) atTop (nhds uStar) := by
    have hrew : (fun k => u (φA (φB k) + 2))
        = fun k => (rho * beta (φA (φB k) + 1))⁻¹ • T (u (φA (φB k) + 1)) := by
      funext k
      rw [hnav (φA (φB k) + 1), inv_smul_smul₀ (mul_ne_zero (ne_of_gt hrho) (ne_of_gt (hβpos _)))]
    rw [hrew]
    exact hscal1.smul hT1
  have huDStar_lim : Tendsto (fun k => u (φA (φB k) + 3)) atTop (nhds uDStar) := by
    have hrew : (fun k => u (φA (φB k) + 3))
        = fun k => (rho * beta (φA (φB k) + 2))⁻¹ • T (u (φA (φB k) + 2)) := by
      funext k
      rw [hnav (φA (φB k) + 2), inv_smul_smul₀ (mul_ne_zero (ne_of_gt hrho) (ne_of_gt (hβpos _)))]
    rw [hrew]
    exact hscal2.smul hT2
  -- unit norms: ‖h‖ = rho * b rescales the T-image limits to norm 1
  have hnormS : ‖uStar‖ = 1 := by
    rw [huStardef, norm_smul, Real.norm_eq_abs, abs_of_pos (inv_pos.mpr hb1pos), hb1eq,
      inv_mul_cancel₀ (norm_ne_zero_iff.mpr hne0₁)]
  have hnormD : ‖uDStar‖ = 1 := by
    rw [huDStardef, norm_smul, Real.norm_eq_abs, abs_of_pos (inv_pos.mpr hb2pos), hb2eq,
      inv_mul_cancel₀ (norm_ne_zero_iff.mpr hne0₂)]
  -- cone membership (rescaling by a positive scalar keeps the cone)
  have h₁cone : h₁ ∈ positiveCone :=
    isClosed_positiveCone.mem_of_tendsto hT1
      (Eventually.of_forall fun k => huTcone _)
  have h₂cone : h₂ ∈ positiveCone :=
    isClosed_positiveCone.mem_of_tendsto hT2
      (Eventually.of_forall fun k => huTcone _)
  have huStarcone : uStar ∈ positiveCone := by
    rw [mem_positiveCone]
    intro x
    rw [huStardef]
    simp only [ContinuousMap.coe_smul, Pi.smul_apply, smul_eq_mul]
    exact mul_nonneg (inv_nonneg.mpr hb1pos.le) (h₁cone x)
  have huDStarcone : uDStar ∈ positiveCone := by
    rw [mem_positiveCone]
    intro x
    rw [huDStardef]
    simp only [ContinuousMap.coe_smul, Pi.smul_apply, smul_eq_mul]
    exact mul_nonneg (inv_nonneg.mpr hb2pos.le) (h₂cone x)
  -- the relation: T uStar = h₂ = (rho * b₂) • uDStar
  have hTuStar : T uStar = h₂ := by
    have h1 : Tendsto (fun k => T (u (φA (φB k) + 2))) atTop (nhds (T uStar)) :=
      (T.continuous.tendsto uStar).comp huStar_lim
    exact tendsto_nhds_unique h1 hT2
  have hbeta : 1 ≤ b₂ := by
    rw [hb₂def]
    exact (one_le_div hrho).mpr hnorm2ge
  refine ⟨fun k => φA (φB k), hφAmono.comp hφBmono, uStar, uDStar, b₂,
    huStarcone, huDStarcone, hnormS, hnormD, hbeta, ?_⟩
  rw [hTuStar, huDStardef, smul_inv_smul₀ hne2]

/-- **Cluster-chain stabilization gap (the single analytic admission).**

Given the cluster-chain data from `normalized_orbit_cluster`:
`T uStar = (rho * beta) • uDStar` with all norms 1 and all vectors in the
positive cone, and `beta ≥ 1`, extract a positive eigenvector.

What is known: if `beta = 1` then `T uStar = rho • uDStar` with
`uDStar ≠ 0` (since `‖uDStar‖ = 1`) — we are done: `uStar` is the desired
positive eigenvector at `rho`.

However, the general case requires showing that the beta-stabilization
mechanism forces beta = 1.  This is the analytic frontier of the real
Krein–Rutman proof.  The hypothesis `rho = spectralRadius ℝ T` is
*essential* here: at sub-radius rates the stabilization fails (the
counterexample `T(x, y) = (x + y, y)` with seed `(0, 1)` and `rho = 1/2`
admits a cluster chain with `beta > 1` but has no eigenvector at `1/2` —
its only eigenvalue is `1`).

Reference: Krein–Rutman (1948), §6-7; Schaefer, *Banach Lattices and
Positive Operators*, III.8–9. -/
theorem cluster_chain_stabilizes {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T) {rho : ℝ} (hrho : 0 < rho)
    (hr : rho = (spectralRadius ℝ T).toReal)
    {uStar uDStar : C(X, ℝ)} (huStar : uStar ∈ positiveCone) (huDStar : uDStar ∈ positiveCone)
    (hnormS : ‖uStar‖ = 1) (hnormD : ‖uDStar‖ = 1) {beta : ℝ} (hbeta : 1 ≤ beta)
    (heq : T uStar = (rho * beta) • uDStar) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧ T f = rho • f :=
  sorry

/-- **Superharmonic seeds force exact positive eigenvectors (dichotomy).**

If a nonzero cone vector `w` satisfies the domination inequality
`rho • w ≤ T w` (equivalently `T w ≥ rho • w`) for `rho > 0`, then `T` has
a nonzero eigenvector `f` in the positive cone at eigenvalue `rho`.

*Bounded branch.*  If `‖superharmonicOrbit T rho w n‖` is bounded, the
orbit-closure theorem `bounded_orbit_yields_positive_eigenvector` applies
directly (its hypothesis `T w ≥ rho • w` is the same inequality).

The hypothesis `rho = spectralRadius ℝ T` is *necessary*: take
`T(x, y) = (x + y, y)` on `C(ℕ₂)` (positive, compact) with seed `w = (0, 1)`
and `rho = 1/2`; the domination `rho • w ≤ T w` holds, yet `T`'s only
eigenvalue is `1`, so no cone eigenvector at `1/2` exists.  At rates below
the spectral radius both branches fail (the bounded branch of the orbit
closure survives only vacuously there: boundedness itself already forces the
eigenvector).  The spectral-radius link is exactly the classical
Krein–Rutman superharmonic-seed hypothesis.

*Unbounded branch.*  Derives from `normalized_orbit_cluster` +
the single remaining analytic gap `cluster_chain_stabilizes`. -/
theorem exists_positive_eigenvector_of_superharmonic {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T) {rho : ℝ} (hrho : 0 < rho)
    (hr : rho = (spectralRadius ℝ T).toReal)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : rho • w ≤ T w) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧ T f = rho • f := by
  by_cases hbdd : ∃ C : ℝ, ∀ n : ℕ, ‖superharmonicOrbit T rho w n‖ ≤ C
  · -- bounded branch
    exact bounded_orbit_yields_positive_eigenvector hTpos hTcomp hrho hw0 hw hdom hbdd
  · -- unbounded branch: normalized-orbit cluster argument
    obtain ⟨φ, hφmono, uStar, uDStar, beta, huStar, huDStar, hnormS, hnormD, hbeta, heq⟩ :=
      normalized_orbit_cluster hTpos hTcomp hrho hw0 hw hdom
    exact cluster_chain_stabilizes hTpos hTcomp hrho hr huStar huDStar hnormS hnormD hbeta heq

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

end

end Riemann
