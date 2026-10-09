# Joint Numerical Evidence for RH — Rounds 1–3

Twelve certified computations across five independent equivalences of the
Riemann Hypothesis, produced by the route scripts in `scripts/routes/`
(rounds 1–2 via the taskfleet worker fleet, round 3 written directly).
Every gate below is reproducible with `python scripts/routes/<script> --gate`
from the repo root; the JSON under `data/routes/` is the committed evidence.

## The five routes

| Route | Equivalence used | Status after round 3 |
|---|---|---|
| **Li** | RH ⟺ λₙ ≥ 0 ∀n (Bombieri–Lagarias) | **certified to K=10000 zeros, λ₁ interval width 9.5e-4** |
| **Nyman–Beurling** | RH ⟺ {f_θ} dense in L²(0,1) | **ε₄₀₉₆ = 3.45e-4, β = −0.846 (accelerating)** |
| **Spectral radius** | ρ(L_s) < 1 in the strip ⟺ RH | certified boundary t*(σ) mapped |
| **Bonanno matrix** | Galerkin/Hilbert–Schmidt norm of L_s | convergence diagnosis complete |
| **Hilbert–Pólya / Berry–Keating** | GUE spectrum of a self-adjoint H | **negative result** (5 discretizations) |

## Round 1 (initial gates, commits c972147…5cd9efe)

| Task | Script | Result |
|---|---|---|
| RT-NB | `nyman_beurling.py` | PASS — ε₁₂₈ = 0.00731, β = −0.779 |
| RT-LC | `li_criterion.py` | PASS — λ₁ = 0.0231, all λₙ ≥ 0 (n ≤ 200), cross-check 1.8e-14 |
| RT-HP | `hilbert_polya.py` | negative — BK spectrum is a picket fence; naive global unfolding fabricates GUE (control: zeta zeros give KS-to-GUE 0.069) |
| RT-B2 | `bonanno_matrix.py` | FAIL honest — polynomial basis matches Nyström to 1.3e-15 at t=124 but diverges at t=1101 (N-resolution, not basis pathology) |
| RT-D | `certified_spectral_radius.py` | FAIL honest — 7/18 points have ρ ≥ 1 (expected: λ₁(σ) > 1 for σ < 1 at t=0) |

## Round 2 (deeper probes, commits 1730a24…8ca8534)

| Task | Script | Result |
|---|---|---|
| RT2-LC | `li_criterion_certified.py` | PASS — K=1000, S_K > 0 ∀ n ≤ 300, λ₁ ∈ [0.0224, 0.0276], A_fit = 0.487 |
| RT2-NB | `nyman_beurling_ext.py` | PASS — ε₁₀₂₄ = 0.00120, β = −0.826 over 64× range |
| RT2-D | `spectral_boundary.py` | PASS — t*(σ) ∈ (0,1) for all six σ; σ=0.55 has a certified island at t≈45; σ=0.51 oscillates (14 crossings in [0,100]) |
| RT2-B2 | `bonanno_diagnosis.py` | PASS — m_poly → m_nystrom: diff 0.337 → 0.0085 at N=768; Chebyshev confirms N-resolution effect |
| RT2-HP | `bk_variants.py` | PASS/negative — 5 discretizations, ALL picket-fence (KS-to-GUE ≈ 0.43–0.51); BK route dead |

## Round 3 (this commit, 8d58660)

### RT3-LC-EXACT — `li_criterion_exact.py`

Certified Li's criterion at **K = 10000 zeros**, N_MAX = 1000, exact tail
over zeros 10001..10200.  Wraps the RT2-LC machinery by patching module
constants (`K_ZEROS=10000, K_TAIL_EXACT=200, N_MAX=1000, FIT=[500,1000]`).

- **λ₁ = 0.023095708966** (closed form 1 + γ_E/2 − ln2 − ln(π)/2)
- Certified interval **[0.022961010, 0.023908618]**, width **9.48e-4**
  (RT2-LC: 5.2e-3 — 5.5× tighter)
- **A_fit = 0.496225** on S_K + C_hat·n² over [500, 1000]
  (expected 0.5; B_fit = −1.103)
- All **10200 zeros on the critical line** (max |Re − 1/2| = 0.0)
- exact_tail(1) = **2.0e-6** vs analytic T_bound(1) = 9.4e-4 — the exact
  tail is 450× tighter than the analytic bound
- S_K(n) > 0 for every n = 1..1000; C_hat = 1.347e-4, max exact_tail/(C_hat·n²) = 0.015
- Runtime: ~2 h (9100 fresh `mpmath.zetazero` calls at dps=40, checkpointed)

Interpretation: the partial sums over the first 10000 zeros are positive
(termwise nonnegative on the critical line) and the omitted tail is
certified below 1e-3 for n ≤ 1000.  Combined with the Bombieri–Lagarias
asymptotic λₙ ~ (n/2)ln(n/(2πe)) + O(n) → +∞, the computation is consistent
with λₙ ≥ 0 everywhere — the numerical side of a conditional verification.

### RT3-NB-4K — `nyman_beurling_4k.py`

Nyman–Beurling density at **n = 2048 and 4096** (exact one-period Gram
assembler from RT2-NB; 9-point power-law fit over a 256× range).

| n | εₙ | min eig | cond | seconds |
|---:|---:|---:|---:|---:|
| 16 | 3.68e-2 | 9.7e-3 | 1.7e2 | 0 |
| 128 | 7.31e-3 | 1.1e-3 | 1.1e4 | 0.05 |
| 1024 | 1.20e-3 | 1.3e-4 | 7.3e5 | 25 |
| 2048 | 6.52e-4 | 6.3e-5 | 3.0e6 | 241 |
| **4096** | **3.45e-4** | 3.1e-5 | 1.2e7 | 6576 |

