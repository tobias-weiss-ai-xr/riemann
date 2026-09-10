# EPIC-4 Fleet Plan: eigenvalue-1 falsification protocol (Exp 19p)

The honest RH avatar (formalized in lean/Riemann/TransferOperator.lean,
commit 8eb3766) is

    m(s) = min_j |1 - lambda_j(s)| > 0  for all Re(s) > 1/2
       <=>  det(I - L_s) != 0  <=>  1 notin Spec(L_s)  <=>  RH

where L_s is the Mayer/Ruelle transfer operator of the Gauss map. Experiment
19o measured the margin law m ~ 2.087*(sigma-1/2) + 0.0130 at the single height
t = 1100.574 with zero-crossing sigma* ~ 0.4938 < 1/2 -- RH-consistent. This
plan extends the falsification protocol: a margin MAP over several zeta-zero
heights (S1, task E4-P1) and a convergence-ladder error bar at the worst
point (S2, task E4-P2). A single point with m(s) <= 0 for Re(s) > 1/2
falsifies the avatar -- i.e. a zero off the critical line. None is known; the
protocol hunts for one.

## Tooling

- scripts/nystrom_collocation.py (tracked, commit 9a32616): overflow-safe
  Nystrom collocation. API:

      margin(s: complex, n: int, nmax: int, chunk: int = 200) -> float
      nystrom_matrix_vec(s: complex, n: int, nmax: int, chunk: int = 200) -> np.ndarray
      leading_pair(s: complex, n: int, nmax: int, chunk: int = 200) -> (float, float)

  Host python3 has numpy (+ mpmath); NO Docker needed.
- Verified reference values (sanity-check your integration against these):

      margin(0.52 + 1100.574j, 512, 8000) ~ 0.0391   |lambda2| ~ 0.9833
      margin(0.51 + 124.2568j, 384, 8000) ~ 0.0825   (matches ZERO_SLIVER_MARGIN.md S4)
      margin(0.55 + 124.2568j, 256, 6000) ~ 0.1167

- Do NOT use lambda1_derivative.nystrom_matrix at N > 384 (its naive
  barycentric weights overflow; NaN/Inf in the matrix).

## S1 Task E4-P1 -- margin map at three zeta-zero heights (Exp 19p)

Write scripts/exp19p_margin_map.py:

1. Grid -- heights t in {124.2568 (gamma41), 1100.574 (zero #731), 150.0 (corner)},
   sigma in {0.501, 0.505, 0.51, 0.515, 0.52, 0.535, 0.55} -> 21 points.
2. Resolution: N=384, nmax=8000 for t <= 500; N=512, nmax=8000 for t > 500
   (only nystrom_collocation is safe at N=512).
3. Per point compute m(s) = min_j|1-lambda_j| and |lambda2(s)| (second-largest modulus).
4. Checkpoint after EVERY point to data/experiment19p/margin_map.json
   (mkdir -p data/experiment19p first) with schema

       {"points": [{"sigma","t","margin","abs_lambda2","N","nmax"}],
        "slopes": [{"t","c","b","sigma_star","n_fit"}]}

   On restart, skip already-computed points (resume).
5. After the grid: per height fit m(sigma) = c*(sigma-1/2) + b by least squares over
   sigma >= 0.505 (sigma=0.501 is tail-unresolved; exclude from the fit but keep in
   points), report c, b, sigma* = 1/2 - b/c.
6. --gate mode: exit 0 iff the JSON exists, has all 21 points, every margin
   > 0, and at least 2 of 3 heights have fitted sigma* < 0.5. Otherwise print a
   clear diagnostic and exit 1.
7. Print a human-readable table (sigma, t, m, |lambda2|).

HONESTY RULE: if any computed margin is <= 0 that is a REAL result (a
candidate counterexample to the eigenvalue-1 avatar). Record it verbatim in
the JSON, print it loudly, and let the gate fail. Never fabricate or clamp.

Budget: ~15-20 min total on the host.

## S2 Task E4-P2 -- convergence-ladder enclosure at the worst point

Write scripts/exp19p_enclosure.py (depends on E4-P1's JSON):

1. Load data/experiment19p/margin_map.json, take the point with the MINIMUM
   margin (sigma_w, t_w).
2. Convergence ladder at (sigma_w, t_w): (N, nmax) in
   {(256,6000), (384,8000), (512,8000), (512,12000)} -- compute m and |lambda2| at
   each rung.
3. Conservative error bar: err = (max-min)/2 over the four rungs,
   m_hat = (max+min)/2, lower_bound = m_hat - err.
4. Write data/experiment19p/enclosure.json:

       {"sigma","t","ladder":[{"N","nmax","margin","abs_lambda2"}],
        "m_hat","err","lower_bound"}

5. --gate: exit 0 iff all four rung margins > 0 AND lower_bound > 0. If
   lower_bound <= 0 the numerics are not converged enough to certify -- that is
   a legitimate FAIL; report which rungs disagree. Do not tune rungs until it
   passes.

This is a convergence-ladder bound, not full interval arithmetic (certified
mp.iv/Arb enclosure is a follow-up).

## References

- research/ZERO_SLIVER_MARGIN.md -- full evidence history (Exp 19k/19l/19o)
- lean/Riemann/TransferOperator.lean -- eigenvalueOneFreeConjecture,
  eigenvalueOneFree_above_one (proved half-plane Re(s) > 1)
- experiments/EXPERIMENT_LOG.md -- experiment history
