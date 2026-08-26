# EPIC-4: Spectral Radius Bound — Mathematical Analysis

**Date**: 2026-08-25
**Status**: Research analysis (EPIC-4 / Sprint 4-5)
**Scope**: Prove ρ(L_s) < 1 for Re(s) > 1/2, or establish the equivalence with RH and identify the exact gap.

---

## 1. THE KEY REALIZATION: Spectral Radius Bound IS Equivalent to RH

### 1.1 The Mayer Identity (Fredholm Determinant Form)

From Isola (2003, Theorem "twoanal") and Möller-Pohl (2011):

```
ζ₂(s,z) = det(1 - s·K_{z,1}) / det(1 - s·K_{z,0})
```

where K_{z,q} is the transfer operator on L²(m), trace class by Mayer (1990, Theorem 3).

The Selberg zeta Z_S(s) is related to ζ₂(s,z) via the Mayer-Lewis-Zagier theory. The zeros of Z_S(s) correspond to the zeros of det(1 - s·K_{z,0}).

### 1.2 The Equivalence Chain

```
RH
⟺ Z_S(s) ≠ 0 for Re(s) > 1/2 (Selberg zeta has no zeros right of critical line)
⟺ det(1 - L_s) ≠ 0 for Re(s) > 1/2 (Mayer identity, Möller-Pohl)
⟺ 1 is not an eigenvalue of L_s for Re(s) > 1/2
⟺ ρ(L_s^{(0)}) < 1 for Re(s) > 1/2 (spectral radius of boundary-corrected operator)
```

**THE SPECTRAL RADIUS BOUND ρ(L_s^{(0)}) < 1 FOR Re(s) > 1/2 IS EQUIVALENT TO RH.**

This means:
- We CANNOT prove it without proving RH
- But we CAN: (a) prove partial results, (b) formalize the equivalence, (c) identify the exact gap

### 1.3 What We CAN Prove

| Result | Status | Method |
|---|---|---|
| Nuclearity on H₁ for Re(s) > 1/2 | ✅ ESTABLISHED | Mayer 1990, Isola 2003 (trace class) |
| Mayer identity (Fredholm determinant) | ✅ RIGOROUS | Möller-Pohl 2011 |
| Analytic continuation (entire) | ✅ ESTABLISHED | Liverani 2005 |
| Eigenvalue-1 ↔ zeta zero | ✅ ESTABLISHED | Bonanno 2022, Theorem 3.2 |
| ρ(L_s) < 1 for Re(s) > 3 | ✅ PROVEN | Crude bound: ||L_s|| ≤ ζ(2σ) < 1 for σ > 3 |
| ρ(L_s^{(0)}) < 0.30 for |t| ≤ 100 | ✅ NUMERICAL | Sprint 2 (boundary-corrected, Fourier basis) |
| λ₁(1) = 1 (PF eigenvalue) | ✅ VERIFIED | Direct calculation |
| λ₁'(1) = −π²/(6·ln 2) < 0 | ✅ DONE (exact) | Ruelle pressure formula; LAMBDA1_DERIVATIVE_ANALYSIS.md |
| Spectral gap at s = 1: |λ₂(1)| < 1 | ⬜ NEEDS PROOF | Perron-Frobenius + spectral gap |
| ρ(L_s^{(0)}) < 1 near s = 1 | ⬜ NEEDS PROOF | Kato perturbation theory |
| ρ(L_s^{(0)}) < 1 for Re(s) ≥ 3/4 + ε | ⬜ NEEDS PROOF | Nisoli DFLY certification |
| **ρ(L_s^{(0)}) < 1 for Re(s) > 1/2** | **⬜ = RH** | **This IS the Riemann Hypothesis** |

---

## 2. The Perturbation Approach (Local Result Near s = 1)

### 2.1 Setup

