"""Test PARI Hecke matrix computation for larger primes."""

from cypari2 import Pari
import time
import numpy as np
import json

pari = Pari()
results = []

for p in [37, 67, 89, 131, 199]:
    t0 = time.time()
    dim = int(pari(f"mfdim([{p},2], 1)"))
    if dim == 0:
        print(f"p={p}: dim=0 (no cusp forms)")
        continue
    t1 = time.time()

    # Compute T_2 Hecke matrix
    code = (
        f"my(mf=mfinit([{p},2],1));"
        f"my(B=mfbasis(mf));"
        f"my(M=matrix(#B,#B));"
        f"for(k=1,#B,"
        f"  my(TBk=mfhecke(mf,B[k],2));"
        f"  my(coords=mftobasis(mf,TBk));"
        f"  for(j=1,#B,M[j,k]=coords[j])"
        f");"
        f"M"
    )
    M = pari(code)
    t2 = time.time()

    M_np = np.array(M.python(), dtype=float)
    eigvals = np.linalg.eigvalsh(M_np)
    t3 = time.time()

    print(
        f"p={p:4d} dim={dim:2d} eigvals={np.round(eigvals, 3)}  "
        f"t_init={t1 - t0:.2f}s t_comp={t2 - t1:.2f}s t_eig={t3 - t2:.3f}s"
    )
    results.append(
        {
            "p": p,
            "dim": dim,
            "eigvals": eigvals.tolist(),
            "times": {"init": t1 - t0, "compute": t2 - t1, "eig": t3 - t2},
        }
    )

with open("/workspace/data/pizer_test_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nTotal: {len(results)} primes computed")
