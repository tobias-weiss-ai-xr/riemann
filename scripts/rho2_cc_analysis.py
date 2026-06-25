"""Correct ρ₂ Galois Correlation Analysis using mf_hecke_cc (true embedding eigenvalues).

The mf_hecke_cc table stores per-embedding complex eigenvalues:
  an_normalized[n] = [real, imag] pairs for each coefficient a_n
  VERIFIED normalization: an_norm[0] = a_1/√1, an_norm[1] = a_2/√2, ...
  (i.e., an_norm[p-1] = a_p/√p for prime p)
  Note: values are a_n/√n, NOT a_n/(2√n). Factor 2 cancels in ρ ratio.
  
So x_p = an_norm[p-1].real gives the normalized eigenvalue a_p/√p.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
import psycopg2
from loguru import logger

PRIMES_100 = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
              53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


def connect_db(test: bool = False):
    """Connect to LMFDB SQL mirror."""
    return psycopg2.connect(
        host=os.environ.get("LMFDB_HOST", "devmirror.lmfdb.xyz"),
        port=int(os.environ.get("LMFDB_PORT", 5432)),
        dbname=os.environ.get("LMFDB_DB", "lmfdb"),
        user=os.environ.get("LMFDB_USER", "lmfdb"),
        password=os.environ.get("LMFDB_PASSWORD", "lmfdb"),
        connect_timeout=10,
    )


def fetch_per_embedding_eigenvalues(
    conn,
    min_dim: int = 1,
    max_dim: int = 20,
    limit: int = 0,
    exclude_cm: bool = False,
) -> dict[int, dict[int, np.ndarray]]:
    """Fetch per-embedding Sato-Tate normalized eigenvalues from mf_hecke_cc.
    
    Returns:
        dict mapping dim -> {orbit_code: np.ndarray of shape (d, n_primes)}
        where array[i, k] = x_{p_k} for embedding i (real part of an_normalized).
    """
    dim_data: dict[int, dict[int, list[list[float]]]] = defaultdict(dict)

    # Get all orbit codes with their dimensions
    # Optionally exclude CM forms (is_cm = true) to match Experiment F's methodology
    cm_clause = "AND n.is_cm = false" if exclude_cm else ""
    query_orbit_codes = f"""
        SELECT DISTINCT n.dim, cc.hecke_orbit_code
        FROM mf_hecke_cc cc
        JOIN mf_newforms n ON cc.hecke_orbit_code = n.hecke_orbit_code
        WHERE n.weight = 2 AND n.char_order = 1
          AND n.dim >= %s AND n.dim <= %s
          {cm_clause}
        ORDER BY n.dim, cc.hecke_orbit_code
    """
    # NOTE: Per-dimension cap is applied in Python (not SQL LIMIT) to ensure
    # every dimension gets its fair share, not just the dominant dim=1.
    params = (min_dim, max_dim)

    logger.info(f"Fetching orbit codes for dim {min_dim}..{max_dim}...")
    with conn.cursor() as cur:
        cur.execute(query_orbit_codes, params)
        orbit_rows = cur.fetchall()
    
    logger.info(f"Found {len(orbit_rows):,} orbit rows (may have duplicates)")

    # Group orbit codes by dimension and collect unique orbits
    dim_orbits: dict[int, set[int]] = defaultdict(set)
    for dim, orbit_code in orbit_rows:
        dim_orbits[dim].add(orbit_code)

    # Apply per-dimension cap if limit is set
    if limit > 0:
        for d in list(dim_orbits.keys()):
            if len(dim_orbits[d]) > limit:
                logger.info(f"  dim={d}: capping {len(dim_orbits[d])} → {limit} orbits")
                dim_orbits[d] = set(list(dim_orbits[d])[:limit])

    total_orbits = sum(len(v) for v in dim_orbits.values())
    logger.info(f"Unique orbit codes: {total_orbits:,}")
    for d in sorted(dim_orbits.keys()):
        logger.info(f"  dim={d}: {len(dim_orbits[d]):,} orbits")

    # For each dimension, fetch per-embedding eigenvalues for each orbit
    # an_normalized is a PostgreSQL array (1-indexed):
    # index 1 = a_0, index 2 = a_1, index 3 = a_2, ...
    # For prime p, we need index (p+1) to get a_p
    # FIX: Fetch full array, slice in Python (avoids invalid SQL array indexing)
    prime_idx_set = {p + 1 for p in PRIMES_100}  # PostgreSQL 1-indexed positions
    
    processed_orbits = 0
    total_orb = total_orbits

    for dim in sorted(dim_orbits.keys()):
        orbit_codes = list(dim_orbits[dim])
        n_orbits = len(orbit_codes)

        # Process in batches
        batch_size = 500
        for batch_start in range(0, n_orbits, batch_size):
            batch_codes = orbit_codes[batch_start:batch_start + batch_size]

            # Fetch full an_normalized array (slicing done in Python)
            query = """
                SELECT cc.hecke_orbit_code, cc.label, cc.an_normalized
                FROM mf_hecke_cc cc
                WHERE cc.hecke_orbit_code = ANY(%s)
            """
            
            try:
                with conn.cursor() as cur:
                    cur.execute(query, (batch_codes,))
                    rows = cur.fetchall()
            except psycopg2.Error as e:
                logger.error(f"Query failed for dim={dim} batch: {e}")
                conn.rollback()
                continue

            # Group embeddings by orbit_code
            orbit_embeddings: dict[int, list[list[float]]] = defaultdict(list)
            for orbit_code, label, an_norm in rows:
                if an_norm is None:
                    continue
                # an_norm is a list of [real, imag] pairs (Python 0-indexed after psycopg2 fetch)
                # VERIFIED: an_norm[0] = a_1, an_norm[1] = a_2, ..., an_norm[n-1] = a_n
                # Values are a_n/√n (NOT a_n/(2√n) Sato-Tate — factor 2 cancels in ρ ratio)
                # For prime p, we need an_norm[p-1] to get a_p/√p
                x_values = []
                for p in PRIMES_100:
                    idx = p - 1  # 0-indexed: a_p is at position p-1
                    if idx < len(an_norm):
                        pair = an_norm[idx]
                        if isinstance(pair, (list, tuple)) and len(pair) >= 1:
                            x_values.append(float(pair[0]))
                        elif isinstance(pair, (int, float)):
                            x_values.append(float(pair))
                        else:
                            x_values.append(0.0)
                    else:
                        x_values.append(0.0)
                orbit_embeddings[orbit_code].append(x_values)

            # Build arrays for each orbit
            for orbit_code, embeddings in orbit_embeddings.items():
                if len(embeddings) != dim:
                    # Some orbits may not have all embeddings in the table
                    logger.debug(f"orbit {orbit_code}: expected {dim} embeddings, got {len(embeddings)}")
                    continue
                
                # Shape: (d, n_primes)
                arr = np.array(embeddings, dtype=np.float64)
                if orbit_code not in dim_data[dim]:
                    dim_data[dim][orbit_code] = arr

        processed_orbits += n_orbits
        logger.info(f"  dim={dim}: {n_orbits} orbits processed ({100 * processed_orbits // total_orb}%)")

    return dict(dim_data)


def compute_rho2_from_cc(dim_data: dict[int, dict[int, np.ndarray]]) -> dict:
    """Compute M₂, M₂·d, and ρ for each dimension using correct mf_hecke_cc data.

    Formula:
      x_p^(i) = an_normalized[p].real (already Sato-Tate normalized)
      Tr(x_p) = sum_i x_p^(i) for prime p
      M₂(d) = E[(Tr(x_p)/d)²]
      M₂(d)·d = d * M₂(d) = E[Tr(x_p)²/d]
      ρ(d) = M₂(d)·d / M₂(1)·1 - 1
    """
    results = {}

    for d in sorted(dim_data.keys()):
        orbits = list(dim_data[d].values())
        n_orbits = len(orbits)
        
        if n_orbits == 0:
            continue

        # Stack: compute Tr(x_p) per orbit
        # For each orbit, sum across embeddings: shape (n_orbits, n_primes)
        trace_values = np.stack([np.sum(orb, axis=0) for orb in orbits])  # (n_orbits, n_primes)
        
        # x_p = Tr(x_p)/d (average across embeddings)
        x_avg = trace_values / d

        # Per-embedding analysis (for REFERENCE)
        all_embeddings = np.vstack(orbits)
        M2_embed = float(np.nanmean(all_embeddings ** 2))

        # M₂(d) = E[x_p²]
        M2_trace = float(np.nanmean(x_avg ** 2))
        
        # M₂(d)·d
        M2d = M2_trace * d
        
        # ρ(d) = M₂(d)·d / M₂(1)·1 - 1
        rho = None
        if 1 in results and d >= 2:
            rho = M2d / results[1]["M2d"] - 1.0

        results[d] = {
            "d": d,
            "n_orbits": n_orbits,
            "M2_trace": M2_trace,
            "M2d": M2d,
            "rho": rho,
            "M2_embed": M2_embed,
        }

        rho_str = f"  ρ={rho:.4f}" if rho is not None else ""
        logger.info(f"dim={d:3d}  orbits={n_orbits:6,d}  M₂={M2_trace:.6f}  M₂·d={M2d:.6f}{rho_str}")

    return results


def compute_pairwise_correlation(dim_data: dict[int, dict[int, np.ndarray]]) -> dict:
    """Compute pairwise correlation between Galois-conjugate embeddings for d=2."""
    orbits_2 = dim_data.get(2, {})
    pairwise_rhos = []

    for orbit_code, arr in orbits_2.items():
        if arr.shape[0] != 2:
            continue
        emb0 = arr[0, :]
        emb1 = arr[1, :]
        valid = ~(np.isnan(emb0) | np.isnan(emb1))
        if valid.sum() < 3:
            continue
        corr = np.corrcoef(emb0[valid], emb1[valid])[0, 1]
        pairwise_rhos.append(corr)

    if len(pairwise_rhos) == 0:
        logger.warning("No valid dim=2 orbits for pairwise correlation; returning NaN.")
        return {
            "n_orbits": 0,
            "mean_rho": float("nan"),
            "std_rho": float("nan"),
            "median_rho": float("nan"),
            "q25_rho": float("nan"),
            "q75_rho": float("nan"),
        }

    pairwise_rhos = np.array(pairwise_rhos)
    result = {
        "n_orbits": len(pairwise_rhos),
        "mean_rho": float(np.mean(pairwise_rhos)),
        "std_rho": float(np.std(pairwise_rhos)),
        "median_rho": float(np.median(pairwise_rhos)),
        "q25_rho": float(np.percentile(pairwise_rhos, 25)),
        "q75_rho": float(np.percentile(pairwise_rhos, 75)),
    }

    logger.info(
        f"\nd=2 pairwise ρ = {result['mean_rho']:.4f} ± {result['std_rho']:.4f} "
        f"(n={result['n_orbits']}, median={result['median_rho']:.4f})"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="ρ₂ analysis from mf_hecke_cc per-embedding eigenvalues")
    parser.add_argument("--min-dim", type=int, default=1, help="Minimum dimension")
    parser.add_argument("--max-dim", type=int, default=20, help="Maximum dimension")
    parser.add_argument("--limit", type=int, default=0, help="Limit orbit codes per dim")
    parser.add_argument("--exclude-cm", action="store_true", help="Exclude CM forms (match Experiment F)")
    parser.add_argument("--output", type=str, default="data/lmfdb/rho2_cc_analysis.json")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    conn = connect_db()
    
    # Fetch per-embedding eigenvalues
    dim_data = fetch_per_embedding_eigenvalues(
        conn, min_dim=args.min_dim, max_dim=args.max_dim, limit=args.limit,
        exclude_cm=args.exclude_cm,
    )
    conn.close()

    # Compute ρ₂
    results = compute_rho2_from_cc(dim_data)
    pairwise = compute_pairwise_correlation(dim_data)

    # Print report
    print("=" * 70)
    print("  ρ₂ Galois Correlation — mf_hecke_cc (True Embedding Eigenvalues)")
    print("=" * 70)
    print(f"  {'d':>4s} {'orbits':>8s} {'M₂':>10s} {'M₂·d':>10s} {'ρ':>10s}")
    print(f"  {'—':>4s} {'—':>8s} {'—':>10s} {'—':>10s} {'—':>10s}")
    for d in sorted(results.keys()):
        r = results[d]
        rho_str = f"{r['rho']:.4f}" if r['rho'] is not None else "— (base)"
        print(f"  {d:4d} {r['n_orbits']:8,d} {r['M2_trace']:10.6f} {r['M2d']:10.6f} {rho_str:>10s}")

    if 2 in results and 1 in results:
        rho2 = results[2]["rho"]
        print(f"\nρ₂ (d=2 Galois correlation): ρ = {rho2:.4f}")
        print(f"  Experiment F reported: ρ = -0.607")
        print(f"  Match: {'✅ EXACT' if abs(rho2 + 0.607) < 0.02 else '⚠️ CLOSE' if abs(rho2 + 0.607) < 0.05 else '⟳ DIFFERENT'}: diff = {abs(rho2 + 0.607):.4f}")

    print(f"\nd=2 pairwise embedding correlation:")
    print(f"  ρ = {pairwise['mean_rho']:.4f} ± {pairwise['std_rho']:.4f}")
    print(f"  median = {pairwise['median_rho']:.4f}")
    print(f"  N = {pairwise['n_orbits']} orbits")

    # Save
    save_data = {
        "n_dimensions": len(results),
        "dimension_results": {str(d): r for d, r in results.items()},
        "pairwise_d2": pairwise,
    }
    output_path = args.output
    with open(output_path, "w") as f:
        json.dump(save_data, f, indent=2)
    logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
