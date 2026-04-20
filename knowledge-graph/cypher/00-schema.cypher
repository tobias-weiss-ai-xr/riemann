// ── Riemann Research Knowledge Graph — Schema ─────────────────────
// Run first: cypher-shell -u neo4j -p <pass> -f 00-schema.cypher

// ── Constraints (unique nodes) ──────────────────────────────────
CREATE CONSTRAINT group_name IF NOT EXISTS FOR (g:Group) REQUIRE g.name IS UNIQUE;
CREATE CONSTRAINT graph_name IF NOT EXISTS FOR (g:Graph) REQUIRE g.name IS UNIQUE;
CREATE CONSTRAINT mfunc_name IF NOT EXISTS FOR (f:MathFunction) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT operator_name IF NOT EXISTS FOR (o:Operator) REQUIRE o.name IS UNIQUE;
CREATE CONSTRAINT theorem_name IF NOT EXISTS FOR (t:Theorem) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT paper_doi IF NOT EXISTS FOR (p:Paper) REQUIRE p.doi IS UNIQUE;
CREATE CONSTRAINT researcher_name IF NOT EXISTS FOR (r:Researcher) REQUIRE r.name IS UNIQUE;
CREATE CONSTRAINT approach_name IF NOT EXISTS FOR (a:Approach) REQUIRE a.name IS UNIQUE;
CREATE CONSTRAINT conjecture_name IF NOT EXISTS FOR (c:Conjecture) REQUIRE c.name IS UNIQUE;

// ── Indexes ─────────────────────────────────────────────────────
CREATE INDEX group_type IF NOT EXISTS FOR (g:Group) ON (g.type);
CREATE INDEX graph_type IF NOT EXISTS FOR (g:Graph) ON (g.type);
CREATE INDEX mfunc_type IF NOT EXISTS FOR (f:MathFunction) ON (f.type);
CREATE INDEX theorem_year IF NOT EXISTS FOR (t:Theorem) ON (t.year);
CREATE INDEX paper_year IF NOT EXISTS FOR (p:Paper) ON (p.year);
CREATE INDEX paper_venue IF NOT EXISTS FOR (p:Paper) ON (p.venue);
CREATE INDEX approach_feasibility IF NOT EXISTS FOR (a:Approach) ON (a.feasibility);

// ── Relationship type documentation ─────────────────────────────
// HAS_SUBGROUP:     (Group) -> (Group)         e.g. Γ₀(N) ⊂ SL(2,Z)
// HAS_CAYLEY_GRAPH: (Group) -> (Graph)         e.g. SL(2,F_p) -> Cayley(SL(2,F_p))
// HAS_SPECTRUM:     (Graph) -> (MathFunction)   e.g. Cayley -> Ihara zeta
// ACTS_ON:          (Operator) -> (MathFunction) e.g. T_p -> modular form
// CORRESPONDS_TO:   (Operator) -> (Operator)    e.g. Hecke T_p <-> Adjacency A_p
// GENERALIZES:      (Theorem) -> (Theorem)      e.g. Langlands -> Class Field Theory
// IMPLIES:          (Theorem) -> (Conjecture)   e.g. Wiener-Ikehara -> PNT
// STATES:           (Conjecture) -> (MathFunction) e.g. RH -> ζ(s)
// ABOUT:            (Paper) -> ANY              e.g. LPS 1988 about Cayley graphs
// PROVES:           (Paper) -> (Theorem)        e.g. Barnet-Lamb proves Sato-Tate
// PROPOSES:         (Paper) -> (Conjecture)     e.g. Riemann 1859 proposes RH
// CITES:            (Paper) -> (Paper)          e.g. Pollicott 2022 cites Riemann 1859
// AUTHORED:         (Researcher) -> (Paper)     e.g. Tao authored PNT+ paper
// TARGETS:          (Approach) -> (Conjecture)  e.g. GNN spectral targets RH
// USES_CONCEPT:     (Approach) -> ANY           e.g. GNN uses Cayley graphs
// BASED_ON:         (Approach) -> (Paper)       e.g. LPS approach based on LPS 1988
// BRIDGE:           (Theorem) -> (Theorem)      e.g. LPS construction bridges graphs<->L-functions
// ANALOGOUS_TO:     (Conjecture) -> (Conjecture) e.g. IH-RH analogous to RH
// COMPUTED_VIA:     (MathFunction) -> (Operator) e.g. L-function computed via Hecke
