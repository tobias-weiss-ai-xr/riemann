#!/usr/bin/env python3
"""Generate Farey graphs at various levels and compute spectral properties.

The Farey graph of order n has:
  - Vertices: all reduced fractions a/b with 0 <= a <= b <= n, gcd(a,b)=1
  - Edges: two fractions a/b and c/d are connected iff |ad - bc| = 1
  - |V| = 1 + sum(phi(k), k=1..n) ≈ 3n²/π²
  - The Farey graph is the Cayley graph of PSL(2,Z)

Construction uses Stern-Brocot tree BFS (O(|V|) time, verified against brute force).

Usage:
    python generate_farey.py --levels 10 20 50 100 200 500
    python generate_farey.py --max-n 500 --step 10
    python generate_farey.py --max-n 500 --step 10 --compute-spectrum
"""

import argparse
import json
import os
import sys
import time
from collections import deque
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import eigsh

DATA_DIR = Path(__file__).parent.parent / "data" / "farey-graphs"


def farey_graph_stern_brocot(n: int):
    """Build Farey graph using Stern-Brocot tree BFS.

    Two fractions a/b and c/d are Farey neighbors iff |ad-bc|=1.
    Stern-Brocot tree edges = Farey graph edges.

    Args:
        n: Maximum denominator (Farey order)

    Returns:
        vertices: dict mapping Fraction -> node index
        edges: list of (int, int) tuples
    """
    vertices = {}
    edges = []
    queue = deque()

    # Start with 0/1 and 1/1
    vertices[Fraction(0, 1)] = 0
    vertices[Fraction(1, 1)] = 1
    edges.append((0, 1))
    queue.append((Fraction(0, 1), Fraction(1, 1)))

    while queue:
        left, right = queue.popleft()
        mediant = Fraction(
            left.numerator + right.numerator,
            left.denominator + right.denominator,
        )
        if mediant.denominator > n:
            continue
        if mediant not in vertices:
            vertices[mediant] = len(vertices)
            edges.append((vertices[left], vertices[mediant]))
            edges.append((vertices[mediant], vertices[right]))
            queue.append((left, mediant))
            queue.append((mediant, right))

    return vertices, edges


def compute_spectral_properties(vertices, edges, num_eigs=20):
    """Compute spectral properties of the Farey graph.

    Args:
        vertices: dict mapping Fraction -> index
        edges: list of (int, int) tuples
        num_eigs: number of smallest Laplacian eigenvalues to compute

    Returns:
        dict with spectral properties
    """
    N = len(vertices)
    if N < 3:
        return {"num_vertices": N, "num_edges": len(edges), "error": "too_small"}

    # Build sparse adjacency matrix
    rows, cols = [], []
    for i, j in edges:
        rows.extend([i, j])
        cols.extend([j, i])
    data = [1.0] * len(rows)
    A = csr_matrix((data, (rows, cols)), shape=(N, N))

    # Degree
    deg = np.array(A.sum(axis=1)).flatten()
    deg_inv_sqrt = 1.0 / np.sqrt(np.maximum(deg, 1e-10))

    # Normalized Laplacian: L_norm = I - D^{-1/2} A D^{-1/2}
    D_inv_sqrt = diags(deg_inv_sqrt)
    L_norm = diags(np.ones(N)) - D_inv_sqrt @ A @ D_inv_sqrt

    # Compute smallest eigenvalues
    k = min(num_eigs, N - 2)
    if k < 1:
        k = 1
    try:
        eigenvalues, _ = eigsh(L_norm, k=k, which="SM")
        eigenvalues = np.sort(np.real(eigenvalues))
    except Exception:
        # Fallback for very small graphs
        from scipy.linalg import eigh

        L_dense = L_norm.toarray()
        eigenvalues = np.sort(np.real(np.linalg.eigvalsh(L_dense)))[:k]

    # Spectral gap = lambda_2 (lambda_1 = 0 for connected graphs)
    spectral_gap = eigenvalues[1] if len(eigenvalues) > 1 else 0.0
    algebraic_conn = spectral_gap  # For normalized Laplacian

    # Eigenvalue spacing statistics
    if len(eigenvalues) > 2:
        spacings = np.diff(eigenvalues[1:])  # Skip lambda_1=0
        spacing_mean = np.mean(spacings)
        spacing_std = np.std(spacings)
    else:
        spacing_mean = 0.0
        spacing_std = 0.0

    # Degree statistics
    result = {
        "num_vertices": N,
        "num_edges": len(edges),
        "avg_degree": 2 * len(edges) / N,
        "min_degree": int(deg.min()),
        "max_degree": int(deg.max()),
        "degree_std": float(deg.std()),
        "spectral_gap": float(spectral_gap),
        "algebraic_connectivity": float(algebraic_conn),
        "eigenvalues": eigenvalues.tolist(),
        "spacing_mean": float(spacing_mean),
        "spacing_std": float(spacing_std),
    }

    return result


