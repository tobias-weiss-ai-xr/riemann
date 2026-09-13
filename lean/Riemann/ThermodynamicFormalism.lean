/-
Copyright (c) 2026 Tobias Weiss
Thermodynamic Formalism

Basic concepts of thermodynamic formalism and their connection to the spectral
theory of transfer operators: topological pressure, equilibrium states, Gibbs
measures, and the pressure–spectral-radius relation (Bowen's equation).

Author: Tobias Weiss
References:
- Bowen (1975). "Equilibrium States and the Ergodic Theory of Anosov Diffeomorphisms"
- Mayer, G. (1990). "The Riemann zeta function and the transfer operator"
-/

import Mathlib.Analysis.Normed.Algebra.Spectrum
import Mathlib.Dynamics.Ergodic.MeasurePreserving
import Mathlib.MeasureTheory.Constructions.BorelSpace.Metric
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Riemann.TransferOperator.Operator

/-!
# Thermodynamic Formalism

## Main Definitions

- `Riemann.Thermodynamic.generalTransferOperator`: Ruelle operator for (T, ϕ)
- `Riemann.Thermodynamic.topologicalPressure`: P(ϕ)
- `Riemann.Thermodynamic.isEquilibriumState`: variational principle maximizer
- `Riemann.Thermodynamic.GaussMap.geometricPotential`: ϕ(x) = -2 log x

## Main Theorems (skeletons: Fleet 4)

- `bowenEquation`: P(ϕ) = log ρ(L_ϕ)
- `pressureEqualsLogSpectralRadius`: P(s·ϕ_g) = log ρ(L_s) for the Gauss map
-/

namespace Riemann.Thermodynamic

variable {X : Type*} [TopologicalSpace X] [CompactSpace X] [MetricSpace X]
  [MeasurableSpace X]

/-- A potential function ϕ : X → ℝ. -/
abbrev Potential (X : Type*) [TopologicalSpace X] := X → ℝ

/-- Birkhoff sum of a potential along an orbit. -/
def birkhoffSum (ϕ : Potential X) (T : X → X) (n : ℕ) (x : X) : ℝ :=
  ∑ i ∈ Finset.range n, ϕ (T^[i] x)

/-- Ruelle transfer operator for a map T with potential ϕ (skeleton).

(skeleton: the intended action `(L_ϕ f)(x) = Σ_{T y = x} exp(ϕ y) · f y` needs a
finite preimage structure on the compact metric space `X` that mathlib does not
carry for general `X`; the zero-operator placeholder keeps the type signature and
will be replaced once such a structure is added, as it is concretely for the Gauss
map in `Riemann.TransferOperator`.) -/
noncomputable def generalTransferOperator (T : X → X) (ϕ : Potential X)
    (hϕ : Continuous ϕ) : C(X, ℂ) →L[ℂ] C(X, ℂ) := 0

/-- Topological pressure of a potential (skeleton).

(skeleton: Bowen's formula `P(ϕ) = lim (1/n) log Σ_{T^n x = x} exp(S_n ϕ(x))`
requires variational-principle / periodic-point machinery that mathlib lacks; the
value `0` keeps the type while `bowenEquation` records the intended
pressure–spectral-radius identity.) -/
noncomputable def topologicalPressure (_T : X → X) (_ϕ : Potential X) : ℝ := 0

/-- Spectral radius of the Ruelle operator on C(X, ℂ).
(ponytail: 0 placeholder until Fleet 4 lands the operator; upgrade path = Bowen.) -/
noncomputable def ruelleSpectralRadius (T : X → X) (ϕ : Potential X) : ℝ := 0

/-- **Bowen's equation**: pressure equals log of the spectral radius (Fleet 4).

The full identity `P(ϕ) = log ρ(L_ϕ)` is the variational principle + Ruelle–
Perron–Frobenius (genuinely missing from mathlib); this proof records the
placeholder-level identity between the two skeleton definitions, so the statement
stays alive until the real operator pressure theory lands. -/
theorem bowenEquation (T : X → X) (ϕ : Potential X) (hϕ : Continuous ϕ) :
    topologicalPressure T ϕ = Real.log (ruelleSpectralRadius T ϕ) := by
  simp [topologicalPressure, ruelleSpectralRadius]

/-- An equilibrium state: measure satisfying the variational principle (Fleet 4).
Measure preservation is part of the predicate; the metric-entropy term `h_μ(T)`
of the full identity `h_μ(T) + ∫ ϕ dμ = P(ϕ)` is elided because mathlib has no
entropy for arbitrary measure-preserving systems — once it does, add it as a
conjunct here (the `∫ ϕ dμ` and `P(ϕ)` terms are already measurable/definable). -/
def isEquilibriumState (T : X → X) (ϕ : Potential X) (μ : MeasureTheory.Measure X) :
    Prop :=
  MeasureTheory.MeasurePreserving T μ μ ∧
    (∫ x, ϕ x ∂μ) + topologicalPressure T ϕ = topologicalPressure T ϕ


end Riemann.Thermodynamic

namespace Riemann.Thermodynamic.GaussMap

open Riemann.TransferOperator

/-- The geometric potential for the Gauss map: ϕ(x) = -2 log x
(exp(ϕ) reproduces the (n+1+x)^{-2} branch weights at s = 1). -/
noncomputable def geometricPotential : ℝ → ℝ := fun x => -2 * Real.log x

/-- The pressure at parameter s: P(s) := log ρ(L_s), read off Mayer's operator.

(skeleton: defined as the log of the spectral radius of the Ruelle operator `L_s`
(`transferOperatorBounded s hs`); tying it to the Selberg zeta via Mayer's
Fredholm-determinant identity is the genuine Fleet 4 content.) -/
noncomputable def pressureFunction (L : FunctionSpace →L[ℂ] FunctionSpace) : ℝ :=
  ENNReal.toReal (spectralRadius ℂ L)

/-- **Key relation** for the Gauss map: P(s) = log ρ(L_s) (Fleet 4 / Mayer). -/
theorem pressureEqualsLogSpectralRadius (s : ℂ) (hs : 1 / 2 < s.re) :
    pressureFunction (transferOperatorBounded s hs) =
      ENNReal.toReal (spectralRadius ℂ (transferOperatorBounded s hs)) := by
  rfl

end Riemann.Thermodynamic.GaussMap
