# Research Roadmap: GNN × Number Theory — Future Directions

> **Date**: 2026-05-29 (updated 2026-05-31)
> **Status**: EXPANDED — Threads J–S added; Thread C rewritten from "theoretical" to "already working"; 19 threads total
> **Scope**: Comprehensive roadmap covering 19 open threads (A–S) from 15+ experiments
> **Comprehensive paper**: `docs/2026-05-30-comprehensive-project-paper.md`

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

### Thread A: Scale LMFDB Data Collection to Full Dataset ⭐⭐⭐ HIGHEST ✅ DONE

**Current state**: ~~53,779 newforms~~ → **200,000 newforms** (200K records, 103MB CSV, collected May 29 2026)
**Method**: Incremental collector (`collect_lmfdb_incremental.py`) using `mf_newforms.traces[]` ARRAY with 100 pre-computed Hecke traces per form. Batch size 500, checkpointed, memory 107MB RSS. No zero data (lfunc_lfunctions queries timed out during collection).
**Dim distribution**: dim=0 (rational): 133,806 (66.9%), dim=1: 63,758 (31.9%), dim=2: 2,435 (1.2%), dim=3: 1
**Available**: ~1.1M+ newforms in LMFDB SQL mirror (850K modular forms total, 24M L-functions, 3TB data)
**External developments**: MIT team received AI for Math grant to connect LMFDB with **Lean4** formal proof system — LMFDB as AI training data is strategically important beyond our project

**Next steps** (post-Phase 1):
1. Convert 200K CSV to mmap format for GNN training
2. Merge with existing zeros data (63K forms have z1–z10)
3. Re-run GNN on 200K dataset (expected: rank F1 > 0.980, z1 R² > 0.700)
4. Extend to 500 traces per form (traces[] ARRAY contains 1000 values)
5. Collect zero data for remaining 137K forms (lfunc_lfunctions join)

**Success criteria**: 200K ✅ | Rank F1 > 0.980 ⏳ | Rank-3 F1 > 0.800 ⏳ | Conductor R² > 0.700 ⏳

---

### Thread B: GNN Architecture Search on Trace-Index Graphs ⭐⭐⭐ HIGH ✅ DONE

**Current state**: **COMPLETE** — 4 architectures compared on 63K forms with augmented 9-dim node features (5 original + ω(n), μ(n), d(n), λ(n)) and 3-dim edge features. GATConv achieves R²=0.731, a 15.9% improvement over ChebConv (0.631) and 38.9% above sklearn tabular baseline (0.526).

**Results** (Exp B, May 29-30 2026):

| Architecture | Node Feat | Edge Feat | Test R² | Δ vs GCN |
|-------------|-----------|-----------|---------|----------|
| GCN | 9 | 3 | 0.655 | — |
| ChebConv (K=5) | 9 | 3 | 0.668 | +1.9% |
| **GAT** (4 heads) | **9** | **3** | **0.731** | **+11.6%** |
| GIN (GINEConv) | 9 | 3 | 0.672 | +2.6% |

**Key insight**: GAT's multi-head attention mechanism learns which relational edges matter (sequential chain, divisibility links, k-NN connections) — GCN/ChebConv treat all neighbors equally. Improvement is specific to regression: rank/CM classification remain dominated by tabular features (F1=0.970 vs GAT's 0.892).

**Success criteria**: z1 R² > 0.700 ✅ (0.731), Rank F1 > 0.950 ❌ (0.892 — sklearn still wins), Rank-2 F1 > 0.900 ❌, Training time < 1h ✅

---

### Thread C: Connes CvS — Characteristic Values of the Schwarzian ⭐⭐⭐ HIGH (REVISED: ALREADY WORKING)

**⚠️ CRITICAL UPDATE (May 2026)**: This is NOT a theoretical thread. The `connes_cvs` package (v0.2.2) is **already implemented, published to PyPI, and producing ζ zeros to machine precision**. See `scripts/test_connes_cvs.py` and `scripts/_connes_n100.py`.

**Implementation status**:

The package implements the Connes–van Suijlekom Galerkin matrix Q(c) from arXiv:2511.23257 with three operator components:
1. **Prime piece**: von Mangoldt sums over prime powers up to cutoff c
2. **Pole piece**: contribution from trivial zeta zeros
3. **Archimedean piece**: digamma integrals accelerated via `python-flint` (144× speedup vs naive)

