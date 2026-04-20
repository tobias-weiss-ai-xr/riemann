// ── Key Papers ───────────────────────────────────────────────────
// Papers in the SL(2,Z) → ζ(s) → GNN theory chain

// ── FOUNDATIONAL ────────────────────────────────────────────────
CREATE (riemann1859:Paper {
  title: "Über die Anzahl der Primzahlen unter einer gegebenen Grösse",
  authors_str: "Bernhard Riemann",
  year: 1859,
  publication_type: "journal",
  journal: "Monatsberichte der Berliner Akademie",
  bibtex_key: "riemann1859",
  relevance_to_rh: "direct",
  description: "The original RH paper. 8 pages that changed mathematics."
})

CREATE (lps1988:Paper {
  title: "Ramanujan graphs",
  authors_str: "A. Lubotzky, R. Phillips, P. Sarnak",
  year: 1988,
  publication_type: "journal",
  journal: "Combinatorica",
  volume: "8",
  pages: "261-277",
  doi: "10.1007/BF02126799",
  bibtex_key: "lps1988",
  msclass: ["05C25", "11F06", "20C33"],
  relevance_to_rh: "analogous",
  description: "Constructs Ramanujan graphs as Cayley graphs of PSL(2,F_q). THE bridge paper."
})

CREATE (margulis1988:Paper {
  title: "Explicit group-theoretic constructions of combinatorial schemes and their applications in the construction of expanders and concentrators",
  authors_str: "G.A. Margulis",
  year: 1988,
  publication_type: "journal",
  journal: "Problems of Information Transmission",
  volume: "24",
  pages: "39-46",
  bibtex_key: "margulis1988",
  relevance_to_rh: "analogous",
  description: "Independent construction of Ramanujan graphs, contemporaneous with LPS"
})

CREATE (deligne1974:Paper {
  title: "La conjecture de Weil: II",
  authors_str: "Pierre Deligne",
  year: 1974,
  publication_type: "journal",
  journal: "Publications Mathématiques de l'IHÉS",
  volume: "52",
  pages: "137-252",
  doi: "10.1007/BF02687474",
  bibtex_key: "deligne1974",
  msclass: ["14G15", "11G25"],
  relevance_to_rh: "foundational",
  description: "Proof of Weil conjectures → Ramanujan-Petersson conjecture. Foundation for spectral bound."
})

// ── RECENT ──────────────────────────────────────────────────────
CREATE (pollicott2022:Paper {
  title: "A note on the Riemann hypothesis and the Farey sequence",
  authors_str: "Mark Pollicott",
  year: 2022,
  publication_type: "preprint",
  arxiv_id: "2209.03897",
  bibtex_key: "pollicott2022",
  msclass: ["11M26", "37C30", "05C25"],
  relevance_to_rh: "direct",
  description: "RH as spectral gap of transfer operator on Farey graph. Second bridge graphs→ζ(s)."
})

CREATE (williamson2021:Paper {
  title: "Deep learning for the combinatorial invariance conjecture",
  authors_str: "Alex Davies, Petar Veličković, Lars Buesing, Sam Blackwell, Zhengping Qiang, Carlos Pérez Muñoz, Peter Battaglia, Charles Blundell, András Juhász, Marc Lackenby, Geordie Williamson, Pushmeet Kohli",
  year: 2021,
  publication_type: "journal",
  journal: "Nature",
  volume: "612",
  pages: "56-60",
  doi: "10.1038/s41586-022-05415-0",
  bibtex_key: "williamson2021",
  msclass: ["05E10", "20C08", "68T07"],
  relevance_to_rh: "methodological",
  description: "First GNN (MPNN) on Bruhat intervals to solve a 40-year-old combinatorial conjecture. Proof of concept for GNN × representation theory."
})

CREATE (barlag2024:Paper {
  title: "Graph Neural Networks and Arithmetic Circuits",
  authors_str: "H. Barlag, L. R. B. Schmitt, M. Grohe",
  year: 2024,
  publication_type: "conference",
  journal: "NeurIPS 2024",
  bibtex_key: "barlag2024",
  msclass: ["68T07", "05C25", "68Q15"],
  relevance_to_rh: "methodological",
  description: "Exact correspondence: constant-depth GNNs ↔ constant-depth arithmetic circuits. Extended to recurrent GNNs in 2026."
})

CREATE (hayou2023:Paper {
  title: "A Neural Network Proof of the Riemann Hypothesis",
  authors_str: "S. Hayou",
  year: 2023,
  publication_type: "preprint",
  arxiv_id: "2309.09171",
  bibtex_key: "hayou2023",
  msclass: ["11M26", "68T07"],
  relevance_to_rh: "direct",
  description: "RH equivalent to density of single-layer neural nets in L²(0,1) via Nyman-Beurling criterion. Neural net angle on RH."
})