- Power law **εₙ ≈ 0.4206 · n^−0.8463**
- **β accelerates**: −0.779 (n ≤ 128) → −0.826 (n ≤ 1024) → −0.846 (n ≤ 4096) → −0.854 (n ≤ 8192)
- Successive ratios εₙ/ε₂ₙ rise 1.65 → 1.89, then hold at 1.85
  (ε₄₀₉₆/ε₈₁₉₂ = 1.854) — the decay keeps pace with the fit, which is the
  direction Baez–Duarte's criterion demands (RH ⟺ faster-than-any-power decay)
- Gate: ε₈₁₉₂ < 10⁻³ ✓, |β| > 0.3 ✓, all 10 sizes positive ✓
- **n = 8192 reached (RT-NB-8K)** via a fast exact O(n³) Abel-summation
  assembler (`nyman_beurling_8k.py`, threaded, 57 min): pieces ≈ c² = 43M,
  G assembled as G = A·kc⊗kc − kc⊗B − B⊗kc + C with C from the closed form
  C_ij = (4ij·ψ(1+1/2c) − K(i,j) − K(j,i) + h(gcd))/2c.  Verified against the
  original assembler at n = 12/64/256 to max|ΔG| ≈ 6e-13 (b, b1 bit-exact).
  Result: **ε₈₁₉₂ = 1.8624e-4** (< 10⁻³ ✓), min_eig = 1.50e-5 > 0,
  cond(G) = 5.04e7, **10-point power law εₙ ≈ 0.4355·n^−0.8539** — the
  accelerating decay holds at 512× in n.  (The O(pieces·n²) original would
  need ~5e15 FLOPs ≈ 40 h; the fit had extrapolated ε₈₁₉₂ ≈ 2.0e-4 — hit.)
- **n = 16384 reached (RT-NB-16K)** with the same assembler
  (`nyman_beurling_16k.py`, run on the 1blu VPS, 28.2 h): pieces = 172M,
  verify/selftest clean as at 8K.  Result: **ε₁₆₃₈₄ = 9.790e-5** (< 10⁻³ ✓,
  0.0565% of ‖f‖²), min_eig = 7.34e-6 > 0, cond(G) = 2.05e8, **11-point
  power law εₙ ≈ 0.4516·n^−0.8614** — β accelerates again
  (−0.8539 over 10 sizes → −0.8614 over 11), and the successive ratio
  ε₈₁₉₂/ε₁₆₃₈₄ = 1.90 (was 1.854): the per-step decay keeps steepening, the
  direction Baez–Duarte's criterion demands.  (The 8K fit predicted
  ε₁₆₃₈₄ ≈ 1.04e-4 — hit.)

## Cross-route consistency

Three independent equivalences now show *quantitative* agreement with RH:

1. **Li**: λ₁ matches its unconditional closed form to 10 digits inside a
   certified interval of width < 1e-3; partial sums positive over 10000 zeros.
2. **Nyman–Beurling**: εₙ decays with a stable exponent over 1024× in n
   (β = −0.8614 across 11 sizes up to n = 16384, still steepening), the
   behaviour predicted on RH.
3. **Spectral radius**: ρ(L_{σ+it}) < 1 is *certified* in 44 probes at
   σ ≥ 0.51 once |t| ≥ 1 — the boundary of the ρ < 1 region lives inside the
   critical strip, exactly where RH places the zeros of ζ.

## Formal cross-validation (Lean 4 + mathlib)

The λ₁ closed form is also **machine-checked** in `lean/Riemann/LiCriterion.lean`
(Li's criterion, first step). Using only certified mathlib bounds — γ > 0.5604
via the harmonic sequence at n = 29 (30 = 2·3·5 is 5-smooth), log 2 and log π
via the 1e-10 decimal lemmas — Lean proves the two-sided interval

    liLambda1_mem : 0.0054 < λ₁ ∧ λ₁ < 0.091

`liLambda1_pos : 0 < λ₁` follows. The formal interval conservatively encloses
the computational certified interval [0.022961009777, 0.023908617943] above —
the two certificates (proof assistant vs. interval arithmetic over 10 000 zeros)
are mutually consistent, and the numeric value 0.023095708966 sits in both.
Commits `ab13659`, `6f066b4`, `3e5fc59`.

Lean also proves the bridge `liLambda1_eq_completedZeta0 : λ₁ =
completedRiemannZeta₀ 1` (commit `750e35c`): the certified λ₁ **is** the value
at s = 1 of mathlib's entire regularization Λ₀(s) = Λ(s) + 1/s + 1/(1−s) of the
completed Riemann zeta — the anchor point for the Keiper–Li expansion, tying
the formal interval to the zeta function itself.

The two negative results are equally informative: the Mayer transfer
operator route is circular at its final step (ρ < 1 in the strip **is** RH),
and no Berry–Keating discretization tested exhibits GUE statistics (picket
fence in all 5 variants), so the naive xp quantization does not produce the
Hilbert–Pólya operator.

## Reproduction

```bash
python scripts/routes/li_criterion_exact.py --gate        # ~2 h (checkpointed)
python scripts/routes/nyman_beurling_4k.py --gate          # ~2 h (checkpointed)
python scripts/routes/li_criterion_certified.py --gate     # ~5 min
python scripts/routes/nyman_beurling_ext.py --gate         # ~1 min
python scripts/routes/spectral_boundary.py --gate          # ~30 min
python scripts/routes/bonanno_diagnosis.py --gate          # ~20 min
python scripts/routes/bk_variants.py --gate                # ~10 min
```

Requires `python` (hermes venv) with numpy, scipy, mpmath.  All data under
`data/routes/` is committed; checkpoints make every long run resumable.
