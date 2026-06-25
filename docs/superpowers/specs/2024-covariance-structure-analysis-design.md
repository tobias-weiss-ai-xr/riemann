# Covariance Structure Analysis Design

**Date:** 2024-XX-XX
**Branch:** b1 (new branch recommended)
**Status:** Design review pending

## Project Context

**Sprint 3 Conclusion**: Phase transition at d=21 (cross-form correlations jump from near-zero to strong positive) is NOT explained by:
- Classical number theory (dimensions sharing 3×7 factors show no special behavior)
- Eigenvalue distributions alone (synthetic experiments fail to reproduce phase transition)
- Direct spectral gaps (analysis deferred due to timeout on large matrices)

**Most promising hypothesis**: Covariance structure of P×P correlation matrices changes across dimensions. The phase transition likely involves dominant eigenvector behavior, eigenspace geometry shifts, or rank concentration changes that are not captured by mean correlations alone.

## Goal

Investigate whether the observed phase transition in Galois correlations is driven by covariance structure changes in the P×P correlation matrices.

**Specific objectives**:
1. Decompose correlation matrices by dimension class (low vs high dimension based on Sprint 3 skewness boundary d=6)
2. Track eigenvalue/eigenvector evolution across dimension boundaries
3. Identify dominant spectral modes and their relationship to the correlation jump

## Architecture

**Multi-Scale Spectral Decomposition**:

```
LMFDB CSV (53,566 non-CM forms)
↓
Dimension boundary split: low-dim (d≤6) vs high-dim (d>6)
↓
Stratified subsample: 1000-2000 forms per class
↓
Build P×P correlation matrices (P=25 traces: first 25 primes)
↓
Full spectral decomposition: eigenvalues λ_i, eigenvectors v_i
↓
Compare spectral properties:
  - Eigenvalue distribution (KL divergence, Wasserstein distance)
  - Top-k eigenvector contributions (explained variance)
  - Rank concentration (effective rank, eigenvector entropy)
  - Eigenvector similarity (cosine distance between classes)
↓
Identify driver modes (top eigenvectors with largest differences)
```

**Rationale for dimension boundary d=6**: Sprint 3 showed consistent skewness reduction at d=6 boundary (d≤6: 0.276 → d>6: 0.131, 37% drop). If phase transition is driven by covariance structure, we should detect spectral differences even at this lower boundary.

### Key Design Decisions

**Subsampling requirement**: Full 53K×53K correlation matrices are infeasible for eigencomputation. We stratified sample 1000-2000 forms per dimension class to approximate spectral properties while staying computationally tractable (1000×1000 matrices decompose in seconds).

**Symmetric positive-semidefinite matrices**: Correlation matrices are always symmetric PSD. We will use `scipy.linalg.eigh` (for hermitian matrices) which is faster and more stable than general eigenvalue decomposition.

**Prime count P=25**: First 25 primes provide sufficient dimensionality to capture spectral structure while keeping matrix sizes reasonable. This matches Sprint 1 analysis that used 25 traces.

## Components

### 1. Data Loading and Dimension Separation

**File**: `scripts/covariance_analysis/data_loader.py`

**Functions**:
- `load_lmfdb_correlation_data()`: Load from `data/galois_correlation/cross_form_correlation.csv`, filter out CM forms (`is_cm == 0`)
- `separate_by_dimension_boundary(boundary_dim=6)`: Split DataFrame into low-dim class (d≤6) and high-dim class (d>6)

### 2. Correlation Matrix Construction

**File**: `scripts/covariance_analysis/matrix_builder.py`

**Functions**:
- `build_correlation_matrix(trace_matrix)`: Build P×P correlation matrix from trace arrays (P=25 primes). Pearson correlation: `C_{ij} = cov(T_i, T_j) / (σ_i σ_j)`
- `subsample_forms(df, n_samples)`: Random stratified sampling to N forms per class. Ensures proportional representation from each original dimension within class.

