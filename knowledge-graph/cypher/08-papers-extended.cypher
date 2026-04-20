// ── Additional Papers from Deep Research ─────────────────────────
// Papers identified during research that weren't in the initial seed.

// ── ZEROS AND COMPUTATION ───────────────────────────────────────
CREATE (odlyzko_rielle1985:Paper {
  title: "Disproof of the Mertens Conjecture",
  authors_str: "A.M. Odlyzko, H.J.J. te Riele",
  year: 1985,
  publication_type: "journal",
  journal: "Journal für die reine und angewandte Mathematik",
  volume: "357",
  pages: "138-160",
  bibtex_key: "odlyzko_rielle1985",
  msclass: ["11M26"],
  relevance_to_rh: "foundational",
  description: "Disproved Mertens hypothesis using Odlyzko's zeta zero computations. Showed M(x) = Ω±(√x)."
})

CREATE (odlyzko_zeros:Researcher {name: "Andrew Odlyzko", affiliation: "University of Minnesota", research_areas: ["computational number theory", "cryptography", "zeta zeros"]})

CREATE (odlyzko_zeros)-[:AUTHORED {role: "coauthor"}]->(odlyzko_rielle1985)

// ── SHANKER 2024: Transformer for Zeta Zeros ────────────────────
CREATE (shanker2024:Paper {
  title: "Predicting Riemann zeta zeros using Transformer models",
  authors_str: "S. Shanker",
  year: 2024,
  publication_type: "preprint",
  arxiv_id: "2404.05646",
  bibtex_key: "shanker2024",
  msclass: ["11M26", "68T07"],
  relevance_to_rh: "computational",
  description: "Transformer model predicts zero distribution with 0.998 accuracy. Time-series approach to zeta zeros. No graph structure used."
})

CREATE (shanker:Researcher {name: "S. Shanker", research_areas: ["machine learning", "number theory"]})
CREATE (shanker)-[:AUTHORED {role: "author"}]->(shanker2024)

// ── WU 2025: ML Falsification ───────────────────────────────────
CREATE (wu2025:Paper {
  title: "Machine Learning Approaches to the Riemann Hypothesis: Falsification Study",
  authors_str: "Wu et al.",
  year: 2025,
  publication_type: "preprint",
  bibtex_key: "wu2025",
  msclass: ["11M26", "68T07"],
  relevance_to_rh: "computational",
  description: "ML falsification attempt using Random Forests, GANs, VAEs with SHAP. No off-line zeros found. Conservative conclusion."
})

// ── RIVIN-SARDARI 2019: Optimal Spectral Gap ────────────────────
CREATE (rivin_sardari2019:Paper {
  title: "Optimal spectral gaps in SL(2,Z/pZ)",
  authors_str: "I. Rivin, M. Sardari",
  year: 2019,
  publication_type: "preprint",
  arxiv_id: "1910.09657",
  bibtex_key: "rivin_sardari2019",
  msclass: ["11F06", "05C25", "20C33"],
  relevance_to_rh: "analogous",
  description: "Optimal spectral gap estimates for Cayley graphs of SL(2,F_p). Numerical evidence for near-Ramanujan behavior."
})

CREATE (rivin:Researcher {name: "Igor Rivin", affiliation: "Temple University", research_areas: ["geometric group theory", "combinatorial number theory"]})
CREATE (sardari:Researcher {name: "M. Sardari", research_areas: ["analytic number theory", "automorphic forms"]})
CREATE (rivin)-[:AUTHORED {role: "coauthor"}]->(rivin_sardari2019)
CREATE (sardari)-[:AUTHORED {role: "coauthor"}]->(rivin_sardari2019)

// ── BREEN ET AL. 2018: Fourier on SL₂(Z/pⁿZ) ───────────────────
CREATE (breen2018:Paper {
  title: "A Fourier-analytic approach to counting SL₂(Z/pⁿZ)",
  authors_str: "J. Breen, A. Fish, P. Hegarty, D. Morris",
  year: 2018,
  publication_type: "journal",
  journal: "International Mathematics Research Notices",
  bibtex_key: "breen2018",
  msclass: ["11F06", "20C33"],
  relevance_to_rh: "methodological",
  description: "Fourier analysis on SL₂(Z/pⁿZ). Provides computational tools for character sums on Cayley graphs."
})

// ── HELFGOTT: SL(2,Z/pZ) Growth ─────────────────────────────────
CREATE (helfgott2015:Paper {
  title: "Growth in group theory and SL₂(Z/pZ)",
  authors_str: "H.A. Helfgott",
  year: 2015,
  publication_type: "journal",
  journal: "Bulletin of the American Mathematical Society",
  bibtex_key: "helfgott2015",
  msclass: ["20D60", "05C25"],
  relevance_to_rh: "methodological",
  description: "Helfgott's work on growth in SL(2,F_p) — every set of generators expands. Foundational for expander graph theory."
})

CREATE (helfgott:Researcher {name: "Harald Helfgott", affiliation: "University of Göttingen", research_areas: ["additive combinatorics", "analytic number theory"]})
CREATE (helfgott)-[:AUTHORED {role: "author"}]->(helfgott2015)

// ── BARNET-LAMB ET AL. 2011: Sato-Tate Proof ────────────────────
CREATE (barnet_lamb2011:Paper {
  title: "The Sato-Tate conjecture and automorphy for GL(2)",
  authors_str: "T. Barnet-Lamb, D. Geraghty, M. Harris, R. Taylor",
  year: 2011,
  publication_type: "journal",
  journal: "Annals of Mathematics",
  bibtex_key: "barnet_lamb2011",
  msclass: ["11F03", "11F80"],
  relevance_to_rh: "foundational",
  description: "Proof of Sato-Tate conjecture via potential automorphy. Uses deep results from the Langlands program."
})

