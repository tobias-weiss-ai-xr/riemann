# Zenodo Upload Master Guide — CayleySpec + L-Function Papers

**Status**: ✅ All archives ready for upload  
**Date**: July 2026  
**Author**: Tobias Weiss

---

## 📦 QUICK OVERVIEW

| Project | Archive | Size | Status |
|---------|---------|------|--------|
| **CayleySpec** | `cayleyspec-v1.0.0-complete.zip` | 262 KB | ✅ Ready |
| **L-Function Paper** | `lfunction_zeros_2026_complete.zip` | 2.5 MB | ✅ Ready |
| **L-Function Data** | `lfunction_data_2026.zip` | 12.8 MB | ✅ Ready |
| **L-Function Code** | `lfunction_code_2026.zip` | 26 KB | ✅ Ready |

**Total**: 4 archives, ~16 MB total

---

## 🎯 UPLOAD OPTIONS

### Option A: One Combined Deposit (RECOMMENDED)

Create **one** Zenodo deposit containing all 4 archives.

**Pros**: Simpler, everything in one place, one DOI
**Cons**: Larger deposit, less granular

### Option B: Two Separate Deposits

**Deposit 1: CayleySpec**
- Archive: `cayleyspec-v1.0.0-complete.zip`
- DOI: 10.xxxx/zenodo.xxxxx

**Deposit 2: L-Function**
- Archives: All 3 L-function ZIP files
- DOI: 10.xxxx/zenodo.yyyyy

**Pros**: Clean separation, individual DOIs
**Cons**: Two deposits to manage

### Option C: Three Separate Deposits (Most Granular)

**Deposit 1: CayleySpec**
- Archive: `cayleyspec-v1.0.0-complete.zip`

**Deposit 2: L-Function Paper+Code**
- Archives: `lfunction_zeros_2026_complete.zip` + `lfunction_code_2026.zip`

**Deposit 3: L-Function Data**
- Archive: `lfunction_data_2026.zip`

**Pros**: Very granular, separate DOIs for paper, code, data
**Cons**: Three deposits to manage

---

## 📝 RECOMMENDATION: OPTION A (Combined)

**Use one deposit with all 4 archives.** This keeps everything together and makes linking easier.

---

## 🚀 UPLOAD INSTRUCTIONS (Option A - Combined)

### Step 1: Create New Deposit
1. Go to: https://zenodo.org/deposit
2. Click "New upload"
3. Select "Software" or "Publication" as upload type

### Step 2: Upload Files
Upload all 4 ZIP archives:
- `cayleyspec-v1.0.0-complete.zip` (from `lean/zenodo/`)
- `lfunction_zeros_2026_complete.zip` (from `riemann/zenodo/`)
- `lfunction_data_2026.zip` (from `riemann/zenodo/`)
- `lfunction_code_2026.zip` (from `riemann/zenodo/`)

### Step 3: Fill Metadata

| Field | Value |
|-------|-------|
| **Upload type** | Publication |
| **Title** | CayleySpec + L-Function Zeros: Complete Formal and Empirical Analysis |
| **Creators** | Tobias Weiss (Independent Researcher, tobias@weiss.com) |
| **Description** | See below |
| **Keywords** | Lean 4, formal verification, mathlib, Cayley graphs, Hecke operators, modular forms, GNN, expressivity, L-function zeros, random matrix theory, spacing statistics |
| **License** | Apache 2.0 |
| **Version** | v1.0.0 |
| **Publication date** | 2026-07-XX (today) |
| **Communities** | Number Theory, Formal Methods, Machine Learning |
| **References** | https://github.com/tobias-weiss-ai-xr/CayleySpec, https://github.com/tobias-weiss-ai-xr/riemann |

### Step 4: Description (Copy-Paste)

