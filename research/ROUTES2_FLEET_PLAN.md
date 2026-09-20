# Routes Fleet Plan 2: follow-ups on the 5 RH research routes

Round 2. Round 1 (ROUTES_FLEET_PLAN.md) produced: RT-NB PASS (eps_128=0.0073,
beta=-0.779), RT-LC PASS (lambda_n >= 0, n=1..200, K=200 zeros), RT-D honest
FAIL (7/18 points rho >= 1: all t=0 as expected, plus sigma=0.51 at t=100),
RT-B2 honest FAIL (poly-basis margin 0.23 vs nystrom 0.034 at t=1101),
RT-HP negative (Berry-Keating FD = picket fence, no GUE).

Round 2 pushes each route to its next decisive question:

| Task    | Route    | Question                                                   |
|---------|----------|------------------------------------------------------------|
| RT2-LC  | Li       | Can lambda_n positivity be CERTIFIED (K=1000 + tail bound)? |
| RT2-NB  | N-B      | Does eps_n -> 0 hold at n=256,512,1024 (same rate beta)?    |
| RT2-D   | Mayer    | WHERE does rho(L_s) cross 1? Map t*(sigma) with certified brackets. |
| RT2-B2  | Bonanno  | WHY does the poly basis fail at high t? Convergence rate?   |
| RT2-HP  | Hilbert  | Does ANY H=xp discretization give GUE spacing? 4 variants.  |

## Tooling

- `python` (3.12, hermes venv): numpy 2.4.4, scipy 1.17.1, mpmath 1.3.0.
  Use `python` for ALL scripts (never `python3`).
- mpmath `zetazero(k)` = k-th nontrivial zero (on critical line, Re=1/2 by
  construction). ~0.1-0.5 s per call at dps=40.
- mpmath `mp.euler` = Euler-Mascheroni gamma.
- Round-1 scripts are ON MASTER and are meant to be READ and REUSED:
  - `scripts/routes/li_criterion.py` (zero-sum + derivative cross-check)
  - `scripts/routes/nyman_beurling.py` (exact period-mean Gram entries)
  - `scripts/routes/certified_spectral_radius.py` (mpmath A^m bound;
    `compute_point(sigma, t)` per-point API)
  - `scripts/routes/bonanno_matrix.py` (Legendre Galerkin assembly)
  - `scripts/routes/hilbert_polya.py` (FD spectra + spacing stats)
  - `scripts/nystrom_collocation.py` (`nystrom_matrix_vec(s,n,nmax)`,
    `margin`, `leading_pair`)
- DO NOT modify round-1 scripts. Each RT2 task writes a NEW script.
- NOTE: `python` is Windows Python -- it needs `C:/...` paths, not `/c/...`.

## S1 Task RT2-LC -- certified Li's criterion (K=1000 zeros, rigorous tail)

Write `scripts/routes/li_criterion_certified.py`. Goal: certify
S_K(n) > 0 for n = 1..300 using the first K=1000 verified on-line zeros,
and place a RIGOROUS certified interval around each lambda_n.

