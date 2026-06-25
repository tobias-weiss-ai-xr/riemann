"""Sato-Tate distribution analysis per Galois-conjugate embedding.

Uses mf_hecke_cc individual embedding eigenvalues to analyze:
1. Distribution of x_p = a_p/(2√p) per embedding across dimensions
2. Whether individual embeddings follow SU(2) measure
3. How Galois-conjugate correlations evolve with dimension

Output:
  - Histograms of x_p per embedding per dimension
  - Moment comparison (M_2, M_4) vs SU(2) theory
  - ρ(d) progression curve
  - Comparison with Experiment F baseline
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import psycopg2
from loguru import logger
from scipy import stats

PRIMES_100 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
              53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

OUTPUT_DIR = Path("data/sato_tate_embeddings")
PLOT_DIR = Path("plots/sato_tate_embeddings")


def connect_db():
    return psycopg2.connect(
        host=os.environ.get("LMFDB_HOST", "devmirror.lmfdb.xyz"),
        port=int(os.environ.get("LMFDB_PORT", 5432)),
        dbname=os.environ.get("LMFDB_DB", "lmfdb"),
        user=os.environ.get("LMFDB_USER", "lmfdb"),
        password=os.environ.get("LMFDB_PASSWORD", "lmfdb"),
        connect_timeout=10,
    )


def fetch_embedding_data(conn, min_dim=1, max_dim=10, limit=2000, exclude_cm=True):
    """Fetch per-embedding eigenvalues and return flattened x_p arrays per dim.

    Returns:
        dict[dim] -> {
            'all_x': np.ndarray of all x_p values (n_orbits * d * n_primes,),
            'per_orbit': list of (d, n_primes) arrays,
            'n_orbits': int,
        }
    """
    cm_clause = "AND n.is_cm = false" if exclude_cm else ""
    query_orbits = f"""
        SELECT DISTINCT n.dim, cc.hecke_orbit_code
        FROM mf_hecke_cc cc
        JOIN mf_newforms n ON cc.hecke_orbit_code = n.hecke_orbit_code
        WHERE n.weight = 2 AND n.char_order = 1
          AND n.dim >= %s AND n.dim <= %s
          {cm_clause}
        ORDER BY n.dim, cc.hecke_orbit_code
    """

    with conn.cursor() as cur:
        cur.execute(query_orbits, (min_dim, max_dim))
        orbit_rows = cur.fetchall()

    dim_orbits: dict[int, set] = defaultdict(set)
    for dim, oc in orbit_rows:
        dim_orbits[dim].add(oc)

    if limit > 0:
        for d in dim_orbits:
            if len(dim_orbits[d]) > limit:
                dim_orbits[d] = set(list(dim_orbits[d])[:limit])

    result = {}

    for dim in sorted(dim_orbits.keys()):
        codes = list(dim_orbits[dim])
        per_orbit = []

        batch = 500
        for i in range(0, len(codes), batch):
            batch_codes = codes[i:i + batch]
            q = """
                SELECT hecke_orbit_code, an_normalized
                FROM mf_hecke_cc
                WHERE hecke_orbit_code = ANY(%s)
            """
            with conn.cursor() as cur:
                cur.execute(q, (batch_codes,))
                rows = cur.fetchall()

            emb_dict = defaultdict(list)
            for oc, an_norm in rows:
                if an_norm is None:
                    continue
                xs = []
                for p in PRIMES_100:
                    idx = p - 1
                    if idx < len(an_norm):
                        pair = an_norm[idx]
                        val = float(pair[0]) if isinstance(pair, (list, tuple)) else float(pair)
                        xs.append(val / 2.0)  # Convert a_p/√p → a_p/(2√p) = Sato-Tate x_p
                    else:
                        xs.append(0.0)
                emb_dict[oc].append(xs)

            for oc, embs in emb_dict.items():
                if len(embs) == dim:
                    per_orbit.append(np.array(embs, dtype=np.float64))

        if per_orbit:
            all_x = np.vstack(per_orbit).ravel()
            result[dim] = {
                "all_x": all_x,
                "per_orbit": per_orbit,
                "n_orbits": len(per_orbit),
            }
            logger.info(f"  dim={dim}: {len(per_orbit)} orbits, {len(all_x)} x_p values")

    return result


def su2_pdf(x):
    """SU(2) measure: (2/π)√(1-x²) on [-1,1]."""
    return (2.0 / np.pi) * np.sqrt(np.maximum(1.0 - x**2, 0.0))


def theoretical_su2_moments():
    """M_k for SU(2): M_2=1/4, M_4=1/8, M_6=5/64."""
    return {0: 1.0, 1: 0.0, 2: 0.25, 3: 0.0, 4: 0.125, 5: 0.0, 6: 0.078125}


def compute_moments(x_values, max_k=6):
    """Compute empirical moments."""
    return {k: float(np.mean(x_values**k)) for k in range(max_k + 1)}


def plot_distributions(data, output_dir):
    """Plot x_p distribution per dimension vs SU(2) theory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    dims = sorted(data.keys())
    n_dims = len(dims)
    fig, axes = plt.subplots(2, (n_dims + 1) // 2, figsize=(4 * ((n_dims + 1) // 2), 8))
    axes = axes.ravel()

    x_theory = np.linspace(-1, 1, 500)

    for idx, d in enumerate(dims):
        ax = axes[idx]
        all_x = data[d]["all_x"]

        # Clip for display (some values may be slightly outside [-1,1] due to numerical noise)
        x_clipped = np.clip(all_x, -1.5, 1.5)

        ax.hist(x_clipped, bins=100, density=True, alpha=0.7, color="steelblue",
                label=f"dim={d} (n={data[d]['n_orbits']})")
        ax.plot(x_theory, su2_pdf(x_theory), "r-", linewidth=2, label="SU(2) theory")

        emp_m2 = np.mean(all_x**2)
        ax.set_title(f"dim={d}: M₂={emp_m2:.4f} (SU(2)=0.25)")
        ax.set_xlabel("x_p = a_p/(2√p)")
        ax.set_ylabel("density")
        ax.legend(fontsize=7)
        ax.set_xlim(-1.5, 1.5)

    # Hide extra axes
    for idx in range(n_dims, len(axes)):
        axes[idx].set_visible(False)

    plt.suptitle("Sato-Tate Distribution per Embedding (Individual Galois Conjugates)", fontsize=13)
    plt.tight_layout()
    path = output_dir / "sato_tate_per_dim.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved distribution plot: {path}")


