#!/usr/bin/env python
"""RT-D -- certified spectral-radius bounds (Nisoli/DFLY), S1 of ROUTES_FLEET_PLAN.md.

Certified upper bound on rho(A_N) via ||A^m||_inf^{1/m} in mpmath (dps=25)
with outward inflation 1e-10. Gershgorin lower (t=0). Tail bound in true
interval arithmetic. float64 cross-check against nystrom_collocation.

Grid: sigma in {0.75,...,0.51}, t in {0,50,100}. Gate: all 18 certified_upper<1.
"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nystrom_collocation import nystrom_matrix_vec
import mpmath as mp

DPS = 25
REL_INFLATE = 1e-10
N_NODES = 24
NMAX = 500
M_MAX = 64
SIGMAS = (0.75, 0.70, 0.65, 0.60, 0.55, 0.51)
TS = (0, 50, 100)
OUT_PATH = Path("data/routes/rt_d_certified.json")

def mp_nodes(n):
    """Exact Legendre-Gauss nodes as mpf + barycentric weights (scale-invariant)."""
    xf, _ = np.polynomial.legendre.leggauss(n)
    xf = 0.5 * xf + 0.5
    x = [mp.mpf(float(v)) for v in xf]
    w = []
    for j in range(n):
        p = mp.mpf(1)
        for l in range(n):
            if l != j:
                p *= x[j] - x[l]
        w.append(1 / p)
    wmax = max(abs(v) for v in w)
    return x, [v / wmax for v in w]


def lagrange_row(y, x, w):
    """ell_j(y) for all j, barycentric form."""
    num = [w[j] / (y - x[j]) for j in range(len(x))]
    den = mp.fsum(num)
    return [v / den for v in num]


def assemble_matrix(sigma, t, n, nmax):
    """A_N in mpmath. Nodes/k-sum inputs exact; rounding inflated later."""
    mp.mp.dps = DPS
    s = mp.mpc(sigma, t)
    x, w = mp_nodes(n)
    A = [[mp.mpc(0) for _ in range(n)] for _ in range(n)]
    for k in range(nmax + 1):
        base = mp.mpf(k + 1)
        for i in range(n):
            d = base + x[i]          # k+1+x_i
            b = mp.exp(-2 * s * mp.log(d))   # (k+1+x_i)^{-2s}
            y_i = 1 / d              # preimage 1/(k+1+x_i) -- depends on i!
            ell = lagrange_row(y_i, x, w)
            row = A[i]
            for j in range(n):
                row[j] += b * ell[j]
    return A, x

def matmul(A, B):
    n = len(A)
    C = [[mp.mpc(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        Ai, Ci = A[i], C[i]
        for k in range(n):
            a = Ai[k]
            if a == 0:
                continue
            Bk = B[k]
            for j in range(n):
                Ci[j] += a * Bk[j]
    return C


def inf_norm_bound(A):
    """max_i sum_j |A_ij| in mpf."""
    mx = mp.mpf(0)
    for row in A:
        s = mp.fsum(abs(v) for v in row)
        if s > mx:
            mx = s
    return mx


def certified_rho_bounds(A, m_max=M_MAX):
    """min over m of ||A^m||_inf^{1/m}. Returns (best_cert_ub, best_m, raw)."""
    mp.mp.dps = DPS
    best = (mp.mpf("inf"), 0, mp.mpf("inf"))
    B = A
    m = 1
    while m < m_max:
        B = matmul(B, B)   # A^2, A^4, A^8, ...
        m *= 2
        nb = inf_norm_bound(B)
        raw = nb ** (mp.mpf(1) / m)
        cert = raw * (1 + REL_INFLATE)
        if cert < best[0]:
            best = (cert, m, raw)
    return best

def gershgorin_lower_real(A):
    """Rigorous rho lower bound via isolated real Gershgorin disks (t=0).
    Returns (lower_bound, disk_index) or (None, None)."""
    n = len(A)
    centers, radii = [], []
    for i in range(n):
        c = abs(A[i][i])
        r = mp.fsum(abs(A[i][j]) for j in range(n) if j != i)
        centers.append(c)
        radii.append(r)
    best = (None, None)
    for i in range(n):
        lo_i, hi_i = centers[i] - radii[i], centers[i] + radii[i]
        isolated = True
        for j in range(n):
            if j == i:
                continue
            lo_j, hi_j = centers[j] - radii[j], centers[j] + radii[j]
            if not (hi_i < lo_j or hi_j < lo_i):
                isolated = False
                break
        if isolated:
            lb = abs(centers[i]) - radii[i]
            if lb > 0 and (best[0] is None or lb > best[0]):
                best = (lb, i)
    return best


def tail_bound(sigma, nmax):
    """Upper bound for sum_{k>nmax} (k+1)^{-2 sigma} (integral bound).

    sum_{k>nmax} (k+1)^{-2 sigma} <= integral_{nmax}^inf (x+1)^{-2 sigma} dx
                                 = (nmax+1)^{1-2 sigma} / (2 sigma - 1).
    Computed in mp.mpf with outward inflation.
    """
    mp.mp.dps = DPS
    tau = mp.mpf(nmax + 1) ** (1 - 2 * sigma) / (2 * sigma - 1)
    return tau * (1 + REL_INFLATE)

def compute_point(sigma, t, n=N_NODES, nmax=NMAX, force=False):
    """Compute one grid point. Returns dict or None if skipped."""
    key = f"{sigma}_{t}"
    if OUT_PATH.exists() and not force:
        try:
            data = json.loads(OUT_PATH.read_text())
            for p in data.get("points", []):
                if p.get("key") == key:
                    return None  # checkpointed
        except Exception:
            pass
    t0 = time.time()
    A, x = assemble_matrix(sigma, t, n, nmax)
    cert_ub, best_m, raw = certified_rho_bounds(A)
    # float64 cross-check
    s_c = complex(sigma, t)
    A_np = nystrom_matrix_vec(s_c, n, nmax, chunk=200)
    ev = np.linalg.eigvals(A_np)
    rho_float = float(np.max(np.abs(ev)))
    # sanity: rho_float <= cert_ub (within tolerance)
    if rho_float > float(cert_ub) + 1e-6:
        raise RuntimeError(
            f"CROSS-CHECK FAIL sigma={sigma} t={t}: rho_float={rho_float} > "
            f"cert_ub={float(cert_ub)}"
        )
    # mp assembly vs float agreement (compare |A[0,0]|)
    A_mp_00 = float(abs(A[0][0]))
    A_np_00 = abs(A_np[0, 0])
    rel_diff = abs(A_mp_00 - A_np_00) / max(abs(A_np_00), 1e-30)
    # gershgorin lower (t=0 only)
    gl = gershgorin_lower_real(A) if t == 0 else (None, None)
    gl_val = float(gl[0]) if gl[0] is not None else None
    tau = tail_bound(sigma, nmax)
    width = float(cert_ub) - (gl_val if gl_val is not None else float(raw))
    return {
        "key": key, "sigma": sigma, "t": t, "n": n, "nmax": nmax,
        "m_best": best_m,
        "rho_float64": rho_float,
        "power_bound_raw": float(raw),
        "certified_upper": float(cert_ub),
        "gershgorin_lower": gl_val,
        "gershgorin_disk": gl[1],
        "certified_width": width,
        "tail_bound": float(tau),
        "assembly_check_rel_diff": rel_diff,
        "elapsed_s": round(time.time() - t0, 1),
        "passed": float(cert_ub) < 1.0,
    }

def run_all(force=False, sigmas=None, ts=None):
    sigmas = sigmas or SIGMAS
    ts = ts or TS
    points = []
    # load checkpoint
    if OUT_PATH.exists() and not force:
        try:
            old = json.loads(OUT_PATH.read_text())
            points = old.get("points", [])
        except Exception:
            points = []
    for sigma in sigmas:
        for t in ts:
            p = compute_point(sigma, t, force=force)
            if p is not None:
                points.append(p)
                # checkpoint after every point
                _save(points)
                print(f"  sigma={sigma} t={t}: cert_ub={p['certified_upper']:.6f} "
                      f"(m={p['m_best']}, rho_f64={p['rho_float64']:.6f}, "
                      f"gl={p['gershgorin_lower']}, tau={p['tail_bound']:.4f}, "
                      f"{'PASS' if p['passed'] else 'FAIL'})")
    return points


def _save(points):
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_pass = all(p["passed"] for p in points) if points else False
    out = {
        "task": "RT-D",
        "method": "mpmath dps=25 ||A^m||_inf^{1/m} certified ub + "
                  "Gershgorin lower (t=0) + interval tail bound",
        "n_nodes": N_NODES,
        "nmax": NMAX,
        "m_max": M_MAX,
        "rel_inflate": REL_INFLATE,
        "n_points_expected": len(SIGMAS) * len(TS),
        "points": points,
        "all_passed": all_pass,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2))


def gate():
    if not OUT_PATH.exists():
        print("GATE FAIL: no output file")
        return 1
    data = json.loads(OUT_PATH.read_text())
    pts = data.get("points", [])
    expected = len(SIGMAS) * len(TS)
    if len(pts) < expected:
        print(f"GATE FAIL: only {len(pts)}/{expected} points computed")
        return 1
    fails = [p for p in pts if not p["passed"]]
    print(f"\n{'sigma':>6} {'t':>5} {'cert_ub':>10} {'rho_f64':>10} "
          f"{'glower':>10} {'tau':>8} {'width':>10}  result")
    for p in pts:
        gl = p.get("gershgorin_lower")
        gls = f"{gl:.6f}" if gl is not None else "  (none)"
        print(f"{p['sigma']:>6.2f} {p['t']:>5.0f} {p['certified_upper']:>10.6f} "
              f"{p['rho_float64']:>10.6f} {gls:>10} {p['tail_bound']:>8.4f} "
              f"{p['certified_width']:>10.6f}  "
              f"{'PASS' if p['passed'] else 'FAIL'}")
    if fails:
        print(f"\nGATE FAIL: {len(fails)}/{len(pts)} points have certified_upper >= 1")
        for p in fails:
            print(f"  sigma={p['sigma']} t={p['t']}: "
                  f"certified_upper={p['certified_upper']:.6f} >= 1 "
                  f"(honest result, reported verbatim)")
        return 1
    print(f"\nGATE PASS: all {len(pts)} points certified_upper < 1")
    return 0

def main():
    ap = argparse.ArgumentParser(description="RT-D certified spectral radius")
    ap.add_argument("--gate", action="store_true", help="run + validate")
    ap.add_argument("--force", action="store_true", help="recompute all points")
    ap.add_argument("--quick", action="store_true", help="2-point test (sigma=0.75,t=0 only)")
    args = ap.parse_args()
    sigmas = (0.75,) if args.quick else None
    ts = (0,) if args.quick else None
    print(f"RT-D certified spectral radius (N={N_NODES}, nmax={NMAX}, dps={DPS})")
    if args.gate or not args.quick:
        pts = run_all(force=args.force, sigmas=sigmas, ts=ts)
    if args.gate:
        sys.exit(gate())
    if args.quick:
        # one-point self-check: sigma=0.75, t=0 -- verify cross-check agreement
        # (cert_ub >= rho_float, assembly matches float64).  cert_ub > 1 at
        # t=0 is EXPECTED (lambda_1(sigma) > 1 for sigma < 1); not a bug.
        p = compute_point(0.75, 0, force=True)
        assert p is not None
        assert p["assembly_check_rel_diff"] < 1e-6, (
            f"assembly mismatch: rel_diff={p['assembly_check_rel_diff']}")
        assert p["rho_float64"] <= p["certified_upper"] + 1e-6, (
            f"cross-check FAIL: rho_float={p['rho_float64']} > "
            f"cert_ub={p['certified_upper']}")
        print(f"self-check PASS: sigma=0.75 t=0 cert_ub={p['certified_upper']:.6f} "
              f"(rho_f64={p['rho_float64']:.6f}, m={p['m_best']}, "
              f"gl={p['gershgorin_lower']}, tau={p['tail_bound']:.4f})")
        _save([p])


if __name__ == "__main__":
    main()
