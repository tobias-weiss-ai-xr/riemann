#!/usr/bin/env python3
"""
Experiment QEC-01: Spectral decomposition of quantum-code decoding graphs.

Bridge experiment: riemann's Cayley-graph spectral methodology (spectral gap,
Ramanujan ratio, expander-mixing) applied to the decoding graphs that
GNN/Belief-Propagation quantum error correction decoders message-pass over.

Why it matters
--------------
POLYMECHANON (Astolfi & Pupillo, 2610.01683) decodes ANY stabilizer code from its
detection error model by treating the code as a graph UGNN's input; its key
empirical claims are code-agnostic transfer, faster decode on qLDPC than BP+OSD,
and failure to generalize to unseen (larger) codes. A natural structural question
is whether the *spectral gap / expansion* of the decoding graph predicts decoder
behaviour — the same local-vs-global question riemann's Cayley graphs (SL(2,F_p))
raise for spectral prediction of number-theoretic objects.

Here we construct the Tanner + syndrome graphs of a small family of CSS codes
(toric Z_d^2 for d=2..15, Steane [[7,1,3]], repetition-5), compute their spectra
with the same spectral-gap conventions as compute_eigenvalues.py, and run a real
belief-propagation (BP) decoder at several physical error rates to measure the
correlation between expansion and logical-error suppression.

Output: data/qec_spectral/qec_decoding_spectra_results.json
Usage:  python qec_decoding_graph_spectra.py  [--mc 2000] [--seed 42]
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np

OUT_DIR = Path("data/qec_spectral")


# ────────────────────────────────────────────────────────────────
# 1. Code construction (CSS parity checks, mod-2 linear algebra)
# ────────────────────────────────────────────────────────────────

def repetition_code(n: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Repetition code on n spins: n qubits, n-1 Z-checks Z_i Z_{i+1}."""
    n_q = n
    n_z = n - 1
    Hz = np.zeros((n_z, n_q), dtype=np.int8)
    for i in range(n_z):
        Hz[i, i] = 1
        Hz[i, i + 1] = 1
    Hx = np.zeros((0, n_q), dtype=np.int8)  # X-stabilizer group is trivial
    return Hx, Hz, n_q


def toric_code(d: int) -> tuple[np.ndarray, np.ndarray, int]:
    """
    Toric code on a d×d torus (Z_d^2). Qubits on edges (2 d^2 of them),
    Z-checks on faces (d^2), X-checks on vertices (d^2).
    This is a CSS code; its Z-syndrome graph is the dual lattice — the
    Cayley graph of G = Z_d^2 with generators ±e1, ±e2.
    """
    n_q = 2 * d * d  # horizontal + vertical edges
    n_z = d * d  # faces
    n_x = d * d  # vertices

    def vid(v, dir):  # qubit index: (row, col, dir)
        r, c = v
        return (dir * (d * d)) + r * d + c

    Hz = np.zeros((n_z, n_q), dtype=np.int8)
    Hx = np.zeros((n_x, n_q), dtype=np.int8)
    for r in range(d):
        for c in range(d):
            # face (r,c): bounding edges  (top h, bottom h', left v, right v')
            f = r * d + c
            Hz[f, vid((r, c), 0)] = 1          # top horizontal at (r,c)
            Hz[f, vid(((r + 1) % d, c), 0)] = 1  # bottom horizontal
            Hz[f, vid((r, c), 1)] = 1          # left vertical
            Hz[f, vid((r, (c + 1) % d), 1)] = 1  # right vertical
            # vertex (r,c): incident edges (right h, left h', down v, up v')
            x = r * d + c
            Hx[x, vid((r, c), 0)] = 1           # right horizontal
            Hx[x, vid((r, (c - 1) % d), 0)] = 1  # left horizontal
            Hx[x, vid((r, c), 1)] = 1           # down vertical
            Hx[x, vid(((r - 1) % d, c), 1)] = 1  # up vertical
    return Hx, Hz, n_q


