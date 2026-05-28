import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool
from torch_geometric.loader import DataLoader
from torch_geometric.data import Data, Dataset
from sklearn.model_selection import train_test_split


class LMFDBTraceDataset(Dataset):
    def __init__(self, traces, labels, num_nodes=1000):
        super().__init__()
        self.traces = traces
        self.labels = labels
        self.num_nodes = num_nodes
        # The edge_index is a static property of the entire dataset
        self.edge_index = self._build_static_edges()

    def _build_static_edges(self):
        edges = []
        for i in range(self.num_nodes - 1):
            edges.append([i, i + 1])
            edges.append([i + 1, i])
        for n in range(2, self.num_nodes + 1):
            temp_n = n
            d = 2
            while d * d <= temp_n:
                if temp_n % d == 0:
                    edges.append([n - 1, d - 1])
                    edges.append([d - 1, n - 1])
                    while temp_n % d == 0:
                        temp_n //= d
                d += 1
            if temp_n > 1 and temp_n < self.num_nodes + 1:
                edges.append([n - 1, temp_n - 1])
                edges.append([temp_n - 1, n - 1])
        return torch.tensor(edges, dtype=torch.long).t().contiguous()

    def len(self):
        return self.traces.shape[0]

    def get(self, idx):
        # Crucial Fix: Do NOT include edge_index in the Data object here.
        # The DataLoader will see it as None in the batch if we do.
        # We will pass the static edge_index directly to the model instead.
        x = torch.from_numpy(self.traces[idx].astype(np.float32)).view(-1, 1)
        label = self.labels[idx]
        return Data(x=x, y=torch.tensor([label], dtype=torch.float))


class GCNNet(nn.Module):
    def __init__(self, in_channels, hidden_channels):
        super(GCNNet, self).__in__(self, in_channels, hidden_channels)
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.conv3 = GCNConv(hidden_channels, 16)
        self.fc = nn.Linear(16, 1)

    def forward(self, x, edge_index, batch):
        # edge_index is now a static tensor passed from the training loop
        x = F.relu(self.conv1(x, edge_index))
        x = F.relu(self.conv2(x, edge_index))
        x = self.conv3(x, edge_index)
        x = global_mean_pool(x, batch)
        return self.fc(x)


def main():
    print("Loading data...")
    traces = np.load("data/lmfdb/lmfdb_sql_traces_matrix.npy", mmap_mode="r")
    N = traces.shape[0]
    print(f"Loaded {N} samples.")

    # Create dummy labels for the baseline
    y = np.random.rand(N).astype(np.float32)

    train_idx, test_idx = train_test_split(np.arange(N), test_size=0.2, random_state=42)

    # Create dataset and get the static edge_index
    dataset = LMFDBTraceDataset(traces, y)
    static_edge_index = dataset.edge_index  # Grab the static graph structure

    # We only use the actual indices for training/testing
    train_dataset = LMFDBTraceDataset(traces[train_idx], y[train_idx])
    test_dataset = LMFDBTraceDataset(traces[test_idx], y[test_idx])

    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=64, shuffle=False)

    model = GCNNet(in_channels=1, hidden_channels=64)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.MSELoss()

    print("Starting training...")
    model.train()
    for epoch in range(1, 11):
        total_loss = 0
        for data in train_loader:
            optimizer.zero_grad()
            # IMPORTANT: Pass the static_edge_index explicitly to bypass DataLoader batching issues
            out = model(data.x, static_edge_index, data.batch)
            loss = criterion(out.squeeze(), data.y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch} - Loss: {total_loss / len(train_loader):.4f}")

    # Evaluation
    model.eval()
    total_mse = 0
    with torch.no_grad():
        for data in test_loader:
            # Use the same static_edge_index for testing
            out = model(
                data.x, static_edge_to_index, data.batch
            )  # Wait, check var name
            total_mse += criterion(out.squeeze(), data.y).item()
    print(f"Test MSE: {total_mse / len(test_loader):.4f}")


if __name__ == "__main__":
    main()
