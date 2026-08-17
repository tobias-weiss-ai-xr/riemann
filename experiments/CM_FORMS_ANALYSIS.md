# CM Forms Analysis: Do Complex Multiplication Forms Explain the GUE Outliers?

**Date:** 2026-08-17
**Script:** `scripts/analyze_cm_forms.py`
**Status:** COMPLETED

## Motivation

The L-function zero spacing paper identifies 1,748 "GUE outliers" among dim≥2 forms (6.0% of 29,216) that retain GUE statistics despite the dim≥2 population being predominantly Poisson (β=0.24). The paper characterizes these outliers as "low-dimension, small-level" forms but does not test whether they are CM (complex multiplication) forms.

**Hypothesis:** CM forms are arithmetically closest to elliptic curves (dim=1, which are all GUE). If CM status explains the GUE outliers, we expect the 1,748 outliers to be predominantly CM.

## Method

1. Merge `is_cm` from `lmfdb_sql_weight2_ml.csv` into `lmfdb_zeros_ml.csv` (63,844 forms, join on `label`)
2. Recompute GUE/GOE preference via KS test (same method as `analyze_gue_outliers.py`)
3. Split by dim≥2 and analyze CM vs non-CM
4. Chi-square test, Fisher's exact test, Cramér's V effect size

## Results

### Contingency Table (dim≥2)

|  | GUE | GOE | Total |
|---|---|---|---|
| **non-CM** | 1,729 | 27,384 | 29,113 |
| **CM** | 19 | 84 | 103 |
| **Total** | 1,748 | 27,468 | 29,216 |

### Key Statistics

| Metric | Value |
|---|---|
| CM forms preferring GUE | 19 / 103 (18.4%) |
| non-CM forms preferring GUE | 1,729 / 29,113 (5.9%) |
| CM fraction of all GUE outliers | 19 / 1,748 (1.1%) |
| CM fraction of all dim≥2 | 103 / 29,216 (0.4%) |
| **Enrichment factor** | **3.58×** |
| Chi-square | χ²=26.36, p=2.8×10⁻⁷ |
| Fisher's exact | OR=3.58, p=1.0×10⁻⁵ |
| Cramér's V | 0.030 |

### Per-Dimension Breakdown

| dim | total | CM | non-CM | GUE (CM) | GUE (non-CM) | CM% |
|---|---|---|---|---|---|---|
| 2 | 8,263 | 60 | 8,203 | 12/60 (20.0%) | 961/8,203 (11.7%) | 0.7% |
| 3 | 4,319 | 14 | 4,305 | 3/14 (21.4%) | 246/4,305 (5.7%) | 0.3% |
| 4 | 3,157 | 24 | 3,133 | 3/24 (12.5%) | 109/3,133 (3.5%) | 0.8% |
| 5 | 2,096 | 3 | 2,093 | 1/3 (33.3%) | 79/2,093 (3.8%) | 0.1% |
| 6 | 1,814 | 2 | 1,812 | 0/2 (0.0%) | 58/1,812 (3.2%) | 0.1% |

### dim=1 Comparison

| Group | GUE preference |
|---|---|
| CM forms | 121 / 232 (52.2%) |
| non-CM forms | 15,651 / 34,396 (45.5%) |

CM forms in dim=1 also show slightly higher GUE preference (52.2% vs 45.5%), consistent with the dim≥2 pattern.

## Interpretation

**CM forms are 3.6× more likely to be GUE outliers** (18.4% vs 5.9%, p=10⁻⁵). This is statistically significant and arithmetically sensible: CM forms have extra endomorphisms that make them "closer" to elliptic curves, and elliptic curves (dim=1) are the GUE population.

**However, CM forms are too rare to be the primary explanation.** Only 103 CM forms exist in dim≥2 (0.4%), and they account for only 1.1% of the 1,748 GUE outliers. The remaining 98.9% of GUE outliers are non-CM.

**Verdict: PARTIALLY CONFIRMED.** CM status is a statistically significant enrichment factor (3.6×, p=10⁻⁵) but explains only 1.1% of the GUE outliers. The GUE outliers are predominantly non-CM forms driven by some other arithmetic property — likely low dimension and small conductor level (as already identified in the paper).

## Implications for the Paper

1. **Add a sentence to the GUE outliers section**: "CM forms are 3.6× enriched among GUE outliers (18.4% vs 5.9%, p=10⁻⁵), but account for only 1.1% of outliers due to their rarity (0.4% of dim≥2)."

2. **No change to the paper's conclusions**: The two-population structure (dim=1→GUE, dim≥2→Poisson) and the 6% outlier rate are unchanged. CM is a minor contributing factor, not the primary explanation.

3. **Future work**: The 98.9% non-CM GUE outliers suggest that low dimension and small level (not CM) are the primary drivers. A more detailed analysis of conductor level distributions within the GUE outliers would be the next step.

## Files

- `scripts/analyze_cm_forms.py` — analysis script
- `data/results/cm_forms_analysis.json` — summary statistics
- `data/results/cm_merged_dim2.csv` — merged dataset with is_cm + prefers_gue
- `papers/cm_forms_analysis.png` — figure (GUE rate by dimension: CM vs non-CM + contingency table heatmap)
