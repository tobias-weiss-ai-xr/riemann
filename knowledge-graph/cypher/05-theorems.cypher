// ── Theorems and Conjectures ────────────────────────────────────
// Proven results, open conjectures, and their relationships

// ── THE RH FAMILY (equivalence class) ───────────────────────────
CREATE (rh:Theorem:Conjecture:OpenProblem {
  name: "Riemann Hypothesis",
  statement: "All non-trivial zeros of ζ(s) have real part 1/2",
  latex_statement: "\\forall s \\in \\mathbb{C}: \\zeta(s) = 0 \\land s \\notin \\{-2,-4,-6,\\ldots\\} \\implies \\text{Re}(s) = \\frac{1}{2}",
  proof_status: "conjectured",
  year_stated: 1859,
  significance: "foundational",
  lean_status: "partial",
  mathlib_name: "riemann_hypothesis",
  lean4: true,
  description: "One of the Clay Millennium Problems. Equivalent to >100 known formulations."
})

CREATE (grh:Theorem:Conjecture:OpenProblem {
  name: "Generalized Riemann Hypothesis",
  statement: "All non-trivial zeros of Dirichlet L-functions L(s,χ) have real part 1/2",
  proof_status: "conjectured",
  year_stated: 1884,
  significance: "foundational",
  description: "Extends RH to all Dirichlet L-functions"
})

CREATE (liouville:Theorem:Conjecture {
  name: "Lindelöf Hypothesis",
  statement: "ζ(1/2 + it) = O(t^ε) for all ε > 0",
  proof_status: "conjectured",
  year_stated: 1908,
  description: "Weaker than RH but still unproven. Equivalent to bounds on moments of ζ(s)."
})

CREATE (robin:Theorem:Conjecture {
  name: "Robin's Inequality",
  statement: "σ(n) < e^γ n log log n for all n ≥ 5041 iff RH holds",
  proof_status: "conjectured",
  year_stated: 1984,
  description: "RH equivalent to Robin's inequality holding for all n ≥ 5041"
})

CREATE (lagarias:Theorem:Conjecture {
  name: "Lagarias Inequality",
  statement: "σ(n) ≤ H_n + exp(H_n) log(H_n) for all n ≥ 1, with equality only for n=1",
  proof_status: "conjectured",
  year_stated: 2002,
  description: "An equivalent formulation of RH using harmonic numbers"
})

// RH equivalences (bidirectional)
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Standard reduction"}]->(liouville)
CREATE (liouville)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Standard reduction"}]->(rh)
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Robin (1984)"}]->(robin)
CREATE (robin)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Robin (1984)"}]->(rh)
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Lagarias (2002)"}]->(lagarias)
CREATE (lagarias)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Lagarias (2002)"}]->(rh)
CREATE (rh)-[:STRENGTHENS {description: "GRH implies RH (restricts to principal character)"}]->(rh)

// ── RAMANUJAN / DELIGNE ─────────────────────────────────────────
CREATE (ramanujan_conj:Theorem:Conjecture {
  name: "Ramanujan Conjecture (original)",
  statement: "|τ(p)| ≤ 2p^{11/2} for all primes p",
  proof_status: "proven",
  year_stated: 1916,
  year_established: 1974,
  significance: "major",
  description: "Ramanujan's conjecture on the tau function, proven by Deligne as consequence of Weil conjectures"
})

CREATE (ramanujan_petersson:Theorem {
  name: "Ramanujan-Petersson Conjecture",
  statement: "For normalized Hecke eigenform f of weight k: |a_p(f)| ≤ 2p^{(k-1)/2}",
  proof_status: "proven",
  year_stated: 1930,
  year_established: 1974,
  significance: "major",
  description: "Generalization to all cusp forms. Proven by Deligne for holomorphic forms via étale cohomology."
})

CREATE (deligne_bound:Theorem {
  name: "Deligne Bound",
  statement: "Hecke eigenvalues of cusp forms satisfy |a_p| ≤ 2p^{(k-1)/2}",
  proof_status: "proven",
  year_established: 1974,
  significance: "foundational",
  proof_technique: "Étale cohomology, proof of Weil conjectures",
  description: "THE fundamental bound connecting modular forms and graph spectral theory. For k=2: |a_p| ≤ 2√p = Ramanujan bound |λ| ≤ 2√(d-1)"
})

CREATE (deligne_bound)-[:PROVES {proof_technique: "algebraic geometry, étale cohomology"}]->(ramanujan_petersson)
CREATE (ramanujan_petersson)-[:GENERALIZES]->(ramanujan_conj)

// ── RAMANUJAN GRAPHS (IH-RH analogue) ───────────────────────────
CREATE (ihrh:Theorem:Conjecture {
  name: "IH-RH (Ihara Riemann Hypothesis)",
  statement: "A d-regular graph is Ramanujan iff all non-trivial eigenvalues λ satisfy |λ| ≤ 2√(d-1)",
  proof_status: "proven",
  year_established: 1985,
  significance: "major",
  description: "Proven independently by Alon-Boppana (lower bound) and Lubotzky-Phillips-Sarnak (achievable). NOT an analogue in the sense of being unproven — it's a theorem about graphs.",
  note: "The RH-analogue status comes from the STRUCTURAL parallel: eigenvalue bound ↔ zero location bound"
})

