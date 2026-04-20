// ── RH Extended Equivalence Class ─────────────────────────────────
// Additional formulations equivalent to the Riemann Hypothesis.
// Run after 05-theorems.cypher (needs rh node to already exist).

// ── NYMAN-BEURLING CRITERION ─────────────────────────────────────
CREATE (nyman_beurling:Theorem {
  name: "Nyman-Beurling Criterion",
  statement: "RH holds iff the functions {f_a(x) = {ax} - a⌊x⌋ : a ∈ (0,1]} span L²(0,1)",
  latex_statement: "\\text{RH} \\iff \\overline{\\text{span}}\\{f_a : a \\in (0,1]\\} = L^2(0,1)",
  proof_status: "proven",
  year_stated: 1950,
  year_established: 1950,
  significance: "major",
  difficulty: "analytic",
  description: "RH equivalent to the density of shifted fractional part functions in L²(0,1). Key bridge for neural network approaches (Hayou 2023).",
  key_paper: "Nyman 1950, Beurling 1955"
})

CREATE (rh)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Nyman (1950), Beurling (1955)"}]->(nyman_beurling)
CREATE (nyman_beurling)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Nyman (1950), Beurling (1955)"}]->(rh)
CREATE (hayou2023)-[:APPROACHES_VIA {strategy: "RH ≡ density of single-layer NNs via Nyman-Beurling", confidence: 0.3}]->(nyman_beurling)

// ── HILBERT-PÓLYA CONJECTURE ─────────────────────────────────────
CREATE (hilbert_polya:Theorem:Conjecture:OpenProblem {
  name: "Hilbert-Pólya Conjecture",
  statement: "The imaginary parts of the non-trivial zeros of ζ(s) are the eigenvalues of a self-adjoint operator (Hermitian matrix) on a Hilbert space",
  proof_status: "open",
  year_stated: 1914,
  significance: "foundational",
  description: "If true, RH follows because self-adjoint operators have real eigenvalues → Im(ρ) real → Re(ρ) = 1/2. Yakaboylu (2023) constructed a Hamiltonian with real eigenvalues under certain conditions.",
  note: "NOT proven equivalent to RH — it's a sufficient condition. If such an operator exists, RH follows, but the converse is unclear."
})

CREATE (hilbert_polya)-[:IMPLIES {description: "Self-adjoint operator has real spectrum → zeros on critical line"}]->(rh)

// ── WEIL CRITERION (Positivity) ─────────────────────────────────
CREATE (weil_criterion:Theorem {
  name: "Weil Positivity Criterion",
  statement: "RH holds iff the function F(z) = Σ_ρ x^ρ + (analytic terms) is positive-definite on the multiplicative group",
  proof_status: "proven",
  year_established: 1952,
  significance: "major",
  difficulty: "algebraic",
  description: "André Weil showed that RH for curves over finite fields follows from a positivity condition on associated zeta functions. This inspired the entire Langlands program.",
  key_paper: "Weil 1952"
})

CREATE (weil_criterion)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Weil (1952)"}]->(rh)
CREATE (weil_criterion)-[:MOTIVATED]->(sato_tate)

// ── LI'S CRITERION ──────────────────────────────────────────────
CREATE (li_criterion:Theorem {
  name: "Li's Criterion",
  statement: "RH holds iff λ_n = Σ_ρ (1 - (1 - 1/ρ)^n) ≥ 0 for all n ∈ N, where ρ runs over non-trivial zeros of ζ(s)",
  proof_status: "proven",
  year_established: 1998,
  significance: "major",
  description: "Xian-Jin Li (1998). Gives an infinite sequence of non-negativity conditions equivalent to RH. Related to the explicit formula.",
  key_paper: "Li 1998, Journal of Number Theory"
})

CREATE (li_criterion)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Li (1998)"}]->(rh)
CREATE (li_criterion)-[:CONNECTS_TO]->(zeta)

// ── MERTENS HYPOTHESIS (disproven!) ─────────────────────────────
CREATE (mertens:Theorem:Conjecture {
  name: "Mertens Hypothesis",
  statement: "|M(x)| = |Σ_{n≤x} μ(n)| < √x for all x > 1",
  proof_status: "disproven",
  year_stated: 1897,
  year_established: 1985,
  significance: "major",
  description: "Conjectured by Mertens (1897). Disproven by Odlyzko & te Riele (1985): M(x) = Ω±(√x) infinitely often. But it's STRONGER than RH — if it were true, RH would follow. Its failure doesn't disprove RH.",
  key_paper: "Odlyzko & te Riele 1985, Journal für die reine und angewandte Mathematik"
})

