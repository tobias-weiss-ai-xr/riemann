"""Build Pizer graph dataset: Hecke operator matrices as weighted adjacency graphs.

Computes T_ℓ Hecke matrices for S_2(Gamma_0(p)) across 289 primes (dim >= 4)
and 6 ℓ values, then packages them as PyG datasets for eigenvalue prediction.

Tasks:
  1. Compute T_ℓ matrices + eigenvalues via PARI (cached per prime)
  2. Save sparse CSR adjacency + eigenvalues as .npz
  3. Build PyG Data objects with node features, edge attributes, graph stats
  4. Two target modes: cross-ℓ (T₂→T₃) and self-prediction
  5. Three splits: prime LOO-CV, random prime, ℓ-level

Usage:
    python scripts/build_pizer_dataset.py
    python scripts/build_pizer_dataset.py --max-prime 500
    python scripts/build_pizer_dataset.py --skip-compute  # only rebuild .pt from .npz
    python scripts/build_pizer_dataset.py --force  # recompute all
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from loguru import logger
from scipy.sparse import csr_matrix
from tqdm import tqdm

# ---------------------------------------------------------------------------
# PARI (deferred import — may not be available on all hosts)
# ---------------------------------------------------------------------------

pari = None


def _ensure_pari():
    global pari
    if pari is None:
        from cypari2 import Pari

        pari = Pari()
    return pari


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ELL_VALUES = [2, 3, 5, 7, 11, 13]
MAX_DIM = 500  # skip primes with dim > MAX_DIM (too expensive / large graphs)
TIMEOUT_PER_PRIME = 10.0  # seconds

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "pizer"

# ---------------------------------------------------------------------------
# Prime generation
# ---------------------------------------------------------------------------


def sieve_primes(n: int) -> list[int]:
    """Return all primes <= n."""
    if n < 2:
        return []
    is_prime = np.ones(n + 1, dtype=bool)
    is_prime[:2] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            is_prime[i * i :: i] = False
    return [int(i) for i in np.nonzero(is_prime)[0]]


def get_candidate_primes(max_prime: int = 1999) -> list[int]:
    """Get primes where we need to check dim >= 4."""
    all_primes = sieve_primes(max_prime)
    # Start from 47 (p<47 has dim<4 for all)
    return [p for p in all_primes if p >= 47]


# ---------------------------------------------------------------------------
# PARI computation
# ---------------------------------------------------------------------------


def _compute_with_timeout(func, timeout: float):
    """Run func with a timeout. Returns result or None on timeout."""
    result = [None]
    exception = [None]

    def _target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e

    import threading

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        # Thread still running — we can't truly kill it, but we can abandon it
        return None, "timeout"
    if exception[0] is not None:
        return None, str(exception[0])
    return result[0], None


def get_hecke_dim(p: int) -> int:
    """Get dimension of S_2(Gamma_0(p))."""
    P = _ensure_pari()
    return int(P(f"mfdim([{p},2], 1)"))


def compute_hecke_matrix(p: int, ell: int) -> np.ndarray | None:
    """Compute T_ℓ matrix on S_2(Gamma_0(p)) as numpy array.

    Returns None on timeout or error.
    """
    P = _ensure_pari()

    def _compute():
        code = (
            f"my(mf=mfinit([{p},2],1));"
            f"my(B=mfbasis(mf));"
            f"my(M=matrix(#B,#B));"
            f"for(k=1,#B,"
            f"  my(TBk=mfhecke(mf,B[k],{ell}));"
            f"  my(coords=mftobasis(mf,TBk));"
            f"  for(j=1,#B,M[j,k]=coords[j])"
            f");"
            f"M"
        )
        M = P(code)
        return np.array(M.python(), dtype=np.float64)

    result, err = _compute_with_timeout(_compute, TIMEOUT_PER_PRIME)
    if err:
        return None
    return result


# ---------------------------------------------------------------------------
# Phase 1: Compute & cache all matrices
# ---------------------------------------------------------------------------


def compute_all_matrices(
    primes: list[int],
    ells: list[int],
    force: bool = False,
) -> list[dict]:
    """Compute Hecke matrices for all (prime, ell) pairs.

    Caches results as individual .npz files. Returns manifest entries.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    desc = f"Computing Hecke matrices ({len(primes)} primes × {len(ells)} ℓ)"
    for p in tqdm(primes, desc=desc):
        # Check dim
        t_dim_start = time.time()
        dim = get_hecke_dim(p)
        if dim < 4:
            continue
        if dim > MAX_DIM:
            logger.debug(f"p={p}: dim={dim} > {MAX_DIM}, skipping")
            continue

        prime_entry = {
            "p": p,
            "dim": dim,
            "ells": {},
            "timing_dim_s": time.time() - t_dim_start,
            "timing_total_s": 0.0,
            "n_ell_computed": 0,
        }
        t_prime_start = time.time()

        for ell in ells:
            if ell == p:
                continue  # ℓ = p not allowed

            npz_path = DATA_DIR / f"p{p}_ell{ell}.npz"

            # Check cache
            if npz_path.exists() and not force:
                try:
                    data = np.load(npz_path)
                    eigenvalues = data["eigenvalues"]
                    deligne_ratio = float(
                        np.max(np.abs(eigenvalues)) / (2.0 * np.sqrt(ell))
                    )
                    prime_entry["ells"][str(ell)] = {
                        "eigenvalues": np.round(eigenvalues, 8).tolist(),
                        "deligne_ratio": deligne_ratio,
                        "cached": True,
                    }
                    prime_entry["n_ell_computed"] += 1
                    continue
                except Exception:
                    pass  # recompute

            # Compute
            t_start = time.time()
            M = compute_hecke_matrix(p, ell)
            t_elapsed = time.time() - t_start

            if M is None:
                logger.warning(f"  p={p} ℓ={ell}: computation failed/timeout")
                continue

            # Verify symmetry (Hecke operators are self-adjoint)
            sym_err = float(np.max(np.abs(M - M.T)))
            if sym_err > 1e-6:
                logger.warning(
                    f"  p={p} ℓ={ell}: asymmetry detected (max|M-Mᵀ|={sym_err:.2e}), symmetrizing"
                )
                M = (M + M.T) / 2.0

            # Compute eigenvalues (symmetric → real eigenvalues)
            eigenvalues = np.linalg.eigvalsh(M)
            eigenvalues = np.sort(eigenvalues)  # ascending

            # Deligne bound ratio: max|eigenvalue| / (2*sqrt(ℓ))
            deligne_ratio = float(np.max(np.abs(eigenvalues)) / (2.0 * np.sqrt(ell)))

            # Save as sparse CSR + eigenvalues
            M_sparse = csr_matrix(M)
            M_sparse.eliminate_zeros()

            np.savez_compressed(
                npz_path,
                data=M_sparse.data,
                indices=M_sparse.indices,
                indptr=M_sparse.indptr,
                shape=np.array(M_sparse.shape),
                eigenvalues=eigenvalues,
                matrix_dense=M,  # keep dense for small dims
            )

            prime_entry["ells"][str(ell)] = {
                "eigenvalues": np.round(eigenvalues, 8).tolist(),
                "deligne_ratio": deligne_ratio,
                "timing_s": t_elapsed,
                "symmetry_error": sym_err,
                "nnz": int(M_sparse.nnz),
                "density": float(M_sparse.nnz / (dim * dim)),
                "cached": False,
            }
            prime_entry["n_ell_computed"] += 1

        prime_entry["timing_total_s"] = time.time() - t_prime_start

        if prime_entry["n_ell_computed"] > 0:
            manifest.append(prime_entry)

    return manifest


