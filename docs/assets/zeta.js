// ---------------------------------------------------------------------------
// zeta.js — Riemann zeta via Euler–Maclaurin summation (complex argument).
//
// Accurate enough for an interactive 1-D cross-section |ζ(σ + i t)|. Not a
// high-precision library — the heavy 2-D surface is precomputed in
// zeta-data.json (scripts/precompute_zeta_surface.py).
// ---------------------------------------------------------------------------

const _BERN = [
  1 / 6, -1 / 30, 1 / 42, -1 / 30, 5 / 66, -691 / 2730,
  7 / 6, -3617 / 510, 43867 / 798, -174611 / 330,
  854513 / 138, -236364091 / 2730,
];

function _fact(n) {
  let f = 1;
  for (let i = 2; i <= n; i++) f *= i;
  return f;
}

// ζ(s) for complex s = {re, im}.  Returns {re, im}.
function zetaEM(s, N = 90, M = 14) {
  const re = s.re, im = s.im;
  let totalRe = 0, totalIm = 0;

  // Σ_{n=1}^{N-1} n^{-s}
  for (let n = 1; n < N; n++) {
    const ln = Math.log(n);
    const r = Math.exp(-re * ln);
    totalRe += r * Math.cos(im * ln);
    totalIm += -r * Math.sin(im * ln);
  }

  // N^{1-s} / (s - 1)
  if (Math.abs(re - 1) > 1e-9 || Math.abs(im) > 1e-9) {
    const lnN = Math.log(N);
    const e = Math.exp((1 - re) * lnN);
    const n1msRe = e * Math.cos(im * lnN);
    const n1msIm = -e * Math.sin(im * lnN);
    const dr = re - 1, di = im;
    const d2 = dr * dr + di * di;
    totalRe += (n1msRe * dr + n1msIm * di) / d2;
    totalIm += (n1msIm * dr - n1msRe * di) / d2;
  }

  // (1/2) N^{-s}
  {
    const lnN = Math.log(N);
    const e = Math.exp(-re * lnN);
    totalRe += 0.5 * e * Math.cos(im * lnN);
    totalIm += -0.5 * e * Math.sin(im * lnN);
  }

  // Bernoulli correction terms
  let riseRe = re, riseIm = im; // s^{(1)}
  let nRe = Math.exp(-(re + 1) * Math.log(N)); // N^{-s-1}
  let nIm = 0;
  for (let k = 1; k <= M; k++) {
    if (k - 1 < _BERN.length) {
      const b = _BERN[k - 1] / _fact(2 * k);
      // term = b * rising * N^{-s-2k+1}
      totalRe += b * (riseRe * nRe - riseIm * nIm);
      totalIm += b * (riseRe * nIm + riseIm * nRe);
    }
    // rising → rising * (s + 2k - 1)(s + 2k)
    const a = { re: re + 2 * k - 1, im: im };
    const c = { re: re + 2 * k, im: im };
    const nr = riseRe * a.re - riseIm * a.im;
    const ni = riseRe * a.im + riseIm * a.re;
    riseRe = nr * c.re - ni * c.im;
    riseIm = nr * c.im + ni * c.re;
    // N^{-s-2k+1} → * N^{-2}
    const m = Math.exp(-2 * Math.log(N));
    const tr = nRe * m;
    nIm = nIm * m;
    nRe = tr;
  }
  return { re: totalRe, im: totalIm };
}

function zetaAbs(sig, t) {
  const z = zetaEM({ re: sig, im: t });
  return Math.hypot(z.re, z.im);
}

if (typeof window !== "undefined") {
  window.zetaEM = zetaEM;
  window.zetaAbs = zetaAbs;
}
if (typeof module !== "undefined") module.exports = { zetaEM, zetaAbs };