### 3. Spectral Decomposition

**File**: `scripts/covariance_analysis/spectral_decomp.py`

**Functions**:
- `compute_full_spectrum(correlation_matrix)`: Use `scipy.linalg.eigh` for symmetric eigencomputation. Returns sorted eigenvalues (descending), eigenvectors as columns
- `compute_spectral_stats(eigenvalues, eigenvectors)`: Compute effective rank (sum(λ_i)/max(λ_i)), eigenvector entropy (-Σ(λ_i/Σλ) log(λ_i/Σλ))

### 4. Mode Analysis and Comparison

**File**: `scripts/covariance_analysis/mode_analysis.py`

**Functions**:
- `extract_top_modes(eigenvalues, eigenvectors, k=5)`: Extract top-k eigenvectors with their eigenvalues and explained variance (λ_i/Σλ)
- `compare_spectra(low_dims, high_dims)`: Compare:
  - Eigenvalue distributions (KL divergence, Wasserstein-1 distance)
  - Eigenvector similarity (cosine distance between corresponding eigenvectors)
  - Rank metrics (effective rank difference, entropy difference)
- `identify_driver_modes(low_modes, high_modes, top_k=5)`: Identify eigenvectors with largest differences (> threshold)

### 5. Visualization

**File**: `scripts/covariance_analysis/visualization.py`

**Functions**:
- `plot_eigenvalue_scree(low_evals, high_evals, output_path)`: Plot eigenvalue scree plots sorted by magnitude, overlaid for comparison
- `plot_top_eigenvectors(low_modes, high_modes, output_path)`: Plot top-k eigenvector components (prime-index vs eigenvector weighting)
- `plot_spectral_metrics_comparison(comparison, output_path)`: Bar plots of KL divergence, effective rank differences, entropy differences

## Data Specification

**Input**: `data/galois_correlation/cross_form_correlation.csv`

**Expected structure** (based on Sprint 1):
- Columns: trace_2, trace_3, trace_5, ..., trace_97, dim, is_cm
- Rows: 53,566 non-CM forms
- dim: integer 1-12 (dimension of the newform)
- is_cm: 0 (non-CM), 1 (CM forms excluded)

**Outputs**:
- `data/covariance_analysis/low_dim_spectrum.json`: `{eigenvalues: [], eigenvectors: [[...]], spectral_stats: {effective_rank, entropy}}`
- `data/covariance_analysis/high_dim_spectrum.json`: Same structure for high-dim class
- `data/covariance_analysis/spectral_comparison.json`: `{kl_divergence: X.XX, wasserstein_distance: Y.YY, eigenvector_distances: [z1, z2, ...], rank_difference: ΔR, entropy_difference: ΔH, driver_modes: [indices]}`
- `plots/covariance_analysis/eigenvalue_scree.png`
- `plots/covariance_analysis/top_k_eigenvectors.png`
- `plots/covariance_analysis/spectral_metrics_comparison.png`

## Error Handling

### Data Loading
- **File not found**: Raise FileNotFoundError with expected path
- **Insufficient forms after filtering**: Raise ValueError if < 50 forms in either class (cannot build meaningful correlation matrix)

### Matrix Construction
- **Column mismatch**: Raise ValueError if expected trace columns not present
- **Matrix not symmetric**: Check `np.allclose(C, C.T, atol=1e-10)`; if fails, raise ValueError (correlation matrices must be symmetric)
- **Zero variance column**: If any trace column has σ=0, raise ValueError (cannot normalize)

### Eigencomputation
- **Convergence failure**: `scipy.linalg.eigh` will raise LinAlgError; catch and log with transition boundary warning
- **Not positive-semidefinite**: Check all eigenvalues >= -1e-10; if negative eigenvalue found, clip to zero and log warning

### Visualization
- **Output directory not found**: Auto-create with Path.mkdir(parents=True, exist_ok=True)
- **File write permission error**: Catch and log with path; continue without crashing

