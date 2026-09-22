#!/usr/bin/env python
"""RT3-LC-EXACT: Li's criterion at K=10000 zeros, N_MAX=1000, tight interval.

Patches li_criterion_certified (RT2-LC) constants and reuses its verified
machinery: checkpointed zetazero, exact nonnegative pair sums, closed-form
lambda_1 calibration, Bombieri-Lagarias asymptotic fit.

K=10000 (vs 1000), K_TAIL_EXACT=200 (vs 100), N_MAX=1000 (vs 300),
fit window [500,1000] (vs [150,300]). Zeros seeded from RT2-LC checkpoint.
"""
from __future__ import annotations
import json, os, sys, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import li_criterion_certified as lc

lc.K_ZEROS = 10000
lc.K_TAIL_EXACT = 200
lc.N_MAX = 1000
lc.FIT_LO, lc.FIT_HI = 500, 1000
lc.OUT_PATH = str(Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_lc_exact.json")
lc.ZEROS_PATH = str(Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_lc_exact_zeros.json")

def validate(res):
    msgs, ok = [], True
    def check(cond, msg):
        nonlocal ok
        msgs.append(("PASS" if cond else "FAIL") + "  " + msg)
        ok = ok and cond
    p = res.get("params", {})
    check(p.get("k_zeros") == 10000 and p.get("k_tail_exact") == 200 and p.get("n_max") == 1000,
          f"params: K={p.get('k_zeros')}, tail={p.get('k_tail_exact')}, n_max={p.get('n_max')}")
    tbl = res.get("lambda_table", [])
    check(len(tbl) == 1000 and [e["n"] for e in tbl] == list(range(1, 1001)),
          f"lambda_table has {len(tbl)} entries (expect 1000)")
    z = res.get("zeros", {})
    check(z.get("all_on_critical_line") is True,
          f"(e) all zeros on critical line (max |Re-1/2| = {z.get('max_re_deviation_from_half')})")
    l1 = res.get("lambda1_check", {})
    check(l1.get("inside_interval") is True,
          f"(a) lambda_1 closed = {l1.get('closed'):.10f} in [{l1.get('S_K_1'):.10f}, {l1.get('certified_upper_1'):.10f}]")
    check(all(e["S_K"] > 0 for e in tbl), "(b) S_K(n) > 0 for all n = 1..1000")
    A = res.get("asymptotic_fit", {}).get("A_fit", 0.0)
    check(0.4 <= A <= 0.6, f"(c) A_fit = {A:.6f} in [0.40, 0.60]")
    bad = [e["n"] for e in tbl if e.get("exact_tail_100", 0) > e["T_bound"]]
    check(not bad, f"(d) exact_tail <= T_bound (violations: {bad if bad else 'none'})")
    return ok, msgs
lc.validate = validate

def seed_zeros():
    if os.path.exists(lc.ZEROS_PATH):
        return
    src = str(Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_lc_certified_zeros.json")
    if os.path.exists(src):
        shutil.copy(src, lc.ZEROS_PATH)
        print(f"[rt3-lc] seeded zeros from RT2-LC checkpoint")
    else:
        print("[rt3-lc] no RT2-LC checkpoint; computing all 10200 zeros from scratch")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="RT3-LC-EXACT: K=10000 Li's criterion")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    seed_zeros()
    res = lc.compute(force=args.force)
    res["task"] = "RT3-LC-EXACT"
    res["title"] = "Certified Li's criterion (K=10000 zeros + exact tail 200)"
    lc.save(res, lc.OUT_PATH)
    lc.summary(res)
    ok, msgs = validate(res)
    for m in msgs:
        print(m)
    if args.gate:
        print(f"\nGATE {'PASSED' if ok else 'FAILED'} (gate_pass={res['gate_pass']})")
        return 0 if ok else 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