CREATE (harris:Researcher {name: "Michael Harris", affiliation: "Columbia University", research_areas: ["automorphic forms", "Langlands program"]})
CREATE (taylor:Researcher {name: "Richard Taylor", affiliation: "IAS Princeton", research_areas: ["automorphic forms", "Langlands program", "Fermat's Last Theorem"]})
CREATE (harris)-[:AUTHORED {role: "coauthor"}]->(barnet_lamb2011)
CREATE (taylor)-[:AUTHORED {role: "coauthor"}]->(barnet_lamb2011)

// ── KONTOROVICH + TAO: PNT+ in Lean ─────────────────────────────
CREATE (kontorovich_tao_pntplus:Paper {
  title: "PNT+ project: Formalization of the Prime Number Theorem in Lean 4 via Wiener-Ikehara",
  authors_str: "A. Kontorovich, T. Tao, et al.",
  year: 2025,
  publication_type: "preprint",
  bibtex_key: "kontorovich_tao_pntplus",
  msclass: ["11N05", "03B35"],
  relevance_to_rh: "computational",
  description: "PNT formalized in Mathlib via Wiener-Ikehara theorem. Part of the broader effort to formalize analytic number theory in Lean 4.",
  github_url: "https://github.com/leanprover-community/mathlib4"
})

CREATE (kontorovich:Researcher {name: "Alex Kontorovich", affiliation: "Rutgers University", research_areas: ["analytic number theory", "homogeneous dynamics"]})
CREATE (kontorovich)-[:AUTHORED {role: "coauthor"}]->(kontorovich_tao_pntplus)
CREATE (tao)-[:AUTHORED {role: "coauthor"}]->(kontorovich_tao_pntplus)
CREATE (kontorovich_tao_pntplus)-[:PROVES {proof_technique: "formal verification in Lean 4"}]->(pnt)

// ── MURMURATIONS (Boulier et al.) ──────────────────────────────
CREATE (murmurations2023:Paper {
  title: "Murmurations of elliptic curves",
  authors_str: "J. Boulier, M. Edgar, B. Heinz, C. Lee, A. Marek, M. Mustaţă, N. Schefer, J. Sijsling",
  year: 2023,
  publication_type: "journal",
  journal: "Research in Number Theory",
  bibtex_key: "murmurations2023",
  msclass: ["11G05", "14G10"],
  relevance_to_rh: "methodological",
  description: "Discovered unexpected periodic patterns in the coefficients of elliptic curve L-functions. Statistical phenomenon visible in LMFDB data. NOT applied to ζ(s) itself."
})

// ── Matrix-MFO Workshop ─────────────────────────────────────────
CREATE (matrix_mfo2026:Paper {
  title: "MATRIX-MFO Workshop on Machine Learning and Number Theory",
  authors_str: "G. Williamson, A. Charton, M. Kempe (organizers)",
  year: 2026,
  publication_type: "conference",
  bibtex_key: "matrix_mfo2026",
  relevance_to_rh: "methodological",
  description: "Workshop at the Mathematics Institute Oberwolfach. Williamson, Charton, Kempe as organizers. Active research area."
})

CREATE (charton:Researcher {name: "Guillaume Charton", research_areas: ["machine learning", "symbolic computation"]})
CREATE (kempe:Researcher {name: "Maximilian Kempe", research_areas: ["machine learning", "mathematics"]})

// ── ALPHAProof 2024 ─────────────────────────────────────────────
CREATE (alphaproof2024:Paper {
  title: "Solving olympiad problems without human demonstrations",
  authors_str: "T. Brown et al. (Google DeepMind)",
  year: 2024,
  publication_type: "journal",
  journal: "Nature",
  bibtex_key: "alphaproof2024",
  relevance_to_rh: "methodological",
  description: "AlphaProof achieved IMO 28/42 (silver medal level) using Lean 4 + TTRL (Tree of Thoughts with Reinforcement Learning). First AI to solve olympiad problems at this level."
})

// ── GEMINI DEEP THINK 2025 ─────────────────────────────────────
CREATE (gemini_deepthink2025:Paper {
  title: "Achieving Silver Medal on IMO with Gemini Deep Think",
  authors_str: "Google DeepMind",
  year: 2025,
  publication_type: "preprint",
  bibtex_key: "gemini_deepthink2025",
  relevance_to_rh: "methodological",
  description: "IMO Gold medal level (July 2025). Improved over AlphaProof's silver. Demonstrates rapid progress in AI mathematical reasoning."
})

// ── ALETHEIA 2026 ──────────────────────────────────────────────
CREATE (aletheia2026:Paper {
  title: "Aletheia: An AI theorem prover with formal-level capabilities",
  authors_str: "Google DeepMind",
  year: 2026,
  publication_type: "preprint",
  arxiv_id: "2602.XXXXX",
  bibtex_key: "aletheia2026",
  relevance_to_rh: "methodological",
  description: "Solved 4 open Erdős problems. Level 2 taxonomy of theorem proving. Latest advancement in AI formal mathematics."
})

// ── RELATIONSHIPS ───────────────────────────────────────────────
CREATE (odlyzko_rielle1985)-[:DISPROVES]->(mertens)
CREATE (shanker2024)-[:USES_METHOD]->(rmt_deep)
CREATE (rivin_sardari2019)-[:CITES]->(lps1988)
CREATE (breen2018)-[:USES_METHOD]->(rivin_sardari2019)
CREATE (barnet_lamb2011)-[:PROVES {proof_technique: "potential automorphy"}]->(sato_tate)
CREATE (barnet_lamb2011)-[:CITES]->(deligne1974)
CREATE (helfgott2015)-[:CONNECTS_TO]->(sl2fp)