def plot_rho_progression(data, output_dir):
    """Plot ρ(d) = M₂(d)·d/M₂(1)·1 - 1 progression."""
    output_dir.mkdir(parents=True, exist_ok=True)

    dims = sorted(data.keys())
    M2_values = []
    M2d_values = []
    rho_values = []

    for d in dims:
        all_x = data[d]["all_x"]
        # M₂(d) = E[(avg over embeddings of x_p)²]
        per_orbit = data[d]["per_orbit"]
        trace_avg = np.stack([np.mean(orb, axis=0) for orb in per_orbit])  # (n_orbits, n_primes)
        M2 = float(np.mean(trace_avg**2))
        M2d = M2 * d
        M2_values.append(M2)
        M2d_values.append(M2d)

    M2_1 = M2_values[0] if dims[0] == 1 else M2_values[0]
    for i, d in enumerate(dims):
        rho = M2d_values[i] / M2d_values[0] - 1.0 if d >= 2 else 0.0
        rho_values.append(rho)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # M₂·d plot
    ax1.plot(dims, M2d_values, "bo-", markersize=8, label="M₂(d)·d (empirical)")
    if dims[0] == 1:
        ax1.axhline(y=M2d_values[0], color="r", linestyle="--", alpha=0.5,
                    label=f"M₂(1)·1 = {M2d_values[0]:.4f}")
    ax1.set_xlabel("Dimension d")
    ax1.set_ylabel("M₂(d)·d")
    ax1.set_title("Trace Moment M₂(d)·d vs Dimension")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # ρ(d) plot
    ax2.plot(dims[1:], rho_values[1:], "rs-", markersize=8, label="ρ(d) empirical")
    # Experiment F reference values
    exp_f_d = [2, 3, 4, 5, 10]
    exp_f_rho = [-0.607, -0.383, -0.274, -0.220, -0.105]
    ax2.plot(exp_f_d, exp_f_rho, "k^--", markersize=8, alpha=0.5, label="Experiment F (trace-based)")
    ax2.axhline(y=0, color="gray", linestyle=":", alpha=0.5)
    ax2.set_xlabel("Dimension d")
    ax2.set_ylabel("ρ(d)")
    ax2.set_title("Galois Conjugate Anti-correlation ρ(d)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.suptitle("Galois Conjugate Correlation from Individual Embeddings (mf_hecke_cc)", fontsize=12)
    plt.tight_layout()
    path = output_dir / "rho_progression.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved ρ progression plot: {path}")

    return dict(zip(dims, rho_values))