## Testing Strategy

### Unit Tests (`scripts/test_covariance_*.py`)

**Test 1: Data Loading and Separation**
- Verify CSV loads correctly (expected dimensions: 53K rows × 25 trace columns)
- Verify dimension split: count low-dim (d≤6) and high-dim (d>6)
- Assert all filtered forms have `is_cm == 0`

**Test 2: Matrix Construction**
- Build correlation matrix from synthetic data (100 forms, 5 traces)
- Assert matrix shape is P×P (5×5)
- Assert diagonal values ≈ 1.0 (within numerical tolerance)
- Assert matrix is symmetric (`np.allclose(C, C.T, atol=1e-10)`)

**Test 3: Subsampling**
- Create test dataset with known dimension distribution (e.g., 200 low-dim, 200 high-dim)
- Subsample to 50 forms per class
- Assert: each class has exactly 50 forms
- Assert: original dimension representation maintained proportionally within classes

**Test 4: Spectral Decomposition**
- Build test matrix (5×5, random correlation matrix)
- Compute spectrum
- Assert: eigenvalues sum to trace (within tolerance)
- Assert: eigenvectors orthonormal (V^T @ V ≈ I)
- Assert: eigenvalues sorted descending

**Test 5: Comparison Metrics**
- Create two known spectra (different eigenvalue distributions)
- Compute KL divergence, verify > 0
- Compute cosine distance between vectors, verify in [0, 2]

### Integration Test

**Test 6: Full Pipeline (Reduced Data)**
- Run full pipeline on test dataset (100 forms total, 5 traces)
- Verify:
  - Output files created
  - Eigenvalues sum to P (within tolerance)
  - Effective rank ∈ [1, P]
  - Eigenvector entropy ∈ [0, log(P)]

### Verification

After completing implementation:
- Run `lsp_diagnostics scripts/covariance_analysis/*.py` — no errors
- Run `pytest scripts/test_covariance_*.py -v` — all tests pass
- Manual verification on sample: inspect JSON outputs for reasonable values

## Success Criteria

### Primary Outcomes
- [ ] Spectral decomposition completes on subsampled data without timeout (< 60s per class)
- [ ] Identify at least 2-3 spectral modes showing significant differences between low and high dimension classes (threshold: cosine distance > 0.3 or KL divergence > 0.2)
- [ ] Document whether eigenvector structure changes correlate with phase transition phenomenon

### Failure Modes (Acceptable)
- [ ] No significant spectral differences found → hypothesis refuted, report as negative result
- [ ] Numerical instability on full 1000×1000 matrices → reduce sample size to 500, document limitation
- [ ] Unexpected eigenvalue behavior (e.g., numerical artifacts) → adjust tolerance thresholds, document findings

### Documentation Deliverables
- [ ] `experiments/EXPERIMENT_13_SPRINT_4.md`: Full methodology, results, interpretation
- [ ] Update `experiments/EXPERIMENT_LOG.md` with Sprint 4 findings
- [ ] All source code, tests, and outputs committed to branch

## Timeline Estimates

- Task 1 (Data + Matrix): 30 min
- Task 2 (Spectral Decomp): 20 min
- Task 3 (Mode Analysis): 30 min
- Task 4 (Visualization): 20 min
- Task 5 (Integration + Docs): 30 min

**Total**: ~2.5 hours

## Dependencies

**External libraries**: numpy, scipy, pandas, matplotlib (all available in research container via Dockerfile)

**Internal dependencies**:
- None (standalone analysis, can be implemented independently)
- CSV structure assumed from Sprint 1

## Execution Context

**Branch**: Create new branch `b1-covariance-analysis` from `main`

**Environment**: Work inside Docker container (`docker compose exec research bash`), Python 3.11+

**Commit strategy**: Frequent commits after each task, following AGENTS.md conventions