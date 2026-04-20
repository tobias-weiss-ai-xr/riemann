# GNN × Number Theory Research

Research environment for exploring graph neural networks on Cayley graphs of SL(2,F_p) and connections to the Riemann Hypothesis.

## Quick Start

```bash
# Copy environment config
cp .env.example .env

# Start all services (research container + Neo4j)
docker compose up -d

# Load knowledge graph
docker compose exec research python /workspace/knowledge-graph/scripts/ingest.py --all

# Generate Cayley graphs
docker compose exec research python /workspace/scripts/generate_graphs.py --primes 2-101

# Compute eigenvalues
docker compose exec research python /workspace/scripts/compute_eigenvalues.py --all

# Train GNN
docker compose exec research python /workspace/scripts/train_gnn.py --epochs 100 --model gat
```

Or use the Makefile:

```bash
make up          # Start services
make ingest      # Load knowledge graph
make graphs      # Generate Cayley graphs
make eigenvalues # Compute eigenvalues
make train       # Train GNN
make eval        # Evaluate model
make paper       # Build paper from markdown
```

## Architecture

```
docker-compose.yml
├── research/     ← Main container (PyTorch, PyG, CayleyPy, Jupyter)
│   └── Dockerfile
├── neo4j/        ← Local knowledge graph
├── sagemath/     ← Optional (docker compose --profile sage up)
├── scripts/      ← Experiment code
├── knowledge-graph/
│   ├── cypher/   ← Neo4j seed scripts (00-06)
│   └── scripts/  ← Ingest + query utilities
├── data/
│   ├── cayley-graphs/   ← Generated .npz / .pt files
│   ├── eigenvalues/     ← Computed spectra
│   └── models/          ← Trained checkpoints
├── paper/        ← Markdown paper
└── notebooks/    ← Jupyter notebooks
```

## Knowledge Graph

The Neo4j knowledge graph encodes the full SL(2,Z) → ζ(s) theory chain:

| Node Types | Count | Examples |
|---|---|---|
| Group | 7 | SL(2,Z), PSL(2,F_p), Γ₀(N) |
| Graph | 7 | Cayley(SL(2,F_p)), Farey, Isogeny |
| MathFunction | 10 | ζ(s), L(s,f), Δ(z), ζ_G(u) |
| Operator | 7 | Hecke T_p, Adjacency, Transfer |
| Theorem | 15+ | RH, Deligne, LPS, Sato-Tate, Pollicott |
| Paper | 15+ | LPS 1988, Williamson 2021, Hayou 2023 |
| Researcher | 7 | Tao, Sarnak, Lubotzky, Williamson |
| AIApproach | 4 | GNN spectral, Lean 4, FunSearch, RMT+DL |

Key queries:

```python
from kg_queries import RiemannKG

kg = RiemannKG()
kg.rh_equivalence_class()        # All RH-equivalent statements
kg.graphs_to_zeta_bridges()      # Graph → ζ(s) bridge paths
kg.theory_chain_sl2z_to_zeta()   # Full mathematical chain
kg.ai_approaches_ranked()        # Approaches by confidence
kg.stats()                       # Node/relationship counts
kg.close()
```

## Services

| Service | URL | Description |
|---|---|---|
| Jupyter Lab | http://localhost:8888 | Research notebook |
| Neo4j Browser | http://localhost:7474 | Knowledge graph viewer |
| Neo4j Bolt | bolt://localhost:7687 | Python driver |
| TensorBoard | http://localhost:6006 | Training metrics |

## Experiment Pipeline

1. **Generate graphs**: `CayleyPy` → SL(2,F_p) Cayley graphs (4-regular)
2. **Compute spectra**: Sparse Lanczos → eigenvalue distribution
3. **Build dataset**: edges → PyG Data objects with spectral targets
4. **Train GNN**: GCN/GAT → predict spectral gap, Ramanujan ratio, cross-prime generalization
5. **Evaluate**: Compare against Ramanujan bound, RMT baselines, LPS theory

## Key References

- LPS 1988: Ramanujan graphs as Cayley graphs of PSL(2,F_q)
- Williamson 2021: GNN on Bruhat intervals (Nature)
- Pollicott 2022: RH as Farey graph transfer operator spectral gap
- Barlag 2024: GNNs ≡ Arithmetic circuits (NeurIPS)
- Hayou 2023: RH ≡ NN density via Nyman-Beurling
- Loeffler & Stoll 2025: ζ(s) formalized in Lean 4 / Mathlib

## Articles

| File | Content |
|---|---|
| `riemann-hypothese-report.md` | RH overview, Millennium Problems, Fields Medal (DE) |
| `ai-algorithmen-p-vs-np.md` | AI algorithm discoveries, P-vs-NP feasibility (DE) |
| `ki-und-riemann-hypothese.md` | AI approaches to RH (DE) |
| `gnn-zahlentheorie-riemann.md` | GNNs for number theory deep-dive (DE) |
