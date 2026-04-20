"""Inspect the Pizer dataset."""

import torch
import json
from pathlib import Path

data_dir = Path("/workspace/data/pizer")

# Load manifest
with open(data_dir / "manifest.json") as f:
    manifest = json.load(f)

print(f"Manifest: {len(manifest)} entries")
dims_all = [e["dim"] for e in manifest]
print(f"  dim range: {min(dims_all)} to {max(dims_all)}")
print(
    f"  primes range: {min(e['p'] for e in manifest)} to {max(e['p'] for e in manifest)}"
)

# Load cross-ell dataset
ds = torch.load(data_dir / "dataset_cross_l2_to_l3.pt", weights_only=False)
samples = ds["samples"]
print(f"\nCross-l2-to-l3 dataset: {len(samples)} samples")
print(f"  Keys per sample: {list(samples[0].keys())}")

g = samples[0]
for k, v in g.items():
    if isinstance(v, torch.Tensor):
        print(f"  {k}: shape={v.shape}, dtype={v.dtype}")
    else:
        print(f"  {k}: {v}")

# Distribution of dimensions
dims = [g["x"].shape[0] for g in samples]
print(
    f"\n  dim stats: min={min(dims)}, max={max(dims)}, mean={sum(dims) / len(dims):.1f}"
)
for lo, hi in [(4, 10), (11, 20), (21, 50), (51, 166)]:
    cnt = sum(1 for d in dims if lo <= d <= hi)
    print(f"    dim {lo:3d}-{hi:3d}: {cnt}")

# Check splits
splits = ds.get("splits", [])
print(f"\nSplits: {len(splits)}")
for s in splits[:3]:
    name = s.get("name", "?")
    train_n = len(s.get("train_indices", []))
    test_n = len(s.get("test_indices", []))
    print(f"  {name}: train={train_n}, test={test_n}")

# Load self dataset
ds2 = torch.load(data_dir / "dataset_self.pt", weights_only=False)
samples2 = ds2["samples"]
print(f"\nSelf-prediction dataset: {len(samples2)} samples")
