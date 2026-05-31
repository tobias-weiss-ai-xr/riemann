.PHONY: help up down build research neo4j ingest logs clean train eval paper

# ── Defaults ─────────────────────────────────────────────────────
DOCKER_COMPOSE := docker compose
RESEARCH_CONTAINER := riemann-research

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Lifecycle ────────────────────────────────────────────────────
up: ## Start all services (research + neo4j)
	$(DOCKER_COMPOSE) up -d

down: ## Stop all services
	$(DOCKER_COMPOSE) down

build: ## Build research container
	$(DOCKER_COMPOSE) build research

restart: down up ## Restart all services

# ── Shells ───────────────────────────────────────────────────────
research: ## Shell into research container
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) bash

jupyter: ## Start Jupyter Lab
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) jupyter lab --ip=0.0.0.0 --no-browser --port=8888

# ── Knowledge Graph ──────────────────────────────────────────────
neo4j: ## Open Neo4j Browser (http://localhost:7474)
	@echo "Opening Neo4j Browser at http://localhost:7474"
	@echo "  User: neo4j"
	@echo "  Pass: $$(grep NEO4J_PASSWORD .env 2>/dev/null | cut -d= -f2 || echo 'riemann-research')"

ingest: ## Ingest theory into knowledge graph
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/knowledge-graph/scripts/ingest.py --all

ingest-schema: ## Load KG schema only
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/knowledge-graph/scripts/ingest.py --schema-only

ingest-theory: ## Load full theory chain
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/knowledge-graph/scripts/ingest.py --theory

cypher-shell: ## Open Cypher shell
	$(DOCKER_COMPOSE) exec neo4j cypher-shell -u neo4j -p $$(grep NEO4J_PASSWORD .env 2>/dev/null | cut -d= -f2 || echo 'riemann-research')

# ── Experiments ──────────────────────────────────────────────────
graphs: ## Generate Cayley graphs for SL(2,F_p)
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/scripts/generate_graphs.py --primes 2-101

eigenvalues: ## Compute eigenvalues for generated graphs
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/scripts/compute_eigenvalues.py --all

train: ## Train GNN model
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/scripts/train_gnn.py --model gat --target spectral_gap --epochs 200 --train-primes 2-50 --test-primes 53-101

eval: ## Evaluate trained model
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/scripts/evaluate.py --checkpoint data/models/best.pt

tensorboard: ## Start TensorBoard
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) tensorboard --logdir data/models/wandb --bind_all --port 6006

# ── Paper ────────────────────────────────────────────────────────
PAPER_SRC  := /workspace/docs/2026-05-30-comprehensive-project-paper.md
PAPER_DIR  := /workspace/paper
PAPER_TEX  := $(PAPER_DIR)/paper.tex
PAPER_OUT  := $(PAPER_DIR)/machine-learning-modular-forms-comprehensive.pdf

paper: ## Build paper from markdown (three-pass: pandoc→.tex → fix_tables → xelatex×2)
	@echo "=== Step 1/4: pandoc → .tex ==="
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) pandoc $(PAPER_SRC) \
		-t latex -s -o $(PAPER_TEX) \
		--lua-filter=/workspace/paper/booktabs.lua \
		--resource-path=/workspace/docs
	@echo "=== Step 2/4: Post-process tables (row colors) ==="
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/scripts/fix_tables.py $(PAPER_TEX) --inplace
	@echo "=== Step 3/4: xelatex (first pass) ==="
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) bash -c \
		"cd $(PAPER_DIR) && xelatex -interaction=nonstopmode paper.tex 2>&1 | tail -10"
	@echo "=== Step 4/4: xelatex (second pass — cross-refs) ==="
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) bash -c \
		"cd $(PAPER_DIR) && xelatex -interaction=nonstopmode paper.tex 2>&1 | tail -10"
	@echo "=== Renaming output ==="
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) bash -c \
		"cp $(PAPER_DIR)/paper.pdf $(PAPER_OUT)"
	@echo "=== PDF built: $(PAPER_OUT) ==="

paper-pdf: paper ## Build paper as PDF (alias)

# ── Utilities ────────────────────────────────────────────────────
logs: ## Tail all service logs
	$(DOCKER_COMPOSE) logs -f

logs-neo4j: ## Tail Neo4j logs
	$(DOCKER_COMPOSE) logs -f neo4j

clean-data: ## Remove generated data (keeps models)
	rm -f data/cayley-graphs/*.npz data/cayley-graphs/*.pt data/eigenvalues/*.npy

clean-all: ## Remove all generated data and models
	rm -rf data/cayley-graphs/* data/eigenvalues/* data/models/*

sage: ## Run SageMath (requires sage profile)
	$(DOCKER_COMPOSE) --profile sage run --rm sagemath sage
