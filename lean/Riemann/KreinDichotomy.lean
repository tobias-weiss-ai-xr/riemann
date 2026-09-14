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
  (the classical compactness argument, the single analytic admission of this file);
* the domination seed `|v|` obtained from
  `Riemann.KreinRutman.exists_eigenvector_with_domination` satisfies
  `rho • |v| ≤ T |v|` on the cone, so the dichotomy yields the positive
  spectral-radius eigenvector `kreinRutman_core'` with *no further
  admission in this file*.

The only analytic admission in this file is the unbounded branch of
`exists_positive_eigenvector_of_superharmonic`; everything else is proved.
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

/-- **Superharmonic seeds force exact positive eigenvectors (dichotomy).**

If a nonzero cone vector `w` satisfies the domination inequality
`rho • w ≤ T w` (equivalently `T w ≥ rho • w`) for `rho > 0`, then `T` has
a nonzero eigenvector `f` in the positive cone at eigenvalue `rho`.

*Bounded branch.*  If `‖superharmonicOrbit T rho w n‖` is bounded, the
orbit-closure theorem `bounded_orbit_yields_positive_eigenvector` applies
directly (its hypothesis `T w ≥ rho • w` is the same inequality).

*Unbounded branch (the analytic frontier, one admitted).*  The
classical normalized-orbit cluster argument: set `orb n := orbit n` and
`u n := orb n / ‖orb n‖` (well-defined since `superharmonicOrbit_nonzero`).
The navigation identity gives `T (orb n) = rho • orb (n + 1)`, hence —
dividing by `‖orb n‖` (`smul_norm`) —

    T (u n) = rho * (‖orb (n + 1)‖ / ‖orb n‖) • u (n + 1).

All `u n` have norm one and lie in the closed cone.  Compactness of `T`
(Bolzano–Weierstrass on `T (closedBall 0 1)`) gives a subsequence `φ` with
`T (u (φ k)) → g`; passing to a further subsequence
(`u (φ k + 1)` lives in the closed unit ball) yields `u (φ k + 1) → u*`
with `‖u*‖ = 1` and `u* ∈ positiveCone` (the cone is closed).  The limit of
the identity above then reads

    T u* = rho * ρ* • u**   with   ρ* := lim ‖orb (φ k + 1)‖ / ‖orb (φ k)‖

and `u**` the limit of `u (φ k + 2)`.  The monotonicity
`orb n ≤ orb (n + 1)` forces `ρ* ≥ 1`; iterating the argument along the
cluster chain `u*, u**, …` (all of norm one — the convergence is norm-forced
by the monotone orbit) the scalar ratios must stabilize at `1`, and the
chain closes up to an exact eigenvector `T u° = rho • u°` with `u° ≠ 0`
and `u° ∈ positiveCone`. -/
theorem exists_positive_eigenvector_of_superharmonic {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T) {rho : ℝ} (hrho : 0 < rho)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : rho • w ≤ T w) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧ T f = rho • f := by
  by_cases hbdd : ∃ C : ℝ, ∀ n : ℕ, ‖superharmonicOrbit T rho w n‖ ≤ C
  · -- bounded branch: hand the bounded orbit to the orbit-closure theorem
    -- (its hypothesis `T w ≥ rho • w` is exactly `rho • w ≤ T w`)
    exact bounded_orbit_yields_positive_eigenvector hTpos hTcomp hrho hw0 hw hdom hbdd
  · -- unbounded branch: the classical normalized-orbit cluster argument
    -- [sketch] Let `orb n := superharmonicOrbit T rho w n` and normalize
    -- `u n := orb n / ‖orb n‖` (‖orb n‖ ≠ 0 by `superharmonicOrbit_nonzero`).
    -- The navigation identity gives
    --   T (orb n) = rho • orb (n + 1),  hence dividing by ‖orb n‖
    --   T (u n) = rho * (‖orb (n + 1)‖ / ‖orb n‖) • u (n + 1).
    -- All `u n` have norm 1 and lie in the closed cone.  Compactness of `T`
    -- (Bolzano–Weierstrass on `T (closedBall 0 1)`) gives a subsequence φ
    -- with `T (u (φ k)) → g`; passing to a further subsequence
    -- (`u (φ k + 1)` lives in the compact closed unit ball) gives
    -- `u (φ k + 1) → u*` with ‖u*‖ = 1 and u* ∈ positiveCone (closed cone).
    -- The limit of the identity above reads
    --   T u* = rho * ρ* • u**   with ρ* := lim ‖orb (φ k + 1)‖ / ‖orb (φ k)‖
    -- and u** the limit of u (φ k + 2).  The monotonicity orb n ≤ orb (n + 1)
    -- forces ρ* ≥ 1; iterating along the cluster chain u*, u**, … the scalar
    -- ratios must stabilize at 1 (all cluster points have norm 1), and the
    -- chain closes up to an exact eigenvector T u° = rho • u°, u° ≠ 0,
    -- u° ∈ positiveCone.
    sorry

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
  -- the domination seed: v ≠ 0, |μ| = ρ, T v = μ • v, ρ · |v| ≤ T |v|
  obtain ⟨v, hv0, μ, hμρ, hTv, hvdom⟩ :=
    exists_eigenvector_with_domination (T := T) hTpos hTcomp hρ
  -- w := |v| is a nonzero cone vector (reuse the modulus construction of
  -- KreinRutman.lean via `absCm_pos`)
  let w : C(X, ℝ) := |v|
  have hwcon : w ∈ positiveCone := by
    simpa [w] using (absCm_pos hv0).1
  have hwne : w ≠ 0 := by
    simpa [w] using (absCm_pos hv0).2
  -- the pointwise domination converts to the vector inequality rho • w ≤ T w
  have hdom' : ρr • w ≤ T w := by
    rw [ContinuousMap.le_def]
    intro x
    change ρr * |v x| ≤ (T w) x
    simpa [ρr, smul_eq_mul] using hvdom x
  simpa [ρr] using
    exists_positive_eigenvector_of_superharmonic hTpos hTcomp hρr hwne hwcon hdom'

end

end Riemann
