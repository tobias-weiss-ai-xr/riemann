// ── Algebraic Groups ─────────────────────────────────────────────
// Core groups in the SL(2,Z) → ζ(s) theory chain

// SL(2,Z) — The fundamental object
CREATE (sl2z:Group {
  name: "SL(2,Z)",
  type: "algebraic_group",
  description: "Special linear group of 2×2 integer matrices with determinant 1",
  order: "infinite",
  generators: "S = [[0,-1],[1,0]], T = [[1,1],[0,1]]",
  presentation: "S² = (ST)³ = -I",
  is_discrete: true,
  is_finite: false,
  properties: "Fuchsian group, lattice in SL(2,R)"
})

// PSL(2,Z) — Projective special linear group
CREATE (psl2z:Group {
  name: "PSL(2,Z)",
  type: "algebraic_group",
  description: "SL(2,Z) / {±I}, isomorphic to free product C₂ * C₃",
  order: "infinite",
  generators: "s = [[0,-1],[1,0]], t = [[1,1],[0,1]]",
  presentation: "s² = (st)³ = I",
  is_discrete: true,
  is_finite: false,
  properties: "Free product of cyclic groups C₂ and C₃"
})

// SL(2,F_p) — Finite field analogue
CREATE (sl2fp:Group {
  name: "SL(2,F_p)",
  type: "finite_group",
  description: "Special linear group over finite field F_p, order p(p²-1)",
  order: "p(p²-1)",
  generators: "4 generators from fundamental roots: E₁₂, E₂₁ and inverses",
  is_discrete: true,
  is_finite: true,
  properties: "PSL(2,F_p) simple for p ≥ 5, strong approximation theorem applies"
})

// PSL(2,F_p)
CREATE (psl2fp:Group {
  name: "PSL(2,F_p)",
  type: "finite_group",
  description: "Projective special linear group over F_p",
  order: "p(p²-1)/2 for odd p",
  is_discrete: true,
  is_finite: true,
  properties: "Simple non-abelian group for p ≥ 5"
})

// Congruence subgroups
CREATE (gamma0n:Group {
  name: "Γ₀(N)",
  type: "congruence_subgroup",
  description: "Congruence subgroup of SL(2,Z) with upper-left entry divisible by N",
  order: "infinite",
  index_in_sl2z: "N ∏(1 + 1/p) for p|N",
  is_discrete: true,
  is_finite: false,
  properties: "Key subgroup for modular forms of level N"
})

CREATE (gamma1n:Group {
  name: "Γ₁(N)",
  type: "congruence_subgroup",
  description: "Congruence subgroup with lower-left entry ≡ 0 mod N and diagonal entries ≡ 1 mod N",
  order: "infinite",
  is_discrete: true,
  is_finite: false,
  properties: "Used in Dirichlet characters and newforms"
})

// GL(2) — General linear group (for Langlands)
CREATE (gl2:Group {
  name: "GL(2)",
  type: "algebraic_group",
  description: "General linear group of 2×2 invertible matrices",
  order: "infinite",
  is_discrete: false,
  is_finite: false,
  properties: "Central object in Langlands program for GL(2)"
})

// ── Relationships ───────────────────────────────────────────────
CREATE (sl2z)-[:HAS_SUBGROUP {
  description: "PSL(2,Z) = SL(2,Z) / {±I}",
  quotient: "C₂"
}]->(psl2z)

CREATE (sl2z)-[:HAS_SUBGROUP {
  description: "Γ₀(N) ⊂ SL(2,Z) for any N ≥ 1"
}]->(gamma0n)

CREATE (sl2z)-[:HAS_SUBGROUP {
  description: "Γ₁(N) ⊂ Γ₀(N) ⊂ SL(2,Z)"
}]->(gamma1n)

CREATE (psl2fp)-[:FINITE_ANALOGUE_OF {
  description: "PSL(2,F_p) is the finite field analogue of PSL(2,Z)"
}]->(psl2z)

CREATE (sl2fp)-[:FINITE_ANALOGUE_OF {
  description: "SL(2,F_p) is the finite field analogue of SL(2,Z)"
}]->(sl2z)

CREATE (gl2)-[:CONTAINS]->(sl2z)
CREATE (gl2)-[:CONTAINS]->(sl2fp)
