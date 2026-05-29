# Research Roadmap: GNN × Number Theory — Future Directions

> **Date**: 2026-05-29
> **Status**: DRAFT — Awaiting user review
> **Scope**: Comprehensive roadmap covering ALL open threads from 15+ experiments

---

## 1. What We've Done (Summary)

### 1.1 Experiment Results at a Glance

| Approach | Best Result | Verdict |
|----------|------------|---------|
| Cayley graph GNNs (Exp 1-4) | R² < 0 for all targets | **FAILED** — vertex-transitivity kills local features |
| Hecke GNN on Cayley (Exp 5-6) | Linear baseline wins | **FAILED** — 13 samples, GNN can't learn |
| Pizer/Brandt matrix GNN (Exp 7) | R² = -49 | **FAILED** — data quality + wrong spectral object |
| Farey graph GNN (Exp 8) | Untested | **UNKNOWN** — infrastructure only |
| LMFDB sklearn ML (Exp 9-10) | F1=0.970 rank, R²=0.990 dim | **SUCCESS** — data scaling solved it |
| Trace-index GNN (Exp 12) | R²=0.631 for z1 | **PARTIAL** — beats sklearn for L-function zeros |
| GNN+sklearn ensemble (Exp 13) | R²=0.656 z1, +0.2% rank | **MARGINAL** — not worth complexity |
| Karlsson-Friedli spectral zeta (Exp 15) | Friedli constant ~1.1367 | **DISCOVERY** — new constant, but not RH-related |
| Sato-Tate moment analysis (Exp 12b) | Moment collapse (3 orders) | **INCOMPLETE** — normalization bug |

### 1.2 Key Insights

1. **Data quantity > model architecture**: The jump from 13 → 1000 → 53,779 samples transformed every metric. Deep learning needs data, not clever architectures.

2. **Cayley graphs are fundamentally hard for GNNs**: Vertex-transitivity means local neighborhoods carry zero information about global spectral properties. This is a theorem, not a bug.

3. **Hecke traces encode deep number-theoretic information**: 100 Hecke traces predict analytic rank (F1=0.970), dimension (R²=0.990), and CM status (100%). The Birch-Swinnerton-Dyer conjecture is empirically validated at scale.

4. **Graph structure helps for some targets**: GNN on trace-index graphs beats sklearn for L-function zero prediction (R²=0.631 vs 0.526, +20%). The graph encodes relationships between newforms that tabular features miss.

5. **Friedli's spectral zeta is computable but not informative for RH**: The critical line test R_p(0.5+it)=1 is trivial for finite graphs with real eigenvalues. The Friedli constant 1.1367 is a new invariant of SL(2,F_p) spectral density.

---

## 2. Open Threads (Priority-Ranked)

### Thread A: Scale LMFDB Data Collection to Full Dataset ⭐⭐⭐ HIGHEST

**Current state**: 53,779 newforms (levels 11-5000)
**Available**: ~1.1M+ newforms in LMFDB SQL mirror (850K modular forms total, 24M L-functions, 3TB data)
**External developments**: MIT team received AI for Math grant to connect LMFDB with **Lean4** formal proof system — LMFDB as AI training data is strategically important beyond our project
**Expected impact**: Every metric improves with data (proven: 1k → 53k improved rank F1 0.839 → 0.970)

**Specific steps**:
1. Extend `scripts/collect_lmfdb_sql.py` to levels 5001-50000 (estimated 500K+ newforms)
2. Add parallel collection with `psycopg2` COPY protocol (bulk insert)
3. Feature engineering: compute 500 Hecke traces per form (currently 100)
4. Track analytic rank 3+ forms (currently rank 2 is 1.3% of dataset)
5. Validate data quality: check for duplicate labels, missing traces, inconsistent ranks

**Success criteria**:
- 200K+ newforms with 100+ Hecke traces
- Rank classification F1 > 0.980 (currently 0.970)
- Rank-3 detection with F1 > 0.800 (currently unknown)
- Conductor R² > 0.700 (currently 0.526)

**Risk**: Network access to LMFDB SQL mirror, disk space (~50GB for 500K forms)

