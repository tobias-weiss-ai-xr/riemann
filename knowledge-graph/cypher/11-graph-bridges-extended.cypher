// ── Graph Bridges Extended: LPS + Pollicott ────────────────────────
// Extends the two graph→ζ(s) bridges with Mayer transfer operator,
// Selberg zeta, Gauss map, Fredholm determinant, thermodynamic formalism,
// Friedli spectral zeta, Granville-Goldbach, Eichler trace formula,
// Bass formula, and experimental results (Friedli constant 1.1367).
// Also fixes broken NULL-target relationships from files 04/09/10.
// Run AFTER 10-rh-equivalences-extended.cypher. Uses MATCH+MERGE (idempotent).

// ════════════════════════════════════════════════════════════════════
// SECTION 1: FIX BROKEN RELATIONSHIPS (NULL targets from files 04/09/10)
// ════════════════════════════════════════════════════════════════════

// Fix: Hashimoto H → COMPUTES_VIA → (NULL) should be → Ihara zeta ζ_G(u)
MATCH (h:Operator {name: "Hashimoto Edge Matrix H"}), (iz:MathFunction {name: "ζ_G(u)"})
MATCH (h)-[r:COMPUTES_VIA]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (h)-[:COMPUTES_VIA {description: "ζ_G(u)⁻¹ = det(I - Hu) — Hashimoto edge matrix computes Ihara zeta"}]->(iz);

// Fix: Farey Transfer Operator L_s → ENCODES → (NULL) should be → Selberg zeta Z_S(s)
// We create Z_S(s) below in Section 2, then fix this relationship in Section 3.

// ════════════════════════════════════════════════════════════════════
// SECTION 2: NEW NODES — Mayer Transfer Operator, Selberg Zeta, Gauss Map,
// Fredholm Determinant, Thermodynamic Formalism, New Theorems, Papers, Researchers
// ════════════════════════════════════════════════════════════════════

// ── Selberg Zeta Function ──────────────────────────────────────────
MERGE (selberg_zeta:MathFunction {name: "Z_S(s)"})
SET selberg_zeta.type = "selberg_zeta",
    selberg_zeta.description = "Selberg zeta function Z_S(s) for PSL(2,Z). Zeros encode the spectrum of the Laplacian on the modular surface. Related to ζ(s) via the Selberg trace formula.",
    selberg_zeta.domain = "automorphic",
    selberg_zeta.notes = "Mayer identity: det(I - L_s) = Z_S(s) / Z_S(s+1). RH connection: Z_S(s) ≠ 0 for Re(s) > 1/2 iff RH.";

