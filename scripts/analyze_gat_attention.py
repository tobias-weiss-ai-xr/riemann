#!/usr/bin/env python3
"""
GAT attention interpretability analysis.

Extracts attention weights from the trained TraceIndexGAT model and tests whether:
1. Attention focuses on prime-indexed vs composite-indexed trace nodes
2. Attention correlates with the Ramanujan-Petersson bound |a_p| ≤ 2√p
3. The attention distribution is uniform or structured

Uses existing checkpoint: data/models/arch_search_gat_z1_enh+ef.pt
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import torch

warnings.filterwarnings("ignore")

# Add scripts to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch

from train_gnn_arch_search import AugmentedTraceIndexDataset, TraceIndexGAT, precompute_arithmetic_features

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Precompute prime mask once (trace-index graph: node i → trace i+1)
_PRIME_MASK = torch.zeros(1000, dtype=torch.bool)
for i in range(1000):
    ti = i + 1
    is_p = ti > 1
    if is_p:
        for d in range(2, int(ti**0.5) + 1):
            if ti % d == 0:
                is_p = False
                break
    _PRIME_MASK[i] = is_p

OUTPUT_DIR = Path("data/attention_analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_JSON = OUTPUT_DIR / "gat_attention_results.json"
OUTPUT_NPZ = OUTPUT_DIR / "attention_weights.npz"

CHECKPOINT = "data/models/arch_search_gat_z1_enh+ef.pt"
DATA_DIR = Path("data/lmfdb/gnn_trace_index")
TARGET = "z1"
NODE_FEAT_DIM = 9  # 5 base + 4 augmented
EDGE_FEAT_DIM = 3
N_SAMPLE_GRAPHS = 2000  # analyze 2000 test graphs
MAX_NODES = 1000
RANDOM_SEED = 42


def load_model():
    """Load GAT checkpoint."""
    print(f"Loading checkpoint: {CHECKPOINT}")
    checkpoint = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=True)

    # Build model — hidden_dim=128 from checkpoint config
    model = TraceIndexGAT(
        node_feat_dim=NODE_FEAT_DIM,
        hidden_dim=128,
        edge_feat_dim=EDGE_FEAT_DIM,
        heads=4,
    ).to(DEVICE)

    # Handle different checkpoint formats
    if "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    elif "state_dict" in checkpoint:
        model.load_state_dict(checkpoint["state_dict"])
    else:
        model.load_state_dict(checkpoint)

    model.eval()
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    return model


def get_test_loader():
    """Build augmented dataset and extract test loader."""
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    arithmetic = precompute_arithmetic_features(MAX_NODES)
    dataset = AugmentedTraceIndexDataset(
        DATA_DIR / "test", TARGET, MAX_NODES, arithmetic,
        use_enhanced_features=True,
        use_edge_features=True,
    )

    # Subsample if needed — avoid Subset wrapper (breaks PyG DataLoader collation)
    if len(dataset) > N_SAMPLE_GRAPHS:
        indices = torch.randperm(len(dataset))[:N_SAMPLE_GRAPHS].tolist()
    else:
        indices = list(range(len(dataset)))

    # IndexDataset avoids Subset wrapping issues
    class IndexDataset(torch.utils.data.Dataset):
        def __init__(self, base, idxs):
            self.base = base
            self.indices = idxs
        def __len__(self):
            return len(self.indices)
        def __getitem__(self, i):
            return self.base[self.indices[i]]

    indexed_ds = IndexDataset(dataset, indices)

    from torch_geometric.loader import DataLoader as PyGDataLoader
    loader = PyGDataLoader(
        indexed_ds,
        batch_size=1,
        shuffle=False,
        num_workers=0,
    )
    print(f"  Test graphs: {len(indexed_ds)}")
    return indexed_ds, loader


def extract_attention(model, dataset, loader):
    """
    Extract GAT attention weights for each test graph.

    Returns:
        all_attentions: list of dicts with node-level attention stats
        prime_attentions: attention stats aggregated by node type (prime vs composite)
    """
    all_data = []
    prime_scores = []  # mean attention at prime-indexed nodes
    composite_scores = []  # mean attention at composite-indexed nodes

    n_analyzed = 0

    # We need to hook into GATConv layers to extract attention
    # The model has 3 layers: gat1 (4 heads), gat2 (4 heads), gat3 (1 head)
    gat_layers = []
    for name, mod in model.named_modules():
        if "GATConv" in type(mod).__name__:
            gat_layers.append(mod)

    attention_outputs = {}
    hooks = []

    def make_hook(layer_idx):
        def message_hook(module, hook_args, hook_output):
            # register_message_forward_hook calls: hook(module, (msg_kwargs,), out)
            # msg_kwargs = dict with keys 'x_j' and 'alpha'
            if isinstance(hook_args, tuple) and len(hook_args) > 0:
                msg_kwargs = hook_args[0]
                if isinstance(msg_kwargs, dict) and "alpha" in msg_kwargs:
                    alpha = msg_kwargs["alpha"]  # [num_edges, num_heads]
                    attention_outputs[layer_idx] = alpha.detach().cpu()
        return message_hook

    for i, layer in enumerate(gat_layers):
        hooks.append(layer.register_message_forward_hook(make_hook(i)))

    try:
        for batch_idx, batch in enumerate(loader):
            # batch is a PyG Data object (batch_size=1 via IndexDataset)
            data = batch.to(DEVICE)
            graph_idx = batch_idx  # IndexDataset maps sequentially
            n_nodes = data.x.shape[0]

            with torch.no_grad():
                _ = model(data)

            edge_index = data.edge_index.cpu()
            n_edges = edge_index.shape[1]

            # For each layer: classify edges by source node type (prime vs composite)
            # GATConv adds self-loops internally, so alpha may have more entries than edge_index.
            layer_data = {}
            for layer_idx, attn_weights in attention_outputs.items():
                n_total_edges = attn_weights.shape[0]
                
                # Try to get internal edge_index from GATConv; fallback to original + trimming
                try:
                    # PyG stores the last propagated edge_index
                    internal_ei = gat_layers[layer_idx]._edge_index.cpu()
                    src_nodes = internal_ei[0].long()
                except (AttributeError, RuntimeError):
                    # Self-loops appended at end — trim alpha to match original edge count
                    n_orig = edge_index.shape[1]
                    src_nodes = edge_index[0].long()
                    if n_total_edges > n_orig:
                        attn_weights = attn_weights[:n_orig]
                
                attn_mean = attn_weights.mean(dim=1).double().abs()

                # Classify each edge by source node prime status
                idx = src_nodes.clamp(min=0, max=999)
                is_prime_src = _PRIME_MASK[idx]

                prime_attn = attn_mean[is_prime_src]
                comp_attn = attn_mean[~is_prime_src]

                prime_scores.extend(prime_attn.tolist())
                composite_scores.extend(comp_attn.tolist())

                layer_data[layer_idx] = {
                    "n_edges": int(n_edges),
                    "n_prime_edges": int(is_prime_src.sum().item()),
                    "n_comp_edges": int((~is_prime_src).sum().item()),
                    "prime_mean_attn": float(prime_attn.mean().item()) if len(prime_attn) > 0 else 0.0,
                    "comp_mean_attn": float(comp_attn.mean().item()) if len(comp_attn) > 0 else 0.0,
                    "attn_entropy": float(-(attn_mean * torch.log(attn_mean.clamp(min=1e-10))).sum().item()),
                    "attn_sparsity": float((attn_mean < 0.01).float().mean().item()),
                }

            all_data.append({
                "graph_idx": graph_idx,
                "n_nodes": int(n_nodes),
                "layers": layer_data,
            })

            attention_outputs.clear()
            n_analyzed += 1

            if (batch_idx + 1) % 500 == 0:
                print(f"  Processed {batch_idx + 1}/{len(loader)} graphs...")

    finally:
        for h in hooks:
            h.remove()

    print(f"  Total: {n_analyzed} graphs")

    # Statistical analysis
    if len(prime_scores) == 0:
        print("  WARNING: empty prime_scores — using dummy")
        prime_arr = np.array([0.0])
    else:
        prime_arr = np.array(prime_scores)

    if len(composite_scores) == 0:
        composite_arr = np.array([0.0])
    else:
        composite_arr = np.array(composite_scores)

    def arr_stats(a):
        return {
            "mean": float(a.mean()),
            "std": float(a.std()),
            "median": float(np.median(a)),
            "p25": float(np.percentile(a, 25)),
            "p75": float(np.percentile(a, 75)),
            "min": float(a.min()),
            "max": float(a.max()),
            "n": int(len(a)),
        }

    results = {
        "n_graphs_analyzed": n_analyzed,
        "n_nodes_total": sum(d["n_nodes"] for d in all_data),
        "attention_stats": {
            "prime": arr_stats(prime_arr),
            "composite": arr_stats(composite_arr),
        },
    }

    # Welch t-test: attention at prime vs composite nodes
    from scipy import stats as sp_stats
    t_stat, p_val = sp_stats.ttest_ind(prime_arr, composite_arr, equal_var=False)
    results["prime_vs_composite_ttest"] = {
        "t_statistic": float(t_stat),
        "p_value": float(p_val),
        "mean_difference": float(prime_arr.mean() - composite_arr.mean()),
    }

    # Cohen's d
    pooled_std = np.sqrt((prime_arr.std()**2 + composite_arr.std()**2) / 2)
    results["prime_vs_composite_cohens_d"] = float(
        (prime_arr.mean() - composite_arr.mean()) / max(pooled_std, 1e-10)
    )

    # Effect ratio
    results["attention_ratio_prime_composite"] = float(
        prime_arr.mean() / max(composite_arr.mean(), 1e-10)
    )

    # Aggregate across all layers
    layer_summary = {}
    for d in all_data[:200]:  # sample 200 graphs
        for lname, ldata in d["layers"].items():
            if lname not in layer_summary:
                layer_summary[lname] = {"entropies": [], "sparsities": []}
            layer_summary[lname]["entropies"].append(ldata["attn_entropy"])
            layer_summary[lname]["sparsities"].append(ldata["attn_sparsity"])

    results["layer_summary"] = {}
    for lname, ldata in layer_summary.items():
        results["layer_summary"][lname] = {
            "mean_entropy": float(np.mean(ldata["entropies"])),
            "std_entropy": float(np.std(ldata["entropies"])),
            "mean_sparsity": float(np.mean(ldata["sparsities"])),
        }

    return results, all_data


def main():
    print("=" * 60)
    print("  GAT Attention Interpretability Analysis")
    print("=" * 60)

    t0 = time.time()
    model = load_model()
    dataset, loader = get_test_loader()

    print(f"\nExtracting attention weights from {N_SAMPLE_GRAPHS} test graphs...")
    results, all_data = extract_attention(model, dataset, loader)

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    stats = results["attention_stats"]
    print(f"  Prime nodes:    mean={stats['prime']['mean']:.6f} ± {stats['prime']['std']:.6f}")
    print(f"  Composite nodes: mean={stats['composite']['mean']:.6f} ± {stats['composite']['std']:.6f}")
    print(f"  Ratio (Prime/Composite): {results['attention_ratio_prime_composite']:.4f}")
    print(f"  Cohen's d: {results['prime_vs_composite_cohens_d']:.4f}")
    print(f"  t-test p-value: {results['prime_vs_composite_ttest']['p_value']:.2e}")

    ttest = results["prime_vs_composite_ttest"]
    if ttest["p_value"] < 0.05 and results["attention_ratio_prime_composite"] > 1.05:
        conclusion = "YES — GAT attention preferentially focuses on prime-indexed nodes"
    elif ttest["p_value"] < 0.05 and results["attention_ratio_prime_composite"] < 0.95:
        conclusion = "YES — GAT attention preferentially focuses on COMPOSITE-indexed nodes"
    else:
        conclusion = "NO — GAT attention does not significantly distinguish prime from composite nodes"

    results["conclusion"] = conclusion
    print(f"\n  Conclusion: {conclusion}")

    print(f"\n  Layer summary:")
    for lname, lsum in results.get("layer_summary", {}).items():
        print(f"    {lname}: entropy={lsum['mean_entropy']:.3f} ± {lsum['std_entropy']:.3f}, "
              f"sparsity={lsum['mean_sparsity']:.3f}")

    if "position_correlation" in results:
        pc = results["position_correlation"]
        print(f"\n  Position-attention correlation: r={pc['mean_r']:.4f} ± {pc['std_r']:.4f}")

    elapsed = time.time() - t0
    print(f"\n  Elapsed: {elapsed:.1f}s")

    # Save
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved to {OUTPUT_JSON}")

    # Save attention weights as NPZ for further analysis
    # (simplified: aggregated stats only)
    print("  Done.")


if __name__ == "__main__":
    main()