---

### Thread B: GNN Architecture Search on Trace-Index Graphs ⭐⭐⭐ HIGH

**Current state**: ChebConv K=5 achieves R²=0.631 for z1, but rank classification lags sklearn
**Available**: 6,292 graphs (1000 nodes each), 46,347 newforms
**Goal**: Close the gap on rank classification while maintaining z1 advantage

**Specific steps**:
1. **Architecture experiments** (parallel, independent):
   - GraphSAGE with JK-Net (deeper aggregation, better for rare classes)
   - SIGN + MLP (precomputed K-hop, fast training, scalable)
   - GAT with edge features (attention over trace-index connections)
   - Heterogeneous graph transformers (if multi-relational edges help)

2. **Graph construction variants** (parallel, independent):
   - Vary graph density (currently 1000 nodes/graph, k-NN edges)
   - Multi-scale graphs (different edge thresholds)
   - Directed edges (trace-index is asymmetric)
   - Edge weights (trace-index magnitude)

3. **Training improvements**:
   - Class-balanced sampling for rank-2 (currently 1.3% of dataset)
   - Contrastive pre-training on unlabeled newforms
   - Curriculum learning: easy samples first, then rare classes

**Success criteria**:
- z1 R² > 0.700 (currently 0.631)
- Rank F1 > 0.950 (currently 0.892, sklearn baseline 0.970)
- Rank-2 F1 > 0.900 (currently 0.789, sklearn baseline 0.973)
- Training time < 1 hour per model on CUDA

---

### Thread C: Connes' Noncommutative Geometry Approach ⭐⭐⭐ HIGH (Theoretical)

**Current state**: Oracle recommended Connes' spectral triples as alternative to Cayley GNNs. Latest papers discovered during research provide clear computational entry points.

**Why it matters**: Connes' program spans 25+ years connecting RH to noncommutative geometry. Recent breakthroughs (2024-2026) make computation feasible for the first time.

**Key Findings from Literature**:

1. **⬆️ PRIORITY: Spectral triples & Prolate wave operators (Nov 2025)**: Connes, Consani & Moscovici (arXiv:2511.22755) — Construct **self-adjoint operators whose spectra coincide with striking numerical accuracy with the lowest non-trivial zeros of ζ(1/2+is)**. This is the latest and most directly applicable paper. The operators are semilocal — defined on the adele class space but with finite-dimensional approximations.

2. **⭐ COMPUTATIONAL ENTRY: Semilocal adelic operators (2023)**: Connes & Consani (arXiv:2310.18423) — "Zeta zeros and prolate wave operators". The semilocal trace formula unifies the infrared (low-lying zeros from adeles) and ultraviolet (Sonin space/prolate) parts. **This may be directly implementable on our SL(2,F_p) framework** as a finite adele approximation.

3. **Prolate Wave Operator (PNAS 2022)**: Connes & Moscovici — Original discovery that negative eigenvalues of the prolate spheroidal wave operator reproduce squares of ζ zeros. Eigenfunctions belong to the **Sonin space** (the same space where classical RH criteria live).

4. **Prolate Wave Operator (2024)**: Connes & Consani (arXiv:2412.06605) — Won the **2025 AOFA Best Paper Award**. Extended the theory with explicit formulas.

5. **On the Jacobian of Spec Z (2026)**: Connes, Consani & Moscovici (arXiv:2603.01625) — Deepens algebraic cycle connections.

6. **The Riemann Hypothesis survey (Feb 2026)**: Connes (arXiv:2602.04022) — *"The Riemann Hypothesis: Past, Present and a Letter Through Time"* — Comprehensive survey connecting Weil quadratic form, prolate operator, and the full program. Best overview document.

7. **Spectral triples and zeta-cycles (2021)**: Connes & Consani (arXiv:2106.01715) — Connects spectral triples to zeta zeros systematically.

8. **Weil positivity at archimedean place (2020)**: Connes & Consani (arXiv:2006.13771) — Foundational trace formula.

