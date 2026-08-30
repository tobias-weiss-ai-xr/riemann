# Zero-Sliver Margin: the min|1−λ| Falsification Protocol

**EPIC-4 / Sprint 6 continuation** — Experiment 19k, 2026-08-30
Files: `scripts/_corner_sweep.py`, `scripts/_corner_deep.py`, `scripts/_corner_nmaxdep.py`,
`scripts/_spec_dump.py`, `scripts/_zero_margin_map.py` (gitignored temp),
`data/spectral-radius/zero_margin_map.json` (gitignored).

---

## 1. Why min|1−λ|, not ρ(L_s) < 1

RH is equivalent (Mayer 1990; Bonanno 2022 "eigenvalue-1"; Möller–Pohl 2011) to

    det(I − L_s) ≠ 0   for Re(s) > 1/2          ⟺   1 ∉ Spec(L_s).

The frequently quoted "ρ(L_s) < 1" is a **strictly stronger** statement
(ρ < 1 ⇒ 1 ∉ Spec, converse requires *no eigenvalue of modulus ≥ 1*, not just
no eigenvalue equal to 1).  Two facts make the distinction load-bearing:

1. **The full operator already has ρ > 1 inside the strip** — the constant
   mode is an almost-eigenfunction with eigenvalue ζ(2σ) → ∞ as σ → ½⁺
   (rigorous: λ₁(σ) ≥ ζ(2σ) × (inner product) → ∞ at t = 0; numerically
   7.57 at (0.51, 0)).  So "ρ(L_s) < 1 for Re(s) > 1/2" is *false* for the
   full operator; the project's `spectralRadiusConjecture` (Lean
   `TransferOperator.lean`, `axiom spectralRadiusConjecture : spectralRadius s < 1`)
   is intended for the **boundary-corrected** operator L_s⁰
   (spectrum = full spectrum minus the leading branch).

2. **Even for the corrected operator the ρ < 1 reading is over-strengthened.**
   Deep in the strip the full operator's *second* eigenvalue (which equals
   ρ(L_s⁰) under the exact rank-one correction) is close to 1 from both sides:
   at (0.505, 150) the converged part of the numerics gives |λ₂| ≈ 1.010
   (slow-tail drift, not resolvable below σ ≈ 0.51).  If |λ₂| genuinely
   exceeds 1 there, then `rhImpliesSpectralRadius` (RH ⇒ ρ(L_s⁰) < 1,
   Lean `sorry`) is *false as literally stated*, while `1 ∉ Spec` still holds —
   the two are NOT equivalent.  The Lean doc comment "equivalent to RH via the
   Mayer identity and the eigenvalue-1 equivalence" is therefore imprecise:
   the correct avatar of RH is `1 ∉ Spec(L_s)` (and for the corrected operator,
   the Bonanno eigenvalue-1 statement).

**Conclusion.**  The numerically safe, honest RH proxy is

    m(s) := min_j |1 − λ_j(s)|     (distance of the spectrum to the critical point 1).

RH ⟺ m(s) > 0 for every Re(s) > 1/2.  A numerical detection of m(s) = 0 at
any σ > 1/2 would be an explicit counterexample (an eigenvalue exactly 1 ⟺ a
zeta zero off the critical line).

---

## 2. Converged corner map (corrected-ρ = |λ₂| of the full matrix, Nyström N=256, n_max=8000)

Convergence verified: N = 120/160/200/320 agree to 6 dp; n_max = 1000…32000
agree to 2e-3 at σ ≥ 0.52 and 1e-5 at σ ≥ 0.55 (slow-tail regime only below
σ ≈ 0.51).

    σ     |λ₂(0)|   max_t |λ₂|   at t      (deep-corner rows, N=256/n_max=8000)
    0.55  0.697     0.9193       100
    0.53  —         0.9518        90
    0.52  —         0.9707       150         ← tightest converged sliver
    0.51  —         0.999        ~150*       (* λ₁ itself = 0.9991 at (0.51,150);
                                              below σ≈0.507, |λ₂|→~1.01, slow-tail regime)
    0.60  0.634     0.8496       100         (reference)

All values < 1 for σ ≥ 0.52 with margin ≥ 0.03; margin collapses to ~1e-3 at
σ = 0.51 and becomes numerically unresolvable (∿1.010, slow downward drift in
n_max) for σ ≤ 0.507 at t ≈ 150.  This sharpens Exp 19e's "worst 0.950@(0.55,100)"
and 19i's "0.855@(0.60,750)": the true worst sliver is the corner
(σ, t) ∈ [0.505, 0.56] × [75, 200], and it tightens monotonically toward
σ = ½⁺.

## 3. The eigenvalue-1 ↔ zeta-zero correspondence (numerically confirmed at height ~125)

The nearest-to-1 eigenvalue creeps toward the critical point 1 exactly at
**zeta-zero heights**:

  σ = 0.51, t scan near γ₄₁ = 124.2568   →   min|1−λ| = 0.0211 at t = 124.5
  σ = 0.51, t = 100 (Δ from γ₃₀ = 1.3)   →   min|1−λ| = 0.2135
  margin map t ∈ [88, 160] (41 dips at depth 0.02–0.06) — dips cluster at
  zero heights γ₂₈…γ₅₇ (e.g. 114.4 near γ₃₆ = 114.32, 124.8 near γ₄₁ = 124.26,
  127.2 near γ₄₂ = 127.52, 131.2 near γ₄₄ = 131.09, 157.6 at γ₅₇ = 157.60),
  smeared by the non-zero σ (floor ~0.02).

