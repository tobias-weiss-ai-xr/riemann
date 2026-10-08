# Quasi-RH certificate audit — independent machine-check + λ₂ extension

Audit date: 2026-10-07. Companion to `OAI_MATH_RECON.md` and FRONTIER §3d.

## Why

Since RH-44 (`5444754`), our build imports `Riemann.quasiRH` as an external
axiom: the OpenAI math release (`../math`, family 003) formalized zero-freeness
of ζ (and every Dirichlet L-function) on `Re s > 7/8`, but their library pins
Lean 4.34.1 / mathlib `d13f23b`, which will not compile on our 4.33.0-rc1 —
so we cite rather than port. An imported theorem is only as good as its
provenance. This note records an **independent verification of that
provenance**, performed on our host, outside their environment.

## Part 1 — independent build (verification)

Full from-source build of the load-bearing import chain in their pinned
toolchain:

| Item | Value |
|---|---|
| Module built | `OAI.NumberTheory.DirichletL.Nonvanishing` |
| Toolchain | `leanprover/lean4:v4.34.1` (their pin, auto-fetched via elan) |
| mathlib | `d13f23b723b8a846827a245b89c10fc7d3f11612` (their pin), 8908 cache files fetched + decompressed |
| External deps | 10 git deps, compatibility patches auto-applied by their lakefile post-clone hook |
| Jobs | **7061/7061 green, zero errors** (~3 h on our host, incl. mathlib-cache-gap deps built from source) |

Result: their theorem chain compiles from source, with their own patches,
on a machine that has no connection to their build environment.

## Part 2 — axiom audit (trust)

`QuasiRHAudit.lean` (kept in their tree) runs `#print axioms` on the three
load-bearing declarations. Verbatim output:

```
'OAI.riemannZeta_ne_zero_of_seven_eighths_lt_re' depends on axioms: [propext, Classical.choice, Quot.sound]
'OAI.DirichletCharacter.LFunction_ne_zero_of_seven_eighths_lt_re' depends on axioms: [propext, Classical.choice, Quot.sound]
'OAI.SevenEighths.ProbeFinalAssemblyUnconditional.zeta_nonzero' depends on axioms: [propext, Classical.choice, Quot.sound]
```

Exactly the classical trio — the same billing our own axiom-clean theorems
carry. **No `sorryAx`, no custom axioms.**

Static sweep over the whole ~70-file `OAI/NumberTheory/DirichletL/` subtree:

- `^axiom` declarations: **0**
- `sorry`: **0**
- `native_decide`: **0**
- `unsafe def/lemma`, `implemented_by`, `@[extern]`: **0**

Comparator contract: `ComparatorChallenges/QuasiRiemannHypothesis.lean`
challenges exactly

```lean
theorem riemannZeta_ne_zero_of_seven_eighths_lt_re
    {s : ℂ} (hs : (7 / 8 : ℝ) < s.re) : riemannZeta s ≠ 0
```

and the library proves precisely that signature (byte-identical binder
structure), as a two-line corollary of
`SevenEighths.ProbeFinalAssemblyUnconditional.zeta_nonzero`.

## Part 3 — certificate anatomy (what we did NOT re-derive)

`DetectorCertifiedBands` is not a list of floats: it is a *predicate*
parameterized by the gap data `D : HighData (β − 7/8)` and source data
`F : SourceData D`, with band constants `1/4`, `9/4`, `33/50` and
data-dependent `kappaPlain D`, `stageError D`. The numerical content lives in
the Gaussian-theta detector pipeline (`Detector/`, `Energy/`, `Moments/`,
`Contours/`, `HeathBrownIteration/`, …). Re-deriving those numbers with our
interval pipeline would be a **port, not an audit** — the vendor-not decision
(`OAI_MATH_RECON.md` §6) stands. What Part 1–2 establish is different and
stronger for our purposes: the certificate consumer is a kernel-checked,
axiom-clean proof term.

## Part 4 — numerical extension: λ₂ certified (our ledger, our pipeline)

The Li chain now covers the first **two** Keiper coefficients. New script:
`scripts/routes/li_lambda2_certified.py` (data: `data/routes/rt_lc_lambda2.json`).

Method — same rigorous sandwich as RT2-LC: for
ρ = 1/2 + iγ, `arg(1 − 1/ρ) = 2 arctan(1/(2γ))` (exact identity), each
conjugate pair contributes `2(1 − cos(2θ_k)) ≥ 0` to λ₂, so with K = 2000
on-line zeros (verified via `mpmath.zetazero`, γ_K = 2515.29):

    λ₂ ∈ [S_K(2), S_K(2) + T_K(2)] = [0.090576382823, 0.103286923022]