def css_from_matrix(H: np.ndarray, name: str) -> tuple[np.ndarray, np.ndarray, int]:
    """Generic CSS code from a single check matrix (H_X = H_Z = H)."""
    n_q = H.shape[1]
    return H.copy(), H.copy(), n_q


# ────────────────────────────────────────────────────────────────
# 2. Graph constructions
# ────────────────────────────────────────────────────────────────

def syndrome_graph(H: np.ndarray) -> tuple[np.ndarray, set, list, bool]:
    """
    Syndrome graph: nodes = Z-checks, edges connect two checks that share a qubit
    (one physical error flips both). Returns (adjacency matrix, edge set,
    node-shared-qubit list, is_regular).
    """
    n = H.shape[0]
    adj = np.zeros((n, n), dtype=np.int8)
    edges: set[tuple[int, int]] = set()
    shared: list[list[int]] = [[] for _ in range(n)]
    for q in range(H.shape[1]):
        checks = np.nonzero(H[:, q])[0]
        for a, b in itertools.combinations(checks, 2):
            adj[a, b] = adj[b, a] = 1
            key = (min(a, b), max(a, b))
            if key not in edges:
                edges.add(key)
            shared[a].append(q)
    degs = adj.sum(axis=1)
    is_regular = bool(len(degs) > 0 and np.all(degs == degs[0]))
    return adj, edges, shared, is_regular


def tanner_graph(Hx: np.ndarray, Hz: np.ndarray, n_q: int) -> np.ndarray:
    """Tanner graph: nodes = qubits + all checks; edges qubit<->check iff H has a 1."""
    n_checks = Hx.shape[0] + Hz.shape[0]
    n = n_q + n_checks
    adj = np.zeros((n, n), dtype=np.int8)
    for (H, base) in ((Hx, 0), (Hz, Hx.shape[0])):
        for i in range(H.shape[0]):
            for q in np.nonzero(H[i])[0]:
                adj[n_q + base + i, q] = adj[q, n_q + base + i] = 1
    return adj


# ────────────────────────────────────────────────────────────────
# 3. Spectral statistics (same conventions as compute_eigenvalues.py)
# ────────────────────────────────────────────────────────────────

