# Mathlib Fork & Contribution Plan

## Overview

We will fork Mathlib, add our implementations, and create PRs for upstream contributions.

## Mathlib Components We Need to Add

### 1. Gauss Map for Continued Fractions

**Module Path**: `Mathlib/Dynamics/GaussMap.lean`

**Definitions**:
- `gaussMap`: T(x) = 1/x - ⌊1/x⌋
- `inverseBranch`: I_n(x) = 1/(n+1+x)

**Theorems**:
- `gaussMap_continuousOn`: Continuity on (0,1]
- `inverseBranch_contraction`: Lipschitz constant ≤ 1/2
- `partitionProperty`: I_n([0,1]) partitions (0,1)

**Placement**: New module under `Mathlib/Dynamics/`

---

### 2. Transfer Operators

**Module Path**: `Mathlib/Analysis/Normed/Operator/TransferOperator/Basic.lean`

**Definitions**:
- `TransferOperator` class for general dynamical systems
- `transferOperator` for Gauss map specific

**Theorems**:
- `transferOperator_bounded`: L_s is bounded
- `transferOperator_linear`: L_s is linear
- `transferOperator_compact`: L_s is compact

**Placement**: New submodule under `Mathlib/Analysis/Normed/Operator/`

---

### 3. Fredholm Determinants

**Module Path**: `Mathlib/Analysis/Operator/FredholmDeterminant.lean`

**Definitions**:
- `IsTraceClass`: Trace-class operator class
- `Trace`: Trace operator
- `fredholmDet`: Fredholm determinant

**Theorems**:
- `fredholmDet_one`: det(1) = 1
- `fredholmDet_product`: det(AB) = det(A)det(B)
- `spectralRadius_lt_one_iff_fredholmDet_ne_zero`

**Placement**: New module under `Mathlib/Analysis/Operator/`

---

### 4. Thermodynamic Formalism (Basic)

**Module Path**: `Mathlib/Dynamics/Ergodic/Thermodynamic.lean`

**Definitions**:
- `topologicalPressure`: Topological pressure
- `equilibriumState`: Gibbs measures
- `pressureFunction`: P(s) for potentials

**Theorems**:
- `bowenEquation`: P(φ) = log ρ(L_φ)
- `equilibriumState_unique`: Uniqueness for Hölder potentials

**Placement**: New module under `Mathlib/Dynamics/Ergodic/`

---

## PR Strategy

### Phase 1: Basic Infrastructure (Week 1-2)

**PR #1: Gauss Map**
- Title: feat(dynamics): Add Gauss map for continued fractions
- Content: `GaussMap.lean` module
- Dependencies: Minimal (basic analysis)

**PR #2: Transfer Operators**
- Title: feat(operator): Add transfer operator framework
- Content: `TransferOperator.lean` module
- Dependencies: Gauss map, compact operator theory

---

### Phase 2: Spectral Theory (Week 3-4)

**PR #3: Fredholm Determinants**
- Title: feat(operator): Add Fredholm determinants for trace-class operators
- Content: `FredholmDeterminant.lean` module
- Dependencies: Transfer operators, spectral theory

**PR #4: Thermodynamic Formalism**
- Title: feat(dynamics): Add basic thermodynamic formalism
- Content: `Thermodynamic.lean` module
- Dependencies: Transfer operators, pressure function

---

### Phase 3: Applications (Week 5-6)

**PR #5: Riemann Zeta Connection**
- Title: feat(numbertory): Add Mayer's identity connection
- Content: Mayer's identity theorem
- Dependencies: All of the above

---

## Fork Setup Instructions

```bash
# 1. Fork mathlib on GitHub (web interface)
#    https://github.com/leanprover-community/mathlib4

# 2. Clone your fork
cd /home/weiss/git/mathlib
gh repo clone leanprover-community/mathlib4
cd mathlib4

# 3. Create contribution branch
git checkout -b feature/gauss-map

# 4. Update lakefile to point to our fork
cd /home/weiss/git/riemann/lean
# Edit lakefile.lean to use local mathlib
```

---

## Module Dependencies

```
Mathlib/Data/... (existing)
    ↓
Mathlib/Dynamics/GaussMap (new)
    ↓
Mathlib/Analysis/Normed/Operator/TransferOperator (new)
    ↓
Mathlib/Analysis/Operator/FredholmDeterminant (new)
    ↓
Mathlib/Dynamics/Ergodic/Thermodynamic (new)
    ↓
Riemann/TransferOperator (our project)
```

---

## Guidelines for Mathlib PRs

1. **Documentation**: Each module needs module-level documentation (/-! ... -/)
2. **Theorems**: All theorems need proper statements and proofs
3. **Imports**: Minimize dependencies
4. **Naming**: Follow Mathlib conventions (snake_case for files, camelCase for functions)
5. **Linter**: Pass all linter checks (lake build lint)
6. **Tests**: Add tests in `Mathlib/Tests/`
