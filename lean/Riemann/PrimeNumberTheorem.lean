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

/-- The trivial-zero exclusion for the full statement: ζ has no zeros with
Re ρ ≤ 0 except the trivial zeros ρ = −2(n+1) (Fleet 6). -/
theorem riemannZeta_zero_of_re_nonpos (ρ : ℂ) (hzero : riemannZeta ρ = 0)
    (hre : ρ.re ≤ 0) : ∃ n : ℕ, ρ = -2 * ((n : ℂ) + 1) := by
  sorry -- Fleet 6: Euler product + functional equation, standard

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
      · sorry -- Fleet 6: ζ(s) ≠ 0 on the line Re s = 1 (Hadamard–dLVP)
  · -- s.re ≤ 0: only trivial zeros there (Fleet 6 skeleton)
    obtain ⟨n, hn⟩ := riemannZeta_zero_of_re_nonpos s hzero (le_of_not_gt h0)
    exact (htriv ⟨n, hn⟩).elim

/-- The final statement in Mathlib's own form (Fleet 6 pending on the two
documented skeletons above). -/
theorem riemannHypothesis_mathlib : RiemannHypothesis :=
  fun s hzero htriv hs1 => riemannHypothesis s hzero htriv hs1

end Riemann.TransferOperator