def spectral_stats(adj: np.ndarray) -> dict:
    """Full spectral profile of an undirected, unweighted adjacency matrix."""
    n = adj.shape[0]
    if n == 0:
        return {}
    evals = np.linalg.eigvalsh(adj.astype(float))
    evals = evals[::-1]  # descending
    deg = adj.sum(axis=1).astype(float)
    dmax = int(deg.max()) if len(deg) else 0
    dmin = int(deg.min()) if len(deg) else 0
    davg = float(deg.mean()) if len(deg) else 0.0

    # normalized Laplacian spectral gap (expansion; scale-free)
    L = np.eye(n)
    for i in range(n):
        for j in range(n):
            if i != j and adj[i, j]:
                L[i, j] = -1.0 / np.sqrt(deg[i] * deg[j]) if deg[i] * deg[j] > 0 else 0.0
    lev = np.linalg.eigvalsh(L)
    # sorted ascending; gap = 2nd smallest eigenvalue
    nz = lev[lev > 1e-9]
    gap_norm = float(nz[0]) if len(nz) > 0 else 0.0

    # adjacency gap & Ramanujan-style ratio
    second_largest = float(evals[1]) if n > 1 else 0.0
    spectral_gap = float(dmax - np.abs(second_largest)) if n > 1 else 0.0

    def cheeger_bound():
        # Cheeger inequality: h ≥ gap_norm / 2
        return float(gap_norm / 2.0)

    # Ramanujan criterion: d-regular, every eigenvalue EXCEPT ±d must satisfy
    # |λ| ≤ 2√(d-1). (Same ratio riemann computes for SL(2,F_p) Cayley graphs.)
    is_regular_graph = bool(n > 0 and dmin == dmax)
    ramanujan_bound = 2.0 * np.sqrt(max(dmax - 1, 0.0)) if dmax >= 1 else 0.0
    nontriv = [float(x) for x in evals if abs(abs(x) - dmax) > 1e-6 and abs(abs(x) - dmin) > 1e-6]
    max_abs_nontriv = max((abs(x) for x in nontriv), default=0.0)
    ramanujan_ratio = (max_abs_nontriv / ramanujan_bound) if ramanujan_bound > 0 else float("inf")
    # Ramanujan criterion is ONLY defined for d-regular graphs; report the flag only then.
    is_ramanujan = bool(
        n > 0 and is_regular_graph and ramanujan_bound > 0 and ramanujan_ratio <= 1.0 + 1e-10
    )

    # girth (shortest cycle) via BFS
    girth = compute_girth(adj)
    return {
        "n_nodes": int(n),
        "n_edges": int(adj.sum() // 2),
        "degree_min": int(dmin),
        "degree_max": int(dmax),
        "degree_avg": round(davg, 3),
        "is_regular": bool(dmin == dmax),
        "eigenvalues_desc_first10": [round(float(x), 5) for x in evals[:10]],
        "second_largest_adjacency": round(float(second_largest), 5),
        "spectral_gap_adjacency": round(float(spectral_gap), 5),
        "normalized_laplacian_gap": round(float(gap_norm), 5),
        "cheeger_bound_h": round(float(cheeger_bound()), 5),
        "ramanujan_bound": round(float(ramanujan_bound), 5),
        "max_abs_nontrivial": round(float(max_abs_nontriv), 5),
        "ramanujan_ratio": round(float(ramanujan_ratio), 5) if ramanujan_ratio != float("inf") else None,
        "is_ramanujan": is_ramanujan,
        "girth": int(girth),
    }


def compute_girth(adj: np.ndarray) -> int:
    """BFS-based girth (smallest cycle)."""
    n = adj.shape[0]
    girth = n + 1
    from collections import deque

    for s in range(n):
        dist = {s: 0}
        parent = {s: -1}
        q = deque([s])
        while q:
            u = q.popleft()
            for v in np.nonzero(adj[u])[0]:
                v = int(v)
                if v not in dist:
                    dist[v] = dist[u] + 1
                    parent[v] = u
                    q.append(v)
                elif parent[u] != v:
                    # cycle: dist[u]+dist[v]+1
                    girth = min(girth, dist[u] + dist[v] + 1)
        if girth <= 3:  # triangles minimal possible
            break
    return girth if girth <= n else 0  # 0 indicates acyclic


# ────────────────────────────────────────────────────────────────
# 4. Belief-propagation decoder (bit-flip CSS code)
# ────────────────────────────────────────────────────────────────

def bp_decode(Hz: np.ndarray, syndrome: np.ndarray, p: float, iters: int = 12) -> np.ndarray:
    """
    Sum-product BP on the Tanner graph of Z-checks for independent X errors.
    Returns estimated error vector (mod 2). Uses log-likelihood ratios.
    """
    n_c, n_q = Hz.shape
    # check -> qubit messages, qubit -> check messages (LLR)
    # adjacency lists
    checks_of = [[] for _ in range(n_q)]
    qubits_of = [[] for _ in range(n_c)]
    for i in range(n_c):
        for q in np.nonzero(Hz[i])[0]:
            checks_of[int(q)].append(i)
            qubits_of[i].append(int(q))

    prior = float(np.log((1 - p) / p))
    # messages c->v
    msg_cv = {i: {q: 0.0 for q in qubits_of[i]} for i in range(n_c)}
    msg_vc = {q: {c: 0.0 for c in checks_of[q]} for q in range(n_q)}

    def tanh(x):
        return np.tanh(x / 2.0)

    for _ in range(iters):
        # variable -> check
        for q in range(n_q):
            for c in checks_of[q]:
                total = prior + sum(msg_cv[c2][q] for c2 in checks_of[q] if c2 != c)
                msg_vc[q][c] = total
        # check -> variable
        for c in range(n_c):
            s = int(syndrome[c])
            for v in qubits_of[c]:
                prod = (-1.0) ** s
                for u in qubits_of[c]:
                    if u != v:
                        prod *= tanh(msg_vc[u][c])
                # avoid atanh(±1) saturation
                prod = min(max(prod, -0.999999), 0.999999)
                msg_cv[c][v] = 2.0 * float(np.arctanh(prod))

    # final decision
    est = np.zeros(n_q, dtype=np.int8)
    for q in range(n_q):
        total = prior + sum(msg_cv[c][q] for c in checks_of[q])
        if total < 0:  # LLR<0 → error more likely
            est[q] = 1
    return est


def mod2_rowspace_membership(v: np.ndarray, rows: np.ndarray) -> bool:
    """Is v (mod 2) in the row space of `rows` (binary)? Gaussian elimination mod 2."""
    if rows.shape[0] == 0:
        return not bool(v.any())
    M = rows.copy().astype(int) % 2
    n_rows, n_cols = M.shape
    rank_piv = []
    r = 0
    for c in range(n_cols):
        piv = None
        for i in range(r, n_rows):
            if M[i, c]:
                piv = i
                break
        if piv is None:
            continue
        M[[r, piv]] = M[[piv, r]]
        for i in range(n_rows):
            if i != r and M[i, c]:
                M[i] ^= M[r]  # type: ignore[assignment]
        rank_piv.append(c)
        r += 1
    # check: extend with v
    target = v.copy().astype(int) % 2
    for i, c in enumerate(rank_piv):
        if target[c]:
            target ^= M[i]  # type: ignore[assignment]
    return not bool(target.any())


def run_mc(Hz, Hx, p, shots, iters=12, seed=42):
    """Monte-Carlo logical failure rate of BP decoder at physical error rate p.

    Each call seeds a fresh RNG from `seed` so that every (code, p) pair draws
    independent samples (a shared stream would couple the five per-p rates).
    """
    rng = np.random.default_rng(seed)
    n_q = Hz.shape[1]
    fails = 0
    for _ in range(shots):
        err = (rng.random(n_q) < p).astype(np.int8)
        syndrome = (Hz @ err) % 2
        est = bp_decode(Hz, syndrome, p, iters)
        residual = (err + est) % 2
        # success iff residual X-error is a stabilizer (row space of X-checks Hx only)
        if mod2_rowspace_membership(residual, Hx):
            pass
        else:
            fails += 1
    return fails / shots


# ────────────────────────────────────────────────────────────────
# 5. Driver
# ────────────────────────────────────────────────────────────────

CODES = {
    "repetition-5": lambda: repetition_code(5),
    "toric-d2": lambda: toric_code(2),
    "toric-d3": lambda: toric_code(3),
    "toric-d4": lambda: toric_code(4),
}

# Steane [[7,1,3]] from Hamming [7,4,3]
STEANE_H = np.array(
    [
        [1, 0, 1, 0, 1, 0, 1],
        [0, 1, 1, 0, 0, 1, 1],
        [0, 0, 0, 1, 1, 1, 1],
    ],
    dtype=np.int8,
)
CODES["steane-7"] = lambda: css_from_matrix(STEANE_H, "steane")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mc", type=int, default=2000, help="MC shots per error rate")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    results: dict = {"metadata": {"experiment": "QEC-01", "mc_shots": args.mc}, "codes": {}}

    for name, build in CODES.items():
        Hx, Hz, n_q = build()
        if Hx.shape[0] > 0 and Hz.shape[0] > 0:
            css = ((Hx @ Hz.T) % 2)
            assert css.size == 0 or not css.any(), f"CSS condition violated for {name}"
        adj_syndrome, edges, shared, is_reg = syndrome_graph(Hz)
        adj_tanner = tanner_graph(Hx, Hz, n_q)
        # X-side syndrome graph (dual): node = X-check sharing a qubit
        # (we reuse syndrome_graph on Hx.T? no — build on Hx directly)
        adj_sx, _, _, reg_x = syndrome_graph(Hx)
        results["codes"][name] = {
            "n_qubits": n_q,
            "n_z_checks": int(Hz.shape[0]),
            "n_x_checks": int(Hx.shape[0]),
            "syndrome_graph_Z": spectral_stats(adj_syndrome),
            "syndrome_graph_X": spectral_stats(adj_sx),
            "tanner_graph": spectral_stats(adj_tanner),
        }
        print(f"✓ {name}: {n_q} qubits, Z-syndrome graph = {results['codes'][name]['syndrome_graph_Z']}")

    # MC decode experiments on small, CSS codes
    mc_codes = {}
    codes_so_far = 0
    for name in ("repetition-5", "toric-d2", "toric-d3"):
        Hx, Hz, _ = CODES[name]()
        mc_codes[name] = {"physical_rates": [], "logical_failure": []}
        for i, p in enumerate((0.03, 0.05, 0.08, 0.10, 0.15)):
            fl = run_mc(Hz, Hx, p, args.mc, seed=args.seed + 1000 * i + codes_so_far)
            mc_codes[name]["physical_rates"].append(p)
            mc_codes[name]["logical_failure"].append(round(fl, 5))
            print(
                f"  MC {name} p={p}: logical failure {fl:.4f} "
                f"(gap_norm={results['codes'][name]['syndrome_graph_Z']['normalized_laplacian_gap']})"
            )
        codes_so_far += 1
    results["mc_decode"] = mc_codes

    # Ramanujan/expansion scaling for toric syndrome graphs across d.
    # Z-syndrome graph of toric Z_d^2 = Cayley graph C(Z_d^2, ±e1, ±e2) (d >= 3);
    # adjacency spectrum: λ(a,b) = 2cos(2πa/d) + 2cos(2πb/d), so
    # λ2 = 2 + 2cos(2π/d) — the +1,-1 nearest-neighbour lattice direction.
    # Compare against the Ramanujan bound 2√3 for this 4-regular graph.
    toric_scaling = []
    for d in range(2, 16):
        Hx, Hz, _ = toric_code(d)
        adj, _, _, _ = syndrome_graph(Hz)
        st = spectral_stats(adj)
        toric_scaling.append(
            {
                "d": d,
                "n_nodes": st["n_nodes"],
                "lambda2_adjacency": st["second_largest_adjacency"],
                "ramanujan_bound": st["ramanujan_bound"],
                "ramanujan_ratio": st["ramanujan_ratio"],
                "is_ramanujan": st["is_ramanujan"],
                "normalized_laplacian_gap": st["normalized_laplacian_gap"],
            }
        )
    results["toric_ramanujan_scaling"] = toric_scaling
    print(f"\nToric syndrome graph = Cayley graph C(Z_d^2, ±e1, ±e2) — Ramanujan scaling:")
    for r in toric_scaling:
        print(
            f"  d={r['d']:>2}  λ₂={r['lambda2_adjacency']:.4f}  RamanujanBound=2√3≈{r['ramanujan_bound']:.4f}  "
            f"ratio={r['ramanujan_ratio'] if r['ramanujan_ratio'] is not None else float('inf'):.3f}  "
            f"{'RAMANUJAN ✓' if r['is_ramanujan'] else 'not expander (needs MWPM)'}"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "qec_decoding_spectra_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {OUT_DIR / 'qec_decoding_spectra_results.json'}")
    print("Cheeger vs failure: codes with larger normalized gap should fail less at fixed p.")


if __name__ == "__main__":
    main()
