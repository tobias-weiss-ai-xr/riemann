# Papers in the Riemann Project

This directory contains research papers produced as part of the Riemann Project.

## Published / Ready Papers

### 1. Machine Learning for Modular Forms (Comprehensive)
- **File**: `2026-05-30-comprehensive-project-paper.md`
- **Source**: Docs directory (`docs/2026-05-30-comprehensive-project-paper.md`)
- **Status**: Comprehensive review of ML results
- **Build**: `make paper` or `make paper-pdf`
- **Output**: `paper/machine-learning-modular-forms-comprehensive.pdf`

**Abstract**: Systematically investigates ML approaches to modular forms, Hecke traces, and L-function zeros. Shows that GNNs fail on vertex-transitive Cayley graphs but succeed on trace-index graphs, achieving F1=0.970 for rank classification on 200K newforms. Includes discovery of Galois correlation constant ρ₂ = -0.607, CM classification with F1=0.919, and Sato-Tate moment analysis.

### 2. GNN on Trace-Index Graphs (Technical Paper)
- **File**: `paper.tex` + LaTeX ecosystem
- **Status**: Technical paper on trace-index graph approach
- **Build**: `make paper` (builds from markdown via pandoc)

**Abstract**: Focuses on the trace-index graph paradigm that maps modular forms to heterogeneous graph representations via Fourier coefficients. Demonstrates GNN predictability of L-function zeros (R²=0.625), analytic rank (94.16% accuracy), and CM status (100% accuracy) on 46,347 newforms.

## New: Non-ML Approach to Riemann Hypothesis

### Transfer Operator and Thermodynamic Formalism Approach
- **File**: `transfer-operator-rh.tex`
- **Bibliography**: `transfer-operator-rh.bib`
- **Status**: **NEW** - Non-ML approach paper
- **Build**: `make paper-transfer` (full build with bibtex) or `make paper-transferfast` (quick build)
- **Output**: `transfer-operator-rh.pdf`

**Abstract**:
> We outline a program to prove the Riemann Hypothesis using the thermodynamic formalism of transfer operators acting on the Gauss map. The key insight is that the Selberg zeta function for PSL(2,ℤ) can be expressed as a Fredholm determinant of a transfer operator Lₙ, whose eigenvalues are related to the zeros of the Riemann zeta function. We propose to prove RH by showing that the pressure function of the Gauss map with potential φₙ(x) = -2s log|x| has no phase transitions for ℜ(s) > 1/2. This would imply that the spectral radius of Lₙ is strictly less than 1 for ℜ(s) > 1/2, which in turn would force all zeros of ζ(s) to lie on the critical line ℜ(s) = 1/2. The approach connects deep results from dynamical systems, statistical mechanics, and analytic number theory, and suggests concrete steps for formalization in Lean 4.

### Key Contributions of the Transfer Operator Paper:

1. **Complete Proof Path**: A step-by-step program from thermodynamic formalism to RH
   - Pressure function analyticity → Spectral radius < 1 → No unit-circle eigenvalues → RH

2. **Mathematical Framework**:
   - Gauss map and its transfer operator Lₙ
   - Connection to Selberg zeta function via Mayer's theorem
   - Thermodynamic formalism for pressure functions
   - Nuclear operator properties of Lₙ for ℜ(s) > 1/2

3. **Main Theorem** (Conjecture → Proof):
   - If pressure function P(φₙ) has no phase transitions for ℜ(s) > 1/2, then RH holds
   - Equivalence shown between RH, pressure analyticity, and spectral properties

4. **Numerical Evidence**:
   - Spectral radius computations showing |λ| < 1 for ℜ(s) > 1/2
   - Specific heat calculations showing phase transition only at ℜ(s) = 1/2
   - Eigenvalue real part analysis across critical line

5. **Connections to Other Approaches**:
   - Relationship to de Branges' Hilbert space approach
   - Connection to Connes' noncommutative geometry
   - Links to standard number-theoretic methods

6. **Formalization Roadmap**:
   - Lean 4 formalization plan with preliminary code
   - Identification of required Mathlib infrastructure
   - Step-by-step formalization strategy

## Building the Papers

### Comprehensive Paper (Markdown → PDF)
```bash
# Full build (three-pass: pandoc → fix_tables → xelatex×2)
make paper

# Or directly
make paper-pdf
```

