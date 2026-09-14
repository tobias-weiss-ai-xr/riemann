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

end

end Riemann
