# Explicit Verification: λ₁(1) = 1

**Date**: January 18, 2025

---

## Objective

Prove that the leading eigenvalue of L_1 is exactly 1, with explicit eigenfunction and dual eigenfunction.

---

## Definition of L_1

```
(L_1 f)(x) = ∑_{n=1}^∞ (n + x)^{-2} f(1/(n + x))
```

---

## Step 1: Find the Invariant Measure (The Gauss Measure)

The **Gauss measure** μ on [0,1) is:
```
dμ(x) = (1/ln 2) · (1 / (1 + x)) dx
```

This measure is invariant for the Gauss map g(x) = 1/x - floor(1/x):
```
∫ f(g(x)) dμ(x) = ∫ f(x) dμ(x)
```

**Verification**: Known result, can be found in any text on continued fractions.

---

## Step 2: Dual Space

The space L²((0,1), dμ(x)) has inner product:
```
⟨f, g⟩_μ = ∫_0^1 f(x) g(x) dμ(x) = (1/ln 2) ∫_0^1 (f(x) g(x) / (1 + x)) dx
```

---

## Step 3: Adjoint of L_1 in L²(μ)

The adjoint of L_1, denoted L_1^*, satisfies:
```
⟨L_1 f, g⟩_μ = ⟨f, L_1^* g⟩_μ
```

Compute:
```
⟨L_1 f, g⟩_μ = (1/ln 2) ∫_0^1 [∑ (n+x)^{-2} f(1/(n+x))] · [g(x)/(1+x)] dx
```

Change of variable: Let y = 1/(n+x), so x = 1/y - n.
Then: dx/dy = -1/y², and when x goes from 0 to 1, y goes from 1/(n+1) to 1/n.

```
= (1/ln 2) ∑_{n=1}^∞ ∫_{1/(n+1)}^{1/n} (n+x)^{-2} f(1/(n+x)) · g(x)/(1+x) dx
```

Substituting x = 1/y - n:
```
n + x = n + 1/y - n = 1/y
1 + x = 1 + 1/y - n = (y + 1 - ny)/y
dx = -dy/y²
```

```
= (1/ln 2) ∑_{n=1}^∞ ∫_{1/n}^{1/(n+1)} (1/y)^{-2} f(y) · g(1/y - n)/[1 + 1/y - n] · (dy/y²)
```

Wait, the limits flip due to the negative sign:
```
= (1/ln 2) ∑_{n=1}^∞ ∫_{1/(n+1)}^{1/n} y² f(y) · g(1/y - n) · y/(y + 1 - ny) · (dy/y²)
= (1/ln 2) ∑_{n=1}^∞ ∫_{1/(n+1)}^{1/n} f(y) · g(1/y - n) · [y/(y + 1 - ny)] · dy
```

Let's simplify the bracket:
```
y/(y + 1 - ny) = y/(y(1 - n) + 1) = y/(1 - (n-1)y)
```

Hmm, this doesn't simplify cleanly. Let me try a different approach.

---

## Alternative Approach: Perron-Frobenius

For a **positive compact operator** on a function space, the Perron-Frobenius theorem states:
1. The spectral radius ρ is a positive eigenvalue
2. There exists a positive eigenfunction corresponding to ρ
3. ρ is simple (algebraic multiplicity 1)

### Positivity

L_1 is positive: (n+x)^{-2} > 0 for all n, x ∈ [0,1), so for f ≥ 0, we have L_1 f ≥ 0.

### Compactness

L_1 is compact if it maps bounded sets to relatively compact sets. For L_1 with summable weights, this is standard.

### Spectral Radius

To find ρ(L_1), we can try calculus of variations:

```
ρ(L_1) = sup_{||f||=1} ||L_1 f||
```

But this is abstract. Let's try to find an invariant function.

---

## Step 4: Look for a Fixed Point

We want f such that L_1 f = λ f.

For the Gauss map with invariant measure μ, we know that constant function 1 is invariant:
```
∫ (L_1 f)(x) dμ(x) = ∫ [∑ (n+x)^{-2} f(1/(n+x))] dμ(x)
```

From invariance of μ:
```
∫ f(1/(n+x)) dμ(x) = ∫ f(y) dμ(y)  (for each fixed n)
```

```
∫ (L_1 f)(x) dμ(x) = ∑_{n=1}^∞ (n+x)^{-2} · ∫ f(1/(n+x)) dμ(x)
```

This isn't quite right because (n+x)² is inside the integral.

