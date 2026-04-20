"""Inspect the Pizer dataset."""

import subprocess

result = subprocess.run(
    [
        "python3",
        "-c",
        """
import torch
import json
from pathlib import Path

data_dir = Path('/workspace/data/pizer')

# Load manifest
with open(data_dir / 'manifest.json') as f:
    manifest = json.load(f)

print(f"Manifest: {len(manifest)} entries")
print(f"  dim range: {min(e['dim'] for e in manifest)} to {max(e['dim'] for e in manifest)}")
print(f"  primes: {sorted(set(e['p'] for e in manifest))[:10]}...")

# Load cross-ell dataset
ds = torch.load(data_dir / 'dataset_cross_l2_to_l3.pt', weights_only=False)
samples = ds['samples']
print(f"\nCross-l2-to-l3 dataset: {len(samples)} samples")
print(f"  First sample keys: {samples[0].keys()}")
g = samples[0]
print(f"  x shape: {g['x'].shape}")
print(f"  edge_index shape: {g['edge_index'].shape}")
print(f"  edge_attr shape: {g.get('edge_attr', 'none')}")
print(f"  target_stats shape: {g.get('target_stats', 'none')}")
print(f"  target_eigenvalues shape: {g.get('target_eigenvalues', 'none')}")
print(f"  graph_stats: {g.get('graph_stats', 'none')}")
print(f"  prime: {g.get('prime', 'none')}")

# Distribution of dimensions
dims = [g['x'].shape[0] for g in samples]
print(f"\n  dim stats: min={min(dims)}, max={max(dims)}, mean={sum(dims)/len(dims):.1f}")
print(f"  dim buckets:")
for lo, hi in [(4,10), (11,20), (21,50), (51,100)]:
    cnt = sum(1 for d in dims if lo <= d <= hi)
    print(f"    {lo}-{hi}: {cnt}")

# Load self dataset
ds2 = torch.load(data_dir / 'dataset_self.pt', weights_only=False)
samples2 = ds2['samples']
print(f"\nSelf-prediction dataset: {len(samples2)} samples")

# Splits
splits = ds['splits']
print(f"\nCross-ℓ splits:")
for s in splits[:3]:
    print(f"  {s['name']}: train={len(s['train_indices'])}, test={len(s['test_indices'])}")
""",
    ],
    capture_output=True,
    text=True,
    timeout=60,
)
print(result.stdout[-3000:])
print("STDERR:", result.stderr[-500:] if result.stderr else "")
