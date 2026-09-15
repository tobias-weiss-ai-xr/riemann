/-
Copyright (c) 2026 Tobias Weiss
Gelfand's formula over ℝ for positive operators, via complexification

The `limsup` half of the real Gelfand formula cannot be proved in ℝ alone:
the rotation `T(x, y) = (-y, x)` has empty real spectrum but
`‖Tⁿ‖^(1/n) → 1`.  Positivity enters as follows.  For a positive `T` the
real walk (`Riemann.GelfandPositive.resolvent_positivity_of_gt_spectralRadius`)
shows every real level `λ > ρ_ℝ(T)` is in the resolvent set; complexifying
the algebra identity `⟨λ - T, (λ - T)⁻¹⟩ = 1 = (λ - T)(λ - T)⁻¹` shows every
`z ∈ ℂ` with `|z| > ρ_ℝ(T)` lies outside the *complex* spectrum of the
complexification `T_ℂ`.  Hence `ρ_ℂ(T_ℂ) ≤ ρ_ℝ(T)`.  Combined with

* mathlib's complex Gelfand formula for `T_ℂ`, and
* the embedding `‖Tⁿ‖ ≤ ‖(T_ℂ)ⁿ‖` (real functions sit inside `C(X, ℂ)`),

we get `limsup ‖Tⁿ‖^{1/n} ≤ ρ_ℂ(T_ℂ) ≤ ρ_ℝ(T)`, and the committed liminf
bound (`Riemann.GelfandPositive.spectralRadius_le_liminf_pow`) closes the
two-sided Gelfand formula for positive `T` over ℝ.
-/

import Riemann.GelfandPositive

open scoped NNReal ENNReal Topology
open Complex ContinuousMap Filter Set

namespace Riemann

variable {X : Type*} [TopologicalSpace X] [CompactSpace X]

set_option linter.unusedSectionVars false
set_option maxHeartbeats 1000000

/-! ## Real and imaginary parts of continuous complex-valued maps -/

/-- Real part of a continuous complex-valued map, as a continuous real map. -/
noncomputable def cmRe (f : C(X, ℂ)) : C(X, ℝ) :=
  ⟨fun x => (f x).re, Complex.continuous_re.comp f.2⟩

/-- Imaginary part of a continuous complex-valued map, as a continuous real map. -/
noncomputable def cmIm (f : C(X, ℂ)) : C(X, ℝ) :=
  ⟨fun x => (f x).im, Complex.continuous_im.comp f.2⟩

/-- Real function embedded into the complex maps. -/
def cmOfReal (g : C(X, ℝ)) : C(X, ℂ) := ⟨fun x => (g x : ℂ), Complex.continuous_ofReal.comp g.2⟩

theorem cmRe_apply (f : C(X, ℂ)) (x : X) : cmRe f x = (f x).re := rfl

theorem cmIm_apply (f : C(X, ℂ)) (x : X) : cmIm f x = (f x).im := rfl

theorem cmOfReal_apply (g : C(X, ℝ)) (x : X) : cmOfReal g x = (g x : ℂ) := rfl

/-- Every complex-valued map is the real part plus `i` times the imaginary part. -/
theorem cmOfReal_re_add_I (f : C(X, ℂ)) :
    cmOfReal (cmRe f) + Complex.I • cmOfReal (cmIm f) = f := by
  ext x
  simp only [ContinuousMap.add_apply, ContinuousMap.smul_apply, cmOfReal_apply, cmRe_apply,
    cmIm_apply, smul_eq_mul]
  exact Complex.ext (by simp) (by simp)

/-- Two complex maps with equal real and imaginary parts are equal. -/
theorem cm_ext_re_im {f g : C(X, ℂ)} (hre : cmRe f = cmRe g) (him : cmIm f = cmIm g) : f = g := by
  rw [← cmOfReal_re_add_I f, hre, him, cmOfReal_re_add_I g]

theorem norm_cmRe_le (f : C(X, ℂ)) : ‖cmRe f‖ ≤ ‖f‖ := by
  refine (ContinuousMap.norm_le (f := cmRe f) (C := ‖f‖) (C0 := norm_nonneg f)).mpr fun x => ?_
  have h := Complex.abs_re_le_norm (f x)
  rw [← Real.norm_eq_abs] at h
  simpa only [cmRe_apply] using h.trans (f.norm_coe_le_norm x)

theorem norm_cmIm_le (f : C(X, ℂ)) : ‖cmIm f‖ ≤ ‖f‖ := by
  refine (ContinuousMap.norm_le (f := cmIm f) (C := ‖f‖) (C0 := norm_nonneg f)).mpr fun x => ?_
  have h := Complex.abs_im_le_norm (f x)
  rw [← Real.norm_eq_abs] at h
  simpa only [cmIm_apply] using h.trans (f.norm_coe_le_norm x)

/-- Embedding into the complex maps is isometric. -/
theorem norm_cmOfReal (g : C(X, ℝ)) : ‖cmOfReal g‖ = ‖g‖ := by
  refine le_antisymm
    ((ContinuousMap.norm_le (f := cmOfReal g) (C := ‖g‖) (C0 := norm_nonneg g)).mpr fun x => ?_)
    ((ContinuousMap.norm_le (f := g) (C := ‖cmOfReal g‖) (C0 := norm_nonneg (cmOfReal g))).mpr
      fun x => ?_)
  · simpa only [cmOfReal_apply] using
      (Complex.norm_real (g x)).trans_le (g.norm_coe_le_norm x)
  · rw [← Complex.norm_real (g x)]
    simpa only [cmOfReal_apply] using (cmOfReal g).norm_coe_le_norm x

end Riemann
