# Riemann Knowledge Graph — Vollständiger Export

**Quelle**: Neo4j (bolt://localhost:7688), 142 relevante Knoten, 270 Beziehungen
**Rohdaten**: `kg_full_export.json` (216 Knoten inkl. 74 APOC-Test-Knoten: Company/PipelineStage/Activity/unlabeled — Testdaten, keine Forschung)

## Statistik (reale KG-Knoten)

| Label | Anzahl |
|---|---|
| Theorem | 49 |
| Paper | 34 |
| Researcher | 17 |
| Graph | 14 |
| MathFunction | 10 |
| Group | 7 |
| Operator | 7 |
| AIApproach | 4 |
| **Gesamt** | **142** |

Top-Beziehungen: EQUIVALENT_TO (13), AUTHORED (14), CITES (8), PROVES (7), GENERALIZES (5), IMPLIES (5), TARGETS (4)

## 1. RH-Äquivalenzklasse (Kern des KG)

**Direkt an RH gekoppelt (EQUIVALENT_TO)**: Robin (1984), Lagarias (2002), Lindelöf
**Weitere bewiesene Äquivalenzen**: Nyman-Beurling (1950), Weil-Positivität (1952), Bagchi (1982), Li (1998), Balazard-Saias-Yor (1999), Baez-Duarte (2002), von Koch (1901), Chebyshev ψ (1901), Franel-Landau (1926), Jensen-Polynom-Hyperbolizität (1927), Laguerre-Pólya (1927), Speiser (1934), Volchkov-Integral (1995), Bombieri-Variation (2000), Redheffer (1977), Horozyklen-Fluss (1990), Divisibilitäts-Graph (2017), Landau-Funktion (2019), de Bruijn-Newman Λ=0 (2020), Liouville-Grenze, lcm-Formulierung, Caveney-Nicolas-Sondow GA1/GA2 (2011)

**Offen/konjektural**: Hilbert-Pólya (offen, Yakaboylu 2023 teilweise), Nicolas (1983), Chowla/Möbius (offen)
**Widerlegt**: Mertens-Hypothese (Odlyzko & te Riele 1985 — war STÄRKER als RH)

## 2. Die Zwei Brücken: Graphen ↔ ζ(s)

1. **LPS-Brücke (1988)**: Adjazenz-Eigenwerte der Cayley-Graphen ≈ Hecke-Eigenwerte. Deligne-Bound |a_p| ≤ 2√p = Ramanujan-Bound |λ| ≤ 2√(d-1). Beide aus GL(2,Q_p)-Darstellungen.
2. **Pollicott-Brücke (2022)**: Farey-Transfer-Operator L_s, Z_Γ₁(s) = det(1 - L_{2s}). RH ≡ Spektrallücke von L_s.

## 3. Operator-Familie

Hecke T_p/T_n (hermitisch, kommutierend, multiplikativ), Adjazenz A, Hashimoto H (ζ_G(u)^{-1} = det(I-Hu)), Farey-Transfer L_s, Frobenius Frob_p (Isogenie-Graphen), Laplace Δ = dI - A.
Verbindungen: Adjazenz ↔ Hecke (LPS), Frobenius ↔ Adjazenz (Eichler-Spurformel), Δ ← A.

## 4. Gruppe → Graph → Funktion Kette

SL(2,Z) ← PSL(2,Z) (C₂*C₃); SL(2,F_p) | p(p²-1) und PSL(2,F_p) | p(p²-1)/2 als FINITE_ANALOGUE_OF; Γ₀(N), Γ₁(N) als HAS_SUBGROUP; GL(2) als CONTAINS SL(2,F_p) und SL(2,Z).
Graphen: Cayley(SL(2,F_p)) [CayleyPy, 4 Generatoren, NICHT garantiert Ramanujan], Cayley_LPS [Ramanujan bewiesen], Farey-Graph [Pollicott], Isogenie-Graphen [Eichler: Frobenius = Adjazenz], LPS-Familie {X^{p,q}} [(p+1)-regulär], Ihara-Graph [GENERAL_THEORY_FOR Cayley+Isogenie], p-adisch Cayley(SL(2,Q_p)).
Funktionen: ζ(s), ζ_G(u) (Ihara, ANALOGOUS_TO ζ_K), ζ_K(s) (GENERALIZES ζ), L(s,f), L(s,χ), L(s,E_k) (FACTOR_OF ζ), E₄, E₆, Δ(z) (Ramanujan τ).

## 5. Paper-Timeline (34)

**Fundament**: Riemann 1859, Deligne 1974 (Weil II), LPS 1988, Margulis 1988.
**Klassisch-surveymäßig**: Conrey 2003, Borwein 2008, Broughan 2017 (2 Bde, 100+ Äquivalenzen), Connes 2026 (Letter Through Time).
**Beweise**: Barnet-Lamb+ 2011 (Sato-Tate), Rodgers-Tao 2019 (Λ ≥ 0), Griffin-Ono-Rolen-Zagier 2019 (Jensen), Platt-Trudgian 2021 (RH bis 3·10¹²).
**ML/Deep-Learning**: Williamson/Davies+ 2021 (GNN Combinatorial Invariance), Hayou 2023 (NN-Dichte via Nyman-Beurling), Bieri+ 2025 (LMFDB 248k), Shanker 2024 (Transformer, 0.998 Acc), Wu+ 2025 (Falsifikation), Murmurations 2023, Barlag+ 2024 (GNN ↔ Arithmetik-Schaltkreise).
**Lean/Formalisierung**: Loeffler-Stoll 2025 (ζ in Lean 4, ~60-70% Maschinerie), Kontorovich-Tao 2025 (PNT+ via Wiener-Ikehara), AlphaProof 2024, Gemini Deep Think 2025, Aletheia 2026 (4 offene Erdős-Probleme).
**Graphen/Zahlen**: Codogni-Lido 2025 (Isogenie-Spektraltheorie), Rivin-Sardari 2019 (optimale Spektrallücken SL(2,F_p)), Platt 2017 (10¹³ Nullstellen), Helfgott 2015 (SL(2) Wachstum).
**Datenbank**: LMFDB 2024 (248k+ L-Funktionen), CayleyPy 2025 (NeurIPS Spotlight, ~200 Vermutungen).

## 6. Researcher (17)

Tao (UCLA), Sarnak (IAS), Lubotzky (Hebrew U), Williamson (Sydney/IAS), Keating (Oxford), Platt (Bristol), Loeffler (Warwick), Odlyzko (Minnesota), Kontorovich (Rutgers), Taylor (IAS), Harris (Columbia), Helfgott (Göttingen), Rivin (Temple), Sardari, Shanker, Charton, Kempe.

## 7. AI-Approaches (11) — mit eigener Bewertung

| Ansatz | Status | Confidence | Anmerkung |
|---|---|---|---|
| GNN Spectral Prediction | planned | 0.4 | Eigene Exp. 1–12: scheitert auf Cayley (R² < 0), funktioniert auf Trace-Index-Graphen (Exp 12: R² = 0.631) |
| Lean 4 Formal Verification | in_progress | 0.6 | Loeffler-Stoll ~60-70%; größte Lücke: Hadamard-Produkt (fehlt in mathlib) |
| FunSearch for NT | inconclusive | 0.2 | DeepMind selbst: "kein Grund" für Durchbruch bei P≠NP — ähnlich limitierend für RH |
| RMT + Deep Learning | exploratory | 0.25 | Keating cross-pollination Idee; wenig konkret |
| Lean 4 Transfer Operator Formalization | in_progress | 0.6 | Exp-19-Linie: Mayer L_s, Fredholm-Determinante, Transferoperator-Formalisierung |
| Friedli Constant Computation (Exp 15b) | completed | 0.8 | Karlsson-Friedli-Slope ≈ 1.1367 auf SL(2,F_p)-Cayley-Graphen |
| Pizer-Brandt Bridge Verification (Exp 18) | completed | 0.85 | Isogeny-Graph-Spektrum aus LMFDB-Hecke-Eigenwerten: RAMANUJAN bestätigt, 0 Verletzungen (q=2..29) |
| Hecke Murmurations Level Aspect (Exp 20) | completed | 0.7 | Rank-2-Formen systematisch unter Rank-0: Separationssignal stabil in 6/6 Primzahlen |
| Spectral Gap x Hecke Trace Correlation (Exp 17/21) | completed | 0.6 | NULL: Cayley- vs. Isogeny-Lücke statistisch unabhängig (spearman +0.22 p=0.40) — Bridges strukturell, nicht eigenwert-isomorph |
| EPIC-4 High-t Strand Pinning (Exp 19m) | completed | 0.75 | Hoch-t-Plateau t=900–1200 gepinnt (Nullstelle #731, t=1100.574), Eigenwert-1-Kriechen zur kritischen Linie (σ*≈0.50), m≥0.015 |
| Cayley vs Isogeny Cross-Bridge Test (Exp 21) | completed | 0.8 | Siehe Exp 17/21 |

## 8. Implikationen (IMPLIES-Beziehungen)

- PNT → RH (schwach: PNT folgt aus ζ ≠ 0 auf Re(s) = 1)
- Hilbert-Pólya → RH (falls selbstadjungierter Operator existiert)
- Mertens → RH (aber Mertens FALSCH)
- Chowla → PNT (nicht äquivalent zu RH)
- von Koch → Chebyshev ψ
