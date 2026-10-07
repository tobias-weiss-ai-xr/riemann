# Recon: the OpenAI math release (`../math`) — what it contains and what it means for us

Recon date: 2026-10-07. Source: `../math` (sibling of this repo), README +
CONTENTS.md + `lean/` tree inspected directly.

## What it is

A collection of **722 mathematical manuscripts in 372 families** produced by an
internal OpenAI model (~4000 problems posed, ~3 h of ChatGPT Pro thinking
compute each). Many families carry **Lean formalizations** in a single large
library: Lean **4.34.1**, mathlib pinned at **d13f23b**, with patched external
dependencies (`patches/*-lean4341.patch`). Verification model: `comparator`
challenge files — each is a `sorry`-stubbed statement; the library must prove
exactly that signature.

## Family 003 — the quasi-Riemann hypothesis (the relevant one)

Three preprints, one Lean formalization:

| Preprint | Statement |
|---|---|
| *The Quasi-Riemann Hypothesis: A Zero-Free Half-Plane Re(s) > 7/8* (Sep 30) | ζ and **every Dirichlet L-function** zero-free for **Re s > 7/8**, pole at s = 1 excepted; same half-plane for finite-order Hecke L-functions over ℚ(√−3) |
| *Alternate 11/12 proof* (Oct 5) | same conclusion with Re s > 11/12, different proof |
| *Uniform exclusion of Landau–Siegel zeros* (Oct 1) | ∃ c > 0: every real zero β of every primitive nonprincipal real Dirichlet L-function satisfies (1−β) log q ≥ c |

Lean artifacts (verified present in the tree):

- Challenge statement: `lean/ComparatorChallenges/QuasiRiemannHypothesis.lean` —
  `theorem riemannZeta_ne_zero_of_seven_eighths_lt_re {s : ℂ} (hs : (7/8 : ℝ) < s.re) : riemannZeta s ≠ 0`
- Proof: `OAI.riemannZeta_ne_zero_of_seven_eighths_lt_re` in
  `OAI/NumberTheory/DirichletL/Nonvanishing.lean` — a two-line corollary of
  `SevenEighths.ProbeFinalAssemblyUnconditional.zeta_nonzero`, which consumes
  `detector_certified_bands : DetectorCertifiedBands` — a **finite certified
  certificate** (explicit constants: bands 1/4, 9/4, 33/50, `kappaPlain`,
  `stageError`) plus a Lean-side theorem that the certificate implies
  nonvanishing (`dirichlet_of_certified`).
- Supporting machinery: ~70 files under `OAI/NumberTheory/DirichletL/`
  (Detector/ProbeWindows/GaussianTheta/Moments/Contours/HeathBrownIteration/…).
  Uses mathlib's **Hadamard three-lines theorem**
  (`Mathlib.Analysis.Complex.Hadamard`) and Borel–Carathéodory.
- Already has downstream use inside the release: the primitive-roots paper
  cites it as "the uniform Hecke zero-free theorem".

## What we can learn

1. **The proven zero-free frontier moved.** A fixed half-plane Re s > 7/8 < 1
   is now a theorem for ζ (and all Dirichlet L), formalized. Our FRONTIER
   placeholder `no_zeros_right_half_plane` (no zeros in (1/2, 1)) is thereby
   *narrowed, not closed*: the slice (7/8, 1) is externally proven. Recorded
   as §3d in `research/FRONTIER.md`.
2. **Our numerical evidence goes beyond the proven region.** The certified
   spectral-radius probes (ρ(L_{σ+it}) < 1 at σ ≥ 0.51, |t| ≥ 1, RT2-D) sit
   ~0.3 deeper in the strip than the 7/8 boundary. The binding constraint on
   what remains open is now (1/2, 7/8].
3. **Methodology cross-validation.** Their proof shape — finite certified
   numerical object + Lean glue theorem — is exactly the pattern of our
   RT3-LC-EXACT intervals and `certified_spectral_radius.py`. Two independent
   formal pipelines (OpenAI's and ours) using certified certificates for zeta
   statements is a sanity check on the approach.
4. **Hadamard factorization is still absent from mathlib** (only the
   three-lines theorem exists). Their zero-free-region proof confirms that
   regions don't need factorization — but our AGENTS.md long-term goal 4
   (Hadamard product gap as the obstruction to a full RH formalization)
   stands unchanged.
5. **Nothing on our routes.** No Nyman–Beurling, no Li's criterion, no
   Fredholm determinants, no SL(2,F_p) Cayley/spectral-gap work, no transfer
   operators anywhere in the 372 families. Our evidence chain occupies
   territory even a 722-paper model attack did not touch.
6. **Vendor-not.** Porting is a project, not a task: toolchain mismatch
   (4.34.1 vs our 4.33.0-rc1), ~70-file DirichletL subtree, 10+ patched
   external dependencies, mmap/`vm.max_map_count` build caveats. Cite and
   cross-reference instead.

## Toolchain facts (for a future port)

- Their pin: `leanprover/lean4:v4.34.1`, mathlib `d13f23b723b8a846827a245b89c10fc7d3f11612`.
- Ours: 4.33.0-rc1 (older mathlib). The three-lines theorem
  `Mathlib.Analysis.Complex.Hadamard` exists in BOTH — usable by us today.
- Their build caveats: whole-library builds can hit `vm.max_map_count`;
  build per-directory instead (`lake build OAI.NumberTheory.DirichletL.Nonvanishing`).
