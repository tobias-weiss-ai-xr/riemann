import Riemann.KreinRutman
import Riemann.RealGelfand

open scoped ContinuousMap ENNReal NNReal Topology
open Filter
open Set

namespace Riemann

noncomputable section

set_option maxHeartbeats 5000000

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [Nonempty X]

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

/-- **Bounded orbit estimate**: by the real Gelfand formula
(`Riemann.RealGelfand.realGelfandFormula`), for every `eps > 0` there is a constant
`C > 0` such that `‖T^n‖ ≤ C * ((spectralRadius ℝ T).toReal + eps) ^ n` for all `n`.
This is the bounded-orbit estimate on which the whole resolvent-positivity route at the
spectral radius rests. -/
theorem eventually_pow_norm_le {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (eps : ℝ) (heps : 0 < eps) :
    ∃ C : ℝ, 0 < C ∧ ∀ n : ℕ, ‖T ^ n‖ ≤ C * ((spectralRadius ℝ T).toReal + eps) ^ n := by
  have hg : Tendsto (fun n : ℕ => (‖T ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ))) atTop
      (𝓝 (spectralRadius ℝ T)) := by
    simpa using (realGelfandFormula (a := T))
  exact eventually_pow_norm_le_of_gelfand hg heps



/-- **Neumann (geometric) series identity for the resolvent at the spectral
radius**: whenever `0 < lam` and the spectral radius satisfies
`(spectralRadius ℝ T).toReal < lam`, the resolvent `(lam • 1 - T)⁻¹` equals the
convergent geometric series `Σₙ (lam⁻¹)ⁿ⁺¹ · Tⁿ`, i.e. `Tⁿ / lamⁿ⁺¹` in the scalar
sense.  The convergence (at `lam` strictly above `ρ(T)`, not just above `‖T‖`) rests
on the bounded-orbit estimate `eventually_pow_norm_le` (a corollary of the real
Gelfand formula `Riemann.RealGelfand.realGelfandFormula`). -/
theorem resolvent_neumann_series_at_radius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} {lam : ℝ}
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
    eventually_pow_norm_le (T := T) eps (by simpa [eps] using heps)
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

/-- **Resolvent positivity at the spectral radius**: if `T` is a positive operator,
`0 < lam` and `(spectralRadius ℝ T).toReal < lam`, then the resolvent
`Ring.inverse (lam • 1 - T)` is well-defined (its Neumann series
`resolvent_neumann_series_at_radius` converges above `ρ(T)`, not just above `‖T‖`)
and is itself a positive operator.  This is the positivity half of the
Krein–Rutman strategy beyond the operator norm: resolvents of positive operators at
positive levels outside the spectrum are positive. -/
theorem resolvent_positivity_at_radius {T : C(X, ℝ) →L[ℝ] C(X, ℝ)}
    (hTpos : IsPositive T) {lam : ℝ} (hlam : 0 < lam)
    (hrho : (spectralRadius ℝ T).toReal < lam) :
    IsPositive (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) := by
  -- the Neumann series converges at the radius and equals the inverse
  have hsum : HasSum (fun n : ℕ => (lam⁻¹ : ℝ) ^ (n + 1) • T ^ n)
      (Ring.inverse (lam • (1 : C(X, ℝ) →L[ℝ] C(X, ℝ)) - T)) :=
    resolvent_neumann_series_at_radius (T := T) hlam hrho
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

end

end Riemann