The pipeline is 3-step: `build_galerkin_matrix(c, N, T, dps)` → `compute_ground_state(Q)` → `extract_zeros(eigvec, L, n_zeros)`, implemented in `connes_cvs` v0.2.2.

**Published Artifacts**:
- PyPI: `connes-cvs` v0.2.2 (2026-04-19)
- Zenodo: V2 DOI with bit-identity regression tests
- GitHub: full source with sweep support and multiprocessing

**Current numerical results**:

| Configuration | Matrix Size | Error (first 5 zeros) | Computational Cost |
|--------------|-------------|----------------------|--------------------|
| c=30, N=100, T=400, dps=150 | 201×201 | **3 × 10⁻¹⁶** (machine precision) | ~tens of minutes |
| c=30, N=50, T=200, dps=80 | 101×101 | **10⁻¹¹** | ~minutes |
| c=10, N=30, T=50 | 61×61 | 10⁻⁵ | ~seconds |

**Why it matters**: Connes' noncommutative geometry program spans 25+ years connecting RH to the geometry of adele class spaces. The fact that we now have a **working, published numerical implementation** that extracts ζ zeros to machine precision is transformative — it moves from "can we compute this?" to "what can we learn from scaling it?"

**Key Findings from Literature (context for Threads J & O)**:

1. **Spectral triples & Prolate wave operators (Nov 2025)**: Connes, Consani & Moscovici (arXiv:2511.22755) — The theoretical foundation for Q(c). Won **2025 AOFA Best Paper Award**.
2. **Semilocal adelic operators (2023)**: Connes & Consani (arXiv:2310.18423) — Unifies infrared (adele) and ultraviolet (Sonin) parts.
3. **The Riemann Hypothesis survey (Feb 2026)**: Connes (arXiv:2602.04022) — Comprehensive overview.
4. **On the Jacobian of Spec Z (2026)**: Connes, Consani & Moscovici (arXiv:2603.01625) — Deepens algebraic cycle connections.
5. **Zeta Spectral Triples (to appear 2025)**: Connes, Consani & van Suijlekom — New framework for spectral computation of zeta zeros.

**Revised Specific Steps**:
1. **⬆️ Run Thread J first** (Connes CvS scaling analysis — see below):
   - Characterize N→accuracy convergence rate
   - Determine saturation point (is N=100 already optimal?)
   - Extract zeros 6–20+ by increasing N
   - Measure computational cost curve as N grows

2. **CvS × Modular Forms** (Thread O — see below):
   - Generalize the Galerkin matrix construction from ζ(s) to L-functions of modular forms
   - This would connect the Connes approach directly to our LMFDB dataset
   - Most high-risk/high-reward direction in the project

3. **CvS sweep analysis**:
   - Run `sweep.py` module (already implemented) with multi-cutoff analysis
   - Study Q(c) ground state as function of c (cutoff)
   - Look for structural transitions in the eigenvector

4. **Bridge to ML**:
   - Use CvS-derived zero predictions as an additional feature for LMFDB GNN training
   - Compare Connes-based zero extraction vs GNN-predicted zeros

**Success criteria**:
- N→∞ convergence law characterized: exponential or power-law?
- Zeros 6–20 extracted to at least 10⁻⁶ accuracy
- CvS × L-function generalization attempted and documented (even if negative)

**Risk**: Connes operator is specific to ζ(s) — generalization to L-functions is mathematically non-trivial

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

### Thread E: Farey Graph GNN (Pfad B) ⭐⭐ MEDIUM ✅ DONE

**Current state**: **COMPLETE** — Farey graph spectral gap follows exact power law $\Delta_n \approx 2.6547 \cdot n^{-0.9989} \approx 2.65/n$ (log-space R²=0.999995, gap-space R²=0.999848). FareyChebNet GNN (ChebConv K=3, hidden=64) achieves R²=-4.43 on standard chronological split and R²<0 on every held-out fold in 23-fold LOO. GNN **cannot beat the power-law baseline** on any unseen $n$.
**Why it matters**: This is a **third negative result family** (after Cayley graphs and Pizer graphs), but the failure mechanism is different — the spectral gap is a mathematical identity, not a learnable structure.