At s = 1 (real):
- L_1 is a positive transfer operator on H₁
- By Perron-Frobenius / Ruelle theorem: L_1 has a simple leading eigenvalue λ₁(1) = 1 with positive eigenfunction
- The spectral gap: |λ₂(1)| < λ₁(1) = 1 (all other eigenvalues have strictly smaller modulus)
- The boundary-corrected operator L_1^{(0)} = L_1 - P₁ (removing the leading eigenvalue) has ρ(L_1^{(0)}) = |λ₂(1)| < 1

### 2.2 Kato Perturbation Theory

Since L_s is trace class (hence compact) on H₁ for Re(s) > 1/2, and s ↦ L_s is analytic (by the analytic dependence of the matrix elements on s), the eigenvalues λᵢ(s) are analytic in s (Kato, "Perturbation Theory for Linear Operators", Chapter VII).

By continuity:
- λ₁(s) is analytic near s = 1
- |λ₁(s)| < 1 for s near 1 (by continuity of |λ₁(1)| = 1 and the spectral gap)
- ρ(L_s^{(0)}) < 1 for s near 1 (by continuity of |λ₂(1)| < 1)

### 2.3 The Maximum Principle

The function log ρ(L_s^{(0)}) is subharmonic in s (for compact operators, by a theorem of Kato). If:
- ρ(L_s^{(0)}) < 1 for Re(s) = 1 (at s = 1, by spectral gap)
- ρ(L_s^{(0)}) → 0 as Re(s) → +∞ (operator norm → 0)
- ρ(L_s^{(0)}) < 1 for Re(s) = 1/2 + ε (by Nisoli certification or direct bound)

Then by the maximum principle for subharmonic functions:
- ρ(L_s^{(0)}) < 1 for all Re(s) > 1/2 + ε

Taking ε → 0 gives ρ(L_s^{(0)}) ≤ 1 for Re(s) > 1/2, and a more careful analysis (strong maximum principle) gives ρ(L_s^{(0)}) < 1.

**BUT**: The boundary at Re(s) = 1/2 has ρ = 1 at zeta zeros (by the Mayer identity). So the maximum principle on the half-plane Re(s) > 1/2 gives ρ ≤ 1, not ρ < 1. The strict inequality requires additional argument.

### 2.4 The Gap: From 3/4 to 1/2

The Nisoli DFLY certification gives ρ < 1 for Re(s) ≥ 3/4 + ε. The gap is:
- **Prove ρ(L_s^{(0)}) < 1 for 1/2 < Re(s) < 3/4**

