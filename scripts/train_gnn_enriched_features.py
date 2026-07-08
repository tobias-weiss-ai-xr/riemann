"""
Thread G: Hybrid GNN with enriched number-theoretic features.

Three ablation configurations on z1 (first L-function zero) regression:
  (a) baseline: 9-dim node features (5 base + 4 arithmetic), NO global features
  (b) enriched_nodes: 17-dim node features (9 + 8 new NT features), NO global features
  (c) enriched_nodes + global: 17-dim node features + 8-dim form-level global features

New index-level features: sigma_1(n), sigma_2(n), phi(n), Lambda(n),
    Ramanujan sums c_q(n) for q in {2,3,5,7}.
New global features: log(conductor), dim, root_number, log(num_zeros),
    Sato-Tate moments (mean a_p^2, skew a_p^3, kurtosis a_p^4), spectral_ratio.

Usage:
    python scripts/train_gnn_enriched_features.py
    python scripts/train_gnn_enriched_features.py --config baseline
    python scripts/train_gnn_enriched_features.py --epochs 200
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import warnings

warnings.filterwarnings("ignore", message=".*torch-scatter.*")

from loguru import logger
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from torch import nn
from torch.utils.data import Dataset
from torch_geometric.loader import DataLoader as PyGDataLoader
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_mean_pool, global_max_pool

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent.parent / "data"
LMFDB_DIR = DATA_DIR / "lmfdb"
RESULTS_DIR = DATA_DIR / "results"
MODEL_DIR = DATA_DIR / "models"

# ---------------------------------------------------------------------------
# Configure loguru
# ---------------------------------------------------------------------------

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)

# ---------------------------------------------------------------------------
# Number-theoretic feature computation (precomputed for n=1..N)
# ---------------------------------------------------------------------------


def sieve_smallest_prime_factor(limit: int) -> np.ndarray:
    """Sieve for smallest prime factor of each n in [1..limit]. spf[1] = 1."""
    spf = np.ones(limit + 1, dtype=np.int64)
    for i in range(2, limit + 1):
        if spf[i] == 1:
            spf[i] = i
            if i * i <= limit:
                for j in range(i * i, limit + 1, i):
                    if spf[j] == 1:
                        spf[j] = i
    return spf


def precompute_arithmetic_features(N: int) -> dict[str, np.ndarray]:
    """Precompute omega, mu, d, liouville for n=1..N.

    Returns dict with keys 'omega', 'mu', 'd', 'liouville', each (N+1,)
    array indexed by n (index 0 is unused/padding).
    """
    omega = np.zeros(N + 1, dtype=np.int32)
    mu = np.ones(N + 1, dtype=np.int32)
    d = np.ones(N + 1, dtype=np.int32)
    smallest_prime_factor = np.zeros(N + 1, dtype=np.int32)
    prime_count = np.zeros(N + 1, dtype=np.int32)

    for i in range(2, N + 1):
        if smallest_prime_factor[i] == 0:
            smallest_prime_factor[i] = i
            for j in range(i * i, N + 1, i):
                if smallest_prime_factor[j] == 0:
                    smallest_prime_factor[j] = i

    for i in range(2, N + 1):
        p = smallest_prime_factor[i]
        j = i // p
        if j % p == 0:
            mu[i] = 0
            omega[i] = omega[j]
            prime_count[i] = prime_count[j] + 1
        else:
            mu[i] = -mu[j]
            omega[i] = omega[j] + 1
            prime_count[i] = prime_count[j] + 1

    d[1] = 1
    for i in range(2, N + 1):
        p = smallest_prime_factor[i]
        j = i // p
        exp = 1
        while j % p == 0:
            j //= p
            exp += 1
        d[i] = d[j] * (exp + 1)

    liouville = np.where(prime_count % 2 == 0, 1, -1)

    return {
        "omega": omega.astype(np.float32),
        "mu": mu.astype(np.float32),
        "d": d.astype(np.float32),
        "liouville": liouville.astype(np.float32),
    }


def precompute_enriched_features(N: int) -> dict[str, np.ndarray]:
    """Precompute enriched number-theoretic features for n=1..N.

    Features (8 total):
      sigma_1(n): sum of divisors
      sigma_2(n): sum of squares of divisors
      phi(n): Euler's totient
      von_mangoldt(n): log(p) if n = p^k, else 0
      ramanujan_2(n), ramanujan_3(n), ramanujan_5(n), ramanujan_7(n):
        Ramanujan sums c_q(n) for q in {2, 3, 5, 7}

    Returns dict with (N+1,) arrays indexed by n.
    """
    spf = sieve_smallest_prime_factor(N)

    # Sigma_1(n) = sum of divisors
    sigma_1 = np.ones(N + 1, dtype=np.float32)
    # Sigma_2(n) = sum of squares of divisors
    sigma_2 = np.ones(N + 1, dtype=np.float32)
    # Euler's totient phi(n)
    phi = np.arange(N + 1, dtype=np.float32)  # phi(n) = n initially
    phi[0] = 0

    for i in range(2, N + 1):
        p = spf[i]
        j = i // p
        if j % p == 0:
            # p^2 | i: phi(i) = phi(j) * p, sigma(i) = sigma(i/p^exp) * (p^{exp+1}-1)/(p-1)
            exp = 1
            jj = j
            while jj % p == 0:
                jj //= p
                exp += 1
            p_power_sum = (p ** (exp + 1) - 1) // (p - 1)
            p_sq_power_sum = (p ** (2 * (exp + 1)) - 1) // (p ** 2 - 1) if p > 1 else 1
            sigma_1[i] = sigma_1[jj] * p_power_sum
            sigma_2[i] = sigma_2[jj] * p_sq_power_sum
            phi[i] = phi[jj] * (p ** exp - p ** (exp - 1))
        else:
            sigma_1[i] = sigma_1[j] * (1 + p)
            sigma_2[i] = sigma_2[j] * (1 + p * p)
            phi[i] = phi[j] * (p - 1)

    # Von Mangoldt function: Lambda(n) = log(p) if n = p^k, else 0
    von_mangoldt = np.zeros(N + 1, dtype=np.float32)
    for i in range(2, N + 1):
        p = spf[i]
        j = i // p
        if j % p == 0:
            # p^2 | i, but still Lambda(p^k) = log(p) for any k >= 1
            pass  # keep 0, will set below
        von_mangoldt[i] = np.log(p)

    # Wait: Lambda(n) = log(p) if n = p^k for some k >= 1, else 0
    # So for any n, if n is a prime power p^k, Lambda(n) = log(p)
    # Actually the above loop already sets it correctly since spf gives the smallest prime factor.
    # But we need to be careful: n = 12 = 2^2 * 3 is NOT a prime power, so Lambda(12) = 0.
    # The code above sets Lambda(12) = log(2) which is WRONG.
    # Fix: check if n is a prime power.

    # Reset and compute correctly
    von_mangoldt = np.zeros(N + 1, dtype=np.float32)
    for i in range(2, N + 1):
        p = spf[i]
        j = i
        while j % p == 0:
            j //= p
        if j == 1:  # n = p^k for some k
            von_mangoldt[i] = np.log(p)

    # Ramanujan sums: c_q(n) = sum_{1 <= a <= q, gcd(a,q)=1} exp(2*pi*i*a*n/q)
    # Equivalently: c_q(n) = sum_{d | gcd(n,q)} d * mu(q/d)
    def ramanujan_sum(q: int, n_values: np.ndarray) -> np.ndarray:
        """Compute c_q(n) for all n in n_values (0-indexed, n_values[0] = c_q(1))."""
        result = np.zeros(len(n_values), dtype=np.float32)
        for n_idx, n in enumerate(n_values):
            if n == 0:
                continue
            g = int(np.gcd(int(n), q))
            # Sum over divisors d of g
            c = 0
            # Get divisors of g
            d = 1
            temp = g
            divisors = []
            while d * d <= temp:
                if temp % d == 0:
                    divisors.append(d)
                    if d != temp // d:
                        divisors.append(temp // d)
                d += 1
            for dd in divisors:
                c += dd * int(np.sign(mu_val[q // dd] if q % dd == 0 else 0))
            # Actually use the precomputed mu
            c = 0
            for dd in divisors:
                if q % dd == 0:
                    c += dd * mu_dict.get(q // dd, 0)
            result[n_idx] = c
        return result

    # Build mu dict for Ramanujan sums
    mu_arr = precompute_arithmetic_features(max(7, N))["mu"]  # just need small values
    mu_dict = {i: int(mu_arr[i]) for i in range(max(7, N) + 1)}

    def ramanujan_sum_fast(q: int, N_max: int) -> np.ndarray:
        """Compute c_q(n) for n=0..N_max."""
        result = np.zeros(N_max + 1, dtype=np.float32)
        for n in range(1, N_max + 1):
            g = np.gcd(n, q)
            if g == 0:
                continue
            c = 0
            d = 1
            temp = g
            while d * d <= temp:
                if temp % d == 0:
                    if q % d == 0:
                        c += d * mu_dict.get(q // d, 0)
                    dd = temp // d
                    if dd != d and q % dd == 0:
                        c += dd * mu_dict.get(q // dd, 0)
                d += 1
            result[n] = c
        return result

    ram_sums = {}
    for q in [2, 3, 5, 7]:
        ram_sums[f"ram_{q}"] = ramanujan_sum_fast(q, N)

    return {
        "sigma_1": sigma_1,
        "sigma_2": sigma_2,
        "phi": phi,
        "von_mangoldt": von_mangoldt,
        **ram_sums,
    }


# ---------------------------------------------------------------------------
# Edge feature construction
# ---------------------------------------------------------------------------


def build_edge_features(
    edge_index: torch.Tensor,
    N: int,
) -> torch.Tensor:
    """Build 3-dim edge features from node indices."""
    src, dst = edge_index[0], edge_index[1]
    n_src = src + 1
    n_dst = dst + 1

    dist = (n_src - n_dst).abs().float() / N
    sequential = (dist * N <= 1.0 + 1e-6).float()
    divides = (n_src % n_dst == 0) | (n_dst % n_src == 0)
    prime_related = divides.float()

    edge_attr = torch.stack([dist, sequential, prime_related], dim=1)
    return edge_attr


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class EnrichedTraceIndexDataset(Dataset):
    """Trace-index graph dataset with enriched node features and global features.

    Loads compact numpy arrays, appends arithmetic/enriched features on the fly,
    and attaches form-level global features.
    """

    def __init__(
        self,
        split_dir: Path,
        trace_indices: np.ndarray,
        csv_indices: np.ndarray,
        csv_df: pd.DataFrame,
        traces_matrix: np.ndarray,
        num_nodes: int = 1000,
        config: str = "baseline",
        arithmetic: dict[str, np.ndarray] | None = None,
        enriched: dict[str, np.ndarray] | None = None,
        use_edge_features: bool = True,
    ):
        self.num_nodes = num_nodes
        self.config = config
        self.trace_indices = trace_indices  # row indices into traces_matrix
        self.csv_indices = csv_indices  # row indices into csv_df
        self.csv_df = csv_df
        self.traces_matrix = traces_matrix
        self.use_edge_features = use_edge_features

        # Load compact arrays
        self.x = np.load(split_dir / "x.npy", mmap_mode="r")
        self.edge_index = np.load(split_dir / "edge_index.npy", mmap_mode="r")
        self.edge_ptr = np.load(split_dir / "edge_ptr.npy", mmap_mode="r")
        self.n_graphs = len(self.edge_ptr) - 1

        # Load z1 targets directly from y_z1.npy
        self.y = np.load(split_dir / "y_z1.npy", mmap_mode="r").astype(np.float32)
        assert len(self.y) == self.n_graphs, (
            f"y_z1 length {len(self.y)} != n_graphs {self.n_graphs}"
        )

        # Precompute static node feature tensors
        self._build_node_features(arithmetic, enriched)

        # Precompute global features per form (only for config 'global')
        if config == "global":
            self._build_global_features()
        else:
            self.global_features = None

        logger.info(
            f"  {split_dir.name}: {self.n_graphs} graphs"
        )

    def _build_node_features(
        self,
        arithmetic: dict[str, np.ndarray] | None,
        enriched: dict[str, np.ndarray] | None,
    ):
        """Build static node feature tensor (shared across all graphs)."""
        N = self.num_nodes

        if self.config == "baseline":
            # 9-dim: 5 base + 4 arithmetic
            a = arithmetic
            arith = np.stack(
                [
                    a["omega"][1 : N + 1] / np.log(np.arange(2, N + 2, dtype=np.float32)),
                    a["mu"][1 : N + 1].astype(np.float32),
                    np.log(a["d"][1 : N + 1] + 1)
                    / np.log(np.arange(2, N + 2, dtype=np.float32)),
                    a["liouville"][1 : N + 1].astype(np.float32),
                ],
                axis=1,
            )
            mean = arith.mean(axis=0, keepdims=True)
            std = arith.std(axis=0, keepdims=True) + 1e-8
            arith = (arith - mean) / std
            self.static_node_feat = torch.from_numpy(arith)  # (N, 4)
            self.static_feat_dim = 4

        elif self.config in ("enriched", "global"):
            # 4 arithmetic + 8 enriched = 12 new features
            a = arithmetic
            e = enriched
            arith = np.stack(
                [
                    a["omega"][1 : N + 1] / np.log(np.arange(2, N + 2, dtype=np.float32)),
                    a["mu"][1 : N + 1].astype(np.float32),
                    np.log(a["d"][1 : N + 1] + 1)
                    / np.log(np.arange(2, N + 2, dtype=np.float32)),
                    a["liouville"][1 : N + 1].astype(np.float32),
                ],
                axis=1,
            )
            # 8 enriched features
            enrich = np.stack(
                [
                    np.log(e["sigma_1"][1 : N + 1] + 1) / np.log(N),
                    np.log(e["sigma_2"][1 : N + 1] + 1) / (2 * np.log(N)),
                    e["phi"][1 : N + 1] / np.arange(1, N + 1, dtype=np.float32),
                    e["von_mangoldt"][1 : N + 1],
                    e["ram_2"][1 : N + 1],
                    e["ram_3"][1 : N + 1],
                    e["ram_5"][1 : N + 1],
                    e["ram_7"][1 : N + 1],
                ],
                axis=1,
            )
            # Concatenate and normalize
            combined = np.concatenate([arith, enrich], axis=1).astype(np.float32)
            mean = combined.mean(axis=0, keepdims=True)
            std = combined.std(axis=0, keepdims=True) + 1e-8
            combined = (combined - mean) / std
            self.static_node_feat = torch.from_numpy(combined)  # (N, 12)
            self.static_feat_dim = 12
        else:
            self.static_node_feat = None
            self.static_feat_dim = 0

    def _build_global_features(self):
        """Build form-level global features for config 'global'.

        8-dim: log(conductor), dim, root_number, log(num_zeros),
               mean(a_p^2), skew(a_p^3), kurtosis(a_p^4), spectral_ratio.
        """
        N_graphs = self.n_graphs
        global_feats = np.zeros((N_graphs, 8), dtype=np.float32)

        for i in range(N_graphs):
            trace_row = self.trace_indices[i]
            csv_row = self.csv_indices[i]
            row = self.csv_df.iloc[csv_row]

            # Form-level features from CSV
            level = float(row.get("level", 1))
            dim = float(row.get("dim", 1))
            root_number = float(row.get("root_number", 1.0))
            num_zeros = float(row.get("num_zeros", 10))

            # Sato-Tate moments from traces (first 100 Hecke eigenvalues)
            traces = self.traces_matrix[trace_row][:100]
            ap2_mean = float(np.mean(traces ** 2))
            t_std = traces.std() + 1e-8
            ap3_skew = float(np.mean(((traces - traces.mean()) / t_std) ** 3))
            ap4_kurt = float(np.mean(((traces - traces.mean()) / t_std) ** 4))

            spectral_ratio = num_zeros / np.log(max(level, 1))

            global_feats[i] = [
                np.log(level + 1),
                dim / 8.0,
                root_number,
                np.log(num_zeros + 1),
                ap2_mean / 2.0,  # normalize: Sato-Tate predicts mean a_p^2 ≈ 2
                ap3_skew / 2.0,
                ap4_kurt / 9.0,
                spectral_ratio / 2.0,
            ]

        # Normalize
        mean = global_feats.mean(axis=0, keepdims=True)
        std = global_feats.std(axis=0, keepdims=True) + 1e-8
        global_feats = (global_feats - mean) / std
        self.global_features = torch.from_numpy(global_feats)  # (N_graphs, 8)
        logger.info(f"  Global features: shape={global_feats.shape}")

    def __len__(self):
        return self.n_graphs

    def __getitem__(self, idx: int) -> Data:
        node_start = idx * self.num_nodes
        node_end = node_start + self.num_nodes

        x = torch.from_numpy(np.array(self.x[node_start:node_end]))  # (N, 5)

        if self.static_node_feat is not None:
            x = torch.cat([x, self.static_node_feat], dim=1)  # (N, 5+static_dim)

        edge_start = int(self.edge_ptr[idx])
        edge_end = int(self.edge_ptr[idx + 1])
        edge_index = torch.from_numpy(
            self.edge_index[:, edge_start:edge_end].astype(np.int64)
        )

        data = Data(
            x=x,
            edge_index=edge_index,
            y=torch.tensor([self.y[idx]], dtype=torch.float32),
        )

        if self.use_edge_features:
            data.edge_attr = build_edge_features(edge_index, self.num_nodes)

        # Attach global features if available
        if self.global_features is not None:
            data.global_feat = self.global_features[idx].unsqueeze(0)  # (1, 8)

        return data


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class EnrichedGAT(nn.Module):
    """GAT with optional global feature fusion at readout."""

    def __init__(
        self,
        node_feat_dim: int,
        global_feat_dim: int = 0,
        hidden_dim: int = 128,
        num_layers: int = 3,
        edge_feat_dim: int = 3,
        heads: int = 4,
    ):
        super().__init__()
        self.heads = heads
        self.global_feat_dim = global_feat_dim

        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()

        for i in range(num_layers):
            in_dim = node_feat_dim if i == 0 else hidden_dim
            out_dim = hidden_dim // heads
            if i < num_layers - 1:
                conv = GATConv(
                    in_dim, out_dim, heads=heads,
                    edge_dim=edge_feat_dim,
                    concat=True,
                )
                norm_in = hidden_dim
            else:
                conv = GATConv(
                    hidden_dim, hidden_dim // 2, heads=1,
                    edge_dim=edge_feat_dim,
                    concat=False,
                )
                norm_in = hidden_dim // 2

            self.convs.append(conv)
            self.norms.append(nn.BatchNorm1d(norm_in))

        # Readout: concat(mean, max) → hidden_dim*2 for last layer
        # Then optionally concat with global features
        readout_dim = norm_in * 2 + global_feat_dim

        self.head = nn.Sequential(
            nn.Linear(readout_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )
        self._norm_in = norm_in

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        edge_attr = data.edge_attr if hasattr(data, "edge_attr") else None

        for i, (conv, norm) in enumerate(zip(self.convs, self.norms)):
            if edge_attr is not None and hasattr(conv, "edge_dim") and conv.edge_dim is not None:
                x = conv(x, edge_index, edge_attr=edge_attr)
            else:
                x = conv(x, edge_index)
            x = norm(x).relu()
            x = F.dropout(x, p=0.1, training=self.training)

        readout = torch.cat(
            [global_mean_pool(x, batch), global_max_pool(x, batch)], dim=1
        )

        # Concat global features if present
        if self.global_feat_dim > 0 and hasattr(data, "global_feat") and data.global_feat is not None:
            # Expand global features to match batch size
            B = readout.shape[0]
            global_expanded = data.global_feat.expand(B, -1)
            readout = torch.cat([readout, global_expanded], dim=1)

        return self.head(readout)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_epoch(model, loader, optimizer, device):
    model.train()
    total_loss = 0.0
    total_samples = 0

    for batch in loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        out = model(batch)
        loss = F.mse_loss(out.squeeze(), batch.y.squeeze())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item() * batch.num_graphs
        total_samples += batch.num_graphs

    return total_loss / total_samples


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    total_loss = 0.0
    total_samples = 0
    all_preds = []
    all_targets = []

    for batch in loader:
        batch = batch.to(device)
        out = model(batch)
        loss = F.mse_loss(out.squeeze(), batch.y.squeeze())
        preds = out.squeeze().cpu().numpy()

        total_loss += loss.item() * batch.num_graphs
        total_samples += batch.num_graphs
        all_preds.extend(preds.flatten())
        all_targets.extend(batch.y.squeeze().cpu().numpy().flatten())

    avg_loss = total_loss / total_samples
    return avg_loss, np.array(all_preds), np.array(all_targets)


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------


def run_single_config(
    config_name: str,
    data_dir: Path,
    split_trace_indices: dict[str, np.ndarray],
    split_csv_indices: dict[str, np.ndarray],
    csv_df: pd.DataFrame,
    traces_matrix: np.ndarray,
    arithmetic: dict[str, np.ndarray],
    enriched: dict[str, np.ndarray],
    args,
) -> dict:
    """Run one ablation configuration."""
    logger.info(f"{'='*60}")
    logger.info(f"Config: {config_name}")
    logger.info(f"{'='*60}")

    config_map = {
        "baseline": "baseline",
        "enriched": "enriched",
        "global": "global",
    }
    config = config_map[config_name]

    # Build datasets
    logger.info("Loading datasets...")
    train_ds = EnrichedTraceIndexDataset(
        data_dir / "train", split_trace_indices["train"], split_csv_indices["train"],
        csv_df, traces_matrix,
        num_nodes=1000, config=config, arithmetic=arithmetic, enriched=enriched,
        use_edge_features=not args.no_edge_features,
    )
    val_ds = EnrichedTraceIndexDataset(
        data_dir / "val", split_trace_indices["val"], split_csv_indices["val"],
        csv_df, traces_matrix,
        num_nodes=1000, config=config, arithmetic=arithmetic, enriched=enriched,
        use_edge_features=not args.no_edge_features,
    )
    test_ds = EnrichedTraceIndexDataset(
        data_dir / "test", split_trace_indices["test"], split_csv_indices["test"],
        csv_df, traces_matrix,
        num_nodes=1000, config=config, arithmetic=arithmetic, enriched=enriched,
        use_edge_features=not args.no_edge_features,
    )

    # Get feature dimensions
    sample = train_ds[0]
    node_feat_dim = sample.x.shape[1]
    global_feat_dim = 8 if config == "global" else 0
    logger.info(f"  node_feat_dim={node_feat_dim}, global_feat_dim={global_feat_dim}")

    # Data loaders
    train_loader = PyGDataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = PyGDataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = PyGDataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"  Device: {device}")

    # Build model
    model = EnrichedGAT(
        node_feat_dim=node_feat_dim,
        global_feat_dim=global_feat_dim,
        hidden_dim=args.hidden,
        num_layers=args.layers,
        edge_feat_dim=3 if not args.no_edge_features else 0,
        heads=args.heads,
    ).to(device)

    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"  Parameters: {param_count:,}")

    # Optimizer + scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.lr, weight_decay=1e-4
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs
    )

    # Training loop
    best_val_loss = float("inf")
    best_state = None
    best_epoch = 0
    epochs_no_improve = 0

    logger.info(f"  Training: {args.epochs} epochs, patience={args.patience}")
    t0 = time.time()

    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, device)
        val_loss, val_preds, val_targets = evaluate(model, val_loader, device)
        scheduler.step()

        val_r2 = r2_score(val_targets, val_preds)

        if epoch % 10 == 0 or epoch == 1:
            logger.info(
                f"    Epoch {epoch:3d}/{args.epochs} | "
                f"Train: {train_loss:.4f} | Val: {val_loss:.4f} | R²: {val_r2:.4f}"
            )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if epochs_no_improve >= args.patience:
            logger.info(f"    Early stopping at epoch {epoch} (patience={args.patience})")
            break

    elapsed = time.time() - t0
    logger.info(
        f"    Best: epoch {best_epoch}, val_loss={best_val_loss:.4f}, time={elapsed:.1f}s"
    )

    # Test evaluation
    model.load_state_dict(best_state)
    model = model.to(device)
    test_loss, test_preds, test_targets = evaluate(model, test_loader, device)

    test_mse = mean_squared_error(test_targets, test_preds)
    test_mae = mean_absolute_error(test_targets, test_preds)
    test_r2 = r2_score(test_targets, test_preds)

    logger.info(f"    Test MSE: {test_mse:.6f} | MAE: {test_mae:.6f} | R²: {test_r2:.4f}")

    # Save checkpoint
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = MODEL_DIR / f"thread_g_{config_name}.pt"
    torch.save({
        "model_state_dict": best_state,
        "config_name": config_name,
        "node_feat_dim": node_feat_dim,
        "global_feat_dim": global_feat_dim,
        "hidden_dim": args.hidden,
        "num_layers": args.layers,
        "heads": args.heads,
        "best_epoch": best_epoch,
        "test_r2": test_r2,
    }, ckpt_path)
    logger.info(f"    Saved: {ckpt_path}")

    return {
        "config": config_name,
        "node_feat_dim": node_feat_dim,
        "global_feat_dim": global_feat_dim,
        "param_count": param_count,
        "best_epoch": best_epoch,
        "val_loss": float(best_val_loss),
        "test_mse": float(test_mse),
        "test_mae": float(test_mae),
        "test_r2": float(test_r2),
        "training_time": elapsed,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Thread G: Hybrid GNN with enriched number-theoretic features"
    )
    parser.add_argument(
        "--config",
        choices=["all", "baseline", "enriched", "global"],
        default="all",
        help="Which config(s) to run (default: all three)",
    )
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--no-edge-features", action="store_true")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    t_total = time.time()

    data_dir = Path(args.data_dir) if args.data_dir else LMFDB_DIR / "gnn_trace_index_cross_level"
    results_dir = Path(args.output_dir) if args.output_dir else RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load CSV for global features
    logger.info("Loading CSV labels...")
    csv_path = LMFDB_DIR / "lmfdb_zeros_ml.csv"
    csv_df = pd.read_csv(csv_path)

    # Load traces matrix for Sato-Tate moments
    logger.info("Loading traces matrix (mmap)...")
    traces_matrix = np.load(LMFDB_DIR / "lmfdb_sql_traces_matrix.npy", mmap_mode="r")
    logger.info(f"  traces_matrix: {traces_matrix.shape}")

    # Build CSV index mapping: traces_matrix row -> CSV row
    # The GNN dataset was built from the join of traces_matrix labels, weight2_ml, zeros_ml.
    # We need to reconstruct which CSV row each GNN graph corresponds to.
    # traces_matrix has 46347 rows matching the join. The GNN dataset uses the same order.
    # CSV has 63844 rows (wider). We need to match via labels.json -> CSV label.
    labels_path = LMFDB_DIR / "lmfdb_sql_labels.json"
    with open(labels_path) as f:
        traces_labels = json.load(f)
    logger.info(f"  labels.json: {len(traces_labels)} entries")

    # Build traces_matrix_index -> CSV row index mapping
    # traces_labels[i] = label string for traces_matrix row i
    # CSV has duplicate labels (e.g. same label for different char_orders)
    # Dedup CSV: keep first occurrence per label
    csv_label_to_row = {}
    for i, label in enumerate(csv_df["label"].values):
        if label not in csv_label_to_row:
            csv_label_to_row[label] = i

    csv_indices = []  # maps traces_matrix row -> CSV row
    missing = 0
    for label in traces_labels:
        if label in csv_label_to_row:
            csv_indices.append(csv_label_to_row[label])
        else:
            csv_indices.append(-1)  # not found in CSV
            missing += 1
    csv_indices = np.array(csv_indices, dtype=np.int64)
    logger.info(f"  CSV mapping: {len(csv_indices)} traces -> CSV, {missing} not found")

    # Build per-split CSV index arrays (matching GNN dataset ordering)
    # The GNN dataset was built with cross_level_split on the meta_df from load_and_join_data.
    # We need to replicate that mapping.
    # Alternative: load y_z1.npy already contains the correct targets.
    # For global features, we use csv_indices[i] for form i in the traces_matrix.

    # Load weight2_ml to reconstruct the join ordering
    weight2_path = LMFDB_DIR / "lmfdb_sql_weight2_ml.csv"
    df_ml = pd.read_csv(weight2_path, usecols=["label", "analytic_rank", "is_cm", "dim", "level"])
    logger.info(f"  weight2_ml: {len(df_ml)} rows")

    # Build join: traces_labels ∩ weight2_ml ∩ zeros_ml
    labels_df = pd.DataFrame({"label": traces_labels, "matrix_idx": np.arange(len(traces_labels))})
    meta_df = labels_df.merge(df_ml, on="label", how="inner")
    # Also need z1 from zeros_ml for the join filter
    df_z = pd.read_csv(LMFDB_DIR / "lmfdb_zeros_ml.csv", usecols=["label", "z1"])
    df_z = df_z.drop_duplicates(subset="label", keep="first")
    meta_df = meta_df.merge(df_z, on="label", how="inner")
    meta_df = meta_df.sort_values("matrix_idx").reset_index(drop=True)
    logger.info(f"  Join result: {len(meta_df)} forms")

    # Now split into train/val/test using cross_level_split
    levels = meta_df["level"].values
    ranks = meta_df["analytic_rank"].values

    def cross_level_split(levels, ranks, max_train=3000, max_val=4000, seed=42):
        rng = np.random.RandomState(seed)
        train_mask = levels <= max_train
        val_mask = (levels > max_train) & (levels <= max_val)
        test_mask = levels > max_val
        def stratify(pool, ranks):
            idx_list = []
            for rv in sorted(np.unique(ranks[pool])):
                class_idx = pool[ranks[pool] == rv]
                rng.shuffle(class_idx)
                idx_list.extend(class_idx.tolist())
            return np.array(idx_list)
        return stratify(np.where(train_mask)[0], ranks), stratify(np.where(val_mask)[0], ranks), stratify(np.where(test_mask)[0], ranks)

    train_idx, val_idx, test_idx = cross_level_split(levels, ranks)
    logger.info(f"  Split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

    # Build per-split indices arrays
    train_trace_idx = np.array([meta_df.iloc[i]["matrix_idx"] for i in train_idx], dtype=np.int64)
    val_trace_idx = np.array([meta_df.iloc[i]["matrix_idx"] for i in val_idx], dtype=np.int64)
    test_trace_idx = np.array([meta_df.iloc[i]["matrix_idx"] for i in test_idx], dtype=np.int64)
    train_csv_idx = np.array([csv_indices[t] for t in train_trace_idx], dtype=np.int64)
    val_csv_idx = np.array([csv_indices[t] for t in val_trace_idx], dtype=np.int64)
    test_csv_idx = np.array([csv_indices[t] for t in test_trace_idx], dtype=np.int64)
    split_trace_indices = {"train": train_trace_idx, "val": val_trace_idx, "test": test_trace_idx}
    split_csv_indices = {"train": train_csv_idx, "val": val_csv_idx, "test": test_csv_idx}

    # Precompute arithmetic features (for baseline)
    logger.info("Precomputing arithmetic features...")
    arithmetic = precompute_arithmetic_features(1000)

    # Precompute enriched features (for enriched + global configs)
    logger.info("Precomputing enriched number-theoretic features...")
    enriched = precompute_enriched_features(1000)
    logger.info(f"  Enriched features: {list(enriched.keys())}")

    # Determine which configs to run
    configs_to_run = []
    if args.config == "all":
        configs_to_run = ["baseline", "enriched", "global"]
    else:
        configs_to_run = [args.config]

    # Run experiments
    all_results = []
    for cfg in configs_to_run:
        result = run_single_config(
            cfg, data_dir, split_trace_indices, split_csv_indices, csv_df, traces_matrix,
            arithmetic, enriched, args,
        )
        all_results.append(result)

    # Print comparison table
    print()
    print("=" * 78)
    print("  Thread G: Feature Ablation Results (z1 Regression)")
    print("=" * 78)
    print(f"  {'Config':<12s} | {'Node Dim':>8s} | {'Global':>6s} | {'Params':>8s} | {'R²':>8s} | {'MAE':>8s} | {'Epoch':>5s} | {'Time':>7s}")
    print(f"  {'-'*12} | {'-'*8} | {'-'*6} | {'-'*8} | {'-'*8} | {'-'*8} | {'-'*5} | {'-'*7}")
    for r in all_results:
        print(
            f"  {r['config']:<12s} | "
            f"{r['node_feat_dim']:>8d} | "
            f"{str(r['global_feat_dim']):>6s} | "
            f"{r['param_count']:>8d} | "
            f"{r['test_r2']:>8.4f} | "
            f"{r['test_mae']:>8.6f} | "
            f"{r['best_epoch']:>5d} | "
            f"{r['training_time']:>6.1f}s"
        )

    # Save results JSON
    results_path = results_dir / "thread_g_enriched_features_results.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Results saved to {results_path}")

    elapsed_total = time.time() - t_total
    logger.info(f"Total time: {elapsed_total:.1f}s")


if __name__ == "__main__":
    main()
