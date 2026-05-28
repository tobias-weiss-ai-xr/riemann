"""
Compute eigenvalues of Cayley graphs using sparse Lanczos.

Outputs:
    data/eigenvalues/sl2fp_p{prime}_eigenvalues.npy  — sorted eigenvalue array
    data/eigenvalues/sl2fp_p{prime}_stats.npz         — spectral gap, Ramanujan ratio, etc.

Usage:
    python compute_eigenvalues.py --all       # All generated graphs
    python compute_eigenvalues.py --primes 2,3,5,7,11
    python compute_eigenvalues.py --k 10     # Compute only top-k eigenvalues (faster)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data"
EIGEN_DIR = DATA_DIR / "eigenvalues"
GRAPH_DIR = DATA_DIR / "cayley-graphs"


def load_graph(prime: int) -> tuple[np.ndarray, int]:
    """Load graph from numpy archive."""
    path = GRAPH_DIR / f"sl2fp_p{prime}.npz"
    if not path.exists():
        # Try PyG format
        pt_path = GRAPH_DIR / f"sl2fp_p{prime}.pt"
        if not pt_path.exists():
            raise FileNotFoundError(f"No graph found for p={prime}")
        data = torch.load(pt_path, weights_only=False)
        edges = data.edge_index.numpy()
        num_nodes = data.num_nodes
    else:
        archive = np.load(path)
        edges = archive["edges"]
        num_nodes = int(archive["num_nodes"])
    return edges, num_nodes


def compute_spectrum(
    edges: np.ndarray, num_nodes: int, k: int | None = None, full: bool = False
) -> np.ndarray:
    """
    Compute eigenvalues of the adjacency matrix.

    Args:
        edges: shape (2, E)
        num_nodes: number of nodes
        k: number of eigenvalues to compute (None = all). For large graphs, use k << num_nodes.
        full: If True, compute the full spectrum.
    """
    # Build sparse adjacency matrix
    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    # Symmetrize (Cayley graphs are undirected)
    adj = adj.maximum(adj.T)

    if full:
        if num_nodes < 3000:
            # For small graphs, use dense solver for stability and speed
            logger.info(f"Computing FULL spectrum for {num_nodes} nodes via dense eigvalsh")
            eigenvalues = np.linalg.eigvalsh(adj.toarray())
        else:
            # For larger graphs, use eigsh to get almost all eigenvalues
            # k must be < n-1 for eigsh
            logger.info(f"Computing FULL spectrum for {num_nodes} nodes via eigsh(k=n-2)")
            k_eigsh = num_nodes - 2
            eigenvalues, _ = eigsh(adj, k=k_eigsh, which="LM")
    elif k is not None and k < num_nodes:
        # Compute only extreme eigenvalues (fastest via Lanczos)
        # k must be < n-1 for eigsh
        k = min(k, num_nodes - 2)
        eigenvalues, _ = eigsh(adj, k=k, which="LM")  # Largest magnitude
    else:
        # Default fallback (should not be hit if k/full are handled correctly)
        eigenvalues = np.linalg.eigvalsh(adj.toarray())

    return np.sort(eigenvalues)[::-1]  # Descending


def compute_stats(eigenvalues: np.ndarray, degree: int) -> dict:
    """Compute spectral statistics."""
    # Skip trivial eigenvalue (degree of regular graph)
    nontrivial = eigenvalues[np.abs(eigenvalues - degree) > 1e-6]

    spectral_gap = degree - np.abs(nontrivial[0]) if len(nontrivial) > 0 else 0.0
    ramanujan_bound = 2 * np.sqrt(degree - 1)

    # Ramanujan ratio: max |λ| / Ramanujan bound (should be ≤ 1.0)
    max_abs_eigenvalue = np.max(np.abs(nontrivial)) if len(nontrivial) > 0 else 0.0
    ramanujan_ratio = (
        max_abs_eigenvalue / ramanujan_bound if ramanujan_bound > 0 else float("inf")
    )

    is_ramanujan = ramanujan_ratio <= 1.0 + 1e-10

    return {
        "spectral_gap": spectral_gap,
        "ramanujan_bound": ramanujan_bound,
        "max_abs_eigenvalue": max_abs_eigenvalue,
        "ramanujan_ratio": ramanujan_ratio,
        "is_ramanujan": is_ramanujan,
        "num_eigenvalues": len(eigenvalues),
    }


def save_eigenvalues(prime: int, eigenvalues: np.ndarray, stats: dict) -> None:
    """Save eigenvalues and stats."""
    EIGEN_DIR.mkdir(parents=True, exist_ok=True)

    np.save(EIGEN_DIR / f"sl2fp_p{prime}_eigenvalues.npy", eigenvalues)
    np.savez_compressed(EIGEN_DIR / f"sl2fp_p{prime}_stats.npz", **stats)

    logger.info(
        f"  p={prime}: gap={stats['spectral_gap']:.4f}, "
        f"R-ratio={stats['ramanujan_ratio']:.4f}, "
        f"Ramanujan={stats['is_ramanujan']}"
    )


def discover_primes() -> list[int]:
    """Find all primes with generated graphs."""
    primes = []
    for f in GRAPH_DIR.glob("sl2fp_p*.npz"):
        p = int(f.stem.split("_p")[1])
        primes.append(p)
    return sorted(primes)


def main():
    parser = argparse.ArgumentParser(description="Compute eigenvalues of Cayley graphs")
    parser.add_argument(
        "--all", action="store_true", help="Process all generated graphs"
    )
    parser.add_argument("--primes", type=str, help="Specific primes (e.g. '2,3,5,7')")
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Number of eigenvalues to compute (default: all)",
    )
    parser.add_argument(
        "--full", action="store_true", help="Compute full spectrum instead of top-k"
    )
    args = parser.parse_args()

def main():
    parser = argparse.ArgumentParser(description="Compute eigenvalues of Cayley graphs")
    parser.add_argument(
        "--all", action="store_true", help="Process all generated graphs"
    )
    parser.add_argument("--primes", type=str, help="Specific primes (e.g. '2,3,5,7')")
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Number of eigenvalues to compute (default: all)",
    )
    parser.add_argument(
        "--full", action="store_true", help="Compute full spectrum instead of top-k"
    )
    args = parser.parse_args()

    if args.all:
        primes = discover_primes()
        logger.info(f"Found {len(primes)} generated graphs")
    elif args.primes:
        primes = [int(p.strip()) for p in args.primes.split(",")]
    else:
        parser.print_help()
        return

    for prime in tqdm(primes, desc="Computing eigenvalues"):
        try:
            edges, num_nodes = load_graph(prime)
            
            full_mode = args.full
            k_val = None
            if not full_mode and args.k is not None:
                k_val = args.k
                
            eigenvalues = compute_spectrum(edges, num_nodes, k=k_val, full=full_mode)
            stats = compute_stats(
                eigenvalues, degree=4
            )  # 4 fundamental root generators
            save_eigenvalues(prime, eigenvalues, stats)
        except Exception as e:
            logger.error(f"  p={prime}: FAILED — {e}")
            continue

    logger.success(f"Done. Eigenvalues saved to {EIGEN_DIR}")


if __name__ == "__main__":
    main()
