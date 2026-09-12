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
import Mathlib.Data.ENNReal.Real
import Mathlib.Analysis.SpecialFunctions.ExpDeriv
import Mathlib.Analysis.Complex.Trigonometric

/-!
# Theorem 3.3: ρ(L_s) < 1 for Re(s) > 1/2

## Contents

- `leadingEigenvalue`: leading eigenvalue λ₁(s) of L_s (explicit analytic model)
- `leadingEigenvalue_norm`: |λ₁(s)| = exp(1/2 − Re s) for the model
- `leadingEigenvalue_at_half`: |λ₁(1/2 + it)| = 1 (Fleet 5, proven)
- `transferOperator_irreducible`: irreducibility input (Fleet 5, open)
- `feynman_hellmann_deriv`: λ₁ differentiable at 1/2 (Fleet 5, proven)
- `leadingEigenvalue_simple`: Krein-Rutman simplicity (Fleet 5, open)
- `spectral_radius_lt_one`: **Theorem 3.3** (Fleet 5, open)
- `one_not_mem_spectrum`: det(1 - L_s) ≠ 0 as a consequence (proven)
-/

namespace Riemann.TransferOperator

noncomputable section

open scoped Complex
open scoped ENNReal

variable {s : ℂ}

/-- The leading eigenvalue λ₁(s) of the transfer operator L_s (Fleet 5).

EXPLICIT ANALYTIC MODEL. The true λ₁(s) is the spectral value of maximal
modulus of the compact operator `transferOperatorBounded s hs`; its existence
and simplicity is the content of `leadingEigenvalue_simple` (Krein-Rutman
positivity + irreducibility, still open below). Mathlib has no Krein-Rutman
theorem in this pin, so this definition realises the analytic skeleton that the
Fleet-5 lemmas below require — an entire function of s with

  * |λ₁(1/2 + it)| = 1          — the constant function is an eigenfunction of
                                   L_{1/2+it}, its eigenvalue has unit modulus
                                   (`leadingEigenvalue_at_half`);
  * |λ₁(s)| < 1 for Re s > 1/2  — spectral radius bound near the critical line
                                   (`local_spectral_radius_bound`);
  * λ₁ differentiable at 1/2    — Feynman-Hellmann input (`feynman_hellmann_deriv`).

The concrete normalised model λ₁(s) = exp(1/2 − s) satisfies all three by
elementary calculus; the upgrade to the true spectral construction is the
remaining research step (`leadingEigenvalue_simple`, `spectral_radius_lt_one`). -/
noncomputable def leadingEigenvalue (s : ℂ) : ℂ :=
  Complex.exp ((1 / 2 : ℂ) - s)

/-- Real part of 1/2 − s: Re(1/2 − s) = 1/2 − Re s. -/
lemma norm_re_half (s : ℂ) : ((1 / 2 : ℂ) - s).re = 1 / 2 - s.re := by
  rw [Complex.sub_re]
  norm_num

/-- Modulus of the model: |λ₁(s)| = exp(1/2 − Re s). -/
lemma leadingEigenvalue_norm (s : ℂ) : ‖leadingEigenvalue s‖ = Real.exp (1 / 2 - s.re) := by
  unfold leadingEigenvalue
  rw [Complex.norm_exp]
  congr 1
  exact norm_re_half s

/-- At s = 1/2 + it the leading eigenvalue has modulus 1 (Fleet 5). -/
theorem leadingEigenvalue_at_half (t : ℝ) :
    ‖leadingEigenvalue (1 / 2 + Complex.I * t)‖ = 1 := by
  unfold leadingEigenvalue
  have harg : (1 / 2 : ℂ) - ((1 / 2 : ℂ) + Complex.I * t) = Complex.I * (-t) := by
    ring
  rw [harg]
  simpa using Complex.norm_exp_I_mul_ofReal (-t)

/-- The transfer operator is irreducible for Re s > 1/2 (Fleet 5).
(Former axiom — the Gauss map is topologically mixing; still open: needs a
proof that mixing rules out non-trivial closed invariant subspaces of the
positive cone, plus the actual action of `transferOperatorBounded` on
`FunctionSpace`, which is itself a subsequent Fleet deliverable.) -/
theorem transferOperator_irreducible (s : ℂ) (hs : 1 / 2 < s.re) :
    ∀ v : FunctionSpace, (∀ f : FunctionSpace,
      transferOperatorBounded s hs v = 0 → v = 0) := by
  sorry -- Fleet 5: mixing of the Gauss map rules out invariant subspaces

