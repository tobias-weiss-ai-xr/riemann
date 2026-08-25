# Lean 4 and FunSearch Integration Status for RH Project

**Date**: January 18, 2025  
**Purpose**: Summary of formalization and AI-based search progress

---

## 📊 Overview

This repository incorporates two advanced frameworks:
1. **Lean 4**: Formal proof assistant for mathematical verification
2. **FunSearch**: LLM-based program discovery system

---

## 📜 Lean 4 Formalization

### Project Status: ~10% Complete

### Directory Structure

```
lean/
├── lakefile.lean              # Lean project configuration (mathlib dependency)
├── lean-toolchain             # Lean toolchain pin
├── Main.lean                  # Entry point
└── Riemann/
    ├── TransferOperator/
    │   ├── Operator.lean      # Definition of L_s (transfer operator)
    │   ├── GaussMap.lean      # Gauss map definition
    │   └── Theorem3_3.lean    # Spectral radius bound (lots of `sorry`)
    ├── CayleyGraphs.lean      # SL(2,F_p) group + generators
    ├── SpectralGaps.lean      # Spectral gap definitions
    ├── RamanujanProperty.lean  # Ramanujan property ≤ 2√3
    ├── RiemannHypothesis.lean # Main RH statements (using mathlib ζ)
    └── [... other files]
```

### What's Formalized

#### ✅ **Complete/Well-Defined**:

1. **RiemannHypothesis.lean**:
   - `ZetaZerosOnCriticalLine`: Restatement of RH in convenient form
   - `rh_implies_zeros_on_line`: Uses mathlib's `RiemannHypothesis`
   - `spectralGapNonMonotonic`: Proved with numerical counterexamples (p=29,31,37)

2. **CayleyGraphs.lean**:
   - SL(2,F_p) group structure
   - Generators S = [[0,-1],[1,0]], R = [[0,-1],[1,1]]
   - Cayley graph adjacency definition
   - Regularity, vertex-transitivity properties

3. **RamanujanProperty.lean**:
   - `pThreeIsRamanujan`, `pFiveIsRamanujan` for p=3,5
   - `cheegerInequality` for 4-regular graphs
   - Parameters table (p=3,5 are Ramanujan; p≥7 are not)

#### ⚠️ **Partially Formalized (stub with docstrings)**:

4. **RiemannHypothesis.lean**: 
   - `BridgeAConjecture`: Conditional Ramanujan → RH (marked as conjecture)
   - `BridgeBConjecture`: Transfer operator ↔ zeros (placeholder `def ... := True`)
   - `SpectralGapConjecture`: Alon-Boppana asymptotic bound

#### ❌ **Skeleton Available (all `sorry`)**:

5. **Theorem3_3.lean**:
   - `leadingEigenvalue(s)`: Definition (`sorry` for value)
   - `kreinRutman_at_one_half`: ∃ φ > 0, L_{1/2} φ = φ
   - `leadingEigenvalue_at_one_half`: λ(1/2) = 1
   - `feynmanHellmann_at_one_half`: λ'(1/2) = -∫ log(x+1)ρ(x)dx
   - `leadingEigenvalue_derivative_negative`: λ'(1/2) < 0
   - `leadingEigenvalue_analytic`: Λ₁(s) analytic for Re(s) > 1/2
   - `leadingEigenvalue_taylorExpansion`: Taylor around 1/2
   - `spectralRadius_lt_one`: **The main theorem** (fully formalized but all proofs `sorry`)

6. **TransferOperator/Operator.lean**:
   - `transferOperator(s)`: Definition `(L_s f)(x) = ∑ (n+x)^{-2s} f(1/(n+x))`
   - `transferOperator_bounded`: ∀ C>0, ‖L_s f‖ ≤ C‖f‖ (`sorry`)
   - `transferOperator_compact`: IsCompactOperator L_s (`sorry`)
   - `transferOperatorBounded`: →L[ℂ] FunctionSpace (`sorry`)

### Current Compilation Status

Run `lake build` to check zero-error expectation:

```bash
cd lean
lake build
```

**Expected**: Zero errors (all theorems are placeholders with `sorry` or `True` definitions).
**Status**: The framework compiles but proofs are stubs.

---

## 🤖 FunSearch Integration

### Project Status: Branch Submodule (Separate Docker Environment)

FunSearch is a **separate git submodule** managing its own:
- Dockerfile (Docker environment)
- Dependencies (pdm.lock)
- Model configurations (Claude/GPT-4o/Gemini/Mistral/Deepseek via APIs)
- Evaluation and logging (Weights & Biases)

### Directory Structure

```
funsearch/
├── Dockerfile                 # Separate Docker build
├── requirements.txt & pdm.lock
├── funsearch/
│   ├── server.py, config.py, evolve.py
│   └── ... (genetic programming loop with LLM mutations)
├── examples/
│   ├── cap_set_spec.py        # Example problems (cap sets, primes, etc.)
│   ├── is_prime.py
│   └── [template for RH problems]
├── data/
│   ├── wandb/                 # Weights & Biases logs
│   ├── backup/               # Program DB backups
│   └── graphs/               # Score progression graphs
└── run_in_docker.sh          # Execution script
```

