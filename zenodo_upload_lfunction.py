"""
Zenodo Upload Script for L-Function Zeros Paper

This script creates a ZIP archive of the L-Function paper and data
for upload to Zenodo.

Usage:
    python zenodo_upload_lfunction.py
"""
from __future__ import annotations

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_DIR = Path("C:/Users/Tobias/git/riemann")
OUTPUT_DIR = PROJECT_DIR / "zenodo"
ZIP_FILENAME = OUTPUT_DIR / "lfunction_zeros_2026_complete.zip"
DATA_ZIP = OUTPUT_DIR / "lfunction_data_2026.zip"
CODE_ZIP = OUTPUT_DIR / "lfunction_code_2026.zip"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_paper_archive():
    """Create ZIP archive of the L-Function paper."""
    print("Creating L-Function paper archive...")
    
    # Files to include
    files_to_include = [
        "papers/lfunction_zeros_2026_clean.tex",
        "papers/lfunction_zeros_2026_clean.pdf",
        "papers/beta_vs_dimension.png",
        "papers/gue_percentage_vs_dimension.png",
        "papers/level_distribution_gue_outliers.png",
        "papers/roc_curve_spectral_rigidity.png",
        "papers/spacing_vs_dimension_scatter.png",
        "papers/references.bib",
        "papers/arxiv_submission/README.md",
    ]
    
    file_list = []
    
    with zipfile.ZipFile(ZIP_FILENAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_include:
            full_path = PROJECT_DIR / file_path
            if full_path.exists():
                arcname = file_path
                zipf.write(full_path, arcname)
                file_list.append(arcname)
                print(f"  + {arcname}")
    
    print(f"\n[OK] Paper archive created: {ZIP_FILENAME}")
    print(f"  Size: {ZIP_FILENAME.stat().st_size / 1024 / 1024:.1f} MB")
    return ZIP_FILENAME, file_list


def create_data_archive():
    """Create ZIP archive of the datasets."""
    print("\nCreating L-Function data archive...")
    
    # Files to include
    data_files = [
        "data/lmfdb/lmfdb_zeros_ml.csv",
        "data/lmfdb/lmfdb_sql_weight2_ml.csv",
        "data/results/task_5_spectral_rigidity_bridge_results.json",
        "data/results/gue_outliers_dim2.csv",
        "experiments/GUE_OUTLIERS_ANALYSIS.md",
        "experiments/TASK_5_SUMMARY.md",
    ]
    
    file_list = []
    
    with zipfile.ZipFile(DATA_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in data_files:
            full_path = PROJECT_DIR / file_path
            if full_path.exists():
                arcname = file_path
                zipf.write(full_path, arcname)
                file_list.append(arcname)
                print(f"  + {arcname}")
            else:
                print(f"  ! {file_path} (not found)")
    
    if file_list:
        print(f"\n[OK] Data archive created: {DATA_ZIP}")
        print(f"  Size: {DATA_ZIP.stat().st_size / 1024 / 1024:.1f} MB")
        return DATA_ZIP, file_list
    else:
        print("\n[WARN] No data files found, skipping data archive")
        return None, []


def create_code_archive():
    """Create ZIP archive of the analysis code."""
    print("\nCreating L-Function code archive...")
    
    # Files to include
    code_files = [
        "scripts/task_5_spectral_rigidity_bridge.py",
        "scripts/analyze_gue_outliers.py",
        "scripts/generate_figures.py",
        "scripts/rho2_cc_analysis.py",
        "scripts/sato_tate_embedding_analysis.py",
        "scripts/train_gnn_enriched_features.py",
    ]
    
    file_list = []
    
    with zipfile.ZipFile(CODE_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in code_files:
            full_path = PROJECT_DIR / file_path
            if full_path.exists():
                arcname = file_path
                zipf.write(full_path, arcname)
                file_list.append(arcname)
                print(f"  + {arcname}")
            else:
                print(f"  ! {file_path} (not found)")
    
    if file_list:
        print(f"\n[OK] Code archive created: {CODE_ZIP}")
        print(f"  Size: {CODE_ZIP.stat().st_size / 1024 / 1024:.1f} MB")
        return CODE_ZIP, file_list
    else:
        print("\n[WARN] No code files found, skipping code archive")
        return None, []


def create_upload_instructions(paper_zip, paper_files, data_zip=None, data_files=None, code_zip=None, code_files=None):
    """Create instructions for Zenodo upload."""
    instructions = f"""
# Zenodo Upload Instructions — L-Function Zeros Paper & Data

**Last updated**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

## 📦 Archives Created

### Paper Archive
**File**: {paper_zip.name}
**Size**: {paper_zip.stat().st_size / 1024 / 1024:.1f} MB
**Status**: [OK] Ready for upload

### Data Archive
**File**: {data_zip.name if data_zip else 'N/A'}
**Size**: {data_zip.stat().st_size / 1024 / 1024:.1f} MB
**Status**: {'[OK] Ready for upload' if data_zip else '[SKIPPED] No data files found'}

### Code Archive
**File**: {code_zip.name if code_zip else 'N/A'}
**Size**: {code_zip.stat().st_size / 1024 / 1024:.1f} MB
**Status**: {'[OK] Ready for upload' if code_zip else '[SKIPPED] No code files found'}

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
| v1.0.0 | {datetime.now().strftime("%Y-%m-%d")} | Initial public release |

---

## 🔗 Related Identifiers

After arXiv submission, add:
- arXiv: 10.48550/arXiv.2607.xxxxx
- GitHub: https://github.com/tobias-weiss-ai-xr/riemann
- Companion paper (CayleySpec): 10.48550/arXiv.2607.xxxxx

---

## 🏗️ Archive Contents

### Paper Archive ({paper_zip.name})
"""
    
    instructions += "\n\nContained files:\n"
    for f in sorted(paper_files):
        instructions += f"- `{f}`\n"

    if data_zip:
        instructions += f"""
### Data Archive ({data_zip.name})

Contained files:
"""
        for f in sorted(data_files):
            instructions += f"- `{f}`\n"

    if code_zip:
        instructions += f"""
### Code Archive ({code_zip.name})

Contained files:
"""
        for f in sorted(code_files):
            instructions += f"- `{f}`\n"

    instructions += f"""
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
     - {paper_zip.name}
     - {data_zip.name if data_zip else 'N/A'}
     - {code_zip.name if code_zip else 'N/A'}

5. **Metadata**:
   - Version: v1.0.0
   - Publication date: {datetime.now().strftime("%Y-%m-%d")}
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
- Upload: {paper_zip.name} + {code_zip.name if code_zip else 'N/A'}
- Metadata: Same as above
- DOI: 10.xxxx/zenodo.xxxxx (paper)

**Deposit 2: Data**
- Upload: {data_zip.name if data_zip else 'N/A'}
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
**{OUTPUT_DIR}**

Run this command to list them:
```bash
ls -lh {OUTPUT_DIR}
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
- Local path: {OUTPUT_DIR}

---

**Created by**: Zenodo Upload Script
**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    instructions_file = OUTPUT_DIR / "ZENODO_UPLOAD_LFUNCTION.md"
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print(f"\n[OK] Instructions saved to: {instructions_file}")
    return instructions_file


def main():
    """Main function."""
    print("="*70)
    print("Zenodo Upload Script for L-Function Zeros Paper")
    print("="*70)
    print()
    
    # Create archives
    paper_zip, paper_files = create_paper_archive()
    data_zip, data_files = create_data_archive()
    code_zip, code_files = create_code_archive()
    
    print()
    
    # Create instructions
    instructions_file = create_upload_instructions(paper_zip, paper_files, data_zip, data_files, code_zip, code_files)
    
    print()
    print("="*70)
    print("[OK] ALL ZENODO UPLOAD FILES PREPARED")
    print("="*70)
    print()
    
    # List all created files
    print("Created files:")
    if paper_zip.exists():
        print(f"  ✓ Paper: {paper_zip.name} ({paper_zip.stat().st_size / 1024 / 1024:.1f} MB)")
    if data_zip and data_zip.exists():
        print(f"  ✓ Data: {data_zip.name} ({data_zip.stat().st_size / 1024 / 1024:.1f} MB)")
    if code_zip and code_zip.exists():
        print(f"  ✓ Code: {code_zip.name} ({code_zip.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  ✓ Instructions: {instructions_file.name}")
    print()
    
    # Calculate total size
    total_size = 0
    if paper_zip.exists():
        total_size += paper_zip.stat().st_size
    if data_zip and data_zip.exists():
        total_size += data_zip.stat().st_size
    if code_zip and code_zip.exists():
        total_size += code_zip.stat().st_size
    
    print(f"Total archive size: {total_size / 1024 / 1024:.1f} MB")
    print()
    
    print("Next steps:")
    print("  1. Visit https://zenodo.org/deposit")
    print("  2. Click 'New upload'")
    print("  3. Upload all created ZIP files")
    print("  4. Fill in metadata (see instructions file)")
    print("  5. Publish")
    print()
    print("Estimated time: 15-30 minutes")
    print("="*70)


if __name__ == "__main__":
    main()