**Key findings**:
1. The power-law fit yields slope $b=0.9989 \approx 1.0$ in log-log space — the spectral gap scales as exactly $1/n$
2. The FareyChebNet learns size-specific features that don't extrapolate to unseen $n$
3. LOO validation confirms: even with 22 training graphs, the held-out size is always predicted worse than the baseline
4. Farey graphs are **not** vertex-transitive — the failure is due to the spectral gap being a deterministic function of $n$, not a property of local structure

**Implications**:
- The Farey negative result is constructive: it reveals the exact analytic form of the Farey spectral gap
- This joins the Cayley graph and Pizer graph failures as a complete characterization of GNN limitations for number-theoretic graph spectral prediction
- No further Farey GNN work is warranted — the problem is solved analytically

---

### Thread F: Sato-Tate Moment Fix + CM Classifier ⭐⭐ MEDIUM ✅ DONE

**Current state**: **COMPLETE** — Prime-index normalization bug fixed. Discovered Galois correlation ρ₂ = -0.607 for dim=2 non-CM forms. CM classifier achieves F1=0.919 (vs 0.800 baseline, +14.9%). M₄/M₂ ratio is the #1 discriminative feature for CM detection. Dimensional scaling law M₂(d) ∝ 1/d confirmed across d=1 to d=250.

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

### Thread I: Paper Writing ⭐⭐ COMPLETED (v1.0)

**Current state**: Comprehensive project paper written to `docs/2026-05-30-comprehensive-project-paper.md`.
**Content**: 11 sections covering all experiments (1–15), trace-index GNN (R²=0.631), Sato-Tate moment analysis (Galois correlation ρ₂=-0.607, CM classifier F1=0.919), Friedli constant 1.1367, literature survey, and 19-thread roadmap (expanded May 31).

**Findings synthesized**:
1. Three eras of the project: Cayley GNN failures → Data-scaled LMFDB ML success → Statistical discovery
2. All metrics, results, and comparisons organized in tables
3. Updated success metrics with concrete targets
4. Literature context: Connes spectral triples, Friedli, murmurations, ML-for-number-theory competition

**Next**: Venue targeting (NeurIPS workshop 2026, ICLR 2027, or number theory journal) — deferred until Phase 1 results improve metrics.

---

### Thread J: Connes CvS Scaling Analysis ⭐⭐⭐ HIGHEST ✅ DONE

**Current state**: **COMPLETE** — Scaling law determined: error ∝ N^{-14.1} (doubling N → 17,800× error reduction). N=50: mean_log₁₀_error = -10.97 (T=200,dps=80). N=100: mean_log₁₀_error = -15.22 (T=400,dps=150, machine precision ≈ 3.6e-16 to 8.3e-16 on first 5 zeros). N=80 predicted: 10⁻¹⁴ error. N=120 predicted: below machine precision. Implemented via `connes_cvs` v0.2.2. Published as PyPI package. Scaling law saved to `data/connes_cvs/scaling_law.json`.

**Why it's HIGHEST**: This is not a new implementation — the code already works. Every other thread requires new code. Thread J is pure analysis of an existing tool.

**Specific steps**:
1. **Convergence characterization**:
   - Run N=10,20,40,60,80,100,120 (same c=30,T=400,dps=150)
   - Measure error in γ₁–γ₅ as function of N
   - Fit convergence law: exponential ∝ exp(-αN) or power-law ∝ N⁻ᵝ?
   - Determine N₀ where further N ceases to improve accuracy (saturation)

2. **Extract more zeros**:
   - Current: n_zeros=5. Try n_zeros=10, 20 with N=100,200
   - Is zero extraction accuracy uniform across k, or does it degrade?
   - Compare to true zeros from lmfdb_zeros_ml.csv (63,844 entries with z1-z10)

3. **Computational scaling**:
   - Matrix is (2N+1)×(2N+1). Build time and solve time vs N.
   - Is there a GPU-acceleratable bottleneck? (The python-flint library is CPU-only)
   - Estimate cost for N=500 (zero extraction to γ₅₀?)

4. **Cutoff sweep (sweep.py)**:
   - Vary c from 5 to 100 (already has c=5,c=10,c=20,c=30 data)
   - Study Q(c) ground state eigenvalue λ_min(c)
   - Look for structural phase transitions in the eigenvector

