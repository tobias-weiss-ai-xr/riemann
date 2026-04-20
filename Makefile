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
paper: ## Build paper from markdown
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) python /workspace/scripts/build_paper.py

paper-pdf: ## Build paper as PDF
	$(DOCKER_COMPOSE) exec $(RESEARCH_CONTAINER) pandoc /workspace/paper/gnn-zahlentheorie-riemann.md \
		-o /workspace/paper/gnn-zahlentheorie-riemann.pdf \
		--pdf-engine=xelatex \
		--resource-path=/workspace/paper

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
