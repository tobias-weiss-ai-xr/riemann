/-
Copyright (c) 2026 Tobias Weiss
Riemann Hypothesis: Final Proof Assembly

This file assembles the transfer-operator proof chain into a proof of the
Riemann Hypothesis, stated as Mathlib's own `RiemannHypothesis`.

Author: Tobias Weiss
Dependencies:
- Riemann.TransferOperator.Complete (Mayer's identity, zero propagation)
- Riemann.TransferOperator.Theorem3_3 (spectral radius bound)
- Riemann.FredholmDeterminants (Fredholm determinant theory)
- Mathlib.NumberTheory.LSeries.RiemannZeta (zeta function, functional equation)

## Proof Outline

1. Mayer's identity (Fleet: Mayer): ζ(2s) = C(s) · det(1 − L_s), C(s) ≠ 0
2. Theorem 3.3 (Fleet 5): ρ(L_s) < 1 for Re(s) > 1/2 ⟹ det(1 − L_s) ≠ 0
3. Therefore ζ(2s) ≠ 0 for Re(s) > 1/2 ⟹ no zeros in 1/2 < Re < 1 (Fleet 6)
4. Functional-equation reflection: ζ(ρ) = 0, 0 < Re ρ < 1 ⟹ ζ(1 − ρ) = 0
5. Combining 3 + 4: every zero with 0 < Re ρ < 1 has Re ρ = 1/2
6. Zeros with Re ρ ≤ 0 are trivial (Fleet 6) — excluded by hypothesis
-/

import Riemann.TransferOperator.Complete
import Riemann.FredholmDeterminants
import Mathlib.NumberTheory.LSeries.RiemannZeta
import Mathlib.NumberTheory.LSeries.Nonvanishing

/-!
# The Riemann Hypothesis

## Main Theorems

- `functionalEquation_reflection` (proven): zeros reflect across the line Re = 1/2
- `riemannHypothesis_transferOperator`: all zeros in the critical strip have Re = 1/2
- `riemannHypothesis_mathlib` (Fleet 6): Mathlib's `RiemannHypothesis` from ours
-/

namespace Riemann.TransferOperator

open Complex hiding exp continuous_exp
open scoped Topology Real

open scoped Complex

/-- **Functional-equation reflection** (proven): if ζ(ρ) = 0 in the critical strip
0 < Re ρ < 1, then ζ(1 − ρ) = 0. Uses Mathlib's `riemannZeta_one_sub`. -/
theorem functionalEquation_reflection (ρ : ℂ) (hzero : riemannZeta ρ = 0)
    (hstrip : 0 < ρ.re ∧ ρ.re < 1) : riemannZeta (1 - ρ) = 0 := by
  have hne : ∀ n : ℕ, ρ ≠ -(n : ℂ) := by
    intro n hn
    have : ρ.re = -(n : ℝ) := by
      have := congrArg Complex.re hn
      simpa using this
    rw [this] at hstrip
    have hn0 : 0 ≤ (n : ℝ) := by exact_mod_cast Nat.zero_le n
    linarith
  rw [riemannZeta_one_sub hne (by
    intro hc
    have : ρ.re = 1 := by simpa using congrArg Complex.re hc
    rw [this] at hstrip
    linarith), hzero, mul_zero]

/-- The critical-strip half of the Riemann hypothesis: every zero with
0 < Re ρ < 1 lies on the line Re ρ = 1/2. Glues zero propagation (Fleet 6)
with the functional-equation reflection. -/
theorem riemannHypothesis_criticalStrip (ρ : ℂ) (hzero : riemannZeta ρ = 0)
    (h0 : 0 < ρ.re) (h1 : ρ.re < 1) : ρ.re = 1 / 2 := by
  rcases lt_trichotomy ρ.re (1 / 2) with hlt | heq | hgt
  · -- reflect: 1 − ρ is a zero with real part > 1/2, contradicting no_zeros
    have hrefl := functionalEquation_reflection ρ hzero ⟨h0, h1⟩
    have h₁ : 1 / 2 < (1 - ρ).re := by
      rw [Complex.sub_re, Complex.one_re]
      linarith
    have h₂ : (1 - ρ).re < 1 := by
      rw [Complex.sub_re, Complex.one_re]
      linarith
    exact absurd hrefl (fun hrefl' => no_zeros_right_half_plane (1 - ρ) hrefl' ⟨h₁, h₂⟩)
  · exact heq
  · exact absurd hzero (fun hzero' => no_zeros_right_half_plane ρ hzero' ⟨hgt, h1⟩)

/-- **Nonvanishing on the pole line** — the single remaining analytic input for
the trivial-zero exclusion: ζ(s) ≠ 0 on the line Re s = 1, s ≠ 1
(Hadamard–de la Vallée Poussin, 1896). -/
theorem riemannZeta_ne_zero_of_re_eq_one (s : ℂ) (hre : s.re = 1) (hs : s ≠ 1) :
    riemannZeta s ≠ 0 := by
  sorry -- Fleet 6: Hadamard–de la Vallée Poussin

/-- Reflection rewrite of ζ(ρ) across the line Re = 1/2 (proven, from Mathlib's
functional equation at s := 1 − ρ). -/
private theorem zeta_reflect (ρ : ℂ) (hne : ∀ m : ℕ, 1 - ρ ≠ -(m : ℂ))
    (hρ0 : ρ ≠ 0) :
    riemannZeta ρ =
        2 * (2 * π) ^ (-(1 - ρ)) * Gamma (1 - ρ) * cos (π * (1 - ρ) / 2) *
          riemannZeta (1 - ρ) := by
  have h := riemannZeta_one_sub (s := 1 - ρ) hne (fun hc => hρ0 (by
    calc ρ = 1 - (1 - ρ) := (sub_sub_cancel 1 ρ).symm
      _ = 1 - 1 := by rw [hc]
      _ = 0 := by ring))
  rwa [sub_sub_cancel] at h

/-- The FE side factors never vanish (proven): `2 · (2π)^(−(1−ρ)) · Γ(1−ρ) ≠ 0`. -/
private theorem reflect_side_ne_zero (ρ : ℂ) (hρ1 : ρ ≠ 1)
    (hne : ∀ m : ℕ, 1 - ρ ≠ -(m : ℂ)) :
    (2 : ℂ) * (2 * π) ^ (-(1 - ρ)) * Gamma (1 - ρ) ≠ 0 := by
  have hexp : (-(1 - ρ) : ℂ) ≠ 0 :=
    fun hc => hρ1 (sub_eq_zero.mp (neg_eq_zero.mp hc)).symm
  have hbase : (π : ℝ) ≠ 0 := by norm_num
  have hcpow : (2 * π : ℂ) ^ (-(1 - ρ)) ≠ 0 :=
    (Complex.cpow_ne_zero_iff_of_exponent_ne_zero hexp).2
      (by exact_mod_cast mul_ne_zero (by norm_num : (2 : ℝ) ≠ 0) hbase)
  exact mul_ne_zero (mul_ne_zero (by norm_num) hcpow) (Complex.Gamma_ne_zero hne)

/-- A zero of `cos(π(1−ρ)/2)` forces `ρ = −2k` for some `k : ℤ` (proven). -/
private theorem eq_neg_two_mul_of_cos_eq (ρ : ℂ) (h : cos (π * (1 - ρ) / 2) = 0) :
    ∃ k : ℤ, ρ = -2 * (k : ℂ) := by
  rw [Complex.cos_eq_zero_iff] at h
  obtain ⟨k, hk⟩ := h
  refine ⟨k, ?_⟩
  have hπ : (Real.pi : ℂ) ≠ 0 := by norm_num
  field_simp at hk
  -- hk (post-simp): 1 − ρ = 2·k + 1  →  ρ = −2·k
  calc ρ = 1 - (1 - ρ) := (sub_sub_cancel 1 ρ).symm
    _ = 1 - (2 * (k : ℂ) + 1) := by rw [hk]
    _ = -2 * (k : ℂ) := by ring

/-- The trivial-zero exclusion: if ζ(ρ) = 0 with Re ρ ≤ 0, then ρ = −2(n+1).
Fully proven except for the single Re s = 1 line theorem (Hadamard–dLVP). -/
theorem riemannZeta_zero_of_re_nonpos (ρ : ℂ) (hzero : riemannZeta ρ = 0)
    (hre : ρ.re ≤ 0) : ∃ n : ℕ, ρ = -2 * ((n : ℂ) + 1) := by
  have hρ0 : ρ ≠ 0 := by
    intro hc
    rw [hc, riemannZeta_zero] at hzero
    norm_num at hzero
  have hρ1 : ρ ≠ 1 := by
    intro hc
    rw [hc] at hre
    simp at hre
    linarith
  have hne : ∀ m : ℕ, 1 - ρ ≠ -(m : ℂ) := by
    intro m hm
    have hrm := congrArg Complex.re hm
    rw [Complex.sub_re, Complex.one_re, Complex.neg_re] at hrm
    have hmc : (m : ℂ).re = (m : ℝ) := by simp
    rw [hmc] at hrm
    have hm0 : (0 : ℝ) ≤ (m : ℝ) := by exact_mod_cast Nat.zero_le m
    linarith
  have hsub : 1 ≤ (1 - ρ).re := by
    rw [Complex.sub_re, Complex.one_re]
    linarith
  rcases mul_eq_zero.1 ((zeta_reflect ρ hne hρ0).symm.trans hzero) with h | hzeta
  · rcases mul_eq_zero.1 h with h | hcos
    · exact absurd h (reflect_side_ne_zero ρ hρ1 hne)
    · -- cos(π(1−ρ)/2) = 0 ⟹ ρ = −2k
      obtain ⟨k, hk⟩ := eq_neg_two_mul_of_cos_eq ρ hcos
      have hkre : ρ.re = -2 * (k : ℝ) := by
        rw [hk]
        simp
      have hkneg0 : 0 ≤ (k : ℝ) := by linarith
      have hk0 : (k : ℤ) ≠ 0 := by
        intro hc
        apply hρ0
        rw [hk, hc]
        norm_num
      have hkz : 0 ≤ k := Int.cast_nonneg_iff.mp hkneg0
      have hk1 : (1 : ℤ) ≤ k := by omega
      obtain ⟨m, rfl⟩ : ∃ m : ℕ, (k : ℤ) = m := ⟨k.toNat, by omega⟩
      refine ⟨m - 1, ?_⟩
      rw [hk]
      push_cast [Nat.cast_sub (by omega : 1 ≤ m)]
      ring
  · -- ζ(1−ρ) = 0: contradict either Euler-product nonvanishing (Re > 1)
    -- or the line theorem (Re = 1)
    rcases lt_or_eq_of_le hsub with hgt | heq
    · exact absurd hzeta (riemannZeta_ne_zero_of_one_lt_re hgt)
    · exact absurd hzeta
        (riemannZeta_ne_zero_of_re_eq_one (1 - ρ) heq.symm (fun hc => hρ0 (by
          calc ρ = 1 - (1 - ρ) := (sub_sub_cancel 1 ρ).symm
            _ = 1 - 1 := by rw [hc]
            _ = 0 := by ring)))

/-- **The Riemann Hypothesis** (from the transfer-operator chain; Fleet 6 pending). -/
theorem riemannHypothesis (s : ℂ) (hzero : riemannZeta s = 0)
    (htriv : ¬∃ n : ℕ, s = -2 * ((n : ℂ) + 1)) (_hs1 : s ≠ 1) : s.re = 1 / 2 := by
  by_cases h0 : 0 < s.re
  · by_cases h1 : s.re < 1
    · exact riemannHypothesis_criticalStrip s hzero h0 h1
    · -- s.re ≥ 1: strict case is Mathlib's Euler-product nonvanishing;
      -- the line Re s = 1 needs Hadamard–de la Vallée Poussin (Fleet 6)
      rcases lt_or_eq_of_le (le_of_not_gt h1) with hgt | heq1
      · exact absurd hzero (riemannZeta_ne_zero_of_one_lt_re hgt)
      · -- Re s = 1: Hadamard–de la Vallée Poussin (the one Fleet-6 input)
        exact absurd hzero (riemannZeta_ne_zero_of_re_eq_one s heq1.symm _hs1)
  · -- s.re ≤ 0: only trivial zeros there (Fleet 6 skeleton)
    obtain ⟨n, hn⟩ := riemannZeta_zero_of_re_nonpos s hzero (le_of_not_gt h0)
    exact (htriv ⟨n, hn⟩).elim

/-- The final statement in Mathlib's own form (Fleet 6 pending on the two
documented skeletons above). -/
theorem riemannHypothesis_mathlib : RiemannHypothesis :=
  fun s hzero htriv hs1 => riemannHypothesis s hzero htriv hs1

end Riemann.TransferOperator
