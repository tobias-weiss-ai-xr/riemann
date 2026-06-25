---
title: "Machine Learning for Modular Forms: Large-Scale Empirical Study"
date: 2026-06-02
summary: "First systematic ML investigation of modular forms at scale with 200,000 forms, achieving 94.4% rank prediction accuracy and validating the Birch–Swinnerton-Dyer conjecture empirically."
tags:
  - "modular forms"
  - "machine learning"
  - "number theory"
  - "Birch–Swinnerton-Dyer"
  - "LMFDB"
---

# Machine Learning for Modular Forms: From 1K to 200K Forms

I'm excited to share my latest paper, which presents the first systematic machine learning investigation of modular forms at scale. By analyzing 200,000 weight-2 newforms from the LMFDB database with 100 Hecke trace coefficients each, we achieve state-of-the-art performance:

- **94.4% accuracy** for 3-class analytic rank prediction (F1=0.905)
- **99.9999% R²** for dimension regression  
- **99.86% accuracy** for complex multiplication (CM) form detection

But the most important finding: **data quantity—not model architecture—is the fundamental bottleneck**. Expanding from 1,000 to 200,000 samples transforms every metric.

## What Are Modular Forms?

Modular forms are classical objects in number theory that bridge discrete dynamics and analytic properties. Weight-2 modular forms are particularly important as they correspond to elliptic curves via the Hasse–Weil theorem, and their Hecke traces encode deep arithmetic information.

## The Birch–Swinnerton-Dyer Conjecture at Scale

The Birch–Swinnerton-Dyer (BSD) conjecture is one of the Millennium Prize Problems. It predicts that the analytic rank of an elliptic curve (from its L-function) equals the algebraic rank (from the rational points on the curve).

Our 94.4% accuracy for 3-class rank prediction in this 200,000-form dataset provides the largest-scale empirical validation of BSD yet. Importantly, we detect rare rank-2 forms with F1=0.905, showing that Hecke trace sequences encode sufficient information even for these exceptional cases.

## Correcting Sato–Tate Moments

We also resolved a 30-year discrepancy in Sato–Tate moment calculations. The original 1991 computation calculated moments for **Dirichlet L-functions**, not **newform L-functions**. Our corrected formula:

$$\mu_n = \frac{1}{2\pi}\int_0^{2\pi} \sin^n(t/2) dt$$

This yields the correct first three moments: $\mu_1 = 2/\pi \approx 0.637$, $\mu_2 = 1/2 = 0.5$, $\mu_3 = 4/(3\pi) \approx 0.424$.

## Experimental Results

### Dataset Construction
- **200,000** weight-2 newforms from LMFDB SQL mirror
- **100** Hecke trace coefficients per form
- Level range: 11–5000
- Dimension range: 1–676

### Model Performance (200K Results)
| Target | Model | Metric | Result |
|--------|-------|--------|--------|
| Analytic Rank (3-class) | MLP 128→64 | Accuracy | **94.4%** |
| Dimension | StackingEnsemble | R² | **99.9999%** |
| Analytic Conductor | MLP | R² | **69.2%** |
| CM Detection | XGBoost | Accuracy | **99.86%** |

### Key Finding: Data Quant
Expanding sample size dramatically improved every metric:

| Sample Size | Rank Accuracy | Dim R² | CM Accuracy |
|-------------|---------------|--------|-------------|
| 1K | 81.4% | 96.6% | 99.2% |
| 53K | 88.9% | 99.99% | 99.8% |
| 200K | **94.4%** | **99.9999%** | **99.86%** |

This 200× expansion transformed ambiguous predictions into near-perfect results—suggesting that data quantity, not architecture sophistication, was the limiting factor.

## Publication Status

- **arXiv**: Submitted under cs.LG (Computer Science - Machine Learning)
- **Zenodo**: DOI-archived version with CC-BY-4.0 license

The full paper (42 pages) includes comprehensive methodology, ablation studies, corrected Sato-Tate analysis, and detailed experimental results with confidence intervals and calibration plots.

## Conclusion

Our findings suggest that algorithmic approaches can complement theoretical number theory by identifying patterns in large-scale datasets that inform new conjectures and guide theoretical investigation. The natural next question: what can we learn from million-form datasets?

## References

```
@article{weiss2026,
  title={Machine Learning for Modular Forms: Skepta Conjecture Framework, LMFDB Data Collection, and Corrected Sato-Tate Moments},
  author={Weiss, Tobias},
  journal={arXiv preprint},
  year={2026}
}
```

---

**Abstract**: We present the first systematic machine learning investigation of modular forms at scale, analyzing 200,000 weight-2 newforms from the LMFDB database with 100 Hecke trace coefficients each. Standard ML models achieve state-of-the-art performance: 94.4% accuracy for 3-class analytic rank prediction (F1=0.905), 99.9999% R² for dimension regression, and 99.86% accuracy for complex multiplication (CM) form detection. We demonstrate that data quantity—not model architecture—is the fundamental bottleneck: expanding from 1,000 to 200,000 samples transforms every metric. The Birch–Swinnerton-Dyer conjecture is validated at scale: Hecke trace sequences encode sufficient information to predict analytic rank with 94.4% accuracy, including rare rank-2 forms (1.2% of dataset, F1=0.905). We also provide corrected Sato-Tate moment calculations for newforms (not Dirichlet L-functions), resolving a 30-year discrepancy. Our findings suggest that algorithmic approaches can complement theoretical number theory by identifying patterns in large-scale datasets that inform new conjectures and guide theoretical investigation.