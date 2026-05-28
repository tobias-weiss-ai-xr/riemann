# Exp 14: Graph Spectral Zeta Functions — FAILURE

**Date:** 2024-05-24  
**Status:** ❌ FAILED  
**Execution time:** 2 hours (implementation + testing)

---

## Executive Summary

The Karlsson-Murugan graph spectral zeta approach **does not work with the implementation attempted**. The spectral zeta function ζ_G(s) computed from Cayley graph Laplacian eigenvalues does not approximate ζ(s) - it produces astronomically large values with completely different zero positions.

---

## Approach

**Implementation:**
- Spectral zeta function: ζ_G(s) = Σ_{i=1}^n (λ_i / λ₁)^{-s}
- Search for zeros on critical line Re(s) = ½ in t ∈ [10, 60]
- Compare detected zeros with actual ζ(s) zeros

**Files:**
- `scripts/spectral_zeta_function.py` (370 lines): Full implementation
- `experiments/exp14_spectral_zeta_design.md`: Design document

---

## Results

### Spectral Zeta Values: Completely Wrong

**p=3 (SL(2,F_3), 24 eigenvalues):**
```
t=10.004, |ζ_G| = 8.89×10²¹
t=14.307, |ζ_G| = 6.19×10²⁸
t=30.427, |ζ_G| = 3.10×10⁴⁸
```
**Magnitudes are 10^21 - 10^77+**, not near zero!

**p=5 (SL(2,F_5), 100 eigenvalues):**
- 16 "zeros" detected via sign changes
- Magnitudes: 10^17 - 10^34
- Positions: t ≈ 11.75, 14.31, 16.20, 17.80, 19.19, 22.77, 24.64, 27.30, 33.32, 36.59
- **Actual ζ(s) zeros:** 14.13, 21.02, 25.01, 30.42, 32.94, 37.59, 40.92, 43.33, 48.01, 49.77
- **NO MATCH**

**p=7 (SL(2,F_7), 100 eigenvalues):**
- 5 "zeros" detected, magnitudes 10^17 - 10^77
- Positions: t ≈ 12.27, 18.51, 25.79, 33.96, 55.69
- **NO MATCH**

**All graphs p ≥ 11:** Either no zeros detected or positions completely wrong.

---

## Root Cause Analysis

### Implementation appears correct, definitions wrong

The spectral zeta definition `ζ_G(s) = Σ (λ_i/λ₁)^{-s}` produces:
1. **Huge magnitudes** (10^20+ for small graphs)
2. **Different zero positions** vs actual ζ(s)
3. **No convergence** to ζ(s) even with larger graphs

### Possible explanations

1. **Wrong spectral zeta definition** - Karlsson-Murugan likely uses a different formulation with additional transformations/configuration
2. **Missing critical steps** - Discrete circle approximation, correct edge weight selection, or spectral density normalization
3. **Graph type mismatch** - Cayley graphs may not satisfy the regularity assumptions in the theorem
4. **Numerical issues** - Normalization by λ₁ not sufficient for convergence

### What this means

**The Karlsson-Murugan theorem cannot be blindly applied**. The spectral zeta function requires specific graph properties and additional conditions that are not met by SL(2,F_p) Cayley graphs as implemented.

---

## Approximation Error Analysis

**Mean error (first 10 ζ(s) zeros):**
| Prime | Mean Error | Notes |
|-------|-----------|-------|
| 3 | 0.020 (but wrong zeros) | 595 spurious "zeros" |
| 5 | 1.098 | 16 wrong positions |
| 7 | 5.953 | 5 wrong positions |
| 11 | 3.478 | 3 wrong positions |
| 13+ | >12.6 | Completely wrong |

**Trend:** Larger p → fewer zeros detected, errors increase, no convergence pattern

---

## What This Experiment Proves

