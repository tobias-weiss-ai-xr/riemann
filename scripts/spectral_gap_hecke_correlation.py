#!/usr/bin/env python3
"""
Experiment 16: Spectral Gap ↔ Hecke Trace Correlation (Direction B).

Tests Pizer's theorem empirically: the Brandt matrix eigenvalues (= Cayley graph
spectra of SL(2,F_p)) should correlate with Hecke eigenvalues on S₂(Γ₀(p)).

If this holds, it bridges Cayley graph spectral properties (Friedli constant,
spectral gap) to L-function zeros via the Hecke → L(f,s) → explicit formula chain,
connecting our spectral work directly to Goldbach representations.

Data sources:
  - Spectral gaps: hardcoded from experiment log (Exp 1-4, p=2..79)
  - Friedli slopes: from Exp 15b (p=2,3,5,7,11,13)
  - Hecke traces: data/lmfdb/lmfdb_sql_weight2_ml.csv (53k newforms, p=11..5000)

Usage:
    python scripts/spectral_gap_hecke_correlation.py

Outputs:
    data/experiment16/ — correlation tables, plots, summary JSON
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Spectral data from experiment log (Exp 1-4, statistical summary table)
# Each entry: (prime, nodes, edges, spectral_gap, ramanujan_ratio, is_ramanujan)
# ---------------------------------------------------------------------------

SPECTRAL_DATA: list[tuple[int, int, int, float, float, bool]] = [
    (2, 6, 12, 2.000000, 1.155, False),
    (3, 24, 48, 1.267949, 0.789, True),
    (5, 120, 240, 0.763932, 0.934, True),
    (7, 336, 672, 0.585786, 1.028, False),
    (11, 1320, 2640, 0.381966, 1.077, False),
    (13, 2184, 4368, 0.324869, 1.104, False),
    (17, 4896, 9792, 0.290725, 1.081, False),
    (19, 6840, 13680, 0.245395, 1.099, False),
    (23, 12096, 24192, 0.206681, 1.103, False),
    (29, 24360, 48720, 0.182153, 1.111, False),
    (31, 29760, 59520, 0.227251, 1.103, False),
    (37, 50652, 101304, 0.170768, 1.116, False),
    (41, 68920, 137840, 0.180865, 1.102, False),
    (43, 79452, 158904, 0.166165, 1.107, False),
    (47, 103776, 207552, 0.180653, 1.106, False),
    (53, 148824, 297648, 0.174447, 1.107, False),
    (59, 205320, 410640, 0.158304, 1.109, False),
    (61, 226980, 453960, 0.185452, 1.106, False),
    (67, 297672, 595344, 0.163890, 1.107, False),
    (71, 357840, 715680, 0.160206, 1.108, False),
    (73, 387072, 774144, 0.131854, 1.117, False),
    (79, 490560, 981120, 0.177011, 1.105, False),
]

# ---------------------------------------------------------------------------
# Friedli slopes from Experiment 15b (full spectra, p ≤ 13)
# ---------------------------------------------------------------------------

FRIEDLI_DATA: list[tuple[int, int, float]] = [
    (2, 6, 1.3208),
    (3, 24, 1.2084),
    (5, 120, 1.1574),
    (7, 336, 1.1422),
    (11, 1320, 1.1369),
    (13, 2184, 1.1367),
]

# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path("data/experiment16")


def _build_spectral_df() -> pd.DataFrame:
    """Build DataFrame from hardcoded spectral data."""
    cols = ["prime", "nodes", "edges", "spectral_gap", "ramanujan_ratio", "is_ramanujan"]
    rows = [(p, n, e, gap, ratio, ram) for p, n, e, gap, ratio, ram in SPECTRAL_DATA]
    df = pd.DataFrame(rows, columns=cols)
    df["log_nodes"] = np.log(df["nodes"].astype(float))
    return df


def _load_lmfdb_csv() -> pd.DataFrame | None:
    """Load LMFDB CSV if available, returning DataFrame indexed by level (prime)."""
    path = Path("data/lmfdb/lmfdb_sql_weight2_ml.csv")
    if not path.exists():
        print(f"[WARN] LMFDB CSV not found: {path}")
        print("  Run `docker compose exec research python scripts/collect_lmfdb_sql.py` first")
        return None
    print(f"[INFO] Loading LMFDB CSV: {path}")
    df = pd.read_csv(path)
    print(f"  Records: {len(df):,}")
    print(f"  Columns: {list(df.columns)}")
    return df


def _compute_level_aggregates(lmfdb_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate Hecke traces by level (= prime)."""
    trace_cols = [f"trace_{i}" for i in range(1, 101)]
    available_traces = [c for c in trace_cols if c in lmfdb_df.columns]

    agg = lmfdb_df.groupby("level").agg(
        num_forms=("level", "count"),
        mean_a2=("trace_1", "mean"),
        std_a2=("trace_1", "std"),
        mean_trace=("trace_mean", "mean"),
        mean_rank=("analytic_rank", "mean"),
        frac_rank0=("analytic_rank", lambda x: (x == 0).mean()),
        frac_rank1=("analytic_rank", lambda x: (x == 1).mean()),
        frac_rank2=("analytic_rank", lambda x: (x == 2).mean()),
        frac_cm=("is_cm", "mean"),
        mean_cond=("analytic_conductor", "mean"),
    )

    # Also compute the first K trace means as separate features
    for tc in available_traces:
        agg[f"mean_{tc}"] = lmfdb_df.groupby("level")[tc].mean()

    agg = agg.reset_index()
    agg = agg.rename(columns={"level": "prime"})
    return agg