# ---------------------------------------------------------------------------
# Phase 2: Load cached data into PyG Data objects
# ---------------------------------------------------------------------------


def _load_hecke_npz(p: int, ell: int) -> dict | None:
    """Load a cached Hecke matrix .npz file."""
    npz_path = DATA_DIR / f"p{p}_ell{ell}.npz"
    if not npz_path.exists():
        return None
    data = np.load(npz_path)
    return {
        "data": data["data"],
        "indices": data["indices"],
        "indptr": data["indptr"],
        "shape": tuple(data["shape"]),
        "eigenvalues": data["eigenvalues"],
        "matrix_dense": data["matrix_dense"],
    }


def build_pyg_graph(p: int, ell: int, cache: dict) -> dict | None:
    """Build graph representation from a Hecke matrix.

    Returns dict with:
        - edge_index: (2, E) tensor of source/target node indices
        - edge_attr: (E, 2) tensor of [abs_weight, sign]
        - x: (N, 3) node features [degree, row_sum, diagonal]
        - eigenvalues: (dim,) sorted eigenvalues
        - graph_stats: (6,) scalar features
        - p, ell, dim: metadata
    """
    key = (p, ell)
    if key not in cache:
        loaded = _load_hecke_npz(p, ell)
        if loaded is None:
            return None
        cache[key] = loaded

    entry = cache[key]
    dim = entry["shape"][0]
    M_dense = entry["matrix_dense"]
    eigenvalues = entry["eigenvalues"]

    # Build edge list from nonzero entries of symmetric matrix
    # Use upper triangle to avoid duplicate edges
    rows, cols = np.where(np.abs(M_dense) > 0)
    # Keep only upper triangle (i <= j) for undirected graph
    mask = rows <= cols
    rows, cols = rows[mask], cols[mask]
    weights = M_dense[rows, cols]

    # Edge attributes: [abs_weight, sign]
    abs_weights = np.abs(weights).astype(np.float32)
    signs = np.sign(weights).astype(np.float32)
    signs[signs == 0.0] = 0.0

    # Node features: degree (row nnz), row_sum, diagonal
    row_nnz = np.array((np.abs(M_dense) > 0).sum(axis=1), dtype=np.float32).flatten()
    row_sums = np.array(M_dense.sum(axis=1), dtype=np.float32).flatten()
    diag_vals = np.diag(M_dense).astype(np.float32)

    # Normalize node features
    max_nnz = row_nnz.max() if row_nnz.max() > 0 else 1.0
    row_nnz_norm = row_nnz / max_nnz

    max_abs_row_sum = np.max(np.abs(row_sums)) if np.max(np.abs(row_sums)) > 0 else 1.0
    row_sums_norm = row_sums / max_abs_row_sum

    max_abs_diag = np.max(np.abs(diag_vals)) if np.max(np.abs(diag_vals)) > 0 else 1.0
    diag_norm = diag_vals / max_abs_diag

    x = np.column_stack([row_nnz_norm, row_sums_norm, diag_norm]).astype(np.float32)

    # Graph-level stats: dim, log(dim), log(|V|), density, ℓ, p
    n_edges = len(rows)
    density = (2 * n_edges) / (dim * dim) if dim > 1 else 0.0
    graph_stats = np.array(
        [
            dim / MAX_DIM,  # normalized dim
            np.log(dim) / np.log(MAX_DIM),  # normalized log(dim)
            np.log(dim + 1),  # log(|V|)
            density,
            np.log(ell) / np.log(13),  # normalized log(ℓ)
            np.log(p) / np.log(2000),  # normalized log(p)
        ],
        dtype=np.float32,
    )

    # Deligne ratio
    deligne_ratio = float(np.max(np.abs(eigenvalues)) / (2.0 * np.sqrt(ell)))

    return {
        "edge_index": np.stack([rows, cols], axis=0).astype(np.int64),
        "edge_attr": np.column_stack([abs_weights, signs]).astype(np.float32),
        "x": x,
        "eigenvalues": eigenvalues.astype(np.float32),
        "graph_stats": graph_stats,
        "p": p,
        "ell": ell,
        "dim": dim,
        "deligne_ratio": deligne_ratio,
    }


