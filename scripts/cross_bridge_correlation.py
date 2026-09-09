#!/usr/bin/env python3
"""Exp 21: Cross-bridge study — Cayley SL(2,F_p) spectral gap vs isogeny-graph (Hecke)
spectrum at the same prime p. Corrected version of the planned Exp 17.

Within-prime comparison (no size confound is fully avoidable, but both objects are
attached to the same p):
  - Cayley 4-regular graph: spectral gap, ramanujan_ratio (Exp 1-4, p=2..79)
  - Isogeny/Brandt graph at level p, q=2: spectrum = embeddings of a_2(f) over
    newforms f of level p (Pizer). Report max|a_2|, gap=(q+1)-max, Ramanujan check.
Cross-correlates: cayley_gap vs isogeny_gap, cayley_ratio vs isogeny_ratio.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path("data/experiment21")
OUT.mkdir(parents=True, exist_ok=True)

CAYLEY = [
    (2, 2.000000, 1.155), (3, 1.267949, 0.789), (5, 0.763932, 0.934),
    (7, 0.585786, 1.028), (11, 0.381966, 1.077), (13, 0.324869, 1.104),
    (17, 0.290725, 1.081), (19, 0.245395, 1.099), (23, 0.206681, 1.103),
    (29, 0.182153, 1.111), (31, 0.227251, 1.103), (37, 0.170768, 1.116),
    (41, 0.180865, 1.102), (43, 0.166165, 1.107), (47, 0.180653, 1.106),
    (53, 0.174447, 1.107), (59, 0.158304, 1.109), (61, 0.185452, 1.106),
    (67, 0.163890, 1.107), (71, 0.160206, 1.108), (73, 0.131854, 1.117),
    (79, 0.177011, 1.105),
]


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
    with open(Path("data/lmfdb/lmfdb_sql_weight2.json")) as f:
        recs = json.load(f)

    # isogeny data per level for q=2 and q=3
    per_level = {p: {2: [], 3: []} for p, _, _ in CAYLEY}
    for r in recs:
        lvl = int(r["level"])
        if lvl not in per_level:
            continue
        for q in (2, 3):
            embs = embeddings_of(r, q)
            if embs:
                per_level[lvl][q].extend(embs)

    rows = []
    print(f"{'p':>3} {'cayley_gap':>10} {'cay_ratio':>9} | {'iso2_max':>8} "
          f"{'iso2_gap':>8} {'iso2_viol':>8} | {'iso3_max':>8} {'iso3_gap':>8}")
    for p, cgap, cratio in CAYLEY:
        mx2 = max((abs(v) for v in per_level[p][2]), default=float("nan"))
        mx3 = max((abs(v) for v in per_level[p][3]), default=float("nan"))
        n2 = len(per_level[p][2])
        n3 = len(per_level[p][3])
        b2, b3 = 2 * math.sqrt(2), 2 * math.sqrt(3)
        viol2 = sum(1 for v in per_level[p][2] if abs(v) > b2 + 1e-9) if n2 else -1
        viol3 = sum(1 for v in per_level[p][3] if abs(v) > b3 + 1e-9) if n3 else -1
        gap2 = (2 + 1) - mx2 if n2 else float("nan")
        gap3 = (3 + 1) - mx3 if n3 else float("nan")
        rows.append({"p": p, "cayley_gap": cgap, "cayley_ratio": cratio,
                     "iso2_max": mx2, "iso2_gap": gap2, "iso2_n": n2, "iso2_viol": viol2,
                     "iso3_max": mx3, "iso3_gap": gap3, "iso3_n": n3, "iso3_viol": viol3})
        print(f"{p:3d} {cgap:10.5f} {cratio:9.4f} | {mx2:8.4f} {gap2:8.4f} "
              f"{viol2:8d} | {mx3:8.4f} {gap3:8.4f}")

    # Correlations (Spearman + Pearson) between cayley_gap and isogeny data (p where both exist)
    valid = [r for r in rows if r["iso2_n"] > 0]
    if len(valid) >= 5:
        cg = np.array([r["cayley_gap"] for r in valid])
        ig2 = np.array([r["iso2_gap"] for r in valid])
        cr = np.array([r["cayley_ratio"] for r in valid])
        im2 = np.array([r["iso2_max"] for r in valid])
        S = lambda a, b: float(np.corrcoef(a, b)[0, 1])  # noqa: E731
        pears = lambda a, b: S(a, b)  # noqa: E731
        print(f"\nCorrelations over {len(valid)} primes:")
        print(f"  pearson(cayley_gap, iso2_gap) = {pears(cg, ig2):+.4f}")
        print(f"  pearson(cayley_ratio, iso2_max) = {pears(cr, im2):+.4f}")
        from scipy.stats import spearmanr
        rs_gap, pv_gap = spearmanr(cg, ig2)
        rs_ratio, pv_ratio = spearmanr(cr, im2)
        print(f"  spearman(cayley_gap, iso2_gap) = {rs_gap:+.4f} (p={pv_gap:.3f})")
        print(f"  spearman(cayley_ratio, iso2_max) = {rs_ratio:+.4f} (p={pv_ratio:.3f})")

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        axes[0].scatter(cg, ig2, c="navy")
        axes[0].set_xlabel("Cayley SL(2,F_p) spectral gap")
        axes[0].set_ylabel("isogeny graph spectral gap (q=2)")
        axes[1].scatter(cr, im2, c="crimson")
        axes[1].set_xlabel("Cayley ramanujan ratio")
        axes[1].set_ylabel("isogeny max|a_2|")
        fig.tight_layout()
        fig.savefig(OUT / "cayley_vs_isogeny.png", dpi=150)
        plt.close(fig)
        print(f"  saved: {OUT / 'cayley_vs_isogeny.png'}")

    import json as _json
    with open(OUT / "summary.json", "w") as f:
        _json.dump({"test": "Exp 21 cross-bridge Cayley vs isogeny", "rows": rows}, f, indent=2)
    print(f"\n[DONE] Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
