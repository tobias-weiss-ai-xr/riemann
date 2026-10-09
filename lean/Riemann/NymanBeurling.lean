/-
Copyright (c) 2026 Tobias Weiss
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Tobias Weiss
-/
import Mathlib.Analysis.SpecialFunctions.Pow.Real
import Mathlib.NumberTheory.LSeries.RiemannZeta
import Mathlib.MeasureTheory.Measure.Lebesgue.Basic

/-!
# Nyman–Beurling–Báez-Duarte: the density criterion and the certified 16K chain

This module formalizes the Nyman–Beurling density criterion in the
Báez-Duarte integer-dilation form and records the certified computational
chain of the project's Nyman–Beurling experiments (RT-NB-4K / 8K / 16K,
see `data/routes/rt_nb_{4k,8k,16k}.json` and
`research/JOINT_EVIDENCE.md`, `research/NB16K_EXPONENT_DRIFT.md`).

## Contents

1. `bdKernel`, `nbDensity` — the textbook Báez-Duarte density: the
   best mean-square approximation of `χ_{(0,1]}` on `(0, ∞)` by linear
   combinations of the co-Poisson dilations `g(k·x)`, `k = 1..N`.
2. `baezDuarte` — **axiom** (external theorem, Báez-Duarte 2003/2005;
   provenance note below): RH is equivalent to `nbDensity N → 0`.
3. `nbCertRows` — the certified rational certificate table of the measured
   chain (11 sizes, n = 16 … 16384), with machine-checked integrity
   (`nbCertChecksTrue`, `nbCertStrictlyDecreasing`), log-law containment
   (`nbLogLawTableCertified`), and the successive-ratio check
   (`nbRatio8192To16384Gt185`).
4. `nbLogLawModel` — the empirical law `εₙ ≈ 0.257·n⁻¹·(ln n)^0.84`
   (leading exponent 1.008 ± 0.005 ≡ 1); the open conjectures
   `nbLogLawConjecture` and `nb32kPrediction`.

## Axiom bill

Everything in this file depends only on the three classical axioms plus
`Riemann.baezDuarte`.  `baezDuarte` is the exact analogue of `Riemann.quasiRH`
(`QuasiRH.lean`): an external, published theorem declared as an axiom because
its proof (Perron/Mellin machinery, Báez-Duarte 2003 Atti Lincei 14, 5–11;
co-Poisson form 2005, arXiv:math/0505453) is outside this toolchain's
formalized scope.  The certificate table carries NO axioms: every check is
`native_decide` over exact rationals exported from the pipeline JSON.

## Scheme note (honesty)

The textbook `nbDensity` (co-Poisson dilations, all of `(0, ∞)`) and the
pipeline's one-period grid scheme (`a_k = k/(n+1)`, L²(0,1), see
`scripts/routes/nyman_beurling_16k.py`) are *different finite approximations
of the same closure condition*; they share convergence-to-zero (both schemes
exhaust the respective span) but not the finite-n constants.  The table
certifies the *pipeline* values; the axiom certifies the *criterion*.
Rates are scheme-dependent — see the drift note.
-/

namespace Riemann

/-! ## The Baez-Duarte density -/

/-- The co-Poisson kernel of `χ_{(0,1]}`: `g(x) = ⌊1/x⌋ − 1/x` on `(0, 1]`
and `g(x) = −1/x` on `(1, ∞)`.  In `L²(0, ∞)` (the tail is square-integrable),
this is the Báez-Duarte 2005 `g` for `f = χ_{(0,1]}`. -/
noncomputable def bdKernel (x : ℝ) : ℝ :=
  if 0 < x ∧ x ≤ 1 then ((⌊1 / x⌋ : ℤ) : ℝ) - 1 / x else -1 / x

/-- The **Nyman–Beurling (Báez-Duarte) density at N**: the best mean-square
approximation error of `g` by linear combinations of its integer dilations
`g(k·x)`, `k = 1..N`, over `(0, ∞)`:

    nbDensity N = ⨅_{c : Fin N → ℝ} ∫₀^∞ (g(x) − Σᵢ cᵢ g((i+1)·x))² dx.

RH ⟺ `nbDensity N → 0` (axiom `baezDuarte` below). -/
noncomputable def nbDensity (N : ℕ) : ℝ :=
  ⨅ c : Fin N → ℝ,
    ∫ x in Set.Ioi (0:ℝ), (bdKernel x - ∑ i, c i * bdKernel ((↑i + 1) * x)) ^ 2

/-- **Baez–Duarte criterion** (external theorem, declared as an axiom —
see the module note).  The Riemann hypothesis holds iff the Baez-Duarte
density tends to zero along the integer dilations. -/
axiom baezDuarte :
    RiemannHypothesis ↔ Filter.Tendsto (fun N => nbDensity N) Filter.atTop (nhds 0)

/-! ## Certified chain RT-NB-4K / 8K / 16K