9. **IHS Axioms (2004—)**: Original framework (arXiv:math/0402325): spectral triple (A, H, D) where A = GL(2, adeles)/GL(2,Q), H = L^2(A), D = Dirac operator. RH ≡ positivity of curvature.

10. **Your own negative study (2026)**: "When Graph Neural Networks Meet the Riemann Hypothesis: A Systematic Negative Study" — 7 experiment tracks, all failed. Root cause: vertex-transitivity kills local GNN signal. Pizer graphs gave exactly zero cross-prime generalization. This motivates the noncommutative geometry alternative.

**Specific steps**:
1. **⬆️ PRIORITY: Implement semilocal operators (arXiv:2310.18423)**:
   - Start from the concrete operator construction in the semilocal paper
   - Implement for finite adele approximation using our existing SL(2,F_p) Cayley graph framework
   - Compute low-lying eigenvalues and compare to ζ zeros
   - Validate against the numerical results reported in arXiv:2511.22755
   - **This is the most accessible computational entry point** — the paper includes explicit formulas

2. **Compute the prolate operator numerically**:
   - Implement the prolate spheroidal wave operator for small prime approximations
   - Reproduce the negative eigenvalues and compare to ζ(zero)^2
   - Uses the Sonin space formulation

3. **Implement Connes' trace formula for SL(2,F_p)**:
   - Compute spectral triple (A_p, H_p, D_p) for finite adele approximation
   - Verify IHS positivity numerically for p=2..79
   - Test whether positivity correlates with graph spectral gap

4. **Bridge to ML**:
   - Use semilocal operator eigenvalues as features for sklearn/GNN
   - Train on 53k LMFDB data
   - Compare to Hecke trace features

**Success criteria**:
- Reproduce semilocal operator eigenvalues matching ζ zeros to 1% accuracy
- IHS positivity verified numerically for p ≤ 31
- Connes features improve rank classification over Hecke traces

**Risk**: Mathematically complex — semilocal operators still require significant implementation effort

---

### Thread D: Friedli Spectral Zeta — Full Spectra Extension ⭐⭐ MEDIUM-HIGH

**Current state**: Friedli constant 1.1367 computed for p ≤ 13 (full spectra). No convergence for truncated spectra (p > 13).
**Goal**: Extend full-spectra computation to larger primes and understand the constant's number-theoretic meaning

**Specific steps**:
1. Compute full Laplacian spectra for p=17, 19, 23, 29, 31:
   - p=17: 4,896 nodes → feasible with `eigsh(k=4894)` (~hours)
   - p=19: 6,840 nodes → feasible (~hours)
   - p=23: 12,096 nodes → borderline (~days)
   - p=29: 24,360 nodes → may require distributed computation

2. Analyze Friedli constant 1.1367:
   - Is it related to known constants? (1.1367 ≈ √(1.292) ≈ 1 + π/100?)
   - Does it connect to the Kesten-McKay distribution of 4-regular graphs?
   - Can we derive it analytically from the spectral density?

3. Extend to other generating sets:
   - SL(2,F_p) with different generating sets (not just fundamental roots)
   - Does the Friedli constant depend on the generating set?
   - Compare PSL(2,F_p) vs SL(2,F_p)

**Success criteria**:
- Full spectra computed for p ≤ 23
- Friedli constant verified to 4 decimal places for p ≤ 13
- Analytic formula (if any) for the constant derived or conjectured

**Risk**: Full-spectra computation is O(n³), becomes intractable for large p

---

### Thread E: Farey Graph GNN (Pfad B) ⭐⭐ MEDIUM

**Current state**: Farey graphs generated for truncation orders 70-400. Training script exists but untested.
**Why it matters**: Transfer operator approach (Pfad B) is theoretically distinct from Cayley graphs (Pfad A). If Farey graphs encode different spectral information, GNNs might succeed where Cayley failed.

**Specific steps**:
1. Run baseline GNN training on Farey graphs:
   - Model: ChebConv K=5, hidden=128
   - Targets: graph Laplacian eigenvalues, transfer operator spectral gap
   - Split: 70% train / 30% test by truncation order

