# AGENTS.md — GNN × Number Theory Research

## Environment

All work runs inside Docker. Do NOT install packages on the host.

```bash
cp .env.example .env          # First-time setup
docker compose up -d          # Start research container + Neo4j
make research                 # Shell into the research container
```

The `PYTHONPATH` inside the container includes `/workspace/scripts` and `/workspace/knowledge-graph/scripts` — import scripts directly (e.g., `from kg_queries import RiemannKG`).

## Key Commands (Makefile)

| Command | What it does |
|---|---|
| `make graphs` | Generate SL(2,F_p) Cayley graphs via CayleyPy |
| `make eigenvalues` | Sparse Lanczos eigenvalue computation |
| `make train` | Train GNN (GAT, spectral gap target) |
| `make eval` | Evaluate trained model |
| `make ingest` | Load full theory chain into Neo4j KG |
| `make paper` | Build paper from markdown |
| `make paper-pdf` | Build PDF via pandoc + xelatex |
| `make sage` | Optional SageMath (requires `--profile sage up` first) |

All `make` targets run inside the container via `docker compose exec`. Run scripts directly if already shelled in.

## Neo4j Port Mapping

The compose file maps Neo4j to **non-standard ports** to avoid conflicts:
- Browser: **7475** (not 7474)
- Bolt: **7688** (not 7687)

Inside the container, use `bolt://neo4j:7687`. From the host, use `bolt://localhost:7688`.

## Architecture

```
scripts/                    ← All experiment code (Python)
├── generate_graphs.py      ← CayleyPy → PyG Data objects
├── compute_eigenvalues.py  ← Sparse Lanczos → numpy spectra
├── train_gnn.py            ← GAT/GCN (Cayley graph spectral gap)
├── train_chebconv.py       ← ChebConv full-graph spectral gap
├── train_hecke_gnn.py      ← Hecke eigenvalue prediction
├── train_pizer_gnn.py      ← Pizer/Brandt matrix GNN
├── train_farey_gnn.py      ← Farey graph GNN (Pfad B, untested)
├── train_lmfdb_ml_53k.py   ← sklearn ML on 53k LMFDB newforms
├── train_lmfdb_zeros.py    ← L-function zeros prediction
├── collect_lmfdb_sql.py    ← LMFDB SQL mirror bulk export (psycopg2)
├── collect_lmfdb_zeros.py  ← L-function zeros extraction
└── augment_dataset.py      ← BFS subgraph extraction + features

knowledge-graph/
├── cypher/00-10            ← Neo4j seed scripts (run in order)
└── scripts/
    ├── ingest.py           ← Cypher loader (--all, --schema-only, --theory)
    └── kg_queries.py       ← RiemannKG query class

configs/default.yaml        ← Training hyperparameters
data/                       ← Generated data (gitignored, except .gitkeep files)
```

## Data Pipeline

1. `generate_graphs.py --primes 2-101` → `data/cayley-graphs/*.pt`
2. `compute_eigenvalues.py --all` → `data/eigenvalues/*.npy`
3. `augment_dataset.py` → `data/augmented/` (BFS subgraphs with 3-dim node features)
4. Training scripts read from `data/` dirs, write checkpoints to `data/models/`

## LMFDB Data Collection

Requires network access to `devmirror.lmfdb.xyz:5432` (PostgreSQL). Run from inside the container:

```bash
python scripts/collect_lmfdb_sql.py --test     # Verify connection
python scripts/collect_lmfdb_sql.py             # Full collection (53k+ forms)
```

Outputs: `data/lmfdb/lmfdb_sql_weight2_ml.csv` (ML-ready), `data/lmfdb/lmfdb_sql_weight2.json` (raw).

## Conventions

- **Language**: Python 3.11+ with `from __future__ import annotations`
- **Logging**: `loguru` (`from loguru import logger`), not stdlib `logging`
- **Args**: `argparse` for CLI scripts, `yaml` for config files
- **Formatting**: Ruff (configured in devcontainer). No separate ruff.toml — uses defaults.
- **Tests**: `pytest` (devcontainer configured for `scripts/` directory). Test files are ad-hoc exploration scripts prefixed `test_*`, not a formal test suite.
- **Temp scripts**: Root-level `quick_test*.py`, `run_*.sh`, `wait_*.py` are disposable (gitignored). `scripts/_*.py` are temp scripts inside the scripts dir.

## Experiment Log

`experiments/EXPERIMENT_LOG.md` contains the full history of 11 experiments with results, findings, and cross-experiment comparison. Read this before designing new experiments to avoid repeating failed approaches.

Key takeaway: GNNs on Cayley graphs consistently fail (R² < 0). sklearn on LMFDB Hecke traces succeeds (R² 0.73–0.99). Data quantity, not model architecture, was the bottleneck.