CREATE (alon_boppana:Theorem {
  name: "Alon-Boppana Bound",
  statement: "For any infinite family of d-regular graphs: lim inf |λ₂(G_n)| ≥ 2√(d-1)",
  proof_status: "proven",
  year_established: 1986,
  description: "Ramanujan graphs ACHIEVE the Alon-Boppana bound — they are optimal expanders"
})

CREATE (lps_construction:Theorem {
  name: "LPS Ramanujan Graph Construction",
  statement: "For every prime p ≡ 1 (mod 4), there exist p+1-regular Ramanujan graphs on SL(2,F_q)",
  proof_status: "proven",
  year_established: 1988,
  significance: "foundational",
  description: "Constructs Ramanujan graphs as Cayley graphs of PSL(2,F_q) with p+1 generators. Uses deep results from representation theory of SL(2).",
  key_paper: "LPS 1988 Combinatorica"
})

CREATE (ihrh)-[:ANALOGOUS_TO {
  description: "Structural parallel: Ramanujan bound |λ| ≤ 2√(d-1) ↔ RH critical line Re(s)=1/2. Both are optimal eigenvalue/zero location statements.",
  shared_representation: "Both follow from representation theory of GL(2) over p-adic fields (Deligne for modular forms, same machinery for LPS)"
}]->(rh)

CREATE (alon_boppana)-[:LOWER_BOUND_FOR]->(ihrh)
CREATE (lps_construction)-[:ACHIEVES]->(ihrh)

// ── SATO-TATE ───────────────────────────────────────────────────
CREATE (sato_tate:Theorem {
  name: "Sato-Tate Conjecture",
  statement: "For non-CM elliptic curve E/Q, the normalized Frobenius traces a_p/√p are equidistributed in [-1,1] with respect to (1/π)√(1-x²)dx",
  proof_status: "proven",
  year_stated: 1960,
  year_established: 2011,
  significance: "major",
  proof_technique: "Potential automorphy",
  description: "Proved by Barnet-Lamb, Geraghty, Harris, Taylor (2011). Connects distribution of eigenvalues to the Sato-Tate measure."
})

// ── LPS BRIDGE THEOREM ─────────────────────────────────────────
CREATE (lps_bridge:Theorem {
  name: "LPS Spectral Bridge",
  statement: "The adjacency operator of the LPS Cayley graph of PSL(2,F_p) acts on L²(Γ\\G/K) as an approximation to the Hecke operator",
  proof_status: "proven",
  year_established: 1988,
  significance: "foundational",
  description: "THE bridge between graph spectral theory and number theory. For k=2 cusp forms, Deligne bound |a_p| ≤ 2√p = Ramanujan bound |λ| ≤ 2√(d-1) because both arise from the same GL(2,ℚ_p) representations."
})

CREATE (lps_bridge)-[:BRIDGE {
  description: "Connects adjacency eigenvalues of Cayley graphs to Hecke eigenvalues of modular forms",
  from_domain: "Graph theory (spectral graph theory)",
  to_domain: "Number theory (modular forms, L-functions)"
}]->(deligne_bound)

// ── POLLICOTT 2022 ──────────────────────────────────────────────
CREATE (pollicott:Theorem {
  name: "Pollicott Farey Graph Theorem",
  statement: "RH is equivalent to the spectral gap of the transfer operator on the Farey graph: Z_{Γ₁}(s) = det(1 - L_{2s})",
  proof_status: "proven",
  year_established: 2022,
  significance: "major",
  description: "Encodes RH as a graph spectral property. The Farey graph provides a SECOND bridge from graphs to ζ(s), independent of LPS."
})

CREATE (pollicott)-[:PROVES {
  proof_technique: "dynamical systems, transfer operators, thermodynamic formalism"
}]->(rh)

// ── SUNADA'S THEOREM ────────────────────────────────────────────
CREATE (sunada:Theorem {
  name: "Sunada's Theorem",
  statement: "Two Riemannian manifolds are isospectral if their fundamental groups have nearly conjugate representations",
  proof_status: "proven",
  year_established: 1985,
  description: "Extended to graphs: Sunada isospectrality. Used to construct isospectral non-isomorphic graphs."
})

// ── RANKIN-SELBERG ──────────────────────────────────────────────
CREATE (rankin_selberg:Theorem {
  name: "Rankin-Selberg Method",
  statement: "L(s, f × g) = ζ(2s) Σ a_n(f) a_n(g) n^{-s} — convolution L-function",
  proof_status: "proven",
  year_established: 1939,
  description: "Method for studying L-functions via integration against Eisenstein series. Used to relate Eisenstein L-functions to ζ(s)."
})

// ── RELATIONSHIPS ───────────────────────────────────────────────
CREATE (sato_tate)-[:USES]->(frobenius)
CREATE (lps_construction)-[:USES]->(sl2fp)
CREATE (pollicott)-[:USES]->(farey)
CREATE (rankin_selberg)-[:CONNECTS]->(lf_eisenstein)
CREATE (rankin_selberg)-[:CONNECTS]->(zeta)

// ── LEAN FORMALIZATION ──────────────────────────────────────────
CREATE (pnt:Theorem {
  name: "Prime Number Theorem",
  statement: "π(x) ~ x/log(x)",
  proof_status: "proven",
  year_established: 1896,
  lean_status: "formalized",
  lean4: true,
  description: "Formalized in Mathlib via Wiener-Ikehara theorem. PNT+ project by Kontorovich and Tao."
})

CREATE (pnt)-[:IMPLIES {description: "PNT follows from non-vanishing of ζ(s) on Re(s)=1, which is weaker than RH"}]->(rh)
