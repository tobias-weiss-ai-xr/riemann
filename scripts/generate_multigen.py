"""
Multi-generator Cayley graph pipeline for SL(2,F_p).

Generates ~130 graphs (13 primes x 10 generator sets), computes eigenvalues,
and saves both numpy and PyG formats.

Generator sets per prime:
    fr      — fundamental roots (existing data, symlinked/referenced)
    rw      — root + weyl generators
    rand_0  through  rand_7  — 8 random 4-element generator sets

Outputs:
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}.npz          — edge list + num_nodes
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}.pt           — PyG Data object
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}_eigenvalues.npy
    data/cayley-multigen/sl2fp_p{prime}_{gen_type}_stats.npz
    data/cayley-multigen/manifest.json

Usage:
    python generate_multigen.py
    python generate_multigen.py --skip-existing
    python generate_multigen.py --primes 11,17,19
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from loguru import logger
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigsh
from torch_geometric.data import Data
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIMES = [11, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]
GEN_TYPES = ["fr", "rw"] + [f"rand_{i}" for i in range(8)]  # 10 total
NUM_RAND_GENERATORS = 4
RANDOM_BASE_SEED = 42
EIGENVALUE_K = 2  # Only need top-2 for spectral gap: degree - |2nd eigenvalue|

DATA_DIR = Path(__file__).parent.parent / "data"
MULTIGEN_DIR = DATA_DIR / "cayley-multigen"
EXISTING_GRAPH_DIR = DATA_DIR / "cayley-graphs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sl2fp_order(p: int) -> int:
    """Order of SL(2,F_p) = p * (p^2 - 1)."""
    return p * (p * p - 1)


def random_sl2_matrix(p: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a random matrix in SL(2,F_p) via rejection sampling."""
    while True:
        m = rng.integers(0, p, size=(2, 2))
        det = int(np.round(np.linalg.det(m))) % p
        if det != 0:
            inv_det = pow(det, p - 2, p)  # Fermat's little theorem
            m = (m * inv_det) % p
            if int(round(np.linalg.det(m))) % p == 1:
                return m


def generate_random_generators(p: int, seed: int) -> list[np.ndarray]:
    """Generate NUM_RAND_GENERATORS random SL(2,F_p) matrices."""
    rng = np.random.default_rng(seed)
    return [random_sl2_matrix(p, rng) for _ in range(NUM_RAND_GENERATORS)]


# ---------------------------------------------------------------------------
# Graph generation
# ---------------------------------------------------------------------------


def generate_fr_graph(prime: int) -> tuple[np.ndarray, int] | None:
    """
    Fundamental roots graph — copy from existing cayley-graphs directory.
    Returns None if source file doesn't exist.
    """
    src_npz = EXISTING_GRAPH_DIR / f"sl2fp_p{prime}.npz"
    if not src_npz.exists():
        return None
    archive = np.load(src_npz)
    return archive["edges"], int(archive["num_nodes"])


def generate_rw_graph(prime: int) -> tuple[np.ndarray, int]:
    """Root + Weyl generator graph."""
    from cayleypy import CayleyGraph, MatrixGroups

    mg = MatrixGroups.special_linear_root_weyl(2, prime)
    graph = CayleyGraph(mg)
    bfs = graph.bfs(return_all_edges=True, return_all_hashes=True)
    edges = bfs.edges_list.T  # (2, E)
    return edges, bfs.num_vertices


def generate_random_graph(
    prime: int, gen_idx: int, max_retries: int = 20
) -> tuple[np.ndarray, int, int] | None:
    """
    Random generator set graph. Returns (edges, num_nodes, seed_used) or None on failure.
    Retries with incremented seeds until generators span the full group.
    """
    from cayleypy.cayley_graph_def import CayleyGraphDef, MatrixGenerator

    expected_order = sl2fp_order(prime)
    for attempt in range(max_retries):
        seed = RANDOM_BASE_SEED + gen_idx * 100 + attempt
        matrices = generate_random_generators(prime, seed)
        mg_list = [MatrixGenerator(matrix=m, modulo=prime) for m in matrices]
        cgdef = CayleyGraphDef.for_matrix_group(
            generators=mg_list, name=f"random_{gen_idx}"
        )
        from cayleypy import CayleyGraph

        cg = CayleyGraph(cgdef)
        bfs = cg.bfs(return_all_edges=True, return_all_hashes=True)
        num_nodes = bfs.num_vertices
        if num_nodes == expected_order:
            edges = bfs.edges_list.T  # (2, E)
            return edges, num_nodes, seed
        logger.debug(
            f"p={prime} rand_{gen_idx} attempt {attempt}: "
            f"got {num_nodes} nodes, expected {expected_order}"
        )
    return None


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------


