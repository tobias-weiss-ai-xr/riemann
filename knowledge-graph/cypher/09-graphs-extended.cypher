// ── Additional Graph Constructions ───────────────────────────────
// Graph types identified in research but not yet in the KG.

// ── P-ADIC CAYLEY GRAPHS ────────────────────────────────────────
CREATE (padic_cayley:Graph {
  name: "Cayley(SL(2, Q_p))",
  type: "cayley_graph",
  base_group: "SL(2, Q_p)",
  description: "Cayley graph of SL(2) over the p-adic numbers. Infinite but locally finite. Key object in the Langlands program — the LPS construction uses representations of SL(2, Q_p).",
  order: "infinite",
  degree: "variable",
  properties: "p-adic analogue of the real Cayley graph. Spectral theory connects to representation theory of GL(2, Q_p).",
  importance: "Deligne bound for modular forms and Ramanujan bound for expanders BOTH arise from the same GL(2, Q_p) representations"
})

CREATE (padic_cayley)-[:P_ADIC_ANALOGUE_OF]->(cayley_sl2z)
CREATE (padic_cayley)-[:USED_IN]->(lps_bridge)

// ── DEDEKIND ZETA GRAPH ─────────────────────────────────────────
CREATE (dedekind_graph:Graph {
  name: "Dedekind Zeta Graph",
  type: "arithmetic_graph",
  description: "Graph construction where vertices correspond to ideals in O_K and edges connect prime ideal factors. The Ihara zeta of such graphs relates to the Dedekind zeta ζ_K(s).",
  properties: "For K = Q, recovers the prime graph. For general K, encodes splitting behavior of primes.",
  research_gap: "No GNN work on ideal-theoretic graph constructions"
})

CREATE (dedekind_graph)-[:HAS_SPECTRUM]->(dedekind_zeta)

// ── PRIME MULTIPLICATION GRAPH ──────────────────────────────────
CREATE (prime_mult_graph:Graph {
  name: "Prime Multiplication Graph",
  type: "arithmetic_graph",
  description: "Vertices are positive integers ≤ N. Edge between n and m if n·m ≤ N. Encodes multiplicative structure of integers.",
  order: "N (for bound N)",
  degree: "variable (depends on N and vertex)",
  research_gap: "Artificial edges (product graph). No natural number-theoretic interpretation of spectral properties.",
  feasibility: "★★★ — easy to construct, but unclear what eigenvalues mean"
})

// ── ZERO SPACING GRAPH ──────────────────────────────────────────
CREATE (zero_spacing_graph:Graph {
  name: "Zeta Zero Spacing Graph",
  type: "time_series_graph",
  description: "Vertices represent zeta zeros γ_n. Edges connect consecutive zeros. Spacing distribution encodes GUE statistics from RMT.",
  properties: "Spacing ~ Tracy-Widom / GUE. Not really a 'graph problem' — more of a time-series / point process question.",
  research_gap: "GNN adds no value over classical time-series methods here",
  feasibility: "★★ — technically possible but wrong tool"
})

// ── SPECTRAL EXPANDER FAMILIES ──────────────────────────────────
CREATE (expander_lps_family:Graph {
  name: "LPS Expander Family {X^{p,q}}",
  type: "expander_family",
  description: "Infinite family of (p+1)-regular Ramanujan graphs X^{p,q} parameterized by primes p, q (both ≡ 1 mod 4). Order ~|PSL(2,F_q)| = q(q²-1)/2.",
  order: "q(q²-1)/2",
  degree: "p+1",
  is_ramanujan: true,
  properties: "Explicit construction of optimal expanders. For each p, infinite family parameterized by q → p-adic building.",
  key_paper: "LPS 1988"
})

CREATE (expander_lps_family)-[:IS_INSTANCE_OF]->(expander_general)

// ── CAYLEPY EXPERIMENTAL RESULTS ────────────────────────────────
CREATE (cayleypy_graphs:Graph {
  name: "CayleyPy Generated Graphs (SL(2,F_p))",
  type: "cayley_graph",
  base_group: "SL(2,F_p)",
  generators: "E₁₂, E₂₁, E₁₂⁻¹, E₂₁⁻¹ (4 fundamental root generators)",
  degree: 4,
  order: "p(p²-1)",
  is_ramanujan: false,
  properties: "NOT guaranteed Ramanujan (4 generators ≠ p+1 LPS generators). CayleyPy generates these for p=2..101+. No published GNN experiments on these graphs.",
  research_gap: "Zero published work of GNN trained on these Cayley graphs. Completely novel.",
  scalability: "p=101 → ~10⁶ nodes, ~1GB RAM. p=503 needs Lanczos eigenvalue computation only (too large for full GNN)."
})

CREATE (cayleypy_graphs)-[:GENERATED_BY]->(cayleypy)

// ── GRAPHON LIMITS ─────────────────────────────────────────────
CREATE (graphon_limit:Graph {
  name: "Cayley Graphon Limit",
  type: "graphon",
  description: "Graphon (graph function) limit of Cayley(SL(2,F_p)) as p → ∞. Encodes asymptotic spectral behavior of the expanding family.",
  properties: "Benjamini-Schramm limit exists for bounded-degree Cayley graphs. Spectral measure converges.",
  research_gap: "No GNN work on graphon approximations for number theory"
})

// ── DATA SOURCES ────────────────────────────────────────────────
CREATE (lmfdb:Paper {
  title: "The L-Functions and Modular Forms Database (LMFDB)",
  authors_str: "LMFDB Collaboration",
  year: 2024,
  publication_type: "database",
  url: "https://www.lmfdb.org",
  bibtex_key: "lmfdb",
  relevance_to_rh: "computational",
  description: "248K+ L-functions with computed data (zeros, coefficients, special values). Primary data source for ML number theory experiments (Bieri et al. 2025)."
})

CREATE (platt_database:Paper {
  title: "Computing the Riemann zeta zeros to 10¹³",
  authors_str: "D.J. Platt",
  year: 2017,
  publication_type: "journal",
  journal: "Mathematics of Computation",
  bibtex_key: "platt2017",
  relevance_to_rh: "computational",
  description: "Database of first 10¹³ zeta zeros with rigorous error bounds. Used for zero-spacing statistics and ML training data."
})

CREATE (platt)-[:AUTHORED {role: "author"}]->(platt_database)
CREATE (platt_database)-[:USES_METHOD]->(rmt_deep)
CREATE (lmfdb)-[:USES_METHOD]->(rmt_deep)

// ── CAYLEYPY DETAILS (API) ─────────────────────────────────────
CREATE (cayleypy_api:Theorem {
  name: "CayleyPy API — SL(2,F_p) Generation",
  statement: "CayleyPy provides MatrixGenerator(modulo=p) with special_linear_fundamental_roots(2, p) → 4 generators E₁₂, E₂₁ and inverses. BFS produces edges_list (numpy), adjacency_matrix_sparse(), all_states.",
  proof_status: "verified",  // via unit tests
  year_established: 2025,
  description: "Verified API: special_linear_fundamental_roots generates 4 generators from positive/negative root spaces. BfsResult provides edges_list, adjacency_matrix_sparse(), save/load. to_networkx_graph() materializes full graph (no truncation). Pre-computed data for p=2..10 in repo.",
  key_paper: "CayleyPy GitHub repository"
})