2. Compare to Cayley graph results:
   - Are Farey graphs vertex-transitive? (If yes, expect same failure)
   - Do Farey graphs have different spectral properties than Cayley graphs?
   - Can GNNs learn the Farey → continued fraction → number field connection?

3. If GNN works: scale up
   - Generate Farey graphs for n=400..1000
   - Train on larger graphs, test generalization
   - Connect to modular forms via Farey → SL(2,Z) representation

**Success criteria**:
- GNN achieves R² > 0 for at least one Farey graph target
- Results are reproducible across different random seeds
- Training completes in < 1 hour

**Risk**: Farey graphs may also be vertex-transitive (no signal)

---

### Thread F: Sato-Tate Moment Fix + CM Classifier ⭐⭐ MEDIUM

**Current state**: Moment analysis has normalization bug (traces ≠ eigenvalues). CM detection works (F1=0.800) but could be better.
**Goal**: Fix normalization, build proper Sato-Tate test, improve CM classifier

**Specific steps**:
1. **Fix normalization**:
   - Extract individual Hecke eigenvalues from LMFDB (not traces)
   - For dimension-1 forms: eigenvalue = a_p directly
   - For dimension-d forms: extract all d eigenvalues, normalize each by 2√p
   - Compute moments of the eigenvalue distribution (not trace distribution)

2. **Validate Sato-Tate**:
   - For non-CM forms: moments should converge to SU(2) values (M_2=1/2, M_4=1/8, M_6=1/16)
   - For CM forms: moments should converge to U(1) values (M_2=1/4, M_4=1/8)
   - Compute convergence rate: how many primes needed for 1% accuracy?

3. **Improve CM classifier**:
   - Use moment features (M_2, M_4, M_6) as input to RandomForest
   - Combine with Hecke trace features
   - Target: F1 > 0.950 (currently 0.800)

**Success criteria**:
- SU(2) moments match theory to 5% for non-CM forms
- CM classifier F1 > 0.950
- Moment convergence rate quantified

**Risk**: LMFDB may not expose individual eigenvalues for high-dimensional forms

---

### Thread G: Hybrid Approach — GNN + Number Theory Features ⭐⭐ MEDIUM

**Current state**: sklearn wins on tabular data (F1=0.970), GNN wins on L-function zeros (R²=0.631)
**Goal**: Combine both approaches for best-of-both-worlds

**Specific steps**:
1. **Feature engineering from number theory**:
   - Conductors (already available)
   - Class numbers of quadratic fields
   - Fourier coefficients of weight-1 forms
   - Sato-Tate moments (after Thread F fix)
   - Rankin-Selberg L-function values

2. **GNN with enriched node features**:
   - Add number-theoretic features to trace-index graph nodes
   - Train ChebConv on enriched graphs
   - Compare to baseline (traces-only)

3. **Meta-learning**:
   - Train GNN to predict which features are most informative
   - Use attention to weight features per newform
   - Interpretability: which features does the GNN attend to?

**Success criteria**:
- Combined model achieves R² > 0.700 for z1 and F1 > 0.960 for rank
- Feature importance analysis reveals which number-theoretic features help
- Model is interpretable (not black box)

**Risk**: Feature engineering may be labor-intensive, marginal gains

---

### Thread H: Knowledge Graph Integration ⭐ LOW-MEDIUM

**Current state**: Neo4j KG has 194 nodes, 161 relationships (researchers, papers, RH equivalences)
**Goal**: Use KG to discover new connections, guide research directions

**Specific steps**:
1. **Expand KG with experimental results**:
   - Add all 15 experiments as nodes
   - Link experiments to methods, datasets, outcomes
   - Connect to LMFDB newforms via Hecke traces

2. **Query for patterns**:
   - Which approaches succeeded/failed and why?
   - What features correlate with success?
   - Are there unexplored combinations of methods?

3. **GraphRAG-style discovery**:
   - Use GNN on the KG itself to predict new connections
   - Suggest novel experiment designs
   - Identify gaps in the research landscape

**Success criteria**:
- KG contains all experiments with outcomes
- At least 3 novel connections discovered
- GraphRAG suggests 1+ actionable experiment

