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
import Riemann.GoldbachBridge

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
  IO.println ""
  IO.println "The Riemann hypothesis (RiemannHypothesis) is already"
  IO.println "defined in mathlib as a Prop. The goal of this project"
  IO.println "is to formalize the connections between spectral graph"
  IO.println "theory and ζ(s) that our GNN experiments have uncovered."