# ---------------------------------------------------------------------------
# Phase 3: Build PyG datasets
# ---------------------------------------------------------------------------


def build_cross_ell_dataset(
    manifest: list[dict],
    input_ell: int = 2,
    target_ell: int = 3,
) -> tuple[list[dict], dict]:
    """Build cross-ℓ prediction dataset: input T_{input_ell}, target eigenvalues of T_{target_ell}.

    Returns (samples, metadata).
    Each sample has: input graph + target eigenvalues (zero-padded to max_dim).
    """
    cache: dict[tuple[int, int], dict] = {}
    samples = []
    max_dim = 0

    valid_primes = []
    for entry in manifest:
        p = entry["p"]
        dim = entry["dim"]
        input_key = str(input_ell)
        target_key = str(target_ell)
        if input_key not in entry["ells"] or target_key not in entry["ells"]:
            continue
        if input_ell == p or target_ell == p:
            continue
        valid_primes.append((p, dim))

    # First pass: find max_dim for padding
    for p, dim in valid_primes:
        max_dim = max(max_dim, dim)

    # Second pass: build samples
    for p, dim in tqdm(
        valid_primes, desc=f"Building cross-ℓ dataset (ℓ={input_ell}→{target_ell})"
    ):
        input_graph = build_pyg_graph(p, input_ell, cache)
        if input_graph is None:
            continue

        target_entry = _load_hecke_npz(p, target_ell)
        if target_entry is None:
            continue

        target_eigs = target_entry["eigenvalues"].astype(np.float32)
        # Pad to max_dim
        padded_target = np.zeros(max_dim, dtype=np.float32)
        padded_target[: len(target_eigs)] = target_eigs
        # Mask: 1 for valid entries, 0 for padding
        target_mask = np.zeros(max_dim, dtype=np.float32)
        target_mask[: len(target_eigs)] = 1.0

        samples.append(
            {
                "input_graph": input_graph,
                "target_eigenvalues": padded_target,
                "target_mask": target_mask,
                "p": p,
                "dim": dim,
                "target_dim": len(target_eigs),
            }
        )

    metadata = {
        "task": "cross_ell",
        "input_ell": input_ell,
        "target_ell": target_ell,
        "n_samples": len(samples),
        "max_dim": max_dim,
        "primes": [s["p"] for s in samples],
    }

    return samples, metadata


