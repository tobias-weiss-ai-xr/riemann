#!/usr/bin/env python
"""RT-NB-16K: Nyman-Beurling density at n=16384 via a fast O(n^3) assembler.

The RT2-NB/RT3-NB-4K assembler accumulates G += (F*w).T @ F over ~c^2 ~ 43M
pieces x n=16384 columns: O(pieces*n^2) ~ 5e15 flops ~ 40 h.  This script
replaces the G accumulation by an exact Abel summation of the floor-structured
basis.  On piece p the value a_p(k) = floor(k*u_p/c) is constant, so with
F_{p,k} = kc_k*fl_p - a_p(k) (kc_k = k/c, fl_p = floor(u_p)):

    G_ij = kc_i kc_j A - kc_j B_i - kc_i B_j + C_ij,
    A  = sum_p w_p fl_p^2,   B_k = sum_p w_p fl_p a_p(k)  (threaded, O(pieces*n)),
    C_ij = (1/(2c)) [4 i j psi(1+1/(2c)) - K(i,j) - K(j,i) + h(gcd(i,j))],
    K(i,j) = sum_{m=1}^{2i} floor(j*m/i) psi(m/(2i)),
    h(g)   = sum_{t=1}^{2g} psi(t/(2g)),

derived by telescoping sum_p f_p (Psi_{p+1} - Psi_p) = f_{M-1} Psi_M - f_0 Psi_0
+ sum_{p=1}^{M-1} (f_{p-1} - f_p) Psi_p over the one-period breakpoint list:
jumps of floor(i u/c) live at u = m c/i (m = 1..2i), coinciding breakpoints
(u = t c/g, t = 1..2g, g = gcd(i,j)) contribute the +h correction, f on the
last piece equals 4ij and f(1) = 0.  K costs O(n^3) ~ 5 min threaded at n=16384.

Threading: numpy ufuncs and BLAS release the GIL; chunk/row tasks use
ThreadPoolExecutor in bounded waves (16 of 32 cores).

Verification: fast assembler vs the original nbe.assemble at n=12,64,256 and
nbe.selftest (round-1 oracle) after patching.  Output: data/routes/rt_nb_16k.json
Gate: eps_16384 in (0, 0.001), |beta| over the 10 sizes 16..16384 > 0.3.
"""
from __future__ import annotations
import json, math, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from scipy.special import digamma

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nyman_beurling_ext as nbe  # round-1/2/3 machinery

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_nb_16k.json"
CKPT = Path(__file__).resolve().parents[2] / "data" / "routes"
N16K = 16384
NTHREADS = 12  # ponytail: 16 of 32 cores; memory caps in-flight temporaries
GATE_EPS_16384_MAX = 0.001
GATE_ABS_BETA_MIN = 0.3

orig_assemble = nbe.assemble  # keep the O(pieces*n^2) reference for --verify