At a fixed zero height, m(σ+it) decreases toward 0 as σ → ½⁺ (at γ₄₁:
0.1167@0.55 → 0.0825@0.51; the collapse to 0 is not numerically resolvable
below σ ≈ 0.51 because the n-sum tail is O(n_max^{−(2σ−1)})).  The
eigenvalue that approaches 1 does so with phase → 0 (e.g. λ = 0.9792 − 0.0037i
at (0.51, 124.5)): it creeps into the critical point 1 from inside the unit
circle.  No eigenvalue equals 1 anywhere tested — consistent with RH and with
all zeta zeros (up to the verified heights) lying on the critical line.

## 4. Honesty corrections to the repo record

1. **`rho(L_s⁰)<0.30 for |t|≤100` (Sprint 2 / Lean `spectralRadiusBound_numerical
   = 0.30`)** is inconsistent with the well-converged Nyström value
   |λ₂(0.6, 100)| = 0.8496 (and 0.95 at σ = 0.53).  The 0.30 was a crude
   Fourier-box bound dominated by a "ghost eigenvalue ≈ 0.25"; it is NOT an
   upper bound on the true corrected-ρ and should not be quoted as one.
2. **`spectralRadiusConjecture` ("ρ(L_s⁰) < 1") is strictly stronger than RH.**
   It implies RH (`spectralRadiusImpliesRH`, fine), but the converse
   (`rhImpliesSpectralRadius`) is questionable: converged numerics give
   corrected-ρ → 1⁻ at σ = 0.51 and suggest |λ₂| > 1 for σ ≲ 0.507 at
   t ≈ 150, both compatible with `1 ∉ Spec` (RH).  The Lean avatar of RH
   should ultimately be restated as `1 ∉ spectrum(L_s)` /
   `det(I − L_s) ≠ 0` for Re(s) > 1/2.  (Deferred: changing the conjecture
   touches the equivalence theorems `spectralRadiusImpliesRH` /
   `rhImpliesSpectralRadius`, both currently `sorry` sketches.)

## 5. Falsification protocol (the live lever)

For a certified zero-free sliver down to ½+ε one must show m(s) > 0 on
[½+ε, 1] × [0, T].  The certified-numerics budget concentrates in the corner
(σ, t) ∈ [0.505, 0.56] × [75, 200] (corrected-ρ ∈ [0.85, 1.0)); outside it the
margin is ≥ 0.15.  Next numerical targets:
  (a) Nisoli/DFLY-style rigorous enclosure of m(s) at the 5–6 tightest points
      (highest |λ₂|) — target margin ≥ 1e-2 with certified error < margin;
  (b) extend the margin map to t up to 1000 at σ = 0.52 (large-t plateau of
      the corrected branch) to confirm the worst is near t ≈ 75–200;
  (c) track the eigenvalue that creeps to 1 at zero heights as σ → ½⁺
      (its rate ∝ |Z_S'(½ + iγ)|·(σ − ½) is a clean slope to measure once
      σ = 0.51 → 0.505 is certified).

---

## 6. High-t refinement (Experiment 19l): the tight region is NOT corner-only

The margin map was extended globally in t (N=256–512, nmax=6000–8000, log-stable
barycentric weights to avoid N≥384 overflow).  Definitive results at σ=0.52 over
t ∈ [0, 3000]:

| t | corrected-|λ2| | m = min|1−λ| | notes |
|---|---|---|---|
| 0   | 0.774  | 0.799 | constant-mode removed (|λ1|=7.72) |
| 125 | 0.971  | 0.042 | corner dip (near γ41) |
| 600 | 0.965  | 0.045 | first high-t dip |
| 900 | 0.972  | 0.037 | dip (N=512) |
| 1100| 0.985  | **0.015** | tightest height found (zeros #729–733 = 1098.8–1102.6; N=512) |
| 1500| 0.970  | 0.082 | plateau |
| 3000| 0.979  | 0.068 | plateau persists |

**Correction to §2/§5**: the single tight sliver [0.505,0.56]×[75,200] is NOT the
whole story — the corrected spectral radius develops a **broad high-t plateau
t≈900–1200 with |λ2| ≈ 0.98–0.99 at σ=0.52**, and the margin dips there are at
least as deep as at the corner (0.015 at t=1100 vs 0.042 at t=125).  At σ=0.51,
t=1100 (N=512): **|λ2| = 1.010 > 1**, |λ1| = 1.028 — the unit-circle crossing
regime found in 19k at (0.505,150) extends to high t along the zero-rich strand
(gaps ~1.2–1.6 near 1100); yet m = 0.0107 (never equal to 1).  Per σ, global
min-m over all tested t: 0.011 (σ=0.51), 0.015 (σ=0.52), 0.039 (σ=0.53),
0.084 (σ=0.55) — roughly m ≈ c·(σ−½) with c ≈ 2–3.

**Numerical caveat (honest)**: at t > 800 the N-convergence is only ±1%
(N=384 vs N=512 |λ2| differ by ~1e-2), so high-t |λ2| values carry ±0.01
uncertainty.  The qualitative structure (plateau ~0.98, dips at zero heights,
no eigenvalue equal to 1) is robust; precise certified numbers there require
higher N and/or the DFLY/Nisoli enclosure machinery, and the certified corner
remains [0.505,0.56]×[75,200] where N=128–256 suffices.

**Net**: the falsification lever has two arms — the corner (tight margin near
point 1, N-converged) and the high-t strand t≈900–1200 (corrected |λ2|→~1.0 as
σ→½⁺, N-marginal).  Both stay below the critical point 1 (m ≥ 0.011 at
σ = 0.51), consistent with RH; a certified enclosure must cover BOTH.
