# arXiv Submission Package — L-Function Paper

**Paper Title**: The Two-Population Structure of L-Function Zero Spacings: dim=1 to GUE, dim≥2 to Poisson with 6% Outliers  
**Authors**: Tobias Weiss  
**arXiv Categories**: math.NT (Number Theory), math.PR (Probability), cs.LG (Machine Learning)  
**Status**: ✅ Ready for submission

---

## 📦 Files Included

```
papers/
├── lfunction_zeros_2026_clean.tex   # LaTeX source (17.5 KB)
├── lfunction_zeros_2026_clean.pdf   # Compiled PDF (1.1 MB)
├── references.bib                   # References (optional, not currently used)
└── figures/
    ├── beta_vs_dimension.png        # Figure 1
    ├── gue_percentage_vs_dimension.png # Figure 2
    ├── level_distribution_gue_outliers.png # Figure 3
    ├── roc_curve_spectral_rigidity.png # Figure 4
    └── spacing_vs_dimension_scatter.png # Figure 5
```

---

## 📋 Submission Checklist

- [x] Paper title finalized
- [x] Abstract written (198 words)
- [x] Paper compiles without errors
- [x] PDF generated successfully (11 pages, 1.1 MB)
- [x] All 5 figures generated and referenced
- [x] File sizes within arXiv limits (source < 10MB, PDF < 30MB)

---

## 📝 Metadata

### Title
The Two-Population Structure of L-Function Zero Spacings: dim=1 to GUE, dim≥2 to Poisson with 6% Outliers

### Abstract
We present empirical evidence for a two-population structure in the spacing statistics of L-function zeros for modular forms, revealing a dimension-dependent transition from Gaussian Unitary Ensemble (GUE) to Poisson statistics. Analyzing 63,844 weight-2 newforms from the LMFDB database with 10 lowest zeros each, we find: (1) dim=1 forms (elliptic curves) exhibit GUE statistics with Brody β=1.88 (R²=0.99 vs GUE reference), (2) dim≥2 forms exhibit near-Poisson statistics with β=0.24, and (3) within dim≥2, 6% of forms retain GUE statistics, characterized as low-dimension, small-level forms. Surprisingly, spectral rigidity properties are predictable from scalar metadata (dimension, level, analytic rank) alone with R²>0.93, while Hecke trace features contribute negligible additional signal (ΔR²<0.02). This suggests that spacing statistics are determined by the form's arithmetic complexity rather than its specific Hecke eigenvalue sequence. Our results refine the Katz-Sarnak philosophy and provide a novel lens on the distribution of L-function zeros.

### Keywords
L-function zeros, random matrix theory, modular forms, spacing statistics, Brody ensemble, machine learning, pseudo-random number generators, zero spacing distribution

### Categories
- **Primary**: math.NT (Number Theory)
- **Secondary**: math.PR (Probability), cs.LG (Machine Learning)

### Author Information
Tobias Weiss
- Email: tobias@weiss.com
- Affiliation: Independent Researcher
- Website: https://tobias-weiss.org

---

## 🏷️ Submission Steps

1. **Go to arXiv**: https://arxiv.org/submit
2. **Log in** (or create account)
3. **Fill submission form**:
   - Title: [copy from above]
   - Authors: Tobias Weiss
   - Abstract: [copy from above]
   - Keywords: [copy from above]
   - Categories: math.NT, math.PR, cs.LG
   - Comments: "Companion code and data: https://github.com/tobias-weiss-ai-xr/riemann"
   - License: Apache 2.0
4. **Upload files**:
   - Main file: `lfunction_zeros_2026_clean.tex`
   - Ancillary files: `lfunction_zeros_2026_clean.pdf`, all 5 PNG figures
5. **Verify** in preview
6. **Submit**

---

## 🔗 Companion Materials

- **Code Repository**: https://github.com/tobias-weiss-ai-xr/riemann
- **Data**: LMFDB database (https://www.lmfdb.org/)
- **Scripts**: 
  - `scripts/task_5_spectral_rigidity_bridge.py`
  - `scripts/analyze_gue_outliers.py`
  - `scripts/generate_figures.py`
- **Data Files**: 
  - `data/lmfdb/lmfdb_zeros_ml.csv`
  - `data/results/task_5_*json`
  - `data/results/gue_outliers_dim2.csv`

---

## 📊 Paper Statistics

| Metric | Value |
|--------|-------|
| Pages | 11 |
| Figures | 5 |
| Tables | 5 |
| Word count | ~6,000 |
| File size (PDF) | 1.1 MB |
| File size (TEX) | 17.5 KB |
| Total size (with figures) | ~2 MB |

---

## 🎯 Key Results Summary

1. **Two-population structure**: dim=1 → GUE (β=1.88), dim≥2 → Poisson (β=0.24)
2. **Continuous transition**: β decreases monotonically with dimension
3. **GUE outliers**: 6% of dim≥2 forms retain GUE statistics
4. **Predictability**: Spectral rigidity predictable from metadata (R²>0.93)
5. **Characterization**: GUE outliers are low-dimension, small-level forms

---

## 📅 Timeline

| Date | Milestone |
|------|-----------|
| July 2026 | Paper drafted and figures generated |
| Ready | Can submit to arXiv now |

---

**Status**: ✅ All files ready for arXiv submission
