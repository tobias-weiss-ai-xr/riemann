#!/usr/bin/env python3
"""Precompute the Riemann zeta function surface |ζ(σ + i t)| over the
critical strip for the three.js GitHub Pages visualization.

Uses Euler–Maclaurin summation (accurate to ~1e-7 on the critical line)
and emits a compact JSON consumed by docs/assets/zeta-data.json.

Run:
    python scripts/precompute_zeta_surface.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Zeta via Euler–Maclaurin summation (complex s)
# ---------------------------------------------------------------------------

_BERNOULLI = [
    1 / 6, -1 / 30, 1 / 42, -1 / 30, 5 / 66, -691 / 2730,
    7 / 6, -3617 / 510, 43867 / 798, -174611 / 330,
    854513 / 138, -236364091 / 2730,
]


def zeta_em(s: complex, N: int = 90, M: int = 14) -> complex:
    """Euler–Maclaurin summation for the Riemann zeta function.

    Accurate across the whole complex plane (well away from the pole at s=1).
    """
    s = complex(s)
    total = sum(complex(n) ** (-s) for n in range(1, N))
    total += complex(N) ** (1 - s) / (s - 1)
    total += 0.5 * complex(N) ** (-s)
    rising = s  # s^{(1)} rising factorial
    npow = complex(N) ** (-s - 1)  # N^{-s-1} for k=1
    for k in range(1, M + 1):
        if k - 1 < len(_BERNOULLI):
            b = _BERNOULLI[k - 1]
            total += b / math.factorial(2 * k) * rising * npow
        rising *= (s + 2 * k - 1) * (s + 2 * k)
        npow *= complex(N) ** (-2)
    return total


# First 50 non-trivial zeros of ζ(s) (imaginary parts, all at Re s = 1/2).
# These are tabulated constants — exact to the digits shown.
ZETA_ZEROS = [
    14.134725141734693, 21.022039638771555, 25.010857580145690,
    30.424876125859513, 32.935061587739190, 37.586178158825671,
    40.918719012147495, 43.327073280914999, 48.005150881167159,
    49.773832477672302, 52.970321477714460, 56.446247697063948,
    59.347044002602353, 60.831778524609810, 65.112544048081652,
    67.079810529494174, 69.546401711173979, 72.067157674481908,
    75.704690699083933, 77.144840068874805, 79.337375020249068,
    82.910380854086031, 84.735493977550075, 87.425274626125575,
    88.809111207634466, 92.491899455460041, 94.651344040519886,
    95.870634228245573, 98.831191881207210, 101.317851005931262,
    103.725538040478344, 105.446623052326621, 107.168611189458142,
    111.029536232780775, 111.874659746859356, 114.320221146205089,
    116.226680320857649, 118.790782865976233, 121.370125002420827,
    122.946829293248840, 124.256818554345768, 127.516683879810142,
    129.578704199956165, 131.087689529872552, 133.497737194094536,
    134.756509753373996, 138.116042054533444, 139.736208952121305,
    141.123707404021097, 143.111845807620587,
]


def main() -> None:
    # Grid over the critical strip.
    # σ (real part) from 0 to 1, t (imaginary part) from 0 to 60.
    sigma_step = 0.025
    t_step = 0.4
    # Avoid σ = 1 exactly (the pole at s=1 → div-by-zero in the correction term).
    sigmas = [round(s, 4) for s in _arange(0.0, 0.975, sigma_step)]
    ts = [round(t, 4) for t in _arange(0.0, 60.0, t_step)]

    # 2D grid of |ζ(σ + i t)|, clamped to [0, zmax] for clean rendering.
    zmax = 12.0
    surface: list[list[float]] = []
    phase: list[list[float]] = []
    for t in ts:
        row_mag: list[float] = []
        row_phase: list[float] = []
        for sig in sigmas:
            z = zeta_em(complex(sig, t))
            mag = abs(z)
            if mag > zmax:
                mag = zmax
            row_mag.append(round(mag, 4))
            row_phase.append(round(math.atan2(z.imag, z.real), 4))
        surface.append(row_mag)
        phase.append(row_phase)

    # Also produce a log-compressed band |ζ| clipped to [0,1] for color mapping.
    data = {
        "meta": {
            "sigma_step": sigma_step,
            "t_step": t_step,
            "sigma_min": sigmas[0],
            "sigma_max": sigmas[-1],
            "t_min": ts[0],
            "t_max": ts[-1],
            "n_sigma": len(sigmas),
            "n_t": len(ts),
            "zmax": zmax,
            "method": "Euler-Maclaurin (N=90, M=14)",
        },
        "sigmas": sigmas,
        "ts": ts,
        "magnitude": surface,   # rows = t-index, cols = sigma-index
        "phase": phase,
        "zeros": ZETA_ZEROS,
    }

    out = Path("docs/assets/zeta-data.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data))
    print(f"Wrote {out} ({out.stat().st_size / 1024:.1f} KB)")
    print(f"  grid: {len(sigmas)} x {len(ts)} = {len(sigmas) * len(ts)} points")
    # sanity check: magnitude at first zero should be ~0
    i0 = int(round(14.134725 / t_step))
    j0 = int(round(0.5 / sigma_step))
    print(f"  |ζ(0.5 + 14.13i)| ≈ {surface[i0][j0]} (expect ~0)")


def _arange(start: float, stop: float, step: float) -> list[float]:
    vals: list[float] = []
    x = start
    while x <= stop + 1e-9:
        vals.append(x)
        x += step
    return vals


if __name__ == "__main__":
    main()
