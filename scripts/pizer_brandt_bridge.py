#!/usr/bin/env python3
"""Exp 18b: Brandt/isogeny graph per-level spectrum — KP fit + spectral gap.

For ONE prime level p, the multiset {a_q(f)} over newforms f of level p is the
nontrivial spectrum of the (q+1)-regular supersingular q-isogeny graph
(Pizer/Eichler). Tests per level:
  1. Ramanujan: max|a_q(f)| <= 2*sqrt(q)  (0 violations expected).
  2. Kesten-McKay(q+1) density fit on the level-p spectrum.
  3. Spectral gap lambda1 - |lambda2| = (q+1) - max|a_q|; compare to Alon-Boppana.
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

OUT = Path("data/experiment18")
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


def km_cdf(x: np.ndarray, d: int) -> np.ndarray:
    a = 2.0 * math.sqrt(d - 1)
    grid = np.linspace(-a, a, 200001)
    denom = d * d - grid * grid
    rho = (d / (2 * np.pi)) * np.sqrt(np.clip(4 * (d - 1) - grid * grid, 0, None)) / denom
    cdf_grid = np.cumsum(rho) * (grid[1] - grid[0])
    cdf_grid /= cdf_grid[-1]
    cdf_grid = np.concatenate([[0.0], cdf_grid])
    grid = np.concatenate([[-a], grid])
    return np.interp(x, grid, cdf_grid)


def main() -> int:
    recs = load_recs()
    by_level: dict[int, list[dict]] = defaultdict(list)
    for r in recs:
        by_level[int(r["level"])].append(r)

    def is_prime(n: int) -> bool:
        if n < 2:
            return False
        for d in range(2, int(n ** 0.5) + 1):
            if n % d == 0:
                return False
        return True

    prime_levels = sorted(p for p in by_level if is_prime(p))
    print(f"[INFO] {len(prime_levels)} prime levels")

    # Find the largest prime level with the most embeddings (biggest single graph)
    q = 2
    best_p = max(prime_levels, key=lambda p: sum(
        len(embeddings_of(r, q) or []) for r in by_level[p]))
    best_n = sum(len(embeddings_of(r, q) or []) for r in by_level[best_p])
    print(f"[INFO] largest prime level: p={best_p}, {len(by_level[best_p])} forms, "
          f"{best_n} embeddings of a_{q}")

    results = []
    for q in [2, 3, 5]:
        d = q + 1
        bound = 2.0 * math.sqrt(q)
        gaps = []
        ks_by_p = []
        for p in prime_levels:
            vals: list[float] = []
            for r in by_level[p]:
                embs = embeddings_of(r, q)
                if embs:
                    vals.extend(embs)
            if len(vals) < 20:
                continue
            arr = np.array(vals)
            mx = np.abs(arr).max()
            viol = int((np.abs(arr) > bound + 1e-9).sum())
            gap = d - mx
            gaps.append((gap, viol, len(arr), p, mx))
            # KM fit on this single graph spectrum
            s = np.sort(arr)
            ce = np.arange(1, len(s) + 1) / len(s)
            cm = km_cdf(s, d)
            ks = float(np.max(np.abs(ce - cm)))
            ks_by_p.append((ks, p, len(arr)))
        if not gaps:
            continue
        gaps.sort(key=lambda t: t[0])
        # spectral gap statistics
        max_gap, min_gap = gaps[-1][0], gaps[0][0]
        print(f"\n=== q={q} (d={d}-regular, Ramanujan bound {bound:.4f}) ===")
        print(f"  levels with >=60 eig: {len(gaps)}")
        print(f"  spectral gap range: [{min_gap:.4f} .. {max_gap:.4f}], "
              f"AB bound (d - 2sqrt(q)) = {d - bound:.4f}")
        print(f"  tightest gap: p={gaps[0][3]}  gap={gaps[0][0]:.4f}  "
              f"max|a_q|={gaps[0][4]:.4f}  n={gaps[0][2]}  violations={gaps[0][1]}")
        if ks_by_p:
            ks_by_p.sort()
            kbest, pbest, nbest = ks_by_p[0]
            print(f"  best single-graph KM fit: p={pbest} KS={kbest:.4f} n={nbest}")
            # plot best single graph
            arr = np.array([v for r in by_level[pbest]
                            for v in (embeddings_of(r, q) or [])])
            a = bound
            fig, ax = plt.subplots(figsize=(9, 5))
            ax.hist(arr, bins=50, range=(-a * 1.2, a * 1.2), density=True, alpha=0.55,
                    color="navy", label=f"p={pbest}, {len(arr)} eigenvalues")
            grid = np.linspace(-a, a, 400)
            denom = d * d - grid * grid
            rho = (d / (2 * np.pi)) * np.sqrt(np.clip(4 * (d - 1) - grid * grid, 0, None)) / denom
            ax.plot(grid, rho, "r-", lw=2, label=f"KM({d})-regular")
            ax.axvline(bound, color="g", ls="--", lw=1)
            ax.set_title(f"q-isogeny graph spectrum at p={pbest} (q={q}, d={d})")
            ax.set_xlabel(f"a_{q}(f)")
            ax.legend()
            fig.tight_layout()
            fig.savefig(OUT / f"km_p{pbest}_q{q}.png", dpi=150)
            plt.close(fig)
            print(f"  saved: km_p{pbest}_q{q}.png")

        # Pooled KS across good single graphs (average)
        avg_ks = float(np.mean([k for k, _, _ in ks_by_p]))
        med_ks = float(np.median([k for k, _, _ in ks_by_p]))
        print(f"  across single graphs: mean KS={avg_ks:.4f}, median KS={med_ks:.4f} "
              f"(n_graphs={len(ks_by_p)})")
        results.append({"q": q, "d": d, "n_graphs": len(gaps),
                        "gap_min": round(min_gap, 4), "gap_max": round(max_gap, 4),
                        "ab_bound": round(d - bound, 4), "avg_ks": round(avg_ks, 4)})

    with open(OUT / "summary_v2.json", "w") as f:
        json.dump({"test": "Exp 18b per-level Brandt graphs", "results": results}, f, indent=2)
    print(f"\n[DONE] Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
