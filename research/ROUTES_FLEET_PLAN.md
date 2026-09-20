# Routes Fleet Plan: 5 alternative RH research routes

Post-EPIC-4 diversification. The Mayer transfer-operator route is stuck at
exactly the point that IS RH (see `research/FRONTIER.md` "the final step is
circular"): the avatar m(s) = min|1-lambda| > 0 is equivalent to RH, so any proof
must go beyond the current numerical protocol. These 5 routes are
**independent mathematical attacks** -- each uses a different reformulation of
RH, not the Mayer operator (except route D, which pushes certified bounds on
the Mayer route).

**Honest status**: none of these prove RH. Each produces numerical evidence,
partial results, or infrastructure that constrains the search space. The goal
is to move from "we believe it because we computed it" to "we can state what
would have to be true and test it."

## Tooling

- `python` (3.12, hermes venv) has **numpy 2.4.4, scipy 1.17.1, mpmath 1.3.0**
  -- use `python` for scripts needing mpmath/scipy.
- `python3` (pyenv 3.10) has numpy only -- sufficient for pure-numpy scripts.
- mpmath `zetazero(n)` gives the n-th nontrivial zeta zero to arbitrary precision.
- mpmath `mp.iv` provides interval arithmetic (for route D).
- `scripts/nystrom_collocation.py` -- the existing Nystrom collocation module
  (route D and B2 cross-validation only; the other routes are independent).
- NOTE: `python` is Windows Python -- it needs `C:/...` paths, not `/c/...`.
## S1 Task RT-D -- certified spectral-radius bounds (Nisoli/DFLY)

Write `scripts/routes/certified_spectral_radius.py`:

1. Use mpmath interval arithmetic (`mp.iv`) to compute **rigorous** upper
   bounds on rho(L_s) for the boundary-corrected Mayer operator.
2. Grid: sigma in {0.75, 0.70, 0.65, 0.60, 0.55, 0.51}, t in {0, 50, 100}.
3. Method: assemble the Nystrom matrix in interval arithmetic (truncate k at
   nmax, bound the tail norm with interval widths), compute interval
   eigenvalues (power iteration on intervals with widening).
4. `--gate`: exit 0 iff the JSON exists, all 18 points have certified
   upper_bound < 1, and the certified width (upper-lower) is reported for each.
5. HONESTY RULE: if an interval upper bound >= 1, report it verbatim and let
   the gate fail. Do not shrink the interval artificially.

Budget: ~30 min. The numerics suggest rho ~ 0.14-0.30 for sigma >= 3/4 (hence
"certified < 1" should pass at sigma = 0.75), but pushing to sigma = 0.51 may
fail -- that failure is informative (current interval technique can't certify
the margin there).

## S2 Task RT-B2 -- Bonanno-style matrix (orthogonal-polynomial basis)

Write `scripts/routes/bonanno_matrix.py`:

1. Assemble the Mayer transfer operator matrix in a global orthonormal
   polynomial basis on (0,1) (shifted Legendre), NOT collocation points.
   Matrix elements:
       M[i,j] = <P_i, L_s P_j> = int_0^1 P_i(x) sum_k (k+1+x)^{-2s} P_j(1/(k+1+x)) dx
   computed with numpy Gauss-Legendre quadrature (N_quad >= 256 nodes, nmax
   terms, chunked).
2. Basis size N in {64, 128, 256, 384}. For each N and each s in
   {0.51+1100.574j, 0.52+1100.574j, 0.55+124.2568j}:
   - Compute all eigenvalues of the NxN matrix.
   - Report m(s) = min|1-lambda| and |lambda2|.
3. Cross-validate against `nystrom_collocation.leading_pair` (import it) at
   the same points -- agreement to ~1e-3 confirms the polynomial basis
   captures the same spectrum.
4. `--gate`: exit 0 iff the JSON exists, has all 12 (N,s) entries, and the
   polynomial-basis m(s) agrees with the Nystrom m(s) to within 5e-2 at N=384.

This is an independent numerical cross-check: if two different bases agree,
the eigenvalue-1 gap is not a collocation artifact.
## S3 Task RT-NB -- Nyman-Beurling density test

Write `scripts/routes/nyman_beurling.py`:

1. Implement f_a(x) = {ax} - a*floor(x) for a in (0,1].
2. For grid size n in {16, 32, 64, 128}, take a_k = k/(n+1) for k = 1..n.
   Build the nxn Gram matrix G[i,j] = int_0^1 f_{a_i}(x) f_{a_j}(x) dx
   (numpy quadrature with 4096 nodes; the integrand has jump discontinuities
   at x = 1/(k*a_j) so use many nodes).
3. Report: min eigenvalue of G, condition number, and the residual
   eps_n = min_{c in R^n} ||f_{1/2} - sum c_k f_{a_k}||^2_{L2}
   (solve the least-squares system G c = <f_{a_k}, f_{1/2}>).
4. Density iff eps_n -> 0 as n -> infinity. Report the rate.
5. `--gate`: exit 0 iff the JSON exists, all 4 entries computed, and
   eps_n < 0.1 for n = 128 (loose: the test is exploratory, not a proof).

Baez-Duarte (2003) showed the convergence rate is tied to RH: eps_n decays
faster than any power iff RH. Observing the empirical rate is the goal.

## S4 Task RT-LC -- Li's criterion computation

Write `scripts/routes/li_criterion.py`:

1. Compute Li coefficients lambda_n = sum_rho [1 - (1 - 1/rho)^n] for
   n = 1..200 using `mpmath.zetazero(k)` for k = 1..200 (the first 200 zeros
   suffice for n <= 200: the truncation error is O(n^2/log(200)) -- estimate
   it and include it in the output).
2. Alternative formula for cross-check:
   lambda_n = (1/(n-1)!) d^n/ds^n [s^{n-1} log xi(s)]|_{s=1}
   Implement the derivative version for n = 1..20 via numerical
   differentiation at high precision (mp.dps = 50) and compare.
3. Report: lambda_n values, all >= 0?, the minimum lambda_n, and the growth
   rate (lambda_n ~ (n log n)/(2 pi) known asymptotically -- verify the fit).
4. `--gate`: exit 0 iff the JSON exists, lambda_n >= 0 for all n = 1..200, and
   the derivative cross-check agrees to 1e-6 for n = 1..20.

RH iff all lambda_n >= 0. A single negative lambda_n would disprove RH.
Finding none is expected; the value is in the infrastructure + asymptotic fit.
## S5 Task RT-HP -- Hilbert-Polya prototype (Berry-Keating)

Write `scripts/routes/hilbert_polya.py`:

1. Discretize the Berry-Keating Hamiltonian H = xp on (0, L] with
   H = -i(x d/dx + 1/2) (self-adjoint form) via a finite-difference grid
   (N_grid in {256, 512, 1024}).
2. Compute eigenvalues of the discretized H. The continuum spectrum is all
   of R -- but on a finite grid with Dirichlet boundaries the eigenvalues
   are discrete. Report them.
3. Compare the eigenvalue spacings with zeta-zero spacings (GUE statistics):
   compute the nearest-neighbour spacing distribution and the
   pair-correlation. GUE-like statistics are the Hilbert-Polya signal.
4. Also implement the truncated Connes trace formula: eigenvalues of the
   "semiclassical zeta operator" (roughly, the values zeta(1/2 + i*lambda_n)
   for lambda_n eigenvalues of H) and check if they vanish near the true
   zeta-zero ordinates.
5. `--gate`: exit 0 iff the JSON exists, has eigenvalue tables for all 3 grid
   sizes, and the spacing distribution is computed (any result -- this is
   exploratory). The gate does NOT require GUE agreement; it requires that
   the computation ran and produced data.

This is a prototype/feasibility study, NOT an RH approach. The output
informs whether a Hilbert-Polya construction is numerically detectable.

## References

- `research/ZERO_SLIVER_MARGIN.md` -- the eigenvalue-1 avatar (route D context)
- `research/FRONTIER.md` -- the honest status of the Mayer route (why these 5)
- `research/EPIC4_FLEET_PLAN.md` -- the predecessor fleet (Exp 19p)
- Nisoli 2026 -- certified spectra for transfer operators (route D)
- Bonanno 2022 -- eigenvalue-1 in Hilbert space (route B2 inspiration)
- Burnol 2004, Baez-Duarte 2003 -- Nyman-Beurling (route NB)
- Bombieri-Lagarias 1999 -- Li's criterion (route LC)
- Berry-Keating 1999, Connes 1999, Sierra 2008 -- Hilbert-Polya (route HP)