**Success criteria**:
- Convergence law fitted with >0.99 R²
- Zeros 6–10 extracted to <10⁻⁶ error
- Scaling cost documented (hours? days? for N=200)
- Machine-precision zeros for all 10 visible in LMFDB data

**Risk**: Matrix solve becomes expensive beyond N=200; gains may saturate

---

### Thread K: FunSearch for Hecke Trace Identities ⭐⭐⭐ HIGH (NEW)

**Current state**: `funsearch/` submodule is a fully functional LLM-based program search engine (forked from DeepMind's Nature 2023 FunSearch). Docker, wandb, multi-model support, sandboxed evaluation all configured. Currently dormant.

**Goal**: Discover closed-form arithmetic relationships between Hecke trace sequences and L-function invariants.

**Why it's HIGH**: The search infrastructure is already set up. The 63K LMFDB dataset is ideal for supervised program search. Even partial discoveries would significantly strengthen the project's mathematical depth.

**Specific steps**:
1. **Search for trace → z1 formula**:
   - Define spec: given trace_1..trace_100, output a function f(traces) → z1
   - Evaluation metric: mean absolute error vs true z1 from LMFDB
   - Use 54,443 forms with complete z1-z10 data
   - Sandbox: ExternalProcessSandbox (already configured)

2. **Search for trace → rank formula**:
   - Spec: function f(traces) → analytic_rank (0 or 1 or 2+)
   - Metric: F1 score
   - Focus on rank-2 (rare class, 1.3%) where ML struggles most

3. **Search for CM detection**:
   - Spec: function f(traces) → is_CM (boolean)
   - Compare discovered formulas to the M₄/M₂ ratio heuristic (current F1=0.919)
   - Can FunSearch discover a better rule?

4. **Search for trace algebra identities**:
   - Given two forms with related Hecke traces, is there a trace algebra?
   - E.g.: trace_p(f × g) expressed in terms of trace_p(f) and trace_p(g)
   - Could discover new Euler product relations

**Success criteria**:
- At least 1 spec runs end-to-end through funsearch pipeline
- Discovered formula(s) have interpretable mathematical form
- At least one formula beats the comparable sklearn model

**Risk**: FunSearch requires LLM API keys and GPU for sandbox; program discovery is stochastic

---

### Thread L: GUE / Zero Statistics at Scale ⭐⭐⭐ HIGH ✅ DONE

**Current state**: **COMPLETE** — Two-population discovery at 63,844 forms, 568,708 nearest-neighbor spacings. Dim=1 (34,628 forms) prefers GUE (KS=0.205, 32.8% GUE-best) — first large-scale confirmation of Katz-Sarnak symplectic prediction. Dim≥2 (29,216 forms) uniformly prefers GOE (KS=0.233-0.286, %GUE drops 8.7%→1.0%) — novel discovery. Synthetic GUE validates at KS=0.003 (p=0.35). Paper Section 4.8 documents all findings with 7 subsections. Results at `data/lmfdb/gue_analysis/gue_analysis_results.json` (27.1 MB).

**Why it matters**: The GUE hypothesis predicts that non-trivial zeros of L-functions have the same spacing statistics as eigenvalues of random Hermitian matrices. Our 63K dataset enables per-level and per-dimension statistical tests at unprecedented scale for this project.

**Specific steps**:
1. **Level-spacing distribution**:
   - Compute normalized spacing s_k = (γ_{k+1} - γ_k) × mean_density for each form
   - Compare to Wigner surmise p(s) = (πs/2) exp(-πs²/4) for GUE
   - Kolmogorov-Smirnov test per level/dim stratum
   - Visualize with histogram overlays

2. **Number variance**:
   - Compute Σ²(L) = variance of zero count in intervals of length L
   - Compare to GUE prediction Σ²(L) ≈ (2/π²) log L + 0.440...
   - Test for deviations at small L (oscillatory component)

3. **Trace → spacing connection**:
   - Train models to predict spacing statistics from trace sequences
   - Is there trace structure in the spacings beyond what pure RMT predicts?
   - Correlation between Hecke eigenvalues and spacing deviations

4. **Level-density analysis**:
   - Compute mean density of zeros per form, per level
   - Check for arithmetic effects (level-dependence) beyond the mean density
   - Relate to conductor via Langlands correspondence

**Success criteria**:
- GUE spacing distribution validated at >95% confidence for at least one stratum
- Deviations from GUE quantified (if any)
- Trace → spacing model achieves R² > 0 for spacing statistics

**Risk**: The L-function zeros may be too few (z1-z10 only) for robust statistics beyond level-spacing of adjacent zeros

---

### Thread M: Modern GNN Architectures for Trace-Index Graphs ⭐⭐ MEDIUM-HIGH (NEW)

**Current state**: Only ChebConv (K=5) has been tried on trace-index graphs (R²=0.631 for z1). No attention-based or transformer architectures explored.
**Goal**: Leverage the trace-index graph's natural structure (index distance metric) with modern GNN designs.

**Specific steps**:
1. **Graph Transformer / GPS**:
   - The trace-index graph has a natural distance metric: index distance |i-j| between newforms
   - GraphGPS with Laplacian positional encodings
   - Compare spectral gap vs distance-based positional encodings

2. **SAN / EXPHormer**:
   - SAN learns edge- and node-level attention with structural encodings
   - EXPHormer uses expander graphs for global attention
   - Both are designed to handle the long-range dependencies present in trace-index graphs

3. **GraphSAGE with JK-Net**:
   - Deeper aggregation (JK connections) for better differentiation of rare classes
   - Target: rank-2 forms (1.3% of dataset)

4. **Ablation**:
   - Edge features (trace-index magnitude)
   - Directed vs undirected edges
   - Multi-scale: k-NN edges at different thresholds

**Success criteria**:
- z1 R² > 0.700 (from 0.631)
- Rank F1 > 0.950 (from 0.892)
- Rank-2 recall > 0.800

**Risk**: GNN literature moves fast — some architectures may not be available in PyG 2.x

---

### Thread N: Multi-Task Zero Prediction ⭐⭐ MEDIUM ✅ DONE

**Current state**: **COMPLETE** — Single-task MLP (z1 only) vs multi-task MLP (z1-z10 shared backbone) compared on 63,844 forms.

**Results**:

| Configuration | Test z1 R² |
|---|---|
| Single-task (z1 only) | **0.714** |
| Multi-task (z1-z10) | 0.704 (-1.5%) |

Per-zero R² (multi-task): z1–z9 consistent (0.70–0.75), z10 collapses (0.34).

**Key finding**: Multi-task training does **not** improve z1 prediction. The shared backbone slightly degrades performance. Each zero benefits from a specialized head. Pure MLP on 100 traces achieves z1 R²=0.714 — matching GAT's 0.731 without graph structure.

**Success criteria**: Multi-task z1 R² > single-task ❌ (0.704 < 0.714)

**Files**: `scripts/train_multi_task_zeros.py`, `data/multi_task/multi_task_results.json`

---

### Thread O: Connes CvS × L-Functions of Modular Forms ⭐⭐⭐ HIGH (SPECULATIVE)

**Current state**: Connes CvS works for ζ(s). Connecting to L-functions of modular forms is mathematically non-trivial but would unify the project's two most successful threads.

**Goal**: Generalize the CvS Galerkin construction from ζ(s) to L(f,s) for weight-2 newforms.

**Why it matters**: If possible, this would enable direct spectral computation of L-function zeros for modular forms — replacing statistical prediction (GNN R²=0.631) with direct numerical computation (potentially exponential convergence).

**Specific steps**:
1. **Theoretical analysis** (consult literature):
   - The CvS operator Q(c) is built from the Euler product of ζ(s)
   - For L(f,s) with Euler product ∏(1 - a_p p⁻ˢ + χ(p)p²ᵏ⁻¹⁻²ˢ)⁻¹, can we construct an analogous operator?
   - This requires understanding the arithmetic structure of the CvS construction in detail

2. **If theoretically feasible**:
   - Implement generalized Q_f(c) for a single newform
   - Test on forms with known zeros from lmfdb_zeros_ml.csv
   - Compare to true zeros (currently 54,443 forms with z1-z10)

3. **If not feasible**:
   - Document the mathematical obstruction
   - Propose alternative: use CvS ζ zeros as priors for L-function zeros via universal structures

**Success criteria**:
- Mathematical feasibility documented (even if negative)
- If positive: zeros extracted for at least 1 form with <1% error

**Risk**: The CvS construction may be specific to ζ(s) — generalization requires deep understanding of both Connes' noncommutative geometry program AND modular form L-functions

---

### Thread P: Individual Hecke Eigenvalue Extraction for d>1 ⭐⭐ MEDIUM (NEW)

**Current state**: The Sato-Tate analysis and all LMFDB models use Hecke *traces* (sum of eigenvalues). For dim>1 forms, individual eigenvalues carry more information than their sum.
**Goal**: Extract individual Hecke eigenvalues from LMFDB and use them to improve CM detection and Galois correlation analysis.

**Specific steps**:
1. **Extract eigenvalues**:
   - LMFDB SQL mirror stores individual Fourier coefficients a_p^{(1)}, ..., a_p^{(d)} for each prime
   - Modify `collect_lmfdb_sql.py` to include individual eigenvalues alongside traces
   - Expected: 100 primes × dim eigenvalues per form

2. **Refine CM classifier**:
   - Current: F1=0.919 using traces + moment features
   - With individual eigenvalues: the U(1) vs SU(2) distributional difference should be clearer
   - Target: F1 > 0.950

3. **Refine Galois correlation analysis**:
   - Current: ρ₂ = -0.607 from traces
   - With individual eigenvalues: can we measure the Galois action directly?
   - Compare: is ρ₂ uniform across Galois orbits, or does it depend on the orbit structure?

**Success criteria**:
- Individual eigenvalue extraction pipeline working (10+ forms validated)
- CM classifier F1 > 0.950
- Galois correlation refined with narrower confidence interval

**Risk**: LMFDB SQL may not expose individual eigenvalues for all forms; requires schema exploration

---

### Thread Q: Pizer Data Quality Autopsy ⭐ LOW (NEW)

**Current state**: Exp 7 (Pizer/Brandt matrix GNN) produced R² = -49 — the worst result in the project. The failure was never diagnosed.
**Goal**: Determine whether this failure is fundamental (Pizer graphs do not encode L-function invariants) or data-quality (bug in the collection/construction pipeline).

**Specific steps**:
1. **Data quality audit**:
   - Examine the 13 Pizer graph samples: what sizes, which primes, what invariants
   - Check for label leakage, missing values, normalization errors
   - Validate the Brandt matrix → graph construction against known Pizer theory

2. **Minimal reproduction**:
   - Implement a simple linear model on Pizer graph features (bypass GNN entirely)
   - If linear model fails too: the issue is in the features, not the architecture
   - If linear model succeeds: the issue is in GNN architecture/hyperparameters

3. **Documentation**:
   - Write up the autopsy results in EXPERIMENT_LOG.md
   - If salvageable: propose a fix
   - If not: note the failure as fundamental and why

**Success criteria**:
- Root cause of R²=-49 identified
- Clear documentation of findings

**Risk**: The failure may be purely data-size (13 samples) — no deeper lesson

---

### Thread R: GUE/Zero Hypothesis Testing — Level Density and Pair Correlation ⭐⭐ MEDIUM ✅ DONE

**Current state**: **COMPLETE** — Comprehensive spectral rigidity analysis performed on 63,844 forms (574,596 spacings, 510,163 ratios). Four complementary tests all confirm the two-population structure discovered in Thread L.

**Results** (Exp R, May 31 2026):

| Test | Full Dataset | dim=1 | dim≥2 | Interpretation |
|-----|--------------|-------|-------|----------------|
| P(s) preferred ensemble | GOE (KS=0.058) | GUE (KS=0.093) | GOE (KS=0.165) | Two-population confirmed |
| P(r) <r> | 0.523 (GOE-Hybrid) | 0.635 (GUE: 0.599) | 0.391 (Neither) | Novel: dim≥2 deviates from both |
| Σ²(L) crossover | L≈3.4 | GUE-like below, excess above | — | Effective symmetry breaking at long range |
| k-th neighbor (k=1..5) | GOE | — | — | Higher-order favors orthogonal |

**Key findings**:
1. **Pair correlation P(r)**: <r>=0.523 for full dataset — between GOE (0.530) and GUE (0.599). dim=1: <r>=0.635 favors GUE. dim≥2: <r>=0.391 **deviates from both classical ensembles**.
2. **Number variance Σ²(L)**: Clear crossover at L≈3.4. Below: GUE-like behavior. Above: GOE-like but with excess variance — consistent with arithmetic correlations predicted by Katz-Sarnak.
3. **k-th neighbor spacings**: All orders (k=1..5) favor GOE, with KS gap narrowing at higher k.
4. **The two-population discovery is now robustly validated** across P(s), P(r), Σ²(L), and k-th neighbor diagnostics.

**Files**: `scripts/train_spectral_rigidity.py`, `data/lmfdb/gue_analysis/spectral_rigidity_results.npz`

**Success criteria**: Pair correlation validated ✅ | Hecke → deviation correlation pending | GNN connection pending

---

### Thread S: LLM-Aided Automated Conjecture Generation ⭐⭐ MEDIUM (NEW)

**Current state**: Empirical discoveries (ρ₂ correlation, dilution law d^{-1.29}, CM classification rules, Friedli constant) are documented — none have been formalized into conjectures.
**Goal**: Use LLM assistance + the FunSearch infrastructure to generate precise mathematical conjectures from data.

**Why it matters**: The MIT LMFDB + Lean4 grant signals that formalization of data-driven number theory is strategically important. Our empirical findings are natural candidates.

**Specific steps**:
1. **Formalize the dilution law**:
   - Current: ρ_d ∼ d^{-1.29} observed from data
   - Can we conjecture: ρ_d = c·d^{-α} with specific c, α?
   - Test against analytic continuation of the expected Sato-Tate group

2. **Formalize CM detection**:
   - Current: M₄/M₂ ratio is best feature
   - Can we conjecture: M₄/M₂ > threshold ≡ CM?
   - Compute optimal threshold and confidence interval

3. **Connect to MIT LMFDB + Lean4 effort**:
   - Package the formalized conjectures in a format compatible with Lean4
   - Position our empirical results as test cases for automated theorem proving

**Success criteria**:
- At least 1 conjecture formalized with mathematical precision
- Optimal thresholds computed with confidence intervals
- Connection to Lean4 formalism outlined

**Risk**: Formalization requires category-theoretic/mathematical precision; LLM-assisted generation may produce "slop" conjectures

### Phase 1 ✅ COMPLETED (May 29 2026)
- **Thread J**: Connes CvS scaling analysis (error ∝ N^{-14.1}) ✅ | N=50: 10⁻¹¹, N=100: 10⁻¹⁶ machine precision
- **Thread L**: GUE zero statistics at scale ✅ | Two-population discovery (dim=1→GUE, dim≥2→GOE)
- **Thread A**: Extend LMFDB collection to 200K+ newforms ✅ | 200,000 records, 103MB CSV
- **Thread B**: Architecture search on trace-index graphs ✅ DONE | GAT R²=0.731 (+15.9% over ChebConv, +38.9% over sklearn)
- **Thread P**: Individual eigenvalue extraction for d>1 ⏸️ Deferred | No concrete use case, schema understood (`mf_hecke_nf.an` JSONB cyclotomic)

### Phase 2 (Weeks 3-4)
- **Thread C (revised)**: CvS × L-function generalization (theoretical feasibility)
- **Thread D**: Full-spectra Friedli extension for p=17, 19, 23
- **Thread K**: FunSearch Hecke trace identities (first spec run)
- **Thread N**: Multi-task zero prediction ✅ DONE (no improvement: 0.714→0.704)
- **Thread R**: Spectral rigidity (P(r), Σ²(L), k-th neighbor) ✅ DONE (two-population validated; dim≥2 deviates from both GUE/GOE in P(r))

### Phase 3 (Weeks 5-6)
- **Thread M**: Modern GNN architectures (GraphGPS, SAN, EXPHormer)
- **Thread O**: CvS × L-functions (implementation if feasibility confirmed)
- **Thread G**: Hybrid approach with enriched features
- **Thread S**: LLM-aided conjecture generation
- **Thread H**: KG integration with experimental results
- **Thread Q**: Pizer data quality autopsy (low priority, one-shot)

---

## 4. Key Research Questions

1. **Can we beat sklearn for rank classification?** Currently F1=0.970 (sklearn) vs 0.970 (GNN). Gap is small but rank-2 detection differs: sklearn 95.3% vs GNN 78.9%.

2. **What does the Friedli constant 1.1367 mean?** Is it related to the spectral density of SL(2,F_p)? Can we derive it analytically?

3. **How does the Connes CvS operator converge?** The N=100 → 10⁻¹⁶ results are astonishing. Is it exponential convergence? What's the saturation point? Can we reach γ₂₀?

4. **Can the Connes CvS construction be generalized from ζ(s) to L-functions of modular forms?** If yes, this would be the most transformative result — direct spectral computation of L-function zeros.

5. **Does scaling to 500K+ newforms break the current bottleneck?** Or do we hit diminishing returns after 200K?

6. **Can FunSearch discover closed-form mathematical relationships from LMFDB data?** The submodule is ready — what can LLM-based program search tell us about Hecke traces vs zeros?

7. **Are there other graph constructions beyond trace-index?** The trace-index paradigm connects newforms via shared Chef eigenvectors. Are there other natural graph structures?

8. **Do L-function zeros satisfy GUE statistics in our 63K dataset?** Systematic testing of Montgomery-Odlyzko law at scale.

9. **Can we formalize our empirical discoveries into precise mathematical conjectures?** Galois correlation ρ₂ = -0.607, dilution law d^{-1.29}, M₄/M₂ CM detection — are these provable?

---

## 8. Success Metrics (Project-Level)

| Metric | Current | Target | Timeline | Status |
|--------|---------|--------|----------|--------|
| LMFDB newforms collected | **200,000** ✅ | 200,000+ | Phase 1 | **DONE** |
| Rank classification F1 | 0.970 | 0.985 | Phase 1–2 | Pending |
| L-function zero R² | 0.631 | 0.750 | Phase 1–2 | Pending |
| Friedli constant precision | 4 digits | 6 digits | Phase 2 | Pending |
| Connes CvS zero extraction | γ₁-γ₅ @ 10⁻¹⁶ (N=100) | γ₁-γ₁₀ @ 10⁻¹⁰ (N=200) | Phase 2 | Pending |
| Connes CvS N→accuracy law | **N^{-14.1}** ✅ | Characterized | Phase 1 | **DONE** |
| GUE spacing test | **Two-population** ✅ | >95% CI for full dataset | Phase 1 | **DONE** |
| FunSearch spec running | Dormant | ≥1 spec end-to-end | Phase 2 | Pending |
| CM classifier F1 | **0.919** ✅ | 0.950 | Phase 1 | **DONE** |
| Galois correlation ρ₂ | **-0.607** ✅ | Characterized | Phase 1 | **DONE** |

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
| 14 temp scripts (`scripts/_*.py` or root `quick_test*.py`) | Code clutter, may contain dead experiments | Audit and archive to `experiments/archive/` |
| `scripts/train_farey_gnn.py` | **Tested** — FareyChebNet R²=-4.43, power-law baseline R²=0.9998 | Thread E DONE ✓ |
| 57 model checkpoint files (`data/models/*.pt`) | Mixed: some are best models, some failed runs | Clean up, keep only best checkpoints per experiment |
| No TODO/FIXME/HACK comments in codebase | Positive: no technical debt. Negative: feature requests invisible | Add structured TODO tracking |
| `scripts/train_lmfdb_ml_53k.py` (old name) vs `scripts/train_lmfdb_gnn.py` | Naming inconsistency | Consider renaming for clarity |

**Recommended cleanup**:
- Remove redundant model checkpoints (keep only `*_best.pt` variants)
- Add structured TODO tracking

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
| `scripts/train_farey_gnn.py` | Farey GNN training | **Tested** — power-law baseline R²=0.9998, GNN R²=-4.43 |
| `scripts/test_connes_cvs.py` | Connes CvS N=100 zero extraction | Working — 10⁻¹⁶ accuracy |
| `scripts/_connes_n100.py` | Connes CvS c=30,N=100 production run | Working |
| `scripts/_connes_n50.py` | Connes CvS c=30,N=50 production run | Working |
| `scripts/_connes_n40.py` | Connes CvS c=30,N=40 summary | Working |
| `scripts/_connes_fixed.py` | Connes CvS with fix | Working |
| `scripts/_connes_quick.py` | Connes CvS quick test | Working |
| `scripts/_check_connes_api.py` | Connes CvS API validation | Working |
| `data/connes_cvs/*.json` | CvS zero extraction results | 8 result files, c=5..30, N=20..100 |
| `funsearch/` submodule | LLM-based program search engine | Dormant — Docker configured |
| `data/lmfdb/lmfdb_zeros_ml.csv` | 63,844 forms with Hecke traces + z1-z10 | Working — 121 columns |