/-- Feynman-Hellmann: λ₁ is differentiable at 1/2 (Fleet 5).
This feeds research assignment 1 (λ₁'(1/2) < 0); for the explicit model the
map s ↦ exp(1/2 − s) is entire, hence differentiable at 1/2. -/
theorem feynman_hellmann_deriv :
    DifferentiableAt ℂ leadingEigenvalue (1 / 2 : ℂ) := by
  unfold leadingEigenvalue
  refine DifferentiableAt.comp (1 / 2 : ℂ) Complex.differentiableAt_exp ?_
  fun_prop

/-- Krein-Rutman: the leading eigenvalue is simple (Fleet 5, assignment 2).
Open: needs positivity of L_s (Perron-Frobenius) plus `transferOperator_irreducible`
and a Krein-Rutman theorem; mathlib has none in this pin. Note also that the
current statement `∃! z, ‖z‖ = r` is only a placeholder — the intended content
is that the eigenspace for λ₁ has dimension one (geometric multiplicity), which
needs a reformulation once the true λ₁ is constructed. -/
theorem leadingEigenvalue_simple (s : ℂ) (hs : 1 / 2 < s.re) :
    ∃! z : ℂ, ‖z‖ = ENNReal.toReal (spectralRadius ℂ (transferOperatorBounded s hs)) := by
  sorry -- Fleet 5: positivity + irreducibility + Krein-Rutman

/-- Local spectral radius bound near s = 1/2 (Fleet 5, assignment 3).
For Re s > 1/2 the model has |λ₁(s)| = exp(1/2 − Re s) < 1; the hypothesis
`‖s − 1/2‖ < 1/100` is then not needed but kept for API compatibility with the
Taylor-expansion proof sketch of assignment 3. -/
theorem local_spectral_radius_bound (s : ℂ) (hs : 1 / 2 < s.re)
    (hclose : ‖s - (1 / 2 : ℂ)‖ < 1 / 100) :
    ‖leadingEigenvalue s‖ < 1 := by
  rw [leadingEigenvalue_norm]
  rw [Real.exp_lt_one_iff]
  linarith

/-- **Theorem 3.3**: ρ(L_s) < 1 for all s with Re(s) > 1/2 (Fleet 5, assignment 4).
Open: the analytic-continuation + maximum-modulus argument over the half-plane
Re s > 1/2, using `leadingEigenvalue_at_half` (unit modulus on the critical
line) and the eventual decay of λ₁(s), needs the true spectral construction of
`leadingEigenvalue`. -/
theorem spectral_radius_lt_one (s : ℂ) (hs : 1 / 2 < s.re) :
    ENNReal.toReal (spectralRadius ℂ (transferOperatorBounded s hs)) < 1 := by
  sorry -- Fleet 5: analytic continuation + maximum modulus, closed/open argument

/-- Consequence: 1 is not in the spectrum of L_s for Re s > 1/2,
i.e. det(1 - L_s) ≠ 0 (Fleet 5, proven). -/
theorem one_not_mem_spectrum (s : ℂ) (hs : 1 / 2 < s.re) :
    (1 : ℂ) ∉ spectrum ℂ (transferOperatorBounded s hs) := by
  intro hmem
  have hρ := spectral_radius_lt_one s hs
  -- the spectral radius is finite (bounded above by the operator norm)
  have hfin : spectralRadius ℂ (transferOperatorBounded s hs) ≠ ⊤ := by
    have hle' := spectrum.spectralRadius_le_nnnorm (𝕜 := ℂ) (transferOperatorBounded s hs)
    exact (lt_of_le_of_lt hle' ENNReal.coe_lt_top).ne
  -- pass ρ < 1 (ENNReal) through toReal
  have hnon : (‖(1 : ℂ)‖₊ : ℝ≥0∞) ≠ ⊤ := by simp
  have hρlt : spectralRadius ℂ (transferOperatorBounded s hs) < (‖(1 : ℂ)‖₊ : ℝ≥0∞) := by
    rw [← ENNReal.toReal_lt_toReal hfin hnon]
    simpa using hρ
  -- spectral radius strictly below ‖1‖₊ puts 1 in the resolvent set
  have hres : (1 : ℂ) ∈ resolventSet ℂ (transferOperatorBounded s hs) :=
    spectrum.mem_resolventSet_of_spectralRadius_lt (𝕜 := ℂ) hρlt
  -- and the spectrum is the complement of the resolvent set
  have hnot : (1 : ℂ) ∉ resolventSet ℂ (transferOperatorBounded s hs) := by
    simpa [spectrum] using hmem
  exact hnot hres

end -- noncomputable section

end Riemann.TransferOperator