def _compute_correlations(
    spectral_df: pd.DataFrame, hecke_agg: pd.DataFrame
) -> dict:
    """Compute Pearson correlations between spectral and Hecke features."""
    merged = pd.merge(spectral_df, hecke_agg, on="prime", how="inner")
    print(f"\n[INFO] Merged dataset: {len(merged)} primes")

    corr_features = [
        ("spectral_gap", "mean_a2"),
        ("spectral_gap", "mean_trace"),
        ("spectral_gap", "mean_rank"),
        ("spectral_gap", "frac_rank0"),
        ("spectral_gap", "frac_rank1"),
        ("spectral_gap", "frac_cm"),
        ("ramanujan_ratio", "mean_a2"),
        ("ramanujan_ratio", "mean_trace"),
        ("ramanujan_ratio", "mean_rank"),
        ("log_nodes", "mean_a2"),
        ("log_nodes", "mean_trace"),
    ]

    results = {}
    for feat_x, feat_y in corr_features:
        if feat_x not in merged or feat_y not in merged:
            continue
        x = merged[feat_x].values.astype(float)
        y = merged[feat_y].values.astype(float)
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 3:
            continue
        x, y = x[mask], y[mask]
        corr = np.corrcoef(x, y)[0, 1]
        results[f"{feat_x} × {feat_y}"] = {
            "pearson_r": float(corr),
            "n": int(mask.sum()),
            "x_feature": feat_x,
            "y_feature": feat_y,
        }
        print(f"  r({feat_x}, {feat_y}) = {corr:+.4f}  (n={int(mask.sum())})")

    # Multi-trace correlation: spectral_gap vs mean_trace_k for k=1..20
    trace_r = []
    trace_cols_agg = [c for c in merged.columns if c.startswith("mean_trace_")][:20]
    for tc in trace_cols_agg:
        x = merged["spectral_gap"].values.astype(float)
        y = merged[tc].values.astype(float)
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < 3:
            continue
        r = float(np.corrcoef(x[mask], y[mask])[0, 1])
        trace_idx = tc.replace("mean_trace_", "")
        trace_r.append((int(trace_idx) if trace_idx.isdigit() else 0, r))

    results["trace_correlation_series"] = [{"trace_k": k, "pearson_r": r} for k, r in trace_r]

    return results


def _plot_spectral_gap_vs_mean_a2(
    spectral_df: pd.DataFrame, hecke_agg: pd.DataFrame, output_dir: Path
) -> None:
    """Scatter: spectral gap vs mean Hecke trace a_2, colored by is_ramanujan."""
    merged = pd.merge(spectral_df, hecke_agg, on="prime", how="inner")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: spectral_gap vs mean_a2
    ax = axes[0]
    for is_ram, group in merged.groupby("is_ramanujan"):
        label = "Ramanujan" if is_ram else "Non-Ramanujan"
        color = "green" if is_ram else "blue"
        ax.scatter(
            group["mean_a2"],
            group["spectral_gap"],
            c=color,
            label=label,
            s=40,
            alpha=0.7,
        )
        for _, row in group.iterrows():
            ax.annotate(
                str(int(row["prime"])),
                (row["mean_a2"], row["spectral_gap"]),
                fontsize=7,
                alpha=0.6,
            )
    ax.set_xlabel("Mean Hecke trace a_2 (trace_1)")
    ax.set_ylabel("Spectral gap")
    ax.set_title("Spectral Gap vs. Mean a_2 Trace")
    ax.legend()
    ax.grid(alpha=0.3)

    # Panel 2: spectral_gap vs mean_rank
    ax = axes[1]
    for is_ram, group in merged.groupby("is_ramanujan"):
        label = "Ramanujan" if is_ram else "Non-Ramanujan"
        color = "green" if is_ram else "blue"
        ax.scatter(
            group["mean_rank"],
            group["spectral_gap"],
            c=color,
            label=label,
            s=40,
            alpha=0.7,
        )
        for _, row in group.iterrows():
            ax.annotate(
                str(int(row["prime"])),
                (row["mean_rank"], row["spectral_gap"]),
                fontsize=7,
                alpha=0.6,
            )
    ax.set_xlabel("Mean analytic rank")
    ax.set_ylabel("Spectral gap")
    ax.set_title("Spectral Gap vs. Mean Analytic Rank")
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = output_dir / "spectral_gap_vs_hecke.png"
    fig.savefig(path, dpi=150)
    print(f"\n[INFO] Saved: {path}")
    plt.close(fig)


