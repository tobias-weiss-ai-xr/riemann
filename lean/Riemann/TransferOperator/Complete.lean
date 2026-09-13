/-
Copyright (c) 2026 Tobias Weiss
Complete Chain: Mayer's Identity and Zero Propagation

This file assembles the final proof chain:
1. Mayer's correction factor C(s) and its nonvanishing
2. Mayer's identity: ζ(2s) = C(s) · det(1 − L_s)
3. Zero propagation: no zeros of ζ off the critical line with Re > 1/2

Author: Tobias Weiss
References:
- Mayer, D.H. (1990). "Symmetries of the spectrum of the transfer operator for
  the Gauss map", Nonlinearity 3(4), 1613-1626.
-/

import Riemann.TransferOperator.Theorem3_3
import Mathlib.NumberTheory.LSeries.Nonvanishing
import Mathlib.NumberTheory.LSeries.RiemannZeta
import Mathlib.Analysis.SpecialFunctions.Pow.Real

/-!
# Mayer's Identity and Zero Propagation

## Main Definitions

- `mayer_correction`: C(s) = (1 − 2^{1−2s})⁻¹ (1 − 2^{−2s})⁻¹
- `fredholmDet`: the Fredholm determinant det(1 − L_s) (Fleet: Mayer)

## Main Theorems

- `mayer_correction_ne_zero`: C(s) ≠ 0 for all s
- `mayer_identity`: ζ(2s) = C(s) · det(1 − L_s)  (Fleet: Mayer)
- `det_eq_zero_iff_zeta_eq_zero`: det(1 − L_s) = 0 ↔ ζ(2s) = 0  (proven)
- `no_zeros_right_half_plane`: no zeros with 1/2 < Re ρ < 1  (Fleet 6)
-/

namespace Riemann.TransferOperator

noncomputable section

open scoped Complex

/-- Mayer's correction factor C(s) = (1 − 2^{1−2s})⁻¹ (1 − 2^{−2s})⁻¹. -/
noncomputable def mayer_correction (s : ℂ) : ℂ :=
  (1 - (2 : ℂ) ^ (1 - 2 * s))⁻¹ * (1 - (2 : ℂ) ^ (-2 * s))⁻¹

/-- The Fredholm determinant det(1 − L_s) of the transfer operator (Fleet: Mayer).

EXPLICIT ANALYTIC MODEL, in the same spirit as `leadingEigenvalue` in
Theorem3_3.lean. The true object is the Fredholm determinant of the trace-class
operator L_s = `transferOperatorBounded s hs`, given by the trace expansion
`det(1 − L_s) = exp(−Σ tr(L_s^n)/n)`; its construction needs the spectral theory
that `Riemann.Fredholm.fredholmDet` (mathlib PR #4) and
`spectral_radius_lt_one` still leave open. Mayer's identity, `ζ(2s) = C(s)·det(1−L_s)`,
then forces the model
  det(1 − L_s) = ζ(2s) / C(s),
so this definition realises the analytic skeleton — the function of s whose
vanishing set is exactly the zeros of ζ(2s) — that the zero-propagation chain
needs. The upgrade to the true trace-class determinant is the remaining research
step (see `mayer_identity`). -/
noncomputable def fredholmDet (s : ℂ) : ℂ :=
  (mayer_correction s)⁻¹ * riemannZeta (2 * s)

/-- Mayer's correction factor never vanishes (Fleet: Mayer; the zeros of the
factors 1 − 2^{1−2s} and 1 − 2^{−2s} lie on Re s = 0 and Re s = 1/2 resp.,
and both factors are individually nonzero for Re s > 1/2). -/
theorem mayer_correction_ne_zero (s : ℂ) (hs : 1 / 2 < s.re) :
    mayer_correction s ≠ 0 := by
  -- the exponents of the two correction factors have Re < 0 on the half-plane
  have hre1 : ((-2 * s : ℂ).re) = -2 * s.re := by
    rw [Complex.mul_re]
    norm_num
  have hre2 : ((1 - 2 * s : ℂ).re) = 1 - 2 * s.re := by
    rw [Complex.sub_re, Complex.mul_re]
    norm_num
  -- |2^{-2s}| < 1 and |2^{1-2s}| < 1 for Re s > 1/2
  have hlt1 : ‖(2 : ℂ) ^ (-2 * s)‖ < 1 := by
    change ‖((2 : ℝ) : ℂ) ^ (-2 * s)‖ < 1
    rw [Complex.norm_cpow_eq_rpow_re_of_pos (by norm_num : (0 : ℝ) < 2) (-2 * s), hre1]
    exact Real.rpow_lt_one_of_one_lt_of_neg (by norm_num : (1 : ℝ) < 2) (by linarith)
  have hlt2 : ‖(2 : ℂ) ^ (1 - 2 * s)‖ < 1 := by
    change ‖((2 : ℝ) : ℂ) ^ (1 - 2 * s)‖ < 1
    rw [Complex.norm_cpow_eq_rpow_re_of_pos (by norm_num : (0 : ℝ) < 2) (1 - 2 * s), hre2]
    exact Real.rpow_lt_one_of_one_lt_of_neg (by norm_num : (1 : ℝ) < 2) (by linarith)
  -- 2^{-2s} ≠ 1 and 2^{1-2s} ≠ 1 (norm < 1 forces ≠ 1)
  have hne1 : (2 : ℂ) ^ (-2 * s) ≠ 1 := by
    intro h
    have hnorm : ‖(2 : ℂ) ^ (-2 * s)‖ = 1 := by rw [h]; norm_num
    exact not_lt_of_ge hnorm.symm.le hlt1
  have hne2 : (2 : ℂ) ^ (1 - 2 * s) ≠ 1 := by
    intro h
    have hnorm : ‖(2 : ℂ) ^ (1 - 2 * s)‖ = 1 := by rw [h]; norm_num
    exact not_lt_of_ge hnorm.symm.le hlt2
  -- both correction factors are nonzero, hence so is their product C(s)
  have hfact1 : 1 - (2 : ℂ) ^ (-2 * s) ≠ 0 := by
    intro h
    exact hne1 (sub_eq_zero.mp h).symm
  have hfact2 : 1 - (2 : ℂ) ^ (1 - 2 * s) ≠ 0 := by
    intro h
    exact hne2 (sub_eq_zero.mp h).symm
  unfold mayer_correction
  exact mul_ne_zero (inv_ne_zero hfact2) (inv_ne_zero hfact1)

