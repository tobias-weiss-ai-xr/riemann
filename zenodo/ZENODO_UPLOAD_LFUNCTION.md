
# Zenodo Upload Instructions — L-Function Zeros Paper & Data

**Last updated**: 2026-08-04 05:42

---

## 📦 Archives Created

### Paper Archive
**File**: lfunction_zeros_2026_complete.zip
**Size**: 2.4 MB
**Status**: [OK] Ready for upload

### Data Archive
**File**: lfunction_data_2026.zip
**Size**: 12.8 MB
**Status**: [OK] Ready for upload

### Code Archive
**File**: lfunction_code_2026.zip
**Size**: 0.0 MB
**Status**: [OK] Ready for upload

---

## 📝 Metadata for Zenodo

### Upload Type
- **Primary**: Publication
- **Secondary**: Software, Dataset

### Title
The Two-Population Structure of L-Function Zero Spacings: dim=1 to GUE, dim>=2 to Poisson with 6% Outliers

### Creators
- Name: Tobias Weiss
- Affiliation: Independent Researcher
- ORCID: [TO BE ADDED]
- Email: tobias@weiss.com

### Description

This repository contains the complete analysis code, data, and paper for the L-Function zero spacing study. 

#### Key Findings:
1. **Two-population structure**: dim=1 forms exhibit GUE statistics (Brody β=1.88), dim>=2 forms exhibit near-Poisson statistics (β=0.24)
2. **Continuous transition**: β decreases monotonically with dimension
3. **GUE outliers**: 6% of dim>=2 forms retain GUE statistics, characterized as low-dimension, small-level forms
4. **Predictability**: Spectral rigidity properties are predictable from scalar metadata alone with R²>0.93

#### Datasets:
- 63,844 weight-2 newforms from LMFDB database
- 10 lowest zeros per form
- First 100-1000 Hecke eigenvalues per form
- Scalar metadata: dimension, level, analytic rank, etc.

#### Results:
- Brody β parameters for each dimension group
- GUE preference classification for each form
- Spectral rigidity predictions from metadata
- Comprehensive outlier characterization

### Keywords
L-function zeros, random matrix theory, modular forms, spacing statistics, Brody ensemble, machine learning, GUE, Poisson, Hecke operators, LMFDB

### License
Apache 2.0

---

## 🎯 Version Information

| Version | Date | Description |
|---------|------|-------------|
| v1.0.0 | 2026-08-04 | Initial public release |

---

## 🔗 Related Identifiers

After arXiv submission, add:
- arXiv: 10.48550/arXiv.2607.xxxxx
- GitHub: https://github.com/tobias-weiss-ai-xr/riemann
- Companion paper (CayleySpec): 10.48550/arXiv.2607.xxxxx

---

## 🏗️ Archive Contents

### Paper Archive (lfunction_zeros_2026_complete.zip)


Contained files:
- `papers/arxiv_submission/README.md`
- `papers/beta_vs_dimension.png`
- `papers/gue_percentage_vs_dimension.png`
- `papers/level_distribution_gue_outliers.png`
- `papers/lfunction_zeros_2026_clean.pdf`
- `papers/lfunction_zeros_2026_clean.tex`
- `papers/roc_curve_spectral_rigidity.png`
- `papers/spacing_vs_dimension_scatter.png`

### Data Archive (lfunction_data_2026.zip)

Contained files:
- `data/lmfdb/lmfdb_sql_weight2_ml.csv`
- `data/lmfdb/lmfdb_zeros_ml.csv`
- `data/results/gue_outliers_dim2.csv`
- `data/results/task_5_spectral_rigidity_bridge_results.json`
- `experiments/GUE_OUTLIERS_ANALYSIS.md`
- `experiments/TASK_5_SUMMARY.md`

### Code Archive (lfunction_code_2026.zip)

Contained files:
- `scripts/analyze_gue_outliers.py`
- `scripts/rho2_cc_analysis.py`
- `scripts/sato_tate_embedding_analysis.py`
- `scripts/task_5_spectral_rigidity_bridge.py`
- `scripts/train_gnn_enriched_features.py`

---

## 📁 Upload Steps

### Option A: Create One Combined Deposit (RECOMMENDED)

1. Go to: https://zenodo.org/deposit
2. Click "New upload"
3. **Basic Information**:
   - Upload type: Publication
   - Title: [from above]
   - Creators: [from above]
   - Description: [from above]
   - Keywords: [from above]
   - License: Apache 2.0

4. **Files**:
   - Upload **all three ZIP files**:
     - lfunction_zeros_2026_complete.zip
     - lfunction_data_2026.zip
     - lfunction_code_2026.zip

5. **Metadata**:
   - Version: v1.0.0
   - Publication date: 2026-08-04
   - Communities: Number Theory, Machine Learning
   - Grants: None
   - References: https://github.com/tobias-weiss-ai-xr/riemann

6. **Access**:
   - Access: Public (recommended)
   - Reserve DOI: No

7. **Publish**: Click "Publish" button

8. **After Publishing**:
   - Note the DOI: 10.xxxx/zenodo.xxxxx
   - Update GitHub README with DOI badge
   - Add DOI to arXiv paper if already submitted

### Option B: Create Separate Deposits

**Deposit 1: Paper + Code**
- Upload: lfunction_zeros_2026_complete.zip + lfunction_code_2026.zip
- Metadata: Same as above
- DOI: 10.xxxx/zenodo.xxxxx (paper)

**Deposit 2: Data**
- Upload: lfunction_data_2026.zip
- Upload type: Dataset
- Title: "L-Function Zero Spacing Data - 63,844 Weight-2 Newforms"
- DOI: 10.xxxx/zenodo.yyyyy

---

## ✅ Verification Checklist

Before publishing:
- [ ] All ZIP files uploaded
- [ ] Title is correct and descriptive
- [ ] Authors are complete
- [ ] Description is informative
- [ ] Keywords are relevant
- [ ] License is specified
- [ ] Version is set
- [ ] Publication date is correct
- [ ] Access is set to Public

After publishing:
- [ ] DOI noted
- [ ] GitHub README updated
- [ ] arXiv paper updated (if applicable)
- [ ] Social media announcement prepared

---

## 🔗 File Locations

All created archives are in:
**C:\Users\Tobias\git\riemann\zenodo**

Run this command to list them:
```bash
ls -lh C:\Users\Tobias\git\riemann\zenodo
```

---

## ⏱️ Estimated Time

| Task | Time |
|------|------|
| Create archives | 1-2 minutes (DONE) |
| Upload to Zenodo | 5-10 minutes |
| Fill metadata | 10-15 minutes |
| Publish | 1 minute |
| **Total** | **15-30 minutes** |

---

## 🎉 Status

All archives have been created and are ready for upload!

**Next action**: Visit https://zenodo.org/deposit and upload the archives.

---

## 💡 Tips

1. **One deposit vs multiple**: One combined deposit is simpler and keeps everything together.

2. **DOI linking**: After publishing both papers (CayleySpec and L-function), remember to link them:
   - Add CayleySpec DOI to L-function Zenodo deposit
   - Add L-function DOI to CayleySpec Zenodo deposit

3. **GitHub integration**: Zenodo can automatically archive GitHub releases. Consider creating a release on GitHub and connecting it to Zenodo.

4. **Versioning**: For future updates, increment the version number and reference the previous DOI.

---

## 📞 Need Help?

- Zenodo help: https://help.zenodo.org/
- Contact: support@zenodo.org
- Local path: C:\Users\Tobias\git\riemann\zenodo

---

**Created by**: Zenodo Upload Script
**Date**: 2026-08-04 05:42:35
