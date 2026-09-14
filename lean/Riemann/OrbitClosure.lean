/-
Copyright (c) 2026 Tobias Weiss
Orbit-closure structure: bounded superharmonic orbits yield positive eigenvectors.

This module isolates the "orbit closure" half of the Krein–Rutman machine for
positive compact operators `T` on `C(X, ℝ)` (see `Riemann.KreinRutman` for the
positive cone).  Given a nonzero cone vector `w` satisfying the domination
inequality `T w ≥ ρ · w` with `ρ > 0`, we study the orbit

    orbitₙ = ρ⁻ⁿ Tⁿ w

and show that, when it is norm-bounded, compactness of `T` forces a nonzero
eigenvector `f` in the positive cone with `T f = ρ · f`.

The navigation identity `T orbitₙ = ρ · orbitₙ₊₁` is exactly the statement
that the orbit is a discrete orbit of the *renormalised* dynamics `ρ⁻¹T`;
below it is proved (it needs `ρ ≠ 0`: for `ρ = 0`, `n = 0` it would claim
`T w = 0` for arbitrary `w`).
-/

import Riemann.KreinRutman

open scoped ContinuousMap NNReal Topology
open Filter
open Set

namespace Riemann

noncomputable section

set_option maxHeartbeats 5000000

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [Nonempty X]

/-- The superharmonic orbit of `w` under `T` at growth rate `ρ`:

    orbitₙ = ρ⁻ⁿ Tⁿ w.

For a vector satisfying the domination inequality `T w ≥ ρ · w` this is the
sequence of renormalised iterates around which the direction of `w` spirals
towards a positive eigenvector of `T`. -/
def superharmonicOrbit (T : C(X, ℝ) →L[ℝ] C(X, ℝ)) (rho : ℝ) (w : C(X, ℝ))
    (n : ℕ) : C(X, ℝ) :=
  (rho⁻¹ : ℝ) ^ n • (T ^ n) w

