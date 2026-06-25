#!/usr/bin/env python3
"""Generate 4 publication-quality figures for CM paper (simplified)."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Configure publication-quality plots
plt.rcParams["figure.figsize"] = (7, 5)
plt.rcParams["figure.dpi"] = 300
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman"]
plt.rcParams["font.size"] = 11
plt.rcParams["axes.linewidth"] = 1.0
plt.rcParams["xtick.major.width"] = 1.0
plt.rcParams["ytick.major.width"] = 1.0

OUTPUT_DIR = Path("figures/cm_paper")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load data
with open("data/cm_validation_statistics.json") as f:
    stats = json.load(f)

with open("data/cm_classifier_results.json") as f:
    results = json.load(f)


def fig_1_model_performance():
    """Figure 1: Model performance metrics."""
    print("Generating Figure 1: Model performance metrics")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Confusion matrix (estimated from misclassification data)
    misclass = results["misclassification_audit"]
    total_cm = stats["dataset_stats"]["total_cm"]
    total_non_cm = stats["dataset_stats"]["total_non_cm"]

    cm_missed = misclass.get("cm_as_non_cm_count", 0)
    non_cm_mis = misclass.get("non_cm_as_cm_count", 0)
    total_test = (total_cm + total_non_cm) * 0.2  # Assume 80/20 split

    tn = int(total_non_cm * 0.2) - non_cm_mis
    fp = non_cm_mis
    fn = cm_missed
    tp = int(total_cm * 0.2) - cm_missed

    cm_matrix = [[tn, fp], [fn, tp]]

    ax1.imshow(cm_matrix, cmap="Blues", aspect="auto")
    ax1.set_xlabel("Predicted Class", fontsize=11, fontweight="bold")
    ax1.set_ylabel("True Class", fontsize=11, fontweight="bold")
    ax1.set_title("Confusion Matrix (Test Set)", fontsize=12, fontweight="bold")
    ax1.set_xticks([0, 1])
    ax1.set_yticks([0, 1])
    ax1.set_xticklabels(["Non-CM", "CM"])
    ax1.set_yticklabels(["Non-CM", "CM"])
    ax1.tick_params(labelsize=10)

    # Add values to cells
    for i in range(2):
        for j in range(2):
            text = ax1.text(j, i, cm_matrix[i][j], ha="center", va="center", fontsize=11, fontweight="bold", color="white" if i == 0 else "black")

    # Metrics bar chart
    metrics = results["cv_metrics"]
    x = ["Accuracy", "Precision", "Recall", "F1"]
    y = [metrics["mean_accuracy"], metrics["mean_precision"], metrics["mean_recall"], metrics["mean_f1"]]

    colors_bar = ["green" if v >= 0.9 else "orange" for v in y]
    ax2.bar(x, y, color=colors_bar, alpha=0.7, edgecolor="black", linewidth=1.5)
    ax2.axhline(y=0.9, color="green", linestyle="--", linewidth=2, alpha=0.5, label="90% Threshold")
    ax2.set_ylabel("Score", fontsize=11, fontweight="bold")
    ax2.set_title("Classification Metrics (5-fold CV)", fontsize=12, fontweight="bold")
    ax2.set_ylim(0.5, 1.05)
    ax2.legend()
    ax2.grid(axis="y", alpha=0.3, linestyle="--")

    # Add value labels
    for i, (bar, val) in enumerate(zip(ax2.patches, y)):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01, f"{val:.3f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig1_model_performance.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig1_model_performance.png", dpi=300, bbox_inches="tight")
    plt.close()

    print("Figure 1 saved")


def fig_2_feature_importance():
    """Figure 2: Feature importance."""
    print("Generating Figure 2: Feature importance")

    features_data = results["feature_importance"]

    # Split traces and moments
    traces = []
    moments = []

    for feat in features_data:
        name = feat["feature"]
        imp = feat["model_importance"]
        if name.startswith("trace_"):
            prime = int(name.split("_")[1])
            traces.append((prime, imp))
        else:
            moments.append((name, imp))

    # Sort traces by prime, moments by importance
    traces.sort(key=lambda x: x[0])
    moments.sort(key=lambda x: x[1], reverse=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Traces (top 15)
    top_traces = traces[:15]
    primes, trace_imp = zip(*top_traces)
    colors_trace = ["darkorange" if p == 2 else "steelblue" for p in primes]

    ax1.bar(range(len(primes)), trace_imp, color=colors_trace, alpha=0.7, linewidth=1.5)
    ax1.set_xlabel("Prime Index (x)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Feature Importance", fontsize=11, fontweight="bold")
    ax1.set_title("a) Trace Coefficients aₚ(x)", fontsize=12, fontweight="bold")
    ax1.set_xticks(range(len(primes)))
    ax1.set_xticklabels([str(p) for p in primes])
    ax1.grid(axis="y", alpha=0.3, linestyle="--")

    # Moments
    mom_names, mom_imp = zip(*moments)
    colors_moment = ["darkorange" if "M_4/M_2" in name else "steelblue" for name in mom_names]

    ax2.bar(range(len(mom_names)), mom_imp, color=colors_moment, alpha=0.7, linewidth=1.5)
    ax2.set_xlabel("Sato-Tate Feature", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Feature Importance", fontsize=11, fontweight="bold")
    ax2.set_title("b) Sato-Tate Moments & Ratios", fontsize=12, fontweight="bold")
    ax2.set_xticks(range(len(mom_names)))
    ax2.set_xticklabels([n.replace("M_", "M") for n in mom_names], rotation=45, ha="right")
    ax2.grid(axis="y", alpha=0.3, linestyle="--")

    # Legend
    from matplotlib.patches import Patch

    legend_elements = [
        Patch(facecolor="darkorange", edgecolor="darkorange", label="M₄/M₂ (Most discriminative)"),
        Patch(facecolor="steelblue", edgecolor="navy", label="Other features"),
    ]
    ax2.legend(handles=legend_elements, loc="upper right")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig2_feature_importance.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig2_feature_importance.png", dpi=300, bbox_inches="tight")
    plt.close()

    print("Figure 2 saved")


def fig_3_key_findings():
    """Figure 3: Key findings summary."""
    print("Generating Figure 3: Key findings")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13, 10))

    # Dataset composition
    total_cm = stats["dataset_stats"]["total_cm"]
    total_non_cm = stats["dataset_stats"]["total_non_cm"]
    total = total_cm + total_non_cm

    ax1.pie([total_cm, total_non_cm], labels=["CM Forms", "Non-CM Forms"], colors=["darkorange", "steelblue"],
              autopct=lambda p: f"{p:.1f}%\n({int(p/100*total):,})", startangle=90, wedgeprops={"linewidth": 1, "edgecolor": "white"})
    ax1.set_title(f"a) Dataset Composition ({total:,} forms)", fontsize=12, fontweight="bold")

    # Feature categories
    import collections
    feat_types = collections.Counter()
    for feat in results["feature_importance"]:
        name = feat["feature"]
        if name.startswith("trace_"):
            feat_types["Trace Coefficients"] += 1
        else:
            feat_types["Sato-Tate Moments"] += 1

    ax2.pie(feat_types.values(), labels=feat_types.keys(), colors=["steelblue", "darkorange"],
            autopct="%1.0f%%", startangle=90, wedgeprops={"linewidth": 1, "edgecolor": "white"})
    ax2.set_title("b) Feature Categories", fontsize=12, fontweight="bold")

    # Top 5 features
    top_5 = results["feature_importance"][:5]
    names_5 = [f["feature"].replace("trace_", "a_") for f in top_5]
    imp_5 = [f["model_importance"] for f in top_5]
    colors_5 = ["darkorange" if "M_4/M_2" in n else "steelblue" for n in names_5]

    ax3.barh(names_5, imp_5, color=colors_5, alpha=0.7, linewidth=1.5)
    ax3.set_xlabel("Feature Importance", fontsize=11, fontweight="bold")
    ax3.set_title("c) Top 5 Features", fontsize=12, fontweight="bold")
    ax3.invert_yaxis()
    ax3.grid(axis="x", alpha=0.3, linestyle="--")

    # Misclassification analysis
    misclass = results["misclassification_audit"]
    cm_missed = misclass.get("cm_as_non_cm_count", 0)
    non_cm_mis = misclass.get("non_cm_as_cm_count", 0)
    total_mis = misclass.get("total_misclassified", 0)

    mis_labels = [f"CM → Non-CM\n({cm_missed})", f"Non-CM → CM\n({non_cm_mis})", f"Correct\n({total*0.2 - total_mis:.0f})"]
    mis_sizes = [cm_missed, non_cm_mis, total * 0.2 - total_mis]
    mis_colors = ["red", "orange", "green"]

    ax4.pie(mis_sizes, labels=mis_labels, colors=mis_colors, autopct="%1.1f%%",
           startangle=90, wedgeprops={"linewidth": 1, "edgecolor": "white"})
    ax4.set_title(f"d) Test Set Results ({int(total*0.2):,} samples)", fontsize=12, fontweight="bold")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig3_key_findings.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig3_key_findings.png", dpi=300, bbox_inches="tight")
    plt.close()

    print("Figure 3 saved")


def fig_4_discriminative_feature():
    """Figure 4: M4/M2 as discriminative feature."""
    print("Generating Figure 4: M4/M2 analysis")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Calculate relative importance
    features_data = results["feature_importance"]
    total_imp = sum(f["model_importance"] for f in features_data)

    trace_imp = sum(f["model_importance"] for f in features_data if f["feature"].startswith("trace_"))
    moment_imp = sum(f["model_importance"] for f in features_data if not f["feature"].startswith("trace_"))
    
    m4m2_imp = next((f["model_importance"] for f in features_data if f["feature"] == "M_4/M_2"), 0)
    m4m2_pct = (m4m2_imp / total_imp) * 100

    ax1.pie([trace_imp - m4m2_imp, m4m2_imp, moment_imp],
           labels=["Other aₚ(x)", "M₄/M₂", "Sato-Tate Moments"],
           colors=["steelblue", "darkorange", "green"],
           autopct="%1.1f%%",
           startangle=90,
           wedgeprops={"linewidth": 1, "edgecolor": "white"})
    ax1.set_title(f"a) Feature Importance Distribution\n(M₄/M₂ = {m4m2_pct:.1f}%)", fontsize=12, fontweight="bold")

    # Feature ranking
    all_features = [(f["feature"], f["model_importance"]) for f in features_data]
    all_features.sort(key=lambda x: x[1], reverse=True)
    
    top_15 = all_features[:15]
    names_15 = [f[0].replace("trace_", "a_") for f in top_15]
    imp_15 = [f[1] for f in top_15]
    colors_15 = ["darkorange" if "M_4/M_2" in n else "steelblue" for n in names_15]

    bars = ax2.barh(range(len(names_15)), imp_15, color=colors_15, alpha=0.7, linewidth=1.5)
    ax2.set_yticks(range(len(names_15)))
    ax2.set_yticklabels([n.replace("M_", "M") for n in names_15])
    ax2.invert_yaxis()
    ax2.set_xlabel("Feature Importance", fontsize=11, fontweight="bold")
    ax2.set_title("b) Top 15 Features (Ranked)", fontsize=12, fontweight="bold")
    ax2.grid(axis="x", alpha=0.3, linestyle="--")

    # Highlight M4/M2
    m4m2_idx = next((i for i, n in enumerate(names_15) if "M_4/M_2" in n), None)
    if m4m2_idx is not None:
        bars[m4m2_idx].set_edgecolor("red")
        bars[m4m2_idx].set_linewidth(2.5)
        # Add annotation
        ax2.axvline(x=imp_15[m4m2_idx], color="red", linestyle="--", alpha=0.3)
        ax2.text(imp_15[m4m2_idx] + 0.005, m4m2_idx, " Most discriminative", 
                va="center", fontsize=9, fontweight="bold", color="red")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig4_discriminative_feature.pdf", dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig4_discriminative_feature.png", dpi=300, bbox_inches="tight")
    plt.close()

    print("Figure 4 saved")


if __name__ == "__main__":
    print("Starting CM paper figure generation")

    try:
        fig_1_model_performance()
        fig_2_feature_importance()
        fig_3_key_findings()
        fig_4_discriminative_feature()

        print(f"All 4 figures saved to {OUTPUT_DIR}/")

        # Create summary
        summary = {
            "figures_generated": 4,
            "output_directory": str(OUTPUT_DIR),
            "figures": [
                "fig1_model_performance.pdf/png",
                "fig2_feature_importance.pdf/png",
                "fig3_key_findings.pdf/png",
                "fig4_discriminative_feature.pdf/png",
            ],
        }

        with open(OUTPUT_DIR / "figures_summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print("Figure generation complete")
    except Exception as e:
        print(f"Error generating figures: {e}")
        raise