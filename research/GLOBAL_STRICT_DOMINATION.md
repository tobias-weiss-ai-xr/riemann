# Global Strict Domination off the Real Axis

**Experiment 19i** — EPIC-4 / Sprint 6, 2026-08-29
`scripts/_strict_domination_global.py`, `scripts/_nystrom_vec.py`

## Statement verified

Two numerical probes at high resolution (vectorized Nyström collocation,
N = 160, n_max = 6000, worst points re-checked at N = 256):

**(A) Global strict domination.** For σ ∈ {0.6, …, 2.0} and **every** t ≠ 0
with |t| ≤ 1000:

    |λ₁(σ+it)| < λ₁(σ).

The maximum ratio over t ≠ 0 occurs at the *smallest* sampled |t| (t = 0.5):
the leading eigenvalue decays monotonically in |t| away from the real axis.
The local theorem (`strictDomination_off_real_axis`, proved in Lean from
P''(σ) > 0, Exp 19h) is therefore **global in t numerically**:

| σ | λ₁(σ) | max_{t≠0} |λ₁(σ+it)| / λ₁(σ) | at t |
|---:|---:|---:|---:|
| 0.60 | 4.405 | 0.3037 | 0.5 |
| 0.70 | 2.604 | 0.4410 | 0.5 |
| 0.80 | 1.759 | 0.5685 | 0.5 |
| 0.90 | 1.292 | 0.6695 | 0.5 |
| 1.00 | 0.9998 | 0.7449 | 0.5 |
| 1.10 | 0.8008 | 0.8003 | 0.5 |
| 1.25 | 0.5991 | 0.8576 | 0.5 |
| 1.50 | 0.3964 | 0.9130 | 0.5 |
| 2.00 | 0.1995 | 0.9606 | 0.5 |

(The ratio approaches 1 at large σ only because λ₁(σ) itself → 0; the strict
inequality holds everywhere.)

**(B) Corrected spectral radius.** The second eigenvalue |λ₂(σ+it)| — the
proxy for the boundary-corrected operator L_s^(0) with the constant-mode
ζ(2σ)-peak removed — satisfies

    |λ₂(σ+it)| < 0.856   for all σ ≥ 0.60, |t| ≤ 1000,

with the worst point at (σ, t) = (0.60, 750): |λ₂| = 0.855 (N=160),
re-measured 0.825 at N=256 (over-estimate direction is safe).  This is a
**strict improvement over Exp 19e's** worst 0.950 at (0.55, 100) — that point
was truncation-inflated (σ ≤ 0.55 is never quotable: the n-sum converges like
n_max^{-(2σ-1)}).

| σ | max_{|t|≤1000} |λ₂| |
|---:|---:|
| 0.60 | 0.855 |
| 0.70 | 0.728 |
| 0.80 | 0.627 |
| 0.90 | 0.544 |
| 1.00 | 0.480 |

## The quadratic law near t = 0 (ties Exp 19h ↔ 19i)

The pressure Taylor law from strict convexity,

    |λ₁(σ+it)| / λ₁(σ) = exp( − (t²/2)·P''(σ) + O(t⁴) ),

i.e.  −ln(ratio)/t² = P''(σ)/2 + O(t²) → P''(σ)/2  as  t → 0,  is confirmed
numerically to 99% agreement at t = 0.1:

| σ | −ln(ratio)/t² at t=0.1 | P''(σ)/2 (Exp 19h) |
|---:|---:|---:|
| 1.0 | 1.664 | 1.688 |
| 0.8 | 3.998 | 4.025 |

The two experiments — second pressure derivative (P''>0) and global strict
domination (|λ₁(σ+it)| < λ₁(σ)) — rest on the same mechanism (thermodynamic
formalism: variance of the equilibrium potential), and now quantitatively
agree.

## Interpretation

- **(A)** is the global-in-t version of the t-anisotropic estimate that the
  envelope obstruction (Exp 19g) says is *required* in the strip.  In Lean the
  local theorem is proved; the global statement is recorded as a labelled
  axiom `strictDomination_global_off_real_axis` (Ruelle, thermodynamic
  formalism for complex potentials; phase-cocycle CLT: the potential is not
  cohomologous to a constant, so adding an imaginary phase strictly reduces
  the top of the spectrum).
- **(B)** is the direct numerical probe of the RH-equivalent statement
  ρ(L_s^(0)) < 1.  The safe region now runs down to σ ≥ 0.60 with margin
  ~0.145; the region σ ∈ (1/2, 0.6) is where both the numerics (n-sum
  truncation) and the mathematics (RH) become delicate.
- **Relation to RH (kept honest).**  (A) is necessary but not sufficient: in
  the strip λ₁(σ) > 1, so |λ₁(σ+it)| < λ₁(σ) does not force |λ₁| < 1.
  (B) is the honest object but rests on certified/rigorous numerics (Nisoli/
  DFLY style) to become a theorem, and on the eigenvalue-1 / det(I−L_s)≠0
  structure to reach the critical line.  The t-anisotropic programme supplies
  the mechanical input; the arithmetic/global step remains = RH.

## Data

`data/spectral-radius/strict_domination_global.json` (gitignored, as all
numerical outputs).  Re-run:

    python scripts/_strict_domination_global.py
