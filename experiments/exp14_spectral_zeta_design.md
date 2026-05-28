# Exp 14: Graph Spectral Zeta Function (Karlsson-Murugan)

**Date:** 2024-05-24
**Approach:** Graph spectral zeta functions as discrete circle approximations to ζ(s)
**Reference:** Karlsson & Murugan (2024-2025) on approximating functional equations

---

## Motivation

Previous experiments (1-13) showed GNNs on graph structure cannot predict spectral properties. Need new approach: **direct spectral-theoretic connection** between Cayley graph Laplacians and ζ(s).

Karlsson-Murugan shows that for graphs satisfying certain regularity conditions, the **spectral zeta function** ζ_G(s) approximates ζ(s) via discrete circle approximations, with rigorous error bounds.

---

## Mathematical Foundation

### Graph Spectral Zeta Function

For a graph G with Laplacian eigenvalues λ_1 ≥ λ_2 ≥ ... ≥ λ_n (excluding λ=0):

```
ζ_G(s) = Σ_{i=1}^n (λ_i / λ_1)^{-s}
```

**Key properties:**
- Normalized by spectral radius λ_1 ensures convergence
- For Laplacians of expander graphs like SL(2,F_p) Cayley graphs, ζ_G(s) approximates ζ(s)
- Discrete circle structure emerges from high-regularity graph spectra

### Karlsson-Murugan Approximation (Summary)

Under assumptions:
1. G is a vertex-transitive regular expander
2. Spectral density converges to a continuous distribution
3. Eigenvalue spacing satisfies Wigner-Dyson statistics

Then:
```
|ζ_G(s) - ζ(s)| ≤ C(surface(G)) · |Im(s)|^{-α}
```

where α > 0 depends on graph parameters and surface(G) is a measure of graph irregularity.

**Implication:** For sufficiently regular graphs (like Cayley graphs of SL(2,F_p)), zeros of ζ_G(s) approximate zeros of ζ(s) on the critical line.

---

## Implementation

### File: `scripts/spectral_zeta_function.py`

**Key components:**

1. **`SpectralZetaComputer` class**
   - Load precomputed eigenvalues from `data/eigenvalues/`
   - Compute spectral zeta values: ζ_G(s) = Σ (λ_i/λ₁)^{-s}
   - Find zeros on critical line via sign-change detection
   - Compare with known ζ(s) zeros

2. **Zero Finding Algorithm**
   - Evaluate ζ_G(½+it) for t in [t_min, t_max]
   - Detect sign changes in Real(ζ_G)
   - Linear interpolation to locate crossing points
   - Refine by evaluating at interpolated t

3. **Approximation Error Metrics**
   - Mean absolute error between detected and true zeros
   - Compute for first N known zeros (N=10 in experiments)
   - Test sensitivity to number of eigenvalue terms used

---

## Experimental Design

### Dataset
- 26 Cayley graphs for primes p=2..101
- Precomputed eigenvalues (22 complete, 4 computing: p=83,89,97,101)

### Parameters

| Parameter | Values |
|-----------|--------|
| Graphs | p ≤ 61 (17 primes with complete eigenvalues) |
| Search range | t ∈ [10, 60] (covers first 8-10 zeros) |
| `num_terms` | All eigenvalues, truncated versions (100, 500, 1000) |
| Resolution | 5000 points for sign-change detection |

### Steps

1. Compute spectral zeta ζ_G(½+it) for each graph
2. Find zeros via sign-change detection
3. Compare with actual ζ(s) zeros
4. Compute approximation error metrics
5. Analyze error vs graph size / num_terms relationship

---

## Success Criteria

### Primary Goals
- [ ] Detect at least 5-10 zeros on critical line for each graph
- [ ] Mean approximation error < 5.0 for first 8 zeros
- [ ] Error decreases with graph size (larger p = better approximation)
- [ ] Error decreases when using more eigenvalue terms

### Secondary Goals
- [ ] Identify which graph parameters best predict approximation quality
- [ ] Establish scaling law: error ≈ C · p^(-α)
- [ ] Determine minimum graph size required for useful ζ(s) approximation

---

## Execution

```bash
# Run analysis on available graphs
docker compose exec research python scripts/spectral_zeta_function.py \
  --primes 2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61 \
  --output data/spectral_zeta_results.json

# Run with different num_terms values
docker compose exec research python scripts/spectral_zeta_function.py \
  --primes 37,41,43,47,53,59,61 \
  --num-terms 100 500 1000 5000 \
  --output data/spectral_zeta_results_terms.json
```

---

## Expected Outcomes

### Most Likely (Success)
- Spectral zeta zeros approximate ζ(s) zeros within 10-20% error
- Accuracy improves with larger primes and more eigenvalue terms
- Establishes direct spectral-theoretic connection between Cayley graphs and ζ(s)

### Alternative (Partial Success)
- Detection works but error remains high (>30%)
- Trend is correct but convergence is slower than paper claims
- May need eigenvalues from larger graphs (p > 101) for good approximation

### Worst Case (Failure)
- No zeros detected or positions are completely wrong
- ζ_G(s) behavior does not resemble ζ(s) in examined range
- Suggests graph regularity assumptions don't hold for Cayley graphs

---

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| 1. Implementation | 30 min | Write `spectral_zeta_function.py` |
| 2. Testing | 15 min | Verify on known test case, check zero detection accuracy |
| 3. Execution | 5-10 min | Run on 17 primes (p ≤ 61) |
| 4. Analysis | 15-30 min | Compute error metrics, analyze trends |
| 5. Documentation | 15 min | Update EXPERIMENT_LOG.md with results and findings |

**Total:** 1.5-2 hours

---

## Next Steps After Experiment

### If successful:
1. Extend to larger graphs (p=83,89,97,101) when eigenvalues complete
2. Implement refinement: use detected zeros as initial guesses for Newton's method
3. Paper: "Approximating Riemann Zeta Zeros via Cayley Graph Spectral Zeta Functions"

### If partial success:
1. Investigate error sources: eigenvalue truncation, graph irregularity
2. Try alternative definitions: modified kernel weights, different normalization
3. Consult original Karlsson-Murugan paper for exact implementation details

### If failed:
1. Verify correctness of eigenvalue data
2. Test on known approximating sequences (circular graphs, hypercube)
3. Report negative result as boundary condition for this approach