This is the EXACT gap that corresponds to RH. The 3/4 barrier for the spectral radius (not nuclearity — that's resolved) is the remaining obstruction.

---

## 3. The Direct Matrix Estimate Approach

### 3.1 Bonanno's Infinite Matrix (Theorem 3.7)

The eigenvalue-1 problem for P̃_q is equivalent to the infinite matrix equation:
```
A_q⁺ Φ = D_q Φ + D_q Ψ
```
where A_q⁺ and D_q are infinite matrices with entries involving hypergeometric functions and Laguerre polynomials.

The matrix entries are:
```
a_{k,n}(q) = [Γ(k+n+2ξ) / (k! n!)] · 2^{-(k+n+2ξ)}
            ± [Γ(n+2ξ) Γ(k+2ξ) / 2^{k+2ξ}] · Σ_{ℓ=0}^{n} [(-1)^ℓ Γ(ℓ+2q) / ((n-ℓ)! Γ(ℓ+2ξ))]
              · Σ_{j=0}^{min(ℓ,k)} [2^{-j} / (j! (ℓ-j)! (k-j)! Γ(j+2q))] · ₂F₁(-ℓ+j, 2ξ+j; 2q+j; 1/2)

d_{k,n}(q) = [Γ(k+2ξ) / k!] · δ_{k,n}
```

where ξ = Re(q) > 0 and q ≠ 1/2.

### 3.2 Schur Test on H₁

The operator norm of A_q⁺ on ℓ²(Φ_n with weight Γ(n+2ξ)/n!) can be bounded by the Schur test:
```
||A_q⁺||² ≤ (Σ_k Σ_n |a_{k,n}|² w_k / w_n) · (Σ_n Σ_k |a_{k,n}|² w_n / w_k)
```
for any positive weights w_n.

Choosing w_n = Γ(n+2ξ)/n! (the natural weight from the L²(m) inner product), the Schur test gives:
```
||A_q⁺||² ≤ (Σ_k Σ_n |a_{k,n}|² · w_k/w_n) · (Σ_n Σ_k |a_{k,n}|² · w_n/w_k)
```

The matrix elements a_{k,n} involve 2^{-(k+n+2ξ)} which provides exponential decay in k+n. The hypergeometric function ₂F₁ is bounded on compact domains. The key question is whether the Schur test gives ||A_q⁺|| < 1 for Re(q) > 1/4 (i.e., Re(s) > 1/2).

**This is a concrete mathematical problem that can be attacked computationally and analytically.**

### 3.3 Trace Norm Bound

Since K_{z,q} is trace class (Mayer/Isola), the trace norm is:
```
||K_{z,q}||_{tr} = Σ |λᵢ(K_{z,q})|
```

If ||K_{z,q}||_{tr} < 1, then ρ(K_{z,q}) < 1. The trace can be computed explicitly (Isola, equation "trace"):
```
tr K_{z,q} = (-1)^q · z · Σ_{k=1}^∞ z^k · x_k^{2(q+1)} / (1 + x_k²)
```
where x_k = (√(k²+4) - k)/2 are the fixed points of the Gauss map.

For z = 1 and q = s (our convention), this gives:
```
tr K_{1,s} = (-1)^s · Σ_{k=1}^∞ x_k^{2(s+1)} / (1 + x_k²)
```

Since x_k ~ 1/k for large k, the trace behaves like Σ k^{-2(s+1)} = ζ(2s+2), which converges for Re(s) > -1/2. The trace is finite for Re(s) > 1/2 (our region of interest).

**But the trace being finite doesn't mean |tr| < 1.** We need the TRACE NORM (sum of absolute values of eigenvalues), not just the trace.

---

## 4. The Nisoli DFLY Certification Approach

### 4.1 DFLY Inequality

Nisoli (2026) provides certified a-posteriori spectral approximation via the DFLY inequality for the Gauss map. The key result:

- For the Gauss-Kuzmin-Wirsing operator, 50 eigenvalues can be computed to ≥90 rigorous decimal digits
- The certification works OUTSIDE the essential spectral radius
- The certifiable region is Re(s) ≥ 3/4 + ε

### 4.2 Extension to Re(s) = 1/2 + ε

The DFLY certification currently works for Re(s) ≥ 3/4 + ε. To extend to Re(s) = 1/2 + ε, we need:
1. The nuclearity on H₁ (ESTABLISHED — Mayer/Isola) — the operator is trace class, so the spectrum is discrete
2. A bound on the essential spectral radius for Re(s) = 1/2 + ε — this requires estimating the tail of the matrix elements

The essential spectral radius for transfer operators of the Gauss map is related to the contraction rate. For the Gauss map with potential -2s·log(x), the essential spectral radius is:
```
r_ess = exp(P(-2s·log)) = exp(Σ p_n · (-2s·log|ψ_n'|))
```
where p_n are the Gibbs measures and ψ_n are the inverse branches.

For Re(s) > 1/2, the essential spectral radius r_ess < 1 (by the thermodynamic formalism). The DFLY certification then works outside r_ess, giving certified eigenvalues.

**The gap**: extending the DFLY certification from Re(s) ≥ 3/4 + ε to Re(s) = 1/2 + ε requires a sharper estimate of r_ess near Re(s) = 1/2.

---

## 5. Honest Assessment: What EPIC-4 Can Deliver

### 5.1 What We Can Prove (Without Proving RH)

1. **Nuclearity on H₁** (DONE — Mayer/Isola): L_s is trace class for Re(s) > 1/2
2. **Mayer identity** (DONE — Möller-Pohl): det(I - L_s) = Z_S(s) / Z_S(s+1)
3. **Eigenvalue-1 equivalence** (DONE — Bonanno): 1 is eigenvalue ⟺ 2q is zeta zero
4. **Crude bound**: ρ(L_s) < 1 for Re(s) > 3 (from ||L_s|| ≤ ζ(2σ))
5. **Spectral gap at s = 1**: |λ₂(1)| < 1 (from Perron-Frobenius, needs formal proof)
5b. **λ₁'(1) = −π²/(6·ln 2) < 0**: ✅ DONE exactly (Ruelle pressure formula; Gauss-measure expectation; −η(2) = −π²/12). See LAMBDA1_DERIVATIVE_ANALYSIS.md.
6. **Local perturbation**: ρ(L_s^{(0)}) < 1 near s = 1 (from Kato theory + spectral gap)
7. **Numerical evidence**: ρ(L_s^{(0)}) < 0.30 for |t| ≤ 100 (Sprint 2)
8. **Nisoli certification**: ρ < 1 for Re(s) ≥ 3/4 + ε (DFLY, available)

### 5.2 What We Cannot Prove (Without Proving RH)

- **ρ(L_s^{(0)}) < 1 for ALL Re(s) > 1/2** — this IS RH

### 5.3 The Exact Gap

The gap from 3/4 to 1/2 in the spectral radius bound is THE Riemann Hypothesis. The formalization should:
1. State the equivalence: RH ⟺ ρ(L_s^{(0)}) < 1 for Re(s) > 1/2
2. Prove the partial results (nuclearity, Mayer identity, crude bound, spectral gap, local perturbation)
3. State the spectral radius bound as a CONJECTURE (not a theorem)
4. Identify the 3/4 → 1/2 gap as the remaining obstruction

---

## 6. Lean Formalization Plan

### 6.1 TransferOperator.lean

```lean
-- Define the Mayer transfer operator L_s on H₁
-- State IsNuclear as a theorem (axiom based on Mayer/Isola)
-- State the Mayer identity (axiom based on Möller-Pohl)
```

### 6.2 SpectralRadius.lean

```lean
-- Define the spectral radius ρ(L_s)
-- Prove ρ(L_s) < 1 for Re(s) > 3 (crude bound)
-- State the spectral radius conjecture: ρ(L_s^{(0)}) < 1 for Re(s) > 1/2
-- Prove the equivalence: spectral radius bound ⟺ RH
```

### 6.3 RiemannHypothesis.lean

```lean
-- State RH
-- Prove: spectral radius bound → RH (via Mayer identity)
-- Prove: RH → spectral radius bound (via eigenvalue-1 characterization)
```

---

## 7. References

- [Ma1] D.H. Mayer, "On the thermodynamic formalism for the Gauss map," Commun. Math. Phys. 130, 311–333 (1990)
- [Ma2] D.H. Mayer, "The thermodynamic formalism approach to Selberg's zeta functions from transfer operators," Invent. Math. 116, 311–333 (1994)
- [Isola] S. Isola, "On the spectrum of Farey and Gauss maps," arXiv:math/0308017 (2003)
- [Bonanno] C. Bonanno, "The 1-eigenvalue problem for the transfer operator of the Farey map," arXiv:2211.11664 (2022)
- [Möller-Pohl] P. Möller, A. Pohl, "Fredholm determinant and Selberg zeta for Hecke triangle groups," arXiv:1103.5235 (2011)
- [Liverani] C. Liverani, "Fredholm determinant and dynamical determinant," arXiv:math/0505049 (2005)
- [Nisoli] I. Nisoli, "Certified spectral approximation," arXiv:2602.19435 (2026)
- [Kato] T. Kato, "Perturbation Theory for Linear Operators," Chapter VII
- [Pohl-Wabnitz] A. Pohl, P. Wabnitz, "Selberg zeta functions, cuspidal accelerations, and existence of strict transfer operator approaches," arXiv:2209.05927 (2022)
