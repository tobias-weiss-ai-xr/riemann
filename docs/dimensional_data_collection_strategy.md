# LMFDB SQL Data Collection Strategy

## Critical Discovery

The `mf_hecke_nf` table in the LMFDB SQL mirror contains **individual eigenvalue data ONLY for dimensions ≤20**. Individual eigenvalue data is **NOT available for dimensions ≥21**.

### Data Availability Summary

| Dimension | Individual Eigenvalues | Metadata + Traces | Count (d=1-20) |
|-----------|------------------------|-------------------|----------------|
| d=1-20     | ✅ Available via mf_hecke_nf | ✅ Available via mf_newforms | 46,347 newforms |
| d≥21      | ❌ Not available | ✅ Available via mf_newforms | Hundreds of thousands |

**Note:** d=20 has 386 forms with individual eigenvalues, then coverage stops completely.

## Dimension-Specific Collection Strategy

### **Strategy A: d≤20 (Individual Eigenvalue Analysis)**

**Use Case:** ρ₂=-0.607 anticorrelation analysis, Sato-Tate normalization, per-embedding analysis

**Data Collection Command:**
```bash
# Full d≤20 dataset with individual eigenvalues
python scripts/collect_lmfdb_sql.py \
  --min-dim 1 --max-dim 20 \
  --individual-eigenvalues \
  --no-traces-matrix \
  --limit 0

# This produces:
# - data/lmfdb/lmfdb_sql_weight2.json (full metadata + individual eigenvalues)
# - data/lmfdb/lmfdb_individual_eigenvalues.json (individual eigenvalues only)
```

**Expected Output:** 46,347 newforms with per-embedding eigenvalue data

**Analysis Methods Enabled:**
- Per-embedding Sato-Tate analysis (xₚ = aₚ/(2√p) per embedding)
- ρ₂ correlation across embeddings within same newform
- Individual L-function zero prediction per embedding
- Galois orbit structure analysis

### **Strategy B: d≥21 (Trace-Only Analysis)**

**Use Case:** d≥21 phase transition analysis, dimension trend analysis, spectral properties

**Data Collection Command:**
```bash
# d≥21 metadata + traces (no individual eigenvalues available)
python scripts/collect_lmfdb_sql.py \
  --min-dim 21 --max-dim 42464 \
  --limit 0

# This produces:
# - data/lmfdb/lmfdb_sql_weight2.json (metadata + traces only)
# - data/lmfdb/lmfdb_traces_matrix.npy (trace matrix)
```

**Expected Output:** All newforms with d≥21 (hundreds of thousands)

**Analysis Methods Enabled:**
- Phase transition analysis at d=21 boundary
- Dimension~spectral gap relationships
- Trace-based ML models (no individual eigenvalue features)

### **Strategy C: Hybrid = Combined Dataset**

**Use Case:** Cross-dimensional studies, unified dimension analysis

**Two-Phase Collection:**
```bash
# Phase 1: d≤20 with individual eigenvalues
python scripts/collect_lmfdb_sql.py \
  --min-dim 1 --max-dim 20 \
  --individual-eigenvalues \
  --no-traces-matrix \
  --limit 0

# Phase 2: d≥21 traces only
python scripts/collect_lmfdb_sql.py \
  --min-dim 21 \
  --limit 0
```

**Output:** Complete dataset with d=1-42464 coverage

## Alternative Individual Eigenvalue Sources for d≥21

If individual eigenvalues for d≥21 become critical, consider:

### **SageMath Paths**
```python
# Path A: ModularSymbols (exact algebraic, weight ≥ 2)
M = ModularSymbols(level, weight, sign)
M.hecke_operator(p).eigenvalues()

# Path B: NumericalEigenforms (fast float64, large levels)
from sage.modular import numerics as modular_numerics
eigvals = modular_numerics.NumericalEigenforms(level, weight)

# Path C: Newforms() constructors (high-level, label-based)
Newforms(level, weight, names='a')

# Path D: Analytic method (arXiv:1806.01586, fastest)
# Fast single eigenvalue computation using modular symbols
```

### **PARI/GP**
```parigp
// ellap() uses SEA for weight 2 eigenvalues at large p
ellap(E, p)  // for elliptic curves (weight 2)

// mfinit() + mfcoefs() for any weight
F = mfinit([N, k, CHI]);
mfcoefs(F, M)  // get M coefficients
```

### **LMFDB mf_hecke_cc Table**
- Complex eigenvalues table (637GB)
- May contain additional eigenvalue data for higher dimensions
- Requires investigation of coverage

## Research Gap Resolution Matrix

| Research Gap | d≤20 Available? | d≥21 Available? | Recommended Approach |
|--------------|----------------|----------------|---------------------|
| **ρ₂=-0.607 anticorrelation** | ✅ mf_hecke_nf | ❌ Not available | Use d≤20 individual eigenvalues directly |
| **Sato-Tate per-embedding** | ✅ mf_hecke_nf | ❌ Not available | Use d≤20 individual eigenvalues directly |
| **d≥21 phase transition** | N/A | ✅ Traces only | Use trace-based analysis |
| **Cross-dimension studies** | ✅ Both | ✅ Traces only | Hybrid: d≤20 eigenvalues + d≥21 traces |
| **Semilocal adelic operators** | ✅ Both | ✅ Metadata | Use available traces for all dimensions |

## Implementation Status

- ✅ `--min-dim` / `--max-dim` flags implemented
- ✅ `--individual-eigenvalues` flag implemented
- ✅ `fetch_individual_eigenvalues()` function working
- ✅ Individual eigenvalues saved to dedicated JSON
- ✅ Verified d≤20 = 46,347 newforms have individual eigenvalue data
- ✅ Confirmed d≥21 individual eigenvalues NOT available in SQL mirror

## Next Steps

1. **Immediate:** Run d≤20 collection with individual eigenvalues for ρ₂ analysis
2. **Short-term:** Run d≥21 collection for phase transition work
3. **Medium-term:** Investigate SageMath/PARI integration for d≥21 individual eigenvalues if needed
4. **Long-term:** Explore mf_hecke_cc table (637GB) for potential coverage

## File Outputs

### d≤20 with Individual Eigenvalues
```
data/lmfdb/
├── lmfdb_sql_weight2.json          # 46,347 newforms + individual eigenvalues
└── lmfdb_individual_eigenvalues.json  # Focused eigenvalue dataset
```

### d≥21 Traces Only
```
data/lmfdb/
├── lmfdb_sql_weight2.json          # All newforms + traces
└── lmfdb_sql_weight2_ml.csv        # ML-ready traces only
```

## Performance Considerations

- **d≤20 collection:** ~15-30 minutes (46,347 newforms)
- **d≥21 collection:** ~2-4 hours (hundreds of thousands of newforms)
- **SageMath computation:** Slow for d≥21 (hours to days depending on level)
- **PARI/GP computation:** Fastest for weight 2 (seconds to minutes per eigenvalue)

## Key Finding Summary

The LMFDB SQL mirror **does not provide individual eigenvalue data for d≥21** in the `mf_hecke_nf` table. This limitation requires a dual-strategy approach:

1. **Direct SQL access** for d≤20 individual eigenvalues (46,347 forms available)
2. **Trace-based analysis** for d≥21 (all-high-dimension newforms accessible)
3. **Alternative computation** (SageMath/PARI/GP) if d≥21 individual eigenvalues become essential

This resolves the research gap blocking the ρ₂=-0.607 analysis while still enabling d≥21 phase transition studies.
