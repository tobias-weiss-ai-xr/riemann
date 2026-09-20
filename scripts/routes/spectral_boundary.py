#!/usr/bin/env python
"""RT2-D -- spectral-radius boundary map t*(sigma) with certified brackets (S3, ROUTES2_FLEET_PLAN.md).

Round 1 (RT-D) found rho(L_sigma(it)) >= 1 at t=0 for all sigma, rho < 1 at
t=50 for all sigma, but rho ~ 1.04 >= 1 again at sigma=0.51, t=100: the
boundary is NON-MONOTONE in t. This script maps it.

Phase 1 (float64 scan): rho_float(t) on t = 0..100 step 5 for sigma in
{0.75, 0.70, 0.65, 0.60, 0.55, 0.51} via nystrom_collocation.nystrom_matrix_vec
(n=24, nmax=500) + np.linalg.eigvals. Approximate crossings of rho_float = 1
are located by sign change between adjacent grid points + linear interpolation.

Phase 2 (certified brackets): each crossing is bracketed by certifying
individual integer t with the round-1 mpmath machinery
(certified_spectral_radius.assemble_matrix + certified_rho_bounds, dps=25,
||A^m||_inf^{1/m} * (1+REL_INFLATE)). The float crossing is first refined at
integer resolution (cheap float64), then the adjacent straddling pair is
certified; if bound looseness prevents a straddle, the walk continues outward
in steps of 1.0 (max 4 certified probes per crossing, max 3 crossings per
sigma) until two ADJACENT integers are certified on opposite sides of 1.
NOTE: the first crossing of every sigma is steeper than one integer step
(rho drops from > 2 at t=0 to < 0.7 at t=1), so its certified bracket is
(0, 1) -- the walk must be able to certify the scan endpoints as well.

Bracket naming (gate criterion (c)): t_lo is the side certified cert_ub < 1,
t_hi the side certified cert_ub >= 1 -- NOT numeric order. `orientation`
records the numeric direction: "downward" = rho crosses 1 from above as t
increases (first crossing of every sigma, since lambda_1(sigma) > 1 at t=0),
"upward" = re-crossing from below (the non-monotone sigma=0.51 case).
Crossings that cannot be bracketed within budget are recorded verbatim with
all raw probes (honest result, gate fails per plan).

Output: data/routes/rt_boundary.json
Gate (--gate): exit 0 iff (a) float64 scan done for all 6 sigma (21 t each),
(b) at least one certified (bracketed) crossing per sigma, (c) every reported
bracket has cert_lo < 1 <= cert_hi.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # scripts/ -> nystrom_collocation
from nystrom_collocation import nystrom_matrix_vec
from certified_spectral_radius import (  # round-1 module: READ-ONLY reuse
    assemble_matrix, certified_rho_bounds, REL_INFLATE, DPS, N_NODES, NMAX)

SIGMAS = (0.75, 0.70, 0.65, 0.60, 0.55, 0.51)
T_MIN, T_MAX, T_STEP = 0, 100, 5
SCAN_TS = list(range(T_MIN, T_MAX + 1, T_STEP))
MAX_PROBES_PER_CROSSING = 4
MAX_CROSSINGS_PER_SIGMA = 3
OUT_PATH = Path("data/routes/rt_boundary.json")


# ---------------------------------------------------------------- computation

def scan_point(sigma, t):
    """float64 spectral radius of the Nystrom matrix at s = sigma + i*t."""
    A = nystrom_matrix_vec(complex(sigma, t), N_NODES, NMAX)
    return float(np.max(np.abs(np.linalg.eigvals(A))))


def cert_probe(sigma, t):
    """Certified rho upper bound at one point (round-1 mpmath machinery)."""
    t0 = time.time()
    A, _ = assemble_matrix(sigma, t, N_NODES, NMAX)
    cert_ub, best_m, raw = certified_rho_bounds(A)
    rho_f = scan_point(sigma, t)
    rec = {"sigma": sigma, "t": t, "cert_ub": float(cert_ub), "power_raw": float(raw),
           "m_best": best_m, "rho_float": rho_f,
           "xc_ok": bool(rho_f <= float(cert_ub) + 1e-6),
           "elapsed_s": round(time.time() - t0, 1)}
    if not rec["xc_ok"]:
        print(f"  !! CROSS-CHECK FAIL sigma={sigma} t={t}: rho_float={rho_f} > "
              f"cert_ub={float(cert_ub)} (recorded verbatim)")
    return rec


# ----------------------------------------------------------- pure logic (tested)

def crossings_from_scan(row):
    """Adjacent scan pairs where sign of rho_float - 1 flips.
    Returns list of (t_a, t_b, t_star) with t_star linearly interpolated."""
    out = []
    vals = [(p["t"], p["rho_float"]) for p in row]
    for (ta, ra), (tb, rb) in zip(vals, vals[1:]):
        if (ra - 1.0) * (rb - 1.0) < 0.0:
            t_star = ta + (1.0 - ra) * (tb - ta) / (rb - ra)
            out.append((ta, tb, t_star))
    return out


def find_straddle(by_t):
    """Adjacent certified integer pair straddling 1.
    Returns (t_lo, t_hi, orientation) with cert(t_lo) < 1 <= cert(t_hi);
    orientation 'up' if rho crosses 1 upward with increasing t, else 'down'."""
    for t in sorted(by_t):
        if t + 1 not in by_t:
            continue
        a, b = by_t[t], by_t[t + 1]
        if a < 1.0 <= b:
            return t, t + 1, "up"
        if b < 1.0 <= a:
            return t + 1, t, "down"
    return None


def walk_order(prof, t_star):
    """Certified-probe order for one crossing. `prof` maps integer t ->
    rho_float on the full crossing interval [t_a, t_b]. Order: the adjacent
    integer pair where rho_float itself straddles 1 (nearest t_star) first,
    then the remaining integers as outward rings from that pair (steps of 1.0
    keep certifications adjacent, which find_straddle needs)."""
    flips = [u for u in sorted(prof) if u + 1 in prof
             and (prof[u] - 1.0) * (prof[u + 1] - 1.0) < 0.0]
    if not flips:
        # no integer-resolution float crossing (sub-integer wiggle):
        # gather info nearest t_star first
        return sorted(prof, key=lambda t: (abs(t - t_star), t))
    u = min(flips, key=lambda v: abs(v + 0.5 - t_star))
    rest = [t for t in sorted(prof) if t != u and t != u + 1]
    rest.sort(key=lambda t: (u - t) if t < u else (t - (u + 1)))
    return [u, u + 1] + rest


# ------------------------------------------------------------------- pipeline

def bracket_crossing(sigma, t_a, t_b, t_star, rho_a, rho_b, probes, save, force):
    """Certify integers around the crossing until two ADJACENT ones are
    certified on opposite sides of 1 (or the probe budget is spent).
    Probes are cached in `probes` (keyed (sigma, t)); `save` checkpoints."""
    # cheap integer-resolution refinement of the float crossing (raw data kept)
    refine = [{"t": t, "rho_float": scan_point(sigma, t)} for t in range(t_a + 1, t_b)]
    prof = {t_a: rho_a, t_b: rho_b}
    prof.update({r["t"]: r["rho_float"] for r in refine})
    order = walk_order(prof, t_star)[:MAX_PROBES_PER_CROSSING]
    rec_probes = []
    straddle = None
    for t in order:
        rec = None if force else probes.get((sigma, t))
        if rec is None:
            rec = cert_probe(sigma, t)
            probes[(sigma, t)] = rec
            save()
        rec_probes.append(rec)
        print(f"    probe t={t}: cert_ub={rec['cert_ub']:.6f} "
              f"(rho_f64={rec['rho_float']:.6f}, m={rec['m_best']}, {rec['elapsed_s']}s)")
        straddle = find_straddle({r["t"]: r["cert_ub"] for r in rec_probes})
        if straddle:
            break
    flips = [u for u in sorted(prof) if u + 1 in prof
             and (prof[u] - 1.0) * (prof[u + 1] - 1.0) < 0.0]
    out = {"t_a": t_a, "t_b": t_b, "rho_a": rho_a, "rho_b": rho_b,
           "t_star_float": t_star, "float_refine": refine,
           "float_flip_pair": [flips[0], flips[0] + 1] if flips else None,
           "probes": rec_probes, "bracketed": straddle is not None}
    if straddle:
        t_lo, t_hi, orient = straddle
        by_t = {r["t"]: r["cert_ub"] for r in rec_probes}
        out.update(t_lo=t_lo, cert_lo=by_t[t_lo], t_hi=t_hi, cert_hi=by_t[t_hi],
                   orientation=orient)
    else:
        out.update(t_lo=None, cert_lo=None, t_hi=None, cert_hi=None, orientation=None)
        print(f"    !! UNBRACKETED crossing sigma={sigma} in ({t_a},{t_b}): "
              f"raw certs recorded verbatim")
    return out


def run(force=False):
    state = _load()
    probes = {(p["sigma"], p["t"]): p for p in state.get("certified_probes", [])}
    scan = state.setdefault("scan", {})

    def save():
        state["scan"] = scan
        state["certified_probes"] = sorted(probes.values(), key=lambda p: (p["sigma"], p["t"]))
        _write(state, gate_pass=None)

    # phase 1: float64 scan (cached per point; checkpoint after each sigma)
    print(f"Phase 1: float64 scan, {len(SIGMAS)} sigma x {len(SCAN_TS)} t "
          f"(n={N_NODES}, nmax={NMAX})")
    for sigma in SIGMAS:
        key = f"{sigma:.2f}"
        cached = {} if force else {p["t"]: p["rho_float"] for p in scan.get(key, [])}
        row = []
        for t in SCAN_TS:
            rho = cached[t] if t in cached else scan_point(sigma, t)
            row.append({"t": t, "rho_float": rho})
        scan[key] = row
        save()
        marks = " ".join((">" if p["rho_float"] >= 1 else "<") + f"{p['rho_float']:.3f}"
                         for p in row)
        print(f"  sigma={sigma}: {marks}")

    # phase 2: certified brackets (probes cached; checkpoint after each probe)
    print(f"Phase 2: certified brackets (dps={DPS}, max {MAX_PROBES_PER_CROSSING} probes/"
          f"crossing, max {MAX_CROSSINGS_PER_SIGMA} crossings/sigma)")
    crossings = {}
    for sigma in SIGMAS:
        key = f"{sigma:.2f}"
        row = scan[key]
        found = crossings_from_scan(row)
        if len(found) > MAX_CROSSINGS_PER_SIGMA:
            print(f"  sigma={sigma}: {len(found)} crossings detected, processing first "
                  f"{MAX_CROSSINGS_PER_SIGMA} (plan budget cap)")
        recs = []
        for ta, tb, t_star in found[:MAX_CROSSINGS_PER_SIGMA]:
            ra = next(p["rho_float"] for p in row if p["t"] == ta)
            rb = next(p["rho_float"] for p in row if p["t"] == tb)
            print(f"  sigma={sigma}: crossing t={ta}..{tb} "
                  f"(rho {ra:.4f} -> {rb:.4f}, t*~{t_star:.2f})")
            recs.append(bracket_crossing(sigma, ta, tb, t_star, ra, rb,
                                         probes, save, force))
        crossings[key] = recs

    state["crossings"] = crossings
    ok, _ = validate(state)
    state["gate_pass"] = ok
    _write(state, gate_pass=ok)
    print(f"gate_pass={ok} (run validation; see --gate for full report)")
    return state


# -------------------------------------------------------------------- output

def _load():
    if OUT_PATH.exists():
        try:
            return json.loads(OUT_PATH.read_text())
        except Exception:
            pass
    return {"task": "RT2-D",
            "method": "float64 Nystrom scan (n=24, nmax=500) + certified brackets "
                      "via mpmath ||A^m||_inf^{1/m} (dps=25, round-1 machinery)",
            "params": {"sigmas": list(SIGMAS), "t_min": T_MIN, "t_max": T_MAX,
                       "t_step": T_STEP, "n_nodes": N_NODES, "nmax": NMAX,
                       "dps": DPS, "rel_inflate": REL_INFLATE,
                       "max_probes_per_crossing": MAX_PROBES_PER_CROSSING,
                       "max_crossings_per_sigma": MAX_CROSSINGS_PER_SIGMA},
            "scan": {}, "certified_probes": [], "crossings": [], "gate_pass": None}


def _write(state, gate_pass):
    state["gate_pass"] = gate_pass
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(state, indent=2))


def validate(data):
    """Gate criteria (a)-(c). Returns (ok, list_of_failures)."""
    fails = []
    scan = data.get("scan", {})
    for sigma in SIGMAS:
        row = scan.get(f"{sigma:.2f}", [])
        if [p["t"] for p in row] != SCAN_TS:
            fails.append(f"(a) scan incomplete for sigma={sigma}: {len(row)}/{len(SCAN_TS)} points")
    crossings = data.get("crossings", {})
    for sigma in SIGMAS:
        crs = crossings.get(f"{sigma:.2f}", [])
        if not any(c.get("bracketed") for c in crs):
            fails.append(f"(b) no certified crossing for sigma={sigma}")
    for sigma, crs in crossings.items():
        for c in crs:
            if c.get("bracketed") and not (c["cert_lo"] < 1.0 <= c["cert_hi"]):
                fails.append(f"(c) bad bracket sigma={sigma} ({c['t_a']}..{c['t_b']}): "
                             f"cert_lo={c['cert_lo']} cert_hi={c['cert_hi']}")
    return (not fails), fails


def gate():
    if not OUT_PATH.exists():
        print("GATE FAIL: no output file")
        return 1
    data = json.loads(OUT_PATH.read_text())
    ok, fails = validate(data)
    print(f"\n{'sigma':>6}  {'crossing':>12} {'orient':>8} {'t_lo':>5} {'cert_lo':>9} "
          f"{'t_hi':>5} {'cert_hi':>9}  bracketed")
    for sigma in SIGMAS:
        crs = data.get("crossings", {}).get(f"{sigma:.2f}", [])
        if not crs:
            print(f"{sigma:>6.2f}  (no crossings detected)")
        for c in crs:
            if c["bracketed"]:
                print(f"{sigma:>6.2f}  {c['t_a']:>5}..{c['t_b']:<6} {c['orientation']:>8} "
                      f"{c['t_lo']:>5} {c['cert_lo']:>9.6f} {c['t_hi']:>5} "
                      f"{c['cert_hi']:>9.6f}  True")
            else:
                print(f"{sigma:>6.2f}  {c['t_a']:>5}..{c['t_b']:<6} {'--':>8} "
                      f"{'--':>5} {'--':>9} {'--':>5} {'--':>9}  False (raw probes kept)")
    if not ok:
        print("\nGATE FAIL:")
        for f in fails:
            print(f"  {f}")
        return 1
    print(f"\nGATE PASS: scan complete for {len(SIGMAS)} sigma; "
          f"every sigma has >= 1 certified crossing; all brackets satisfy "
          f"cert_lo < 1 <= cert_hi")
    return 0


# ------------------------------------------------------------------ selfcheck

def _selftest():
    """Pure-logic checks (no computation)."""
    row = [{"t": 0, "rho_float": 1.9}, {"t": 5, "rho_float": 0.9},
           {"t": 10, "rho_float": 1.1}]
    cr = crossings_from_scan(row)
    assert len(cr) == 2 and cr[0][:2] == (0, 5) and cr[1][:2] == (5, 10)
    assert abs(cr[0][2] - 4.5) < 1e-12          # linear interpolation
    assert abs(cr[1][2] - 7.5) < 1e-12
    assert crossings_from_scan([{"t": 0, "rho_float": 1.2},
                                {"t": 5, "rho_float": 1.1}]) == []
    assert find_straddle({2: 1.02, 3: 0.98}) == (3, 2, "down")
    assert find_straddle({2: 0.98, 3: 1.02}) == (2, 3, "up")
    assert find_straddle({2: 0.98, 3: 0.99, 4: 0.97}) is None
    assert find_straddle({1: 1.2, 2: 1.02, 3: 0.98}) == (3, 2, "down")
    assert find_straddle({2: 1.0, 3: 0.999}) == (3, 2, "down")   # cert == 1 counts as >= 1
    # walk_order: steep first crossing -> straddling pair (0,1) probed first
    prof = {0: 2.04, 1: 0.64, 2: 0.40, 3: 0.32, 4: 0.30, 5: 0.34}
    assert walk_order(prof, 3.06)[:2] == [0, 1]
    # walk_order: outward rings stay adjacent to the pair
    prof = {40: 0.95, 41: 0.94, 42: 0.88, 43: 0.85, 44: 0.94, 45: 1.005}
    assert walk_order(prof, 44.5) == [44, 45, 43, 42, 41, 40]
    # walk_order: no integer flip -> nearest t_star first
    prof = {0: 1.1, 1: 0.9, 2: 0.95, 3: 1.05, 4: 1.1, 5: 1.2}
    assert walk_order(prof, 2.5) == [2, 3, 1, 4, 0, 5]
    print("selftest PASS")
    return 0


def main():
    ap = argparse.ArgumentParser(description="RT2-D spectral-radius boundary map")
    ap.add_argument("--gate", action="store_true", help="run computation + validate")
    ap.add_argument("--force", action="store_true", help="recompute everything")
    ap.add_argument("--selftest", action="store_true", help="pure-logic checks only")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(_selftest())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    run(force=args.force)
    if args.gate:
        sys.exit(gate())


if __name__ == "__main__":
    main()
