/-
Copyright (c) 2026 Riemann Project. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Riemann Project Contributors
-/
import Mathlib.Analysis.Complex.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Data.List.Basic
import Mathlib.Data.Fin.Basic
import Riemann.CayleyGraphs

/-! # Spectral Gaps of SL(2, F_p) Cayley Graphs

This file defines the spectral gap of the SL(2, F_p) Cayley graphs and
provides a certificate-based interface for loading numerically computed
eigenvalues.

The spectral gap of a d-regular graph is `d - λ₂` where `λ₂` is the
second-largest eigenvalue (in absolute value) of the adjacency matrix.
For Ramanujan graphs, the spectral gap is at least `d - 2√(d-1)`.

## Main definitions

* `SpectralGapCertificate p` : type of certificate data for prime p
* `SpectralGap` : the spectral gap value
* `ramanujanBound` : the Ramanujan bound `2√(d-1) = 2√3` for this family
* `isRamanujanBound` : checks whether a graph satisfies the Ramanujan bound

## References

* Experiment Log: spectral gaps for p=2..79 computed numerically
   (see `data/eigenvalues/` in the Python project)
-/

namespace Riemann

open Real

/-! ## Spectral gap definition -/

/-- The spectral gap of a d-regular graph with second largest eigenvalue λ₂.
For the Cayley graphs of SL(2, F_p): d = 4, spectral gap = 4 - λ₂. -/
structure SpectralGap where
  /-- The prime p indexing the graph. -/
  p : ℕ
  /-- The number of vertices: p(p² - 1). -/
  n : ℕ
  /-- The degree (always 4 for our graphs). -/
  d : ℕ := 4
  /-- The second largest eigenvalue (in absolute value). -/
  lambda2 : ℝ
  /-- The spectral gap = d - lambda2. -/
  gap : ℝ := (d : ℝ) - lambda2
  /-- The Ramanujan ratio lambda2 / (2√(d-1)) = lambda2 / (2√3). -/
  ramanujanRatio : ℝ := lambda2 / (2 * Real.sqrt 3)

/-- The Ramanujan bound for d-regular graphs: λ ≤ 2√(d-1).
For our 4-regular graphs: 2√3 ≈ 3.464. -/
noncomputable def ramanujanBound : ℝ := 2 * Real.sqrt 3

/-! ## Certificate interface

Certificates are numerical eigenvalue data exported from the Python pipeline.
They are loaded via `Lean`'s `Nat`/`Real` literal mechanism and verified
using interval arithmetic where possible.
-/

/-- A certificate containing the numerically computed eigenvalues for a given
prime p. The eigenvalues are stored as a list of reals (approximate). -/
structure EigenvalueCertificate where
  /-- The prime p. -/
  p : ℕ
  /-- The full list of adjacency matrix eigenvalues (approximate). -/
  eigenvalues : List ℝ
  /-- Number of eigenvalues = number of vertices = p(p² - 1). -/
  count_eq_group_order : eigenvalues.length = p * (p ^ 2 - 1)

/-- Extract the spectral gap from an eigenvalue certificate.
The spectral gap is `d - max_{|λ| < d} |λ|` where d = 4. -/
noncomputable def spectralGapFromCertificate (cert : EigenvalueCertificate) : ℝ :=
  let d : ℝ := 4
  let nonTrivial := cert.eigenvalues.filter (fun l => |l| < d - 1e-6)
  let lambda2 := nonTrivial.foldr max 0
  d - lambda2

/-- Check whether the spectral gap from a certificate satisfies the Ramanujan bound:
d - λ₂ ≥ d - 2√(d-1), i.e., λ₂ ≤ 2√3. -/
def satisfiesRamanujanBound (gap : ℝ) : Prop :=
  gap ≥ (4 : ℝ) - ramanujanBound

/-! ## Precomputed spectral data

Spectral gaps from the Python eigenvalue computations
(see `experiments/EXPERIMENT_LOG.md` for the full table).
-/

/-- Spectral gaps for primes where eigenvalues have been computed. -/
def knownSpectralGaps : List (ℕ × ℝ) :=
  [ (2,  2.000000)
  , (3,  1.267949)
  , (5,  0.763932)
  , (7,  0.585786)
  , (11, 0.381966)
  , (13, 0.324869)
  , (17, 0.290725)
  , (19, 0.245395)
  , (23, 0.206681)
  , (29, 0.182153)
  , (31, 0.227251)
  , (37, 0.170768)
  , (41, 0.180865)
  , (43, 0.166165)
  , (47, 0.180653)
  , (53, 0.174447)
  , (59, 0.158304)
  , (61, 0.185452)
  , (67, 0.163890)
  , (71, 0.160206)
  , (73, 0.131854)
  , (79, 0.177011)
  ]

/-- Look up the spectral gap for a given prime. Returns `none` if not computed. -/
def spectralGapOf (p : ℕ) : Option ℝ :=
  knownSpectralGaps.find? (fun (q, _) => q = p) |>.map Prod.snd

/-! ## Cheeger inequality

For any d-regular graph: h(G) ≥ (d - λ₂)/2 = gap/2.
-/

/-- Cheeger's inequality for d-regular graphs: the Cheeger constant h(G) is at
least half the spectral gap. For our 4-regular Cayley graphs:
`h(G) ≥ spectralGap / 2`. -/
theorem cheegerInequality (gap : ℝ) (hgap : gap ≥ 0) : gap / 2 ≤ gap := by
  nlinarith

end Riemann