def edges_to_pyg(edges: np.ndarray, num_nodes: int, prime: int, gen_type: str) -> Data:
    """Convert edge list to PyG Data object."""
    edge_index = torch.from_numpy(edges).long()
    x = torch.ones(num_nodes, 1, dtype=torch.float32)
    return Data(
        x=x,
        edge_index=edge_index,
        num_nodes=num_nodes,
        prime=prime,
        group="SL(2,F_p)",
        generator_type=gen_type,
        degree=NUM_RAND_GENERATORS if gen_type.startswith("rand") else None,
    )


def save_graph(
    edges: np.ndarray,
    num_nodes: int,
    prime: int,
    gen_type: str,
    pyg_data: Data,
) -> None:
    """Save graph as .npz and .pt."""
    MULTIGEN_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"sl2fp_p{prime}_{gen_type}"
    np.savez_compressed(MULTIGEN_DIR / f"{stem}.npz", edges=edges, num_nodes=num_nodes)
    torch.save(pyg_data, MULTIGEN_DIR / f"{stem}.pt")


# ---------------------------------------------------------------------------
# Eigenvalue computation
# ---------------------------------------------------------------------------


def compute_eigenvalues(
    edges: np.ndarray, num_nodes: int, k: int = EIGENVALUE_K
) -> tuple[np.ndarray, dict]:
    """
    Compute top-k eigenvalues and spectral stats.
    Returns (eigenvalues_descending, stats_dict).
    """
    adj = csr_matrix(
        (np.ones(edges.shape[1], dtype=np.float64), (edges[0], edges[1])),
        shape=(num_nodes, num_nodes),
    )
    adj = adj.maximum(adj.T)

    # Infer degree from diagonal for regular graphs
    degree = int(adj.sum(axis=1).max())

    k_eff = min(k, num_nodes - 2)
    eigenvalues, _ = eigsh(adj, k=k_eff, which="LM")
    eigenvalues = np.sort(eigenvalues)[::-1]

    # Stats
    nontrivial = eigenvalues[np.abs(eigenvalues - degree) > 1e-6]
    spectral_gap = float(degree - np.abs(nontrivial[0])) if len(nontrivial) > 0 else 0.0
    ramanujan_bound = 2.0 * np.sqrt(max(degree - 1, 1))
    max_abs_eig = float(np.max(np.abs(nontrivial))) if len(nontrivial) > 0 else 0.0
    ramanujan_ratio = (
        max_abs_eig / ramanujan_bound if ramanujan_bound > 0 else float("inf")
    )
    is_ramanujan = ramanujan_ratio <= 1.0 + 1e-10

    stats = {
        "spectral_gap": spectral_gap,
        "ramanujan_bound": ramanujan_bound,
        "max_abs_eigenvalue": max_abs_eig,
        "ramanujan_ratio": ramanujan_ratio,
        "is_ramanujan": is_ramanujan,
        "num_eigenvalues": len(eigenvalues),
        "degree": degree,
    }
    return eigenvalues, stats


