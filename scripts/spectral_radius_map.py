#!/usr/bin/env python3
"""
EPIC-4: Spectral-radius map over the strip (1/2, 1] for L_s (Gauss map)
=======================================================================

Maps the full-operator leading eigenvalue |λ₁(σ+it)| and the corrected
(second) spectral radius |λ₂(σ+it)| over the RH-relevant strip, using the
Nyström collocation (n_max-truncated — see caveat near σ ≈ 1/2).

Key facts it reproduces:
  * full operator has ρ > 1 for 1/2 < σ < 1 (constant-mode ζ(2σ) peak;
    |λ₁| ≈ 7.6 at σ=0.51, t=0) — the boundary correction L_s^(0) is essential
  * corrected ρ = |λ₂| < 1 over the strip grid   (worst ≈ 0.95 at σ=0.55,
    t=100 on our grid; approaching 1 as σ → 1/2⁺ where truncation is delicate)
  * |λ₂(1)| = GKW ≈ 0.304 at t=0, σ=1 (sanity)
  * σ ≥ 1 safe everywhere (previous experiments)

CAVEAT: near σ = 1/2 the n-sum Σ (n+1)^{-2σ} converges only slowly
(n_max^{-(2σ−1)}), so near-boundary values at σ ≤ 0.55 are truncation-
sensitive; report always includes n_max for context.

Outputs: data/spectral-radius/spectral_radius_map.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from lambda1_derivative import nystrom_matrix


def two_leading(s: complex, n: int, nmax: int) -> tuple[float, float]:
    A = nystrom_matrix(s, n, nmax)
    ev = np.linalg.eigvals(A)
    o = np.argsort(-np.abs(ev))
    return float(abs(ev[o[0]])), float(abs(ev[o[1]]))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=48)
    p.add_argument("--nmax", type=int, default=2400)
    p.add_argument("--sigmas", type=float, nargs="+",
                   default=[0.55, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0])
    p.add_argument("--ts", type=float, nargs="+",
                   default=[0, 5, 10, 15, 20, 30, 50, 100])
    p.add_argument("--sigma-critical", type=float, default=0.51,
                   help="horizontal line just above the critical line to fine-scan")
    p.add_argument("--output", default="data/spectral-radius/spectral_radius_map.json")
    args = p.parse_args()

    out = {"N": args.n, "n_max": args.nmax, "caveat": "near sigma->1/2 truncation sensitive",
           "strip": {}, "critical_zone": {}, "worst": None}
    worst = (0.0, 0.0, 0.0)
    for sig in args.sigmas:
        row = {}
        for t in args.ts:
            l1, l2 = two_leading(complex(sig, t), args.n, args.nmax)
            row[str(t)] = {"abs_l1": l1, "abs_l2_corrected": l2}
            if l2 > worst[0]:
                worst = (l2, sig, t)
        out["strip"][str(sig)] = row
    out["worst"] = {"abs_l2": worst[0], "sigma": worst[1], "t": worst[2],
                    "below_one": worst[0] < 1}

    # fine scan on the line just above the critical line
    crit = {}
    for t in np.arange(0.0, 101.0, 5.0):
        t = round(float(t), 2)
        l1, l2 = two_leading(complex(args.sigma_critical, t), args.n, args.nmax)
        crit[str(t)] = {"abs_l1": l1, "abs_l2_corrected": l2}
    out["critical_zone"] = {"sigma": args.sigma_critical, "scan": crit}

    pth = Path(args.output)
    pth.parent.mkdir(parents=True, exist_ok=True)
    pth.write_text(json.dumps(out, indent=2))
    print(f"worst corrected ρ (strip grid) = {worst[0]:.4f} at σ={worst[1]:.2f}, t={worst[2]}  "
          f"-> < 1: {worst[0] < 1}")
    print(f"wrote {pth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
