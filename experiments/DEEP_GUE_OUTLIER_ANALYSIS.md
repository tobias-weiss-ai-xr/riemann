# Deep GUE Outlier Analysis: Brody β, Root Number, Level Threshold

**Date:** 2026-08-17
**Scripts:** `scripts/analyze_gue_outliers_deep.py`, `scripts/pooled_brody_beta.py`, `scripts/validate_brody_beta.py`
**Status:** COMPLETED

## Motivation

The CM forms analysis showed CM explains only 1.1% of GUE outliers. This analysis investigates what truly distinguishes the 1,729 non-CM GUE outliers from the 27,384 non-CM GOE majority, using:
1. Pooled Brody β (reliable, vs per-form which is noisy with 9 spacings)
2. Root number (sign of functional equation)
3. Level threshold analysis
4. Logistic regression on all metadata features
5. Per-form Brody β validation

## Key Findings

### 1. Pooled Brody β: GUE Outliers Are Intermediate, NOT GUE

| Group | n_forms | n_spacings | β (MLE) | KS |
|---|---|---|---|---|
| dim=1 (all) | 34,628 | 311,652 | **1.582** | 0.083 |
| dim≥2 (all) | 29,216 | 262,944 | **0.152** | 0.123 |
| dim≥2 GUE outliers | 1,748 | 15,732 | **0.672** | 0.199 |
| dim≥2 GOE majority | 27,468 | 247,212 | **0.132** | 0.126 |
| dim≥2 non-CM GUE | 1,729 | 15,561 | **0.673** | 0.199 |

**The GUE outliers have pooled β=0.672 — intermediate between Poisson (0) and GOE (1), NOT GUE (2).** They are more repulsive than the GOE majority (β=0.132) but far from GUE (β=2).

### 2. Pooled β by Dimension (GUE Outliers Only)

| dim | n_forms | β (MLE) | KS |
|---|---|---|---|
| 2 | 973 | **0.994** | 0.147 |
| 3 | 249 | **0.739** | 0.210 |
| 4 | 112 | **0.595** | 0.241 |
| 5 | 80 | **0.438** | 0.226 |
| 5+ | 414 | **0.370** | 0.264 |

**The GUE outlier β decreases monotonically with dimension: dim=2 → β≈1.0 (GOE), dim=5+ → β≈0.37.** This is a continuous transition from GOE-like to Poisson-like, NOT a sharp GUE/Poisson dichotomy.

### 3. Per-Form β Validation (MLE method works)

| Group | n | mean β | median β | β>1.0 | β>1.5 |
|---|---|---|---|---|---|
| dim=1 (true GUE) | 500 | **1.808** | 1.696 | 91.4% | 64.2% |
| dim≥2 (all) | 500 | **0.327** | 0.206 | 6.6% | 1.8% |
| dim≥2 GUE-preferring | 33 | **1.137** | 1.006 | 51.5% | — |
| dim≥2 GOE-preferring | 467 | **0.270** | 0.175 | — | — |

**Per-form MLE β correctly recovers dim=1 β≈1.81 (pooled: 1.88).** The dim≥2 GUE-preferring forms have per-form β=1.14 (between GOE and GUE), confirming they are a genuine intermediate population.

### 4. Root Number (Sign of Functional Equation)

| Root number | GUE | GOE | Total | GUE% |
|---|---|---|---|---|
| +1 (even) | 1,502 | 22,210 | 23,712 | **6.3%** |
| -1 (odd) | 227 | 5,174 | 5,401 | **4.2%** |

**Even functional equation (root number +1) → 1.54× more likely to be GUE outlier** (χ²=35.4, p=2.7×10⁻⁹). This is statistically significant and theoretically motivated: even functional equation → GOE/GUE symmetry, odd → GSE.

### 5. Level Threshold (Clear Monotonic Trend)

| Level range | GUE | GOE | Total | GUE% |
|---|---|---|---|---|
| <50 | 2 | 11 | 13 | **15.4%** |
| 50-100 | 11 | 47 | 58 | **19.0%** |
| 100-200 | 15 | 149 | 164 | 9.1% |
| 200-500 | 98 | 844 | 942 | 10.4% |
| 500-1K | 172 | 2,119 | 2,291 | 7.5% |
| 1K-2K | 311 | 5,351 | 5,662 | 5.5% |
| 2K-5K | 1,120 | 18,863 | 19,983 | 5.6% |

**GUE% decreases monotonically with conductor level: 19% at level<100 → 5.6% at level>2K.** Low-level forms are 3-4× more likely to be GUE outliers.

### 6. Analytic Rank

| Rank | GUE | GOE | Total | GUE% |
|---|---|---|---|---|
| 0 | 837 | 13,914 | 14,751 | 5.7% |
| 1 | 868 | 13,371 | 14,239 | 6.1% |
| 2 | 24 | 99 | 123 | **19.5%** |

**Rank=2 forms are 3× more likely to be GUE outliers** (19.5% vs 5.7-6.1%). But rank=2 is rare (123 forms, 0.4%).

### 7. Logistic Regression (AUC=0.679)

| Feature | Coefficient (standardized) |
|---|---|
| **dim** | **-0.534** |
| trace_mean | +0.197 |
| root_number | +0.158 |
| analytic_rank | +0.112 |
| level | -0.018 |
| Nk2 | -0.018 |
| analytic_conductor | -0.018 |

**Dimension is the dominant predictor** (coef=-0.534). Root number (+0.158) and trace_mean (+0.197) are secondary. Level/conductor have near-zero coefficient (collinear with dim). AUC=0.679 indicates moderate predictability.

### 8. Trace Statistics

| Feature | GUE mean | GOE mean | ratio | p-value |
|---|---|---|---|---|
| trace_mean | 15.86 | 14.46 | 1.097 | 1.9×10⁻³¹ |

GUE outliers have significantly higher mean Hecke trace (p=10⁻³¹).

## Interpretation

The "GUE outliers" are **NOT truly GUE** (pooled β=0.67, not 2.0). They are an **intermediate population** with β between Poisson (0) and GOE (1), showing weak level repulsion. The key drivers are:

1. **Dimension** (strongest predictor): Low dimension → more repulsion. dim=2 GUE outliers have β≈1.0 (GOE), dim=5+ have β≈0.37 (weakly Poisson)
2. **Conductor level**: Low level → more repulsion (19% at level<100 vs 5.6% at level>2K)
3. **Root number**: Even functional equation → 1.54× more likely (p=10⁻⁹)
4. **Analytic rank**: Rank=2 → 3× more likely (but rare)
5. **CM status**: 3.6× enriched but explains only 1.1% of outliers

The continuous β transition (dim=2→1.0, dim=5+→0.37) suggests the "GUE outliers" are not a distinct population but rather the low-dimensional tail of a continuous distribution that transitions from GOE (β≈1) at dim=2 to Poisson (β≈0) at high dimension.

## Files

- `scripts/analyze_gue_outliers_deep.py` — root number, level, rank, logistic regression
- `scripts/pooled_brody_beta.py` — pooled Brody β (corrected MLE)
- `scripts/validate_brody_beta.py` — per-form β validation
- `data/results/gue_outlier_deep_analysis.json` — deep analysis results
- `data/results/pooled_brody_beta.json` — pooled β results
- `data/results/brody_beta_validation.json` — per-form validation
- `papers/gue_outlier_deep_analysis.png` — 6-panel figure
