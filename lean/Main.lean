/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Riemann.CayleyGraphs
import Riemann.SpectralGaps
import Riemann.RamanujanProperty
import Riemann.FriedliRatio
import Riemann.LMFDBConjectures
import Riemann.RiemannHypothesis
import Riemann.LiCriterion
import Riemann.NymanBeurling
import Riemann.GoldbachBridge
import Riemann.ZeroFreeRegion.ThreeFourOne

open Riemann

/-! # Riemann Project — Lean 4 Formalization

This is the main entry point for the Lean formalization branch of the
GNN × Number Theory Riemann Hypothesis research project.

## Overview

The project formalizes:

1. **SL(2, F_p) Cayley graphs** — definitions, 4-regularity, vertex-transitivity
2. **Spectral gaps** — numerical certificates, Cheeger inequality
3. **Ramanujan property** — p=3, p=5 are Ramanujan; p≥7 are not
4. **Friedli ratio** — spectral zeta functional equation
5. **LMFDB conjectures** — empirical results from ML experiments
6. **RH bridges** — connections to mathlib's RiemannHypothesis
7. **Li's criterion** — certified interval λ₁ ∈ (0.0054, 0.091) (`liLambda1_mem`),
   bridge to the completed zeta (`liLambda1_eq_completedZeta0`); extended to the
   second Keiper–Li coefficient λ₂ ∈ (0.07, 0.15) via the certified decimal γ₁
   (`stieltjes1Certified`, no axiom) and `λ₁ < λ₂` (`liLambda2_mem`,
   `liLambda1_lt_liLambda2`); extended to the third coefficient λ₃ ∈ (0.15, 0.3)
   via the certified decimals γ₂ and ζ(3) (`stieltjes2Certified`,
   `zeta3Certified`, no axiom), `λ₂ < λ₃` (`liLambda3_mem`,
   `liLambda2_lt_liLambda3`)
8. **Nyman–Beurling density** — the Báez-Duarte criterion
   (`baezDuarte`, axiom) plus the certified rational certificate table of the
   measured εₙ chain n = 16 … 16384 (`nbCertRows`, gate PASS at 16K:
   ε₁₆₃₈₄ = 9.79e-5), machine-checked log-law containment
   (`nbCertChecksTrue`: εₙ ≈ 0.257·n⁻¹·(ln n)^0.84 over 1024× in n),
   strict decay (`nbCertStrictlyDecreasing`) and the 1.90 successive ratio
   (`nbRatio8192To16384Gt185`)

## Running

```bash
make lean-build      # Build the project
make lean-test       # Run verification
make lean-eigenvalues # Export Python eigenvalues → Lean certificates
```
-/

/-- Print a summary of the formalized statements. -/
def main : IO Unit := do
  IO.println "Riemann Project — Lean 4 Formalization"
  IO.println ""
  IO.println "Formalized modules:"
  IO.println "  ✓ CayleyGraphs.lean — SL(2,F_p) graph definitions"
  IO.println "  ✓ SpectralGaps.lean — Spectral gap certificates"
  IO.println "  ✓ RamanujanProperty.lean — p=3,5 Ramanujan verification"
  IO.println "  ✓ FriedliRatio.lean — Spectral zeta ratio"
  IO.println "  ✓ LMFDBConjectures.lean — Empirical ML conjectures"
  IO.println "  ✓ RiemannHypothesis.lean — Bridge to mathlib's RH"
  IO.println "  ✓ GoldbachBridge.lean — Granville's RH ↔ averaged Goldbach"
  IO.println "  ✓ NymanBeurling.lean — Báez-Duarte density criterion + certified 16K chain"
  IO.println ""
  IO.println "The Riemann hypothesis (RiemannHypothesis) is already"
  IO.println "defined in mathlib as a Prop. The goal of this project"
  IO.println "is to formalize the connections between spectral graph"
  IO.println "theory and ζ(s) that our GNN experiments have uncovered."