## Lean 4 Formalization Branch

A new research branch under `lean/` formalizes SL(2,F_p) Cayley graph spectral properties and their conjectured connections to the Riemann hypothesis using Lean 4 + mathlib.

### Directory Structure

```
lean/
├── lakefile.lean                 # Lean 4 project config (mathlib dependency)
├── lean-toolchain                # Lean toolchain pin
├── Main.lean                     # Entry point
├── Riemann/
│   ├── CayleyGraphs.lean         # SL(2,F_p) group + generators + Cayley graph
│   ├── SpectralGaps.lean         # Spectral gap, Cheeger inequality, certificates
│   ├── RamanujanProperty.lean    # p=3,5 are Ramanujan; p≥7 are not
│   ├── FriedliRatio.lean         # Spectral zeta functional equation ratio
│   ├── LMFDBConjectures.lean     # Formalized empirical conjectures from ML
│   ├── RiemannHypothesis.lean    # Bridge to mathlib's RiemannHypothesis
│   └── Certificates/             # Auto-generated eigenvalue data (by extract script)
├── scripts/
│   └── extract_lean_data.py      # Python → Lean certificate exporter
```

### How to Build

```bash
cd lean
lake update        # Download mathlib (first time, ~30 min)
lake build         # Compile — zero errors expected
```

From project root:
```bash
make lean-setup    # lake update
make lean-build    # lake build
make lean-eigenvalues  # Export Python data → Lean certificates
make lean-test    # Run #eval statements
```

### What Is Formalized

| File | Status | Contents |
|---|---|---|
| `CayleyGraphs.lean` | ✅ Done | SL(2,F_p) group, generators S,R, Cayley graph, regularity, vertex-transitivity |
| `SpectralGaps.lean` | ✅ Done | Spectral gap definition, certificate interface, Cheeger inequality, known values table |
| `RamanujanProperty.lean` | ✅ Done | p=3,p=5 Ramanujan theorems, ratio table, asymptotic conjecture |
| `FriedliRatio.lean` | 🟡 Partial | Spectral zeta ratio, Friedli constant 1.1367, functional equation on critical line |
| `LMFDBConjectures.lean` | 🟡 Partial | Hecke→rank conjecture, murmurations, zero statistics classification |
| `RiemannHypothesis.lean` | 🟡 Partial | RH restatement, Bridge A (LPS/Hecke→RH), Bridge B (Mayer→RH) |
| `Certificates/*.lean` | 🔵 Auto | Generated by `extract_lean_data.py` from Python pipeline data |

### Key Theorems

- `pThreeIsRamanujan` / `pFiveIsRamanujan` — p=3 and p=5 SL(2,F_p) Cayley graphs satisfy the Ramanujan bound `λ₂ ≤ 2√3`
- `cheegerInequality` — Cheeger constant lower bound for 4-regular graphs
- `rh_implies_zeros_on_line` — mathlib's `RiemannHypothesis` → all non-trivial zeros on Re(s)=1/2
- `BridgeAConjecture` — conditional: Ramanujan property at all primes → RH
- `friedliConstantPositive` — the Friedli derivative constant 1.1367 is positive

### Lean Development Workflow

1. Edit `.lean` files in `lean/Riemann/`
2. Run `lake build` to check compilation
3. For data-dependent statements, run `python scripts/extract_lean_data.py --primes 2-101` first
4. Use `native_decide` for finite computations (eigenvalue list comparisons, group order checks)

### Long-term Goals

1. Formalize the connection between Cayley graph spectral gaps and the Riemann hypothesis
2. Contribute SL(2,F_p) graph theory to mathlib
3. Formalize empirical discoveries from the ML pipeline (Friedli constant, murmurations)
4. Target the Hadamard product gap in mathlib (the single biggest obstruction to a full RH formalization)

### Connection to Docker

Lean 4 is installed on the host, not inside Docker. The `make lean-*` targets run on the host. The `extract_lean_data.py` script reads from `data/` (host-mapped) and writes to `lean/`.

## Important Constraints

- Graph sizes range from 6 nodes (p=2) to 1M+ nodes (p=101). Large graphs require GPU + `shm_size: 16gb`.
- Cayley graphs are vertex-transitive — local subgraph features carry zero information about global spectral properties. This is why local GNN approaches failed.
- The `funsearch/` directory is a separate git submodule (FunSearch for arithmetic function discovery). It has its own Dockerfile and dependencies.
- Root-level markdown files (DE): research notes and articles, not code. Do not modify without understanding the German-language context.
- No CI/CD pipelines exist. No pre-commit hooks. No lockfile for Python deps (requirements.txt only, pinned in Dockerfile).
- The `lean/` directory is outside Docker. Lean 4 toolchain must be installed on the host (see `leanlang.org`).