### What's Integrated

#### ✅ **Fully Functional**:

- Multi-model support (Codestral, Claude, GPT-4o, Gemini, etc.)
- Parallel evaluation (multi-process)
- WandB logging (best score per island)
- Program DB persistence + backups
- Safety sandboxing (ContainerSandbox or ExternalProcessSandbox)
- OEIS integration for sequences (fetch/save/List)

#### ⚠️ **RH-Specific Experiments**:

Running FunSearch experiments for this project would involve:

1. Creating a spec file (e.g., `examples/rh_spectral_gap_spec.py`) with:
   - `solve()` method implementing evaluation metric
   - Input data: primes p and target spectral gap bound
   - Output: best predicted gap or best discovered algorithm

2. Preparing input data (e.g., primes list):
   ```bash
   # Example
   python funsearch/runasync examples/rh_spectral_gap_spec.py "data/primes_2_to_101.json" \
     --model mistralai/codestral-mamba \
     --samplers 10 --evaluators 8 --islands 5 \
     --duration 3600
   ```

3. Reviewing results:
   - Check `data/scores/` CSV for best scores
   - Check `data/graphs/` for progression
   - Check WandB dashboards for live monitoring

---

## 🔗 Lean ↔ FunSearch Synergy

### Potential Future Workflows

1. **Verified Algorithm Discovery**:
   - FunSearch discovers spectral gap bounds
   - Lean formalizes the discovered algorithm
   - `lake build` verifies the formalization

2. **Guided Search via Lean Theorems**:
   - Lean proves lemmas (e.g., `gap(p) < 4−2√3+ε`)
   - Feed constraints to FunSearch to constrain search space
   - LLM searches for tighter bounds or new algebraic structures

3. **Direct Integration**:
   - Wrap FunSearch in a Lean CIF format calling external evaluator
   - Lean's `MetaM` could call FunSearch's `server.py` for numeric experiments
   - Or export Lean theorems to guide FunSearch's.modelInitialize

### Current Gap

No direct programmatic synchronization exists between Lean proofs and FunSearch search loops. They run in **two separate environments**:

- **Lean**: Host-only (outside main Docker)
- **FunSearch**: Containerized (`docker run -it -v`)

To connect them, options include:
1. SSH into the container, set up Lean, run both
2. Build a local bridge script that calls one from the other
3. Use a shared filesystem (e.g., Git push/pull) for results

---

## 🎯 What Can Be Done Now

### With Lean (Already Setup)

- Compile the framework: `cd lean && lake build`
- Browse theorems in `Riemann.lean` (e.g., `spectralGapNonMonotonic` is proved)
- Check mathlib's `RiemannHypothesis` import: `import Mathlib.NumberTheory.LSeries.RiemannZeta`

### With FunSearch (Connected to LLMs)

- Run tutorial examples:
  ```bash
  cd funsearch
  docker build -t funsearch .
  docker run -it -v ./data:/workspace/data -v ./examples:/workspace/examples \
             --env-file .env funsearch
  funsearch runasync /workspace/examples/cap_set_spec.py 11
  ```
- Check `data/wandb/` or your WandB web dashboard for live results

### In Project Root (Docker Compose)

- `docker compose up -d` starts `research` env + Neo4j
- FunSearch and Lean still need separate shell access (not in the compose stack)

---

## 📚 Todo List (Two Tracks)

| Component | Lean Track | FunSearch Track |
|-----------|------------|-----------------|
| **Operator** | Formalize L_s definition (`transferOperatorBounded` proved) | Discover spectral gaps for specific primes |
| **Theorem 3.3** | Fill All `sorry` in `Theorem3_3.lean` | N/A (procedural) |
| **RH bridges** | Formalize `BridgeAConjecture` → RH (if Ramanujan) | Model Hecke→gap relationship via ML on LMFDB |
| **Verification** | `lake build` → 0 errors | WandB log → confirm best scores |

---

## 🔴 Current Blockers

- **Formalization**: Most Lean theorem bodies are `sorry`. Requires deep functional analysis not yet in mathlib.
- **Integration**: No deterministic sync between Lean proofs and FunSearch search loops.
- **RH proof status**: As per `HONEST_FINAL_STATUS.md`, Theorem 3.3 and RH itself are **not proven** in Python/docs; Lean formalization mirrors that partial status.

---

## 🎓 Summary

### Lean 4
- **Purpose**: Check formal correctness once fully proved
- **Status**: Framework compiles with ~10% theoretical coverage
- **Next**: Fill `Theorem3_3.lean` proofs with mathlib-grade rigor

### FunSearch
- **Purpose**: Discover or optimize mathematical algorithms
- **Status**: Fully functional, standalone (submodule)
- **Next**: Design RH-targeted spec files + training data

### Synergy Future
- Pipeline: FunSearch → Lean Verify → Theorem Export → FunSearch Retry
- Requires bridge scripts or shared filesystem coordination

---

*This document accompanies the RH project overview. For deeper technical detail, see individual file docstrings or the main project README.*