```
This repository contains the complete source code, datasets, and papers for two complementary research projects: CayleySpec (formal verification) and L-Function Zero Statistics (empirical analysis).

## CayleySpec (Formal Methods)
CayleySpec is the first complete formalization in Lean 4 of the dictionary between Cayley graph spectral theory and Hecke eigenvalue theory for modular forms.

- 3,265 Lean jobs, 0 errors, 0 admitted theorems
- All theorems proven including boundedness at cusps
- Proofs of vertex-transitivity, Peter-Weyl theorem, SL(2,Z)-invariance, holomorphy
- Companion paper: "A Formal Dictionary between Cayley Graph Spectra and Hecke Eigenvalues"
- Built with Lean 4.31.0 and mathlib v4.31.0

## L-Function Zero Statistics (ML + Number Theory)
Large-scale empirical study of L-function zero spacing statistics for modular forms.

- 63,844 weight-2 newforms from LMFDB database
- Discovery: Two-population structure (dim=1 → GUE, dim≥2 → Poisson)
- GUE outliers: 6% of dim≥2 forms retain GUE statistics
- Predictability: Spectral rigidity from metadata (R²>0.93)
- Paper: "The Two-Population Structure of L-Function Zero Spacings"
- 5 publication-ready figures

## Archive Contents
- cayleyspec-v1.0.0-complete.zip: CayleySpec source code and paper
- lfunction_zeros_2026_complete.zip: L-Function paper and figures
- lfunction_data_2026.zip: Raw datasets (12.8 MB)
- lfunction_code_2026.zip: Analysis code (26 KB)

## Related arXiv Submissions
- CayleySpec: [TO BE ADDED]
- L-Function: [TO BE ADDED]

## License
Apache 2.0 License — see LICENSE files in individual archives
```

### Step 5: Set Access & Publish
1. **Access**: Public (recommended)
2. **Reserve DOI**: No (will be created on publish)
3. Click **"Publish"** button
4. Confirm metadata
5. Wait for DOI assignment (typically within 24 hours)

### Step 6: After Publishing
1. Note the DOI: 10.xxxx/zenodo.xxxxx
2. Update GitHub READMEs in both repositories
3. Update arXiv paper "Comments" sections with DOI
4. Announce on social media

---

## 📁 FILE LOCATIONS

### CayleySpec Archive
```
C:/Users/Tobias/git/lean/zenodo/cayleyspec-v1.0.0-complete.zip
```
**Contents**: CayleySpec source code, companion paper, README, LICENSE

### L-Function Archives
```
C:/Users/Tobias/git/riemann/zenodo/
├── lfunction_zeros_2026_complete.zip    # Paper + figures
├── lfunction_data_2026.zip            # Datasets (12.8 MB)
├── lfunction_code_2026.zip            # Analysis code
└── ZENODO_UPLOAD_LFUNCTION.md          # Detailed instructions
```

---

## 📊 ARCHIVE DETAILS

### CayleySpec Archive
- **Filename**: cayleyspec-v1.0.0-complete.zip
- **Size**: 262 KB
- **Files**:
  - CayleySpec/ (all .lean files)
  - CayleySpec.lean
  - paper/cayleyspec.tex
  - paper/cayleyspec.pdf
  - paper/references.bib
  - lakefile.toml
  - lean-toolchain
  - lake-manifest.json
  - README.md
  - LICENSE

### L-Function Paper Archive
- **Filename**: lfunction_zeros_2026_complete.zip
- **Size**: 2.5 MB
- **Files**:
  - papers/lfunction_zeros_2026_clean.tex
  - papers/lfunction_zeros_2026_clean.pdf
  - papers/beta_vs_dimension.png
  - papers/gue_percentage_vs_dimension.png
  - papers/level_distribution_gue_outliers.png
  - papers/roc_curve_spectral_rigidity.png
  - papers/spacing_vs_dimension_scatter.png
  - papers/arxiv_submission/README.md