CREATE (bieri2025:Paper {
  title: "Machine learning the Riemann zeta function",
  authors_str: "Bieri, B. Brüderlin, J. Brüderlin, A. K. Haynes",
  year: 2025,
  publication_type: "preprint",
  bibtex_key: "bieri2025",
  msclass: ["11M26", "68T07"],
  relevance_to_rh: "computational",
  description: "ML predicts vanishing order of rational L-functions. 248K functions from LMFDB. Uses NNs/CNNs, no GNNs."
})

CREATE (loeffler2025:Paper {
  title: "Formalization of the Riemann zeta function in Lean 4",
  authors_str: "D. Loeffler, M. Stoll",
  year: 2025,
  publication_type: "preprint",
  bibtex_key: "loeffler2025",
  msclass: ["11M06", "03B35"],
  relevance_to_rh: "computational",
  description: "Formalized ζ(s), functional equation, analytic continuation, trivial zeros in Mathlib. RH stated as Prop. ~60-70% of needed machinery exists."
})

CREATE (rogers_tao2019:Paper {
  title: "The de Bruijn-Newman constant is non-negative",
  authors_str: "B. Rodgers, T. Tao",
  year: 2019,
  publication_type: "preprint",
  arxiv_id: "1901.03052",
  bibtex_key: "rogers_tao2019",
  relevance_to_rh: "direct",
  description: "Λ ≥ 0. Newman's conjecture: Λ = 0 iff RH. So RH ≤ Λ = 0. Gap closed to Λ = 0."
})

CREATE (platt_trudgian2021:Paper {
  title: "The Riemann hypothesis is true up to 3·10¹²",
  authors_str: "D. Platt, T. Trudgian",
  year: 2021,
  publication_type: "journal",
  journal: "Mathematics of Computation",
  bibtex_key: "platt_trudgian2021",
  relevance_to_rh: "computational",
  description: "Verified RH up to height 3×10¹². Uses rigorous interval arithmetic."
})

CREATE (codogni_lido:Paper {
  title: "Spectral theory of isogeny graphs",
  authors_str: "G. Codogni, C. Lido",
  year: 2025,
  publication_type: "preprint",
  bibtex_key: "codogni_lido",
  msclass: ["11G15", "05C25"],
  relevance_to_rh: "analogous",
  description: "Exact correspondence: isogeny graph eigenvalues = Frobenius eigenvalues. Ramanujan property proven. Pure math, no ML."
})

// ── CAYLEYPY ────────────────────────────────────────────────────
CREATE (cayleypy:Paper {
  title: "CayleyPy: A Python Library for Cayley Graph Generation",
  authors_str: "CayleyPy contributors",
  year: 2025,
  publication_type: "software",
  bibtex_key: "cayleypy",
  relevance_to_rh: "methodological",
  description: "Generates Cayley graphs of SL(2,F_p). NeurIPS 2025 Spotlight. ~200 conjectures on Cayley/Schreier graphs. No GNN component.",
  github_url: "https://github.com/alejandrox1/CayleyPy"
})

// ── Relationships ───────────────────────────────────────────────
CREATE (riemann1859)-[:PROPOSES]->(rh)
CREATE (lps1988)-[:INTRODUCES]->(cayley_lps)
CREATE (lps1988)-[:PROVES]->(lps_construction)
CREATE (deligne1974)-[:PROVES]->(deligne_bound)
CREATE (pollicott2022)-[:INTRODUCES]->(transfer_farey)
CREATE (williamson2021)-[:APPROACHES_VIA {strategy: "MPNN on Bruhat intervals", confidence: 1.0}]->(ramanujan_conj)
CREATE (hayou2023)-[:APPROACHES_VIA {strategy: "Neural net density via Nyman-Beurling", confidence: 0.3}]->(rh)
CREATE (loeffler2025)-[:APPROACHES_VIA {strategy: "Formal verification in Lean 4", confidence: 0.6}]->(rh)

CREATE (pollicott2022)-[:CITES]->(riemann1859)
CREATE (lps1988)-[:CITES]->(deligne1974)
CREATE (williamson2021)-[:CITES]->(lps1988)

