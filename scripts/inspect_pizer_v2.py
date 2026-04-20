"""Inspect the Pizer dataset - check keys."""

import torch
from pathlib import Path

data_dir = Path("/workspace/data/pizer")

ds = torch.load(data_dir / "dataset_cross_l2_to_l3.pt", weights_only=False)
print(f"Type: {type(ds)}")
if isinstance(ds, dict):
    print(f"Keys: {list(ds.keys())}")
    for k, v in ds.items():
        if isinstance(v, list):
            print(f"  {k}: list of {len(v)} items")
            if len(v) > 0:
                print(f"    first item type: {type(v[0])}")
                if isinstance(v[0], dict):
                    print(f"    first item keys: {list(v[0].keys())}")
                    for kk, vv in v[0].items():
                        if hasattr(vv, "shape"):
                            print(f"      {kk}: {vv.shape}")
                        else:
                            print(f"      {kk}: {type(vv).__name__}")
        elif isinstance(v, torch.Tensor):
            print(f"  {k}: Tensor {v.shape}")
        else:
            print(f"  {k}: {type(v).__name__}")
elif isinstance(ds, list):
    print(f"List of {len(ds)} items")
    if len(ds) > 0:
        item = ds[0]
        print(f"  First item type: {type(item)}")
        if hasattr(item, "keys"):
            for k, v in item.items():
                if hasattr(v, "shape"):
                    print(f"    {k}: {v.shape}")
                else:
                    print(f"    {k}: {type(v).__name__}")