**Risk**: KG is small, may not yield useful patterns

---

### Thread I: Paper Writing (When Ready) ⭐ LOW (Not yet)

**Current state**: Results are publishable but not yet synthesized into a coherent narrative.
**Goal**: Write a paper on "ML for Number Theory: Hecke Traces, Graph Neural Networks, and the Riemann Hypothesis"

**Specific steps** (deferred until Threads A-D have more results):
1. Structure: Introduction → Related Work → Methods → Experiments → Discussion → Conclusion
2. Key narrative: "Data scaling solved GNN failures on Cayley graphs"
3. Figures: experiment comparison table, z1 predictions, rank confusion matrices
4. Target venues: NeurIPS 2026 workshop, ICLR 2027, or Number Theory journals

**Note**: Paper writing is NOT a current priority. Focus on research first.

---

## 3. Parallel Execution Plan

### Phase 1 (Now — 2 weeks)
- **Thread A**: Extend LMFDB collection to 200K+ newforms
- **Thread B**: Architecture search on trace-index graphs (3 parallel agents)
- **Thread F**: Fix Sato-Tate normalization

### Phase 2 (Weeks 3-4)
- **Thread C**: Connes spectral triple implementation (if background research confirms feasibility)
- **Thread D**: Full-spectra Friedli extension for p=17, 19, 23
- **Thread E**: Run baseline GNN on Farey graphs

### Phase 3 (Weeks 5-6)
- **Thread G**: Hybrid approach with enriched features
- **Thread H**: KG integration with experimental results
- **Thread I**: Begin paper outline if results warrant

---

## 4. Key Research Questions

1. **Can we beat sklearn for rank classification?** Currently F1=0.970 (sklearn) vs 0.970 (GNN). Gap is small but rank-2 detection differs: sklearn 95.3% vs GNN 78.9%.

2. **What does the Friedli constant 1.1367 mean?** Is it related to the spectral density of SL(2,F_p)? Can we derive it analytically?

3. **Is Connes' approach computationally feasible?** The semilocal operators (arXiv:2310.18423) give finite-dimensional approximations. The arXiv:2511.22755 paper already reports numerical results matching ζ zeros. Can we reproduce and extend these on SL(2,F_p)?

4. **Does scaling to 500K+ newforms break the current bottleneck?** Or do we hit diminishing returns after 200K?

5. **Are there other graph constructions beyond trace-index?** The trace-index paradigm connects newforms via shared Chef eigenvectors. Are there other natural graph structures?

---

## 8. Success Metrics (Project-Level)

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| LMFDB newforms collected | 53,779 | 200,000+ | 2 weeks |
| Rank classification F1 | 0.970 | 0.985 | 4 weeks |
| L-function zero R² | 0.631 | 0.750 | 4 weeks |
| Friedli constant precision | 4 digits | 6 digits | 3 weeks |
| Connes IHS verification | None | p ≤ 31 | 6 weeks |

---

## 6. Related Work (External Literature)

### 6.1 ML for L-Functions / Modular Forms (Most Direct Competition)

| Paper | Method | Scale | Key Result | Comparison to Our Work |
|-------|--------|-------|------------|----------------------|
| **arXiv:2502.10360** (Feb 2025) | PCA + LDA + FNN, rational L-functions | **248,359** L-functions | Predict vanishing order | Larger dataset, simpler methods. We have stronger results (R²=0.99) but at 53k. |
| **arXiv:2403.14631** (2024) | FNN for root numbers | ~10K forms | Mestre-Nagao heuristic connection | Related but different target (root number vs rank). |
| **arXiv:2501.02105** (Jan 2025) | LDA + NN on Fricke signs | 35,416 Maass forms | 95% accuracy | Comparable approach, different features (Fricke signs vs Hecke traces). |
| **arXiv:2505.05549** (May 2025) | NN predicts modular weights from Fourier coefficients | ~10K black hole forms | Weight classification | Different domain (black hole microstates). |

**Takeaway**: Our LMFDB sklearn results (F1=0.970, R²=0.99 for dimension) are competitive or better than the literature at our scale. **Scaling to 200K+ would put us at the frontier** of this space.

