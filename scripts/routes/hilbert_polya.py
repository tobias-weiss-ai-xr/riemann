#!/usr/bin/env python
"""RT-HP -- Hilbert-Polya prototype (Berry-Keating H = xp + GUE spacing test).

Implements section S5 of research/ROUTES_FLEET_PLAN.md.

Method
------
1. Berry-Keating Hamiltonian H = xp in self-adjoint (Weyl-ordered) form
   H = -i(x d/dx + 1/2) on (0, L], uniform grid x_j = j*h (j = 1..N,
   h = L/N), Dirichlet ghost points x_0 = x_{N+1} = 0. Hermitian stencil of
   -i(x d/dx + d/dx x)/2 (plan step 1):
       (H psi)_j = -i/(4h) [ (x_j + x_{j+1}) psi_{j+1}
                           - (x_j + x_{j-1}) psi_{j-1} ]
   The matrix is exactly Hermitian; its entries (2j+1)/4 are L-invariant,
   so the spectrum depends only on N (the uniform grid has fixed aspect
   ratio x_max/x_min = N). L is a harmless convention (L = 2*pi*e).
   (The naive non-symmetrized central difference -i(x_j D + 1/2) is NOT
   Hermitian -- the Weyl ordering above is what makes the matrix exact.)

2. Eigenvalues via numpy.linalg.eigvalsh (plan step 2). The continuum
   spectrum of xp on (0, inf) is all of R; the finite box + Dirichlet ghost
   points discretize it. Analytic reference: under t = log x the operator
   maps unitarily to -i d/dt on a box of width log(N) (picket-fence
   spectrum lambda_n ~ n*pi/log(N)). The FD x-grid distorts the smooth
   density (O(1) deviation), but the local level sequence stays rigid --
   see spectrum_structure in the output.

3. Nearest-neighbour spacing distribution (NNSD) + pair correlation of the
   bulk eigenvalues (central 80% of the positive branch). Two unfoldings
   are reported:
     - LOCAL (primary): each spacing normalized by a running mean over
       +/-25 neighbouring spacings; unfolded levels u = cumsum of the
       normalized spacings. This removes the smooth spectral drift.
     - GLOBAL (diagnostic): normalization by the window-mean spacing.
       The BK spectral density drifts by a factor ~5 across the window,
       which mimics GUE statistics; recorded verbatim as a warning that
       naive unfolding of a drifting spectrum fabricates a "GUE signal".
   References: GUE Wigner surmise
   p(s) = (32/pi^2) s^2 exp(-4 s^2/pi) and Poisson exp(-s); KS distances to
   both. Internal control: the same pipeline applied to the first 200 zeta
   zeros (unfolded analytically via Riemann-von Mangoldt) must come out
   GUE-like -- this validates the statistics code, not RH.

4. Truncated Connes trace formula (plan step 4): evaluate
   |zeta(1/2 + i*lambda_n)| for all positive lambda_n of the largest grid
   (mpmath, dps 30) and compare with a uniform random control of the same
   size in the same range. Metrics: min |zeta|, fractions below thresholds,
   mean log|zeta|, Pearson correlation of log|zeta| with the distance to
   the nearest true zeta-zero ordinate.

HONESTY RULE: every computed value is reported verbatim. The observed
outcome is a negative prototype result: after proper LOCAL unfolding the
naive BK finite-difference spectrum is a near-perfect picket fence
(spacing std ~1e-3 vs GUE 0.422), NOT GUE -- while naive global unfolding
mimics GUE (KS ~0.08). Both are recorded; the gate (plan step 5) requires
data, not GUE agreement.

Output: data/routes/rt_hp.json (checkpointed after each stage).
--gate: recompute-if-needed + validate, exit 0 on success.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import mpmath as mp
import numpy as np
from scipy.special import erf

GRIDS = [256, 512, 1024]
L_BOX = 2.0 * math.pi * math.e   # convention only; spectrum is L-invariant
K_ZEROS = 200                    # zeta zeros for the GUE control + Connes
ZERO_DPS = 40
ZETA_DPS = 30
SKIP_ZEROS = 10                  # drop first zeros from stats (unfold transient)
WINDOW_FRAC = 0.10               # central 80% of positive eigenvalues
UNFOLD_HALF = 25                 # running-mean unfolding half-width (spacings)
SPACING_EDGES = np.arange(0.0, 3.0 + 1e-9, 0.15)
PC_EDGES = np.arange(0.0, 3.0 + 1e-9, 0.10)
CONNES_GRID = 1024
CONNES_THRESHOLDS = [1.0, 0.5, 0.2, 0.1]
RNG_SEED = 0
OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "routes" / "rt_hp.json"


def log(msg: str) -> None:
    print(f"[rt-hp] {msg}", flush=True)


def save(data: dict) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=1))
    tmp.replace(OUT_PATH)


# ---------------------------------------------------------------- statistics

def gue_pdf(s: np.ndarray) -> np.ndarray:
    return (32.0 / np.pi ** 2) * s ** 2 * np.exp(-4.0 * s ** 2 / np.pi)


def gue_cdf(s: np.ndarray) -> np.ndarray:
    s = np.asarray(s, dtype=float)
    return erf(2.0 * s / math.sqrt(np.pi)) - (4.0 * s / np.pi) * np.exp(
        -4.0 * s ** 2 / np.pi)


def poisson_cdf(s: np.ndarray) -> np.ndarray:
    return 1.0 - np.exp(-np.asarray(s, dtype=float))


def ks_distance(samples: np.ndarray, cdf) -> float:
    x = np.sort(np.asarray(samples, dtype=float))
    n = x.size
    F = cdf(x)
    d_hi = float(np.max(np.arange(1, n + 1) / n - F))
    d_lo = float(np.max(F - np.arange(0, n) / n))
    return max(d_hi, d_lo)


def spacing_block(r: np.ndarray) -> dict:
    """NNSD of normalized spacings r (mean 1 by construction)."""
    counts, edges = np.histogram(r, bins=SPACING_EDGES)
    width = np.diff(edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    total = max(int(counts.sum()), 1)
    emp = counts / total / width
    l1_gue = float(np.abs(emp - gue_pdf(centers)).sum() * float(width.mean()))
    l1_poi = float(np.abs(emp - np.exp(-centers)).sum() * float(width.mean()))
    return {"n_spacings": int(r.size),
            "mean": float(r.mean()), "std": float(r.std()),
            "ks_gue": ks_distance(r, gue_cdf),
            "ks_poisson": ks_distance(r, poisson_cdf),
            "l1_gue": l1_gue, "l1_poisson": l1_poi,
            "histogram": {"bin_edges": [float(v) for v in edges],
                          "counts": [int(c) for c in counts]},
            "first_normalized_spacings": [float(v) for v in r[:20]]}


def pair_corr_block(u: np.ndarray) -> dict:
    """Pair correlation of unfolded levels u (unit mean density)."""
    M = u.size
    d = u[None, :] - u[:, None]
    d = d[(d > 0) & (d < PC_EDGES[-1])]
    counts, edges = np.histogram(d, bins=PC_EDGES)
    width = float(np.diff(edges).mean())
    centers = 0.5 * (edges[:-1] + edges[1:])
    rate = counts / (M * width)
    gue = 1.0 - (np.sin(np.pi * centers)
                 / (np.pi * np.maximum(centers, 1e-12))) ** 2
    return {"n_levels": int(M), "n_pairs": int(d.size),
            "bin_edges": [float(v) for v in edges],
            "counts": [int(c) for c in counts],
            "pair_correlation": [float(v) for v in rate],
            "gue_reference": [float(v) for v in gue],
            "l2_vs_gue": float(np.sqrt(np.mean((rate - gue) ** 2)))}


def local_unfold(vals: np.ndarray, half: int = UNFOLD_HALF
                 ) -> tuple[np.ndarray, np.ndarray]:
    """Running-mean unfolding: normalized spacings + unit-density levels."""
    s = np.diff(vals)
    half = max(2, min(half, (len(s) - 1) // 4))
    sloc = np.convolve(s, np.ones(2 * half + 1) / (2 * half + 1),
                       mode="valid")
    r = s[half:len(s) - half] / sloc
    u = np.concatenate([[0.0], np.cumsum(r)])
    return r, u


# ------------------------------------------------------------------ operator

def bk_matrix(n: int, L: float) -> np.ndarray:
    """Hermitian FD matrix of H = -i(x d/dx + 1/2) on (0, L], grid j*h."""
    h = L / n
    x = np.arange(1, n + 1) * h
    c = (x[:-1] + x[1:]) / (4.0 * h)          # = (2j+1)/4, L-invariant
    H = np.zeros((n, n), dtype=np.complex128)
    i = np.arange(n - 1)
    H[i, i + 1] = -1j * c
    H[i + 1, i] = 1j * c
    return H


def grid_spectrum(n: int, L: float) -> tuple[np.ndarray, float, float]:
    H = bk_matrix(n, L)
    herm = float(np.abs(H - H.conj().T).max())
    ev = np.linalg.eigvalsh(H)                # ascending, real
    sym = float(np.abs(ev + ev[::-1]).max())  # spectrum is +- symmetric
    return ev, herm, sym


# --------------------------------------------------------------------- zeros

def rvm_unfold(gammas: np.ndarray) -> np.ndarray:
    """Riemann-von Mangoldt counting function N(t) (smooth part + 7/8)."""
    t = np.asarray(gammas, dtype=float)
    return (t / (2 * np.pi)) * np.log(t / (2 * np.pi * math.e)) \
        + 7.0 / 8.0 + 1.0 / (48 * np.pi * t)


def get_zeros(data: dict, force: bool) -> np.ndarray:
    cached = data.get("zeros", {})
    gammas = []
    if not force and cached.get("k") == len(cached.get("gammas", []) or []):
        gammas = list(cached["gammas"])
    if len(gammas) >= K_ZEROS:
        log(f"reusing {K_ZEROS} cached zeros (checkpoint)")
        return np.array(gammas[:K_ZEROS], dtype=float)
    t0 = time.time()
    with mp.workdps(ZERO_DPS):
        for k in range(len(gammas) + 1, K_ZEROS + 1):
            gammas.append(float(mp.im(mp.zetazero(k))))
            if k % 50 == 0 or k == K_ZEROS:
                log(f"zero {k}/{K_ZEROS}: gamma = {gammas[-1]:.6f}  "
                    f"({time.time() - t0:.1f}s elapsed)")
                data["zeros"] = {"k": k, "gammas": gammas}
                data["phase"] = "zeros_partial" if k < K_ZEROS else "zeros"
                save(data)
    return np.array(gammas, dtype=float)


# -------------------------------------------------------------------- Connes

def connes_block(lams: np.ndarray, gammas: np.ndarray) -> dict:
    """|zeta(1/2 + i*lambda)| at BK eigenvalues vs uniform random control."""
    log(f"Connes: |zeta(1/2+i*lambda)| for {lams.size} eigenvalues ...")

    def zvals(ts: np.ndarray) -> np.ndarray:
        out = []
        with mp.workdps(ZETA_DPS):
            for i, t in enumerate(ts):
                out.append(float(abs(mp.zeta(mp.mpc(0.5, float(t))))))
                if (i + 1) % 100 == 0:
                    log(f"  {i + 1}/{ts.size}")
        return np.array(out)

    v = zvals(lams)
    rng = np.random.default_rng(RNG_SEED)
    ctrl = np.sort(rng.uniform(lams[0], lams[-1], lams.size))
    vc = zvals(ctrl)
    d = np.abs(lams[:, None] - gammas[None, :]).min(axis=1)
    dc = np.abs(ctrl[:, None] - gammas[None, :]).min(axis=1)
    lv = np.log(np.maximum(v, 1e-300))
    corr = float(np.corrcoef(lv, d)[0, 1])
    table = [{"lambda": float(l),
              "abs_zeta": float(a),
              "nearest_zero_gamma": float(gammas[int(np.argmin(np.abs(
                  gammas - l)))]),
              "distance": float(dd)}
             for l, a, dd in zip(lams, v, d)]
    clipped = int((lams > gammas[-1]).sum())
    return {"n": int(lams.size),
            "lambda_range": [float(lams[0]), float(lams[-1])],
            "zeros_available_up_to": float(gammas[-1]),
            "eigenvalues_beyond_last_zero": clipped,
            "abs_zeta_min": float(v.min()),
            "argmin_lambda": float(lams[int(np.argmin(v))]),
            "control_min": float(vc.min()),
            "mean_log_abs_zeta": float(lv.mean()),
            "control_mean_log_abs_zeta": float(
                np.log(np.maximum(vc, 1e-300)).mean()),
            "fractions_below_threshold":
                {str(e): {"eigenvalues": float((v < e).mean()),
                          "control": float((vc < e).mean())}
                 for e in CONNES_THRESHOLDS},
            "mean_distance_to_nearest_zero":
                {"eigenvalues": float(d.mean()), "control": float(dc.mean())},
            "corr_log_abszeta_vs_distance": corr,
            "note": ("Connes' idea: the semiclassical zeta operator is "
                     "diagonal in the BK basis with entries "
                     "zeta(1/2+i*lambda_n); vanishing near true zero "
                     "ordinates is the Hilbert-Polya signal. Control = "
                     "uniform random ordinates in the same range. "
                     f"{clipped} eigenvalues exceed gamma_{K_ZEROS}; their "
                     "nearest-zero distances are clipped."),
            "table": table,
            "control_t": [float(t) for t in ctrl],
            "control_abs_zeta": [float(a) for a in vc]}


# ------------------------------------------------------------------- compute

def compute(force: bool = False) -> dict:
    data = {"task": "RT-HP",
            "title": "Hilbert-Polya prototype (Berry-Keating H = xp "
                     "discretization + GUE spacing test)",
            "phase": "start",
            "params": {"grids": GRIDS, "L": L_BOX, "k_zeros": K_ZEROS,
                       "window_frac": WINDOW_FRAC, "skip_zeros": SKIP_ZEROS,
                       "unfold_half": UNFOLD_HALF,
                       "connes_grid": CONNES_GRID, "zeta_dps": ZETA_DPS,
                       "rng_seed": RNG_SEED}}
    if not force and OUT_PATH.exists():
        try:
            old = json.loads(OUT_PATH.read_text())
            if old.get("params") == data["params"]:
                for key in ("zeros", "grids"):
                    if isinstance(old.get(key), (dict, list)):
                        data[key] = old[key]
                log("resuming from checkpoint")
        except Exception as exc:  # noqa: BLE001 - corrupt checkpoint
            log(f"ignoring corrupt checkpoint: {exc}")

    # --- zeros ------------------------------------------------------------
    gammas = get_zeros(data, force)

    # --- grids: eigenvalues + statistics ----------------------------------
    if not isinstance(data.get("grids"), dict):
        data["grids"] = {}
    for N in GRIDS:
        key = str(N)
        blk = data["grids"].get(key) or {}
        if not force and len(blk.get("eigenvalues", [])) == N:
            ev = np.array(blk["eigenvalues"], dtype=float)
            herm = blk["hermiticity_residual"]
            sym = blk["pair_symmetry_residual"]
            log(f"grid {N}: reusing cached eigenvalues")
        else:
            log(f"grid {N}: assembling BK matrix and diagonalizing ...")
            ev, herm, sym = grid_spectrum(N, L_BOX)
        if herm > 1e-12 or sym > 1e-8:
            log(f"!! ANOMALY grid {N}: hermiticity residual {herm:.2e}, "
                f"+- symmetry residual {sym:.2e}")
        pos = ev[ev > 0.0]
        M = pos.size
        lo, hi = int(M * WINDOW_FRAC), int(M * (1.0 - WINDOW_FRAC))
        w = pos[lo:hi]
        s = np.diff(w)
        mean_s = float(s.mean())
        r_loc, u_loc = local_unfold(w)
        r_glob = s / mean_s
        W = math.log(N)                    # = log(x_max/x_min) of the grid
        ref = np.arange(1, M + 1) * math.pi / W
        rel = np.abs(pos - ref) / ref
        data["grids"][key] = {
            "n_grid": N, "L": L_BOX, "h": L_BOX / N,
            "eigenvalues": [float(v) for v in ev],
            "hermiticity_residual": herm,
            "pair_symmetry_residual": sym,
            "n_positive": int(M),
            "lambda_min": float(ev[0]), "lambda_max": float(ev[-1]),
            "first_positive_eigenvalues": [float(v) for v in pos[:8]],
            "spectrum_structure": {
                "local_spacing_std": float(r_loc.std()),
                "normalized_spacing_range": [float(r_loc.min()),
                                             float(r_loc.max())],
                "ref_picket_fence_pi_over_logN": math.pi / W,
                "mean_rel_dev_from_pi_over_logN": float(rel[lo:hi].mean()),
                "note": "H maps to -i d/dt on a log-box of width log(N), "
                        "whose continuum spectrum is the picket fence "
                        "n*pi/log(N). The FD x-grid distorts the smooth "
                        "density (O(1) deviation from n*pi/log(N)), but the "
                        "local level sequence stays near-perfectly "
                        "regular: local_spacing_std ~ 1e-3 vs GUE 0.422."},
            "window": {"lo_index": lo, "hi_index": hi, "n": int(w.size),
                       "lambda_range": [float(w[0]), float(w[-1])],
                       "mean_spacing": mean_s,
                       "local_density_drift": [float(s[:20].mean()),
                                               float(s[-20:].mean())]},
            "unfolding": f"local running mean over +/-{UNFOLD_HALF} spacings",
            "spacing": spacing_block(r_loc),
            "pair_correlation": pair_corr_block(u_loc),
            "naive_global_unfolding": {
                "note": "diagnostic: normalizing by the window-mean "
                        "spacing while the density drifts ~5x across the "
                        "window fabricates a GUE-like KS; pitfall recorded",
                "mean_window_spacing": mean_s,
                "spacing": spacing_block(r_glob)}}
        data["phase"] = f"grid_{N}_done"
        save(data)

    # --- zeros statistics (pipeline control) ------------------------------
    u0 = rvm_unfold(gammas[SKIP_ZEROS:])
    sz = np.diff(u0)
    data["zeros_stats"] = {
        "k": K_ZEROS, "skip_first": SKIP_ZEROS,
        "gamma_first": float(gammas[0]), "gamma_last": float(gammas[-1]),
        "unfolding": "Riemann-von Mangoldt N(t) = t/2pi log(t/2pi e) "
                     "+ 7/8 + 1/(48 pi t)",
        "unfolding_drift": float(sz.mean() - 1.0),
        "spacing": spacing_block(sz / sz.mean()),
        "pair_correlation": pair_corr_block((u0 - u0[0]) / sz.mean())}
    data["phase"] = "zeros_stats_done"
    save(data)

    # --- Connes truncated trace -------------------------------------------
    ev_c = np.array(data["grids"][str(CONNES_GRID)]["eigenvalues"], float)
    lams = ev_c[ev_c > 0.0]
    old_c = data.get("connes") if not force else None
    if isinstance(old_c, dict) and old_c.get("n") == int(lams.size):
        log("reusing cached Connes block (checkpoint)")
    else:
        data["connes"] = connes_block(lams, gammas)
        data["phase"] = "connes_done"
        save(data)

    # --- findings (honest, verbatim numbers) ------------------------------
    g = data["grids"]
    b1024 = g["1024"]
    sp = b1024["spacing"]
    ng = b1024["naive_global_unfolding"]["spacing"]
    zks = data["zeros_stats"]["spacing"]["ks_gue"]
    data["findings"] = {
        "bk_spectrum": (
            "After LOCAL unfolding the naive Berry-Keating FD spectrum is "
            "a near-perfect picket fence: normalized-spacing std "
            f"{sp['std']:.1e} vs GUE 0.422; all spacings in "
            f"[{b1024['spectrum_structure']['normalized_spacing_range'][0]:.3f},"
            f" {b1024['spectrum_structure']['normalized_spacing_range'][1]:.3f}]; "
            f"KS to GUE {sp['ks_gue']:.3f}, KS to Poisson "
            f"{sp['ks_poisson']:.3f} (the distribution is a delta-like "
            "spike, matching neither law). Consistent with "
            "H = -i d/dt on a log-box: no level repulsion, no GUE "
            "statistics. A GUE-producing Hilbert-Polya operator needs more "
            "than the naive xp discretization (e.g. Berry-Keating boundary "
            "conditions at both cutoffs, or the Connes/adeolic "
            "modification)."),
        "unfolding_artifact": (
            "Naive GLOBAL unfolding (normalization by the window-mean "
            "spacing) fabricates a GUE signal: KS to GUE "
            f"{ng['ks_gue']:.3f}, std {ng['std']:.3f} -- close to the zeta-"
            "zero control -- purely because the BK spectral density drifts "
            f"~5x across the window (mean spacing "
            f"{b1024['window']['local_density_drift'][0]:.2f} at the "
            f"bottom vs {b1024['window']['local_density_drift'][1]:.2f} at "
            "the top, N=1024). Methodological warning recorded verbatim; "
            "the local-unfolding numbers above are the real ones."),
        "control": (f"first {K_ZEROS} zeta zeros unfolded by RvM: KS to GUE "
                    f"{zks:.3f} (vs Poisson "
                    f"{data['zeros_stats']['spacing']['ks_poisson']:.3f}) "
                    "-- the statistics pipeline reproduces the known "
                    "GUE-like behaviour of zeta zeros, validating the "
                    "spacing/pair-correlation code."),
        "connes": (f"min |zeta(1/2+i*lambda)| over BK eigenvalues: "
                   f"{data['connes']['abs_zeta_min']:.4f} vs random control "
                   f"{data['connes']['control_min']:.4f}; mean log|zeta| "
                   f"{data['connes']['mean_log_abs_zeta']:.4f} vs control "
                   f"{data['connes']['control_mean_log_abs_zeta']:.4f}. "
                   "The BK eigenvalues do not hit zeta zeros better than "
                   "random ordinates -- negative prototype result for the "
                   "truncated Connes trace on this discretization."),
        "verdict": ("Feasibility study: the naive xp discretization does "
                    "NOT exhibit the Hilbert-Polya signal (picket fence, "
                    "no Connes alignment). Recorded verbatim per the "
                    "honesty rule; the unfolding pitfall is a reusable "
                    "lesson for the fleet.")}
    data["phase"] = "complete"
    save(data)
    log(f"wrote {OUT_PATH}")
    return data


# ------------------------------------------------------------------ validate

def validate(res: dict) -> tuple[bool, list[str]]:
    msgs, ok = [], True

    def check(cond: bool, msg: str) -> None:
        nonlocal ok
        msgs.append(("PASS" if cond else "FAIL") + "  " + msg)
        ok = ok and cond

    check(res.get("phase") == "complete", "JSON exists, phase complete")
    p = res.get("params", {})
    check(p.get("grids") == [256, 512, 1024],
          "params: N_grid in {256, 512, 1024}")
    grids = res.get("grids", {})
    for N in [256, 512, 1024]:
        blk = grids.get(str(N), {})
        ev = blk.get("eigenvalues", [])
        finite = all(isinstance(v, float) and math.isfinite(v) for v in ev)
        check(len(ev) == N and finite,
              f"grid {N}: eigenvalue table complete ({len(ev)}/{N} entries)")
        sp = blk.get("spacing", {})
        h = sp.get("histogram", {})
        nb = len(h.get("bin_edges", [])) - 1
        check(sp.get("n_spacings", 0) > 0 and nb > 0
              and len(h.get("counts", [])) == nb,
              f"grid {N}: spacing distribution computed "
              f"(n={sp.get('n_spacings')}, {nb} bins)")
        check(blk.get("pair_correlation", {}).get("n_pairs", 0) > 0,
              f"grid {N}: pair correlation computed")
        check("naive_global_unfolding" in blk,
              f"grid {N}: global-unfolding diagnostic recorded")
    zs = res.get("zeros_stats", {})
    check(zs.get("spacing", {}).get("n_spacings", 0) > 0,
          "zeta-zero GUE control computed (spacing distribution)")
    cn = res.get("connes", {})
    check(cn.get("n", 0) > 0 and "control_min" in cn and "table" in cn,
          f"Connes truncated trace computed (n={cn.get('n')}, control "
          f"present)")
    # exploratory task: findings are reported loudly, never gate-failing
    for N in [256, 512, 1024]:
        sp = grids.get(str(N), {}).get("spacing", {})
        if sp:
            msgs.append(f"FINDING (not a gate failure): grid {N} spacings "
                        f"(local unfolding) KS-to-GUE = {sp.get('ks_gue')}, "
                        f"KS-to-Poisson = {sp.get('ks_poisson')}, "
                        f"std = {sp.get('std')}")
    if cn:
        msgs.append(f"FINDING (not a gate failure): Connes min "
                    f"|zeta| eigen {cn.get('abs_zeta_min'):.4f} vs control "
                    f"{cn.get('control_min'):.4f}")
    return ok, msgs


def summary(res: dict) -> None:
    print("\n=== RT-HP summary ===")
    print(f"{'N':>5} {'lam_max':>9} {'local std(s)':>12} {'KS GUE':>7} "
          f"{'KS Pois':>7} {'naiveKS':>7} {'PC L2':>7}")
    for N in GRIDS:
        b = res["grids"][str(N)]
        sp = b["spacing"]
        ng = b["naive_global_unfolding"]["spacing"]
        pc = b["pair_correlation"]
        print(f"{N:>5} {b['lambda_max']:>9.3f} "
              f"{b['spectrum_structure']['local_spacing_std']:>12.2e} "
              f"{sp['ks_gue']:>7.3f} {sp['ks_poisson']:>7.3f} "
              f"{ng['ks_gue']:>7.3f} {pc['l2_vs_gue']:>7.3f}")
    ss = res["grids"]["1024"]["spectrum_structure"]
    print(f"normalized spacing range (N=1024, local unfolding): "
          f"[{ss['normalized_spacing_range'][0]:.4f}, "
          f"{ss['normalized_spacing_range'][1]:.4f}]  (GUE std 0.422)")
    print(f"first 5 positive eigenvalues (N=1024): "
          f"{[round(v, 4) for v in res['grids']['1024']['first_positive_eigenvalues'][:5]]}"
          f"  picket-fence pi/log(N) = "
          f"{ss['ref_picket_fence_pi_over_logN']:.4f}")
    zs = res["zeros_stats"]
    print(f"zeta-zero control (k={zs['k']}, gamma in "
          f"[{zs['gamma_first']:.2f}, {zs['gamma_last']:.2f}]): std(s) = "
          f"{zs['spacing']['std']:.3f}, KS GUE = {zs['spacing']['ks_gue']:.3f}, "
          f"KS Poisson = {zs['spacing']['ks_poisson']:.3f}")
    cn = res["connes"]
    print(f"Connes (N={CONNES_GRID}, n={cn['n']} positive eigenvalues in "
          f"[{cn['lambda_range'][0]:.2f}, {cn['lambda_range'][1]:.2f}]):")
    print(f"  min |zeta(1/2+i*lam)| = {cn['abs_zeta_min']:.4f} at lam = "
          f"{cn['argmin_lambda']:.3f};  random control min = "
          f"{cn['control_min']:.4f}")
    print(f"  mean log|zeta| = {cn['mean_log_abs_zeta']:.4f} vs control "
          f"{cn['control_mean_log_abs_zeta']:.4f};  corr(log|zeta|, dist) = "
          f"{cn['corr_log_abszeta_vs_distance']:.3f}")
    for thr, fb in cn["fractions_below_threshold"].items():
        print(f"  fraction |zeta| < {thr}: eigenvalues {fb['eigenvalues']:.3f} "
              f"vs control {fb['control']:.3f}")
    for k, v in res["findings"].items():
        print(f"  [{k}] {v}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gate", action="store_true",
                    help="compute if needed, validate output, exit code")
    ap.add_argument("--force", action="store_true",
                    help="recompute everything from scratch")
    args = ap.parse_args()

    res = compute(force=args.force)
    summary(res)
    ok, msgs = validate(res)
    for m in msgs:
        print(m)
    if args.gate:
        print(f"\nGATE {'PASSED' if ok else 'FAILED'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