def build_self_dataset(manifest: list[dict]) -> tuple[list[dict], dict]:
    """Build self-prediction dataset: input T_ℓ graph, target its own eigenvalues."""
    cache: dict[tuple[int, int], dict] = {}
    samples = []
    max_dim = 0

    valid_entries = []
    for entry in manifest:
        p = entry["p"]
        dim = entry["dim"]
        for ell_str, ell_data in entry["ells"].items():
            ell = int(ell_str)
            if ell == p:
                continue
            valid_entries.append((p, ell, dim))

    # Find max_dim
    for p, ell, dim in valid_entries:
        max_dim = max(max_dim, dim)

    for p, ell, dim in tqdm(valid_entries, desc="Building self-prediction dataset"):
        graph = build_pyg_graph(p, ell, cache)
        if graph is None:
            continue

        eigs = graph["eigenvalues"]
        padded_target = np.zeros(max_dim, dtype=np.float32)
        padded_target[: len(eigs)] = eigs
        target_mask = np.zeros(max_dim, dtype=np.float32)
        target_mask[: len(eigs)] = 1.0

        samples.append(
            {
                "input_graph": graph,
                "target_eigenvalues": padded_target,
                "target_mask": target_mask,
                "p": p,
                "ell": ell,
                "dim": dim,
                "target_dim": len(eigs),
            }
        )

    metadata = {
        "task": "self",
        "n_samples": len(samples),
        "max_dim": max_dim,
        "entries": [(s["p"], s["ell"]) for s in samples],
    }

    return samples, metadata


