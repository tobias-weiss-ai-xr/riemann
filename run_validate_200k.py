#!/usr/bin/env python3
"""Quick validation of 200K incremental CSV."""
from __future__ import annotations

import pandas as pd

df = pd.read_csv("data/lmfdb/lmfdb_incremental_ml.csv")
print(f"Rows: {len(df)}")
print(f"Cols: {list(df.columns)}")
print(f"is_cm: {df.is_cm.value_counts().to_dict()}")
print(f"analytic_rank distribution: {df.analytic_rank.value_counts().head(10).to_dict()}")
print(f"dim distribution: {df.dim.value_counts().head(10).to_dict()}")
print(f"NaN in dim: {df.dim.isna().sum()}")
print(f"NaN in is_cm: {df.is_cm.isna().sum()}")
print(f"NaN in traces: {df.filter(like='trace_', axis=1).isna().sum().sum()}")
print(f"char_order values: {df.char_order.unique()[:10]}")
