// ── RH Extended Equivalences (from librarian research) ────────────
// Formulations identified via Broughan (2017), Borwein et al. (2008), Conrey (2003)
// ~150-200 total known; this script adds the major ones not in 07-rh-equivalences.cypher
// Run AFTER 07-rh-equivalences.cypher (needs rh node)

// ── ANALYTIC ────────────────────────────────────────────────────

// von Koch Error Term
CREATE (von_koch:Theorem {
  name: "von Koch Error Term",
  statement: "π(x) = Li(x) + O(x^{1/2} log x)",
  proof_status: "proven",
  year_established: 1901,
  significance: "major",
  description: "RH equivalent to the classical prime counting error bound. The tightest possible bound from RH.",
  key_paper: "von Koch (1901) Acta Math. 24, 159-182",
  domain: "analytic number theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "von Koch (1901)"}]->(von_koch)
CREATE (von_koch)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "von Koch (1901)"}]->(rh)

// Chebyshev ψ Error Term
CREATE (chebyshev_err:Theorem {
  name: "Chebyshev ψ Error Term",
  statement: "ψ(x) = x + O(x^{1/2} log²x), where ψ(x) = Σ_{n≤x} Λ(n)",
  proof_status: "proven",
  year_established: 1901,
  description: "Equivalent to RH via explicit formula. Stronger than PNT (ψ(x) ~ x).",
  domain: "analytic number theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(chebyshev_err)
CREATE (chebyshev_err)-[:STRENGTHENS]->(pnt)

// Volchkov Integral
CREATE (volchkov:Theorem {
  name: "Volchkov Integral",
  statement: "∫₀^∞ (1-12t²)/(1+4t²)³ ∫_{1/2}^∞ log|ζ(σ+it)| dσ dt = π(3-γ)/32",
  proof_status: "proven",
  year_established: 1995,
  description: "V.V. Volchkov. A single integral equation equivalent to RH. Elegant but computationally hard.",
  key_paper: "Volchkov (1995); Balazard-Saias-Yor (1999) Adv. Math. 143",
  domain: "complex analysis"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Volchkov (1995)"}]->(volchkov)

// Balazard-Saias-Yor Integral
CREATE (bsy:Theorem {
  name: "Balazard-Saias-Yor Integral",
  statement: "(1/π)∫₀^∞ log|ζ(1/2+it)|/(1/4+t²) dt = 0",
  proof_status: "proven",
  year_established: 1999,
  description: "A cleaner integral on the critical line itself. If ζ has a zero off the line, the integral is positive.",
  key_paper: "Balazard, Saias, Yor (1999) Adv. Math. 143, 284-287",
  domain: "complex analysis"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Balazard-Saias-Yor (1999)"}]->(bsy)

// Franel-Landau Criterion
CREATE (franel_landau:Theorem {
  name: "Franel-Landau Criterion",
  statement: "D(N) = O(N^{1/2+ε}) where D(N) = |#{squarefree n≤N : ω(n) even} - #{squarefree n≤N : ω(n) odd}|",
  proof_status: "proven",
  year_established: 1926,
  description: "Balance of squarefree integers with even vs. odd number of prime factors. Elementary formulation.",
  domain: "elementary number theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(franel_landau)

// Liouville λ Limit
CREATE (liouville_lim:Theorem {
  name: "Liouville λ Limit Criterion",
  statement: "Σ_{k=1}^n λ(k) = O(n^{1/2+ε}) for all ε > 0, where λ is Liouville function",
  proof_status: "proven",
  description: "Liouville function λ(n) = (-1)^{Ω(n)}. Closely related to Mertens function.",
  domain: "elementary number theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(liouville_lim)

// Hardy-Littlewood Series
CREATE (hardy_littlewood_series:Theorem {
  name: "Hardy-Littlewood Series",
  statement: "Σ_{k=1}^∞ (-x)^k/k! · ζ(2k+1) = O(x^{-1/4}) as x → ∞",
  proof_status: "proven",
  year_established: 1918,
  description: "Asymptotic behavior of odd zeta values in exponential generating function.",
  key_paper: "Hardy, Littlewood (1918); Conrey (2003) Notices AMS",
  domain: "analytic number theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(hardy_littlewood_series)

// ── OPERATOR-THEORETIC (additional) ─────────────────────────────

// Baez-Duarte Strengthening of Nyman-Beurling
CREATE (baez_duarte:Theorem {
  name: "Baez-Duarte Criterion",
  statement: "RH iff χ ∈ closure(span{ρ_a : a ∈ N}) in L²(0,∞), where χ is the indicator of (0,1] — countable version of Nyman-Beurling",
  proof_status: "proven",
  year_established: 2002,
  description: "Luis Báez-Duarte strengthened Nyman-Beurling from uncountable to countable generating set. Numerical evidence by Báez-Duarte up to a=100.",
  key_paper: "Báez-Duarte (2002) arXiv:math/0202141",
  domain: "functional analysis"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Báez-Duarte (2002)"}]->(baez_duarte)
CREATE (baez_duarte)-[:STRENGTHENS]->(nyman_beurling)

// Jensen Polynomial Hyperbolicity
CREATE (jensen_poly:Theorem {
  name: "Jensen Polynomial Hyperbolicity (Pólya-Jensen)",
  statement: "All Jensen polynomials J_{d,0}(x) for the Taylor coefficients of Ξ(t) are hyperbolic (all roots real) for all d ≥ 1",
  proof_status: "proven",
  year_established: 1927,
  year_stated: 1927,
  description: "Pólya (1927) established equivalence. Griffin-Ono-Rolen-Zagier (2019) proved hyperbolicity for n ≥ N(d) — computational evidence supporting RH.",
  key_paper: "Griffin, Ono, Rolen, Zagier (2019) PNAS 116, 11103-11110",
  domain: "real analysis / polynomial theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Pólya (1927)"}]->(jensen_poly)

// De Bruijn-Newman Constant Λ = 0 (as equivalence)
CREATE (dbn_equiv:Theorem {
  name: "De Bruijn-Newman Constant Λ = 0",
  statement: "RH iff Λ = 0, where H(λ,z) has only real zeros iff λ ≥ Λ. Rodgers-Tao proved Λ ≥ 0, so RH ↔ Λ = 0",
  proof_status: "proven",
  year_established: 2020,
  description: "de Bruijn (1950): Λ ≤ 1/2. Newman (1976): Λ exists, conjectured ≥ 0. Rodgers-Tao (2020): Λ ≥ 0. Gap closed to Λ = 0.",
  key_paper: "Rodgers, Tao (2020) Forum Math. Pi 8, e6",
  domain: "complex analysis / entire functions"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "de Bruijn (1950) + Rodgers-Tao (2020) Λ ≥ 0"}]->(dbn_equiv)
CREATE (rogers_tao2019)-[:PROVES {proof_technique: "real-variable methods, Pólya-Jensen"}]->(dbn_equiv)

// Bombieri's Variational Approach
CREATE (bombieri_var:Theorem {
  name: "Bombieri Variational Approach",
  statement: "RH equivalent to existence of minimizing function for Bombieri's variational functional on the explicit formula",
  proof_status: "proven",
  year_established: 2000,
  description: "Enrico Bombieri (2000, 2003). Generalizes Weil positivity via calculus of variations. Connected to Connes' noncommutative geometry trace formula.",
  key_paper: "Bombieri (2003) Comm. Pure Appl. Math. 56, 1151-1164",
  domain: "calculus of variations"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(bombieri_var)
CREATE (bombieri_var)-[:GENERALIZES]->(weil_criterion)

// Laguerre-Pólya Class
CREATE (laguerre_polya:Theorem {
  name: "Laguerre-Pólya Class",
  statement: "The Riemann Ξ-function belongs to the Laguerre-Pólya class — the uniform limit on compacts of polynomials with only real zeros",
  proof_status: "proven",
  year_established: 1927,
  description: "G. Pólya (1927), I. Schur. If RH is true, Ξ is in LP class. Equivalent statement about Hadamard product factorization.",
  key_paper: "Pólya (1927) Jber. Deutsch. Math.-Verein.",
  domain: "complex analysis"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Pólya (1927)"}]->(laguerre_polya)
CREATE (laguerre_polya)-[:CONNECTS_TO]->(jensen_poly)

// ── ARITHMETIC (additional) ─────────────────────────────────────

// Caveney-Nicolas-Sondow GA1/GA2
CREATE (ga_cns:Theorem {
  name: "Caveney-Nicolas-Sondow GA1/GA2 Criterion",
  statement: "The only number that is both GA1 (composite N with G(N)≥G(N/p) ∀p|N) and GA2 (G(N)≥G(aN) ∀a) is 4, where G(n) = σ(n)/(n log log n)",
  proof_status: "proven",
  year_established: 2011,
  description: "Refinement of Robin's inequality. Connected to colossally abundant numbers.",
  key_paper: "Caveney, Nicolas, Sondow (2011) arXiv:1107.1295",
  domain: "arithmetic functions"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(ga_cns)
CREATE (ga_cns)-[:REFINES]->(robin)

// Redheffer Matrix
CREATE (redheffer:Theorem {
  name: "Redheffer Matrix Criterion",
  statement: "|det(A_n)| = O(n^{1/2+ε}) where A_{ij}=1 if j=1 or i|j, 0 otherwise. Since det(A_n) = M(n), this is equivalent to Mertens bound.",
  proof_status: "proven",
  year_established: 1977,
  description: "R. Redheffer. Matrix formulation of Mertens function. All non-trivial eigenvalues in unit disk ↔ RH.",
  key_paper: "Redheffer (1977); Barrett, Forcade, Pollington (1988)",
  domain: "linear algebra / matrix theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(redheffer)
CREATE (redheffer)-[:CONNECTS_TO {description: "det(A_n) = M(n)"}]->(mertens)

// Landau Function / Symmetric Group
CREATE (landau_fn:Theorem {
  name: "Landau Function Criterion",
  statement: "log g(n) < li^{-1}(n) for all n ≥ 1, where g(n) = maximal order of element in symmetric group S_n",
  proof_status: "proven",
  year_established: 2019,
  description: "M. Deleglise, J.-L. Nicolas (2019). Connects RH to combinatorics of permutations.",
  key_paper: "Deleglise, Nicolas (2019) arXiv:1907.02580",
  domain: "combinatorics / group theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(landau_fn)

// lcm Formulation
CREATE (lcm_form:Theorem {
  name: "lcm Formulation",
  statement: "|log lcm(1,2,...,n) - n| < √n log²n for all n ≥ 3",
  proof_status: "proven",
  description: "Follows from explicit formula. Elementary formulation in terms of least common multiple.",
  domain: "elementary number theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(lcm_form)

// Speiser's Criterion
CREATE (speiser:Theorem {
  name: "Speiser's Criterion",
  statement: "RH equivalent to absence of non-trivial zeros of ζ'(s) to the left of the critical line Re(s) = 1/2",
  proof_status: "proven",
  year_established: 1934,
  description: "Andreas Speiser (1934). The derivative ζ'(s) has no zeros with Re(s) < 1/2 iff RH holds. Quantified by Levinson-Montgomery (1974).",
  key_paper: "Speiser (1934) Math. Ann. 110, 514-521",
  domain: "complex analysis"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Speiser (1934)"}]->(speiser)

// ── PROBABILISTIC ───────────────────────────────────────────────

// Brownian Excursion
CREATE (brownian_excursion:Theorem {
  name: "Brownian Excursion (Biane-Pitman-Yor)",
  statement: "E[Z_s] = Ξ(s) where Z_s = ∫₀^∞ cos(st)|B_u|du for Brownian excursion B_u. RH connects to moment conditions.",
  proof_status: "proven",
  year_established: 2001,
  description: "P. Biane, J. Pitman, M. Yor (2001). The Riemann Ξ-function has a probabilistic interpretation via Brownian excursion area.",
  key_paper: "Biane, Pitman, Yor (2001) Bull. AMS 38, 435-465",
  domain: "probability theory"
})
CREATE (brownian_excursion)-[:CONNECTS_TO {description: "probability interpretation of Ξ-function"}]->(zeta)

// Horocycle Flow Ergodicity
CREATE (horocycle:Theorem {
  name: "Horocycle Flow Ergodicity Rate",
  statement: "∫₀^T f(h_t z)dt = T∫f + O(T^{1/2+ε}) for nice f on SL(2,R)/SL(2,Z) iff RH",
  proof_status: "proven",
  year_established: 1990,
  description: "D. Mayer. The rate of equidistribution of horocycle flows on the modular surface encodes RH. Connects dynamical systems to number theory.",
  key_paper: "Mayer (1990); noted by Zagier; Lagarias (2010) Clay Math. Proc.",
  domain: "dynamical systems / ergodic theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(horocycle)

// ── GRAPH-THEORETIC ─────────────────────────────────────────────

// Divisibility Graph (Broughan)
CREATE (divisibility_graph:Theorem {
  name: "Divisibility Graph Criterion",
  statement: "RH equivalent to spectral properties of the divisibility graph (vertices 1..N, edges n→m if n|m)",
  proof_status: "proven",
  year_established: 2017,
  description: "K.A. Broughan. The divisibility graph's spectral radius behavior encodes RH.",
  key_paper: "Broughan (2017) Equivalents of RH Vol I, Ch. 10",
  domain: "graph theory"
})
CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional"}]->(divisibility_graph)

// ── SURVEY PAPERS ────────────────────────────────────────────────

CREATE (broughan_survey:Paper {
  title: "Equivalents of the Riemann Hypothesis, Volumes I and II",
  authors_str: "Keith A. Broughan",
  year: 2017,
  publication_type: "book",
  publisher: "Cambridge University Press",
  doi: "10.1017/9781108178228",
  bibtex_key: "broughan2017",
  relevance_to_rh: "foundational",
  description: "THE definitive catalog of RH equivalences. 100+ formulations across 2 volumes. Arithmetic + analytic equivalents with full proofs."
})

CREATE (borwein_survey:Paper {
  title: "The Riemann Hypothesis: A Resource for the Afficionado and Virtuoso Alike",
  authors_str: "P. Borwein, S. Choi, B. Rooney, A. Weirathmueller",
  year: 2008,
  publication_type: "book",
  publisher: "Springer",
  doi: "10.1007/978-0-387-72126-2",
  bibtex_key: "borwein2008",
  relevance_to_rh: "foundational",
  description: "Comprehensive survey with Chapter 5 covering ~30 major equivalent formulations."
})

CREATE (conrey2003:Paper {
  title: "The Riemann Hypothesis",
  authors_str: "J. Brian Conrey",
  year: 2003,
  publication_type: "journal",
  journal: "Notices of the American Mathematical Society",
  volume: "50",
  pages: "341-353",
  bibtex_key: "conrey2003",
  relevance_to_rh: "foundational",
  description: "Influential survey covering the main equivalent formulations, history, and implications."
})

CREATE (connes2026:Paper {
  title: "The Riemann Hypothesis: Past, Present and a Letter Through Time",
  authors_str: "Alain Connes",
  year: 2026,
  publication_type: "preprint",
  arxiv_id: "2602.04022",
  bibtex_key: "connes2026",
  relevance_to_rh: "foundational",
  description: "Connes' modern survey. Notes 'over 100 equivalent formulations'. Noncommutative geometry approach."
})

CREATE (griffin2019:Paper {
  title: "Jensen polynomials for the Riemann zeta function and other sequences",
  authors_str: "M.J. Griffin, K. Ono, L. Rolen, D. Zagier",
  year: 2019,
  publication_type: "journal",
  journal: "PNAS",
  volume: "116",
  pages: "11103-11110",
  doi: "10.1073/pnas.1902572116",
  bibtex_key: "griffin2019",
  relevance_to_rh: "direct",
  description: "Proved hyperbolicity of Jensen polynomials for n ≥ N(d). Computational evidence supporting RH via polynomial theory."
})

// ── RELATIONSHIPS ───────────────────────────────────────────────
CREATE (von_koch)-[:IMPLIES]->(chebyshev_err)
CREATE (volchkov)-[:RELATED_TO]->(bsy)
CREATE (bombieri_var)-[:GENERALIZES]->(weil_criterion)
CREATE (ga_cns)-[:REFINES]->(robin)
CREATE (redheffer)-[:CONNECTS_TO]->(mertens)
CREATE (broughan_survey)-[:CITES]->(riemann1859)
CREATE (conrey2003)-[:CITES]->(riemann1859)
CREATE (connes2026)-[:CITES]->(riemann1859)
CREATE (griffin2019)-[:PROVES {proof_technique: "polynomial theory, arithmetic of Dirichlet series"}]->(jensen_poly)
