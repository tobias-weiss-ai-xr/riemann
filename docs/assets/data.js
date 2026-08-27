// ---------------------------------------------------------------------------
// research-data.js
//
// Research findings from the GNN × Number Theory investigation of the
// Riemann Hypothesis, embedded for the three.js visualisation.
// All numbers are pulled directly from the project's data/ JSON outputs.
// ---------------------------------------------------------------------------

const RESEARCH = {
  // ----- The headline finding: the dimension split in L-function zero stats
  // 63,844 weight-2 newforms from the LMFDB → 568,708 nearest-neighbour
  // spacings, fitted to the Brody distribution (β interpolates Poisson↔GUE).
  dimensionSplit: {
    totalForms: 63844,
    totalSpacings: 568708,
    // Hecke-field degree / group
    groups: [
      { label: "dim = 1  (CM forms)",  beta: 1.879, n: 34628, ci: [1.870, 1.888], ksGue: 0.0165, regime: "GUE" },
      { label: "dim = 2",               beta: 0.494, n: 8263,  ci: [0.484, 0.503], ksGue: 0.180, regime: "Poisson" },
      { label: "dim = 3",               beta: 0.316, n: 4319,  ci: [0.304, 0.326], ksGue: 0.220, regime: "Poisson" },
      { label: "dim = 4",               beta: 0.213, n: 3157,  ci: [0.202, 0.224], ksGue: 0.247, regime: "Poisson" },
      { label: "dim ≥ 5",               beta: 0.128, n: 13477, ci: [0.123, 0.133], ksGue: 0.266, regime: "Poisson" },
      { label: "all (aggregate)",       beta: 0.620, n: 63844, ci: [0.615, 0.624], ksGue: 0.125, regime: "mixed" },
    ],
    // Reference repulsion levels
    references: [
      { label: "Poisson (β = 0)", beta: 0, color: 0x4f8ef7 },
      { label: "GOE (β = 1)",     beta: 1, color: 0xf0a020 },
      { label: "GUE (β = 2)",     beta: 2, color: 0x33d6a6 },
    ],
    cohensD: 8.808,
    zScore: 101.6,
  },

  // ----- Machine learning on L-function zeros (from multi_task results)
  ml: {
    singleTaskZ1R2: 0.714,
    multiTaskPerZeroR2: {
      z1: 0.704, z2: 0.709, z3: 0.724, z4: 0.735, z5: 0.741,
      z6: 0.745, z7: 0.744, z8: 0.749, z9: 0.710, z10: 0.340,
    },
    benchmark: {
      tracesOnly: 0.962,
      tracesPlusZeros: 0.985,
    },
    note: "sklearn on 53k–63k LMFDB Hecke traces: R² 0.73–0.99. GNNs on Cayley graphs failed (R² < 0).",
  },

  // ----- Cayley graphs of SL(2,F_p) → Ramanujan / spectral gap connection
  cayley: {
    regularity: 4,
    ramanujanBound: 2 * Math.sqrt(3), // ≈ 3.464 for 4-regular
    ramanujanBoundStr: "2√3 ≈ 3.464",
    primes: [
      { p: 3,  ramanujan: true,  order: 24,    lambda2: null },
      { p: 5,  ramanujan: true,  order: 120,   lambda2: null },
      { p: 7,  ramanujan: false, order: 336 },
      { p: 11, ramanujan: false, order: 1320 },
      { p: 13, ramanujan: false, order: 2184 },
    ],
    pThreeIsRamanujan: true,
    pFiveIsRamanujan: true,
    note: "LPS 1988: p=3,5 are Ramanujan. Hecke eigenvalues ↔ graph eigenvalues ↔ L-functions ↔ ζ(s).",
  },

  // ----- Farey graph (Pollicott–Ruelle transfer operator bridge to RH)
  farey: {
    gapLaw: "gap ≈ 2.6547 · n^(-0.9989) ≈ 2.65 / n",
    baselineR2: 0.9999,
    gnnR2: -7.57,
    note: "Pollicott 2022: RH ⇔ spectral gap of the Farey transfer operator. Gap scales as 1/n.",
  },

  // ----- Zeta-landscape facts (shown in the hero scene)
  zeta: {
    criticalLine: "Re(s) = 1/2",
    firstZerosImag: [
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
    ],
    poleAt: "s = 1",
  },

  // ----- Provenance
  provenance: {
    zenodo: "https://doi.org/10.5281/zenodo.21974748",
    repo: "https://github.com/tobias-weiss-ai-xr/riemann",
    headline:
      "The Montgomery–Odlyzko law is NOT universal: CM forms (dim = 1) are GUE-like (β ≈ 1.88), " +
      "generic non-CM forms (dim ≥ 2) are near-Poisson (β ≈ 0.24). The aggregate β ≈ 0.62 is a mixing artifact.",
  },
};