# ---------------------------------------------------------------------------
# Phase 4: Data splits
# ---------------------------------------------------------------------------


def create_prime_loo_splits(samples: list[dict], key: str = "p") -> list[dict]:
    """Create leave-one-out splits by prime.

    For each prime, one fold has all graphs with that prime as test,
    all others as train. In cross-ℓ mode, each prime has 1 sample.
    """
    primes = sorted(set(s[key] for s in samples))
    splits = []
    for test_prime in primes:
        train_idx = [i for i, s in enumerate(samples) if s[key] != test_prime]
        test_idx = [i for i, s in enumerate(samples) if s[key] == test_prime]
        splits.append(
            {
                "name": f"loo_p{test_prime}",
                "split_type": "prime_loo",
                "train_indices": train_idx,
                "test_indices": test_idx,
                "test_prime": test_prime,
            }
        )
    return splits


def create_random_prime_split(
    samples: list[dict], key: str = "p", seed: int = 42, train_ratio: float = 0.8
) -> dict:
    """Random 80/20 split by prime (no prime leakage)."""
    primes = sorted(set(s[key] for s in samples))
    rng = np.random.RandomState(seed)
    shuffled = rng.permutation(primes).tolist()
    n_train = int(len(shuffled) * train_ratio)
    train_primes = set(shuffled[:n_train])
    test_primes = set(shuffled[n_train:])

    train_idx = [i for i, s in enumerate(samples) if s[key] in train_primes]
    test_idx = [i for i, s in enumerate(samples) if s[key] in test_primes]

    return {
        "name": "random_prime_80_20",
        "split_type": "random_prime",
        "train_indices": train_idx,
        "test_indices": test_idx,
        "train_primes": sorted(train_primes),
        "test_primes": sorted(test_primes),
        "seed": seed,
    }


def create_ell_split(
    samples: list[dict],
    train_ells: list[int] | None = None,
    test_ells: list[int] | None = None,
) -> dict | None:
    """ℓ-level split: train on some ℓ values, test on others.

    Only works for self-prediction dataset (has 'ell' key).
    """
    if train_ells is None:
        train_ells = [2, 3, 5]
    if test_ells is None:
        test_ells = [7, 11, 13]

    train_ells_set = set(train_ells)
    test_ells_set = set(test_ells)

    train_idx = [i for i, s in enumerate(samples) if s.get("ell") in train_ells_set]
    test_idx = [i for i, s in enumerate(samples) if s.get("ell") in test_ells_set]

    if not train_idx or not test_idx:
        return None

    return {
        "name": "ell_split",
        "split_type": "ell_level",
        "train_indices": train_idx,
        "test_indices": test_idx,
        "train_ells": train_ells,
        "test_ells": test_ells,
    }


# ---------------------------------------------------------------------------
# Phase 5: Save PyG datasets
# ---------------------------------------------------------------------------


def convert_to_pyg_data(sample: dict) -> object:
    """Convert a sample dict to a PyG Data object."""
    import torch
    from torch_geometric.data import Data

    graph = sample["input_graph"]

    data = Data(
        edge_index=torch.from_numpy(graph["edge_index"]),
        edge_attr=torch.from_numpy(graph["edge_attr"]),
        x=torch.from_numpy(graph["x"]),
        graph_stats=torch.from_numpy(graph["graph_stats"]).unsqueeze(0),
        y=torch.from_numpy(sample["target_eigenvalues"]),
        target_mask=torch.from_numpy(sample["target_mask"]),
        p=torch.tensor(sample["p"], dtype=torch.long),
        dim=torch.tensor(sample["dim"], dtype=torch.long),
    )

    if "ell" in sample:
        data.ell = torch.tensor(sample["ell"], dtype=torch.long)

    return data


