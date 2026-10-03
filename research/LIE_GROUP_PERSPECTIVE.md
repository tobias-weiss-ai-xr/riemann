# EPIC-4 / Lie Group Perspective — Making the Representation Theory of PSL(2,ℝ) Explicit

**Date**: 2026-09-11
**Status**: Position note (no new theorems; reinterprets 19g + the transfer-operator program)
**Scope**: The program is already the representation theory of G = PSL(2,ℝ), implicitly.
          Making it explicit explains *why* the envelope obstruction (19g) holds, identifies
          exactly what "t-anisotropic input" means representation-theoretically, and
          sharpens the next experimental steps.

---

## 1. The Lie Group in the Room

The Gauss map's inverse branches x ↦ 1/(n+x) are fractional linear transformations
with integer coefficients — elements of PGL(2,ℤ) ⊂ PGL(2,ℝ) = PSL(2,ℝ) (as a Lie
group; PGL(2,ℝ) ≅ PSL(2,ℝ) canonically). So:

- **G = PSL(2,ℝ)** acts on the boundary ℝ̂; PSL(2,ℤ) is the lattice.
- **Iwasawa decomposition** G = K·A·N (K = SO(2), A = diagonal, N = upper unitriangular):
  the Gauss/continued-fraction dynamics is the combinatorics of the N-direction
  relative to the lattice — the boundary map of the geodesic flow on
  PSL(2,ℤ)\ℍ (modular surface).
- **Mayer identity / Möller–Pohl (2011)** (already used in this repo,
  see NUCLEARITY_SYNTHESIS.md §2.3): the Selberg zeta function of PSL(2,ℤ) is the
  Fredholm determinant of the transfer-operator family. The spectral data of L_s
  *is* Lie-theoretic spectral data of G.

## 2. The Dictionary

| This repo / dynamical side | Lie / representation side |
|---|---|
| spectral parameter s = σ+it | principal-series parameter of PSL(2,ℝ); σ=1/2 is the **tempered** (unitary) axis |
| Ruelle operator L_s on boundary functions | boundary (Berezin/Heintze-type) realization of the principal series, restricted to the lattice |
| Fourier basis L_{k,l} (Sprint 2 infinite matrix) | **K-type decomposition** — Fourier modes on the boundary = SO(2)-weight |
| det(I−L_s) = Z_Sel(s) | Selberg zeta = spectral determinant of G on PSL(2,ℤ)\ℍ |
| λ₁(σ), pressure P(σ) | spherical (bi-K-invariant) part of the representation |
| Ruelle domination \|λ₁(σ+it)\| ≤ λ₁(σ) | unitary twist (K-spherical character) cannot raise Perron–Frobenius pressure |
| envelope obstruction (19g) | **σ-only bounds are K-spherical; the strip (1/2,1) provably cannot be closed by spherical input** |
| SL(2,F_p) Cayley graphs (main branch) | same Lie type A₁ over finite fields; Ramanujan bound ⇔ temperedness (LPS) |

## 3. What 19g Says in Representation Language

The envelope obstruction — no f(σ) < 1 with |λ₁(σ+it)| ≤ f(σ) in (1/2,1] — is
exactly the statement:

> **Spherical spectral data cannot reach the tempered axis.**
> Any bound depending only on σ sees only the K-spherical vector of the
> principal series; on that vector the eigenvalue modulus is ≥ 1 throughout
> (1/2,1]. RH (ρ(L_s) < 1 for Re(s) > 1/2) therefore *requires* input from
> non-spherical K-types — the t-anisotropy that 19g proves is unavoidable.

This is the same mechanism as on the finite-field side: LPS Ramanujan graphs are
"tempered" representations of PGL(2,F_p); non-Ramanujan failures are
non-tempered constituents. One program, two fields, one criterion: **temperedness**.

## 4. Where the Non-Spherical Input Lives Here

- **Sprint-2 Fourier matrix L_{k,l}**: the (k,l) indices are K-weights. The
  boundary-corrected operator whose ρ < 1 was verified numerically (ρ < 0.30 on
  Re(s)=1/2, |t| ≤ 100) acts on the full K-type ladder — the spherical restriction
  (k=l=0 block) is precisely what 19g proves cannot suffice.
- **LMFDB pipelines** (`train_lmfdb_zeros.py`, `collect_lmfdb_zeros.py`): Hecke
  eigenvalues / L-function zeros of GL(2) forms = the arithmetic K-type data
  (Maass forms and weight-k modular forms are the K-finite and K-invariant
  vectors of automorphic representations of G). Murmurations = K-type statistics.
- **Nisoli DFLY certified bounds**: already non-spherical (acts on function
  spaces, not just constants) — the one ingredient that reaches σ = 3/4 + ε.

## 5. Concrete Next Steps (ranked, small)

1. **K-type-resolved numerics** (~1 day): recompute the Sprint-2 spectrum of
   L_{σ+it} with the Fourier basis split into |k|-blocks. Test:
   ρ(block_k(σ+it)) strictly decreasing in |k| ≥ 1 — a direct measurement of
   the anisotropy mechanism and of how many K-types the ρ<1 proof must control.
2. **Certified ρ<1 per K-block at σ = 1/2 + ε** (DFLY on each block): if every
   block with |k| ≥ 1 is < 1 by a uniform margin and the k=0 block is handled
   by the boundary correction, the strip closes blockwise — this is the
   representation-theoretic rephrasing of the Sprint-5/6 goal.
3. **Lean**: no new surface needed now — the 19g axioms already encode the
   obstruction. A genuine Lie-group formalization (SL(2,ℝ) as Lie group,
   Iwasawa decomposition) would hook into `Riemann/TransferOperator.lean` but
   requires mathlib's manifold/Lie-group API; deferred (mathlib not cached on
   this host; `lake update` ≈ 30 min + build).
4. **Cross-field experiment**: correlate K-type statistics (murmurations) with
   the SL(2,F_p) Ramanujan ratio table (`RamanujanProperty.lean`) — temperedness
   as a single observable across both fields. Low priority; exploratory.

## 6. References

- Möller–Pohl 2011 (arXiv:1103.5235) — Z_Sel = det(I−L_s), Hecke triangle groups.
- Isola 2003; Bonanno–Isola 2009; Giulietti–Liverani 2014 — Hilbert/anisotropic
  Banach frameworks for L_s (already catalogued in NUCLEARITY_SYNTHESIS.md).
- Dolgopyat 1998 — cancellation from non-spherical directions (oscillatory
  bounds); the classical shape of "t-anisotropic input".
- Helgason, *Groups and Geometric Analysis* — boundary theory, spherical functions.
- Lubotzky–Phillips–Sarnak 1988 — Ramanujan graphs as temperedness, PGL(2,F_p).
- This repo: `RUELLE_DOMINATION.md` (19g), `NUCLEARITY_SYNTHESIS.md`,
  `TRANSFER_OPERATOR_MATH.md` §Selberg, `lean/Riemann/TransferOperator.lean`.
