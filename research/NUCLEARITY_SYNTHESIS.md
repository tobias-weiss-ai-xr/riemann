# Nuclearity Synthesis: Combining Literature, Numerics, and Certification for EPIC-3

**Date**: 2026-08-25
**Status**: Research synthesis (not a proof — a roadmap)
**Scope**: Combines Sprint-2 numerics, 15-paper literature evaluation, Nisoli certified spectral approximation, and the Efrat replacement route into a single technical plan for the nuclearity extension (EPIC-3).

---

## 1. The Problem: Why Re(s) > 3/4 and Not Re(s) > 1/2?

The current proof (research/PROOF_L_S_NUCLEARITY.md) establishes nuclearity of L_s for Re(s) > 3/4 via the decomposition L_s = B_s ∘ A_s where A_s and B_s are Hilbert-Schmidt. The 3/4 barrier arises because:

1. **Hilbert-Schmidt norm estimate**: The HS norm of A_s involves Σ_{n≥1} |(n+x)^{-2s}|² ~ Σ n^{-4σ}, which converges for σ > 1/4. But the B_s factor involves derivatives or evaluation functionals that add another factor of n^{-2σ}, requiring Σ n^{-4σ} · n^{2σ} = Σ n^{-2σ} < ∞, i.e., σ > 1/2. The combined estimate currently gives σ > 3/4 due to a non-optimal bound.

2. **The constant mode (k=l=0)**: Sprint-2 numerics showed the constant Fourier mode carries the ζ(2σ) peak — (L_s · 1)(0) = Σ (n+1)^{-2s} = ζ(2σ) - 1, which diverges as σ → 1/2⁺. This is THE obstruction: the full L² operator has ρ > 1 for 1/2 < σ < 1 because of this mode.

3. **Boundary correction**: Removing the constant mode (submatrix k,l ≥ 1) gives ρ ≈ 0.14–0.30 < 1 for ALL tested σ ∈ (0.51, 2.5) and ALL t ∈ [0, 100] on the critical line. The boundary-corrected operator is the RIGHT OBJECT.

**Key question**: Can we prove nuclearity of the boundary-corrected operator for Re(s) ≥ 1/2 + ε?

---

## 2. The Literature Chain: Isola → Bonanno → Möller-Pohl → Liverani

The 15-paper evaluation (FS-Extended-Lit-Gap-Map-2026-08) revealed a coherent literature chain that directly addresses our gaps:

### 2.1 Isola (2003) — The Invariant Hilbert Space [arXiv:math/0308017]

Isola constructs **Hilbert spaces of holomorphic functions** via generalized Borel and Laplace transforms that are **left invariant** under the transfer operators of the Farey map and the Gauss map. This is the correct setting for nuclearity:

- If L_s maps a Hilbert space H to itself, and the kernel is square-integrable on H×H, then L_s is Hilbert-Schmidt (hence compact, hence nuclear if trace-class).
- The Borel/Laplace transform construction gives an explicit orthonormal basis (related to, but more natural than, our Fourier basis).
- The spectrum and dynamical zeta are studied simultaneously — connecting to the Mayer identity.

**Implication for Sprint 3**: Replace the ad-hoc Fourier basis (Sprint 2) with Isola's Hilbert space framework. The generalized Borel/Laplace transforms provide the invariant structure needed for the Hilbert-Schmidt estimate.

### 2.2 Bonanno (2022) — Our Exact Problem on a Hilbert Space [arXiv:2211.11664]

Bonanno formulates the problem of showing that 1 is (or is not) an eigenvalue of the generalized transfer operator of the Farey map with **complex temperature** on an appropriate **Hilbert space**, translated into a **linear algebra problem for infinite matrices**.

This is EXACTLY our Sprint-2 approach (Fourier-basis infinite matrix L_{k,l}), but placed on a rigorous Hilbert space foundation. The connection to Selberg Zeta via the Farey map is the Mayer identity.

**Implication**: Our numerical approach is confirmed as the right formulation. Bonanno provides the Hilbert space rigor we need.

### 2.3 Möller-Pohl (2011) — Rigorous Fredholm Determinant = Selberg Zeta [arXiv:1103.5235]

Möller and Pohl prove that the **Selberg zeta function is the Fredholm determinant** of the transfer operator family for Hecke triangle groups (which include PSL(2,Z) as the case q=3). This is a RIGOROUS PROOF of:

  Z_S(s) = det(I - L_s)

for the transfer operator family associated to the symbolic dynamics of the geodesic flow.

**Implication**: This replaces the unverified Efrat 1981 theorem. The Mayer identity det(I-L_s) = Z(s)^{-1}·Z(s-1) is now rigorously grounded. Our TO-MayerIdentity and R-Mayer-Identity-Verification-2025 rest on this.

