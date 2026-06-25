#!/usr/bin/env python3
"""Run 200K sklearn ML experiment (scale-up of Exp 10)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LOG_DIR = Path("data/lmfdb/sklearn_200k")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Run standard pipeline (no HPO, no CV) on 200K
cmd = [
    sys.executable, "scripts/train_lmfdb_ml_53k.py",
    "--data", "data/lmfdb/lmfdb_incremental_ml.csv",
    "--skip-ablation",
]

with open(LOG_DIR / "200k_std_pipeline.log", "w") as f:
    result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, text=True)

print(f"Exit code: {result.returncode}")
print(f"Log: {LOG_DIR / '200k_std_pipeline.log'}")
