#!/usr/bin/env python3
"""Build manifest from existing Farey graph files."""

import json, os, numpy as np
from pathlib import Path

DATA_DIR = Path("/workspace/data/farey-graphs")
manifest = {"graphs": []}

for npz_file in sorted(DATA_DIR.glob("farey_n*_spectrum.npz")):
    n_str = npz_file.stem.replace("farey_n", "").replace("_spectrum", "")
    n = int(n_str)

    # Load spectrum
    spec = np.load(npz_file)
    spectral_gap = float(spec["spectral_gap"])

    # Load graph data
    graph_file = DATA_DIR / f"farey_n{n:04d}.npz"
    if graph_file.exists():
        gdata = np.load(graph_file)
        shape = gdata["adj_shape"]
        num_vertices = int(shape[0])
        num_edges = len(gdata["adj_data"]) // 2  # symmetric
    else:
        num_vertices = 0
        num_edges = 0

    avg_degree = 2 * num_edges / num_vertices if num_vertices > 0 else 0

    entry = {
        "level": n,
        "num_vertices": num_vertices,
        "num_edges": num_edges,
        "spectral_gap": spectral_gap,
        "avg_degree": round(avg_degree, 4),
        "file_graph": f"farey_n{n:04d}.npz",
        "file_spectrum": f"farey_n{n:04d}_spectrum.npz",
    }
    manifest["graphs"].append(entry)

manifest_path = DATA_DIR / "manifest.json"
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"Manifest: {len(manifest['graphs'])} graphs")
for g in manifest["graphs"]:
    print(
        "  n=%4d V=%6d E=%6d gap=%.6f deg=%.2f"
        % (
            g["level"],
            g["num_vertices"],
            g["num_edges"],
            g["spectral_gap"],
            g["avg_degree"],
        )
    )
