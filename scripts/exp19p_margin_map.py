#!/usr/bin/env python3
"""Exp 19p (EPIC-4 / task E4-P1, plan S1): eigenvalue-1 margin map.

Grid: t in {124.2568 (gamma_41), 1100.574 (zero #731), 150.0 (corner)} x
sigma in {0.501, 0.505, 0.51, 0.515, 0.52, 0.535, 0.55} -> 21 points.
Per point compute m(s) = min_j |1 - lambda_j(s)| and |lambda_2(s)| for the
Mayer/Ruelle transfer operator L_s, assembled with the overflow-safe chunked
Nystrom collocation (scripts/nystrom_collocation.py).

RH <=> m(s) > 0 on Re(s) > 1/2, so HONESTY RULE: any margin <= 0 is a REAL
candidate counterexample -- record verbatim, print loudly, let --gate fail.

Checkpoint after every point to data/experiment19p/margin_map.json; a restart
skips already-computed (sigma, t) pairs. Resolution per plan: N=384, nmax=8000
for t <= 500; N=512, nmax=8000 for t > 500.
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from nystrom_collocation import nystrom_matrix_vec

HEIGHTS = (124.2568, 1100.574, 150.0)  # gamma_41, zero #731, corner
SIGMAS = (0.501, 0.505, 0.51, 0.515, 0.52, 0.535, 0.55)
FIT_SIGMA_MIN = 0.505  # sigma=0.501 is tail-unresolved: kept in points, excluded from fit
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # worktree root
JSON_PATH = os.path.join(_ROOT, "data", "experiment19p", "margin_map.json")


def resolution(t: float) -> tuple[int, int]:
    """(N, nmax) per plan: N=384 for t <= 500, N=512 above; nmax=8000."""
    return (384, 8000) if t <= 500 else (512, 8000)


def compute_point(sigma: float, t: float) -> dict:
    """One assembly -> both m(s) and |lambda2| (bit-identical to margin()/leading_pair)."""
    n, nmax = resolution(t)
    ev = np.linalg.eigvals(nystrom_matrix_vec(sigma + 1j * t, n, nmax))
    order = np.argsort(-np.abs(ev))
    return {
        "sigma": sigma,
        "t": t,
        "margin": float(np.min(np.abs(ev - 1.0))),
        "abs_lambda2": float(abs(ev[order[1]])),
        "N": n,
        "nmax": nmax,
    }


def fit_slopes(points: list[dict]) -> list[dict]:
    """Per height: least-squares m(sigma) = c*(sigma-1/2) + b over sigma >= 0.505."""
    slopes = []
    for t in HEIGHTS:
        xy = [(p["sigma"] - 0.5, p["margin"]) for p in points
              if p["t"] == t and p["sigma"] >= FIT_SIGMA_MIN]
        if len(xy) < 2:
            continue
        c, b = np.polyfit([x for x, _ in xy], [y for _, y in xy], 1)
        slopes.append({
            "t": t,
            "c": float(c),
            "b": float(b),
            "sigma_star": float(0.5 - b / c) if c > 0 else None,
            "n_fit": len(xy),
        })
    return slopes


def save(points: list[dict], slopes: list[dict]) -> None:
    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"points": points, "slopes": slopes}, f, indent=1)
    os.replace(tmp, JSON_PATH)


def gate(points: list[dict], slopes: list[dict]) -> list[str]:
    """Empty list == pass. Nonzero margins are checked verbatim (honesty rule)."""
    fails = []
    if len(points) < len(HEIGHTS) * len(SIGMAS):
        fails.append(f"incomplete grid: {len(points)}/{len(HEIGHTS) * len(SIGMAS)} points")
    bad = [p for p in points if p["margin"] <= 0]
    for p in bad:
        print(f"!!! MARGIN <= 0 at sigma={p['sigma']}, t={p['t']}: m={p['margin']:.6g}"
              "  <-- CANDIDATE RH COUNTEREXAMPLE (recorded verbatim)")
    if bad:
        fails.append(f"{len(bad)} point(s) with margin <= 0 -- candidate counterexample")
    n_star = sum(1 for s in slopes if s["sigma_star"] is not None and s["sigma_star"] < 0.5)
    if n_star < 2:
        fails.append(f"only {n_star}/{len(HEIGHTS)} heights have sigma* < 0.5 (need >= 2)")
    return fails


def print_report(points: list[dict], slopes: list[dict]) -> None:
    print(f"\n{'sigma':>7} {'t':>10} {'N':>4} {'m(s)':>12} {'|lambda2|':>11}")
    for p in sorted(points, key=lambda q: (q["t"], q["sigma"])):
        print(f"{p['sigma']:>7.3f} {p['t']:>10.4f} {p['N']:>4d}"
              f" {p['margin']:>12.6f} {p['abs_lambda2']:>11.5f}")
    print("\nlinear fit m(sigma) = c*(sigma-1/2) + b over sigma >= 0.505:")
    for s in slopes:
        star = "n/a" if s["sigma_star"] is None else f"{s['sigma_star']:.4f}"
        print(f"  t={s['t']:>10.4f}  c={s['c']:+.4f}  b={s['b']:+.5f}"
              f"  sigma*={star}  (n_fit={s['n_fit']})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true",
                    help="validate the existing JSON; no computation")
    args = ap.parse_args()

    if args.gate:
        if not os.path.exists(JSON_PATH):
            print(f"GATE FAIL: {JSON_PATH} not found -- run without --gate first")
            return 1
        with open(JSON_PATH) as f:
            data = json.load(f)
        print_report(data["points"], data["slopes"])
        fails = gate(data["points"], data["slopes"])
        if fails:
            for msg in fails:
                print("GATE FAIL:", msg)
            return 1
        print("GATE PASS: all 21 points, every margin > 0, >= 2/3 heights sigma* < 0.5")
        return 0

    points = []
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH) as f:
            points = json.load(f)["points"]
    done = {(p["sigma"], p["t"]) for p in points}
    print(f"exp19p: {len(done)} points already done, {21 - len(done)} to compute -> {JSON_PATH}")

    for t in HEIGHTS:
        for sigma in SIGMAS:
            if (sigma, t) in done:
                continue
            t0 = time.time()
            p = compute_point(sigma, t)
            points.append(p)
            save(points, fit_slopes(points))  # checkpoint after EVERY point
            if p["margin"] <= 0:
                print(f"!!! MARGIN <= 0 at sigma={sigma}, t={t}: m={p['margin']:.6g}"
                      "  <-- CANDIDATE RH COUNTEREXAMPLE (recorded verbatim)")
            print(f"[{len(points)}/21] sigma={sigma:<6} t={t:<9} N={p['N']} "
                  f"m={p['margin']:.6f} |lambda2|={p['abs_lambda2']:.5f} "
                  f"({time.time() - t0:.1f}s)")

    slopes = fit_slopes(points)
    save(points, slopes)
    print_report(points, slopes)
    fails = gate(points, slopes)
    if fails:
        for msg in fails:
            print("GATE FAIL:", msg)
        return 1
    print("GATE PASS: all 21 points, every margin > 0, >= 2/3 heights sigma* < 0.5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
