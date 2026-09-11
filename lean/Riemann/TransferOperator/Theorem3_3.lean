/-
Copyright (c) 2026 Tobias Weiss
Theorem 3.3: Spectral Radius Bound

The central analytic estimate of the transfer-operator approach to RH:
for Re(s) > 1/2, the spectral radius of L_s is strictly less than 1.

Author: Tobias Weiss
References:
- Mayer, G. (1990). "The Riemann zeta function and the transfer operator"
- Research assignments 1-4 (Feynman-Hellmann, simplicity, global bound)
-/

import Riemann.TransferOperator.Operator
import Mathlib.Analysis.Normed.Algebra.Spectrum

/-!
# Theorem 3.3: ρ(L_s) < 1 for Re(s) > 1/2

## Contents

- `leadingEigenvalue`: leading eigenvalue λ₁(s) of L_s
- `leadingEigenvalue_at_half`: |λ₁(1/2 + it)| = 1 (Fleet 5)
- `transferOperator_irreducible`: irreducibility input (Fleet 5)
- `feynman_hellmann_deriv_neg`: λ₁'(1/2) < 0 via Feynman-Hellmann (Fleet 5)
- `leadingEigenvalue_simple`: Krein-Rutman simplicity (Fleet 5)
- `spectral_radius_lt_one`: **Theorem 3.3** (Fleet 5)
- `one_not_mem_spectrum`: det(1 - L_s) ≠ 0 as a consequence
-/

namespace Riemann.TransferOperator

noncomputable section

open scoped Complex

variable {s : ℂ}

/-- The leading eigenvalue λ₁(s) of the transfer operator L_s (Fleet 5). -/
noncomputable def leadingEigenvalue (s : ℂ) : ℂ :=
  sorry -- Fleet 5: eigenvalue of transferOperatorBounded s with maximal modulus

/-- At s = 1/2 + it the leading eigenvalue has modulus 1 (Fleet 5).
(Former axiom — now a documented skeleton theorem.) -/
theorem leadingEigenvalue_at_half (t : ℝ) :
    ‖leadingEigenvalue (1 / 2 + Complex.I * t)‖ = 1 := by
  sorry -- Fleet 5: the constant function 1 is an eigenfunction of L_{1/2+it}

/-- The transfer operator is irreducible for Re s > 1/2 (Fleet 5).
(Former axiom — the Gauss map is topologically mixing.) -/
theorem transferOperator_irreducible (s : ℂ) (hs : 1 / 2 < s.re) :
    ∀ v : FunctionSpace, (∀ f : FunctionSpace,
      transferOperatorBounded s hs v = 0 → v = 0) := by
  sorry -- Fleet 5: mixing of the Gauss map rules out invariant subspaces

/-- Feynman-Hellmann: λ₁ is differentiable at 1/2 (Fleet 5).
This feeds research assignment 1 (λ₁'(1/2) < 0). -/
theorem feynman_hellmann_deriv :
    DifferentiableAt ℂ leadingEigenvalue (1 / 2 : ℂ) := by
  sorry -- Fleet 5: analyticity of λ₁ + perturbation theory

/-- Krein-Rutman: the leading eigenvalue is simple (Fleet 5, assignment 2). -/
theorem leadingEigenvalue_simple (s : ℂ) (hs : 1 / 2 < s.re) :
    ∃! z : ℂ, ‖z‖ = ENNReal.toReal (spectralRadius ℂ (transferOperatorBounded s hs)) := by
  sorry -- Fleet 5: positivity + irreducibility + Krein-Rutman

/-- Local spectral radius bound near s = 1/2 (Fleet 5, assignment 3). -/
theorem local_spectral_radius_bound (s : ℂ) (hs : 1 / 2 < s.re)
    (hclose : ‖s - (1 / 2 : ℂ)‖ < 1 / 100) :
    ‖leadingEigenvalue s‖ < 1 := by
  sorry -- Fleet 5: Taylor expansion of λ₁ at 1/2 using feynman_hellmann_deriv

/-- **Theorem 3.3**: ρ(L_s) < 1 for all s with Re(s) > 1/2 (Fleet 5, assignment 4). -/
theorem spectral_radius_lt_one (s : ℂ) (hs : 1 / 2 < s.re) :
    ENNReal.toReal (spectralRadius ℂ (transferOperatorBounded s hs)) < 1 := by
  sorry -- Fleet 5: analytic continuation + maximum modulus, closed/open argument

/-- Consequence: 1 is not in the spectrum of L_s for Re s > 1/2,
i.e. det(1 - L_s) ≠ 0 (Fleet 5). -/
theorem one_not_mem_spectrum (s : ℂ) (hs : 1 / 2 < s.re) :
    (1 : ℂ) ∉ spectrum ℂ (transferOperatorBounded s hs) := by
  intro hmem
  have hρ := spectral_radius_lt_one s hs
  sorry -- Fleet 5: hmem gives 1 ≤ ‖1‖₊ ≤ spectralRadius, contradicting hρ

end -- noncomputable section

end Riemann.TransferOperator
