# Complex Multiplication Detection in Weight 2 Cusp Forms - arXiv Submission

## Overview
This directory contains the LaTeX source and arXiv submission materials for the CM paper.

## Files
- paper.tex - Main LaTeX document (generated from cm_paper.md via pandoc)
- paper.pdf - Compiled PDF (8 pages)
- efs.bib - Bibliography file with 3 references
- bstract.txt - arXiv abstract
- keywords.txt - arXiv submission keywords
- igures/ - Publication-quality figures
  - ig1_model_performance.pdf - Model performance metrics + confusion matrix
  - ig2_feature_importance.pdf - Feature importance analysis
  - ig3_key_findings.pdf - Key findings summary
  - ig4_discriminative_feature.pdf - M₄/M₂ discriminative analysis

## Compilation
To compile the paper:
`ash
xelatex paper.tex
bibtex paper
xelatex paper.tex
xelatex paper.tex
`

## Paper Structure
1. Introduction (Background, Motivation, Contributions)
2. Data and Methods (Dataset, Features, Model, Evaluation)
3. Results (Performance, Feature Importance, Analysis)
4. Discussion (Why CM is Learnable, Comparison, Limitations, Future Work)
5. Conclusion
6. Appendix A (Implementation Details)

## Key Findings
- F1 = 0.900 on 10,756 test samples
- Top feature: M₄/M₂ (importance 0.157)
- 8/8 misclassifications (0.074% error rate)
- Dataset: 53,779 forms, 213 CM (0.40%)

## Submission Notes
- Primary category: Number Theory (math.NT)
- Secondary category: Machine Learning (cs.LG)
- 8 pages, 4 figures
- 3 references

## Dependencies
- LaTeX with xelatex compiler
- Standard packages: graphicx, amsmath, booktabs, hyperref
- No special fonts required

---
Generated for arXiv submission - June 2026
