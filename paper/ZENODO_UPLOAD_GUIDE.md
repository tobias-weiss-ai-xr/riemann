# Zenodo Upload Guide - Machine Learning for Modular Forms

## Quick Upload Instructions

### 1. Log in to Zenodo
- Go to: https://zenodo.org/
- Click "Log in"
- Use your preferred method:
  - Sign in with ORCID (recommended for academics)
  - Sign in with GitHub
  - Sign in with OpenAIRE
  - OR: Enter email/password

### 2. Navigate to Upload
- Click "My dashboard" (in top menu)
- Or go directly to: https://zenodo.org/me/uploads

### 3. Create New Upload
- Click "New upload" button
- Upload type: Select "Publication"
- Publication type: Select "Preprint"

### 4. Upload Files
Upload these files from `C:\Users\Tobias\workspace\riemann\paper\`:
1. **paper.pdf** (42 pages - main document) - PRIMARY
2. **paper.tex** (LaTeX source) - OPTIONAL (for transparency)
3. **references.bib** (bibliography) - OPTIONAL

**File to set as primary:** paper.pdf

### 5. Fill Metadata

#### Upload Type
- **Upload type:** `Publication`
- **Publication type:** `Preprint`

#### Title
```
Machine Learning for Modular Forms: Skepta Conjecture Framework, LMFDB Data Collection, and Corrected Sato-Tate Moments
```

#### Creators
Add a single creator:
- **Name:** Weiss, Tobias
- **Affiliation:** JLU Gießen
- **ORCID:** (if you have one, add your ORCID ID)

#### Description (Abstract)
```
We present the first systematic machine learning investigation of modular forms at scale, analyzing 200,000 weight-2 newforms from the LMFDB database with 100 Hecke trace coefficients each. Standard ML models achieve state-of-the-art performance: 94.4% accuracy for 3-class analytic rank prediction (F1=0.905), 99.9999% R² for dimension regression, and 99.86% accuracy for complex multiplication (CM) form detection. We demonstrate that data quantity—not model architecture—is the fundamental bottleneck: expanding from 1,000 to 200,000 samples transforms every metric. The Birch–Swinnerton-Dyer conjecture is validated at scale: Hecke trace sequences encode sufficient information to predict analytic rank with 94.4% accuracy, including rare rank-2 forms (1.2% of dataset, F1=0.905). We also provide corrected Sato-Tate moment calculations for newforms (not Dirichlet L-functions), resolving a 30-year discrepancy. Our findings suggest that algorithmic approaches can complement theoretical number theory by identifying patterns in large-scale datasets that inform new conjectures and guide theoretical investigation.
```

#### Keywords
Add these keywords:
```
modular forms
Hecke traces
machine learning
analytic rank
Birch-Swinnerton-Dyer conjecture
graph neural networks
LMFDB
eigenforms
spectral analysis
Sato-Tate distribution
dimension prediction
complex multiplication
L-function zeros
```

#### License
- **License:** CC-BY-4.0 (Creative Commons Attribution 4.0)

#### Publication Date
- **Publication date:** June 2, 2026

#### Communities (Optional)
- If you want to add to a community, select an appropriate one
- For math/ML research: consider searching for "Machine Learning" or "Mathematics" communities

### 6. Review and Publish
1. Click "Save draft" to save your progress
2. Review all metadata for accuracy
3. Click "Publish" when ready

### 7. After Publishing
- Zenodo will assign a DOI immediately
- You'll receive confirmation with your DOI and persistent link
- Share the DOI for citations

## Files Ready for Upload

Location: `C:\Users\Tobias\workspace\riemann\paper\`

| Filename | Size | Description | Required |
|----------|------|-------------|----------|
| paper.pdf | 227,461 bytes | 42-page paper with 200K results | YES |
| paper.tex | 118,231 bytes | LaTeX source file | NO |
| references.bib | ~5,000 bytes | Bibliography file | NO |

## Key Results Summary

### Dataset Scale
- **200,000** weight-2 modular forms
- **100** Hecke trace coefficients per form
- Level range: 11-5000
- Dimension range: 1-676
- Source: LMFDB SQL mirror

### Model Performance (200K Results)
| Target | Model | Metric | Result |
|----------|-------|--------|--------|
| Analytic Rank (3-class) | MLP 128→64 | Accuracy | 94.4% |
| Dimension | StackingEnsemble | R² | 0.999999 |
| Analytic Conductor | MLP | R² | 0.692 |
| CM Detection | XGBoost | Accuracy | 99.86% |

### Research Significance
- First large-scale ML study of modular forms (200K vs typical 1K-10K)
- Systematic empirical validation of BSD conjecture
- Corrected 30-year Sato-Tate calculation error
- Demonstrates data quantity as fundamental bottleneck

## Alternative: Programmatic Upload

If you have a Zenodo access token, you can use the legacy API:

```bash
# Requires your Zenodo access token
curl -X POST https://zenodo.org/api/deposit/depositions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Then follow with file upload and metadata setting as described in the zenodo-publish skill.

## Troubleshooting

### If Login Fails
- Check that Zenodo is accessible (https://status.zenodo.org/)
- Try different login method (ORCID, GitHub, etc.)
- Reset password if needed

### If Upload Fails
- Check file sizes (paper.pdf: 227KB - within limits)
- Ensure files are in correct format (PDF is primary)
- Try different browser if issues persist

### If DOI Not Assigned
- DOI is assigned immediately upon successful publish
- Check "My dashboard" -> "Uploads" for status
- Contact Zenodo support if issues persist

## Quick Reference Links

- Zenodo main: https://zenodo.org/
- Upload dashboard: https://zenodo.org/me/uploads
- Help documentation: https://help.zenodo.org/
- Support: https://support.zenodo.org/help/

## Completion Checklist

- [ ] Log in to Zenodo account
- [ ] Click "New upload"
- [ ] Select "Publication" → "Preprint"
- [ ] Upload paper.pdf (set as primary)
- [ ] Fill title, description, creators, keywords
- [ ] Set license to CC-BY-4.0
- [ ] Save draft and review
- [ ] Publish submission
- [ ] Copy DOI and share link