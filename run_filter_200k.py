#!/usr/bin/env python3
"""Filter rank 3 record from 200K CSV."""
from __future__ import annotations

import pandas as pd

df = pd.read_csv("data/lmfdb/lmfdb_incremental_ml.csv")
print(f"Before: {len(df)} rows")
rank3 = df[df.analytic_rank >= 3]
print(f"Dropping {len(rank3)} records with rank >= 3")
if len(rank3) > 0:
    print(rank3[["label", "level", "dim", "analytic_rank"]].to_string())

df = df[df.analytic_rank < 3]
print(f"After: {len(df)} rows")
df.to_csv("data/lmfdb/lmfdb_incremental_200k_clean.csv", index=False)
print("Saved to data/lmfdb/lmfdb_incremental_200k_clean.csv")
