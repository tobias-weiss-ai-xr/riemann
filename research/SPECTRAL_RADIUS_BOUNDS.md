# Rigorous Bounds: ρ(L_s) < 1 for Re(s) > 1

**Date**: January 18, 2025

---

## Goal

Prove that for all s ∈ ℂ with Re(s) > 1, the spectral radius ρ(L_s) < 1.

---

## Method 1: Operator Norm Bound on L∞([0,1])

Consider L_s acting on X = C([0,1]) with sup norm ||f||∞ = sup_{x∈[0,1]} |f(x)|.

```
||L_s|| = sup_{||f||∞ ≤ 1} ||L_s f||∞
```

For any f with ||f||∞ ≤ 1:
```
|(L_s f)(x)| = |∑ (n+x)^{-2s} f(1/(n+x))|
           ≤ ∑ |n+x|^{-2Re(s)} |f(1/(n+x))|
           ≤ ∑ (n)^{-2σ} · 1  (since x ≥ 0, so n+x ≥ n)
           = ∑_{n=1}^∞ n^{-2σ}
           = ζ(2σ)
```

where σ = Re(s).

So: ||L_s|| ≤ ζ(2σ)

**Now**, for σ > 1:
- ζ(s) is decreasing on the positive real axis
- ζ(2) ≈ 1.64
- ζ(3) ≈ 1.20
- ζ(4) ≈ 1.08

But we need ||L_s|| < 1!

The bound ζ(2σ) < 1 is only achieved when:
- ζ(2σ) < 1
- 2σ > 6 ⇒ σ > 3

**Result**: For Re(s) > 3, we have ||L_s|| < ζ(6) < 1, hence ρ(L_s) < 1.

**But**: For 1 < Re(s) ≤ 3, this bound doesn't give ρ < 1.

---

## Method 2: Better Estimate using x-Dependence

The previous bound used (n+x) ≥ n. But for x > 0, n+x can be larger than n.

```
∑_{n=1}^∞ (n+x)^{-2σ}
```

For fixed x > 0, this sum can be bounded more tightly.

For σ > 1:
```
∑_{n=1}^∞ (n+x)^{-2σ}
= ∑_{n=1}^∞ (n(1 + x/n))^{-2σ}
= ∑_{n=1}^∞ n^{-2σ} (1 + x/n)^{-2σ}
≤ ∑_{n=1}^∞ n^{-2σ}  (since (1 + x/n) ≥ 1)
```

This doesn't help—it gives the same bound.

But we can try a different bound. For σ > 1:

```
∑_{n=1}^∞ (n+x)^{-2σ}
= ∑_{n=1}^∞ ∫_{n}^{n+1} (n)^{-2σ} dn  (crudely)
```

This still doesn't help.

**Actually**, we can use the integral test:
```
∑_{n=1}^∞ (n+x)^{-2σ} = 1^{-2σ} + ∑_{n=2}^∞ (n+x)^{-2σ}
                        = 1 + ∑_{n=2}^∞ (n+x)^{-2σ}
```

For n ≥ 2 and x ≤ 1:
```
(n+x)^{-2σ} ≤ (n+1)^{-2σ}
```

So:
```
∑_{n=2}^∞ (n+x)^{-2σ} ≤ ∑_{n=2}^∞ (n+1)^{-2σ} = ∑_{m=3}^∞ m^{-2σ} = ζ(2σ) - 1 - 2^{-2σ}
```

This gives:
```
∑_{n=1}^∞ (n+x)^{-2σ} ≤ 1 + ζ(2σ) - 1 - 2^{-2σ} = ζ(2σ) - 2^{-2σ}
```

So: ||L_s|| ≤ ζ(2σ) - 2^{-2σ}

For σ = 1: ζ(2) - 2^{-2} = 1.64 - 0.25 = 1.39 > 1
For σ = 2: ζ(4) - 2^{-4} = 1.08 - 0.06 = 1.02 > 1
For σ = 3: ζ(6) - 2^{-6} = 1.01 - 0.02 = 0.99 < 1

**Result**: For Re(s) > 2.8 (approximately), ρ(L_s) < 1.

Still not reaching Re(s) > 1.

---

## Method 3: Smoothness of L_s

The previous bounds on the C∞ norm are crude because they don't account for the change of variables.

Consider the adjoint or a related operator.

**Alternative**: Use the L² norm with Gauss measure.

Let µ be the Gauss measure: dµ(x) = (1/ln 2) · (1+x)^{-1} dx.

Define the weighted L² space:
```
||f||²_μ = ∫_0^1 |f(x)|² dµ(x) = (1/ln 2) ∫_0^1 |f(x)|² / (1+x) dx
```

Now consider how L_s acts in this space.

Actually, this is getting complicated. Let me try a **direct computational approach**.

---

## Method 4: Numerical Bounds (for verification)

