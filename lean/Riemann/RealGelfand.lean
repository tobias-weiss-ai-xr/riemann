/-
Copyright (c) 2026 Tobias Weiss
Real Gelfand spectral-radius module
-/

import Mathlib.Analysis.Normed.Algebra.Spectrum
import Mathlib.Analysis.Normed.Algebra.GelfandFormula

open scoped NNReal Topology Ring
open Filter ENNReal

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

/-- Upper bound (admitted frontier): limsup of nth roots of norms ≤ spectral radius -/
theorem realGelfandUpperBound :
    limsup (fun n : ℕ => (‖a ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ)) atTop ≤ spectralRadius ℝ a := by
  sorry

/-- Gelfand's formula over ℝ: nth roots of norms converge to spectral radius -/
theorem realGelfandFormula :
    Tendsto (fun n : ℕ => (‖a ^ n‖₊ : ℝ≥0∞) ^ (1 / n : ℝ)) atTop
      (nhds (spectralRadius ℝ a)) :=
  tendsto_of_le_liminf_of_limsup_le
    (realSpectralRadius_le_liminf_pow_nnnorm_pow_one_div a)
    (realGelfandUpperBound a)
end

end Riemann