Let me try f ≡ 1 (constant function):
```
(L_1 1)(x) = ∑_{n=1}^∞ (n+x)^{-2} · 1
```

This sum depends on x, so constant 1 is NOT an eigenfunction.

---

## Step 5: Try Different Approach - Use Known Results

From the literature on transfer operators for the Gauss map:

**Known result**: The Perron-Frobenius operator (transfer operator) of the Gauss map has:
- Spectral radius = 1
- Leading eigenfunction related to the invariant density
- Eigenvalue 1 corresponds to the invariant measure

The **invariant density** of the Gauss map in the standard L¹ space is:
```
ψ(x) = 1/(1+x)
```

Let's verify:
```
(ℒ ψ)(x) = ∑_{n=1}^∞ |g'(g_n(x))| · ψ(g_n(x))
```

For the Gauss map: |g'(y)| = 1/y², and g_n(x) = 1/(n+x).

```
= ∑_{n=1}^∞ [1/(n+x)²] · [1/(1 + 1/(n+x))]
= ∑_{n=1}^∞ [1/(n+x)²] · [(n+x)/(n+x+1)]
= ∑_{n=1}^∞ 1/[(n+x)(n+x+1)]
= ∑_{n=1}^∞ [1/(n+x) - 1/(n+x+1)]
= 1/(1+x)  (telescoping series!)
```

**VERIFIED!** The operator ℒ (standard transfer operator) has eigenfunction ψ(x) = 1/(1+x) with eigenvalue 1.

But wait, our L_1 is:
```
(L_1 f)(x) = ∑_{n=1}^∞ (n+x)^{-2} f(1/(n+x))
```

This is different from ℒ! The standard transfer operator is:
```
(ℒ f)(x) = ∑_{n=1}^∞ |g'(g_n(x))| f(g_n(x)) = ∑_{n=1}^∞ (n+x)² f(1/(n+x))
```

Our L_1 has (n+x)^{-2}, not (n+x)²!

This means:
```
L_1 = (D)^{-2} ℒ
```
where D is the multiplication operator (Df)(x) = (n+x)f... no that doesn't make sense.

Actually, the relationship is:
```
L_1 f = ∑ (n+x)^{-2} f(1/(n+x))
ℒ f = ∑ (n+x)² f(1/(n+x))
```

These are **different operators**. The standard literature is about ℒ, not L_1.

---

## CRITICAL REALIZATION

The literature on transfer operators for the Gauss map typically uses:
```
ℒ f(x) = ∑_{n=1}^∞ (n+x)² f(1/(n+x))
```
which has spectral radius 1.

**But our operator L_s is:**
```
L_s f(x) = ∑_{n=1}^∞ (n+x)^{-2s} f(1/(n+x))
```

These are **inverses** in some sense (at least for s = -1).

For s = 1:
- ℒ L_1 = ? This doesn't simplify.

**This is a fundamental issue**: The existing literature (Mayer, Baladi, etc.) might be studying a different class of operators than our L_s.

Let me check Mayer (1991) to see what transfer operator he actually uses...

**From Mayer (1991)**: The transfer operator is defined with weights |g'|^s, not |g'|^{-s}.

**Conclusion**: The L_s in our paper might be the **wrong operator** or might be using a different convention.

This needs to be clarified before proceeding.

---

## 🔴 STATUS UPDATE

**Previous assumption**: L_1 is the Perron-Frobenius operator of the Gauss map.

**Actual situation**: 
- L_s f(x) = ∑ (n+x)^{-2s} f(1/(n+x))
- Standard Perron-Frobenius: ℒ_s f(x) = ∑ (n+x)^{2s} f(1/(n+x))
- These are DIFFERENT operators

**Critical question**: Which operator does Mayer (1991) use?

If Mayer uses ℒ_s (the standard PF operator), then:
- Z_S(s) = det(1-ℒ_s)det(1+ℒ_s)
- But our paper talks about L_s

**This is either**:
1. A notational difference (unlikely)
2. A confusion in the paper (possible)
3. I'm misreading the paper (possible)

---

## 🎯 NEXT STEP

**Action Required**: 
1. Check Mayer (1991) paper for EXACT transfer operator definition
2. Verify that our L_s matches what Mayer uses
3. If not, the entire identity approach is invalid

**If Mayer uses L_s as defined here**: Good, proceed.
**If Mayer uses a different operator**: The proof foundation is invalid.

---

*End Status Check - Need Literature Verification*