def fast_assemble(n: int, log=print) -> dict:
    """Same interface as nbe.assemble: exact G, b, b1, gtt via O(n^3) Abel summation."""
    c = n + 1
    P = 2 * c
    # ---- phase 1: one-period pieces + threaded O(pieces*n) accumulations ----
    parts = [np.arange(1.0, P + 2.0)]
    for k in range(1, c):
        parts.append(np.arange(1.0, int(((1.0 + P) * k) // c) + 2.0) * (c / k))
    u = np.concatenate(parts)
    del parts
    u = np.unique(u[(u >= 1.0) & (u <= 1.0 + P)])
    mids = 0.5 * (u[1:] + u[:-1])
    w = (digamma(u[1:] / P) - digamma(u[:-1] / P)) / P
    del u
    sumw = float(w.sum())
    npieces = int(mids.size)
    p1 = CKPT / f"_nb16k_phase1_{n}.npz"

    kvec = np.arange(1.0, c)
    kc = kvec / c
    fl = np.floor(mids)
    fr = mids - fl
    tgt = 0.5 * fl - np.floor(0.5 * fl + 0.5 * fr)

    if p1.exists():
        z = np.load(p1)
        A = float(z["A"])
        B, b, b1 = z["B"], z["b"], z["b1"]
        gtt = float(z["gtt"])
        log(f"phase1: loaded checkpoint ({npieces} pieces, A={A:.4f})")
    else:
        gtt = float(np.dot(w, tgt * tgt))
        A = 0.0
        Bacc = np.zeros(n)
        b = np.zeros(n)   # final b = sum_p w_p tgt_p F_{p,k} (direct, as nbe loop)
        b1 = np.zeros(n)  # final b1 = sum_p w_p F_{p,k}
        chunk = max(1, (1 << 22) // n)
        bounds = [(s, min(s + chunk, npieces)) for s in range(0, npieces, chunk)]

        def p1_work(lohi):
            lo, hi = lohi
            fc, frc, wc, tg = fl[lo:hi], fr[lo:hi], w[lo:hi], tgt[lo:hi]
            num = np.multiply.outer(fc, kvec) + np.multiply.outer(frc, kvec)
            F = np.multiply.outer(fc, kc) - np.floor_divide(num, c)
            return (float(np.dot(wc, fc * fc)),
                    F.T @ (wc * fc), F.T @ (wc * tg), F.T @ wc)

        t0 = time.time()
        with ThreadPoolExecutor(NTHREADS) as ex:
            for s0 in range(0, len(bounds), 128):  # bounded wave: 128 x ~200KB
                for (a_, ba, bb, b1_) in ex.map(p1_work, bounds[s0:s0 + 128]):
                    A += a_
                    Bacc += ba
                    b += bb
                    b1 += b1_
        B = kc * A - Bacc   # B_k = sum_p w_p fl_p a_p(k) via a = kc*fc - F
        del Bacc
        np.savez(p1, A=A, B=B, b=b, b1=b1, gtt=gtt)
        log(f"phase1: pieces={npieces} A={A:.4f} gtt={gtt:.6f} "
            f"[{time.time() - t0:.1f}s]")
    del fl, fr, tgt, mids, w

    # ---- phase 2: K matrix, Kmat[i-1,j-1] = sum_m floor(j m/i) psi(m/(2i)) ----
    t1 = time.time()
    Kmat = np.empty((n, n))
    jall = np.arange(1.0, n + 1)
    jb = max(1, (1 << 22) // (2 * n))

    def k_work(i):
        m = np.arange(1.0, 2.0 * i + 1.0)
        v = digamma(m / (2.0 * i))
        mr = m / i
        row = np.empty(n)
        for s in range(0, n, jb):
            js = jall[s:s + jb]
            # +1e-9: when i | jm the float product lands ~2e-12 below the true
            # integer and floor is off by one; 1e-9 << min gap 1/i ~ 1.2e-4
            row[s:s + jb] = np.floor(np.multiply.outer(js, mr) + 1e-9) @ v
        return i, row

    with ThreadPoolExecutor(NTHREADS) as ex:
        for s0 in range(1, n + 1, 32):  # bounded wave: 32 x ~0.5MB rows
            for i, row in ex.map(k_work, range(s0, min(s0 + 32, n + 1))):
                Kmat[i - 1] = row
            if (s0 - 1) // 32 % 32 == 31:
                log(f"  K rows {s0 + 31}/{n} [{time.time() - t1:.0f}s]")
    log(f"phase2: Kmat done [{time.time() - t1:.1f}s]")

    # ---- phase 3: C -> G ----
    ivec = np.arange(1, n + 1)
    g = np.gcd.outer(ivec, ivec)
    h = np.empty(n)
    for g_ in range(1, n + 1):
        h[g_ - 1] = digamma(np.arange(1.0, 2.0 * g_ + 1.0) / (2.0 * g_)).sum()
    psi_end = float(digamma(1.0 + 1.0 / (2.0 * c)))
    Cmat = (4.0 * psi_end) * np.multiply.outer(ivec, jall)
    Cmat -= Kmat          # Kmat + Kmat.T, in place
    Cmat -= Kmat.T
    Cmat += h[g - 1]      # +h(gcd) correction (coinciding breakpoints)
    Cmat /= (2.0 * c)
    del g, h
    G = A * np.multiply.outer(kc, kc)
    G -= np.multiply.outer(kc, B)
    G -= np.multiply.outer(B, kc)
    G += Cmat
    del Cmat, Kmat
    return {"G": G, "b": b, "b1": b1, "gtt": gtt,
            "sumw": sumw, "npieces": npieces}


def verify(log) -> bool:
    """Fast vs original assembler at n=12,64,256; report max diffs and timing."""
    ok = True
    for n in (12, 64, 256):
        t0 = time.time()
        f = fast_assemble(n, lambda *_: None)
        tf = time.time() - t0
        t0 = time.time()
        o = orig_assemble(n)
        to = time.time() - t0
        dG = float(np.max(np.abs(f["G"] - o["G"])))
        db = float(np.max(np.abs(f["b"] - o["b"])))
        db1 = float(np.max(np.abs(f["b1"] - o["b1"])))
        dg = abs(f["gtt"] - o["gtt"])
        scale = max(1.0, float(np.max(np.abs(o["G"]))))
        this_ok = dG < 1e-9 * scale and db < 1e-9 and db1 < 1e-9 and dg < 1e-12
        ok &= this_ok
        log(f"n={n}: max|dG|={dG:.3e} max|db|={db:.3e} max|db1|={db1:.3e} "
            f"|dgtt|={dg:.1e}  fast={tf:.2f}s orig={to:.2f}s  "
            f"{'OK' if this_ok else 'FAIL'}")
    return ok


def run(log) -> dict:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if OUT_PATH.exists():
        try:
            data = json.loads(OUT_PATH.read_text())
        except json.JSONDecodeError:
            data = {}
    if not verify(log):
        log("!! VERIFICATION FAILED -- aborting before n=16384")
        data["verify_ok"] = False
        OUT_PATH.write_text(json.dumps(data, indent=2))
        return data
    data["verify_ok"] = True
    data["task"] = "RT-NB-16K"
    data["title"] = "Nyman-Beurling density at n=16384 (fast O(n^3) Abel assembler)"
    data["params"] = {
        "n": N16K,
        "assembler": "G_ij = kc_i kc_j A - kc_j B_i - kc_i B_j + C_ij, "
                     "C_ij = (4ij psi(1+1/2c) - K(i,j) - K(j,i) + h(gcd))/2c, "
                     "K(i,j) = sum_m floor(jm/i) psi(m/2i), O(n^3), threaded",
        "grid": "a_k = k/(n+1), k=1..n (as RT2-NB)",
        "gate": {"eps_16384_max": GATE_EPS_16384_MAX, "abs_beta_min": GATE_ABS_BETA_MIN},
    }
    nbe.assemble = fast_assemble  # nbe.compute/selftest now use the fast assembler
    st = nbe.selftest()
    data["selftest"] = st
    if not st["ok"]:
        log(f"!! SELFTEST FAILED: {json.dumps(st)}")
    if not (data.get("sizes") and data["sizes"][-1].get("n") == N16K
            and data["sizes"][-1].get("complete")):
        t0 = time.time()
        e = nbe.compute(N16K, log)
        data["sizes"] = [e]
        OUT_PATH.write_text(json.dumps(data, indent=2))
        log(f"n={N16K}: compute done [{time.time() - t0:.1f}s]")
    else:
        log(f"n={N16K}: cached, skipping")
    # power-law refit over all 10 sizes (9 from rt_nb_4k + this one)
    sizes = {e["n"]: e for e in data.get("sizes", [])}
    for prior in ("rt_nb_4k.json", "rt_nb_8k.json"):
        p = CKPT / prior
        if p.exists():
            for e in json.loads(p.read_text()).get("sizes", []):
                if e.get("complete"):
                    sizes[e["n"]] = e
    ns = sorted(sizes)
    eps = [sizes[m]["eps_n"] for m in ns]
    fit = {}
    if all(e > 0 for e in eps):
        beta, inter = (float(v) for v in
                       np.polyfit(np.log(np.array(ns, float)), np.log(eps), 1))
        fit = {"A": math.exp(inter), "beta": beta, "sizes": ns,
               "eps_by_n": {str(m): sizes[m]["eps_n"] for m in ns}}
    else:
        fit = {"A": None, "beta": None}
    data["powerlaw_fit"] = fit
    e8 = sizes.get(N16K, {}).get("eps_n")
    ok_pos = all(sizes[m]["eps_n"] > 0 and sizes[m]["min_eig"] > 0 for m in ns)
    ok_eps = e8 is not None and 0.0 < e8 < GATE_EPS_16384_MAX
    ok_beta = fit.get("beta") is not None and abs(fit["beta"]) > GATE_ABS_BETA_MIN
    data["gate_pass"] = bool(ok_pos and ok_eps and ok_beta and st["ok"])
    OUT_PATH.write_text(json.dumps(data, indent=2))
    for stale in CKPT.glob("_nb16k_phase1_*.npz"):
        stale.unlink()
    return data


def gate(log):
    data = run(log)
    if not data.get("verify_ok", False):
        return 1
    e8 = data["sizes"][-1]
    fit = data.get("powerlaw_fit", {})
    beta = fit.get("beta")
    print("\n" + "=" * 78)
    print("RT-NB-16K results:")
    print(f"  n=16384: pieces={e8['npieces']} min_eig={e8['min_eig']:.3e} "
          f"cond={e8['cond']:.3e} eps_n={e8['eps_n']:.8f} "
          f"({e8['eps_over_target_norm2']:.4%} of ||f||^2) [{e8['seconds']}s]")
    if beta is not None:
        print(f"  power law over {len(fit['sizes'])} sizes 16..16384: "
              f"eps_n ~ {fit['A']:.5f} * n^{beta:.4f}")
    ok_eps = 0.0 < e8["eps_n"] < GATE_EPS_16384_MAX
    ok_beta = beta is not None and abs(beta) > GATE_ABS_BETA_MIN
    print(f"GATE: eps_16384={e8['eps_n']} < {GATE_EPS_16384_MAX}: {ok_eps}"
          f"  |beta|={abs(beta) if beta else None} > {GATE_ABS_BETA_MIN}: {ok_beta}")
    print("GATE:", "PASS" if data.get("gate_pass") else "FAIL")
    print("=" * 78)
    return 0 if data.get("gate_pass") else 1


def main():
    import argparse
    ap = argparse.ArgumentParser(description="RT-NB-16K: Nyman-Beurling at n=16384")
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()
    if args.verify_only:
        return 0 if verify(print) else 1
    if args.gate:
        return gate(print)
    run(print)
    return 0


if __name__ == "__main__":
    sys.exit(main())