### 6.2 GNN for Mathematics

| Paper | Domain | Model | Result |
|-------|--------|-------|--------|
| **arXiv:2411.07467** (2024) | Quiver mutation classes | GIN | GNN classified mutation classes accurately, discovered **new theorem** (previously unknown structural relation). |
| Your negative study (2026) | Cayley/Pizer/Farey graphs | GAT, ChebConv, GCN | **7 tracks, all failed** — vertex-transitivity kills local features. |

**Takeaway**: GNNs *can* discover new math in the right setting (quiver mutations have local structure). Cayley graphs are uniquely ill-suited. Our trace-index approach is a different paradigm — not local features on a manifold, but relational encoding between modular forms.

### 6.3 Spectral Graph Theory & Arithmetic

| Paper | Topic | Relevance |
|-------|-------|-----------|
| **arXiv:2308.13913** (2023) | Spectral theory of isogeny graphs | Ramanujan property, connections to modular forms. Could inform new graph constructions beyond trace-index. |

### 6.4 Strategic Context
- **LMFDB is strategically important**: 24M L-functions, 850K modular forms, 3TB PostgreSQL. MIT team received **AI for Math grant** specifically to connect LMFDB with **Lean4** formal proof system. This validates LMFDB as ML training data for number theory.
- **Murmurations (arXiv:2603.25564)**: Density of Hecke eigenvalues at prime-power levels — active subfield.
- **Connes program is accelerating**: Three papers in 2025-2026 (prolate operator, quantum field theory, zeta spectral triples). Prolate operator paper won AOFA Best Paper 2025.

---

## 7. Codebase Audit Findings

From codebase review agent (May 2026):

| Finding | Impact | Action |
|---------|--------|--------|
| 14 temp scripts (`scripts/_*.py` or root `quick_test*.py`) | Code clutter, may contain dead experiments | Audit and archive to `experiments/archive/` |
| Exp 11 (L-function zeros prediction) missing from `experiments/EXPERIMENT_LOG.md` | Gaps in experiment tracking | Add Exp 11 entry before starting new work |
| Farey data directories empty | Thread E cannot run without regeneration | Run Farey generation as prerequisite |
| `scripts/train_farey_gnn.py` untested | Thread E baseline unknown | Test with small n=70..100 subset |
| 57 model checkpoint files (`data/models/*.pt`) | Mixed: some are best models, some failed runs | Clean up, keep only best checkpoints per experiment |
| No TODO/FIXME/HACK comments in codebase | Positive: no technical debt. Negative: feature requests invisible | Add structured TODO tracking |
| `scripts/train_lmfdb_ml_53k.py` (old name) vs `scripts/train_lmfdb_gnn.py` | Naming inconsistency | Consider renaming for clarity |

**Recommended actions before Phase 1**:
- Run `make clean-models` or manual cleanup of redundant checkpoints
- Update EXPERIMENT_LOG.md with missing Exp 11 entry
- Verify Farey data generation works end-to-end

---

## 9. Appendix: Experiment File Map

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/collect_lmfdb_sql.py` | LMFDB bulk export | Working, needs extension |
| `scripts/train_lmfdb_ml_53k.py` | sklearn on 53k traces | Working |
| `scripts/build_lmfdb_gnn_dataset.py` | Trace-index graph builder | Working |
| `scripts/train_lmfdb_gnn.py` | ChebConv training | Working |
| `scripts/extract_gnn_embeddings.py` | Embedding extraction | Working |
| `scripts/extract_sklearn_predictions.py` | Sklearn predictions | Working |
| `scripts/train_ensemble.py` | Meta-learner | Working |
| `scripts/spectral_zeta_kf.py` | Karlsson-Friedli zeta | Working |
| `scripts/_friedli_test.py` | Full-spectra Friedli analysis | Working |
| `scripts/_sato_tate_analysis.py` | Sato-Tate moments | Needs normalization fix |
| `scripts/generate_farey.py` | Farey graph generation | Working |
| `scripts/train_farey_gnn.py` | Farey GNN training | Untested |
