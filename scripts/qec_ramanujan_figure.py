#!/usr/bin/env python3
"""
Figure QEC-01: Ramanujan crossover for the toric-code decoding graph.

The Z-syndrome graph of the toric code is the Cayley graph C(Z_d^2, ±e1, ±e2),
4-regular. Its second eigenvalue is λ₂ = 2 + 2cos(2π/d) (analytic). The
Ramanujan bound is B = 2√3 ≈ 3.4641. For odd d the graph is non-bipartite and
the binding eigenvalue is the most-negative nontrivial one.

Saves: data/qec_spectral/qec_ramanujan_crossover.png
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path("data/qec_spectral")
data = json.load(open(OUT / "qec_decoding_spectra_results.json"))
scaling = data["toric_ramanujan_scaling"]
ds = [r["d"] for r in scaling]
lam2 = [r["lambda2_adjacency"] for r in scaling]
bound = [r["ramanujan_bound"] for r in scaling]
ram = [r["is_ramanujan"] for r in scaling]
# analytic
d_cont = np.linspace(2, 16, 400)
lam2_ana = 2 + 2 * np.cos(2 * np.pi / d_cont)

fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
ax.axhline(2 * np.sqrt(3), color="#dc2626", ls="--", lw=1.4, label=r"Ramanujan bound $B = 2\sqrt{3}$")
ax.plot(d_cont, lam2_ana, color="#8b5cf6", lw=2.2, label=r"analytic $\lambda_2 = 2 + 2\cos(2\pi/d)$")
for d, l2, isr in zip(ds, lam2, ram):
    color = "#22c55e" if isr else "#ef4444"
    ax.plot(d, l2, "o", color=color, ms=7, zorder=5)
ax.plot([d for d, r in zip(ds, ram) if r], [l for d, l, r in zip(ds, lam2, ram) if r], "o", color="#22c55e", ms=7, label="Ramanujan (numerics)")
ax.plot([d for d, r in zip(ds, ram) if not r], [l for d, l, r in zip(ds, lam2, ram) if not r], "o", color="#ef4444", ms=7, label="not expander (needs MWPM-class decoder)")
ax.set_xlabel("toric code size $d$ (syndrome graph $= C(\\mathbb{Z}_d^2, \\pm e_1, \\pm e_2)$)")
ax.set_ylabel("second eigenvalue $\\lambda_2$")
ax.set_title("Toric-code decoding graph: Ramanujan crossover at $d \\approx 7$")
ax.legend(loc="lower right", fontsize=9)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "qec_ramanujan_crossover.png")
print("saved", OUT / "qec_ramanujan_crossover.png")
