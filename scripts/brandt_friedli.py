#!/usr/bin/env python3
"""Exp 18c: Friedli spectral-zeta analysis of Hecke-derived isogeny graph spectra.

Cross-bridge test: Exp 15b found the Friedli constant C ~ 1.1367 for the
SL(2,F_p) 4-regular Cayley graphs. Here we compute the same spectral-zeta
generating functional on the Brandt/isogeny graph spectra (built purely from
LMFDB Hecke eigenvalues) and compare the slope behavior.

Spectral zeta of a graph on nontrivial eigenvalues {lambda_i}:
    zeta_G(s) = sum_i |lambda_i|^{-s}
Friedli ratio R(s) = |zeta_G(1-s) / zeta_G(s)|; slope d(log R)/ds at s=1/2 is
a measure of zeta-function asymmetry (Friedli/Karlsson).
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


def spectral_zeta_ratio_slope(vals: np.ndarray, s0: float = 0.5) -> tuple[float, float, float]:
    """Compute log|zeta(1-s)/zeta(s)| and its s-derivative at s0."""
    v = vals[vals > 1e-6]
    if len(v) < 3:
        return float("nan"), float("nan"), 0
    # zeta(s) = sum |v|^{-s}
    logv = np.log(v)
    zs = float((np.exp(-s0 * logv)).sum())
    z1ms = float((np.exp(-(1 - s0) * logv)).sum())
    ratio = math.log(z1ms / zs)
    # d/ds log Z(s) = -<log|v|>_s ; d/ds at s0
    w = np.exp(-s0 * logv)
    dlog = -float((logv * w).sum() / w.sum())
    # d/ds log R(s) = -d/ds log Z(s) - d/ds' log Z(s')|... 
    # log R(s) = log Z(1-s) - log Z(s)
    # d/ds = -Z'(1-s)/Z(1-s) - Z'(s)/Z(s) = (dlog at 1-s) - (dlog at s)?? 
    # Z'(s) = -sum logv e^{-s logv};  dlogZ/ds = -<logv>_s
    # logR'(s) = - dlogZ(1-s) - dlogZ(s)  (chain rule: d/ds Z(1-s) = -Z'(1-s))
    w1 = np.exp(-(1 - s0) * logv)
    dlog_1ms = -float((logv * w1).sum() / w1.sum())
    slope = -dlog_1ms - dlog  # = -(dlogZ at 1-s) + (dlogZ at s)?? 
    # Verify: logR = logZ(1-s)-logZ(s); d/ds = (-dlogZ(1-s)) - (dlogZ(s))
    # dlogZ(1-s)/ds = dlogZ at (1-s) * (-1)  => -dlog_1ms... careful
    # d/ds Z(1-s) = -Z'(1-s);  so d/ds logZ(1-s) = - dlogZ(1-s).
    # slope = (-dlogZ(1-s)) - (dlogZ(s)) = -dlog_1ms - dlog
    return ratio, slope, len(v)


def main() -> int:
    if sys.argv[1:] and sys.argv[1] == "--has-friedli":
        print("flag accepted")
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

    print("=" * 70)
    print("Exp 18c: Friedli spectral-zeta slope on Hecke-derived spectra")
    print("=" * 70)

    # For each q, pooled spectrum over ALL prime levels -> one big graph spectrum
    rows = []
    for q in [2, 3, 5, 7, 11, 13]:
        allv: list[float] = []
        for p in prime_levels:
            for r in by_level[p]:
                embs = embeddings_of(r, q)
                if embs:
                    allv.extend(embs)
        arr = np.array(allv)
        if len(arr) < 50:
            continue
        ratio, slope, n = spectral_zeta_ratio_slope(arr, s0=0.5)
        # also at s0=1.0
        ratio1, slope1, n1 = spectral_zeta_ratio_slope(arr, s0=1.0)
        print(f"q={q:3d}: n={n}  R(1/2)={ratio:+.5f}  slope@1/2={slope:+.5f}  "
              f"R(1)={ratio1:+.5f}  slope@1={slope1:+.5f}")
        rows.append({"q": q, "n": n, "R_half": round(ratio, 5),
                     "slope_half": round(slope, 5), "R_1": round(ratio1, 5),
                     "slope_1": round(slope1, 5)})

    # Friedli constant from Exp 15b for comparison
    friedli = {2: 1.3208, 3: 1.2084, 5: 1.1574, 7: 1.1422, 11: 1.1369, 13: 1.1367}
    print("\nExp 15b Friedli slopes (4-regular Cayley SL(2,F_p), full spectra):")
    print("  ", {k: round(v, 4) for k, v in friedli.items()})

    with open(OUT / "summary_v3_friedli.json", "w") as f:
        json.dump({"test": "Exp 18c Friedli slope on Hecke-derived spectra",
                   "results": rows, "friedli_cayley": friedli}, f, indent=2)
    print(f"\n[DONE] Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
