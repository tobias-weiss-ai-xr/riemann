"""Minimal Pizer GNN test — inline script to verify training works."""

import torch, numpy as np
from pathlib import Path
from torch_geometric.data import Batch
from torch_geometric.nn import ChebConv, global_mean_pool, global_max_pool
import torch.nn as nn, torch.nn.functional as F

ds = torch.load(
    Path("/workspace/data/pizer/dataset_cross_l2_to_l3.pt"), weights_only=False
)
dl = ds["data_list"]

tr = Batch.from_data_list(dl[:60])
te = Batch.from_data_list(dl[60:65])


# KEY FIX: reshape y from (sum,) to (B, 41)
def get_t(b):
    y, m = b.y, b.target_mask
    ng = b.batch.max().item() + 1
    return y.reshape(ng, 41), m.reshape(ng, 41)


tr_y, tr_m = get_t(tr)
te_y, te_m = get_t(te)


def compute_stats(y, m):
    B = y.shape[0]
    s = torch.zeros(B, 9)
    for i in range(B):
        e = y[i, m[i].bool()]
        if e.numel() < 2:
            continue
        s[i, 0] = e.mean()
        s[i, 1] = e.std() if e.numel() > 1 else 0.0
        s[i, 2] = e.min()
        s[i, 3] = e.max()
        s[i, 4] = e.median()
        se, _ = torch.sort(e)
        n = len(se)
        s[i, 5] = se[n // 4]
        s[i, 6] = se[3 * n // 4]
        s[i, 7] = e.abs().max()
        s[i, 8] = (e > 0).float().mean()
    return s


tr_tgt = compute_stats(tr_y, tr_m)
te_tgt = compute_stats(te_y, te_m)

print(f"Train: {tr.x.shape}, y reshaped: {tr_y.shape}, target: {tr_tgt.shape}")
print(f"Test:  {te.x.shape}, y reshaped: {te_y.shape}, target: {te_tgt.shape}")


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.c1 = ChebConv(3, 64, 3)
        self.c2 = ChebConv(64, 64, 3)
        self.c3 = ChebConv(64, 64, 3)
        self.mlp = nn.Linear(64 * 2 + 6, 9)

    def forward(self, x, ei, ew, b, gs):
        gs = gs.squeeze(1) if gs.dim() == 3 else gs
        h = F.gelu(self.c1(x, ei, ew))
        h = F.gelu(h + self.c2(h, ei, ew))
        h = F.gelu(h + self.c3(h, ei, ew))
        return self.mlp(
            torch.cat([global_mean_pool(h, b), global_max_pool(h, b), gs], dim=-1)
        )


model = Model()
opt = torch.optim.Adam(model.parameters(), lr=1e-3)


def norm_ew(b):
    ew = (
        b.edge_attr[:, 0]
        if b.edge_attr is not None
        else torch.ones(b.edge_index.shape[1])
    )
    d = torch.zeros(b.x.shape[0])
    d.scatter_add_(0, b.edge_index[0], ew.abs())
    return ew / d.clamp(min=1e-8)[b.edge_index[0]].sqrt()


ew_tr = norm_ew(tr)
ew_te = norm_ew(te)

print("\nTraining...")
for ep in range(100):
    model.train()
    opt.zero_grad()
    p = model(tr.x, tr.edge_index, ew_tr, tr.batch, tr.graph_stats)
    loss = F.mse_loss(p, tr_tgt)
    loss.backward()
    opt.step()
    if ep % 25 == 0 or ep == 99:
        model.eval()
        with torch.no_grad():
            tp = model(te.x, te.edge_index, ew_te, te.batch, te.graph_stats)
            tl = F.mse_loss(tp, te_tgt)
        print(
            f"  ep {ep:3d}: train={loss.item():.4f} test={tl.item():.4f} pred=[{tp.min():.3f},{tp.max():.3f}]"
        )

print("\nFinal R2:")
model.eval()
with torch.no_grad():
    tp = model(te.x, te.edge_index, ew_te, te.batch, te.graph_stats)
p, t = tp.numpy(), te_tgt.numpy()
names = ["mean", "std", "min", "max", "median", "Q25", "Q75", "radius", "pos_frac"]
for j, n in enumerate(names):
    ss_r = np.sum((p[:, j] - t[:, j]) ** 2)
    ss_t = np.sum((t[:, j] - np.mean(t[:, j])) ** 2)
    r2 = 1 - ss_r / ss_t if ss_t > 1e-10 else 0.0
    print(f"  {n:10s}: R2={r2:+.4f}")