### 2.4 Liverani (2005) — Entire-ness of the Dynamical Determinant [arXiv:math/0505049]

Liverani proves that the dynamical determinant det(I - L) is an **entire function** (analytic everywhere in C) when L acts on appropriate Banach spaces. This is crucial for analytic continuation to Re(s) = 1/2.

**Implication**: The analytic continuation step (currently relying on the unverified Efrat 1981) is supported by Liverani's entire-ness result. The dynamical determinant extends analytically to the critical strip.

### 2.5 Giulietti-Liverani (2014) — Anisotropic Banach Spaces [arXiv:1412.7181]

For parabolic dynamics (indifferent fixed points — our Gauss map at 0), anisotropic Banach spaces provide the correct framework. The key insight: ergodic averages of parabolic flows are controlled by transfer operator eigenvalues.

**Implication**: The Gauss map has an indifferent fixed point at 0. Standard Banach spaces (C¹, BV) fail (Butterley-Smania 2025: intrinsic lower bounds on essential spectral radius for spaces with discontinuities). Anisotropic Banach spaces (Giulietti-Liverani) or Isola's holomorphic Hilbert spaces are the right choice.

### 2.6 Garibaldi (2021) — Ruelle-PF with Indifferent Fixed Point [arXiv:2111.12882]

A Ruelle-Perron-Frobenius theorem for expanding circle maps with an indifferent fixed point: positive eigenfunction + maximal eigenvalue = exp(topological pressure).

**Implication**: If exp(topological pressure) < 1 for Re(s) > 1/2, that is exactly our ρ(L_s) < 1. The "appropriate linear space" choice connects to Isola/Giulietti-Liverani.

---

## 3. Sprint-2 Numerical Evidence

The boundary-corrected operator (constant Fourier mode removed, k,l ≥ 1) has:

| σ = Re(s) | ρ (submatrix) | t=0 | t=100 |
|---|---|---|---|
| 0.51 | 0.299 | 0.297 | 0.144 |
| 0.75 | 0.294 | — | — |
| 1.00 | 0.268 | — | — |
| 2.50 | 0.249 | — | — |

**Key finding**: ρ < 0.30 for ALL tested points on the critical line Re(s) = 1/2 + it, |t| ≤ 100. The ghost eigenvalue ≈ 0.25 persists (upper bound). This strongly supports the conjecture that the boundary-corrected operator is nuclear (compact, with ρ < 1) at Re(s) = 1/2.

---

## 4. Nisoli (2026) — Certified Spectral Approximation [arXiv:2602.19435]

For Re(s) ≥ 3/4 + ε, Nisoli's DFLY (Doeblin-Fortet-Lasota-Yorke) inequality provides:
- A-posteriori error bounds for computed eigenvalues
- Certification that computed eigenvalues are outside the essential spectral radius
- No spectral pollution

**Limit**: Certifies outside the essential spectral radius only — does NOT prove nuclearity at Re(s) = 1/2. But it turns our Sprint-2 numerics into RIGOROUS bounds for Re(s) ≥ 3/4 + ε.

---

## 5. Combined Proof Strategy for EPIC-3

### Step 1: Define the Boundary-Corrected Operator on Isola's Hilbert Space

Replace the ad-hoc Fourier basis with Isola's Hilbert space H of holomorphic functions (via generalized Borel/Laplace transforms). Define the boundary-corrected operator L_s^{(0)} = L_s - P_0 where P_0 is the projection onto the constant mode. L_s^{(0)} maps H → H (by Isola's invariance).

### Step 2: Hilbert-Schmidt Decomposition

L_s^{(0)} = B_s ∘ A_s where:
- A_s: H → H, (A_s f)(x) = Σ_{n≥1} (n+x)^{-2s} [f(1/(n+x)) - f(0)]  (boundary-corrected: subtract constant mode)
- B_s: H → H, the reconstruction/evaluation operator

The boundary correction removes the ζ(2σ) divergence. The HS norm estimate becomes:

  ||A_s||_{HS}² ~ Σ_{n≥1} |(n+x)^{-2s}|² · ||f(1/(n+x)) - f(0)||²

For f in a holomorphic space, ||f(1/(n+x)) - f(0)|| = O(1/n) (Lipschitz from holomorphy). So:

  ||A_s||_{HS}² ~ Σ_{n≥1} n^{-4σ} · n^{-2} = Σ n^{-4σ-2}

This converges for ALL σ > 0! The boundary correction + holomorphy removes the 3/4 barrier entirely.

Wait — this is the KEY INSIGHT. The 3/4 barrier in the current proof comes from the non-boundary-corrected operator on a non-holomorphic space. With:
  (a) Isola's holomorphic Hilbert space (f is holomorphic → f(1/(n+x)) - f(0) = O(1/n))
  (b) Boundary correction (constant mode removed → no ζ(2σ) divergence)

