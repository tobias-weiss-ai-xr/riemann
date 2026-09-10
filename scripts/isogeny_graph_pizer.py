#!/usr/bin/env python3
"""Exp 22: Direct supersingular isogeny graph construction + Pizer spectrum check.

Builds the ACTUAL Brandt-style 2-isogeny graph on ALL supersingular j-invariants
over F_{p^2} and compares its nontrivial spectrum against the Hecke eigenvalues
a_2(f) over weight-2 newforms f of level p (Pizer/Brandt/Jacquet-Langlands/
Eichler correspondence).

Key facts used:
  - E/Fbar_p is supersingular iff the Hasse invariant vanishes: the coefficient
    of x^{p-1} in f(x)^{(p-1)/2} (f = x^3+a*x+b) is 0. Supersingularity is a
    j-invariant property, so test one curve per j over F_{p^2} (all
    supersingular j live in F_{p^2}).
  - The 2-isogeny graph is a (2+1)=3-regular MULTIGRAPH: A[j][k] = multiplicity
    of k as root of the classical modular polynomial Phi_2(j, Y) = 0 (degree 3
    in Y; self-loops possible, e.g. Phi_2(25,25)=0 at p=29). Row sums are
    always 3 (the three cyclic 2-subgroups).
  - Pizer: the nontrivial spectrum (Perron eigenvalue 3 excluded) equals the
    multiset of Hecke eigenvalues a_2(f) over all real embeddings of all
    weight-2 newforms at level p.
  - Ramanujan: max |lambda| <= 2*sqrt(2) ~ 2.828.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

OUT = Path("data/experiment22")
OUT.mkdir(parents=True, exist_ok=True)

_D_CACHE: dict[int, int] = {}


def field_param(p: int) -> int:
    """Non-square d mod p: F_{p^2} = F_p[w]/(w^2 - d)."""
    if p not in _D_CACHE:
        for d in range(2, p):
            if pow(d, (p - 1) // 2, p) == p - 1:
                _D_CACHE[p] = d
                break
        else:
            _D_CACHE[p] = 2
    return _D_CACHE[p]


# ---- F_{p^2} arithmetic: element (u, v) = u + v*w, w^2 = d -------------------
def f2_add(a, b, p):
    return ((a[0] + b[0]) % p, (a[1] + b[1]) % p)


def f2_neg(a, p):
    return ((-a[0]) % p, (-a[1]) % p)


def f2_mul(a, b, p):
    u, v = a
    x, y = b
    d = field_param(p)
    return ((u * x + d * v * y) % p, (u * y + v * x) % p)


def f2_scalar(k, p):
    return (k % p, 0)


def f2_one():
    return (1, 0)


def f2_zero():
    return (0, 0)


def pmul(f, g, p, cap):
    """Polynomial multiply, dicts deg -> f2 coeff, truncate above cap."""
    out: dict[int, tuple[int, int]] = {}
    for e1, c1 in f.items():
        for e2, c2 in g.items():
            e = e1 + e2
            if e > cap:
                continue
            out[e] = f2_add(out.get(e, f2_zero()), f2_mul(c1, c2, p), p)
    return out


def hasse_zero(a, b, p):
    """Supersingular? coeff of x^{p-1} in (x^3 + a x + b)^{(p-1)/2} == 0."""
    k = (p - 1) // 2
    base = {3: f2_one(), 1: a, 0: b}
    res = {0: f2_one()}
    cap = p - 1
    while k:
        if k & 1:
            res = pmul(res, base, p, cap)
        base = pmul(base, base, p, cap)
        k >>= 1
    return res.get(p - 1, f2_zero()) == (0, 0)


def j_of(a, b, p):
    """j-invariant of y^2 = x^3 + a x + b over F_{p^2}."""
    a3 = f2_mul(f2_mul(a, a, p), a, p)
    b2 = f2_mul(b, b, p)
    num = f2_mul(f2_scalar(1728 * 4, p), a3, p)
    den = f2_add(f2_mul(f2_scalar(4, p), a3, p), f2_mul(f2_scalar(27, p), b2, p), p)
    if den == (0, 0):
        return None
    u, v = den
    d = field_param(p)
    nrm = (u * u - d * v * v) % p
    if nrm == 0:
        return None
    inv = pow(nrm, p - 2, p)
    return f2_mul(num, ((u * inv) % p, (-v * inv) % p), p)


def supersingular_js_fp2(p: int) -> list[tuple[int, int]]:
    """All supersingular j-invariants in F_{p^2}: scan all (a,b) in F_{p^2}^2,
    dedupe by j, test the Hasse invariant once per j. Complete by construction
    (every supersingular j is realized by curves over F_{p^2})."""
    ss: set[tuple[int, int]] = set()
    seen: set[tuple[int, int]] = set()
    for au in range(p):
        for av in range(p):
            a = (au, av)
            for bu in range(p):
                for bv in range(p):
                    b = (bu, bv)
                    a3 = f2_mul(f2_mul(a, a, p), a, p)
                    b2 = f2_mul(b, b, p)
                    disc = f2_add(f2_mul(f2_scalar(4, p), a3, p),
                                  f2_mul(f2_scalar(27, p), b2, p), p)
                    if disc == (0, 0):
                        continue
                    j = j_of(a, b, p)
                    if j is None or j in seen:
                        continue
                    seen.add(j)
                    if hasse_zero(a, b, p):
                        ss.add(j)
    return sorted(ss, key=lambda z: (z[0], z[1]))


# ---- Phi_2(j, Y) as monic cubic in Y with F_{p^2} coefficients ---------------
# Phi2(X,Y) = X^3 + Y^3 - X^2Y^2 + 1488XY(X+Y) - 162000(X^2+Y^2)
#             + 40773375XY + 8748000000(X+Y) - 157464000000000
def phi2_coeffs(j, p):
    j2 = f2_mul(j, j, p)
    j3 = f2_mul(j2, j, p)
    c2 = f2_add(f2_neg(j2, p), f2_mul(f2_scalar(1488, p), j, p), p)
    c2 = f2_add(c2, f2_scalar(-162000, p), p)
    c1 = f2_add(f2_mul(f2_scalar(1488, p), j2, p),
                f2_mul(f2_scalar(40773375, p), j, p), p)
    c1 = f2_add(c1, f2_scalar(8748000000, p), p)
    c0 = f2_add(j3, f2_mul(f2_scalar(-162000, p), j2, p), p)
    c0 = f2_add(c0, f2_mul(f2_scalar(8748000000, p), j, p), p)
    c0 = f2_add(c0, f2_scalar(-157464000000000, p), p)
    return [f2_one(), c2, c1, c0]


def f2_peval(q, r, p):
    """Horner evaluation of f2-coefficient polynomial q at r."""
    acc = f2_zero()
    for c in q:
        acc = f2_add(f2_mul(acc, r, p), c, p)
    return acc


def synth_div(q, r, p):
    """Monic polynomial q divided by (Y - r); returns (quotient, remainder)."""
    n = len(q)
    out = [q[0]]
    for i in range(1, n - 1):
        out.append(f2_add(q[i], f2_mul(out[-1], r, p), p))
    rem = f2_add(q[n - 1], f2_mul(out[-1], r, p), p)
    return out, rem


def roots_with_mult(j, p):
    """Roots of Phi_2(j, Y) over F_{p^2} with multiplicities (sum = 3)."""
    q = phi2_coeffs(j, p)
    roots = []
    for ru in range(p):
        for rv in range(p):
            r = (ru, rv)
            if f2_peval(q, r, p) == (0, 0):
                roots.append(r)
    mults: dict[tuple[int, int], int] = {}
    for r in roots:
        m = 0
        cur = q
        while len(cur) > 1:
            cur, rem = synth_div(cur, r, p)
            if rem == (0, 0):
                m += 1
            else:
                break
        mults[r] = m
    return mults


def brandt_matrix(js, p):
    """A[j][k] = multiplicity of k as root of Phi_2(j, Y). Row sums = 3."""
    idx = {j: i for i, j in enumerate(js)}
    n = len(js)
    A = np.zeros((n, n), dtype=int)
    for i, j in enumerate(js):
        mults = roots_with_mult(j, p)
        assert all(r in idx for r in mults), \
            f"2-isogeny target outside supersingular set: j={j} mults={mults}"
        assert sum(mults.values()) == 3, f"row sum != 3 at j={j}: {mults}"
        for r, m in mults.items():
            A[i, idx[r]] = m
    return A


def hecke_a2_at_level(recs: list[dict], level: int) -> list[float]:
    """Per-embedding Hecke eigenvalues a_2(f) for all newforms f of level p.

    The mirror's individual_eigenvalues[k] = a_{k+1} in Hecke-FIELD power-basis
    coordinates (NOT per embedding); traces[k] = trace(a_{k+1}).  Per-embedding
    a_2 values = roots of the char. poly of T_2 on the orbit, obtained from
    power sums via Newton's identities, using the Hecke relations
      T_2^2 = T_4 + 2 T_1,  T_2^3 = T_8 + 4 T_2,  T_2^4 = T_16 + 6 T_4 + 8 T_1.
    (valid for (2, p) = 1; levels here are odd primes)
    """
    out = []
    for r in recs:
        if int(r["level"]) != level:
            continue
        tr = r.get("traces") or []
        if len(tr) < 16:
            continue
        d = int(r.get("eigenvalue_dimension") or r.get("dim") or 1)
        # power sums s_j = trace(a_2^j) over the d embeddings
        s1 = tr[1]
        if d == 1:
            out.append(float(s1))
            continue
        s2 = tr[3] + 2.0 * d          # a_2^2 = a_4 + 2 a_1
        s3 = tr[7] + 4.0 * tr[1]      # a_2^3 = a_8 + 4 a_2
        # Newton's identities for monic x^d + c1 x^{d-1} + ... + cd
        c = [0.0] * (d + 1)           # c[k], c[0] unused
        c[1] = -s1
        c[2] = -(s2 + c[1] * s1) / 2.0
        if d >= 3:
            s4 = tr[15] + 6.0 * tr[3] + 8.0 * d  # a_2^4 = a_16 + 6 a_4 + 8 a_1
            c[3] = -(s3 + c[1] * s2 + c[2] * s1) / 3.0
        if d >= 4:
            c[4] = -(s4 + c[1] * s3 + c[2] * s2 + c[3] * s1) / 4.0
        poly = [1.0] + [c[k] for k in range(1, d + 1)]  # numpy: highest first
        roots = np.roots(poly)
        out.extend(float(x.real) for x in roots if abs(x.imag) < 1e-8)
    return out


def main() -> int:
    t0 = time.time()
    with open(Path("data/lmfdb/lmfdb_sql_weight2.json")) as f:
        recs = json.load(f)

    primes = [n for n in range(11, 100)
              if all(n % d for d in range(2, int(n ** 0.5) + 1))]
    # F_{p^2}^2 supersingular scan is O(p^4) -> keep p <= 47 for runtime
    primes = [p for p in primes if p <= 47]

    rows = []
    exact = diff = no_data = not_reg = 0
    print(f"{'p':>4} {'#ss':>4} {'reg':>4} {'n_a2':>5} {'max|ev|':>8} "
          f"{'bound':>6} {'viol':>5}  match")
    for p in primes:
        js = supersingular_js_fp2(p)
        if not js:
            print(f"{p:4d}: no supersingular j found!")
            continue
        n = len(js)
        try:
            A = brandt_matrix(js, p)
        except AssertionError as e:
            print(f"{p:4d}: {e}")
            rows.append({"p": p, "n_ss": n, "error": str(e)})
            not_reg += 1
            continue
        degs = A.sum(axis=1)
        reg = bool((degs == 3).all())
        ev = np.linalg.eigvals(A.astype(float))
        max_imag = float(np.abs(ev.imag).max())
        evc = ev[np.abs(ev - 3) > 1e-9]   # drop Perron eigenvalue 3 only
        nontriv = np.sort(np.abs(evc))    # moduli (complex pairs share modulus)
        g_sig = np.sort(evc.real)         # signed spectrum (eigenvalues are real)
        mx = float(nontriv.max()) if len(nontriv) else float("nan")
        hk = hecke_a2_at_level(recs, p)
        viol = -1 if not hk else int(
            sum(1 for v in hk if abs(v) > 2 * math.sqrt(2) + 1e-9))
        g = np.sort(nontriv)
        h = np.sort([abs(v) for v in hk]) if hk else np.array([])
        h_sig = np.sort(hk) if hk else np.array([])
        if len(g) == len(h) and len(g) > 0:
            m = "EXACT" if np.allclose(g, h, atol=1e-6) else "DIFF"
            exact += m == "EXACT"
            diff += m == "DIFF"
        elif not hk:
            m = "no-LMFDB"
            no_data += 1
        else:
            m = f"{len(g)}v{len(h)}"
            diff += 1
        if len(g_sig) == len(h_sig) and len(g_sig) > 0:
            m_sig = "EXACT" if np.allclose(g_sig, h_sig, atol=1e-6) else "DIFF"
        elif not hk:
            m_sig = "no-LMFDB"
        else:
            m_sig = f"{len(g_sig)}v{len(h_sig)}"
        print(f"{p:4d} {n:4d} {str(reg):>4} {len(hk):5d} {mx:8.4f} "
              f"{2*math.sqrt(2):6.3f} {viol:5d}  {m}  signed: {m_sig}")
        rows.append({"p": p, "n_ss": n, "regular": reg, "max_abs_ev": round(mx, 6),
                     "n_a2": len(hk), "viol": viol, "match": m, "match_signed": m_sig,
                     "max_imag": max_imag,
                     "nontriv_evs": [round(float(x), 6) for x in nontriv],
                     "signed_evs": [round(float(x), 6) for x in g_sig],
                     "hecke_a2_abs": [round(abs(v), 6) for v in hk],
                     "hecke_a2_signed": [round(float(v), 6) for v in hk],
                     "j_invariants": [[int(x) for x in z] for z in js]})

    print(f"\nEXACT: {exact}  DIFF/partial: {diff}  no-LMFDB: {no_data}  "
          f"errors: {not_reg}  ({time.time()-t0:.0f}s)")
    with open(OUT / "summary.json", "w") as f:
        json.dump({"test": "Exp 22 direct isogeny graph (Brandt/Phi2 multiplicities)"
                   " + Pizer spectrum",
                   "n_exact": exact, "n_diff": diff, "n_nodata": no_data,
                   "rows": rows}, f, indent=1)
    print(f"[DONE] Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