### L-Function Data Archive
- **Filename**: lfunction_data_2026.zip
- **Size**: 12.8 MB
- **Files**:
  - data/lmfdb/lmfdb_zeros_ml.csv
  - data/lmfdb/lmfdb_sql_weight2_ml.csv
  - data/results/task_5_spectral_rigidity_bridge_results.json
  - data/results/gue_outliers_dim2.csv
  - experiments/GUE_OUTLIERS_ANALYSIS.md
  - experiments/TASK_5_SUMMARY.md

### L-Function Code Archive
- **Filename**: lfunction_code_2026.zip
- **Size**: 26 KB
- **Files**:
  - scripts/task_5_spectral_rigidity_bridge.py
  - scripts/analyze_gue_outliers.py
  - scripts/rho2_cc_analysis.py
  - scripts/sato_tate_embedding_analysis.py
  - scripts/train_gnn_enriched_features.py

---

## ⚡ QUICK START

If you just want to get this done quickly:

1. **Go to**: https://zenodo.org/deposit
2. **New upload**
3. **Upload all 4 ZIP files** from their respective zenodo/ directories
4. **Copy metadata** from above
5. **Publish**
6. **Note DOI**

**Time required**: 15-20 minutes

---

## ✅ VERIFICATION CHECKLIST

Before publishing:
- [ ] All 4 ZIP files uploaded
- [ ] Title is descriptive
- [ ] Authors are complete (name, affiliation, email)
- [ ] Description is informative and complete
- [ ] Keywords cover all relevant topics
- [ ] License is Apache 2.0
- [ ] Version is v1.0.0
- [ ] Publication date is correct
- [ ] Access is set to Public
- [ ] Communities are selected (Number Theory, Formal Methods, Machine Learning)
- [ ] References/links are included

After publishing:
- [ ] DOI noted
- [ ] GitHub READMEs updated with DOI badge
- [ ] arXiv papers updated (if already submitted)
- [ ] Social media announcement prepared
- [ ] Emailed to collaborators (if any)

---

## 🎯 RECOMMENDED WORKFLOW

### Day 1: Submit to arXiv
1. Submit CayleySpec to arXiv
2. Submit L-Function paper to arXiv
3. Note arXiv IDs

### Day 1 (continued): Upload to Zenodo
1. Upload all 4 archives to Zenodo (combined deposit)
2. Fill in metadata
3. Publish
4. Note Zenodo DOI

### Day 2: Update Links
1. Update GitHub READMEs with arXiv and Zenodo links
2. Add DOIs to arXiv paper "Comments" sections
3. Prepare announcements

### Day 3: Announce
1. Twitter/LinkedIn/Mastodon
2. Lean Zulip (for CayleySpec)
3. Number Theory Discord (for L-function)
4. ML Reddit (for L-function)
5. Personal website/blog

---

## 💡 TIPS

### When to Link DOIs
- **arXiv → Zenodo**: Add Zenodo DOI to arXiv paper "Comments" section
- **Zenodo → arXiv**: Add arXiv DOI to Zenodo description
- **GitHub → Both**: Add badges with both DOIs to READMEs

### File Size Considerations
- CayleySpec: 262 KB (very small)
- L-Function Paper: 2.5 MB (reasonable)
- L-Function Data: 12.8 MB (large but acceptable)
- L-Function Code: 26 KB (tiny)
- **Total**: ~16 MB (well within Zenodo limits)

### Versioning
- For future updates, create new version (v1.1.0, v2.0.0, etc.)
- Reference previous version's DOI in new version

### GitHub Integration
- Zenodo can automatically archive GitHub releases
- Consider creating GitHub releases and connecting to Zenodo
- This enables automatic DOI assignment on release

---

## 📞 NEED HELP?

- Zenodo help: https://help.zenodo.org/
- Zenodo support: support@zenodo.org
- Local archives: See file locations above

---

## 🎉 STATUS: READY TO UPLOAD

**All archives are created and ready.**

**Next immediate action**: Visit https://zenodo.org/deposit and upload all 4 ZIP files.

---

*"The journey of a thousand miles begins with a single step." — Lao Tzu*

*"You've done the research. Now share it with the world." — This guide*
