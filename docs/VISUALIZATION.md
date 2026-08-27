# Visualizing the Riemann Hypothesis — interactive 3D page

An interactive [three.js](https://threejs.org/) page that visualises the Riemann
Hypothesis and the findings of this project (GNN × Number Theory → RH).

Live at `https://<user>.github.io/riemann/` once GitHub Pages is enabled.

## Scenes

| Tab | What it shows | Source |
|---|---|---|
| **ζ Landscape** | 3D surface of `|ζ(σ + i t)|` over the critical strip `0 ≤ σ ≤ 1`, `0 ≤ t ≤ 60`. The cyan line is `Re(s) = ½`; the golden orbs are the first non-trivial zeros; the spike at `σ → 1` is the pole at `s = 1`. | `assets/zeta-data.json` (precomputed via `scripts/precompute_zeta_surface.py`, Euler–Maclaurin) |
| **Critical Line** | `|ζ(½ + i t)|` for `0 ≤ t ≤ 80`, evaluated live in the browser. Every dip to zero is a non-trivial zero. | live `assets/zeta.js` |
| **Dimension Split** | Brody repulsion parameter `β` per Hecke-field dimension. CM forms (dim = 1) are GUE-like (`β ≈ 1.88`); non-CM forms (dim ≥ 2) are near-Poisson (`β ≈ 0.24`); the aggregate `β ≈ 0.62` is a mixing artifact. | `data/spectral_rigidity/*` |
| **GUE → Poisson** | The Brody distribution `P(s;β)` as `β` sweeps `0 → 2` — a waterfall through the phase transition. | analytic |
| **L-Function Spectrum** | Top-12 correlation-matrix eigenvalues per dimension; the leading eigenvalue fans upward as effective rank collapses with dimension. | `data/phase_transition_spectral/spectral_analysis.json` |

## Files

```
docs/
├── index.html              ← page + import map (three.js r160 via jsDelivr CDN)
├── VISUALIZATION.md        ← this file
└── assets/
    ├── style.css
    ├── data.js             ← research findings (RESEARCH global)
    ├── zeta.js             ← live ζ(s) via Euler–Maclaurin
    ├── viz.js              ← three.js scenes + scene controller
    └── zeta-data.json      ← precomputed |ζ| surface grid (40 × 151 points)
scripts/
└── precompute_zeta_surface.py   ← regenerate zeta-data.json
```

## Regenerate the ζ surface

```bash
python scripts/precompute_zeta_surface.py   # writes docs/assets/zeta-data.json
```

## Local preview

Serve over HTTP (ES modules + `fetch` do not work from `file://`):

```bash
cd docs && python3 -m http.server 8099
# open http://localhost:8099/
```

## Enabling GitHub Pages

- **Easiest:** repo Settings → Pages → Build and deployment → Source = *Deploy from a
  branch* → Branch = `master`, Folder = `/docs`.
- **CI:** push this repo; the `.github/workflows/pages.yml` workflow deploys `docs/` via
  the official Pages action (Settings → Pages → Source = *GitHub Actions*).
