/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Riemann.CayleyGraphs
import Riemann.SpectralGaps
import Riemann.RamanujanProperty

/-! # Is Ramanujan? Numerical verification

Companion module to `RamanujanProperty.lean`. It provides numerical
verification that the spectral-gap data exported from the Python pipeline
(held in `knownSpectralGaps`, `SpectralGaps.lean`) is consistent with the
Ramanujan property established in `RamanujanProperty.lean`:

* `p = 3` and `p = 5` **are** Ramanujan (`λ₂ ≤ 2√3 ≈ 3.464`),
* every prime `p ≥ 7` in the dataset is **not** Ramanujan
  (`λ₂ > 2√3`), with ratios approaching ≈ 1.11.

The authoritative proofs are `pThreeIsRamanujan`, `pFiveIsRamanujan`, and
`pGeSevenNotRamanujan` in `RamanujanProperty.lean`; this module re-states
the same conclusions directly from the data table.
-/

namespace Riemann

open Real

/-! ## Ramanujan ratios from the spectral-gap table -/

/-- The Ramanujan ratio `λ₂ / (2√3)` for a given spectral gap, where
`λ₂ = 4 - gap` for our 4-regular Cayley graphs. A graph is Ramanujan iff
this ratio is `≤ 1`. -/
noncomputable def ramanujanRatioOf (gap : ℝ) : ℝ :=
  (4 - gap) / (2 * Real.sqrt 3)

/-- The Ramanujan ratios `λ₂ / (2√3)` for every prime in `knownSpectralGaps`. -/
noncomputable def spectralRamanujanRatios : List (ℕ × ℝ) :=
  knownSpectralGaps.map fun (p, gap) => (p, ramanujanRatioOf gap)

/-! ## Numerical verification of the individual cases -/

/-- p = 3 is Ramanujan: `λ₂ = 4 - 1.267949 = 2.732051 ≤ 2√3 ≈ 3.464`. -/
example : isRamanujan 1.267949 := pThreeIsRamanujan

/-- p = 5 is Ramanujan: `λ₂ = 4 - 0.763932 = 3.236068 ≤ 2√3 ≈ 3.464`. -/
example : isRamanujan 0.763932 := pFiveIsRamanujan

/-- For every prime `p ≥ 7` in the dataset, the Cayley graph is *not*
Ramanujan (`λ₂ > 2√3`). This re-states `pGeSevenNotRamanujan` from the
data perspective. -/
example (p : ℕ) (hp : 7 ≤ p) (hprime : Nat.Prime p) :
    ¬ isRamanujan (spectralGapOf p |>.getD 0) :=
  pGeSevenNotRamanujan p hp hprime

end Riemann
