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

## Important Constraints

- Graph sizes range from 6 nodes (p=2) to 1M+ nodes (p=101). Large graphs require GPU + `shm_size: 16gb`.
- Cayley graphs are vertex-transitive — local subgraph features carry zero information about global spectral properties. This is why local GNN approaches failed.
- The `funsearch/` directory is a separate git submodule (FunSearch for arithmetic function discovery). It has its own Dockerfile and dependencies.
- Root-level markdown files (DE): research notes and articles, not code. Do not modify without understanding the German-language context.
- No CI/CD pipelines exist. No pre-commit hooks. No lockfile for Python deps (requirements.txt only, pinned in Dockerfile).
