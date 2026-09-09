#!/usr/bin/env python3
"""Exp 20 (v2): Hecke eigenvalue murmurations — rank separation, cumulative average.

Robust test across q = 2..13:
  - for each (level, rank): mean of a_q embeddings over newforms at that level
  - cumulative moving average over levels sorted ascending
  - rank separation statistic: signed difference rank2 - rank0 over common levels
  - stability check: does separation persist for every q?
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("data/experiment20")
OUT.mkdir(parents=True, exist_ok=True)


def load_recs() -> list[dict]:
    with open(Path("data/lmfdb/lmfdb_sql_weight2.json")) as f:
        return json.load(f)


def embeddings_of(rec: dict, n: int) -> list[float] | None:
    ie = rec.get("individual_eigenvalues") or {}
    vals = ie.get(str(n - 1))
    if vals is None:
        return None
    try:
        return [float(x) for x in vals]
    except (TypeError, ValueError):
        return None


def main() -> int:
    recs = load_recs()
    qs = [2, 3, 5, 7, 11, 13]

    rows = []
    fig, axes = plt.subplots(2, 3, figsize=(16, 8), sharey=False)
    for idx, q in enumerate(qs):
        # mean a_q per (level, rank)
        lvl_rank_mean: dict[tuple[int, int], float] = {}
        lvl_rank_n: dict[tuple[int, int], int] = {}
        for r in recs:
            lvl = int(r["level"])
            rank = int(r.get("analytic_rank", -1))
            embs = embeddings_of(r, q)
            if not embs:
                continue
            key = (lvl, rank)
            s = lvl_rank_mean.get(key, 0.0)
            n = lvl_rank_n.get(key, 0)
            lvl_rank_mean[key] = s + sum(embs)
            lvl_rank_n[key] = n + len(embs)
        means = {k: v / lvl_rank_n[k] for k, v in lvl_rank_mean.items()}

        ranks = [0, 1, 2]
        lvls = sorted(set(l for (l, _) in means))
        # cumulative average curve per rank (all levels, not just prime)
        curves = {}
        for r in ranks:
            xs, acc = [], []
            for L in lvls:
                v = means.get((L, r))
                if v is not None:
                    acc.append(v)
                    xs.append(L)
            ys = np.cumsum(acc) / np.arange(1, len(acc) + 1)
            curves[r] = (xs, ys)

        # separation: rank2 - rank0 cumulative at the END (all levels)
        x0, y0 = curves[0]
        if len(y0) and len(curves[2][1]):
            sep = float(curves[2][1][-1] - y0[-1])
            sep_pct_pos = float(np.mean(curves[2][1][-100:] > y0[-100:]))
        else:
            sep, sep_pct_pos = float("nan"), float("nan")
        rows.append({"q": q, "sep_rank2_minus_rank0_final": round(sep, 5),
                     "pct_pos_last100": round(sep_pct_pos, 3)})

        ax = axes[idx // 3][idx % 3]
        colors = {0: "tab:blue", 1: "tab:orange", 2: "tab:green"}
        for r in ranks:
            xs, ys = curves[r]
            if len(xs) and len(ys):
                ax.plot(xs, ys, "-", color=colors[r], lw=1.2, alpha=0.9,
                        label=f"rank {r}")
        ax.axhline(0, color="gray", ls="--", lw=0.7)
        ax.set_title(f"q={q}  sep(r2-r0)={sep:+.4f}")
        ax.set_xlabel("level")
        ax.set_xscale("log")
        ax.legend(fontsize=8)
    fig.suptitle("Exp 20: Hecke eigenvalue murmurations — cumulative mean a_q by rank")
    fig.tight_layout()
    fig.savefig(OUT / "murmurations_multiq.png", dpi=150)
    plt.close(fig)
    print(f"  saved: {OUT / 'murmurations_multiq.png'}")

    for r in rows:
        print(f"  q={r['q']:2d}: sep(rank2-rank0, final cum) = {r['sep_rank2_minus_rank0_final']:+.5f}  "
              f"pct_pos_last100 = {r['pct_pos_last100']}")

    sig = [r for r in rows if r["sep_rank2_minus_rank0_final"] < -0.05]
    print(f"\n  rank2 BELOW rank0 (murmuration sign) in {len(sig)}/{len(rows)} primes")

    with open(OUT / "summary_v2.json", "w") as f:
        json.dump({"test": "Exp 20v2 Hecke murmurations", "results": rows}, f, indent=2)
    print(f"\n[DONE] Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
