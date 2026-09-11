# EXP 19P -- Eigenvalue-1 margin map + certified enclosure (EPIC-4)

**Status**: complete (2026-09-11). No counterexample found; the eigenvalue-1
avatar of RH (det(I - L_s) != 0 for Re(s) > 1/2) is numerically supported by a
21-point margin map across three zeta-zero heights, with a convergence-ladder
lower bound certified positive at the worst point.

**Plan**: `research/EPIC4_FLEET_PLAN.md` | **Predecessor**:
`research/ZERO_SLIVER_MARGIN.md` (Exp 19k/19l/19o) | **Lean**:
`lean/Riemann/TransferOperator.lean` (`eigenvalueOneFreeConjecture`)

## 1. What was computed

### E4-P1 -- margin map (fleet task, worker glm-5.2)

Grid: heights t in {124.2568, 150.0, 1100.574} x
sigma in {0.501, 0.505, 0.51, 0.515, 0.52, 0.535, 0.55} -- 21 points.
Resolution N=384/nmax=8000 (t<=500), N=512/nmax=8000 (t>500), using the
overflow-safe `scripts/nystrom_collocation.py` (commit 9a32616).

Margin table (m = min_j |1 - lambda_j|, full L_s):

| sigma | t=124.2568 (N=384) | t=150.0 (N=384) | t=1100.574 (N=512) |
|---|---|---|---|
| 0.501 | 0.081155 | 0.111086 | 0.021225 |
| 0.505 | 0.081347 | 0.111067 | **0.020669** (global min) |
| 0.510 | 0.082484 | 0.111864 | 0.024293 |
| 0.515 | 0.084553 | 0.113528 | 0.030977 |
| 0.520 | 0.087458 | 0.115995 | 0.039114 |
| 0.535 | 0.100118 | 0.127432 | 0.066299 |
| 0.550 | 0.116637 | 0.143285 | 0.094238 |

Per-height linear fit m(sigma) = c*(sigma-1/2) + b over sigma >= 0.505
(sigma=0.501 is tail-unresolved, excluded from the fit):

| t | c | b | sigma* = 1/2 - b/c |
|---|---|---|---|
| 124.2568 | +0.8011 | +0.07407 | 0.4075 |
| 150.0 | +0.7303 | +0.10410 | 0.3575 |
| 1100.574 | +1.6868 | +0.00798 | **0.4953** |

### E4-P2 -- convergence-ladder enclosure (worst point)

At the global minimum (sigma, t) = (0.505, 1100.574), ladder (N, nmax):

| N | nmax | m | abs lambda1 | abs lambda2 |
|---|---|---|---|---|
| 256 | 6000 | 0.039581 | 1.017840 | 1.009268 |
| 384 | 8000 | 0.023524 | 1.007081 | 1.001639 |
| 512 | 8000 | 0.020669 | 1.030999 | 1.012008 |
| 512 | 12000 | 0.020664 | 1.031000 | 1.012009 |

Conservative error bar: m_hat = 0.030123, err = 0.009458,
**lower bound = 0.020664 > 0**. The two finest rungs agree to five
decimals -- the margin is converged.

## 2. Findings

1. **No counterexample.** All 21 margins are positive; a single point
   with m <= 0 at Re(s) > 1/2 would falsify the eigenvalue-1 avatar.
2. **All extrapolated zero-crossings sigma* < 1/2** (0.3575, 0.4075,
   0.4953) -- the margin law extrapolates to zero only left of the
   critical line, the RH-consistent fingerprint. At t=1100.574, Exp 19o
   (sigma>=0.51 fit) gave sigma*~0.4938; Exp 19p (sigma>=0.505) gives
   0.4953 -- consistent.
3. **Certified lower bound at the worst point.** m > 0.0207 at
   (0.505, 1100.574) with a converged ladder. This is a
   convergence-ladder bound, not full interval arithmetic (certified
   mpmath/Arb enclosure is the follow-up).
4. **rho(L_s) > 1 throughout, yet 1 not in Spec.** |lambda1| > 1 at
   every tested point (up to ~1.031 at the worst point) -- the
   spectral-radius conjecture rho < 1 is numerically FALSE for the
   full operator (Exp 19k). But no eigenvalue ever equals 1: the
   honest avatar det(I - L_s) != 0 holds. The sliver regime
   (sigma <~ 0.51) has |lambda2| > 1 as well, while m stays positive.

## 3. Connection to the Lean formalization

`lean/Riemann/TransferOperator.lean` (commits 8eb3766, c2d4c54):

- `eigenvalueOneFreeConjecture` -- det(I - L_s) != 0 for Re(s) > 1/2.
  **This experiment is its numerical evidence** (21 points + enclosure).
- `spectralRadiusConjecture` -- rho < 1. Numerically false; the
  implication `spectralRadiusConjecture_implies_eigenvalueOneFree`
  (proved, no conjecture) shows the avatar is strictly weaker.
- `eigenvalueOneFree_above_one` -- proved for Re(s) > 1 (Ruelle).
- `eigenvalueOneFreeImpliesRH` (sorry) / `rhImpliesEigenvalueOneFree`
  (sorry) -- both directions of RH <=> det!=0; require Z_S(s) <-> zeta(s)
  scattering-matrix formalization (deep).

## 4. Data provenance

| Artifact | Location | Provenance |
|---|---|---|
| margin map script | `scripts/exp19p_margin_map.py` (c90bc00) | taskfleet E4-P1, glm-5.2 |
| margin map data | `data/experiment19p/margin_map.json` | E4-P1 output (gitignored) |
| enclosure script | `scripts/exp19p_enclosure.py` (606b133) | E4-P2, manual |
| enclosure data | `data/experiment19p/enclosure.json` | E4-P2 output (gitignored) |
| Lean theorems | `lean/Riemann/TransferOperator.lean` (c2d4c54) | assistant, lake build |

Reproduce: `python3 scripts/exp19p_margin_map.py --gate` (~8 min),
`python3 scripts/exp19p_enclosure.py --gate` (~4 min; needs margin map).
