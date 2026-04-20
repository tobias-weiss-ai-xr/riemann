"""Test PARI Hecke matrices for many primes × multiple ℓ values."""

from cypari2 import Pari
import time
import numpy as np
import json
import itertools

pari = Pari()

# Primes to test (up to ~500)
test_primes = [37, 67, 89, 131, 199, 277, 349, 401, 499]
ell_values = [2, 3, 5, 7, 11, 13]


def compute_hecke_matrix(p, ell):
    """Compute T_ell Hecke matrix on S_2(Gamma_0(p)) via PARI."""
    code = (
        f"my(mf=mfinit([{p},2],1));"
        f"my(B=mfbasis(mf));"
        f"my(M=matrix(#B,#B));"
        f"for(k=1,#B,"
        f"  my(TBk=mfhecke(mf,B[k],{ell}));"
        f"  my(coords=mftobasis(mf,TBk));"
        f"  for(j=1,#B,M[j,k]=coords[j])"
        f");"
        f"M"
    )
    return pari(code)


results = []
total_start = time.time()

for p in test_primes:
    t0 = time.time()
    dim = int(pari(f"mfdim([{p},2], 1)"))
    if dim == 0:
        print(f"p={p}: dim=0 (skip)")
        continue
    t1 = time.time()

    # Compute matrices for all ℓ values
    matrices = {}
    for ell in ell_values:
        M = compute_hecke_matrix(p, ell)
        M_np = np.array(M.python(), dtype=float)
        eigvals = np.linalg.eigvalsh(M_np)
        matrices[ell] = {"matrix": M_np, "eigenvalues": eigvals}

    t2 = time.time()

    entry = {"p": p, "dim": dim, "ells": {}}
    for ell in ell_values:
        eigs = matrices[ell]["eigenvalues"]
        entry["ells"][str(ell)] = {
            "eigenvalues": np.round(eigs, 6).tolist(),
            "max_eig": float(np.max(eigs)),
            "min_eig": float(np.min(eigs)),
            "deligne_bound": float(2 * np.sqrt(ell)),
            "satisfies_deligne": bool(np.all(np.abs(eigs) <= 2 * np.sqrt(ell) + 1e-6)),
        }

    results.append(entry)
    print(
        f"p={p:4d} dim={dim:2d} | "
        + " | ".join(
            f"T_{ell:2d}: [{min(matrices[ell]['eigenvalues']):.1f},{max(matrices[ell]['eigenvalues']):.1f}]"
            for ell in ell_values
        )
        + f" | {t2 - t0:.2f}s"
    )

total_time = time.time() - total_start
print(
    f"\nTotal: {len(results)} primes × {len(ell_values)} ℓ values in {total_time:.2f}s"
)

# Cross-ℓ analysis: correlation between T_2 and T_3 eigenvalues
print("\n=== Cross-ℓ Eigenvalue Correlation ===")
for r in results:
    if 2 in [int(e) for e in r["ells"]] and 3 in [int(e) for e in r["ells"]]:
        e2 = np.array(r["ells"]["2"]["eigenvalues"])
        e3 = np.array(r["ells"]["3"]["eigenvalues"])
        corr = np.corrcoef(e2, e3)[0, 1] if len(e2) > 1 else float("nan")
        print(f"p={r['p']:4d}: corr(T2,T3)={corr:.4f}")

with open("/workspace/data/pizer_dataset_test.json", "w") as f:
    json.dump(results, f, indent=2)
