"""Experiment Z: Sato-Tate convergence to SU(2) for high dimensions (d=50-200).

Tests hypothesis: M_2/SU(2) ≈ 1 - c/d for some constant c.

Uses mf_hecke_cc table for per-embedding eigenvalues.
an_normalized stores a_n/sqrt(n), so x_p = a_p/(2*sqrt(p)) = an_norm[p-1]/2.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import psycopg2

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


def fetch_embedding_data(min_dim: int, max_dim: int, limit_per_dim: int) -> dict[int, np.ndarray]:
    """Fetch per-embedding Sato-Tate-normalized x_p values.

    Returns dict[dim] -> ndarray of shape (total_embeddings, n_primes)
    where each row is one embedding's x_p values for the 25 primes.
    """
    conn = psycopg2.connect(
        host="devmirror.lmfdb.xyz", port=5432, dbname="lmfdb", user="lmfdb", password="lmfdb"
    )
    cur = conn.cursor()

    # Get orbit codes per dimension with cap
    cur.execute(
        """
        SELECT dim, hecke_orbit_code
        FROM mf_newforms
        WHERE weight = 2 AND char_order = 1 AND dim BETWEEN %s AND %s
        ORDER BY dim, hecke_orbit_code
        """,
        (min_dim, max_dim),
    )
    rows = cur.fetchall()

    # Group by dim, cap per dim
    dim_orbits: dict[int, list[int]] = defaultdict(list)
    for dim, hoc in rows:
        if len(dim_orbits[dim]) < limit_per_dim:
            dim_orbits[dim].append(hoc)

    print(f"Found {len(dim_orbits)} dimensions, total orbits: {sum(len(v) for v in dim_orbits.values())}")

    # Fetch embeddings per orbit in batches
    result: dict[int, list[np.ndarray]] = defaultdict(list)
    all_orbits_with_dim = [(d, hoc) for d, hocs in dim_orbits.items() for hoc in hocs]
    batch_size = 200

    for batch_start in range(0, len(all_orbits_with_dim), batch_size):
        batch = all_orbits_with_dim[batch_start : batch_start + batch_size]
        hoc_list = [hoc for _, hoc in batch]
        placeholders = ",".join(["%s"] * len(hoc_list))

        cur.execute(
            f"""
            SELECT hecke_orbit_code, an_normalized
            FROM mf_hecke_cc
            WHERE hecke_orbit_code IN ({placeholders})
            """
            if False
            else f"SELECT hecke_orbit_code, an_normalized FROM mf_hecke_cc WHERE hecke_orbit_code IN ({placeholders})",
            hoc_list,
        )
        cc_rows = cur.fetchall()

        # Map orbit -> list of embeddings
        orbit_embs: dict[int, list[list]] = defaultdict(list)
        for hoc, an_norm in cc_rows:
            orbit_embs[hoc].append(an_norm)

        for dim, hoc in batch:
            if hoc not in orbit_embs:
                continue
            embs = orbit_embs[hoc]
            if len(embs) != dim:
                continue  # skip orbits without full embedding data
            for emb in embs:
                # x_p = an_norm[p-1] / 2 (since an_norm = a_n/sqrt(n), and x_p = a_p/(2*sqrt(p)))
                try:
                    xp = np.array([float(emb[p - 1][0]) / 2.0 for p in PRIMES])
                except (IndexError, TypeError):
                    continue
                if not np.any(np.isnan(xp)):
                    result[dim].append(xp)

        if (batch_start // batch_size) % 5 == 0:
            print(f"  Processed {batch_start + len(batch)}/{len(all_orbits_with_dim)} orbits")

    cur.close()
    conn.close()

    # Convert to ndarrays
    return {d: np.vstack(embs) for d, embs in result.items() if embs}


def compute_moments(x: np.ndarray) -> dict:
    """Compute Sato-Tate moments from x values (shape: (n_samples, n_primes))."""
    flat = x.flatten()
    m2 = float(np.mean(flat**2))
    m4 = float(np.mean(flat**4))
    m6 = float(np.mean(flat**6))
    return {
        "M2": m2,
        "M4": m4,
        "M6": m6,
        "M2_over_SU2": m2 / 0.25,
        "M4_over_SU2": m4 / 0.09375,  # SU(2): <x^4> = 3/32 = 0.09375
        "M6_over_SU2": m6 / 0.043945,  # SU(2): <x^6> = 5/128 ≈ 0.0390625? check
    }


def fit_convergence_law(dims: list[int], ratios: list[float]) -> dict:
    """Fit M2/SU(2) = 1 - c/d via linear regression on (1/d, ratio)."""
    x = np.array([1.0 / d for d in dims])
    y = np.array(ratios)
    # y = 1 - c*x => (1 - y) = c*x
    z = 1.0 - y
    # Fit through origin: z = c*x
    c = float(np.sum(z * x) / np.sum(x * x))
    residuals = z - c * x
    rss = float(np.sum(residuals**2))
    return {"c": c, "residual_sum_squares": rss, "fit_quality": "1 - c/d"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-dim", type=int, default=50)
    parser.add_argument("--max-dim", type=int, default=200)
    parser.add_argument("--limit", type=int, default=100, help="orbits per dimension")
    parser.add_argument("--output", type=str, default="data/sato_tate_highdim")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Experiment Z: Sato-Tate convergence d={args.min_dim}-{args.max_dim}")
    data = fetch_embedding_data(args.min_dim, args.max_dim, args.limit)

    results = {}
    for dim in sorted(data.keys()):
        x = data[dim]
        moments = compute_moments(x)
        moments["n_embeddings"] = int(x.shape[0])
        moments["n_primes"] = int(x.shape[1])
        results[dim] = moments
        print(f"  d={dim}: n={x.shape[0]:5d}  M2={moments['M2']:.4f}  M2/SU2={moments['M2_over_SU2']:.4f}  M4/SU2={moments['M4_over_SU2']:.4f}")

    # Fit convergence law
    dims_sorted = sorted(results.keys())
    ratios = [results[d]["M2_over_SU2"] for d in dims_sorted]
    fit = fit_convergence_law(dims_sorted, ratios)
    print(f"\nFit: M2/SU(2) = 1 - {fit['c']:.4f}/d  (RSS={fit['residual_sum_squares']:.6f})")

    output = {
        "experiment": "Z",
        "description": "Sato-Tate convergence to SU(2) for high dimensions",
        "primes": PRIMES,
        "results_by_dim": {str(d): r for d, r in results.items()},
        "convergence_fit": fit,
        "n_primes": len(PRIMES),
    }

    out_file = out_dir / "sato_tate_highdim.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
