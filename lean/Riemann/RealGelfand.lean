/-
Copyright (c) 2026 Tobias Weiss
Real Gelfand spectral-radius module
-/

import Mathlib.Analysis.Normed.Algebra.Spectrum
import Mathlib.Analysis.Normed.Algebra.GelfandFormula

open scoped NNReal Topology Ring
open Filter ENNReal

/-!
## The general-real Gelfand upper bound is FALSE

The upper bound `limsup ‖a^n‖₊ ^ (1/n) ≤ ρ(a)` is false for general real normed
algebras.  **Counterexample**: take `A := ℂ` and `a := Complex.I` (all instance
hypotheses hold).  For every real `s`, the element `s - I` is a unit of `ℂ` —
its inverse is `(s + I)/(s^2 + 1)` — so the real spectrum of `Complex.I` is
empty and `spectralRadius ℝ Complex.I = 0` (the supremum over `∅`).  But
`‖I^n‖ = 1` for all `n` (since `‖I‖ = 1`), so the limsup of the nth-root norms
is `1`, and `1 ≤ 0` is false; see `counterexampleRotation` below.

Consequently the erroneous admitted lemmas `realGelfandUpperBound` and
`realGelfandFormula` have been removed.  Over `ℂ` mathlib's own Gelfand formula
applies (`spectrum.pow_nnnorm_pow_one_div_tendsto_nhds_spectralRadius`), so the
failure is specific to the real field. -/

namespace Riemann

noncomputable section

set_option maxHeartbeats 5000000

variable {A : Type*} [NormedRing A] [NormedAlgebra ℝ A] [CompleteSpace A]
         (a : A)

/-- Lower bound: spectral radius ≤ liminf of nth roots of norms -/
theorem realSpectralRadius_le_liminf_pow_nnnorm_pow_one_div :
    spectralRadius ℝ a ≤ atTop.liminf fun n : ℕ =>
      (‖a ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ) :=
  spectrum.spectralRadius_le_liminf_pow_nnnorm_pow_one_div ℝ a

/-- `Complex.I` is not in the real spectrum of itself: for every `s : ℝ`,
`s - I` is a unit of `ℂ` with explicit inverse `(s + I)/(s^2 + 1)`. -/
lemma not_mem_spectrum_I (s : ℝ) : s ∉ spectrum ℝ (Complex.I : ℂ) := by
  let inv : ℂ := ((s : ℂ) + Complex.I) / ((s : ℂ) ^ 2 + 1)
  have hprod : ((s : ℂ) - Complex.I) * ((s : ℂ) + Complex.I) = (s : ℂ) ^ 2 + 1 := by
    calc
      ((s : ℂ) - Complex.I) * ((s : ℂ) + Complex.I) = (s : ℂ) ^ 2 - Complex.I ^ 2 := by ring
      _ = (s : ℂ) ^ 2 + 1 := by simp
  have hsq : (s : ℂ) ^ 2 = ((s ^ 2 : ℝ) : ℂ) := by norm_num
  have hcoe : (s : ℂ) ^ 2 + 1 = ((s ^ 2 + 1 : ℝ) : ℂ) := by
    rw [hsq]
    norm_num
  have hnnz : (s : ℂ) ^ 2 + 1 ≠ 0 := by
    intro h
    apply (show (s ^ 2 + 1 : ℝ) ≠ 0 by nlinarith [sq_nonneg s])
    rw [hcoe] at h
    exact Complex.ofReal_injective h
  have hinv1 : ((s : ℂ) - Complex.I) * inv = 1 := by
    dsimp [inv]
    rw [← mul_div_assoc, hprod, div_self hnnz]
  have hinv2 : inv * ((s : ℂ) - Complex.I) = 1 := by
    rw [mul_comm, hinv1]
  have hres : s ∈ resolventSet ℝ (Complex.I : ℂ) := by
    exact spectrum.mem_resolventSet_of_left_right_inverse (a := (Complex.I : ℂ))
      (b := inv) (c := inv) hinv1 hinv2
  simpa [spectrum] using hres

/-- The real spectrum of `Complex.I` is empty. -/
lemma spectrum_zero : spectrum ℝ (Complex.I : ℂ) = ∅ := by
  ext s
  constructor
  · intro hs
    exact (not_mem_spectrum_I s hs).elim
  · intro hs
    simp at hs

/-- Hence the real spectral radius of `Complex.I` is `0` (the supremum over the
empty spectrum). -/
lemma spectralRadius_zero : spectralRadius ℝ (Complex.I : ℂ) = 0 := by
  simp [spectralRadius, spectrum_zero]

/-- `‖I^n‖₊ = 1` for all `n`, since `‖I‖₊ = 1`. -/
lemma nnnorm_pow_of_Complex_I (n : ℕ) : ‖(Complex.I : ℂ) ^ n‖₊ = 1 := by
  have hn : ‖(Complex.I : ℂ) ^ n‖ = 1 := by
    rw [norm_pow, Complex.norm_I, one_pow]
  rw [← NNReal.coe_inj, coe_nnnorm, hn]
  norm_num

/-- The sequence of nth-root norms for `Complex.I` is constantly `1`. -/
private lemma nthRootSeq_eq_one :
    (fun n : ℕ => ((‖(Complex.I : ℂ) ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ)))) =
      fun _ : ℕ => (1 : ℝ≥0∞) := by
  funext n
  rw [nnnorm_pow_of_Complex_I n]
  simp

/-- **Counterexample to the general-real Gelfand upper bound**: for
`a = Complex.I` in the real normed algebra `ℂ`, we have
`limsup (‖I^n‖₊ : ℝ≥0∞) ^ (1/n) = 1` while `spectralRadius ℝ Complex.I = 0`, so
`limsup (...) ≤ spectralRadius ℝ Complex.I` fails.  This disproves the (false)
admitted lemma `realGelfandUpperBound`; over `ℂ` mathlib's own complex Gelfand
formula applies instead. -/
theorem counterexampleRotation :
    ¬ (limsup (fun n : ℕ => ((‖(Complex.I : ℂ) ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ)))) atTop ≤
      spectralRadius ℝ Complex.I) := by
  apply not_le.mpr
  rw [spectralRadius_zero]
  have hlim : atTop.limsup (fun n : ℕ =>
      ((‖(Complex.I : ℂ) ^ n‖₊ : ℝ≥0∞) ^ (1 / (n : ℝ)))) = 1 := by
    rw [nthRootSeq_eq_one]
    simp
  rw [hlim]
  norm_num

end

end Riemann