def _plot_friedli_vs_hecke(
    hecke_agg: pd.DataFrame, output_dir: Path
) -> None:
    """Friedli slope vs Hecke trace aggregates for the 6 primes with full spectra."""
    friedli_df = pd.DataFrame(FRIEDLI_DATA, columns=["prime", "nodes", "friedli_slope"])

    merged = pd.merge(friedli_df, hecke_agg, on="prime", how="inner")
    if len(merged) < 3:
        print("[WARN] Too few Friedli primes with Hecke data for plotting")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: Friedli slope vs mean_a2
    ax = axes[0]
    ax.scatter(merged["mean_a2"], merged["friedli_slope"], c="darkred", s=60, alpha=0.8)
    for _, row in merged.iterrows():
        ax.annotate(
            f"p={int(row['prime'])}",
            (row["mean_a2"], row["friedli_slope"]),
            fontsize=9,
            alpha=0.8,
        )
    ax.set_xlabel("Mean Hecke trace a_2")
    ax.set_ylabel("Friedli slope d(log R)/dσ at σ=1/2")
    ax.set_title("Friedli Slope vs. Mean a_2 (p ≤ 13)")
    ax.grid(alpha=0.3)

    # Panel 2: Friedli slope vs nodes
    ax = axes[1]
    ax.scatter(merged["nodes"], merged["friedli_slope"], c="darkred", s=60, alpha=0.8)
    for _, row in merged.iterrows():
        ax.annotate(
            f"p={int(row['prime'])}",
            (row["nodes"], row["friedli_slope"]),
            fontsize=9,
            alpha=0.8,
        )
    ax.set_xlabel("Graph size |SL(2,F_p)|")
    ax.set_ylabel("Friedli slope")
    ax.set_title("Friedli Slope Convergence (p → ∞)")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = output_dir / "friedli_vs_hecke.png"
    fig.savefig(path, dpi=150)
    print(f"[INFO] Saved: {path}")
    plt.close(fig)


def _plot_trace_correlation_series(
    results: dict, output_dir: Path
) -> None:
    """Plot spectral_gap vs mean_trace_k correlation for k=1..K."""
    series = results.get("trace_correlation_series", [])
    if not series:
        return

    ks = [s["trace_k"] for s in series]
    rs = [s["pearson_r"] for s in series]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(ks, rs, "o-", color="purple", alpha=0.7, markersize=4)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
    ax.set_xlabel("Trace index k")
    ax.set_ylabel("Pearson r (spectral_gap vs mean_trace_k)")
    ax.set_title("Spectral Gap Correlation with Trace Index")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = output_dir / "trace_correlation_series.png"
    fig.savefig(path, dpi=150)
    print(f"[INFO] Saved: {path}")
    plt.close(fig)


def _save_results(results: dict, output_dir: Path) -> None:
    """Save correlation results as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "correlation_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[INFO] Results saved: {path}")


def main() -> None:
    """Run the correlation analysis."""
    print("=" * 60)
    print("Experiment 16: Spectral Gap ↔ Hecke Trace Correlation")
    print("=" * 60)

    spectral_df = _build_spectral_df()
    print(f"\nSpectral data: {len(spectral_df)} primes")
    print(list(spectral_df.columns))

    lmfdb_df = _load_lmfdb_csv()
    if lmfdb_df is None:
        print("\n[INFO] No LMFDB data available. Run with Docker:")
        print("  docker compose exec research python scripts/collect_lmfdb_sql.py")
        print("\nSaving spectral-only data for inspection...")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        spectral_df.to_csv(OUTPUT_DIR / "spectral_data.csv", index=False)
        return

    hecke_agg = _compute_level_aggregates(lmfdb_df)
    print(f"\nHecke aggregates: {len(hecke_agg)} levels (primes)")
    print(hecke_agg.head(10).to_string())

    # Merge and correlate
    results = _compute_correlations(spectral_df, hecke_agg)

    # Plot
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _plot_spectral_gap_vs_mean_a2(spectral_df, hecke_agg, OUTPUT_DIR)
    _plot_friedli_vs_hecke(hecke_agg, OUTPUT_DIR)
    _plot_trace_correlation_series(results, OUTPUT_DIR)
    _save_results(results, OUTPUT_DIR)

    print("\n[DONE] Experiment 16 complete.")


if __name__ == "__main__":
    main()
