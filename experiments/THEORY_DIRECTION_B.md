# Direction B: Spectral Gap × Hecke Trace Correlation — Theory Reference

## Overview

Direction B tests whether SL(2,F_p) Cayley graph spectral gaps correlate with
Hecke trace statistics of weight-2 newforms at level p. This is an empirical
check of Pizer's theorem (Brandt eigenvalues ↔ Hecke eigenvalues) and the first
link in the chain connecting Cayley graph spectra to L-functions to the
explicit formula to Granville's averaged Goldbach ↔ RH.

## The Theoretical Chain

```
SL(2,F_p) Cayley spectral gap
  → Brandt matrix eigenvalue B(ℓ) on supersingular isogeny graph
    (Pizer's theorem, 1990)
  → Hecke eigenvalue T_ℓ on S₂(Γ₀(p))
  → Fourier coefficient a_ℓ(f) of modular form f
  → L-function L(f,s) analytic properties (analytic continuation, functional eq.)
  → Explicit formula (Weil distribution) → error term in prime counting
  → Averaged Goldbach sum Σ (G(2N) - J(2N))
    (Granville, 2007: RH ⇔ averaged Goldbach bound)
```

## What Pizer's Theorem Actually Says

### Brandt Module Setup

Fix a prime p. Let B_{p,∞} be the definite quaternion algebra ramified at p
and ∞. Choose a maximal order O. The **Brandt module** is the free abelian
group on the set of left ideal classes of O, identified with supersingular
elliptic curves over $\bar{\mathbb{F}}_p$.

Dimension: $h = \text{class number of } O = \dim S_2(\Gamma_0(p))$.

### Brandt Matrix B(ℓ)

For a prime ℓ ≠ p, the Brandt matrix B(ℓ) is a $h \times h$ integer matrix
whose (i,j) entry counts the number of degree-ℓ isogenies between the i-th
and j-th supersingular elliptic curve (weighted by automorphisms).

**Key property**: B(ℓ) is the adjacency matrix of the ℓ-isogeny graph on
supersingular elliptic curves mod p.

### Pizer's Theorem (1990)

> **Theorem** (Pizer, Compositio Math 40:177-241, 1980; refined 1990):
> The eigenvalues of the Brandt matrix B(ℓ) acting on the Brandt module are
> *exactly* the Hecke eigenvalues T_ℓ acting on the space of weight-2 cusp
> forms S₂(Γ₀(p)), together with the eigenvalues of the Eisenstein series.

There is an isomorphism:
$$M_2(\Gamma_0(p)) \cong \text{BrandtModule}(B_{p,\infty})$$

that is Hecke-equivariant: the B(ℓ) action corresponds to T_ℓ simultaneously
on both the cusp forms and the Eisenstein subspace.

### Critical Subtlety (Learned from Exp 7)

**Brandt matrix eigenvalues ≠ Hecke eigenvalues of individual cusp forms.**

The Brandt matrix B(ℓ) acts on the *full space*, which includes:
1. The cuspidal subspace S₂(Γ₀(p)) — eigenvalue a_ℓ(f) for each eigenform f
2. The Eisenstein subspace E₂(Γ₀(p)) — eigenvalue σ₁(ℓ) = 1 + ℓ

So the eigenvalue spectrum of B(ℓ) is:
$$\text{Spec}(B(\ell)) = \{a_\ell(f) : f \in \text{Newforms}(S_2(\Gamma_0(p)))\} \cup \{1 + \ell\}$$

The 1+ℓ (Eisenstein) eigenvalue is typically the largest in absolute value,
and this *dominates* the spectral statistics, drowning out the cusp form signal.
This is why Exp 7's GNN (predicting T_3 statistics from T_2 graph structure)
failed catastrophically (R² = -49.2).

**Implication for Direction B**: We must carefully separate cusp form Hecke
traces from Eisenstein contributions. The `spectral_gap_hecke_correlation.py`
script correctly uses LMFDB data which distinguishes newforms from Eisenstein
series.

## Bridge A: Cayley Graph → Hecke → RH

The LPS/Pizer bridge has two stages:

### Stage 1: Cayley Graph → Brandt Matrix (LPS Construction)

Lubotzky-Phillips-Sarnak (1988) construct Ramanujan graphs from quaternion
algebras. For our SL(2,F_p) Cayley graphs:

- Generators: S = [[1,1],[0,1]], R = [[1,0],[1,1]]
- The adjacency matrix eigenvalues are related to Brandt matrix eigenvalues
  through a representation-theoretic correspondence

**Not equality**: The Cayley graph eigenvalues are NOT literally the Brandt
eigenvalues. They are related through:
- The representation theory of GL(2) over Qₚ
- The Jacquet-Langlands correspondence
- The trace formula relating the Selberg trace on the quaternion algebra to
  the Arthur-Selberg trace on GL(2)

### Stage 2: Brandt → Hecke (Pizer)

As described above: the Brandt module is Hecke-equivariantly isomorphic to
S₂(Γ₀(p)) ⊕ Eisenstein.