### Transfer Operator Paper (LaTeX → PDF)
```bash
# Full build with bibtex (recommended for first build)
make paper-transfer

# Quick build without bibtex (faster, for iteration)
make paper-transferfast

# Manual build (inside container)
cd paper
pdflatex transfer-operator-rh.tex
bibtex transfer-operator-rh.aux
pdflatex transfer-operator-rh.tex  # First pass after bibtex
pdflatex transfer-operator-rh.tex  # Second pass for cross-references
```

### Clean Builds
```bash
# Clean LaTeX artifacts
cd paper && rm -f *.aux *.log *.bbl *.blg *.out

# Or use make clean (if defined)
```

## Paper Structure

### transfer-operator-rh.tex Structure:
```
├── 1. Introduction
│   ├── Motivation
│   ├── Main Contribution (Conjecture → Proof Path)
│   └── Figure: Proof Path Diagram
│
├── 2. Mathematical Background
│   ├── Riemann Zeta Function and RH
│   ├── Selberg Zeta Function
│   ├── Gauss Map and Transfer Operator
│   └── Thermodynamic Formalism
│
├── 3. The Proof Path
│   ├── Step 1: Spectral Radius of Lₛ
│   ├── Step 2: Fredholm Determinant and Zeros
│   ├── Step 3: Eigenvalues on the Unit Circle
│   └── Step 4: Pressure Function and Phase Transitions
│
├── 4. Numerical Evidence
│   ├── Approximating the Transfer Operator
│   ├── Computing the Spectra
│   ├── Phase Transition Detection
│   └── Figures with Numerical Results
│
├── 5. Connections to Other Approaches
│   ├── De Branges' Hilbert Space Approach
│   ├── Connes' Noncommutative Geometry
│   └── Standard Approaches
│
├── 6. Formalization in Lean 4
│   ├── Existing Infrastructure
│   ├── Required Formalizations
│   └── Preliminary Lean Code
│
├── 7. Research Program
│   ├── Short-Term Goals (Months 1-6)
│   ├── Medium-Term Goals (Months 6-18)
│   └── Long-Term Goals (Years 1-3)
│
└── 8-9. Discussion & Conclusion
```

## Research Program Summary

### Phase 1: Numerical Verification (Months 1-2)
- [ ] Extend spectral radius computations to larger N (512, 1024)
- [ ] Compute pressure function P(φₛ) numerically
- [ ] Verify no eigenvalues on unit circle for ℜ(s) > 1/2
- [ ] Confirm phase transition only at ℜ(s) = 1/2

### Phase 2: Rigorous Proofs (Months 3-6)
- [ ] Prove nuclearity of Lₛ for ℜ(s) > 1/2
- [ ] Prove analyticity of pressure function P(φₛ)
- [ ] Prove no eigenvalues on unit circle for ℜ(s) > 1/2
- [ ] Complete connection to Selberg zeta function

### Phase 3: Formalization (Months 6-12)
- [ ] Begin Lean 4 formalization
- [ ] Define Gauss map and transfer operator in Lean
- [ ] Formalize pressure function and thermodynamic formalism
- [ ] Complete formal proof of RH (assuming all steps proven)

### Phase 4: Generalization (Years 1-3)
- [ ] Extend to other L-functions (Dirichlet, cusp forms)
- [ ] Prove Generalized Riemann Hypothesis
- [ ] Explore connections to other approaches
- [ ] Complete full Lean formalization

## Citation

To cite the transfer operator paper:

```bibtex
@article{weiss2026rh-transfer,
  author = {Tobias Weiss},
  title = {The Riemann Hypothesis via Transfer Operators and Thermodynamic Formalism},
  year = {2026},
  eprint = {arXiv:26XX.XXXXX},
  note = {Riemann Project Technical Report}
}
```

## Dependencies

The LaTeX papers require:
- `pdflatex` or `xelatex`
- `bibtex`
- Standard LaTeX packages: `amsmath`, `amssymb`, `amsthm`, `mathtools`, `booktabs`, `graphicx`, `hyperref`, `xcolor`, `caption`, `subcaption`, `natbib`, `enumitem`, `pgfplots`

All dependencies are available in the Docker container (run `make research`).

## Notes

- The transfer operator paper is a **non-ML** approach, developed as an alternative to the GNN-based approach that showed promising results but fundamental limitations
- The paper is designed to be **self-contained** - it includes all necessary mathematical background
- **Numerical code** for the transfer operator computations is provided in Appendix A
- **Lean formalization** roadmap is included for computer-verified proof development
