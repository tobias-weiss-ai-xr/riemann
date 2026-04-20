"""Debug: check y shape in batched data."""

import torch
from pathlib import Path
from torch_geometric.data import Batch

ds = torch.load(
    Path("/workspace/data/pizer/dataset_cross_l2_to_l3.pt"), weights_only=False
)
data_list = ds["data_list"]

# Single graph
g = data_list[0]
print(f"Single graph y: {g.y.shape}")
print(f"Single graph target_mask: {g.target_mask.shape}")
print(f"Single graph x: {g.x.shape}")

# Batch of 5 graphs
batch = Batch.from_data_list(data_list[:5])
print(f"\nBatch of 5: y: {batch.y.shape}")
print(f"Batch of 5: target_mask: {batch.target_mask.shape}")
print(f"Batch of 5: batch: {batch.batch.shape}, unique: {batch.batch.unique()}")
print(f"Batch of 5: x: {batch.x.shape}")
print(f"Batch of 5: graph_stats: {batch.graph_stats.shape}")

# What we need: for each graph i, get y[i] (its eigenvalues)
# Currently y is concatenated: [graph0_y, graph1_y, ...] with max_dim padding
# So for batch of 5 with dims [4,4,5,5,5], y has shape (23, 41) not (5, 41)!
# We need to index y by graph: y[graph_offset[i]:graph_offset[i]+dim[i]]
