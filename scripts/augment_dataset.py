"""
Data augmentation for GNN training on SL(2,F_p) Cayley graphs.

Generates hundreds of training samples from 18 full graphs via:
  1. Random connected subgraph extraction (BFS from random seed node)
  2. Alternative generator sets (root_weyl in addition to fundamental_roots)

Outputs:
    data/augmented/train/*.pt  — PyG Data objects for training
    data/augmented/test/*.pt   — PyG Data objects for testing
    data/augmented/manifest.json

Usage:
    python augment_dataset.py --all
    python augment_dataset.py --primes 2,3,5,7,11
    python augment_dataset.py --num-subgraphs 100 --min-size 50 --max-size 5000
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from scipy.sparse import csr_matrix
from torch_geometric.data import Data
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data"
GRAPH_DIR = DATA_DIR / "cayley-graphs"
EIGEN_DIR = DATA_DIR / "eigenvalues"
AUG_DIR = DATA_DIR / "augmented"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def discover_primes() -> list[int]:
    """Find all primes with both graph and eigenvalue data."""
    primes = []
    for f in GRAPH_DIR.glob("sl2fp_p*.pt"):
        p = int(f.stem.split("_p")[1])
        stats_path = EIGEN_DIR / f"sl2fp_p{p}_stats.npz"
        if stats_path.exists():
            primes.append(p)
    return sorted(primes)


def load_graph(prime: int) -> tuple[np.ndarray, int]:
    """Load graph edges and node count from .pt file."""
    pt_path = GRAPH_DIR / f"sl2fp_p{prime}.pt"
    data = torch.load(pt_path, weights_only=False)
    edge_index = data.edge_index.numpy()
    num_nodes = data.num_nodes
    return edge_index, num_nodes


def load_stats(prime: int) -> dict:
    """Load eigenvalue stats for a prime."""
    stats_path = EIGEN_DIR / f"sl2fp_p{prime}_stats.npz"
    stats = dict(np.load(stats_path))
    return {k: float(v) for k, v in stats.items()}


def parse_primes(spec: str) -> list[int]:
    """Parse prime specification: '2-61', '2,3,5,7,11'."""
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return [p for p in range(int(lo), int(hi) + 1) if _is_prime(p)]
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


# ---------------------------------------------------------------------------
# Node feature computation (subgraph-local)
# ---------------------------------------------------------------------------


def compute_node_features(
    edge_index: np.ndarray, num_nodes: int, max_nodes_for_triangles: int = 5000
) -> torch.Tensor:
    """
    Compute rich node features from edge_index alone.

    Features per node:
        x[0]: degree in subgraph (normalized by max degree)
        x[1]: local clustering coefficient
        x[2]: number of triangles the node participates in

    For large graphs (> max_nodes_for_triangles), skip expensive
    triangle/clustering computation and use degree-only features padded with zeros.
    """
    # Build adjacency as sparse matrix
    adj = csr_matrix(
        (
            np.ones(edge_index.shape[1], dtype=np.float64),
            (edge_index[0], edge_index[1]),
        ),
        shape=(num_nodes, num_nodes),
    )
    # Symmetrize
    adj = adj.maximum(adj.T)

    degrees = np.array(adj.sum(axis=1)).flatten().astype(np.float64)
    max_deg = max(degrees.max(), 1.0)
    norm_degrees = degrees / max_deg

    if num_nodes > max_nodes_for_triangles:
        # Fast path: degree-only features (pad with zeros for triangle/clustering)
        clustering = np.zeros(num_nodes, dtype=np.float64)
        triangles = np.zeros(num_nodes, dtype=np.float64)
    else:
        # Clustering coefficient + triangle count (fully vectorized)
        adj_bool = adj.astype(bool)
        adj_sq = adj_bool.dot(adj_bool)
        tri_matrix = adj_bool.multiply(adj_sq)
        triangles = np.array(tri_matrix.sum(axis=1)).flatten() / 2.0

        possible = degrees * (degrees - 1) / 2.0
        clustering = np.zeros(num_nodes, dtype=np.float64)
        nonzero = possible > 0
        clustering[nonzero] = triangles[nonzero] / possible[nonzero]

    x = torch.tensor(
        np.stack([norm_degrees, clustering, triangles], axis=1),
        dtype=torch.float32,
    )
    return x


# ---------------------------------------------------------------------------
# Connected subgraph extraction via BFS
# ---------------------------------------------------------------------------


def extract_connected_subgraph(
    edge_index: np.ndarray,
    num_nodes: int,
    subgraph_size: int,
    rng: random.Random,
) -> tuple[np.ndarray, int] | None:
    """
    Extract a connected subgraph of exactly subgraph_size nodes via BFS
    from a random seed node. Uses scipy sparse for fast adjacency lookups.

    Returns (sub_edge_index, sub_num_nodes) or None if graph too small.
    """
    if subgraph_size >= num_nodes:
        return edge_index, num_nodes

    # Build sparse adjacency matrix for O(1) neighbor lookups
    adj = csr_matrix(
        (np.ones(edge_index.shape[1], dtype=bool), (edge_index[0], edge_index[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)  # symmetrize

    seed = rng.randint(0, num_nodes - 1)
    visited = np.zeros(num_nodes, dtype=bool)
    visited[seed] = True
    queue = [seed]
    idx = 0
    count = 1

    while count < subgraph_size and idx < len(queue):
        node = queue[idx]
        idx += 1
        # Get all neighbors via sparse row slice
        row = adj.getrow(node)
        neighbors = row.indices
        for nb in neighbors:
            if not visited[nb]:
                visited[nb] = True
                queue.append(nb)
                count += 1
                if count >= subgraph_size:
                    break

    if count < 3:
        return None

    # Build node mask and remap
    node_indices = np.where(visited)[0]
    node_map = -np.ones(num_nodes, dtype=np.int64)
    node_map[node_indices] = np.arange(count)

    # Filter edges using numpy boolean indexing (vectorized)
    src_mask = visited[edge_index[0]]
    dst_mask = visited[edge_index[1]]
    edge_mask = src_mask & dst_mask
    sub_edges = edge_index[:, edge_mask]
    sub_edges = node_map[sub_edges]  # remap node IDs

    if sub_edges.shape[1] == 0:
        return None

    return sub_edges, count


# ---------------------------------------------------------------------------
# Alternative generator sets via CayleyPy
# ---------------------------------------------------------------------------


def generate_root_weyl_graph(prime: int) -> tuple[np.ndarray, int]:
    """Generate Cayley graph using root+weyl generators."""
    from cayleypy import CayleyGraph, MatrixGroups

    mg = MatrixGroups.special_linear_root_weyl(2, prime)
    graph = CayleyGraph(mg)
    bfs = graph.bfs(return_all_edges=True, return_all_hashes=True)
    edge_list = bfs.edges_list
    num_nodes = bfs.num_vertices
    edges = edge_list.T  # (2, E)
    return edges, num_nodes


# ---------------------------------------------------------------------------
# PyG Data construction
# ---------------------------------------------------------------------------


def make_pyg_data(
    edge_index: np.ndarray,
    num_nodes: int,
    prime: int,
    generator_type: str,
    stats: dict,
    target: str,
    subgraph_size: int | None = None,
    parent_prime: int | None = None,
) -> Data:
    """Build a PyG Data object with rich node features and target."""
    x = compute_node_features(edge_index, num_nodes)

    if target == "spectral_gap":
        y = torch.tensor([stats["spectral_gap"]], dtype=torch.float32)
    elif target == "ramanujan_ratio":
        y = torch.tensor([stats["ramanujan_ratio"]], dtype=torch.float32)
    elif target == "is_ramanujan":
        y = torch.tensor([stats["is_ramanujan"]], dtype=torch.long)
    else:
        raise ValueError(f"Unknown target: {target}")

    data = Data(
        x=x,
        edge_index=torch.from_numpy(edge_index).long(),
        num_nodes=num_nodes,
        y=y,
    )

    return data


# ---------------------------------------------------------------------------
# Train/test split logic
# ---------------------------------------------------------------------------


def get_train_test_primes(
    all_primes: list[int], train_spec: str = "2-50", test_spec: str = "53-101"
) -> tuple[list[int], list[int]]:
    """Split primes into train and test sets matching train_gnn.py defaults."""
    train_set = set(parse_primes(train_spec))
    test_set = set(parse_primes(test_spec))
    train_primes = [p for p in all_primes if p in train_set]
    test_primes = [p for p in all_primes if p in test_set]
    return train_primes, test_primes


# ---------------------------------------------------------------------------
# Main augmentation pipeline
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Augment SL(2,F_p) Cayley graph dataset"
    )
    parser.add_argument(
        "--all", action="store_true", help="Augment all available graphs"
    )
    parser.add_argument("--primes", type=str, help="Specific primes (e.g. '2,3,5,7')")
    parser.add_argument(
        "--num-subgraphs", type=int, default=50, help="Subgraphs per graph"
    )
    parser.add_argument("--min-size", type=int, default=20, help="Min subgraph size")
    parser.add_argument("--max-size", type=int, default=5000, help="Max subgraph size")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--target",
        type=str,
        choices=["spectral_gap", "ramanujan_ratio", "is_ramanujan"],
        default="spectral_gap",
        help="Prediction target",
    )
    parser.add_argument(
        "--include-root-weyl",
        action="store_true",
        default=False,
        help="Generate alternative generator set graphs (expensive for large primes)",
    )
    parser.add_argument(
        "--root-weyl-max-nodes",
        type=int,
        default=5000,
        help="Skip root_weyl generation for graphs larger than this",
    )
    parser.add_argument(
        "--train-primes", type=str, default="2-50", help="Train split primes"
    )
    parser.add_argument(
        "--test-primes", type=str, default="53-101", help="Test split primes"
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    # Determine primes to process
    if args.all:
        all_primes = discover_primes()
        logger.info(f"Found {len(all_primes)} graphs with eigenvalue data")
    elif args.primes:
        all_primes = parse_primes(args.primes)
    else:
        parser.print_help()
        return

    train_primes, test_primes = get_train_test_primes(
        all_primes, args.train_primes, args.test_primes
    )
    logger.info(f"Train primes: {train_primes}")
    logger.info(f"Test primes: {test_primes}")

    train_dir = AUG_DIR / "train"
    test_dir = AUG_DIR / "test"
    train_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "target": args.target,
        "num_subgraphs_per_graph": args.num_subgraphs,
        "min_size": args.min_size,
        "max_size": args.max_size,
        "include_root_weyl": args.include_root_weyl,
        "seed": args.seed,
        "samples": [],
    }

    total_generated = 0

    for prime in tqdm(all_primes, desc="Augmenting graphs"):
        try:
            edge_index, num_nodes = load_graph(prime)
            stats = load_stats(prime)
        except Exception as e:
            logger.warning(f"p={prime}: skipping (load error: {e})")
            continue

        is_train = prime in set(train_primes)
        split = "train" if is_train else "test"
        out_dir = train_dir if is_train else test_dir

        # --- 1. Full graph with rich features (replace constant-1 features) ---
        full_data = make_pyg_data(
            edge_index, num_nodes, prime, "fundamental_roots", stats, args.target
        )
        full_path = out_dir / f"p{prime}_fundamental_full.pt"
        torch.save(full_data, full_path)
        manifest["samples"].append(
            {
                "file": str(full_path.relative_to(AUG_DIR)),
                "prime": prime,
                "generator_type": "fundamental_roots",
                "type": "full_graph",
                "num_nodes": num_nodes,
                "split": split,
            }
        )
        total_generated += 1

        # --- 2. Connected subgraphs from fundamental_roots graph ---
        actual_min = max(args.min_size, 3)
        actual_max = min(args.max_size, num_nodes)
        if actual_max < actual_min:
            actual_max = actual_min  # tiny graph, take whole thing
        for i in range(args.num_subgraphs):
            size = rng.randint(actual_min, actual_max)
            if size >= num_nodes:
                continue  # skip, full graph already saved
            result = extract_connected_subgraph(edge_index, num_nodes, size, rng)
            if result is None:
                continue
            sub_edges, sub_n = result

            sub_data = make_pyg_data(
                sub_edges,
                sub_n,
                prime,
                "fundamental_roots",
                stats,
                args.target,
                subgraph_size=sub_n,
                parent_prime=prime,
            )
            sub_path = out_dir / f"p{prime}_fundamental_sub{i:04d}.pt"
            torch.save(sub_data, sub_path)
            manifest["samples"].append(
                {
                    "file": str(sub_path.relative_to(AUG_DIR)),
                    "prime": prime,
                    "generator_type": "fundamental_roots",
                    "type": "subgraph",
                    "num_nodes": sub_n,
                    "parent_prime": prime,
                    "split": split,
                }
            )
            total_generated += 1

        # --- 3. Alternative generator set (root_weyl) ---
        if args.include_root_weyl and num_nodes <= args.root_weyl_max_nodes:
            try:
                rw_edges, rw_num_nodes = generate_root_weyl_graph(prime)
                # Root-weyl graphs share the same group, so same spectral class
                # Compute eigenvalues for the root_weyl graph
                from scipy.sparse import csr_matrix as _csr
                from scipy.sparse.linalg import eigsh as _eigsh

                adj = _csr(
                    (
                        np.ones(rw_edges.shape[1], dtype=np.float64),
                        (rw_edges[0], rw_edges[1]),
                    ),
                    shape=(rw_num_nodes, rw_num_nodes),
                )
                adj = adj.maximum(adj.T)
                k = min(100, rw_num_nodes - 2)
                eigenvalues = np.sort(_eigsh(adj, k=k, which="LM")[0])[::-1]
                nontrivial = eigenvalues[np.abs(eigenvalues - 4) > 1e-6]
                spectral_gap = (
                    4.0 - np.abs(nontrivial[0]) if len(nontrivial) > 0 else 0.0
                )
                ramanujan_bound = 2.0 * np.sqrt(3)
                max_abs_eig = np.max(np.abs(nontrivial)) if len(nontrivial) > 0 else 0.0
                ramanujan_ratio = (
                    max_abs_eig / ramanujan_bound
                    if ramanujan_bound > 0
                    else float("inf")
                )
                is_ramanujan = ramanujan_ratio <= 1.0 + 1e-10
                rw_stats = {
                    "spectral_gap": spectral_gap,
                    "ramanujan_ratio": ramanujan_ratio,
                    "is_ramanujan": is_ramanujan,
                }

                # Full root-weyl graph
                rw_data = make_pyg_data(
                    rw_edges, rw_num_nodes, prime, "root_weyl", rw_stats, args.target
                )
                rw_path = out_dir / f"p{prime}_root_weyl_full.pt"
                torch.save(rw_data, rw_path)
                manifest["samples"].append(
                    {
                        "file": str(rw_path.relative_to(AUG_DIR)),
                        "prime": prime,
                        "generator_type": "root_weyl",
                        "type": "full_graph",
                        "num_nodes": rw_num_nodes,
                        "split": split,
                    }
                )
                total_generated += 1

                # Subgraphs from root_weyl graph
                rw_actual_min = max(args.min_size, 3)
                rw_actual_max = min(args.max_size, rw_num_nodes)
                if rw_actual_max < rw_actual_min:
                    rw_actual_max = rw_actual_min
                for i in range(args.num_subgraphs):
                    size = rng.randint(rw_actual_min, rw_actual_max)
                    if size >= rw_num_nodes:
                        continue
                    result = extract_connected_subgraph(
                        rw_edges, rw_num_nodes, size, rng
                    )
                    if result is None:
                        continue
                    sub_edges_rw, sub_n_rw = result

                    sub_data_rw = make_pyg_data(
                        sub_edges_rw,
                        sub_n_rw,
                        prime,
                        "root_weyl",
                        rw_stats,
                        args.target,
                        subgraph_size=sub_n_rw,
                        parent_prime=prime,
                    )
                    sub_path_rw = out_dir / f"p{prime}_root_weyl_sub{i:04d}.pt"
                    torch.save(sub_data_rw, sub_path_rw)
                    manifest["samples"].append(
                        {
                            "file": str(sub_path_rw.relative_to(AUG_DIR)),
                            "prime": prime,
                            "generator_type": "root_weyl",
                            "type": "subgraph",
                            "num_nodes": sub_n_rw,
                            "parent_prime": prime,
                            "split": split,
                        }
                    )
                    total_generated += 1

            except Exception as e:
                logger.warning(f"p={prime}: root_weyl generation failed ({e})")

    # Save manifest
    manifest_path = AUG_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    train_count = len(list(train_dir.glob("*.pt")))
    test_count = len(list(test_dir.glob("*.pt")))
    logger.success(
        f"Done. {total_generated} samples → "
        f"{train_count} train, {test_count} test → {AUG_DIR}"
    )


if __name__ == "__main__":
    main()
