"""Inspect Pizer dataset PyG Data objects."""

import torch
from pathlib import Path

data_dir = Path("/workspace/data/pizer")

ds = torch.load(data_dir / "dataset_cross_l2_to_l3.pt", weights_only=False)
data_list = ds["data_list"]
meta = ds["metadata"]
splits = ds["splits"]

print(f"Dataset: {len(data_list)} graphs")
print(f"Metadata: {meta}")

g = data_list[0]
print(f"\nFirst graph attributes:")
for k in sorted(g.keys()):
    v = getattr(g, k)
    if isinstance(v, torch.Tensor):
        print(
            f"  {k}: shape={v.shape}, dtype={v.dtype}, range=[{v.min():.4f}, {v.max():.4f}]"
        )
    else:
        print(f"  {k}: {v}")

# Dimension distribution
dims = [g.x.shape[0] for g in data_list]
print(
    f"\nDimension stats: min={min(dims)}, max={max(dims)}, mean={sum(dims) / len(dims):.1f}"
)
for lo, hi in [(4, 10), (11, 20), (21, 50)]:
    cnt = sum(1 for d in dims if lo <= d <= hi)
    print(f"  dim {lo:3d}-{hi:3d}: {cnt}")

# Splits
print(f"\nSplits ({len(splits)}):")
for s in splits[:3]:
    print(
        f"  {s['name']}: train={len(s['train_indices'])}, test={len(s['test_indices'])}"
    )
# Count split types
from collections import Counter

types = Counter(s["split_type"] for s in splits)
print(f"  Types: {dict(types)}")

# Check edge weights
print(f"\nEdge weight analysis:")
for i in [0, 40, 80]:
    if i < len(data_list):
        g = data_list[i]
        ea = getattr(g, "edge_attr", None)
        if ea is not None:
            print(
                f"  graph {i}: edge_attr range=[{ea.min():.2f}, {ea.max():.2f}], unique={len(ea.unique())}"
            )