def save_eigenvalues(
    prime: int, gen_type: str, eigenvalues: np.ndarray, stats: dict
) -> None:
    """Save eigenvalues and stats."""
    stem = f"sl2fp_p{prime}_{gen_type}"
    np.save(MULTIGEN_DIR / f"{stem}_eigenvalues.npy", eigenvalues)
    np.savez_compressed(MULTIGEN_DIR / f"{stem}_stats.npz", **stats)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def save_manifest(records: list[dict]) -> None:
    """Write manifest.json with all generated graph metadata."""
    MULTIGEN_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "description": "Multi-generator Cayley graphs of SL(2,F_p)",
        "num_graphs": len(records),
        "primes": PRIMES,
        "gen_types": GEN_TYPES,
        "eigenvalue_k": EIGENVALUE_K,
        "graphs": records,
    }
    with open(MULTIGEN_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-generator Cayley graph pipeline for SL(2,F_p)"
    )
    parser.add_argument(
        "--primes",
        type=str,
        default=None,
        help="Comma-separated primes (default: 13 primes with cusp forms)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip graphs that already have .npz output",
    )
    parser.add_argument(
        "--skip-eigenvalues",
        action="store_true",
        help="Skip eigenvalue computation (graph generation only)",
    )
    args = parser.parse_args()

    primes = [int(p.strip()) for p in args.primes.split(",")] if args.primes else PRIMES
    MULTIGEN_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Multi-generator pipeline: {len(primes)} primes x {len(GEN_TYPES)} gen_types"
    )

    # --- Phase 1: Generate graphs ---
    records: list[dict] = []
    tasks = [(p, gt) for p in primes for gt in GEN_TYPES]

    for prime, gen_type in tqdm(tasks, desc="Generating graphs", unit="graph"):
        stem = f"sl2fp_p{prime}_{gen_type}"

        # Skip existing
        if args.skip_existing and (MULTIGEN_DIR / f"{stem}.npz").exists():
            logger.debug(f"Skipping existing: {stem}")
            continue

        try:
            t0 = time.time()

            if gen_type == "fr":
                result = generate_fr_graph(prime)
                if result is None:
                    logger.warning(f"p={prime} fr: source file not found, skipping")
                    continue
                edges, num_nodes = result
            elif gen_type == "rw":
                edges, num_nodes = generate_rw_graph(prime)
            else:
                # rand_i
                gen_idx = int(gen_type.split("_")[1])
                result = generate_random_graph(prime, gen_idx)
                if result is None:
                    logger.warning(
                        f"p={prime} {gen_type}: failed to generate full group after max retries"
                    )
                    continue
                edges, num_nodes, seed_used = result

            # Validate full group coverage
            expected = sl2fp_order(prime)
            if num_nodes != expected:
                logger.warning(
                    f"p={prime} {gen_type}: {num_nodes} nodes != {expected}, skipping"
                )
                continue

            pyg_data = edges_to_pyg(edges, num_nodes, prime, gen_type)
            save_graph(edges, num_nodes, prime, gen_type, pyg_data)

            elapsed = time.time() - t0
            num_edges = edges.shape[1]

            record = {
                "prime": prime,
                "gen_type": gen_type,
                "num_nodes": num_nodes,
                "num_edges": num_edges,
                "generation_time_s": round(elapsed, 2),
            }
            if gen_type.startswith("rand"):
                record["seed"] = seed_used

            # --- Phase 2: Eigenvalues (sequential, same loop) ---
            if not args.skip_eigenvalues:
                try:
                    eigenvalues, stats = compute_eigenvalues(edges, num_nodes)
                    save_eigenvalues(prime, gen_type, eigenvalues, stats)
                    record.update(
                        {
                            "spectral_gap": round(stats["spectral_gap"], 6),
                            "ramanujan_ratio": round(stats["ramanujan_ratio"], 6),
                            "is_ramanujan": stats["is_ramanujan"],
                            "degree": stats["degree"],
                        }
                    )
                    record["eigenvalue_time_s"] = round(time.time() - t0 - elapsed, 2)
                except Exception as e:
                    logger.error(f"  p={prime} {gen_type}: eigenvalue FAILED — {e}")

            records.append(record)
            logger.info(
                f"  p={prime} {gen_type}: {num_nodes} nodes, {num_edges} edges "
                f"({elapsed:.1f}s)"
            )

        except Exception as e:
            logger.error(f"  p={prime} {gen_type}: FAILED — {e}")
            continue

    # --- Phase 3: Manifest ---
    save_manifest(records)

    # --- Phase 4: Summary table ---
    if records:
        header = f"{'Prime':>5} {'GenType':>8} {'Nodes':>8} {'Edges':>10} {'SpectralGap':>12} {'RamanujanR':>11} {'Ramanujan':>9}"
        sep = "-" * len(header)
        print(f"\n{'=' * len(header)}")
        print("SUMMARY")
        print(f"{'=' * len(header)}")
        print(header)
        print(sep)
        for r in records:
            sg = r.get("spectral_gap", "N/A")
            rr = r.get("ramanujan_ratio", "N/A")
            ir = r.get("is_ramanujan", "N/A")
            print(
                f"{r['prime']:>5} {r['gen_type']:>8} {r['num_nodes']:>8} "
                f"{r['num_edges']:>10} {sg:>12} {rr:>11} {ir!s:>9}"
            )
        print(sep)
        print(f"Total graphs: {len(records)}")
        print(f"Output directory: {MULTIGEN_DIR}")
    else:
        logger.warning("No graphs were generated!")

    logger.success("Done.")


if __name__ == "__main__":
    main()
