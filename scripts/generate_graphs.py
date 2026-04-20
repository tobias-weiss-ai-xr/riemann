"""
Generate Cayley graphs of SL(2,F_p) using CayleyPy.

Outputs:
    data/cayley-graphs/sl2fp_p{prime}.npz  — sparse edge list (numpy)
    data/cayley-graphs/sl2fp_p{prime}.pt   — PyG Data object

Usage:
    python generate_graphs.py --primes 2-101       # All primes up to 101
    python generate_graphs.py --primes 2,3,5,7,11   # Specific primes
    python generate_graphs.py --primes 2-50 --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from torch_geometric.data import Data
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data" / "cayley-graphs"


def parse_primes(spec: str) -> list[int]:
    """Parse prime specification: '2-101', '2,3,5,7,11', or '2-50'."""
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return [p for p in range(int(lo), int(hi) + 1) if _is_prime(p)]
    else:
        return [int(p.strip()) for p in spec.split(",")]


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def generate_cayley_graph_cayleypy(prime: int) -> tuple[np.ndarray, int]:
    """
    Generate Cayley graph of SL(2,F_p) using CayleyPy.

    Returns:
        edges: numpy array of shape (2, E) — source, target pairs
        num_nodes: number of nodes (|SL(2,F_p)| = p(p²-1))
    """
    from cayleypy import CayleyGraph, MatrixGroups

    mg = MatrixGroups.special_linear_fundamental_roots(2, prime)
    graph = CayleyGraph(mg)
    bfs = graph.bfs(return_all_edges=True, return_all_hashes=True)

    # edges_list is (E, 2) numpy array of [src, dst] pairs
    edge_list = bfs.edges_list
    num_nodes = bfs.num_vertices

    edges = edge_list.T  # shape (2, E)

    return edges, num_nodes


def edges_to_pyg(edges: np.ndarray, num_nodes: int, prime: int) -> Data:
    """Convert edge list to PyTorch Geometric Data object."""
    edge_index = torch.from_numpy(edges).long()

    # Node features: prime number as constant feature (placeholder for richer features)
    x = torch.ones(num_nodes, 1, dtype=torch.float32)

    # Metadata
    data = Data(
        x=x,
        edge_index=edge_index,
        num_nodes=num_nodes,
        prime=prime,
        group="SL(2,F_p)",
        generator_type="fundamental_roots",
        degree=4,  # CayleyPy fundamental roots give 4 generators
    )
    return data


def save_graph(edges: np.ndarray, num_nodes: int, pyg_data: Data, prime: int) -> None:
    """Save graph in both numpy and PyG formats."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # NumPy sparse format
    npz_path = DATA_DIR / f"sl2fp_p{prime}.npz"
    np.savez_compressed(npz_path, edges=edges, num_nodes=num_nodes)

    # PyG format
    pt_path = DATA_DIR / f"sl2fp_p{prime}.pt"
    torch.save(pyg_data, pt_path)

    logger.info(
        f"  p={prime}: {num_nodes} nodes, {edges.shape[1]} edges → {npz_path.name}"
    )


def main():
    parser = argparse.ArgumentParser(description="Generate SL(2,F_p) Cayley graphs")
    parser.add_argument(
        "--primes",
        type=str,
        default="2-101",
        help="Prime specification (e.g. '2-101' or '2,3,5,7')",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print primes without generating"
    )
    args = parser.parse_args()

    primes = parse_primes(args.primes)
    logger.info(f"Primes to process: {primes} ({len(primes)} primes)")

    if args.dry_run:
        for p in primes:
            n = p * (p * p - 1)
            logger.info(f"  p={p}: ~{n:,} nodes, ~{n * 2:,} edges (estimated)")
        return

    for prime in tqdm(primes, desc="Generating Cayley graphs"):
        try:
            edges, num_nodes = generate_cayley_graph_cayleypy(prime)
            pyg_data = edges_to_pyg(edges, num_nodes, prime)
            save_graph(edges, num_nodes, pyg_data, prime)
        except Exception as e:
            logger.error(f"  p={prime}: FAILED — {e}")
            continue

    logger.success(f"Done. Graphs saved to {DATA_DIR}")


if __name__ == "__main__":
    main()