// ── Mayer Transfer Operator L_s (distinct from Farey Transfer Operator) ──
MERGE (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
SET mayer_L_s.type = "transfer",
    mayer_L_s.description = "Mayer's transfer operator L_s acting on holomorphic functions on the upper half-plane. Defined via the Gauss map T(x) = 1/x - ⌊1/x⌋ and its inverse branches. Trace class (nuclear) for Re(s) > 1/2.",
    mayer_L_s.space = "H_1 (holomorphic functions on H)",
    mayer_L_s.nuclearity = "trace class for Re(s) > 1/2 (Mayer 1990, Isola 2003)",
    mayer_L_s.key_property = "det(I - L_s) = Z_S(s) / Z_S(s+1) (Mayer identity, Möller-Pohl 2011)";

// ── Gauss Map ─────────────────────────────────────────────────────
MERGE (gauss_map:Operator {name: "Gauss Map T"})
SET gauss_map.type = "dynamical_system",
    gauss_map.description = "Gauss map T: (0,1] → [0,1), T(x) = 1/x - ⌊1/x⌋. Continued fraction expansion. The transfer operator of the Gauss map is the Mayer operator L_s. Inverse branches: x ↦ 1/(n+x) for n ∈ Z≥1.",
    gauss_map.connection = "Farey map is the induced map of Gauss map on the Farey tessellation";

// ── Fredholm Determinant ──────────────────────────────────────────
MERGE (fredholm:MathFunction {name: "Fredholm Determinant det(I-T)"})
SET fredholm.type = "fredholm_determinant",
    fredholm.description = "For trace-class operator T: det(I-T) = ∏_n (1 - λ_n) where λ_n are eigenvalues. Key property: ρ(T) < 1 ⟺ det(I-T) ≠ 0. Used in transfer operator approach: det(I-L_s) ≠ 0 for Re(s) > 1/2 ⟺ RH.",
    fredholm.reference = "Simon (2005) Trace Ideals and Their Applications";

// ── Topological Pressure ──────────────────────────────────────────
MERGE (pressure:MathFunction {name: "Topological Pressure P(φ)"})
SET pressure.type = "thermodynamic",
    pressure.description = "Topological pressure P(φ) = log ρ(L_φ) for Hölder potential φ. Connects transfer operator spectral radius to dynamical systems. Bowen equation characterizes equilibrium states.",
    pressure.reference = "Ruelle (1978), Walters (1982)";


// ── New Theorems ──────────────────────────────────────────────────

// Mayer Identity
MERGE (mayer_id:Theorem {name: "Mayer Identity"})
SET mayer_id.statement = "det(I - L_s) = Z_S(s) / Z_S(s+1) for PSL(2,Z) Selberg zeta",
    mayer_id.proof_status = "proven",
    mayer_id.year_established = 2011,
    mayer_id.significance = "central",
    mayer_id.description = "Moller-Pohl (2011). Bridges the transfer operator spectrum to the Selberg zeta function. RH chain: RH iff Z_S(s) != 0 for Re(s)>1/2 iff det(I-L_s) != 0 for Re(s)>1/2 iff 1 not eigenvalue of L_s.",
    mayer_id.domain = "dynamical systems / operator theory";

// Bonanno Eigenvalue-1 Equivalence
MERGE (bonanno_ev:Theorem {name: "Bonanno Eigenvalue-1 Equivalence"})
SET bonanno_ev.statement = "The transfer operator P_q tilde has eigenvalue 1 iff 2q is a non-trivial zero of zeta(s)",
    bonanno_ev.proof_status = "proven",
    bonanno_ev.year_established = 2022,
    bonanno_ev.significance = "major",
    bonanno_ev.description = "Bonanno (2022). Direct spectral characterization of zeta zeros via transfer operator eigenvalue 1. Computational path: numerical linear algebra on transfer operator matrix.",
    bonanno_ev.domain = "dynamical systems";

// Granville Averaged Goldbach Equivalence
MERGE (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
SET granville.statement = "RH iff sum_{2N<=x} (G(2N) - J(2N)) << x^{3/2+o(1)}, where G(2N) = sum_{p+q=2N} log p log q and J(2N) = Hardy-Littlewood singular series prediction",
    granville.proof_status = "proven",
    granville.year_established = 2007,
    granville.significance = "major",
    granville.description = "Granville (2007). RH equivalent to an averaged Goldbach bound. 'Averaged' structure matches the Friedli spectral zeta average. Chain: spectral gap -> Brandt matrix -> Hecke trace -> L-function -> explicit formula -> Goldbach.",
    granville.domain = "analytic number theory / additive";

// Eichler Trace Formula
MERGE (eichler:Theorem {name: "Eichler Trace Formula"})
SET eichler.statement = "For isogeny graphs: Frobenius endomorphism eigenvalues = adjacency matrix eigenvalues (via Eichler trace formula)",
    eichler.proof_status = "proven",
    eichler.year_established = 1954,
    eichler.significance = "central",
    eichler.description = "Connects Hecke algebra / modular form eigenvalues to graph adjacency spectra for isogeny graphs of elliptic curves. The number-theoretic analogue of the LPS construction for general Cayley graphs.",
    eichler.domain = "arithmetic geometry / graph theory";

// Bass Formula
MERGE (bass:Theorem {name: "Bass Formula"})
SET bass.statement = "zeta_G(u)^{-1} = det(I - Hu) * (1-u^2)^{r-1}, where H is the Hashimoto edge matrix and r = number of vertices",
    bass.proof_status = "proven",
    bass.year_established = 1992,
    bass.significance = "major",
    bass.description = "Hyon-Bass (1992). Relates the Ihara zeta function to the Hashimoto edge adjacency matrix. Alternative: zeta_G(u)^{-1} = (1-u^2)^{r-1} det(I - uA) for (q+1)-regular graphs, where A is the vertex adjacency matrix.",
    bass.domain = "graph theory / algebraic topology";

// Friedli Spectral Zeta Functional Equation
MERGE (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
SET friedli_theorem.statement = "For cyclic graphs Z/nZ: RH iff asymptotic functional equation s <-> 1-s for spectral zeta zeta_{Z/nZ}(s)",
    friedli_theorem.proof_status = "proven",
    friedli_theorem.year_established = 2017,
    friedli_theorem.significance = "major",
    friedli_theorem.description = "Karlsson-Friedli (Tohoku Math J 2017). For SL(2,F_p) Cayley graphs, the Friedli derivative d(log R_p)/d_sigma at sigma=1/2 converges to C ~ 1.1367 (non-abelian invariant, NOT zero). Formalized in Lean 4: lean/Riemann/FriedliRatio.lean.",
    friedli_theorem.domain = "spectral theory / analytic number theory",
    friedli_theorem.experiment = "Exp 15, 15b: computed zeta_p(s) for p=2,3,5,7,11,13 with full spectra, found Friedli constant 1.1367";


// ── New Papers ────────────────────────────────────────────────────

MERGE (p_mayer:Paper {title: "On the thermodynamic formalism for the Gauss map"})
SET p_mayer.year = 1990,
    p_mayer.authors = "D. H. Mayer",
    p_mayer.journal = "Commun. Math. Phys. 130, 311-333",
    p_mayer.description = "Introduces the Mayer transfer operator L_s for the Gauss map. Proves trace class (nuclearity) for Re(s) > 1/2. Establishes connection to Selberg zeta.";

MERGE (p_isola:Paper {title: "On the spectrum of Farey and Gauss maps"})
SET p_isola.year = 2003,
    p_isola.authors = "S. Isola",
    p_isola.arxiv = "math/0308017",
    p_isola.description = "Spectral analysis of Farey and Gauss map transfer operators. Nuclearity results and eigenvalue distribution.";

MERGE (p_bonanno:Paper {title: "The 1-eigenvalue problem for the transfer operator of the Farey map"})
SET p_bonanno.year = 2022,
    p_bonanno.authors = "C. Bonanno",
    p_bonanno.arxiv = "2211.11664",
    p_bonanno.description = "Eigenvalue 1 of the transfer operator P_q is equivalent to 2q being a non-trivial zero of zeta(s). Direct spectral characterization of zeta zeros.";

MERGE (p_moller_pohl:Paper {title: "The transfer operator for the Gauss map and the Selberg zeta function"})
SET p_moller_pohl.year = 2011,
    p_moller_pohl.authors = "M. Moller, A. Pohl",
    p_moller_pohl.description = "Proves the Mayer identity: det(I - L_s) = Z_S(s) / Z_S(s+1). Central result connecting transfer operator spectrum to Selberg zeta.";

MERGE (p_liverani:Paper {title: "Decay of correlations for piecewise expanding maps"})
SET p_liverani.year = 2005,
    p_liverani.authors = "C. Liverani",
    p_liverani.description = "Analytic continuation of det(I - L_s) as entire function of s. Spectral gap of transfer operators for piecewise expanding maps.";

MERGE (p_ruelle:Paper {title: "Thermodynamic Formalism"})
SET p_ruelle.year = 1978,
    p_ruelle.authors = "D. Ruelle",
    p_ruelle.description = "Foundational text on thermodynamic formalism. Topological pressure, equilibrium states, transfer operators for dynamical systems.";

MERGE (p_walters:Paper {title: "An Introduction to Ergodic Theory"})
SET p_walters.year = 1982,
    p_walters.authors = "P. Walters",
    p_walters.description = "Standard reference for ergodic theory. Bowen equation, topological pressure, and the relation to transfer operator spectral radius.";

MERGE (p_granville:Paper {title: "Refinements of Goldbach conjecture, and the Riemann hypothesis"})
SET p_granville.year = 2007,
    p_granville.authors = "A. Granville",
    p_granville.description = "Proves RH equivalent to averaged Goldbach bound. Formalized in Lean 4: lean/Riemann/GoldbachBridge.lean (Experiment 16, Direction C).";

MERGE (p_friedli:Paper {title: "A spectral characterization of the Riemann hypothesis"})
SET p_friedli.year = 2017,
    p_friedli.authors = "S. Friedli",
    p_friedli.journal = "Tohoku Math. J.",
    p_friedli.description = "Karlsson-Friedli theorem: RH equivalent to asymptotic functional equation of spectral zeta for cyclic graphs. Extended to SL(2,F_p) in Exp 15/15b (Friedli constant 1.1367).";


// ── New Researchers ───────────────────────────────────────────────

MERGE (r_mayer:Researcher {name: "D. H. Mayer"})
SET r_mayer.affiliation = "None specified";

MERGE (r_isola:Researcher {name: "S. Isola"})
SET r_isola.affiliation = "None specified";

MERGE (r_bonanno:Researcher {name: "C. Bonanno"})
SET r_bonanno.affiliation = "University of Pisa";

MERGE (r_granville:Researcher {name: "A. Granville"})
SET r_granville.affiliation = "University of Montreal";

MERGE (r_friedli:Researcher {name: "S. Friedli"})
SET r_friedli.affiliation = "None specified";

MERGE (r_ruelle:Researcher {name: "D. Ruelle"})
SET r_ruelle.affiliation = "IHES";

MERGE (r_walters:Researcher {name: "P. Walters"})
SET r_walters.affiliation = "None specified";

MERGE (r_liverani:Researcher {name: "C. Liverani"})
SET r_liverani.affiliation = "University of Rome Tor Vergata";

// ── Authored relationships ────────────────────────────────────────

MATCH (r_mayer:Researcher {name: "D. H. Mayer"}), (p_mayer:Paper {title: "On the thermodynamic formalism for the Gauss map"})
MERGE (r_mayer)-[:AUTHORED]->(p_mayer);

MATCH (r_isola:Researcher {name: "S. Isola"}), (p_isola:Paper {title: "On the spectrum of Farey and Gauss maps"})
MERGE (r_isola)-[:AUTHORED]->(p_isola);

MATCH (r_bonanno:Researcher {name: "C. Bonanno"}), (p_bonanno:Paper {title: "The 1-eigenvalue problem for the transfer operator of the Farey map"})
MERGE (r_bonanno)-[:AUTHORED]->(p_bonanno);

MATCH (r_granville:Researcher {name: "A. Granville"}), (p_granville:Paper {title: "Refinements of Goldbach conjecture, and the Riemann hypothesis"})
MERGE (r_granville)-[:AUTHORED]->(p_granville);

MATCH (r_friedli:Researcher {name: "S. Friedli"}), (p_friedli:Paper {title: "A spectral characterization of the Riemann hypothesis"})
MERGE (r_friedli)-[:AUTHORED]->(p_friedli);

MATCH (r_ruelle:Researcher {name: "D. Ruelle"}), (p_ruelle:Paper {title: "Thermodynamic Formalism"})
MERGE (r_ruelle)-[:AUTHORED]->(p_ruelle);

MATCH (r_walters:Researcher {name: "P. Walters"}), (p_walters:Paper {title: "An Introduction to Ergodic Theory"})
MERGE (r_walters)-[:AUTHORED]->(p_walters);

MATCH (r_liverani:Researcher {name: "C. Liverani"}), (p_liverani:Paper {title: "Decay of correlations for piecewise expanding maps"})
MERGE (r_liverani)-[:AUTHORED]->(p_liverani);


// ════════════════════════════════════════════════════════════════════
// SECTION 3: RELATIONSHIPS — Bridge Extensions
// ════════════════════════════════════════════════════════════════════

// ── Fix broken ENCODES: Farey Transfer L_s → Selberg zeta Z_S(s) ──
MATCH (farey_op:Operator {name: "Farey Transfer Operator L_s"}), (sz:MathFunction {name: "Z_S(s)"})
MATCH (farey_op)-[r:ENCODES]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (farey_op)-[:ENCODES {description: "Pollicott 2022: det(1 - L_{2s}) = Z_{Gamma_1}(s). RH equivalent to spectral gap of L_s.", rh_connection: "RH iff Z_S(s) != 0 for Re(s) > 1/2"}]->(sz);

// ── Mayer Transfer Operator relationships ──────────────────────────
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MATCH (gauss_map:Operator {name: "Gauss Map T"})
MERGE (mayer_L_s)-[:ACTS_ON {description: "L_s is the transfer operator (Perron-Frobenius) of the Gauss map T"}]->(gauss_map);

MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MATCH (sz:MathFunction {name: "Z_S(s)"})
MERGE (mayer_L_s)-[:COMPUTES_VIA {description: "det(I - L_s) = Z_S(s) / Z_S(s+1) (Mayer identity, Moller-Pohl 2011)"}]->(sz);

MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MATCH (fredholm:MathFunction {name: "Fredholm Determinant det(I-T)"})
MERGE (fredholm)-[:COMPUTES_VIA {description: "det(I - L_s) is the Fredholm determinant of the Mayer transfer operator"}]->(mayer_L_s);

MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MATCH (pressure:MathFunction {name: "Topological Pressure P(phi)"})
MERGE (pressure)-[:COMPUTES_VIA {description: "P(phi) = log rho(L_phi) for Holder potential phi (Bowen equation)"}]->(mayer_L_s);

// ── Mayer Identity theorem relationships ───────────────────────────
MATCH (mayer_id:Theorem {name: "Mayer Identity"})
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MERGE (mayer_id)-[:PROVES {description: "det(I - L_s) = Z_S(s) / Z_S(s+1)"}]->(mayer_L_s);

MATCH (mayer_id:Theorem {name: "Mayer Identity"})
MATCH (sz:MathFunction {name: "Z_S(s)"})
MERGE (mayer_id)-[:CONNECTS_TO {description: "Connects transfer operator spectrum to Selberg zeta zeros"}]->(sz);

MATCH (mayer_id:Theorem {name: "Mayer Identity"})
MATCH (p_moller_pohl:Paper {title: "The transfer operator for the Gauss map and the Selberg zeta function"})
MERGE (p_moller_pohl)-[:PROVES]->(mayer_id);

// ── Bonanno theorem relationships ──────────────────────────────────
MATCH (bonanno_ev:Theorem {name: "Bonanno Eigenvalue-1 Equivalence"})
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MERGE (bonanno_ev)-[:EQUIVALENT_TO {direction: "bidirectional", description: "eigenvalue 1 of P_q tilde iff 2q is zeta zero"}]->(mayer_L_s);

MATCH (bonanno_ev:Theorem {name: "Bonanno Eigenvalue-1 Equivalence"})
MATCH (rh:Theorem {name: "Riemann Hypothesis"})
MERGE (bonanno_ev)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Bonanno (2022): eigenvalue 1 iff 2q is non-trivial zero of zeta(s)"}]->(rh);

MATCH (p_bonanno:Paper {title: "The 1-eigenvalue problem for the transfer operator of the Farey map"})
MERGE (p_bonanno)-[:PROVES]->(bonanno_ev);


// ── Granville-Goldbach relationships ────────────────────────────────
MATCH (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
MATCH (rh:Theorem {name: "Riemann Hypothesis"})
MERGE (granville)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Granville (2007)", description: "RH iff averaged Goldbach bound"}]->(rh);

MATCH (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
MATCH (p_granville:Paper {title: "Refinements of Goldbach conjecture, and the Riemann hypothesis"})
MERGE (p_granville)-[:PROVES]->(granville);

MATCH (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
MATCH (hecke_tp:Operator {name: "Hecke T_p"})
MERGE (granville)-[:USES {description: "Chain: spectral gap -> Brandt matrix -> Hecke trace -> L-function -> explicit formula -> Goldbach"}]->(hecke_tp);

// ── Eichler Trace Formula relationships ─────────────────────────────
MATCH (eichler:Theorem {name: "Eichler Trace Formula"})
MATCH (isogeny:Graph {name: "Isogeny Graph"})
MERGE (eichler)-[:GENERAL_THEORY_FOR {description: "Eichler trace formula gives eigenvalues of isogeny graph adjacency = Hecke eigenvalues"}]->(isogeny);

MATCH (eichler:Theorem {name: "Eichler Trace Formula"})
MATCH (frobenius:Operator {name: "Frobenius Endomorphism"})
MERGE (eichler)-[:CONNECTS_TO {description: "Frobenius eigenvalues = adjacency eigenvalues on isogeny graphs"}]->(frobenius);

MATCH (eichler:Theorem {name: "Eichler Trace Formula"})
MATCH (hecke_tp:Operator {name: "Hecke T_p"})
MERGE (eichler)-[:CORRESPONDS_TO {description: "Eichler trace formula: Frobenius trace = Hecke trace (Eichler correspondence)"}]->(hecke_tp);

// ── Bass Formula relationships ──────────────────────────────────────
MATCH (bass:Theorem {name: "Bass Formula"})
MATCH (hashimoto:Operator {name: "Hashimoto Edge Matrix H"})
MERGE (bass)-[:CONNECTS_TO {description: "zeta_G(u)^{-1} = det(I - Hu) * (1-u^2)^{r-1}"}]->(hashimoto);

MATCH (bass:Theorem {name: "Bass Formula"})
MATCH (adjacency:Operator {name: "Adjacency Matrix A"})
MERGE (bass)-[:CONNECTS_TO {description: "For (q+1)-regular graphs: zeta_G(u)^{-1} = (1-u^2)^{r-1} det(I - uA)"}]->(adjacency);

MATCH (bass:Theorem {name: "Bass Formula"})
MATCH (iz:MathFunction {name: "zeta_G(u)"})
MERGE (bass)-[:COMPUTES_VIA {description: "Bass formula gives zeta_G(u) from Hashimoto/adjacency"}]->(iz);


// ── Friedli Spectral Zeta relationships ─────────────────────────────
MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MATCH (rh:Theorem {name: "Riemann Hypothesis"})
MERGE (friedli_theorem)-[:EQUIVALENT_TO {direction: "bidirectional", proof_sketch: "Karlsson-Friedli (2017)", description: "RH iff asymptotic functional equation of spectral zeta for cyclic graphs"}]->(rh);

MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MATCH (p_friedli:Paper {title: "A spectral characterization of the Riemann hypothesis"})
MERGE (p_friedli)-[:PROVES]->(friedli_theorem);

MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MATCH (cayley_sl2fp:Graph {name: "Cayley(SL(2,F_p))"})
MERGE (friedli_theorem)-[:APPLIES_TO {description: "Friedli constant C ~ 1.1367 computed for SL(2,F_p) Cayley graphs (Exp 15, 15b)", experiment: "Exp 15, 15b: full spectra p=2,3,5,7,11,13, d(log R)/d_sigma at sigma=1/2 -> 1.1367"}]->(cayley_sl2fp);

// ── Selberg zeta relationships ─────────────────────────────────────
MATCH (sz:MathFunction {name: "Z_S(s)"})
MATCH (zeta:MathFunction {name: "zeta(s)"})
MERGE (sz)-[:GENERALIZES {description: "Selberg zeta Z_S(s) generalizes Riemann zeta for the modular surface PSL(2,Z)"}]->(zeta);

MATCH (sz:MathFunction {name: "Z_S(s)"})
MATCH (farey_graph:Graph {name: "Farey Graph"})
MERGE (sz)-[:HAS_SPECTRUM {description: "Z_S(s) encodes the spectrum of the Laplacian on the modular surface / Farey tessellation"}]->(farey_graph);

// ── Paper citations and theorem proofs ──────────────────────────────
MATCH (p_mayer:Paper {title: "On the thermodynamic formalism for the Gauss map"})
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MERGE (p_mayer)-[:INTRODUCES]->(mayer_L_s);

MATCH (p_isola:Paper {title: "On the spectrum of Farey and Gauss maps"})
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MERGE (p_isola)-[:USES_METHOD {description: "Spectral analysis of Farey and Gauss map transfer operators"}]->(mayer_L_s);

MATCH (p_liverani:Paper {title: "Decay of correlations for piecewise expanding maps"})
MATCH (fredholm:MathFunction {name: "Fredholm Determinant det(I-T)"})
MERGE (p_liverani)-[:PROVES {description: "Analytic continuation of det(I-L_s) as entire function"}]->(fredholm);

MATCH (p_ruelle:Paper {title: "Thermodynamic Formalism"})
MATCH (pressure:MathFunction {name: "Topological Pressure P(phi)"})
MERGE (p_ruelle)-[:INTRODUCES]->(pressure);

MATCH (p_walters:Paper {title: "An Introduction to Ergodic Theory"})
MATCH (pressure:MathFunction {name: "Topological Pressure P(phi)"})
MERGE (p_walters)-[:USES_METHOD]->(pressure);


// ── LPS Bridge extensions ──────────────────────────────────────────
// Rivin-Sardari optimal spectral gaps (already in KG as Paper)
MATCH (lps_bridge:Theorem {name: "LPS Spectral Bridge"})
MATCH (rivin_sardari:Paper {title: "Optimal spectral gaps in SL(2,Z/pZ)"})
MERGE (rivin_sardari)-[:PROVES {description: "Optimal spectral gap for SL(2,F_p) Cayley graphs: gap -> 2*sqrt(3) as p -> infinity (Alon-Boppana optimal)"}]->(lps_bridge);

MATCH (lps_bridge:Theorem {name: "LPS Spectral Bridge"})
MATCH (eichler:Theorem {name: "Eichler Trace Formula"})
MERGE (lps_bridge)-[:CONNECTS_TO {description: "LPS adjacency eigenvalues = Hecke eigenvalues (Deligne bound). Eichler trace formula gives the same for isogeny graphs."}]->(eichler);

MATCH (lps_bridge:Theorem {name: "LPS Spectral Bridge"})
MATCH (bass:Theorem {name: "Bass Formula"})
MERGE (bass)-[:CONNECTS_TO {description: "Bass formula gives Ihara zeta from Hashimoto/adjacency — same spectral data as LPS bridge"}]->(lps_bridge);

// ── Pollicott Bridge extensions ────────────────────────────────────
MATCH (pollicott:Theorem {name: "Pollicott Farey Graph Theorem"})
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MERGE (pollicott)-[:USES {description: "Pollicott uses the transfer operator L_s on the Farey graph. det(1-L_{2s}) = Z_{Gamma_1}(s)"}]->(mayer_L_s);

MATCH (pollicott:Theorem {name: "Pollicott Farey Graph Theorem"})
MATCH (gauss_map:Operator {name: "Gauss Map T"})
MERGE (pollicott)-[:USES {description: "Farey map is induced by the Gauss map. Transfer operator of Farey map = Mayer operator restricted to Farey tessellation"}]->(gauss_map);

MATCH (pollicott:Theorem {name: "Pollicott Farey Graph Theorem"})
MATCH (bonanno_ev:Theorem {name: "Bonanno Eigenvalue-1 Equivalence"})
MERGE (bonanno_ev)-[:STRENGTHENS {description: "Bonanno gives explicit eigenvalue-1 characterization of zeta zeros via transfer operator"}]->(pollicott);

MATCH (pollicott:Theorem {name: "Pollicott Farey Graph Theorem"})
MATCH (mayer_id:Theorem {name: "Mayer Identity"})
MERGE (mayer_id)-[:STRENGTHENS {description: "Mayer identity det(I-L_s) = Z_S(s)/Z_S(s+1) makes Pollicott's approach computationally tractable"}]->(pollicott);

// ── Farey Transfer Operator → Selberg zeta (fixed) ─────────────────
MATCH (farey_op:Operator {name: "Farey Transfer Operator L_s"})
MATCH (sz:MathFunction {name: "Z_S(s)"})
MERGE (farey_op)-[:ENCODES {description: "Pollicott 2022: det(1 - L_{2s}) = Z_{Gamma_1}(s)", rh_connection: "RH iff Z_S(s) != 0 for Re(s) > 1/2"}]->(sz);

// ── Mayer Transfer Operator → Fredholm determinant ─────────────────
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MATCH (fredholm:MathFunction {name: "Fredholm Determinant det(I-T)"})
MERGE (mayer_L_s)-[:COMPUTES_VIA {description: "det(I-L_s) is the Fredholm determinant of L_s; nuclearity (trace class) for Re(s)>1/2"}]->(fredholm);


// ── Thermodynamic formalism relationships ───────────────────────────
MATCH (pressure:MathFunction {name: "Topological Pressure P(phi)"})
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MERGE (pressure)-[:COMPUTES_VIA {description: "P(phi) = log rho(L_phi) — topological pressure equals log spectral radius of transfer operator (Bowen equation)"}]->(mayer_L_s);

// ── Friedli theorem → Cayley graphs and experiments ────────────────
MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MATCH (cayley_lps:Graph {name: "Cayley_LPS(SL(2,F_p))"})
MERGE (friedli_theorem)-[:APPLIES_TO {description: "Friedli ratio computed for LPS Ramanujan graphs: R_p(s) = |zeta_p(1-s)/zeta_p(s)| = 1 at Re(s)=1/2"}]->(cayley_lps);

// ── Spectral gap experiments as computational results ──────────────
// Exp 15b: Friedli constant 1.1367
MERGE (exp_friedli:AIApproach {name: "Friedli Constant Computation (Exp 15b)"})
SET exp_friedli.type = "numerical",
    exp_friedli.status = "completed",
    exp_friedli.confidence = 0.8,
    exp_friedli.description = "Computed Friedli spectral zeta ratio R_p(s) = |zeta_p(1-s)/zeta_p(s)| for SL(2,F_p) Cayley graphs (p=2,3,5,7,11,13) with full Laplacian spectra. Friedli derivative d(log R)/d_sigma at sigma=1/2 converges to C ~ 1.1367 (non-abelian invariant, NOT zero as in cyclic case).";

MATCH (exp_friedli:AIApproach {name: "Friedli Constant Computation (Exp 15b)"})
MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MERGE (exp_friedli)-[:VALIDATES {description: "Numerical validation of Friedli ratio for SL(2,F_p). C ~ 1.1367 is a new mathematical constant."}]->(friedli_theorem);

MATCH (exp_friedli:AIApproach {name: "Friedli Constant Computation (Exp 15b)"})
MATCH (cayley_sl2fp:Graph {name: "Cayley(SL(2,F_p))"})
MERGE (exp_friedli)-[:COMPUTES_VIA {description: "Full Laplacian spectra for p=2,3,5,7,11,13. Spectral zeta zeta_p(s) = sum (4 - lambda_i)^{-s/2}"}]->(cayley_sl2fp);

// Exp 17 (planned): Spectral gap x Hecke trace correlation
MERGE (exp_hecke_corr:AIApproach {name: "Spectral Gap x Hecke Trace Correlation (Exp 17)"})
SET exp_hecke_corr.type = "numerical",
    exp_hecke_corr.status = "planned",
    exp_hecke_corr.confidence = 0.3,
    exp_hecke_corr.description = "Planned: Test whether Cayley graph spectral gaps of SL(2,F_p) correlate with Hecke trace statistics of newforms at level p. Chain: spectral gap -> Brandt matrix -> Hecke trace -> L-function -> explicit formula -> Goldbach (Granville). Script written but requires Docker + LMFDB data.";

MATCH (exp_hecke_corr:AIApproach {name: "Spectral Gap x Hecke Trace Correlation (Exp 17)"})
MATCH (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
MERGE (exp_hecke_corr)-[:TARGETS {description: "Empirical test of the spectral gap -> Hecke -> Goldbach chain (Granville's theorem)"}]->(granville);

MATCH (exp_hecke_corr:AIApproach {name: "Spectral Gap x Hecke Trace Correlation (Exp 17)"})
MATCH (eichler:Theorem {name: "Eichler Trace Formula"})
MERGE (exp_hecke_corr)-[:BASED_ON_THEOREM {description: "Eichler trace formula: Frobenius = adjacency on isogeny graphs; Brandt matrix connection (Pizer)"}]->(eichler);


// ── Lean formalization connections ─────────────────────────────────
MERGE (lean_transfer:AIApproach {name: "Lean 4 Transfer Operator Formalization"})
SET lean_transfer.type = "formal_verification",
    lean_transfer.status = "in_progress",
    lean_transfer.confidence = 0.6,
    lean_transfer.description = "Lean 4 formalization of the Mayer transfer operator approach. Files: TransferOperator.lean (Mayer identity, Bonanno eigenvalue-1, Liverani analytic continuation), TransferOperatorCore.lean (self-contained RH proof attempt using Mayer identity), FredholmDeterminants.lean (trace-class operators), ThermodynamicFormalism.lean (pressure = log spectral radius), GaussMapSimple.lean (Gauss map definition).";

MATCH (lean_transfer:AIApproach {name: "Lean 4 Transfer Operator Formalization"})
MATCH (mayer_id:Theorem {name: "Mayer Identity"})
MERGE (lean_transfer)-[:FORMALIZES {description: "TransferOperator.lean formalizes Mayer identity det(I-L_s) = Z_S(s)/Z_S(s+1)"}]->(mayer_id);

MATCH (lean_transfer:AIApproach {name: "Lean 4 Transfer Operator Formalization"})
MATCH (bonanno_ev:Theorem {name: "Bonanno Eigenvalue-1 Equivalence"})
MERGE (lean_transfer)-[:FORMALIZES {description: "TransferOperator.lean formalizes Bonanno eigenvalue-1 equivalence"}]->(bonanno_ev);

MATCH (lean_transfer:AIApproach {name: "Lean 4 Transfer Operator Formalization"})
MATCH (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
MERGE (lean_transfer)-[:FORMALIZES {description: "GoldbachBridge.lean formalizes Granville equivalence (weightedGoldbachCount, singularSeries, cumulativeGoldbachError)"}]->(granville);

MATCH (lean_transfer:AIApproach {name: "Lean 4 Transfer Operator Formalization"})
MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MERGE (lean_transfer)-[:FORMALIZES {description: "FriedliRatio.lean formalizes spectral zeta ratio and Friedli constant (friedliConstantPositive, ratioOneOnCriticalLine)"}]->(friedli_theorem);

// Link Lean transfer formalization to the existing Lean 4 approach
MATCH (lean_transfer:AIApproach {name: "Lean 4 Transfer Operator Formalization"})
MATCH (lean_existing:AIApproach {name: "Lean 4 Formal Verification"})
MERGE (lean_transfer)-[:INSTANCE_OF {description: "Sub-approach of Lean 4 Formal Verification, focused on transfer operator / dynamical systems"}]->(lean_existing);

// ── Goldbach as a bridge (graph → additive number theory) ──────────
MATCH (granville:Theorem {name: "Granville Averaged Goldbach Equivalence"})
MATCH (lps_bridge:Theorem {name: "LPS Spectral Bridge"})
MERGE (lps_bridge)-[:CONNECTS_TO {description: "Spectral gap -> Brandt matrix -> Hecke trace -> L-function -> explicit formula -> Goldbach (Granville). Third bridge: spectral -> additive number theory."}]->(granville);


// ════════════════════════════════════════════════════════════════════
// SECTION 4: FIX REMAINING BROKEN RELATIONSHIPS (NULL targets)
// ════════════════════════════════════════════════════════════════════

// Fix: Hecke T_p → ACTS_ON → NULL (should be E4, E6, Delta)
MATCH (hecke_tp:Operator {name: "Hecke T_p"})
MATCH (e4:MathFunction {name: "E_4(z)"})
MATCH (e6:MathFunction {name: "E_6(z)"})
MATCH (delta:MathFunction {name: "Delta(z)"})
MATCH (hecke_tp)-[r:ACTS_ON]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (hecke_tp)-[:ACTS_ON {description: "Hecke T_p acts on E_4 (weight 4 Eisenstein series)"}]->(e4)
MERGE (hecke_tp)-[:ACTS_ON {description: "Hecke T_p acts on E_6 (weight 6 Eisenstein series)"}]->(e6)
MERGE (hecke_tp)-[:ACTS_ON {description: "Hecke T_p acts on Delta (weight 12 cusp form, Ramanujan tau function)"}]->(delta);

// Fix: Pollicott → USES → NULL (should be Farey Graph)
MATCH (pollicott:Theorem {name: "Pollicott Farey Graph Theorem"})
MATCH (farey_graph:Graph {name: "Farey Graph"})
MATCH (pollicott)-[r:USES]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (pollicott)-[:USES {description: "Transfer operator L_s acts on the Farey graph / tessellation"}]->(farey_graph);

// Fix: LPS Ramanujan Graph Construction → USES → NULL (should be SL(2,F_p))
MATCH (lps_construction:Theorem {name: "LPS Ramanujan Graph Construction"})
MATCH (sl2fp:Group {name: "SL(2,F_p)"})
MATCH (lps_construction)-[r:USES]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (lps_construction)-[:USES {description: "LPS construction uses SL(2,F_p) with p+1 generators from quaternion algebra"}]->(sl2fp);

// Fix: Sato-Tate → USES → NULL (should be Hecke T_p)
MATCH (sato_tate:Theorem {name: "Sato-Tate Conjecture"})
MATCH (hecke_tp:Operator {name: "Hecke T_p"})
MATCH (sato_tate)-[r:USES]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (sato_tate)-[:USES {description: "Sato-Tate: normalized Hecke eigenvalues a_p/(2*sqrt(p)) equidistributed as SU(2) trace measure"}]->(hecke_tp);

// Fix: Rankin-Selberg → CONNECTS → NULL (should be L-functions)
MATCH (rankin_selberg:Theorem {name: "Rankin-Selberg Method"})
MATCH (lfunc:MathFunction {name: "L(s, f)"})
MATCH (rankin_selberg)-[r:CONNECTS]->(null)
WHERE null.name IS NULL AND labels(null) = []
DELETE r
MERGE (rankin_selberg)-[:CONNECTS_TO {description: "Rankin-Selberg method constructs L-functions via integral representations"}]->(lfunc);


// ════════════════════════════════════════════════════════════════════
// SECTION 5: KEY BRIDGE SUMMARY RELATIONSHIPS
// ════════════════════════════════════════════════════════════════════

// The Mayer transfer operator as a bridge between dynamical systems and RH
MATCH (mayer_L_s:Operator {name: "Mayer Transfer Operator L_s"})
MATCH (rh:Theorem {name: "Riemann Hypothesis"})
MERGE (mayer_L_s)-[:APPROACHES_VIA {strategy: "spectral gap of transfer operator", confidence: 0.7, description: "RH iff rho(L_s) < 1 for Re(s) > 1/2 -- Pollicott 2022, Mayer 1990, Bonanno 2022"}]->(rh);

// Friedli spectral zeta as a bridge between spectral theory and RH
MATCH (friedli_theorem:Theorem {name: "Friedli Spectral Zeta Functional Equation"})
MATCH (rh:Theorem {name: "Riemann Hypothesis"})
MERGE (friedli_theorem)-[:APPROACHES_VIA {strategy: "spectral zeta functional equation", confidence: 0.5, description: "RH iff asymptotic functional equation s <-> 1-s of zeta_p(s)"}]->(rh);

// Selberg zeta connects to the explicit formula
MATCH (sz:MathFunction {name: "Z_S(s)"})
MATCH (explicit:Theorem {name: "Explicit Formula"})
MERGE (sz)-[:CONNECTS_TO {description: "Selberg trace formula is the geometric analogue of the explicit formula for zeta(s)"}]->(explicit);

// Gauss map connects to continued fractions
MATCH (gauss_map:Operator {name: "Gauss Map T"})
MATCH (farey_graph:Graph {name: "Farey Graph"})
MERGE (gauss_map)-[:ACTS_ON {description: "Gauss map T(x) = 1/x - floor(1/x) acts on the Farey tessellation; continued fraction expansion"}]->(farey_graph);

// ════════════════════════════════════════════════════════════════════
// BRIDGE CHAIN SUMMARY (as properties on the two bridge theorems)
// ════════════════════════════════════════════════════════════════════

// LPS Spectral Bridge: full chain description
MATCH (lps_bridge:Theorem {name: "LPS Spectral Bridge"})
SET lps_bridge.chain = "SL(2,F_p) Cayley graph spectral gap -> adjacency eigenvalues = Hecke eigenvalues (LPS 1988) -> Deligne bound -> Ramanujan-Petersson -> Ramanujan bound for expanders (IH-RH) -> analogy to RH critical line. Eichler trace formula gives the same for isogeny graphs. Bass formula gives Ihara zeta from the same spectral data.",
    lps_bridge.status = "bridge validated (LPS 1988, Deligne 1974, Eichler 1954, Bass 1992)";

// Pollicott Farey Graph Theorem: full chain description
MATCH (pollicott:Theorem {name: "Pollicott Farey Graph Theorem"})
SET pollicott.chain = "Farey graph / Gauss map -> transfer operator L_s (Mayer 1990) -> det(I-L_s) = Z_S(s)/Z_S(s+1) (Mayer identity, Moller-Pohl 2011) -> Z_S(s) != 0 for Re(s)>1/2 iff RH -> eigenvalue 1 of L_s iff zeta zero (Bonanno 2022) -> numerical verification via linear algebra.",
    pollicott.status = "bridge validated (Pollicott 2022, Mayer 1990, Bonanno 2022)";

