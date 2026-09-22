#!/usr/bin/env python
"""RT3-NB-4K: Nyman-Beurling at n=2048, 4096 (extends RT2-NB n<=1024).

Reuses assemble/compute/selftest from nyman_beurling_ext (RT2-NB).
SIZES = (16, 32, 64, 128, 256, 512, 1024, 2048, 4096).
Output: data/routes/rt_nb_4k.json
Gate: all 9 sizes, eps_4096 < 0.001, |beta| > 0.3.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyman_beurling_ext as nbe

SIZES = (16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_nb_4k.json"
GATE_EPS_4096_MAX = 0.001
GATE_ABS_BETA_MIN = 0.3

def run(log):
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if OUT_PATH.exists():
        try:
            data = json.loads(OUT_PATH.read_text())
        except json.JSONDecodeError:
            data = {}
    sizes = {e["n"]: e for e in data.get("sizes", []) if e.get("complete")}
    data["task"] = "RT3-NB-4K"
    data["title"] = "Nyman-Beurling density at n up to 4096"
    data["params"] = {"sizes": list(SIZES),
                      "gate": {"eps_4096_max": GATE_EPS_4096_MAX, "abs_beta_min": GATE_ABS_BETA_MIN}}
    st = nbe.selftest()
    data["selftest"] = st
    if not st["ok"]:
        log(f"!! SELFTEST FAILED: {json.dumps(st)}")
    for n in SIZES:
        if n in sizes:
            log(f"n={n}: cached, skipping")
            continue
        sizes[n] = nbe.compute(n, log)
        data["sizes"] = [sizes[m] for m in SIZES if m in sizes]
        OUT_PATH.write_text(json.dumps(data, indent=2))
    data["sizes"] = [sizes[m] for m in SIZES]
    eps = [sizes[m]["eps_n"] for m in SIZES]
    fit = {}
    if all(e > 0 for e in eps):
        beta, inter = (float(v) for v in np.polyfit(np.log(np.array(SIZES, float)), np.log(eps), 1))
        fit = {"A": math.exp(inter), "beta": beta,
               "eps_by_n": {str(m): sizes[m]["eps_n"] for m in SIZES},
               "successive_ratios": {f"eps_{p}/eps_{q}": sizes[p]["eps_n"] / sizes[q]["eps_n"]
                                     for p, q in zip(SIZES[:-1], SIZES[1:])}}
    else:
        fit = {"A": None, "beta": None}
    data["powerlaw_fit"] = fit
    ok_sizes = len(data["sizes"]) == len(SIZES)
    ok_pos = ok_sizes and all(sizes[m]["eps_n"] > 0 and sizes[m]["min_eig"] > 0 for m in SIZES)
    e4096 = sizes.get(4096, {}).get("eps_n")
    ok_eps = e4096 is not None and 0.0 < e4096 < GATE_EPS_4096_MAX
    ok_beta = fit.get("beta") is not None and abs(fit["beta"]) > GATE_ABS_BETA_MIN
    data["gate_pass"] = bool(ok_sizes and ok_pos and ok_eps and ok_beta and st["ok"])
    OUT_PATH.write_text(json.dumps(data, indent=2))
    return data

def gate(log):
    data = run(log)
    sizes = {e["n"]: e for e in data.get("sizes", [])}
    fit = data.get("powerlaw_fit", {})
    st = data.get("selftest", {})
    print("\n" + "=" * 78)
    print("RT3-NB-4K results:")
    for n in SIZES:
        e = sizes.get(n, {})
        cond = e.get("cond")
        cond_s = f"{cond:.3e}" if cond is not None else "inf"
        print(f"  n={n:5d}  eps_n={e.get('eps_n', float('nan')):.6f}"
              f"  cond={cond_s}  [{e.get('seconds', 0):.1f}s]")
    beta = fit.get("beta")
    if beta is not None:
        print(f"  power law: eps_n ~ {fit['A']:.4f} * n^{beta:.4f}")
    print("-" * 78)
    e4096 = sizes.get(4096, {}).get("eps_n")
    ok_eps = e4096 is not None and 0.0 < e4096 < GATE_EPS_4096_MAX
    ok_beta = beta is not None and abs(beta) > GATE_ABS_BETA_MIN
    ok_sizes = all(n in sizes and sizes[n].get("complete") for n in SIZES)
    ok_pos = ok_sizes and all(sizes[n]["eps_n"] > 0 and sizes[n]["min_eig"] > 0 for n in SIZES)
    passed = ok_sizes and ok_pos and ok_eps and ok_beta and bool(st.get("ok"))
    print(f"GATE: eps_4096={e4096} < {GATE_EPS_4096_MAX}: {ok_eps}"
          f"  |beta|={abs(beta) if beta else None} > {GATE_ABS_BETA_MIN}: {ok_beta}")
    print("GATE:", "PASS" if passed else "FAIL")
    print("=" * 78)
    return 0 if passed else 1

def main():
    import argparse
    ap = argparse.ArgumentParser(description="RT3-NB-4K: Nyman-Beurling at n=2048,4096")
    ap.add_argument("--gate", action="store_true")
    args = ap.parse_args()
    if args.gate:
        return gate(print)
    run(print)
    return 0

if __name__ == "__main__":
    sys.exit(main())