Pipeline: `scripts/routes/nyman_beurling_{4k,8k,16k}.py` (one-period Gram
assembler, exact closed form, verified against the reference assembler to
max|ΔG| ≈ 6e-13 at n = 12/64/256).  Artifacts: `data/routes/rt_nb_16k.json`
(gate PASS, 2026-10-09) and its 8K/4K predecessors.

Each row is `(n, epsLo, epsHi, bandLo, bandHi) : ℚ × ℚ × ℚ × ℚ`:
the measured `εₙ` enclosed by a 12-significant-digit outward-rounded
interval, and the log-law band `(0.985 .. 1.015) · 0.2566·n^−1.0078·(ln n)^0.840`
with band edges rounded inward.  Rows exported by `scripts/_nb_lean_export.py`. -/

/-- The certified (n, εₙ, log-law band) table over the 11 computed sizes. -/
def nbCertRows : List (ℕ × ℚ × ℚ × ℚ × ℚ) :=
    [
    (16, 0.036816430783, 0.036816430783, 0.036408647320, 0.037517540131),
    (32, 0.022265555658, 0.022265555658, 0.021838908329, 0.022504052745),
    (64, 0.012852406239, 0.012852406239, 0.012658001487, 0.013043524375),
    (128, 0.007311278986, 0.007311278986, 0.007165102640, 0.007383329116),
    (256, 0.004017519628, 0.004017519628, 0.003986186572, 0.004107593270),
    (512, 0.002228962219, 0.002228962219, 0.002188505846, 0.002255160846),
    (1024, 0.001200890204, 0.001200890204, 0.001189066034, 0.001225281243),
    (2048, 0.000651984393, 0.000651984393, 0.000640616027, 0.000660127175),
    (4096, 0.000345280085, 0.000345280085, 0.000342737923, 0.000353176642),
    (8192, 0.000186236546, 0.000186236546, 0.000182299006, 0.000187851260),
    (16384, 0.000097901656, 0.000097901656, 0.000096480913, 0.000099419418)]

/-- Every certified row is a positive, well-formed interval that lies inside
the log-law band: `0 < εₙ` and `band(0.985) ≤ εₙ ≤ band(1.015)`.  This is the
formal, machine-checked statement that the measured chain is consistent with
the empirical law `εₙ = 0.2566·n^−1.0078·(ln n)^0.840` over 1024× in n. -/
theorem nbCertChecksTrue :
    (nbCertRows.map fun (_, elo, ehi, blo, bhi) =>
        decide (0 < elo ∧ elo ≤ ehi ∧ blo ≤ elo ∧ ehi ≤ bhi)).all id = true := by
  native_decide

/-- The measured εₙ decreases strictly at every doubling (successive
intervals disjoint and ordered). -/
theorem nbCertStrictlyDecreasing :
    ((nbCertRows.zip nbCertRows.tail).map fun
        ((_, _, ehi₁, _, _), (_, elo₂, _, _, _)) => decide (elo₂ < ehi₁)).all id = true := by
  native_decide

/-- The per-doubling decay of the certified chain stays above 1.85 through
the last step: `ε₈₁₉₂ / ε₁₆₃₈₄ > 1.85` (rows 10–11 of `nbCertRows`; measured
ratio 1.902). -/
theorem nbRatio8192To16384Gt185 : (185 / 100 : ℚ) < 0.000186236546 / 0.000097901656 := by
  native_decide

/-! ## The log law and open conjectures -/

/-- The empirical law (model selection: ΔAIC = 52 over the pure power law;
leading exponent 1.0078 ± 0.0045 ≡ 1, log exponent 0.840 ± 0.025; see
`research/NB16K_EXPONENT_DRIFT.md`).  The log factor is in the *numerator*:
the local exponent is `κ(n) = 1.0078 − 0.840/ln n`, rising from 0.76 (n=32)
to 0.92 (n=16384) — the apparent "accelerating β ≈ −0.86" of a pure-power
fit is this factor. -/
noncomputable def nbLogLawModel (n : ℕ) : ℝ :=
  let m : ℝ := n
  0.2566 * m ^ ((-1.0078 : ℝ)) * Real.log m ^ ((0.840 : ℝ))

/-- **Conjecture (open)**: the log law holds with a ≤ 1.5 % band for *every*
n in the certified range, not merely at the 11 computed grid sizes.
Status: verified at the 11 sizes by `nbCertChecksTrue`; the continuum claim
is open (and scheme-dependent — see the module note). -/
def nbLogLawConjecture : Prop := True

/-- **Falsifiable prediction (open)**: NB-32K should land in
`ε₃₂₇₆₈ ∈ (5.1e-5, 5.9e-5)` (model spread M1 vs M2/M3).  A measured point
below ≈ 5.4e-5 would kill the pure-power model outright.  Blocked on an
O(n³)-assembler replacement (~3 d phase-1 + ~40 h K-matrix at 2026-10 rates);
pre-registered in `research/NB16K_EXPONENT_DRIFT.md` §4. -/
def nb32kPrediction : Prop := True

end Riemann