Mathematics (all verifiable in the script's self-check):

1. For rho_k = 1/2 + i*gamma_k (k-th zero, upper half plane):
   1 - 1/rho_k = (-1 + 2i*g)/(1 + 2i*g), so |1 - 1/rho_k| = 1 and
   arg(1 - 1/rho_k) = theta_k = 2*arctan(1/(2*gamma_k))   [exact identity]
2. The k-th CONJUGATE PAIR contributes exactly
       c(n,k) = 2*(1 - cos(n*theta_k))  >= 0.
   Hence the partial sum S_K(n) = sum_{k=1..K} c(n,k) is >= 0
   unconditionally (each term is computed from a verified on-line zero).
3. lambda_n = S_K(n) + tail(n), tail(n) = sum_{k>K} c(n,k) >= 0 on RH.
   TAIL UPPER BOUND (use 1 - cos(x) <= x^2/2 and theta_k <= 1/gamma_k,
   zero density dN ~ ln(t/(2pi))/(2pi) dt):
       T_K(n) <= n^2 * ( ln(gamma_K/(2*pi)) + 2 ) / gamma_K  +  n^2/gamma_K^2
   Also compute the EXACT tail from the next 100 zeros (K+1..K+100) to
   show the bound's tightness: report both.
4. CLOSED FORM lambda_1 = 1 + mp.euler/2 - mp.log(2) - mp.log(mp.pi)/2
   (~0.0230957...). This is a theorem (no RH needed). CERTIFIED CHECK:
   lambda_1_closed must lie inside [S_K(1), S_K(1) + T_K(1)].
5. Asymptotic (Bombieri-Lagarias): lambda_n ~ (n/2)*ln(n/(2*pi*e)) + O(n).
   Fit A,B in A*n*ln(n)+B*n over n in [150,300]; gate requires
   A_fit in [0.40, 0.60].

Parameters: K_ZEROS=1000, K_TAIL_EXACT=100, N_MAX=300, dps=50 for sums,
dps=40 for zetazero. Runtime ~5-10 min (1100 zetazero calls dominate).
Checkpoint: save zero gammas to data/routes/rt_lc_certified_zeros.json
first, then the main output.

Output: data/routes/rt_lc_certified.json with keys: params, zeros
(k, gamma_first, gamma_last, all_on_critical_line), lambda_table (n,
S_K, T_bound, exact_tail_100, certified_lower=S_K, certified_upper,
asymptotic), lambda1_check (closed, S_K_1, inside_interval: bool),
asymptotic_fit (A_fit, B_fit, window), gate_pass.

Gate (`--gate`): exit 0 iff (a) lambda_1_closed in [S_K(1), S_K(1)+T_K(1)],
(b) S_K(n) > 0 for all n=1..300, (c) A_fit in [0.4, 0.6],
(d) exact_tail_100 <= T_bound for all sampled n (bound is valid).

## S2 Task RT2-NB -- Nyman-Beurling at n=256, 512, 1024

Write `scripts/routes/nyman_beurling_ext.py`. Round 1 computed eps_n for
n in {16,32,64,128} with beta = -0.779. Round 2 extends to n = 256, 512,
1024 to test whether the power law holds over a 64x range.

READ `scripts/routes/nyman_beurling.py` FIRST and reuse its exact
period-mean formula for the Gram matrix entries (validated against naive
quadrature to 1e-6 in round 1). Do NOT use naive quadrature at n >= 256
(too slow).

Method:
1. For n in {256, 512, 1024}: a_k = k/(n+1), build G (n x n) via the
   exact formula, compute min eigenvalue (np.linalg.eigh) and the
   least-squares residual eps_n = min ||f_{1/2} - sum c_k f_{a_k}||^2.
2. Report condition number at each size; if cond > 1e12, switch to
   mp.iv / mpmath eigenvalue computation for min_eig only (honest report).
3. Fit eps_n ~ A * n^beta over ALL 7 sizes {16..1024} (merge with round-1
   values, which you recompute for consistency in the same run).
4. Expected if RH-consistent: beta stays near -0.78 and eps_1024 < 0.002.
   If beta levels off (rate slows), that is an HONEST result: report it.

Output: data/routes/rt_nb_ext.json with keys: params, sizes (list of
{n, eps_n, min_eig, cond}), powerlaw_fit (A, beta, over range), gate_pass.

Gate (`--gate`): exit 0 iff (a) all 7 sizes computed, (b) eps_n > 0 and
min_eig > 0 at every size, (c) eps_1024 < 0.01, (d) |beta| > 0.3 over
the full range (density signal). beta deterioration = honest FAIL.

## S3 Task RT2-D -- spectral-radius boundary map t*(sigma)

Write `scripts/routes/spectral_boundary.py`. Round 1 found: at t=0 all
sigma fail (rho > 1, expected since lambda_1(sigma) > 1 for sigma < 1),
at t=50 all pass, at t=100 sigma=0.51 fails again (rho = 1.054) -- the
boundary is NON-MONOTONE in t. Map it.

READ `scripts/routes/certified_spectral_radius.py` FIRST. Reuse its
functions: `mp_nodes`, `assemble_matrix`, `certified_rho_bounds`,
`tail_bound`, `compute_point(sigma, t)` (returns certified upper bound).
Do NOT rewrite the mpmath assembly.

Method (two phases):
1. FLOAT64 SCAN (fast): for each sigma in {0.75, 0.70, 0.65, 0.60, 0.55,
   0.51}, compute rho_float(t) for t in 0..100 step 5 via
   `nystrom_collocation.nystrom_matrix_vec(s, 24, 500)` + np.linalg.eigvals
   (~2 s per sigma). Find approximate crossings of rho_float = 1.
2. CERTIFIED BRACKET (mpmath): for each approximate crossing, walk outward
   in steps of 1.0 until `compute_point(sigma, t)` certifies
   upper_bound < 1 on one side and >= 1 on the other. Record the bracket
   [t_lo, t_hi] with cert values. Budget ~30 s per certified probe, max
   4 probes per crossing, max 3 crossings per sigma.
3. HONESTY: if a crossing cannot be bracketed (cert_ub jumps wildly),
   record the raw data. Non-monotonicity (sigma=0.51) is expected and
   must appear in the output, not be smoothed away.

Output: data/routes/rt_boundary.json with keys: params, scan (per sigma:
list of {t, rho_float}), crossings (per sigma: list of {t_lo, t_hi,
cert_lo, cert_hi, bracketed: bool}), gate_pass.

Gate (`--gate`): exit 0 iff (a) float64 scan done for all 6 sigma,
(b) at least one certified crossing per sigma, (c) every reported
bracket has cert_lo < 1 <= cert_hi. Missing brackets = honest FAIL.

## S4 Task RT2-B2 -- Bonanno high-t convergence diagnosis

Write `scripts/routes/bonanno_diagnosis.py`. Round 1 found the
shifted-Legendre Galerkin basis agrees with Nyström at low t
(|m_poly - m_nystrom| = 1.3e-15 at s=0.55+124.3j) but DIVERGES at high t
(|m_poly - m_nystrom| = 0.23 at s=0.51+1101j, N=384). Diagnose WHY and
estimate the convergence rate.

READ `scripts/routes/bonanno_matrix.py` FIRST. Reuse its matrix assembly
(shifted Legendre, Gauss-Legendre quadrature). The failing point is
s = 0.51 + 1100.574j.

Method:
1. CONVERGENCE TABLE: for N in {256, 384, 512, 768}, compute
   m_poly(N) at s=0.51+1100.574j with n_quad = max(256, 4*N).
   Cross-validate against `nystrom_collocation.leading_pair(s, 384, 8000)`.
2. QUADRATURE CHECK: at N=384, double n_quad (768, 1536, 3072) and
   check m_poly(N=384) stabilizes. If it does NOT stabilize, the issue
   is quadrature, not basis size.
3. EXTRAPOLATE: fit m_poly(N) = m_inf + c * N^(-alpha) over the 4 N
   values. Report m_inf, alpha, and |m_inf - m_nystrom|.
4. CHEBYSHEV VARIANT (optional bonus): repeat N=384 with Chebyshev
   polynomials (first kind, weight 1/sqrt(x(1-x))) instead of Legendre.
   Report whether Chebyshev converges faster.

Output: data/routes/rt_b2_diag.json with keys: params, convergence_table
(N, m_poly, n_quad, m_nystrom_ref, abs_diff), quadrature_check
(n_quad, m_poly, abs_diff_to_highest), extrapolation (m_inf, alpha,
c, nystrom_ref, extrapolated_diff), chebyshev_variant (if computed),
gate_pass.

Gate (`--gate`): exit 0 iff (a) convergence table has all 4 N values,
(b) quadrature check shows m_poly(N=384) stable to 1e-4 when n_quad
doubles, (c) |m_inf - m_nystrom| < 5e-2 (extrapolation converges to
the Nyström value). If the extrapolation does NOT converge to Nyström,
that is an HONEST FAIL: report the rate and the gap.

## S5 Task RT2-HP -- Berry-Keating variants (does ANY discretization give GUE?)

Write `scripts/routes/bk_variants.py`. Round 1 found the naive Dirichlet
finite-difference (FD) discretization of H = xp gives a PICKET FENCE
spectrum (KS-to-GUE ~ 0.5, i.e. Poisson). Test 4 variants to see if ANY
gives GUE-like level repulsion.

READ `scripts/routes/hilbert_polya.py` FIRST. Reuse its eigenvalue
computation and spacing-statistics code (unfolding, KS distance).

Method -- 4 variants at N_grid = 512:
1. DIRICHLET_FD (baseline): reproduce round-1 picket fence. H = -i(x d/dx
   + 1/2), Dirichlet BC on (0, L], L = 2*pi*N_grid. Expected: KS ~ 0.5.
2. PERIODIC_FD: same H but periodic BC (wrap-around). This changes the
   boundary term and may mix the picket fence.
3. SYMMETRIC_FD: H = -i*(x*d/dx + d/dx*x)/2 = -i*(x*d/dx + 1/2) -- wait,
   that IS the same as variant 1. Use instead H = (xp+px)/2 with the
   symmetric discretization (centered difference for d/dx, x on half-grid).
4. CHEBYSHEV_COLLOCATION: discretize H on Chebyshev nodes (not uniform),
   which clusters points near the boundaries where xp has rapid variation.

For each variant:
- Compute eigenvalues lambda_j (j=1..N_grid), sort, unfold by
  mean spacing, compute nearest-neighbor spacing distribution P(s),
  and KS distance to GUE (Wigner surmise p(s) = (32/pi^2)*s^2*exp(-4s^2/pi))
  and to Poisson (p(s) = exp(-s)).
- Connes check: min_j |zeta(1/2 + i*lambda_j)| over the first 50 eigenvalues.

Output: data/routes/rt_bk_variants.json with keys: params, variants
(list of {name, N_grid, eigenvalues (first 20), ks_gue, ks_poisson,
connes_min_zeta}), best_variant (name, ks_gue), gate_pass.

Gate (`--gate`): exit 0 iff (a) all 4 variants computed, (b) at least one
variant has eigenvalues + spacing stats, (c) JSON matches schema. Any
physics outcome is acceptable (exploratory). Report which variant (if any)
gives KS-to-GUE < 0.1.

## References

- `research/ROUTES_FLEET_PLAN.md` -- round 1 plan (sections S1-S5)
- `research/FRONTIER.md` -- why the Mayer route alone is not enough
- `research/RUELLE_DOMINATION.md` -- rho(L_s) <= rho(L_sigma) context (RT2-D)
- `scripts/routes/li_criterion.py` -- round-1 Li script (K=200, n=1..200)
- `scripts/routes/nyman_beurling.py` -- round-1 N-B script (n<=128)
- `scripts/routes/certified_spectral_radius.py` -- round-1 certified rho
- `scripts/routes/bonanno_matrix.py` -- round-1 Bonanno (Legendre basis)
- `scripts/routes/hilbert_polya.py` -- round-1 BK (Dirichlet FD)
- `scripts/nystrom_collocation.py` -- Nyström collocation cross-check API
- Bombieri-Lagarias 1999 -- Li's criterion (RT2-LC)
- Baez-Duarte 2003 -- Nyman-Beurling density (RT2-NB)
- Nisoli 2026 -- certified spectra for transfer operators (RT2-D)
- Berry-Keating 1999, Sierra 2008 -- Hilbert-Polya variants (RT2-HP)