/-- The orbit stays inside the positive cone (pointwise nonnegativity). -/
theorem superharmonicOrbit_mem {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {rho : ℝ} (hrho : 0 < rho) {w : C(X, ℝ)} (hw : w ∈ positiveCone)
    (hdom : T w ≥ rho • w) : ∀ n : ℕ, superharmonicOrbit T rho w n ∈ positiveCone := by
  intro n
  rw [mem_positiveCone]
  intro x
  unfold superharmonicOrbit
  exact mul_nonneg
    (pow_nonneg (inv_nonneg.mpr (le_of_lt hrho)) n)
    (IsPositive.apply_nonneg (IsPositive.pow hT n) hw x)

/-- Navigation: `T orbitₙ = ρ · orbitₙ₊₁`.

This is pure algebra from the definition.  The hypothesis `ρ ≠ 0` is
necessary: for `ρ = 0` the identity at `n = 0` would read `T w = 0`,
which is false for arbitrary `w`. -/
theorem superharmonicOrbit_navigation {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {rho : ℝ}
    (hrho : rho ≠ 0) {w : C(X, ℝ)} (n : ℕ) :
    T (superharmonicOrbit T rho w n) = rho • superharmonicOrbit T rho w (n + 1) := by
  unfold superharmonicOrbit
  have hstep : T ((T ^ n) w) = (T ^ (n + 1)) w := by
    rw [pow_succ']
    rfl
  have hfac : rho * (rho⁻¹ : ℝ) ^ (n + 1) = (rho⁻¹ : ℝ) ^ n := by
    rw [pow_succ]
    calc
      rho * ((rho⁻¹ : ℝ) ^ n * rho⁻¹) = (rho * rho⁻¹) * (rho⁻¹ : ℝ) ^ n := by ring
      _ = 1 * (rho⁻¹ : ℝ) ^ n := by rw [mul_inv_cancel₀ hrho]
      _ = (rho⁻¹ : ℝ) ^ n := by ring
  calc
    T (((rho⁻¹ : ℝ) ^ n) • ((T ^ n) w)) = ((rho⁻¹ : ℝ) ^ n) • (T ((T ^ n) w)) := by
      simpa using map_smul T ((rho⁻¹ : ℝ) ^ n) ((T ^ n) w)
    _ = ((rho⁻¹ : ℝ) ^ n) • ((T ^ (n + 1)) w) := by rw [← hstep]
    _ = rho • (((rho⁻¹ : ℝ) ^ (n + 1)) • ((T ^ (n + 1)) w)) := by
      rw [smul_smul]
      rw [hfac]

/-- Iterating the domination inequality: `ρⁿ w ≤ Tⁿ w` for every `n`. -/
theorem pow_T_ge_smul {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T) {rho : ℝ}
    (hrho : 0 < rho) {w : C(X, ℝ)} (hw : w ∈ positiveCone) (hdom : T w ≥ rho • w) :
    ∀ n : ℕ, (rho : ℝ) ^ n • w ≤ (T ^ n) w := by
  intro n
  induction n with
  | zero => simp
  | succ k ih =>
      calc
        (rho : ℝ) ^ (k + 1) • w = rho • ((rho : ℝ) ^ k • w) := by
          rw [pow_succ', ← smul_smul]
        _ ≤ rho • ((T ^ k) w) := by
          rw [ContinuousMap.le_def]
          intro x
          exact mul_le_mul_of_nonneg_left ((ContinuousMap.le_def.mp ih) x) (le_of_lt hrho)
        _ ≤ (T ^ (k + 1)) w := by
          have hmono := IsPositive.monotone (IsPositive.pow hT k) hdom
          have hTkm : (T ^ k) (rho • w) = rho • ((T ^ k) w) := by
            simpa using map_smul (T ^ k) rho w
          have hTkT : (T ^ k) (T w) = (T ^ (k + 1)) w := by
            rw [pow_succ]
            rfl
          rw [← hTkT, ← hTkm]
          exact hmono

/-- The orbit never hits zero: every renormalised iterate is a nonzero
function (it stays strictly above `w` at a point where `w` is positive). -/
theorem superharmonicOrbit_nonzero {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {rho : ℝ} (hrho : 0 < rho) {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone)
    (hdom : T w ≥ rho • w) : ∀ n : ℕ, superharmonicOrbit T rho w n ≠ 0 := by
  intro n
  have hTn_ne : (T ^ n) w ≠ 0 := by
    have hpen : ∃ x0 : X, 0 < w x0 := by
      by_contra h
      apply hw0
      ext x
      have hle : w x ≤ 0 := le_of_not_gt (fun hgt => h ⟨x, hgt⟩)
      simpa using (le_antisymm hle (hw x))
    obtain ⟨x0, hx0⟩ := hpen
    have hge := (ContinuousMap.le_def.mp (pow_T_ge_smul hT hrho hw hdom n)) x0
    intro hz
    have hpos : 0 < (rho : ℝ) ^ n * w x0 := mul_pos (pow_pos hrho n) hx0
    have hle0 : (rho : ℝ) ^ n * w x0 ≤ 0 := by
      simpa [hz, smul_eq_mul] using hge
    exact (not_lt_of_ge hle0) hpos
  have hc : (rho⁻¹ : ℝ) ^ n ≠ 0 := pow_ne_zero n (inv_ne_zero (ne_of_gt hrho))
  unfold superharmonicOrbit
  intro hz
  rcases smul_eq_zero.mp hz with hc0 | h0
  · exact hc hc0
  · exact hTn_ne h0

/-- The orbit is pointwise nondecreasing: `orbitₙ ≤ orbitₙ₊₁`. -/
theorem superharmonicOrbit_mono {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T)
    {rho : ℝ} (hrho : 0 < rho) {w : C(X, ℝ)} (hw : w ∈ positiveCone)
    (hdom : T w ≥ rho • w) : ∀ n : ℕ,
    superharmonicOrbit T rho w n ≤ superharmonicOrbit T rho w (n + 1) := by
  intro n
  rw [ContinuousMap.le_def]
  intro x
  unfold superharmonicOrbit
  have hstep : rho * ((T ^ n) w) x ≤ ((T ^ (n + 1)) w) x := by
    have hle : rho • ((T ^ n) w) ≤ (T ^ (n + 1)) w := by
      have hmono := IsPositive.monotone (IsPositive.pow hT n) hdom
      have hTkm : (T ^ n) (rho • w) = rho • ((T ^ n) w) := by
        simpa using map_smul (T ^ n) rho w
      have hTkT : (T ^ n) (T w) = (T ^ (n + 1)) w := by
        rw [pow_succ]
        rfl
      rw [← hTkT, ← hTkm]
      exact hmono
    exact (ContinuousMap.le_def.mp hle) x
  have hfac : (rho⁻¹ : ℝ) ^ (n + 1) * rho = (rho⁻¹ : ℝ) ^ n := by
    rw [pow_succ]
    calc
      ((rho⁻¹ : ℝ) ^ n * rho⁻¹) * rho = (rho⁻¹ : ℝ) ^ n * (rho⁻¹ * rho) := by ring
      _ = (rho⁻¹ : ℝ) ^ n * 1 := by rw [inv_mul_cancel₀ (ne_of_gt hrho)]
      _ = (rho⁻¹ : ℝ) ^ n := by ring
  have hnonneg : 0 ≤ (rho⁻¹ : ℝ) ^ (n + 1) :=
    pow_nonneg (inv_nonneg.mpr (le_of_lt hrho)) (n + 1)
  calc
    (rho⁻¹ : ℝ) ^ n * ((T ^ n) w) x =
        (rho⁻¹ : ℝ) ^ (n + 1) * rho * ((T ^ n) w) x := by rw [hfac]
    _ ≤ (rho⁻¹ : ℝ) ^ (n + 1) * ((T ^ (n + 1)) w) x := by
      rw [mul_assoc]
      exact mul_le_mul_of_nonneg_left hstep hnonneg

/-- A pointwise-nonnegative function majorised by `g` has norm at most `‖g‖`. -/
theorem norm_le_of_nonneg_le {f g : C(X, ℝ)} (hf : 0 ≤ f) (hfg : f ≤ g) : ‖f‖ ≤ ‖g‖ := by
  exact (f.norm_le (norm_nonneg (a := g))).mpr (fun x => by
    calc
      |f x| = f x := by exact abs_of_nonneg (hf x)
      _ ≤ g x := hfg x
      _ ≤ ‖g‖ := ContinuousMap.apply_le_norm g x)

/-- **Bounded orbit from an eigenvector**: if the starting vector `w` is
pointwise dominated by a positive eigenvector `v` (`T v = ρ · v`, `v ≥ 0`)
then the whole orbit of `w` is norm-bounded.  This is the mechanism by which
an eigenvector in the cone stabilises the orbit: `orbitₙ ≤ v` for all `n`,
so `‖orbitₙ‖ ≤ ‖v‖`. -/
theorem orbit_bounded {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hT : IsPositive T) {rho : ℝ}
    (hrho : 0 < rho) {w v : C(X, ℝ)} (hw : w ∈ positiveCone) (hv : v ∈ positiveCone)
    (hdom : T w ≥ rho • w) (hle : w ≤ v) (hTw_v : T v = rho • v) :
    ∃ C : ℝ, ∀ n : ℕ, ‖superharmonicOrbit T rho w n‖ ≤ C := by
  refine ⟨‖v‖, ?_⟩
  intro n
  have hTnv : (T ^ n) v = (rho : ℝ) ^ n • v := by
    induction n with
    | zero => simp
    | succ k ih =>
        calc
          (T ^ (k + 1)) v = T ((T ^ k) v) := by
            rw [pow_succ']
            rfl
          _ = T ((rho : ℝ) ^ k • v) := by rw [ih]
          _ = (rho : ℝ) ^ k • T v := by
            simpa using map_smul T ((rho : ℝ) ^ k) v
          _ = (rho : ℝ) ^ k • (rho • v) := by rw [hTw_v]
          _ = (rho : ℝ) ^ (k + 1) • v := by
            rw [pow_succ, smul_smul]
  have hmono : (T ^ n) w ≤ (T ^ n) v := IsPositive.monotone (IsPositive.pow hT n) hle
  have hsmul_le : ((rho⁻¹ : ℝ) ^ n) • ((T ^ n) w) ≤ ((rho⁻¹ : ℝ) ^ n) • ((T ^ n) v) := by
    rw [ContinuousMap.le_def]
    intro x
    exact mul_le_mul_of_nonneg_left ((ContinuousMap.le_def.mp hmono) x)
      (pow_nonneg (inv_nonneg.mpr (le_of_lt hrho)) n)
  have hnormal : ((rho⁻¹ : ℝ) ^ n) • ((rho : ℝ) ^ n • v) = v := by
    rw [smul_smul]
    rw [← mul_pow]
    rw [inv_mul_cancel₀ (ne_of_gt hrho)]
    simp
  have hole : superharmonicOrbit T rho w n ≤ v := by
    calc
      superharmonicOrbit T rho w n = ((rho⁻¹ : ℝ) ^ n) • ((T ^ n) w) := rfl
      _ ≤ ((rho⁻¹ : ℝ) ^ n) • ((T ^ n) v) := hsmul_le
      _ = ((rho⁻¹ : ℝ) ^ n) • ((rho : ℝ) ^ n • v) := by rw [hTnv]
      _ = v := hnormal
  have h0 : 0 ≤ superharmonicOrbit T rho w n := by
    rw [ContinuousMap.le_def]
    intro x
    exact (superharmonicOrbit_mem hT hrho hw hdom n) x
  exact norm_le_of_nonneg_le h0 hole

/-- **Bounded superharmonic orbit yields a positive eigenvector.**

If the orbit `orbitₙ = ρ⁻ⁿ Tⁿ w` of a nonzero cone vector `w` satisfying
`T w ≥ ρ · w` is norm-bounded and `T` is a compact, positive operator, then
`T` has a nonzero eigenvector `f` in the cone at eigenvalue `ρ`.

*Proof.*  `Aₙ := T orbitₙ = ρ · orbitₙ₊₁` is a sequence lying in the
relatively compact set `T (closedBall 0 R)` (compactness of `T`), so
Bolzano–Weierstrass gives a subsequence `A (φ k) → a`.  Then
`u k := orbit (φ k + 1) → f := ρ⁻¹ a`.  The orbit is pointwise increasing,
and every `orbit n` is majorised by `f` (a closed-set/`Ici` argument), from
which we read off that in fact the *whole* orbit converges to `f`.  Then `f`
lies in the closed cone, is nonzero (it sits above the nonzero `w`), and
passing the navigation identity `T orbitₙ = ρ · orbitₙ₊₁` through the limit
gives `T f = ρ · f` by continuity of `T`. -/
theorem bounded_orbit_yields_positive_eigenvector {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) (hTcomp : IsCompactOperator T) {rho : ℝ} (hrho : 0 < rho)
    {w : C(X, ℝ)} (hw0 : w ≠ 0) (hw : w ∈ positiveCone) (hdom : T w ≥ rho • w)
    (hbound : ∃ C : ℝ, ∀ n : ℕ, ‖superharmonicOrbit T rho w n‖ ≤ C) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧ T f = rho • f := by
  let orb : ℕ → C(X, ℝ) := fun n => superharmonicOrbit T rho w n
  let A : ℕ → C(X, ℝ) := fun n => T (orb n)
  have hnav : ∀ n : ℕ, A n = rho • orb (n + 1) := by
    intro n
    dsimp [A, orb]
    exact superharmonicOrbit_navigation (ne_of_gt hrho) n
  -- bound the orbit, take R ≥ 0 into which the whole orbit fits
  obtain ⟨C₁, hC₁⟩ := hbound
  let R : ℝ := max C₁ 0
  have horbR : ∀ n : ℕ, ‖orb n‖ ≤ R := fun n => le_trans (hC₁ n) (le_max_left C₁ 0)
  -- {A n} lives (up to closure) in a compact set: T (closedBall 0 R)
  have hK : IsCompact (closure (T '' Metric.closedBall 0 R)) :=
    hTcomp.isCompact_closure_image_closedBall R
  have hAinK : ∀ n : ℕ, A n ∈ closure (T '' Metric.closedBall 0 R) := by
    intro n
    exact subset_closure (mem_image_of_mem T (by
      simpa [Metric.mem_closedBall, dist_eq_norm, orb] using horbR n))
  -- Bolzano–Weierstrass
  obtain ⟨a, _haK, φ, hφmono, hAφ⟩ := IsCompact.tendsto_subseq hK hAinK
  -- candidate eigenvector
  let f : C(X, ℝ) := (rho⁻¹ : ℝ) • a
  let u : ℕ → C(X, ℝ) := fun k => orb (φ k + 1)
  -- rho • u → a: the navigation identity transfers the limit of A ∘ φ
  have hru : Tendsto (fun k : ℕ => rho • u k) atTop (nhds a) := by
    have hAφu : (fun k : ℕ => rho • u k) = A ∘ φ := by
      funext k
      exact (hnav (φ k)).symm
    simpa [hAφu] using hAφ
  -- u → f (via scalar stabilisation: (ρ⁻¹ ) • (ρ • u) = u)
  have huf : Tendsto u atTop (nhds f) := by
    have h₁ : Tendsto (fun k : ℕ => (rho⁻¹ : ℝ) • (rho • u k)) atTop
        (nhds ((rho⁻¹ : ℝ) • a)) :=
      hru.const_smul (rho⁻¹ : ℝ)
    have hsim : (fun k : ℕ => (rho⁻¹ : ℝ) • (rho • u k)) = u := by
      funext k
      rw [smul_smul]
      rw [inv_mul_cancel₀ (ne_of_gt hrho), one_smul]
    have hf : f = (rho⁻¹ : ℝ) • a := rfl
    simpa [hsim, hf] using h₁
  -- orbit is pointwise increasing
  have hstep_mono : ∀ k : ℕ, orb k ≤ orb (k + 1) := fun k => by
    simpa [orb] using superharmonicOrbit_mono hTpos hrho hw hdom k
  have horb_mono : ∀ {n m : ℕ}, n ≤ m → orb n ≤ orb m := by
    intro n m hnm
    induction m with
    | zero =>
        have : n = 0 := Nat.eq_zero_of_le_zero hnm
        subst n
        rfl
    | succ k ih =>
        by_cases hlt : n ≤ k
        · exact le_trans (ih hlt) (hstep_mono k)
        · have hnk : n = k + 1 := by omega
          subst n
          rfl
  -- φ is a strict subsequence, so φ k ≥ k
  have hφge : ∀ k : ℕ, k ≤ φ k := by
    intro k
    induction k with
    | zero => simp
    | succ k ih =>
        exact Nat.succ_le_of_lt (lt_of_le_of_lt ih (hφmono (Nat.lt_succ_self k)))
  -- every orbit term is majorised by f (pointwise, via the closed cone)
  have hdomALL : ∀ n : ℕ, orb n ≤ f := by
    intro n
    rw [ContinuousMap.le_def]
    intro x
    have hev : ∀ᶠ k : ℕ in atTop, n ≤ φ k + 1 := by
      refine (Filter.eventually_ge_atTop n).mono ?_
      intro k hk
      have hk2 : k ≤ φ k := hφge k
      omega
    have hmemALL : ∀ᶠ k : ℕ in atTop, u k - orb n ∈ positiveCone := by
      refine hev.mono ?_
      intro k hk
      rw [mem_positiveCone]
      intro y
      exact sub_nonneg.mpr (horb_mono hk y)
    have hseq : Tendsto (fun k : ℕ => u k - orb n) atTop (𝓝 (f - orb n)) :=
      huf.sub tendsto_const_nhds
    have hlim : f - orb n ∈ positiveCone :=
      isClosed_positiveCone.mem_of_tendsto hseq hmemALL
    exact sub_nonneg.mp (hlim x)
  -- the whole orbit converges to f (in norm)
  have hglob : Tendsto orb atTop (nhds f) := by
    rw [Metric.tendsto_nhds]
    intro ε hε
    have hε2 : 0 < ε / 2 := by positivity
    have huε : ∀ᶠ k : ℕ in atTop, ‖u k - f‖ < ε / 2 := by
      have hm := (Metric.tendsto_nhds.mp huf) (ε / 2) hε2
      refine hm.mono ?_
      intro k hk
      simpa [dist_eq_norm] using hk
    obtain ⟨k₀, hk₀⟩ := huε.exists
    rw [Filter.eventually_atTop]
    refine ⟨φ k₀ + 1, ?_⟩
    intro n hn
    have hle : ‖f - orb n‖ ≤ ‖u k₀ - f‖ := by
      have hle0 : 0 ≤ f - orb n := by
        rw [ContinuousMap.le_def]
        intro x
        exact sub_nonneg.mpr ((hdomALL n) x)
      have hle1 : f - orb n ≤ f - orb (φ k₀ + 1) := by
        rw [ContinuousMap.le_def]
        intro x
        exact sub_le_sub_left (horb_mono hn x) (f x)
      have himpl : ‖f - orb n‖ ≤ ‖f - orb (φ k₀ + 1)‖ := norm_le_of_nonneg_le hle0 hle1
      calc
        ‖f - orb n‖ ≤ ‖f - orb (φ k₀ + 1)‖ := himpl
        _ ≤ ‖f - u k₀‖ := le_of_eq rfl
        _ = ‖u k₀ - f‖ := by
          rw [← neg_sub (f) (u k₀)]
          rw [norm_neg]
    have hlt : ‖f - orb n‖ < ε := by
      linarith [hle, hk₀, hε]
    rw [dist_eq_norm]
    rw [← neg_sub (f) (orb n)]
    rw [norm_neg]
    exact hlt
  -- f is in the closed cone
  have hfcone : f ∈ positiveCone := by
    have huc : ∀ k : ℕ, u k ∈ positiveCone := fun k => by
      dsimp [u]
      exact superharmonicOrbit_mem hTpos hrho hw hdom (φ k + 1)
    exact isClosed_positiveCone.mem_of_tendsto huf (Eventually.of_forall huc)
  -- f ≠ 0
  have hfne0 : f ≠ 0 := by
    have hpen : ∃ x0 : X, 0 < w x0 := by
      by_contra h
      apply hw0
      ext x
      have hle : w x ≤ 0 := le_of_not_gt (fun hgt => h ⟨x, hgt⟩)
      simpa using (le_antisymm hle (hw x))
    obtain ⟨x0, hx0⟩ := hpen
    have hwx : w x0 ≤ f x0 := by
      have horb0 : orb 0 = w := by
        dsimp [orb, superharmonicOrbit]
        simp
      have hof : w ≤ f := by
        simpa [horb0] using hdomALL 0
      exact hof x0
    have hfx : 0 < f x0 := lt_of_lt_of_le hx0 hwx
    intro hz
    have : 0 < f x0 := hfx
    rw [hz] at this
    simpa using this
  -- T f = rho • f : pass the navigation identity through the limit
  have hTf : T f = rho • f := by
    have ht1 : Tendsto (fun n : ℕ => T (orb n)) atTop (nhds (T f)) :=
      (T.continuous.tendsto f).comp hglob
    have ht2 : Tendsto (fun n : ℕ => T (orb n)) atTop (nhds (rho • f)) := by
      have hshift : Tendsto (fun n : ℕ => orb (n + 1)) atTop (nhds f) :=
        hglob.comp (tendsto_add_atTop_nat 1)
      have hrshift : Tendsto (fun n : ℕ => rho • orb (n + 1)) atTop (nhds (rho • f)) :=
        hshift.const_smul rho
      have hnavA : (fun n : ℕ => T (orb n)) = fun n : ℕ => rho • orb (n + 1) := by
        funext n
        exact hnav n
      simpa [hnavA] using hrshift
    exact tendsto_nhds_unique ht1 ht2
  exact ⟨f, hfcone, hfne0, hTf⟩

end

end Riemann