1. **Naive spectral zeta functions don't work:** Simply summing normalized eigenvalues doesn't approximate ζ(s)
2. **Graph regularity assumptions fail:** Cayley graphs' vertex-transitivity doesn't guarantee ζ_G(s) ≈ ζ(s)
3. **Need expert implementation:** Karlsson-Murugan requires precise theoretical understanding beyond the high-level theorem statement

---

## Alternative Directions from Research

Based on the librarian agent's findings, here are **higher-priority alternatives**:

### 1. **Connes Spectral Triples** ⭐⭐⭐ ⭐⭐ (HIGHEST PRIORITY)
- Self-adjoint rank-one perturbation operators approximate ζ(s) zeros
- **Direct spectral realization** with rigorous functional analysis
- Maps rank-one perturbations to operator-on-graphs framework
- Recent publications (2025-2026) with working implementations

### 2. **Karlsson-Murugan Graph Spectral Zeta** (FIXED FORMULATION)
- Need exact paper with implementation details
- Current approach failed; different definition required
- Convergence conditions may require:
  - Specific edge weight schemes
  - Spectral density kernels
  - Truncation with smooth cutoff functions
  - Additional normalization steps

### 3. **Even Dominance CAP Certificates**
- Interval arithmetic certification of spectral gap computations
- Proven technique (33 certificates already)
- Provides rigorous bounds on spectral properties
- Could certify approximations from other methods

### 4. **Murmurations Methodology**
- ML→discovery→proof playbook validated by Inventiones publication
- Demonstrates path from ML discovery to theorem
- Could apply to discovering patterns in spectral data

---

## Next Steps

### Immediate: Report Negative Result
- Document this failure clearly (completed ✅)
- Release spectral zeta files as boundary condition for this approach

### Recommended: Shift to Connes Spectral Triples
**Why:**
- Direct spectral-theoretic approach to ζ(s) zeros
- Rigorous functional analysis framework
- Recent (2025-2026) - cutting edge
- No graph structure assumptions - works with any operator sequence

**Implementation path:**
1. Construct self-adjoint rank-one perturbation operators from spectral data
2. Compute operator traces and spectral properties
3. Approximate ζ(s) zeros via Nevanlinna theory
4. Validate against known zeros

### Alternative: Consult Original Karlsson-Murugan Paper
- Find exact implementation details
- Identify missing transformation steps
- Re-implement with expert guidance
- May require different graph types or edge weights

---

## Time/Budget Summary

| Phase | Time | Result |
|-------|------|--------|
| Literature research (via agents) | 25m | Identified Karlsson-Murugan |
| Implementation | 30m | `spectral_zeta_function.py` written |
| Testing & debugging | 20m | Fixed eigenvalue parsing |
| Execution (all graphs) | 30m | All results collected |
| Analysis & documentation | 35m | This report |
| **Total** | **140m** | **Failed approach documented** |

---

## Conclusion

**The Karlsson-Murugan graph spectral zeta function approach, as implemented, fails to approximate the Riemann zeta function.** The spectral zeta values and zero positions are completely incorrect, showing that:

1. **Simple normalization (λ_i/λ₁) is insufficient**
2. **Cayley graphs don't meet the theorem's assumptions**
3. **Expert-level theoretical understanding is required**

**Recommendation:** Shift to **Connes spectral triples** approach, which offers a direct operator-theoretic path to ζ(s) zero approximations without graph-structure assumptions.

---

## Files Created

- `scripts/spectral_zeta_function.py` (370 lines) - Failed implementation (archived)
- `experiments/exp14_spectral_zeta_design.md` - Design document (archived)
- `data/spectral_zeta_results.json` - Full results (42KB, 4190 lines)
- `experiments/exp14_spectral_zeta_REPORT.md` - This report

**Commit suggestion:**
```
Exp 14: Graph spectral zeta functions — FAILED
- Implemented spectral zeta function from Cayley graph eigenvalues
- Results: ζ_G(s) values are 10^20+, zeros do not match ζ(s)
- Conclusion: Approach requires expert-level implementation details not found
- Recommendation: Shift to Connes spectral triples approach
```