// ── Mathematical Functions ───────────────────────────────────────
// ζ(s), L-functions, modular forms, Ihara zeta

// ── Zeta Functions ──────────────────────────────────────────────
CREATE (zeta:MathFunction {
  name: "ζ(s)",
  type: "zeta_function",
  full_name: "Riemann Zeta Function",
  definition: "ζ(s) = Σ 1/nˢ = Π (1 - p⁻ˢ)⁻¹",
  domain: "C \\ {1}",
  properties: "Analytic continuation to C, simple pole at s=1 with residue 1",
  functional_equation: "Λ(s) = π^{-s/2} Γ(s/2) ζ(s) = Λ(1-s)",
  zeros_trivial: "s = -2, -4, -6, ... (negative even integers)",
  zeros_nontrivial: "0 < Re(s) < 1 (critical strip), conjectured on Re(s) = 1/2",
  key_paper: "Riemann 1859",
  importance: "Encodes distribution of prime numbers via explicit formula"
})

CREATE (ihara_zeta:MathFunction {
  name: "ζ_G(u)",
  type: "zeta_function",
  full_name: "Ihara Zeta Function of Graph G",
  definition: "ζ_G(u) = (1 - u²)^{-(r-1)/2} det(I - Au + (d-1)u²I)^{-1}",
  domain: "Complex u (converges for |u| < (d-1)^{-1/2})",
  properties: "Analogue of Dedekind zeta for graphs. Poles encode cycle structure.",
  functional_equation: "Symmetric under u ↔ 1/((d-1)u)",
  rh_analogue: "IH-RH: all poles lie on |u| = 1/√(d-1) iff G is Ramanujan",
  importance: "Bridge between graph theory and number theory via Sunada's theorem"
})

CREATE (dedekind_zeta:MathFunction {
  name: "ζ_K(s)",
  type: "zeta_function",
  full_name: "Dedekind Zeta Function of number field K",
  definition: "ζ_K(s) = Σ N(I)^{-s} over ideals I of O_K",
  domain: "Re(s) > 1",
  properties: "Generalizes ζ(s) (ζ_Q(s) = ζ(s)). Has Euler product over prime ideals.",
  importance: "For K = Q(i), relates to distribution of Gaussian primes"
})

// ── L-Functions ─────────────────────────────────────────────────
CREATE (lf_general:MathFunction {
  name: "L(s, f)",
  type: "l_function",
  full_name: "L-function of automorphic form f",
  definition: "L(s, f) = Σ a_n n^{-s} = Π (1 - a_p p^{-s} + ε(p) p^{k-1-2s})^{-1}",
  domain: "Re(s) > (k+1)/2 (half-plane of convergence)",
  functional_equation: "Λ(s, f) = (2π)^{-s} Γ(s) L(s, f) = ε(f) (-1)^{k/2} Λ(k-s, f)",
  properties: "Euler product, functional equation, analytic continuation, Ramanujan-Petersson bound |a_p| ≤ 2p^{(k-1)/2}",
  importance: "Central objects in Langlands program. Generalize Dirichlet L-functions."
})

CREATE (lf_eisenstein:MathFunction {
  name: "L(s, E_k)",
  type: "l_function",
  full_name: "L-function of Eisenstein series E_k",
  description: "L-function coefficients from Eisenstein series: σ_{k-1}(n) = sum of d^{k-1} over d|n",
  properties: "L(s, E_k) = ζ(s) ζ(s-k+1) — DIRECT bridge to ζ(s)!",
  importance: "Eisenstein series provide the explicit connection between modular forms and ζ(s)"
})

CREATE (lf_cusp:MathFunction {
  name: "L(s, f) for cusp form f",
  type: "l_function",
  full_name: "L-function of cusp form (Hecke eigenform)",
  description: "L-function of a cuspidal Hecke eigenform of weight k, level N",
  properties: "Hecke eigenvalues a_p = λ_f(p) are multiplicative, satisfy |a_p| ≤ 2p^{(k-1)/2} (Deligne bound)",
  importance: "Non-trivial L-functions. Birch-Swinnerton-Dyer conjecture about L(1, f) for elliptic curves."
})

CREATE (dirichlet_l:MathFunction {
  name: "L(s, χ)",
  type: "l_function",
  full_name: "Dirichlet L-function",
  definition: "L(s, χ) = Σ χ(n) n^{-s}",
  domain: "Re(s) > 1 (analytic continuation to C except possible pole at s=1)",
  properties: "Generalized Riemann Hypothesis: all non-trivial zeros on Re(s) = 1/2",
  importance: "Used in Dirichlet's theorem on primes in arithmetic progressions"
})

// ── Modular Forms ───────────────────────────────────────────────
CREATE (eisenstein4:MathFunction {
  name: "E₄(z)",
  type: "modular_form",
  weight: 4,
  level: 1,
  description: "Eisenstein series of weight 4: E₄(z) = 1 + 240 Σ σ₃(n) q^n"
})

CREATE (eisenstein6:MathFunction {
  name: "E₆(z)",
  type: "modular_form",
  weight: 6,
  level: 1,
  description: "Eisenstein series of weight 6: E₆(z) = 1 - 504 Σ σ₅(n) q^n"
})

CREATE (delta:MathFunction {
  name: "Δ(z)",
  type: "modular_form",
  weight: 12,
  level: 1,
  description: "Ramanujan's cusp form: Δ(z) = q Π (1-q^n)²⁴ = Σ τ(n) q^n",
  properties: "τ(n) = Ramanujan tau function. First Fourier coefficient of discriminant modular form.",
  importance: "Generates the space of cusp forms S₁₂(Γ(1))"
})

// ── Relationships ───────────────────────────────────────────────
CREATE (lf_eisenstein)-[:FACTOR_OF]->(zeta)
CREATE (lf_eisenstein)-[:INSTANCE_OF]->(lf_general)
CREATE (lf_cusp)-[:INSTANCE_OF]->(lf_general)
CREATE (dirichlet_l)-[:INSTANCE_OF]->(lf_general)

CREATE (eisenstein4)-[:HAS_L_FUNCTION]->(lf_eisenstein)
CREATE (eisenstein6)-[:HAS_L_FUNCTION]->(lf_eisenstein)
CREATE (delta)-[:HAS_L_FUNCTION]->(lf_cusp)

CREATE (dedekind_zeta)-[:GENERALIZES]->(zeta)

CREATE (ihara_zeta)-[:ANALOGOUS_TO {
  description: "Ihara zeta ζ_G(u) is the graph-theoretic analogue of Dedekind zeta ζ_K(s). Poles ↔ closed geodesics ↔ prime ideals."
}]->(dedekind_zeta)