def generate_farey_dataset(levels, compute_spectrum=True, num_eigs=20):
    """Generate Farey graphs at specified levels.

    Args:
        levels: list of integers (Farey orders)
        compute_spectrum: whether to compute spectral properties
        num_eigs: number of eigenvalues to compute

    Returns:
        manifest: dict with all graph metadata
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"graphs": [], "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    for n in levels:
        t0 = time.time()
        vertices, edges = farey_graph_stern_brocot(n)
        t1 = time.time()
        N = len(vertices)
        E = len(edges)

        print(f"n={n:4d}: V={N:6d}, E={E:6d}, generation={t1 - t0:.3f}s", end="")

        # Save graph data
        graph_data = {
            "level": n,
            "num_vertices": N,
            "num_edges": E,
            "vertices": sorted([(f.numerator, f.denominator) for f in vertices.keys()]),
            "edges": edges,
        }

        # Save as JSON (vertices list + edge list)
        graph_path = DATA_DIR / f"farey_n{n:04d}.json"
        with open(graph_path, "w") as f:
            json.dump(graph_data, f)

        # Save sparse adjacency as NPZ
        rows, cols = [], []
        for i, j in edges:
            rows.extend([i, j])
            cols.extend([j, i])
        data = np.ones(len(rows), dtype=np.float32)
        adj = csr_matrix((data, (rows, cols)), shape=(N, N))
        np.savez_compressed(
            DATA_DIR / f"farey_n{n:04d}.npz",
            adj_data=data,
            adj_indices=np.array(rows + cols, dtype=np.int64),
            adj_indptr=adj.indptr.astype(np.int64),
            adj_shape=np.array([N, N], dtype=np.int64),
        )

        entry = {
            "level": n,
            "num_vertices": N,
            "num_edges": E,
            "generation_time": t1 - t0,
            "file_json": str(graph_path.name),
            "file_npz": f"farey_n{n:04d}.npz",
        }

        # Compute spectral properties
        if compute_spectrum and N >= 3:
            t2 = time.time()
            spectral = compute_spectral_properties(vertices, edges, num_eigs)
            t3 = time.time()
            print(f", spectrum={t3 - t2:.3f}s", end="")

            # Save spectral data
            np.savez_compressed(
                DATA_DIR / f"farey_n{n:04d}_spectrum.npz",
                eigenvalues=np.array(spectral["eigenvalues"], dtype=np.float64),
                spectral_gap=np.float64(spectral["spectral_gap"]),
                algebraic_connectivity=np.float64(spectral["algebraic_connectivity"]),
                avg_degree=np.float64(spectral["avg_degree"]),
            )

            entry.update(
                {
                    "spectral_gap": spectral["spectral_gap"],
                    "algebraic_connectivity": spectral["algebraic_connectivity"],
                    "avg_degree": spectral["avg_degree"],
                    "min_degree": spectral["min_degree"],
                    "max_degree": spectral["max_degree"],
                    "degree_std": spectral["degree_std"],
                    "spacing_mean": spectral["spacing_mean"],
                    "spacing_std": spectral["spacing_std"],
                    "num_eigenvalues": len(spectral["eigenvalues"]),
                    "spectrum_time": t3 - t2,
                    "file_spectrum": f"farey_n{n:04d}_spectrum.npz",
                }
            )

        print()
        manifest["graphs"].append(entry)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate Farey graphs")
    parser.add_argument(
        "--levels",
        type=int,
        nargs="+",
        default=None,
        help="Specific Farey orders to generate",
    )
    parser.add_argument(
        "--max-n",
        type=int,
        default=500,
        help="Maximum Farey order (for --step mode)",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=10,
        help="Step size between levels (for --max-n mode)",
    )
    parser.add_argument(
        "--compute-spectrum",
        action="store_true",
        default=True,
        help="Compute spectral properties",
    )
    parser.add_argument(
        "--no-spectrum",
        action="store_true",
        help="Skip spectral computation",
    )
    parser.add_argument(
        "--num-eigs",
        type=int,
        default=20,
        help="Number of eigenvalues to compute",
    )

    args = parser.parse_args()

    # Determine levels
    if args.levels:
        levels = sorted(args.levels)
    else:
        levels = list(range(args.step, args.max_n + 1, args.step))

    print(f"Generating Farey graphs at {len(levels)} levels: {levels}")
    print(f"Output directory: {DATA_DIR}")
    print()

    compute_spectrum = args.compute_spectrum and not args.no_spectrum
    manifest = generate_farey_dataset(levels, compute_spectrum, args.num_eigs)

    # Save manifest
    manifest_path = DATA_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nManifest saved to {manifest_path}")
    print(f"Total graphs: {len(manifest['graphs'])}")


if __name__ == "__main__":
    main()
