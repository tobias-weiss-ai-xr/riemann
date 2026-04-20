// ── Operators in the Theory Chain ───────────────────────────────
// Hecke, Transfer, Adjacency, Frobenius, Laplacian

// ── Hecke Operators ─────────────────────────────────────────────
CREATE (hecke_tp:Operator {
  name: "Hecke T_p",
  symbol: "T_p",
  operator_type: "hecke",
  acts_on: "Space of modular forms M_k(Γ₀(N))",
  definition: "(T_p f)(z) = p^{k/2-1} Σ_{ad=p, 0≤b<d} d^{-k} f((az+b)/d)",
  hermitian: true,
  commuting: true,
  multiplicative: true,
  eigenvalue_name: "Hecke eigenvalue λ_f(p)",
  properties: "Double coset decomposition: Γ₀(N) diag(1,p) Γ₀(N) = ⊔ Γ₀(N)(a b; 0 d)",
  importance: "Hecke eigenvalues a_p are the central bridge between modular forms and L-functions",
  key_paper: "Hecke 1937"
})

CREATE (hecke_tn:Operator {
  name: "Hecke T_n",
  symbol: "T_n",
  operator_type: "hecke",
  acts_on: "Space of modular forms M_k(Γ₀(N))",
  hermitian: true,
  commuting: true,
  multiplicative: true,
  properties: "T_m T_n = T_{mn} for (m,n)=1, T_p T_{p^r} = T_{p^{r+1}} + p^{k-1} T_{p^{r-1}} (recursion)"
})

// ── Adjacency Operator ──────────────────────────────────────────
CREATE (adjacency:Operator {
  name: "Adjacency Matrix A",
  symbol: "A",
  operator_type: "adjacency",
  acts_on: "L²(V) for vertex set V of graph G",
  definition: "(Af)(v) = Σ_{u~v} f(u)",
  hermitian: true,
  properties: "Eigenvalues λ₁ ≥ λ₂ ≥ ... ≥ λ_n. Spectral gap = λ₁ - |λ₂|. Ramanujan iff |λ| ≤ 2√(d-1).",
  importance: "THE operator for graph spectral theory. Connected to Hecke via LPS construction."
})

CREATE (hashimoto:Operator {
  name: "Hashimoto Edge Matrix H",
  symbol: "H",
  operator_type: "adjacency",
  acts_on: "Space of directed edges",
  definition: "H_{e,e'} = 1 if terminal vertex of e = initial vertex of e' and e' ≠ ē",
  properties: "ζ_G(u)^{-1} = det(I - Hu). Related to adjacency by Bass's formula.",
  importance: "Encodes the Ihara zeta function. Used in Sunada's theorem."
})

// ── Transfer Operator (Farey graph) ─────────────────────────────
CREATE (transfer_farey:Operator {
  name: "Farey Transfer Operator L_s",
  symbol: "L_s",
  operator_type: "transfer",
  acts_on: "C(Γ₁) — functions on the Farey graph boundary",
  definition: "Perron-Frobenius operator for the Gauss map / Farey flow",
  properties: "Pollicott 2022: Z_{Γ₁}(s) = det(1 - L_{2s}). RH equivalent to spectral gap of L_s.",
  importance: "DIRECT encoding of RH as spectral gap of an operator on a graph."
})

// ── Frobenius Operator ──────────────────────────────────────────
CREATE (frobenius:Operator {
  name: "Frobenius Endomorphism",
  symbol: "Frob_p",
  operator_type: "frobenius",
  acts_on: "ℓ-adic cohomology of elliptic curves / varieties",
  definition: "Geometric Frobenius: (x,y) ↦ (x^p, y^p) on elliptic curve over F̄_p",
  properties: "Trace of Frobenius a_p = p+1 - #E(F_p). Eigenvalues of Frobenius on H¹ are the key to Sato-Tate.",
  importance: "Connects arithmetic of elliptic curves to spectral properties of isogeny graphs."
})

// ── Laplacian ───────────────────────────────────────────────────
CREATE (laplacian:Operator {
  name: "Graph Laplacian Δ",
  symbol: "Δ = dI - A",
  operator_type: "laplacian",
  acts_on: "L²(V)",
  properties: "Δ = dI - A for d-regular graph. Eigenvalues 0 = μ₁ ≤ μ₂ ≤ ... ≤ μ_n ≤ 2d. Spectral gap = μ₂.",
  importance: "Alternative spectral characterization. Connected to random walks and expansion."
})

// ── Relationships ───────────────────────────────────────────────
// Adjacency ≈ Hecke via LPS bridge
CREATE (adjacency)-[:CORRESPONDS_TO {
  description: "LPS 1988: On L²(Γ\G/K), the adjacency operator of the Cayley graph approximates the Hecke operator",
  via: "L²(Γ\\G/K) — the space of K-invariant L² functions on Γ\\G where G=SL(2,R), K=SO(2)",
  precision: "Approximate — exact for isogeny graphs, approximate for LPS expanders",
  key_paper: "LPS 1988, Lubotzky-Phillips-Sarnak"
}]->(hecke_tp)

CREATE (hashimoto)-[:COMPUTES_VIA]->(ihara_zeta)

CREATE (transfer_farey)-[:ENCODES {
  description: "Pollicott 2022: The transfer operator L_s on the Farey graph has det(1 - L_{2s}) = Z_{Γ₁}(s)",
  rh_connection: "RH is equivalent to the spectral gap of L_s"
}]->(zeta)

CREATE (frobenius)-[:CORRESPONDS_TO {
  description: "On isogeny graphs: eigenvalues of Frobenius on H¹(E) = eigenvalues of adjacency matrix of isogeny graph",
  via: "Eichler trace formula / Deligne's proof of Ramanujan conjecture"
}]->(adjacency)

CREATE (laplacian)-[:DERIVED_FROM]->(adjacency)

CREATE (hecke_tp)-[:INSTANCE_OF]->(hecke_tn)

CREATE (hecke_tp)-[:ACTS_ON]->(delta)
CREATE (hecke_tp)-[:ACTS_ON]->(eisenstein4)
CREATE (hecke_tp)-[:ACTS_ON]->(eisenstein6)