CREATE (mertens)-[:IMPLIES {description: "Mertens hypothesis implies RH, but Mertens is FALSE"}]->(rh)

// ── NICOLAS CRITERION ───────────────────────────────────────────
CREATE (nicolas:Theorem:Conjecture {
  name: "Nicolas Criterion",
  statement: "RH holds iff Σ_{d|n} d ≥ H_n + exp(H_n) log(H_n) for all n ≥ 2, where H_n is the nth harmonic number",
  proof_status: "conjectured",
  year_stated: 1983,
  description: "Jean-Louis Nicolas. Related to Robin's inequality but using the harmonic numbers. Equivalent to RH."
})

CREATE (nicolas)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Nicolas (1983)"}]->(rh)

// ── EXPLICIT FORMULA ────────────────────────────────────────────
CREATE (explicit_formula:Theorem {
  name: "Explicit Formula",
  statement: "ψ₀(x) = x - Σ_ρ x^ρ/ρ - log(2π) - ½log(1 - x⁻²), where ψ₀(x) = Σ_{n≤x} Λ(n) (Chebyshev function), ρ runs over non-trivial zeros",
  proof_status: "proven",
  year_established: 1896,
  significance: "foundational",
  description: "THE central formula connecting prime distribution to zeta zeros. Von Mangoldt. RH equivalent to ψ(x) = x + O(x^{1/2+ε}).",
  key_paper: "von Mangoldt 1896"
})

CREATE (explicit_formula)-[:CONNECTS_TO]->(zeta)
CREATE (explicit_formula)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "RH ↔ ψ(x) = x + O(x^{1/2+ε})"}]->(rh)
CREATE (explicit_formula)-[:USED_IN]->(li_criterion)

// ── BAGCHI'S THEOREM ────────────────────────────────────────────
CREATE (bagchi:Theorem {
  name: "Bagchi's Theorem",
  statement: "RH holds iff the Hurwitz zeta function ζ(s,a) is cyclic in L²(0,1) with respect to the translation semigroup",
  proof_status: "proven",
  year_established: 1982,
  description: "Bhaskar Bagchi (1982). Reformulates Nyman-Beurling in terms of dynamical systems on L². Connects RH to ergodic theory.",
  key_paper: "Bagchi 1982, PhD Thesis"
})

CREATE (bagchi)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Bagchi (1982)"}]->(rh)
CREATE (bagchi)-[:GENERALIZES]->(nyman_beurling)

// ── VORONIN UNIVERSALITY ────────────────────────────────────────
CREATE (voronin:Theorem {
  name: "Voronin Universality Theorem",
  statement: "For any ε > 0, any analytic function f(s) non-vanishing on the strip {1/2 < Re(s) < 1}, there exists τ > 0 such that max_{|s-3/4|≤r} |ζ(s+iτ) - f(s)| < ε",
  proof_status: "proven",
  year_established: 1975,
  significance: "major",
  description: "Sergei Voronin (1975). The Riemann zeta function is universal — it can approximate any non-vanishing analytic function in any right-half of the critical strip. Striking implication: if RH is false, the universality domain changes.",
  key_paper: "Voronin 1975"
})

CREATE (voronin)-[:CONNECTS_TO]->(zeta)

// ── YAKABOYLU HAMILTONIAN ───────────────────────────────────────
CREATE (yakaboylu:Theorem {
  name: "Yakaboylu Hamiltonian Construction",
  statement: "Constructs a quantum Hamiltonian H with real eigenvalues (under conditions) whose spectrum encodes zeta zeros",
  proof_status: "partial",
  year_established: 2023,
  description: "Yakaboylu (2023) partially realized Hilbert-Pólya. Shows real eigenvalues under certain conditions. No ML work on operator search exists — open gap.",
  key_paper: "Yakaboylu 2023, arXiv"
})

CREATE (yakaboylu)-[:APPROACHES_TOWARDS]->(hilbert_polya)

// ── MÖBIUS RANDOMNESS ───────────────────────────────────────────
CREATE (mobius_randomness:Theorem:Conjecture {
  name: "Möbius Randomness (Chowla Conjecture)",
  statement: "Σ_{n≤x} μ(n) μ(n+h) = o(x) for all fixed h ≠ 0",
  proof_status: "open",
  year_stated: 1965,
  significance: "major",
  description: "Sarvadaman Chowla. Möbius function is random (uncorrelated at shifts). Stronger than PNT. Connected to Sarnak's conjecture on deterministic sequences."
})

CREATE (mobius_randomness)-[:IMPLIES {description: "Chowla implies PNT (via partial summation), but NOT equivalent to RH"}]->(pnt)
