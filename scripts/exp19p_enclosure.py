#!/usr/bin/env python3
"""EPIC-4 Exp 19p: convergence-ladder enclosure at the worst margin point.

Loads the margin map from E4-P1, finds the point with minimum margin,
and computes a convergence ladder (N, nmax) at that point to certify
the margin is positive with a conservative error bar.

    err = (max - min) / 2 over the four rungs
    m_hat = (max + min) / 2
    lower_bound = m_hat - err

Gate: exit 0 iff all four rung margins > 0 AND lower_bound > 0.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from nystrom_collocation import margin, leading_pair

DATA = pathlib.Path("data/experiment19p")
LADDER = [(256, 6000), (384, 8000), (512, 8000), (512, 12000)]


def main() -> None:
    gate = "--gate" in sys.argv
    mm = json.loads((DATA / "margin_map.json").read_text())
    pts = mm["points"]
    worst = min(pts, key=lambda p: p["margin"])
    sigma, t = worst["sigma"], worst["t"]
    s = complex(sigma, t)

    print(f"Worst point: (sigma={sigma}, t={t})  margin={worst['margin']:.6f}")
    print(f"Convergence ladder:")
    rungs = []
    for N, nmax in LADDER:
        m = margin(s, N, nmax)
        l1, l2 = leading_pair(s, N, nmax)
        rungs.append({"N": N, "nmax": nmax, "margin": m, "abs_lambda2": l2})
        print(f"  N={N:3d} nmax={nmax:5d}  m={m:.6f}  |lambda1|={l1:.6f}  |lambda2|={l2:.6f}")

    ms = [r["margin"] for r in rungs]
    m_hat = (max(ms) + min(ms)) / 2
    err = (max(ms) - min(ms)) / 2
    lower_bound = m_hat - err

    enc = {
        "sigma": sigma,
        "t": t,
        "ladder": rungs,
        "m_hat": m_hat,
        "err": err,
        "lower_bound": lower_bound,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "enclosure.json").write_text(json.dumps(enc, indent=2) + "\n")
    print(f"\nm_hat={m_hat:.6f}  err={err:.6f}  lower_bound={lower_bound:.6f}")

    if gate:
        ok = all(r["margin"] > 0 for r in rungs) and lower_bound > 0
        if ok:
            print(f"GATE PASS: all rungs > 0, lower_bound={lower_bound:.6f} > 0")
            sys.exit(0)
        bad = [r for r in rungs if r["margin"] <= 0]
        if bad:
            print(f"GATE FAIL: rungs with margin <= 0: {bad}")
        if lower_bound <= 0:
            print(f"GATE FAIL: lower_bound={lower_bound:.6f} <= 0 (not converged)")
        sys.exit(1)


if __name__ == "__main__":
    main()