where T_K is the standard Riemann–von-Mangoldt tail bound. Closed form
(extracted from Keiper's generating function `log ξ(1/(1−z)) = −log 2 +
Σ λₙzⁿ/n`, coefficient of z²; unconditional theorem, no RH needed):

    λ₂ = 1 + γ − γ² − 2γ₁ − 2 ln 2 − ln π + π²/8 = 0.09234573522804667…

with γ = 0.5772156649… (Euler) and γ₁ = −0.0728158454… (first Stieltjes
constant). Gates, all PASS:

- **(a)** closed form ∈ certified interval ✓
- **(b)** λ₂ > λ₁: λ₂ − λ₁ = 0.069250026… > 0 ✓ (Keiper coefficients strictly
  increasing at the start — consistent with Li's criterion direction)
- **(c)** independent high-precision series check (central finite difference
  of `log ξ(1/(1−z)) + log 2` at h = 10⁻⁶): error 1.8e-13 ✓

## Part 5 — numerical extension: λ₃ certified (pipeline scales)

The ledger now covers the first **three** Keiper coefficients. New script:
`scripts/routes/li_lambda3_certified.py` (data: `data/routes/rt_lc_lambda3.json`).

Method — identical sandwich machinery at n = 3: each conjugate pair
contributes `2(1 − cos(3θ_k)) ≥ 0` to λ₃, tail bound with n² = 9; K = 2000
on-line zeros (γ_K = 2515.29):

    λ₃ ∈ [S_K(3), S_K(3) + T_K(3)] = [0.203657877722, 0.232256593171]

Closed form — **derived, not recalled**: PSLQ identification at 80 dps
against basis {1, γ, γ², γ³, γ₁, γγ₁, γ₂, ln 2, ln π, π², ζ(3)}, then
confirmed three independent ways (OEIS A104540; derivative route
λ₃ = ½·d³/ds³[s² ln ξ(s)]|₁, error 5.0e-51; Keiper generating-function
third difference, error 1.7e-10):

    λ₃ = 1 + (3/2)γ − 3γ² + γ³ − 6γ₁ + 3γγ₁ + (3/2)γ₂
         − 3 ln 2 − (3/2) ln π + (3/8)π² − (7/8)ζ(3)
       = 0.20763892055432480…

with γ₂ = −0.0096903631928723… (second Stieltjes constant) and
ζ(3) = 1.2020569031595942853… (Apéry). Gates, all PASS:

- **(a)** closed form ∈ certified interval ✓
- **(b)** λ₃ > λ₂ = 0.115293185326… > 0 ✓, and the two certified sandwiches
  are disjoint ✓
- **(c)** series check (5-point central third difference of
  `log ξ(1/(1−z)) + log 2`): error 1.7e-10 ✓
- **(d)** derivative route at 80 dps: error 5.0e-51 ✓
- **(e)** Lean-witness box check with exact `fractions.Fraction` arithmetic:
  under the same box reasoning the Lean proof uses (γ ∈ (0.5604, 0.594),
  the γ-atoms jointly bounded by monotone-cubic endpoint identities,
  γγ₁ boxed by constants, π² ∈ (3.1415², 3.1416²), ln 2 and ln π at the
  certified decimals), the decimal closed form lies in [0.159594, 0.296349]
  ⊃ (0.15, 0.3), and λ₃ − λ₂ ≥ 0.088616 > 0 ✓

Lean formalization **is done**: γ₂ and ζ(3) enter `Riemann.LiCriterion.lean`
as certified decimals `stieltjes2Certified` / `zeta3Certified` (no axiom);
`liLambda3_mem : λ₃ ∈ (0.15, 0.3)` and `liLambda2_lt_liLambda3 : λ₂ < λ₃` are
machine-checked. The γ-atoms γ³ − 3γ² + (3/2)γ (and the difference-cubic
γ³ − 2γ² + γ/2) are bounded JOINTLY by monotonicity endpoint identities
(`cubicQ0_gt_endpoint`, `cubicQ0_lt_endpoint`) — the same concavity-product
pattern that certified λ₂, one degree higher. Axiom audit: classical trio
only (`propext, Classical.choice, Quot.sound`) across all nine new
declarations.

## Bottom line

1. `Riemann.quasiRH` is no longer trust-by-provenance only: the external
   chain is **independently rebuilt and axiom-audited** on our host.
2. Our own certified Li chain now covers λ₁, λ₂ **and** λ₃ with positive
   margins λ₂ − λ₁ = 0.0693 and λ₃ − λ₂ = 0.1153 — a certified,
   strictly-increasing Keiper-coefficient ledger to n = 3.
3. Lean formalization of λ₂ **is done**: γ₁ enters `Riemann.LiCriterion.lean`
   as the certified decimal `stieltjes1Certified` (no axiom — same pattern
   as all numerical certificates in this repo); the closed form is
   machine-checked as `liLambda2 ∈ (0.07, 0.15)` (`liLambda2_mem`),
   enclosing the certified interval [0.090576382823, 0.103286923022], and
   `liLambda1_lt_liLambda2 : λ₁ < λ₂` proves gate (b) formally. Axiom audit:
   classical trio only (`propext, Classical.choice, Quot.sound`). The
   identity of the decimal with the true Stieltjes constant remains external
   mathematical content — exactly what this document certifies.