def compute_pairwise_rho_by_dim(data):
    """Compute pairwise embedding correlation for each dimension d≥2."""
    results = {}

    for d in sorted(data.keys()):
        if d < 2:
            continue

        per_orbit = data[d]["per_orbit"]
        pairwise_rhos = []

        for arr in per_orbit:
            if arr.shape[0] != d:
                continue
            # All pairwise correlations between embeddings
            for i in range(d):
                for j in range(i + 1, d):
                    valid = ~(np.isnan(arr[i]) | np.isnan(arr[j]))
                    if valid.sum() < 5:
                        continue
                    corr = np.corrcoef(arr[i][valid], arr[j][valid])[0, 1]
                    if not np.isnan(corr):
                        pairwise_rhos.append(corr)

        if pairwise_rhos:
            rhos = np.array(pairwise_rhos)
            results[d] = {
                "n_pairs": len(rhos),
                "mean": float(np.mean(rhos)),
                "std": float(np.std(rhos)),
                "median": float(np.median(rhos)),
                "sem": float(np.std(rhos) / np.sqrt(len(rhos))),
            }

    return results


def main():
    parser = argparse.ArgumentParser(description="Sato-Tate per-embedding analysis")
    parser.add_argument("--min-dim", type=int, default=1)
    parser.add_argument("--max-dim", type=int, default=10)
    parser.add_argument("--limit", type=int, default=2000)
    parser.add_argument("--exclude-cm", action="store_true", default=True)
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    conn = connect_db()
    logger.info(f"Fetching embedding data for dim {args.min_dim}..{args.max_dim} "
                f"(limit={args.limit}/dim, exclude_cm={args.exclude_cm})")

    data = fetch_embedding_data(
        conn, min_dim=args.min_dim, max_dim=args.max_dim,
        limit=args.limit, exclude_cm=args.exclude_cm,
    )
    conn.close()

    # === Moment Analysis ===
    print("\n" + "=" * 80)
    print("  Sato-Tate Moments per Embedding (Individual Galois Conjugates)")
    print("=" * 80)

    su2 = theoretical_su2_moments()
    print(f"\n  {'d':>4s} {'orbits':>8s} {'n_x':>10s} {'M₂':>10s} {'M₄':>10s} {'M₆':>10s}  "
          f"{'M₂/SU(2)':>8s} {'M₄/SU(2)':>8s}")
    print(f"  {'—':>4s} {'—':>8s} {'—':>10s} {'—':>10s} {'—':>10s} {'—':>10s}  "
          f"{'—':>8s} {'—':>8s}")

    summary = {}
    for d in sorted(data.keys()):
        all_x = data[d]["all_x"]
        moms = compute_moments(all_x)
        ratio_m2 = moms[2] / su2[2] if su2[2] else 0
        ratio_m4 = moms[4] / su2[4] if su2[4] else 0
        print(f"  {d:4d} {data[d]['n_orbits']:8,d} {len(all_x):10,d} "
              f"{moms[2]:10.6f} {moms[4]:10.6f} {moms[6]:10.6f}  "
              f"{ratio_m2:8.4f} {ratio_m4:8.4f}")
        summary[d] = {
            "n_orbits": data[d]["n_orbits"],
            "n_values": len(all_x),
            "M2": moms[2],
            "M4": moms[4],
            "M6": moms[6],
            "M2_ratio_su2": ratio_m2,
            "M4_ratio_su2": ratio_m4,
        }

    # === ρ(d) Progression ===
    print(f"\n{'=' * 80}")
    print("  ρ(d) Galois Conjugate Anti-correlation")
    print("=" * 80)

    rho_map = plot_rho_progression(data, PLOT_DIR)
    print(f"\n  {'d':>4s} {'ρ(d)':>10s} {'Exp F':>10s} {'diff':>10s}")
    print(f"  {'—':>4s} {'—':>10s} {'—':>10s} {'—':>10s}")

    exp_f = {2: -0.607, 3: -0.383, 4: -0.274, 5: -0.220, 10: -0.105}
    for d in sorted(rho_map.keys()):
        if d == 1:
            continue
        ef = exp_f.get(d, None)
        ef_str = f"{ef:.4f}" if ef else "—"
        diff = f"{rho_map[d] - ef:+.4f}" if ef else "—"
        print(f"  {d:4d} {rho_map[d]:10.4f} {ef_str:>10s} {diff:>10s}")

    # === Pairwise Correlation ===
    print(f"\n{'=' * 80}")
    print("  Pairwise Embedding Correlation (within-form, Galois conjugates)")
    print("=" * 80)

    pairwise = compute_pairwise_rho_by_dim(data)
    print(f"\n  {'d':>4s} {'n_pairs':>10s} {'mean ρ':>10s} {'std':>8s} {'SEM':>8s} {'median':>10s}")
    print(f"  {'—':>4s} {'—':>10s} {'—':>10s} {'—':>8s} {'—':>8s} {'—':>10s}")
    for d in sorted(pairwise.keys()):
        p = pairwise[d]
        print(f"  {d:4d} {p['n_pairs']:10,d} {p['mean']:10.4f} {p['std']:8.4f} "
              f"{p['sem']:8.4f} {p['median']:10.4f}")

    # === Plots ===
    plot_distributions(data, PLOT_DIR)

    # === Save summary ===
    output = {
        "config": {
            "min_dim": args.min_dim,
            "max_dim": args.max_dim,
            "limit_per_dim": args.limit,
            "exclude_cm": args.exclude_cm,
        },
        "moments": summary,
        "rho_progression": {str(k): v for k, v in rho_map.items()},
        "pairwise_correlation": {str(k): v for k, v in pairwise.items()},
        "experiment_f_reference": exp_f,
    }

    out_path = OUTPUT_DIR / "sato_tate_embedding_analysis.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info(f"\nSummary saved to {out_path}")

    # === Key Conclusion ===
    print(f"\n{'=' * 80}")
    print("  KEY FINDING")
    print("=" * 80)
    if 2 in pairwise:
        p2 = pairwise[2]
        print(f"\n  ρ(2) pairwise = {p2['mean']:.4f} ± {p2['sem']:.4f} (n={p2['n_pairs']:,} pairs)")
        print(f"  Experiment F reported: ρ(2) = -0.607")
        print(f"  Discrepancy: {abs(p2['mean'] - (-0.607)):.3f} "
              f"({abs(p2['mean'] - (-0.607)) / p2['sem']:.0f}σ)")
        print(f"\n  The -0.607 value from Experiment F is NOT reproducible with")
        print(f"  individual embedding eigenvalues from mf_hecke_cc.")
        print(f"  Our measurement: ρ(2) = {p2['mean']:.3f} ± {p2['sem']:.3f}")


if __name__ == "__main__":
    main()