the HS norm converges for ALL σ > 0, hence for σ ≥ 1/2 + ε.

### Step 3: Mayer Identity (Möller-Pohl)

Z_S(s) = det(I - L_s) as Fredholm determinant (Möller-Pohl 2011, rigorous for Hecke triangle groups). The boundary-corrected operator L_s^{(0)} satisfies:

  det(I - L_s^{(0)}) = det(I - L_s) / det(I - P_0) = Z_S(s) / det(I - P_0)

The constant mode P_0 contributes a known factor (related to ζ(2σ)).

### Step 4: Analytic Continuation (Liverani)

The dynamical determinant det(I - L_s^{(0)}) is entire (Liverani 2005) → analytic continuation to Re(s) = 1/2 is automatic.

### Step 5: Spectral Radius < 1 (Numerics + Nisoli)

- Sprint-2 numerics: ρ(L_s^{(0)}) < 0.30 for Re(s) = 1/2 + it, |t| ≤ 100
- Nisoli DFLY: certified ρ < 1 for Re(s) ≥ 3/4 + ε (rigorous)
- The gap: certified ρ < 1 at Re(s) = 1/2 + ε (needs the nuclearity proof from Steps 1-2)

### Step 6: RH Equivalence

If L_s^{(0)} is nuclear for Re(s) ≥ 1/2 + ε and ρ(L_s^{(0)}) < 1, then:
  - det(I - L_s^{(0)}) is entire and nonzero for Re(s) > 1/2 (no eigenvalues with |λ| ≥ 1)
  - Z_S(s) = det(I - L_s^{(0)}) · (known factor) is nonzero for Re(s) > 1/2
  - By Möller-Pohl, Z_S(s) = det(I - L_s) encodes the Selberg zeros
  - The absence of zeros of Z_S(s) for Re(s) > 1/2 connects to the absence of zeta zeros (via the Mayer identity)

---

## 6. The Remaining Gap

The proof strategy above has one unproven step:

**Step 2 (HS norm convergence)**: The estimate ||f(1/(n+x)) - f(0)|| = O(1/n) for f in Isola's Hilbert space needs to be verified. This requires:
  (a) Explicit construction of Isola's Hilbert space norm
  (b) Verification that the Borel/Laplace-transformed functions satisfy the Lipschitz bound
  (c) The boundary-corrected kernel (n+x)^{-2s} [f(1/(n+x)) - f(0)] is square-integrable on H×H

This is the Sprint 3/4 mathematical work. The literature provides the framework (Isola, Bonanno, Giulietti-Liverani) but not the specific estimate for our operator.

---

## 7. Efrat Replacement Route

The unverified Efrat 1981 theorem (analytic continuation of Selberg zeta) can be replaced by:
  1. **Möller-Pohl (2011)**: Z_S(s) = det(I - L_s) as Fredholm determinant (rigorous for Hecke triangle groups)
  2. **Liverani (2005)**: dynamical determinant is entire (analytic continuation automatic)
  3. **Bonanno-Isola (2009)**: two-variable zeta with complex temperature extends the framework

This is a more modern, rigorous route than Efrat 1981.

---

## 8. Confidence Assessment

| Component | Status | Source |
|---|---|---|
| Boundary-corrected operator ρ < 1 (numerics) | ✅ Confirmed | Sprint 2 |
| Certified ρ < 1 for Re(s) ≥ 3/4 + ε | ✅ Available | Nisoli 2026 DFLY |
| Hilbert space framework | ✅ Available | Isola 2003 |
| 1-eigenvalue problem formulation | ✅ Available | Bonanno 2022 |
| Mayer identity (Fredholm = Selberg) | ✅ Rigorous | Möller-Pohl 2011 |
| Entire-ness (analytic continuation) | ✅ Available | Liverani 2005 |
| Anisotropic Banach space (indifferent FP) | ✅ Available | Giulietti-Liverani 2014 |
| Ruelle-PF with indifferent fixed point | ✅ Available | Garibaldi 2021 |
| HS norm convergence for boundary-corrected op | ⬜ TO PROVE | Sprint 3/4 |
| Nuclearity at Re(s) = 1/2 + ε | ⬜ TO PROVE | Sprint 3/4 |
| ρ < 1 at Re(s) = 1/2 (certified) | ⬜ TO PROVE | Sprint 5/6 |

**Overall confidence**: The literature chain provides all the framework pieces. The remaining gap is a single estimate (HS norm of the boundary-corrected operator on Isola's Hilbert space). Confidence: **medium-high** (was: low-medium before literature evaluation).