### Stage 3: Hecke → L-functions → Explicit Formula

Each Hecke eigenform f ∈ S₂(Γ₀(p)) gives an L-function:
$$L(f, s) = \sum_{n=1}^\infty a_n(f) n^{-s}$$

with:
- Analytic continuation to entire ℂ (Hecke, 1937)
- Functional equation $s \leftrightarrow 1 - s$
- Ramanujan-Petersson bound $|a_p(f)| \leq 2\sqrt{p}$ (Deligne, 1974)

The explicit formula (Weil, 1952) relates sums of $\Lambda(n) a_n(f)$ over
primes to sums over zeros of L(f,s). This is the key bridge to the distribution
of primes and Goldbach.

### Stage 4: Averaged Goldbach → RH (Granville)

Granville (2007): RH is equivalent to:
$$\sum_{2N \leq x} (G(2N) - J(2N)) \ll x^{3/2 + o(1)}$$

where G(2N) is the weighted Goldbach count and J(2N) the Hardy-Littlewood
prediction. The explicit formula connects L-function zeros to error terms in
this sum.

## What Our Codebase Does

### Files

| File | Purpose | Key Finding |
|---|---|---|
| `scripts/compute_hecke.py` | Compute Hecke eigenvalues via PARI/GP `mfeigenbasis` | Reliable for p=11..61 |
| `scripts/build_pizer_dataset.py` | Build Brandt matrix graphs from T_ℓ matrices | 57 primes p=47..499, ℓ=2,3,5,7,11,13 |
| `scripts/train_pizer_gnn.py` | WeightedChebNet: T₂ → T₃ eigenvalue statistics | **Failed** R²=-49.2 (Eisenstein contamination) |
| `scripts/spectral_gap_hecke_correlation.py` | **Direction B**: spectral gap vs Hecke trace correlation | **Blocked** — needs Docker + LMFDB data |
| `scripts/train_hecke_gnn.py` | Cayley graph features → Hecke eigenvalue prediction | Standard split R²=-30, LOO negative |
| `scripts/train_lmfdb_ml_53k.py` | sklearn ML on 53k LMFDB newforms (Exp 9-10) | **Succeeded** R²=0.73-0.99 |

### Experimental Results Summary

| Experiment | What | R² | Why |
|---|---|---|---|
| Exp 7 | Pizer GNN (T₂→T₃) | -49.2 | Eisenstein contamination, data quality |
| Exp 5 | Hecke GNN (Cayley→mean a_p) | -30 (std split) | Insufficient data (18 primes) |
| Exp 9-10 | LMFDB ML (traces→Hecke) | 0.73-0.99 | 53k samples sufficient |

### Key Takeaway from Existing Work

> **Data quantity, not model architecture, was the bottleneck.**
> When we had 53k samples (Exp 9-10), ML succeeded. With 18-57 samples
> (Exps 5, 7), GNNs failed. The correlation signal exists but is weak enough
> that statistical power requires many data points.

## What Direction B Specifically Tests

The script `scripts/spectral_gap_hecke_correlation.py` computes:

1. **Spectral gap vs mean a₂ trace**: Does the gap correlate with average
   Hecke trace at level p? (This tests whether the Cayley graph encodes
   aggregate Hecke information per Pizer's theorem)

2. **Spectral gap vs mean analytic rank**: Do graphs with larger gaps
   correspond to levels with higher/lower average ranks?

3. **Spectral gap vs trace_k series**: For which trace indices k does the
   correlation peak? (This identifies which Hecke operators carry the
   strongest spectral signal)

4. **Friedli slope vs Hecke traces** (p=2,3,5,7,11,13): Does the Friedli
   constant 1.1367 correlate with Hecke trace statistics?

## Open Theoretical Questions

1. **Why does the Friedli constant converge to ~1.1367?** This is the spectral
   zeta functional equation derivative at σ=1/2. Is this a universal constant
   for families of arithmetic groups?

2. **Does spectral gap correlate with L-function zero statistics?** If so,
   gap → (Pizer) → Hecke eigenvalues → L-function → zero spacing → RH relevance.

3. **Is there a direct spectral gap → RH bridge independent of Pizer?**
   The Friedli constant structure (averaged functional equation derivative)
   parallels Granville's averaged Goldbach structure. This might be a more
   direct path than the LPS/Hecke bridge.

## Next Steps (When Docker is Available)

```bash
# 1. Collect LMFDB Hecke trace data
docker compose exec research python scripts/collect_lmfdb_sql.py --max-level 1000

# 2. Run Direction B correlation analysis
docker compose exec research python scripts/spectral_gap_hecke_correlation.py

# 3. Expected output: correlation_results.json in data/experiment16/
#    Key metric: Pearson r between spectral_gap and mean_a2
```

The output will be a JSON file with Pearson correlations. If |r| > 0.3,
there is evidence that Cayley graph spectral structure encodes aggregate
Hecke information — supporting Pizer's theorem as an empirical bridge.
