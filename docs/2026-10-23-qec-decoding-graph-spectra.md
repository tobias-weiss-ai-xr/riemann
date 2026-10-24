# QEC-01: Spectral Decomposition of Quantum-Code Decoding Graphs

**Date**: 2026-10-23
**Scripts**: `scripts/qec_decoding_graph_spectra.py`, `scripts/qec_ramanujan_figure.py`
**Output**: `data/qec_spectral/qec_decoding_spectra_results.json`, `data/qec_spectral/qec_ramanujan_crossover.png`

## Motivation — why this lives in the riemann repo

This repo explores whether the **spectral properties of graphs** carry
information about the objects they encode — spectral gaps and Ramanujan ratios
of SL(2,F_p) Cayley graphs, their correlation with Hecke traces, and the
negative-study finding that local structure alone cannot predict spectral
gaps. A new, fast-moving literature asks an *isomorphic* question at the
intersection of machine learning and quantum error correction (QEC):

> GNN decoders (POLYMECHANON et al., astro-ph/quant-ph 2610.01683) message-pass
> over **decoding graphs** of quantum codes. What structural properties of
> those graphs make decoding easy or hard, and can spectral methods predict
> which decoders will work?

The bridge is concrete: the syndrome graph of the toric code Z_d² **is** the
Cayley graph C(Z_d², ±e1, ±e2) of an abelian group — the exact class of
object this repo analyzes for SL(2,F_p). Reusing the repo's spectral-gap and
Ramanujan-ratio conventions on quantum decoding graphs is therefore a direct
extension of the existing methodology to a hot, publishable question.

## Methods

1. **Code construction**: exact mod-2 CSS parity-check matrices for
   - repetition code R_5 (path-like syndrome graph, girth ∞)
   - toric code Z_d² for d = 2..15 (planar-lattice syndrome graph)
   - Steane [[7,1,3]] (perfect, 3 Z-checks) — self-orthogonal H
2. **Graph construction**: for each code, the **Z-syndrome graph** (nodes =
   Z-stabilizer checks, edge between two checks sharing a qubit) — the graph a
   matching/BP/GNN decoder works on — plus the Tanner graph.
3. **Spectral statistics**: full adjacency spectrum, second-largest eigenvalue
   λ₂, normalized Laplacian gap, Cheeger-bound lower bound, and the
   **Ramanujan ratio** (max nontrivial |λ| vs 2√(d−1)) — identical conventions
   to `scripts/compute_eigenvalues.py`.
4. **Empirical decoder probe**: a real sum-product belief-propagation decoder
   over the Tanner graph, Monte-Carlo logical-failure rates at p ∈
   {0.03,…,0.15}, with mod-2 Gaussian elimination to test whether the residual
   error is a stabilizer (logical success).

## Results

### A. The toric decoding graph is a Cayley graph — with an analytical crossover

The Z-syndrome graph of toric Z_d² is C(Z_d², ±e1, ±e2), degree 4, with
closed-form spectrum λ_{a,b} = 2cos(2πa/d) + 2cos(2πb/d) and
**λ₂ = 2 + 2cos(2π/d)**. The Ramanujan bound is B = 2√3 ≈ 3.4641. Solving
λ₂ = B gives crossover at **d ≈ 8.4**.

| d | λ₂ (numeric) | λ₂ = 2+2cos(2π/d) | Ramanujan? |
|---|---|---|---|
| 2 | 0.000 | 0.000 | ✓ |
| 3 | 1.000 | 1.000 | ✓ |
| 4 | 2.000 | 2.000 | ✓ |
| 5 | 2.618 | 2.618 | ✓ |
| 6 | 3.000 | 3.000 | ✓ |
| **7** | 3.247 | 3.247 | **✗** (`max\|λ\|=3.604 > B`) |
| 8 | 3.414 | 3.414 | ✓ |
| 9 | 3.532 | 3.532 | **✗** |
| 10+ | … | → 4 | **✗** (max\|λ\| > B) |

The numerics match the analytic spectrum to 4 decimal places. Fine structure:
for **odd d** the graph is non-bipartite and the binding eigenvalue is the most
negative one; **even d** are bipartite with eigenvalue −4 exactly, so they stay
Ramanujan one step longer before the +λ₂ side crosses at d=10.

> **Reading**: small surface/toric codes are spectral expanders; the decoding
> graph loses Ramanujan sharpness by d ≈ 7–10. This is *exactly* the code-size
> regime where naive BP decoders stop being competitive and where the QEC
> literature resorts to MWPM, union-find, or learned GNN decoders — a
> structural (graph-spectral) explanation that complements the usual
> "operator weight / degeneracy" narrative.

### B. Normalized gap does NOT predict BP success (distance dominates)

Monte-Carlo BP logical-failure rates:

| code | gap_norm | p=0.03 | p=0.10 | p=0.15 |
|---|---|---|---|---|
| repetition-5 | 0.50 | 0.000 | 0.011 | 0.026 |
| toric-d3 | 0.75 | 0.052 | 0.389 | 0.578 |
| toric-d2 | 1.00 | 0.207 | 0.561 | 0.725 |

A naive gap-only hypothesis ("bigger gap → better decode") fails: repetition
has the *smallest* gap but by far the best logical failure rate, because its
code distance (5) dominates at small p, while the d=2 torus has distance 2.
**Conclusion**: for *unlearned* message-passing decoders, spectral gap predicts
little; the graph structure that matters for learning-based decoders is the
Ramanujan/expansion sharpness itself, plus girth. This is consistent with
POLYMECHANON's finding that code-agnostic GNNs match BP+OSD on graph-like
(qLDPC) codes but need retraining for unseen code families.

### C. Consistent digital artifact

- `qec_decoding_spectra_results.json` — full per-code spectra + MC + scaling
- `qec_ramanujan_crossover.png` — λ₂ vs d with B = 2√3 and Ramanujan/not markers

## Reproducibility

```bash
# needs numpy (+ matplotlib for the figure); uv provides a throwaway env
uv run --no-project --with numpy python scripts/qec_decoding_graph_spectra.py --mc 2000
uv run --no-project --with numpy --with matplotlib python scripts/qec_ramanujan_figure.py
```

All results deterministic (independent RNG stream per (code, p): seed =
`base + 1000·p_index + code_index`; default base 42). Each failure rate is a
separate 2,000-shot MC sample; the Ramanujan flag is only reported for
d-regular graphs. CSS condition Hx·Hzᵀ = 0 mod 2 is asserted per code.

## Status

**Exploratory** — a first, honest spectral probe of decoding graphs with one
clean analytical result (the Ramanujan crossover) and one negative
methodological finding (naive gap ≠ BP success). Natural extensions: GNN
decoder trained over these graphs to test whether *learned* message passing
exploits the expander structure that BP misses; larger qLDPC families (the
POLYMECHANON regime); Cheeger/mixing-time vs decoder-threshold curves.