def save_pyg_dataset(
    samples: list[dict],
    metadata: dict,
    splits: list[dict] | dict,
    save_path: Path,
):
    """Save dataset as PyG .pt file with metadata and splits."""
    import torch
    from torch_geometric.data import Data

    # Convert to PyG Data objects
    data_list = []
    for sample in tqdm(samples, desc="Converting to PyG Data"):
        try:
            pyg_data = convert_to_pyg_data(sample)
            data_list.append(pyg_data)
        except Exception as e:
            logger.warning(f"Failed to convert sample p={sample.get('p')}: {e}")

    # Save
    save_dict = {
        "data_list": data_list,
        "metadata": metadata,
        "splits": splits if isinstance(splits, list) else [splits],
    }

    torch.save(save_dict, save_path)
    logger.info(f"Saved {len(data_list)} graphs to {save_path}")


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------


def print_summary(manifest: list[dict]):
    """Print summary statistics of the dataset."""
    if not manifest:
        logger.warning("No data computed!")
        return

    dims = [e["dim"] for e in manifest]
    primes = [e["p"] for e in manifest]

    deligne_ratios = []
    densities = []
    n_ell_total = 0
    for e in manifest:
        for ell_str, ell_data in e["ells"].items():
            if "deligne_ratio" in ell_data:
                deligne_ratios.append(ell_data["deligne_ratio"])
            if "density" in ell_data:
                densities.append(ell_data["density"])
            n_ell_total += 1

    logger.info("=" * 60)
    logger.info("DATASET SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Primes:          {len(manifest)}")
    logger.info(f"  (Prime, ℓ) pairs:{n_ell_total}")
    logger.info(f"  Prime range:     [{min(primes)}, {max(primes)}]")
    logger.info(f"  Dim range:       [{min(dims)}, {max(dims)}]")
    logger.info(f"  Mean dim:        {np.mean(dims):.1f}")
    logger.info(f"  Median dim:      {np.median(dims):.1f}")
    if deligne_ratios:
        logger.info(
            f"  Deligne ratios:  mean={np.mean(deligne_ratios):.4f}  "
            f"max={np.max(deligne_ratios):.4f}"
        )
        over_bound = sum(1 for r in deligne_ratios if r > 1.0)
        if over_bound:
            logger.warning(f"  ** {over_bound} graphs exceed Deligne bound (ratio > 1)")
    if densities:
        logger.info(f"  Density range:   [{min(densities):.4f}, {max(densities):.4f}]")
        logger.info(f"  Mean density:    {np.mean(densities):.4f}")

    # Timing
    timings = [e.get("timing_total_s", 0) for e in manifest]
    if timings:
        logger.info(
            f"  Time per prime:  mean={np.mean(timings):.2f}s  "
            f"max={np.max(timings):.2f}s"
        )
        logger.info(f"  Total time:      {sum(timings):.1f}s")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build Pizer graph dataset from Hecke operator matrices"
    )
    parser.add_argument(
        "--max-prime",
        type=int,
        default=1999,
        help="Maximum prime to consider (default: 1999)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute all matrices (ignore cache)",
    )
    parser.add_argument(
        "--skip-compute",
        action="store_true",
        help="Skip PARI computation, rebuild .pt from existing .npz files only",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for splits",
    )
    args = parser.parse_args()

    np.random.seed(args.seed)
    total_start = time.time()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {DATA_DIR}")

    # ---- Phase 1: Compute or load manifest ----
    manifest_path = DATA_DIR / "manifest.json"

    if args.skip_compute and manifest_path.exists():
        logger.info("Skipping computation, loading existing manifest...")
        with open(manifest_path) as f:
            manifest = json.load(f)
    elif args.force or not manifest_path.exists():
        logger.info("Phase 1: Computing Hecke matrices...")
        primes = get_candidate_primes(args.max_prime)
        logger.info(f"  Candidate primes: {len(primes)} (checking dim >= 4)")

        # Discover actual dims
        valid_primes = []
        for p in tqdm(primes, desc="Checking dims"):
            dim = get_hecke_dim(p)
            if 4 <= dim <= MAX_DIM:
                valid_primes.append(p)

        logger.info(f"  Valid primes (4 <= dim <= {MAX_DIM}): {len(valid_primes)}")

        manifest = compute_all_matrices(valid_primes, ELL_VALUES, force=args.force)

        # Save manifest
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Saved manifest: {manifest_path}")
    else:
        logger.info("Loading existing manifest...")
        with open(manifest_path) as f:
            manifest = json.load(f)

    print_summary(manifest)

    # ---- Phase 2: Build PyG datasets ----
    logger.info("\nPhase 2: Building PyG datasets...")

    # Cross-ℓ dataset: T_2 → T_3
    cross_samples, cross_meta = build_cross_ell_dataset(
        manifest, input_ell=2, target_ell=3
    )
    logger.info(
        f"  Cross-ℓ (T₂→T₃): {cross_meta['n_samples']} samples, max_dim={cross_meta['max_dim']}"
    )

    # Self-prediction dataset
    self_samples, self_meta = build_self_dataset(manifest)
    logger.info(
        f"  Self-prediction: {self_meta['n_samples']} samples, max_dim={self_meta['max_dim']}"
    )

    # ---- Phase 3: Create splits ----
    logger.info("\nPhase 3: Creating data splits...")

    # Cross-ℓ splits
    cross_loo_splits = create_prime_loo_splits(cross_samples)
    cross_random_split = create_random_prime_split(cross_samples, seed=args.seed)
    logger.info(f"  Cross-ℓ LOO-CV: {len(cross_loo_splits)} folds")
    logger.info(
        f"  Cross-ℓ random: train={len(cross_random_split['train_indices'])}, "
        f"test={len(cross_random_split['test_indices'])}"
    )

    # Self-prediction splits
    self_loo_splits = create_prime_loo_splits(self_samples)
    self_random_split = create_random_prime_split(self_samples, seed=args.seed)
    self_ell_split = create_ell_split(self_samples)
    logger.info(f"  Self LOO-CV: {len(self_loo_splits)} folds")
    logger.info(
        f"  Self random: train={len(self_random_split['train_indices'])}, "
        f"test={len(self_random_split['test_indices'])}"
    )
    if self_ell_split:
        logger.info(
            f"  Self ℓ-split: train={len(self_ell_split['train_indices'])}, "
            f"test={len(self_ell_split['test_indices'])}"
        )

    # ---- Phase 4: Save PyG datasets ----
    logger.info("\nPhase 4: Saving PyG datasets...")

    cross_splits = cross_loo_splits + [cross_random_split]
    save_pyg_dataset(
        cross_samples,
        cross_meta,
        cross_splits,
        DATA_DIR / "dataset_cross_l2_to_l3.pt",
    )

    self_splits = self_loo_splits + [self_random_split]
    if self_ell_split:
        self_splits.append(self_ell_split)
    save_pyg_dataset(
        self_samples,
        self_meta,
        self_splits,
        DATA_DIR / "dataset_self.pt",
    )

    # ---- Done ----
    elapsed = time.time() - total_start
    logger.info(f"\nDone in {elapsed:.1f}s")
    logger.info(f"Files saved to {DATA_DIR}/")
    logger.info("  manifest.json")
    logger.info("  dataset_cross_l2_to_l3.pt")
    logger.info("  dataset_self.pt")
    logger.info(
        f"  p{{prime}}_ell{{ell}}.npz  ({len(manifest)} primes × up to {len(ELL_VALUES)} ℓ)"
    )


if __name__ == "__main__":
    main()
