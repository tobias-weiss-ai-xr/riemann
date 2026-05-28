import numpy as np
import torch
from torch_geometric.data import Data, Dataset
from sklearn.model_selection import train_test_split

class LMFDBTraceDataset(Dataset):
    def __init__(self, traces, labels, num_nodes=1000):
        super().__init__()
        self.traces = traces
        self.labels = labels
        self.num_nodes = num_nodes
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
        x = torch.from_numpy(self.traces[idx].astype(np.float32)).view(-1, 1)
        label = self.labels[idx]
        return Data(x=x, y=torch.tensor([label], dtype=torch.float))

def build_dataset():
    print('Loading data...')
    traces = np.load('data/lmfdb/lmfdb_sql_traces_matrix.npy', mmap_mode='r')
    N = traces.shape[0]
    print(f'Loaded {N} samples.')
    y_dummy = np.zeros(N) 
    train_idx, test_idx = train_test_split(np.arange(N), test_size=0.2, random_state=42)
    print('Creating PyG Dataset...')
    dataset = LMFDBTraceDataset(traces, y_dummy)
    print(f'Successfully created LMFDBTraceDataset with {len(dataset)} samples.')
    print(f'Edge index shape: {dataset.edge_index.shape}')
    save_path = 'data/lmfdb/lmfdb_pyg_dataset.pt'
    print('Converting traces to tensor...')
    full_traces_tensor = torch.from_numpy(traces.astype(np.float32))
    torch.save({
        'traces': full_traces_tensor,
        'edge_index': dataset.edge_index,
        'train_idx': torch.tensor(train_idx),
        'test_idx': torch.tensor(test_idx)
    }, save_path)
    print(f'Saved dataset to {save_path}')

if __name__ == '__main__':
    build_dataset()
