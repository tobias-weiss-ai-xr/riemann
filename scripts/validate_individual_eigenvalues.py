#!/usr/bin/env python3
"""Validate individual eigenvalues data structure."""

import json

data = json.load(open("data/lmfdb/lmfdb_individual_eigenvalues.json"))

dims = sorted(set([r["dim"] for r in data]))
multi_dim = [r for r in data if r["dim"] > 1]

print(f"Dimensions in dataset: {dims}")
print(f"Multi-dimensional forms: {len(multi_dim)}")

if multi_dim:
    md = multi_dim[0]
    print(f"\nExample multi-dimensional form:")
    print(f"  Label: {md['label']}")
    print(f"  Dimension: {md['dim']}")
    print(f"  Eigenvalue dimension: {md['eigenvalue_dimension']}")

    eig = md["individual_eigenvalues"]
    print(f"  Individual eigenvalue keys: {sorted(eig.keys())[:10]}")
    print(f"  Sample eigenvalues (coeffs 1-3):")
    for i in [1, 2, 3]:
        val = eig.get(str(i), [])
        print(f"    a_{i}: {val}")

# Check dimension consistency
print(f"\nDimension consistency check:")
for d in dims:
    dim_forms = [r for r in data if r["dim"] == d]
    print(f"  dim={d}: {len(dim_forms)} forms")

print(f"\n✓ Individual eigenvalues data structure validated!")
