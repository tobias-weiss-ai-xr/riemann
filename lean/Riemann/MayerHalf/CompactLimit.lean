/-
Copyright (c) 2026 Tobias Weiss. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
-/
import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.Normed.Operator.Compact.Basic

/-!
# The operator-norm limit of compact operators is compact

This module closes the compactness chain for the Mayer operator on the half-disc algebra:

- T3 proves each n≥1 summand is compact
- The tail is the operator-norm limit of partial sums (T5)
- Hence compact by this lemma

This is the honest entry point of RH-42: the Mayer operator has a compact tail on the
half-disc algebra.
-/

open Metric Set Filter Complex Topology

open scoped Classical

namespace Riemann

noncomputable section

/-- The operator-norm limit of compact operators is compact.
This is a thin wrapper around `Mathlib.Analysis.Normed.Operator.Compact.isCompactOperator_of_tendsto`
specialized to sequences (ι := ℕ, l := atTop) over the complex field. -/
theorem isCompactOperator_of_tendsto_nat
    {E F : Type*} [NormedAddCommGroup E] [NormedAddCommGroup F]
    [NormedSpace ℂ E] [NormedSpace ℂ F] [CompleteSpace F]
    {u : ℕ → E →L[ℂ] F} {T : E →L[ℂ] F}
    (hu : Tendsto u atTop (𝓝 T))
    (hu' : ∀ n, IsCompactOperator (u n)) :
    IsCompactOperator T := by
  apply isCompactOperator_of_tendsto
    (ι := ℕ) (l := atTop) (𝕜₁ := ℂ) (𝕜₂ := ℂ)
  · exact hu
  · exact Filter.Eventually.of_forall hu'

end

end Riemann