We can compute ||L_s|| numerically for specific s values on the real line.

For s real and s > 1:
```
||L_s|| ≈ ||L_s 1|| = ||f||∞ where f(x) = ∑ (n+x)^{-2s}
```

Compute f(x) for x ∈ [0,1] and find the sup:

For s = 1.5: f(x) = ∑ (n+x)^{-3}
- At x = 0: f(0) = ∑ n^{-3} = ζ(3) ≈ 1.20
- At x = 1: f(1) = ∑ (n+1)^{-3} = ζ(3) - 1 ≈ 0.20
- f is decreasing in x (since each term (n+x)^{-3} decreases)
- So sup is at x = 0: f(0) ≈ 1.20

For s = 2: f(x) = ∑ (n+x)^{-4}
- At x = 0: ζ(4) ≈ 1.08
- At x = 1: ζ(4) - 1 ≈ 0.08

For s = 3: f(x) = ∑ (n+x)^{-6}
- At x = 0: ζ(6) ≈ 1.01
- At x = 1: ζ(6) - 1 ≈ 0.01

**Observation**: For s → 1+, f(0) → ζ(2) ≈ 1.64

So the sup norm approach gives ||L_1|| = ζ(2) ≈ 1.64 > 1.

**Conclusion**: On C∞[0,1], the operator norm of L_1 is approximately 1.64 > 1.

**This means**: ρ(L_1) ≥ 1 (since spectral radius ≤ operator norm, ρ could still be < 1).

**But**: The eigenvector corresponding to ρ(L_1) is NOT the constant function 1.

We need to find the actual eigenvector with eigenvalue ρ(L_1).

---

## Method 5: Find Eigenfunction at s = 1

We want f such that L_1 f = λ f.

```
∑_{n=1}^∞ (n+x)^{-2} f(1/(n+x)) = λ f(x)
```

This is a functional equation. Let's try to find a solution.

Make substitution: Let y = 1/x, so x = 1/y.

Then the equation becomes complicated. Instead, try:

**Guess**: f(x) = x^α for some α.

```
L_1 f(x) = ∑ (n+x)^{-2} (1/(n+x))^α
        = ∑ (n+x)^{-2-α}
```

For this to equal λ x^α = λ (1/y)^α, we need:
```
∑ (n+x)^{-2-α} = λ x^α = λ (1/y)^α
```

This doesn't match unless α = 0, which gives f = 1, which we already know doesn't work.

---

## 🎯 CRITICAL REALIZATION

Finding λ₁(1) explicitly is **extremely difficult**.

The operator L_1:
```
(L_1 f)(x) = ∑ (n+x)^{-2} f(1/(n+x))
```

is what's called a **transfer operator with weighted Hölder weights**.

The standard theory (Baladi 2000, Theorem 3.1) says:

**For expanding maps and a Hölder potential φ**, the transfer operator:
```
ℒ_φ f = ∑ e^{φ|g_n|} f ◦ g_n
```

has a unique leading eigenvalue λ₁ and corresponding positive eigenfunction.

For our L_s, we can write:
```
L_s f = ∑ e^{-2s log(n+x)} f(1/(n+x))
```

The potential is φ_s(y) = -2s log(y), acting on the preimages.

**For s = 1**: φ₁(y) = -2 log(y)

**Question**: Is φ₁ Hölder continuous on (0,1]?

|φ₁(y₁) - φ₁(y₂)| = 2|log y₁ - log y₂|

This is **infinitely differentiable** on (0,1], but as y → 0+, |log(y)| → ∞.

So φ₁ is **not bounded**, and not Hölder near 0.

**This is the core problem**: The standard Perron-Frobenius and spectral gap theorems require either:
1. The potential to be bounded Hölder, OR
2. Additional weighted spaces

The documents claim to use weighted L² spaces (x^{-α} weights), but the application isn't fully justified in ASSIGNMENT_4_GLOBAL_BOUND.md.

---

## 🚀 Conclusion for This Document

**What I CAN prove**:
- ✅ ρ(L_s) < 1 for Re(s) > 3 (by crude norm bound)
- ⚠️ The spectral radius is likely < 1 for Re(s) > 1/2 (plausible but not rigorous)
- ⚠️ The assignments make claims that are consistent with literature

**What I CANNOT rigorously prove**:
- ❌ Exact value of λ₁(1)
- ❌ λ₁(1) = 1 specifically
- ❌ ρ(L_s) < 1 for all Re(s) > 1/2

**What next steps would look like**:
1. Articulate and work in the exact weighted Banach space
2. Verify all conditions of Baladi (2000) Theorem 3.1
3. Establish the exact position of λ₁(s) as a function of s
4. Use perturbation theory carefully, with proper justification

This requires **specialized knowledge** in complex dynamical systems and functional analysis that goes beyond what I can verify from first principles in this session.

---

*Status: Partial progress, foundation not complete*
