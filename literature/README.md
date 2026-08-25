# Literature Base

Structured corpus transferred from `riemann-research` (3,460 papers, categorized).

This base supports the riemann project's research on GNNs × Cayley graphs × RH.

**Total: 3,460 papers** across 10 categories.

## Research Area Mapping

| Project Focus | Corpus Categories | Papers |
|---------------|-------------------|--------|
| GNNs on Cayley Graphs | spectral-theory, machine-learning | **853** |
| Transfer Operators & Selberg Zeta | dynam-systems | **251** |
| L-Functions & Hecke | number-theory | **861** |
| RH Equivalences | equivalences | **660** |
| Lean 4 Formalization | formalization | **15** |
| Surveys & Reviews | survey | **64** |

## Category Distribution

| Category | Papers | Project Relevance |
|----------|--------|-------------------|
| number-theory | **861** | 🟡 MED — L-functions, Hecke operators |
| equivalences | **660** | 🟡 MED — RH equivalences |
| spectral-theory | **440** | 🔴 HIGH — Cayley graphs, spectral gaps |
| machine-learning | **413** | 🔴 HIGH — GNNs on Cayley |
| method | **293** |  |
| evaluation | **260** |  |
| dynam-systems | **251** | 🔴 HIGH — Transfer operators, Selberg zeta |
| application | **203** |  |
| survey | **64** | 🟢 USEFUL — Literature review |
| formalization | **15** | 🟢 LOW — Lean 4 RH |

## Priority Subcategories (Project Focus)

### spectral-theory

| Subcategory | Papers |
|-------------|--------|
| cayley-graphs | 195 |
| theory | 191 |
| application | 24 |
| method | 16 |
| development | 6 |

### machine-learning

| Subcategory | Papers |
|-------------|--------|
| theory | 169 |
| method | 160 |
| mechanism | 55 |
| application | 10 |
| cayley-graphs | 9 |

### dynam-systems

| Subcategory | Papers |
|-------------|--------|
| theory | 124 |
| cayley-graphs | 47 |
| method | 46 |
| development | 17 |
| application | 12 |

## Usage

```python
import yaml
with open('literature/papers.yaml') as f:
    papers = yaml.safe_load(f)['papers']

# Filter by category
cayley_papers = [p for p in papers if p.get('category')=='spectral-theory']
```

Discovery queries (arXiv, OpenAlex, other sources) are in `literature/config/taxonomy.yaml`.

## Core Corpus (Priority Areas)

For the project's main focus (GNNs × Cayley graphs × RH), use `papers_core.yaml`:
- **1,104 papers** (spectral-theory + machine-learning + dynam-systems)
- Faster to load, focused on the project's primary research areas

```python
import yaml
with open('literature/papers_core.yaml') as f:
    core = yaml.safe_load(f)['papers']
print(f"{len(core)} priority papers")
```

## Files

| File | Description |
|------|-------------|
| `papers.yaml` | Full corpus (3,460 papers, all categories) |
| `papers_core.yaml` | Priority subset (1,104 papers: spectral-theory, machine-learning, dynam-systems) |
| `config/taxonomy.yaml` | Taxonomy + discovery queries (arXiv, OpenAlex, other sources) |
| `references.bib` | BibTeX export (3,460 entries) |
| `export_bibtex.py` | Regenerate references.bib from papers.yaml |
| `README.md` | This file |