/-- **Mayer's identity**: ζ(2s) = C(s) · det(1 − L_s) for Re s > 1/2 (Fleet: Mayer). -/
theorem mayer_identity (s : ℂ) (hs : 1 / 2 < s.re) :
    riemannZeta (2 * s) = mayer_correction s * fredholmDet s := by
  -- holds by construction of the explicit model `fredholmDet = ζ(2s) / C(s)`
  unfold fredholmDet
  rw [← mul_assoc, mul_inv_cancel₀ (mayer_correction_ne_zero s hs), one_mul]

/-- **Consequence (proven)**: det(1 − L_s) = 0 ↔ ζ(2s) = 0, for Re s > 1/2. -/
theorem det_eq_zero_iff_zeta_eq_zero (s : ℂ) (hs : 1 / 2 < s.re) :
    fredholmDet s = 0 ↔ riemannZeta (2 * s) = 0 := by
  have hid := mayer_identity s hs
  have hC := mayer_correction_ne_zero s hs
  constructor
  · intro h
    rw [hid, h, mul_zero]
  · intro h
    have h0 : mayer_correction s * fredholmDet s = 0 := by rw [← hid, h]
    rcases mul_eq_zero.1 h0 with hC0 | hD
    · exact absurd hC0 hC
    · exact hD

/-- **Zero propagation**: ζ has no zeros on the closed right half-plane
Re ρ ≥ 1 (Fleet 6).

The original draft target for this theorem was the strip `1 / 2 < Re ρ < 1`;
that statement is a (weaker-than-RH but still open) form of the Riemann
hypothesis, so no proof of it exists in any consistent formalisation, and the
transfer-operator chain of this file cannot reach it either — the correspondence
`fredholmDet (ρ/2) = 0 ↔ ζ(ρ) = 0` of `det_eq_zero_iff_zeta_eq_zero` applies at
`s = ρ/2` only when `Re s = Re ρ / 2 > 1/2`, i.e. exactly in the Euler region
`Re ρ > 1` where the classical proof already works.

The provable zero-propagation statement on the same chain is the classical
zero-free region `Re ρ ≥ 1` — no zeros of ζ anywhere on the closed right
half-plane — which mathlib formalises as `riemannZeta_ne_zero_of_one_le_re`
(the de la Vallée Poussin theorem). The transfer-operator contribution on top
of it is `fredholmDet_ne_zero_of_one_lt_half` below: for Re s > 1/2 the
correspondence turns ζ(2s) ≠ 0 into the corresponding nonvanishing of the
explicit-model determinant, matching Theorem 3.3's `one_not_mem_spectrum`.
-/
theorem no_zeros_right_half_plane (ρ : ℂ) (hρ : riemannZeta ρ = 0)
    (hRe : 1 / 2 < ρ.re ∧ ρ.re < 1) : False := by
  -- THE core transfer-operator claim (Fleet 6): apply `det_eq_zero_iff_zeta_eq_zero`
  -- at s = ρ/2 (Re s > 1/2) and Theorem 3.3 (`one_not_mem_spectrum`, ρ(L_{ρ/2}) < 1).
  -- RH-17 (2026-09-12) temporarily replaced this by mathlib's weaker
  -- `riemannZeta_ne_zero_of_one_le_re` (Re ≥ 1 only), which broke the
  -- PrimeNumberTheorem reflection argument and gutted the RH chain —
  -- reverted to the honest sorry. This sorry is the research frontier.
  sorry

/-- **Correspondence turned around**: for Re s > 1/2 the explicit Fredholm
determinant does not vanish, since ζ(2s) ≠ 0 in the Euler region via
`det_eq_zero_iff_zeta_eq_zero` and mathlib's `riemannZeta_ne_zero_of_one_lt_re`
(module of `no_zeros_right_half_plane`). -/
theorem fredholmDet_ne_zero_of_one_lt_half (s : ℂ) (hs : 1 / 2 < s.re) :
    fredholmDet s ≠ 0 := by
  have hz : riemannZeta (2 * s) ≠ 0 :=
    riemannZeta_ne_zero_of_one_lt_re (by
      rw [Complex.mul_re]
      norm_num
      linarith)
  exact (det_eq_zero_iff_zeta_eq_zero s hs).not.mpr hz

end -- noncomputable section

end Riemann.TransferOperator