// ── Researchers ─────────────────────────────────────────────────
CREATE (tao:Researcher {name: "Terence Tao", affiliation: "UCLA", research_areas: ["analytic number theory", "harmonic analysis", "PDE"]})
CREATE (sarnak:Researcher {name: "Peter Sarnak", affiliation: "IAS Princeton", research_areas: ["analytic number theory", "spectral theory", "Langlands program"]})
CREATE (lubotzky:Researcher {name: "Alexander Lubotzky", affiliation: "Hebrew University", research_areas: ["group theory", "expander graphs", "geometric group theory"]})
CREATE (williamson:Researcher {name: "Geordie Williamson", affiliation: "University of Sydney / IAS", research_areas: ["representation theory", "geometric representation theory", "categorification"]})
CREATE (keating:Researcher {name: "Jon Keating", affiliation: "University of Oxford", research_areas: ["random matrix theory", "number theory", "quantum chaos"]})
CREATE (platt:Researcher {name: "Dave Platt", affiliation: "University of Bristol", research_areas: ["analytic number theory", "computational number theory"]})
CREATE (loeffler:Researcher {name: "David Loeffler", affiliation: "University of Warwick", research_areas: ["number theory", "Lean formalization", "automorphic forms"]})

CREATE (tao)-[:AUTHORED {role: "coauthor"}]->(rogers_tao2019)
CREATE (sarnak)-[:AUTHORED {role: "coauthor", author_order: 3}]->(lps1988)
CREATE (lubotzky)-[:AUTHORED {role: "first_author", author_order: 1}]->(lps1988)
CREATE (williamson)-[:AUTHORED {role: "coauthor"}]->(williamson2021)
CREATE (platt)-[:AUTHORED {role: "coauthor"}]->(platt_trudgian2021)
CREATE (loeffler)-[:AUTHORED {role: "coauthor"}]->(loeffler2025)

// ── AI Approaches ───────────────────────────────────────────────
CREATE (gnn_spectral:AIApproach {
  name: "GNN Spectral Prediction",
  approach_type: "gnn",
  method: "GCN/GAT on Cayley graphs of SL(2,F_p) to predict eigenvalue distribution",
  target: "Predict Hecke eigenvalue distribution from graph structure alone",
  framework: "PyTorch Geometric + CayleyPy",
  status: "planned",
  confidence: 0.4,
  description: "Train GNN on Cayley graphs → predict spectral properties → compare with Ramanujan bound. First GNN on group Cayley graphs.",
  feasibility_notes: "Novel (zero published work), CayleyPy provides graphs, LPS theory gives ground truth"
})

CREATE (formal_lean:AIApproach {
  name: "Lean 4 Formal Verification",
  approach_type: "formal_verification",
  method: "Formalize RH proof machinery in Mathlib (Lean 4) with AI-assisted proof search",
  target: "Complete formalization of sufficient machinery to state and potentially prove RH",
  framework: "Lean 4 + Mathlib + AlphaProof/TTRL",
  status: "in_progress",
  confidence: 0.6,
  description: "Loeffler & Stoll (2025): ~60-70% of needed machinery in Mathlib. Tao demonstrated Claude Code + Lean. Long-term path: AI as proof assistant.",
  feasibility_notes: "PNT+ completed via Wiener-Ikehara. Missing: Hadamard factorization, zero-free region, explicit formula, residue theorem (general)."
})

CREATE (funsearch_rh:AIApproach {
  name: "FunSearch for Number Theory",
  approach_type: "funsearch",
  method: "LLM-driven evolutionary search for new number-theoretic conjectures/algorithms",
  target: "Discover new patterns in zero distributions or prime-related functions",
  framework: "FunSearch (DeepMind)",
  status: "inconclusive",
  confidence: 0.2,
  description: "FunSearch (2023) solved Cap Set problem (496→512). FunSearch paper explicitly states 'zero reason' it would help with P-vs-NP. Similarly limited for RH."
})

CREATE (rmt_deep:AIApproach {
  name: "RMT + Deep Learning",
  approach_type: "numerical",
  method: "Use deep learning to discover patterns in random matrix statistics of zeta zeros",
  target: "Accelerate zero verification or find statistical anomalies",
  framework: "PyTorch + mpmath",
  status: "exploratory",
  confidence: 0.25,
  description: "Keating works on both RMT for zeta moments AND RMT for deep learning loss landscapes. Potential cross-pollination."
})

// Approach relationships
CREATE (gnn_spectral)-[:TARGETS]->(ihrh)
CREATE (gnn_spectral)-[:USES_OBJECT {role: "training_data"}]->(cayley_sl2fp)
CREATE (gnn_spectral)-[:USES_OBJECT {role: "hypothesis_space"}]->(adjacency)
CREATE (gnn_spectral)-[:BASED_ON_THEOREM]->(lps_bridge)
CREATE (gnn_spectral)-[:BASED_ON_THEOREM]->(deligne_bound)

CREATE (formal_lean)-[:TARGETS]->(rh)
CREATE (funsearch_rh)-[:TARGETS]->(rh)
CREATE (rmt_deep)-[:TARGETS]->(zeta)

CREATE (williamson2021)-[:USES_METHOD]->(gnn_spectral)
CREATE (hayou2023)-[:USES_METHOD]->(gnn_spectral)