if (typeof window !== "undefined") window.RESEARCH = RESEARCH;
if (typeof module !== "undefined") module.exports = { RESEARCH };

// Compact L-function correlation-spectrum data (data/phase_transition_spectral/spectral_analysis.json)
RESEARCH.spectral = [{"dim": 1, "n_forms": 57270, "effective_rank": 24.888, "spectral_entropy_norm": 0.9993, "top1_concentration": 0.0493, "top_eigs": [1.2331, 1.1262, 1.0837, 1.0519, 1.0344, 1.0282, 1.0238, 1.0159, 1.0031, 0.9989, 0.9925, 0.9877]}, {"dim": 2, "n_forms": 24377, "effective_rank": 24.27, "spectral_entropy_norm": 0.9958, "top1_concentration": 0.0656, "top_eigs": [1.64, 1.2977, 1.2156, 1.1279, 1.0872, 1.0623, 1.0402, 1.0353, 1.0033, 0.991, 0.9744, 0.9635]}, {"dim": 3, "n_forms": 11964, "effective_rank": 23.1, "spectral_entropy_norm": 0.9891, "top1_concentration": 0.0822, "top_eigs": [2.0546, 1.5768, 1.387, 1.1598, 1.0912, 1.0735, 1.0432, 1.0206, 0.9957, 0.9767, 0.931, 0.912]}, {"dim": 4, "n_forms": 9438, "effective_rank": 21.835, "spectral_entropy_norm": 0.9816, "top1_concentration": 0.0977, "top_eigs": [2.4429, 1.721, 1.4482, 1.2457, 1.101, 1.0948, 1.0833, 1.0191, 1.0083, 0.9714, 0.9208, 0.8992]}, {"dim": 5, "n_forms": 5704, "effective_rank": 19.444, "spectral_entropy_norm": 0.966, "top1_concentration": 0.1217, "top_eigs": [3.042, 2.0978, 1.599, 1.2758, 1.1392, 1.0949, 1.0313, 1.0187, 0.9832, 0.9499, 0.8715, 0.8578]}, {"dim": 6, "n_forms": 5895, "effective_rank": 18.677, "spectral_entropy_norm": 0.9606, "top1_concentration": 0.1304, "top_eigs": [3.2592, 2.1567, 1.6375, 1.2515, 1.1674, 1.1191, 1.0405, 1.0094, 0.9876, 0.9497, 0.8531, 0.8276]}, {"dim": 7, "n_forms": 3691, "effective_rank": 16.072, "spectral_entropy_norm": 0.9386, "top1_concentration": 0.1556, "top_eigs": [3.8912, 2.5685, 1.7506, 1.3614, 1.1267, 1.1236, 1.0164, 0.9981, 0.9752, 0.9046, 0.8054, 0.7812]}, {"dim": 8, "n_forms": 4282, "effective_rank": 15.878, "spectral_entropy_norm": 0.9369, "top1_concentration": 0.1598, "top_eigs": [3.9952, 2.4951, 1.7235, 1.4201, 1.1459, 1.0756, 1.0514, 1.0033, 0.9854, 0.921, 0.8373, 0.7567]}, {"dim": 9, "n_forms": 3020, "effective_rank": 13.629, "spectral_entropy_norm": 0.914, "top1_concentration": 0.1881, "top_eigs": [4.7021, 2.7483, 1.8593, 1.4186, 1.1204, 1.0507, 1.0052, 0.972, 0.9282, 0.8676, 0.767, 0.7104]}, {"dim": 10, "n_forms": 3178, "effective_rank": 13.601, "spectral_entropy_norm": 0.9124, "top1_concentration": 0.1874, "top_eigs": [4.6847, 2.7383, 1.8626, 1.495, 1.1493, 1.0469, 1.0245, 0.9927, 0.9708, 0.8558, 0.8213, 0.7109]}, {"dim": 11, "n_forms": 2316, "effective_rank": 11.92, "spectral_entropy_norm": 0.8901, "top1_concentration": 0.2103, "top_eigs": [5.2574, 3.0144, 1.9805, 1.4287, 1.0843, 1.0618, 1.004, 0.9572, 0.8885, 0.8749, 0.8136, 0.6597]}, {"dim": 12, "n_forms": 3005, "effective_rank": 12.461, "spectral_entropy_norm": 0.9009, "top1_concentration": 0.2095, "top_eigs": [5.2364, 2.636, 1.8627, 1.3801, 1.2051, 1.0413, 1.0022, 0.9522, 0.9234, 0.8484, 0.8024, 0.6935]}];
