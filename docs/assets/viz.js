// ===========================================================================
//  viz.js — interactive three.js visualisation of the Riemann Hypothesis
//  Scenes:  ζ Landscape · Critical Line · Dimension Split · GUE→Poisson · Spectrum
// ===========================================================================

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// Globals provided by the classic scripts data.js / zeta.js (loaded before this module).
const RESEARCH = window.RESEARCH;
const zetaAbs = window.zetaAbs;

let zetaData = null;
let renderer, scene, camera, controls, clock;
let currentGroup = null;
let currentUpdate = null;
let glowTex = null;
let selectedNode = null;   // approaches scene pick state
let hoverNode = null;

const canvas = document.getElementById('scene');
const infoTitle = document.getElementById('info-title');
const infoBody = document.getElementById('info-body');
const infoPanel = document.getElementById('info');
const loadingEl = document.getElementById('loading');
const footText = document.getElementById('foot-text');

// ---------------------------------------------------------------------------
//  Small math / colour helpers
// ---------------------------------------------------------------------------

const lerp = (a, b, t) => a + (b - a) * t;
const map = (v, a, b, c, d) => c + ((v - a) / (b - a)) * (d - c);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// Inferno-like colormap, v in [0,1] → {r,g,b} in [0,1]
const INFERNO = [
  [0.001, 0.000, 0.070],
  [0.270, 0.040, 0.390],
  [0.730, 0.170, 0.290],
  [0.960, 0.580, 0.110],
  [1.000, 0.990, 0.760],
];
function inferno(v) {
  v = clamp(v, 0, 1);
  const x = v * (INFERNO.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = INFERNO[i];
  const b = INFERNO[Math.min(i + 1, INFERNO.length - 1)];
  return { r: lerp(a[0], b[0], f), g: lerp(a[1], b[1], f), b: lerp(a[2], b[2], f) };
}

// Log-gamma (Lanczos) + gamma
function lgamma(z) {
  const g = 7;
  const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
  if (z < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * z)) - lgamma(1 - z);
  z -= 1;
  let x = c[0];
  for (let i = 1; i < g + 2; i++) x += c[i] / (z + i);
  const t = z + g + 0.5;
  return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(x);
}
const gamma = (z) => Math.exp(lgamma(z));

// Brody level-spacing distribution P(s; β)
function brody(s, b) {
  if (b <= 1e-6 || s <= 0) return (b <= 1e-6) ? Math.exp(-s) : 0;
  const a = Math.pow(gamma((b + 2) / (b + 1)) / (b + 1), b + 1);
  return (b + 1) * a * Math.pow(s, b) * Math.exp(-a * Math.pow(s, b + 1));
}

// ---------------------------------------------------------------------------
//  Sprite helpers (text labels + glow halos)
// ---------------------------------------------------------------------------

function makeGlowTexture() {
  const s = 128;
  const cv = document.createElement('canvas');
  cv.width = cv.height = s;
  const ctx = cv.getContext('2d');
  const g = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
  g.addColorStop(0.0, 'rgba(255,255,255,1)');
  g.addColorStop(0.25, 'rgba(255,255,255,0.65)');
  g.addColorStop(1.0, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, s, s);
  const tex = new THREE.CanvasTexture(cv);
  return tex;
}

function makeGlow(colorHex, size = 1) {
  const mat = new THREE.SpriteMaterial({
    map: glowTex, color: colorHex, transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.9,
  });
  const sp = new THREE.Sprite(mat);
  sp.scale.set(size, size, size);
  return sp;
}

function makeLabel(text, opts = {}) {
  const { color = '#e8ecf4', size = 44, mono = true, bg = null } = opts;
  const pad = 12;
  const cv = document.createElement('canvas');
  const ctx = cv.getContext('2d');
  const font = `${size}px ${mono ? 'ui-monospace, Menlo, Consolas, monospace' : 'sans-serif'}`;
  ctx.font = font;
  const w = Math.ceil(ctx.measureText(text).width) + pad * 2;
  const h = size + pad * 2;
  cv.width = w; cv.height = h;
  ctx.font = font;
  if (bg) {
    ctx.fillStyle = bg;
    ctx.roundRect ? ctx.roundRect(0, 0, w, h, 8) : ctx.rect(0, 0, w, h);
    ctx.fill();
  }
  ctx.fillStyle = color;
  ctx.textBaseline = 'middle';
  ctx.fillText(text, pad, h / 2 + 1);
  const tex = new THREE.CanvasTexture(cv);
  tex.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, depthTest: false });
  const sp = new THREE.Sprite(mat);
  const scale = 0.012;
  sp.scale.set(w * scale, h * scale, 1);
  sp.userData.aspect = w / h;
  return sp;
}

// ---------------------------------------------------------------------------
//  Scene builders
// ---------------------------------------------------------------------------

function buildLandscape() {
  const g = new THREE.Group();
  const { sigmas, ts, magnitude } = zetaData;
  const { zmax, t_max } = zetaData.meta;
  const nS = sigmas.length, nT = ts.length;
  const X = 6, Z = 16, H = 0.5;

  // Surface mesh
  const positions = new Float32Array(nS * nT * 3);
  const colors = new Float32Array(nS * nT * 3);
  for (let i = 0; i < nT; i++) {
    for (let j = 0; j < nS; j++) {
      const sig = sigmas[j], t = ts[i], mag = magnitude[i][j];
      const idx = (i * nS + j) * 3;
      positions[idx] = (sig - 0.5) * 2 * X;
      positions[idx + 1] = Math.min(mag, zmax) * H;
      positions[idx + 2] = (t / t_max) * 2 * Z - Z;
      const c = inferno(mag / zmax);
      colors[idx] = c.r; colors[idx + 1] = c.g; colors[idx + 2] = c.b;
    }
  }
  const indices = [];
  for (let i = 0; i < nT - 1; i++) {
    for (let j = 0; j < nS - 1; j++) {
      const a = i * nS + j, b = a + 1, c = a + nS, d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({ vertexColors: true, metalness: 0.25, roughness: 0.65, side: THREE.DoubleSide });
  g.add(new THREE.Mesh(geo, mat));

  // Wireframe overlay
  const wire = new THREE.LineSegments(
    new THREE.WireframeGeometry(geo),
    new THREE.LineBasicMaterial({ color: 0x3fe0ff, transparent: true, opacity: 0.10 })
  );
  g.add(wire);

  // Critical line (σ = 1/2 → x = 0)
  const clPts = [new THREE.Vector3(0, 0.02, -Z), new THREE.Vector3(0, 0.02, Z)];
  const clCurve = new THREE.LineCurve3(clPts[0], clPts[1]);
  const clTube = new THREE.Mesh(
    new THREE.TubeGeometry(clCurve, 2, 0.05, 8, false),
    new THREE.MeshStandardMaterial({ color: 0x3fe0ff, emissive: 0x1b9ec0, emissiveIntensity: 0.8 })
  );
  g.add(clTube);
  g.add(makeGlow(0x3fe0ff, 0.9).translateX(0).translateY(0.02).translateZ(Z - 1));

  // Zeros as glowing orbs on the critical line
  const zeroMeshes = [];
  zetaData.zeros.forEach((t, k) => {
    if (t > t_max) return;
    const z = (t / t_max) * 2 * Z - Z;
    const orb = new THREE.Mesh(
      new THREE.SphereGeometry(0.17, 20, 20),
      new THREE.MeshStandardMaterial({ color: 0xffcf5c, emissive: 0xffcf5c, emissiveIntensity: 1.4 })
    );
    orb.position.set(0, 0.05, z);
    const halo = makeGlow(0xffcf5c, 1.3);
    halo.position.set(0, 0.05, z);
    g.add(orb); g.add(halo);
    zeroMeshes.push({ orb, halo, phase: k * 0.7 });
  });

  // Faint ground grid
  const grid = new THREE.GridHelper(2 * Z + 6, 24, 0x16203a, 0x0c1322);
  grid.position.y = -0.05;
  g.add(grid);

  function update(dt, t) {
    zeroMeshes.forEach((zr) => {
      const s = 1 + 0.28 * Math.sin(t * 2.2 + zr.phase);
      zr.halo.scale.setScalar(1.3 * s);
      zr.orb.material.emissiveIntensity = 1.0 + 0.6 * s;
    });
  }
  return { group: g, update };
}

function buildCritical() {
  const g = new THREE.Group();
  const tMax = 80, step = 0.25, X = 16, Y = 3.4;
  const pts = [];
  const vals = [];
  for (let t = 0; t <= tMax; t += step) {
    const v = zetaAbs(0.5, t);
    vals.push(v);
    pts.push(new THREE.Vector3(map(t, 0, tMax, -X, X), Math.min(v, 2.2) * Y, 0));
  }
  const curve = new THREE.CatmullRomCurve3(pts);
  const tube = new THREE.Mesh(
    new THREE.TubeGeometry(curve, pts.length, 0.06, 8, false),
    new THREE.MeshStandardMaterial({ color: 0x3fe0ff, emissive: 0x2a83a8, emissiveIntensity: 0.7, metalness: 0.3, roughness: 0.5 })
  );
  g.add(tube);

  // Zero-level reference plane
  const plane = new THREE.Mesh(
    new THREE.PlaneGeometry(2 * X, 3),
    new THREE.MeshBasicMaterial({ color: 0x0e1830, transparent: true, opacity: 0.4, side: THREE.DoubleSide })
  );
  plane.rotation.x = -Math.PI / 2;
  g.add(plane);

  // Mark the first zeros where the curve crosses zero
  const zeroMeshes = [];
  zetaData.zeros.forEach((t, k) => {
    if (t > tMax) return;
    const x = map(t, 0, tMax, -X, X);
    const orb = new THREE.Mesh(
      new THREE.SphereGeometry(0.2, 18, 18),
      new THREE.MeshStandardMaterial({ color: 0xffcf5c, emissive: 0xffcf5c, emissiveIntensity: 1.3 })
    );
    orb.position.set(x, 0.1, 0);
    const halo = makeGlow(0xffcf5c, 1.5);
    halo.position.set(x, 0.1, 0);
    g.add(orb); g.add(halo);
    zeroMeshes.push({ halo, orb, phase: k * 0.6 });
  });

  // t-axis label ticks
  [0, 14.13, 21.02, 25.01, 30.42, 40.92, 60].forEach((t) => {
    if (t > tMax) return;
    const lab = makeLabel(`${t}`, { color: '#5d6884', size: 30 });
    lab.position.set(map(t, 0, tMax, -X, X), -0.9, 0.6);
    g.add(lab);
  });

  function update(dt, t) {
    zeroMeshes.forEach((zr) => {
      const s = 1 + 0.3 * Math.sin(t * 2 + zr.phase);
      zr.halo.scale.setScalar(1.5 * s);
    });
  }
  return { group: g, update };
}

function buildDimension() {
  const g = new THREE.Group();
  const groups = RESEARCH.dimensionSplit.groups; // 6 entries
  const refs = RESEARCH.dimensionSplit.references;
  const Y = 2.4; // scale: β=2 → 4.8
  const spacing = 2.2;
  const x0 = -((groups.length - 1) * spacing) / 2;

  groups.forEach((grp, k) => {
    const x = x0 + k * spacing;
    const h = grp.beta * Y;
    const color = grp.regime === 'GUE' ? 0x33d6a6 : grp.regime === 'Poisson' ? 0x4f8ef7 : 0xff5cc8;
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(1.1, h, 1.1),
      new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.35, metalness: 0.3, roughness: 0.5 })
    );
    bar.position.set(x, h / 2, 0);
    g.add(bar);
    // halo on top
    const top = makeGlow(color, 1.6);
    top.position.set(x, h + 0.3, 0);
    g.add(top);
    // label
    const lab = makeLabel(`${grp.label}  β=${grp.beta.toFixed(2)}`, { color: '#dfe6f2', size: 30 });
    lab.position.set(x, h + 0.9, 0);
    g.add(lab);
    const nLab = makeLabel(`${grp.n.toLocaleString()} forms`, { color: '#6f7891', size: 24 });
    nLab.position.set(x, -0.8, 0);
    g.add(nLab);
  });

  // Reference planes: Poisson β=0, GOE β=1, GUE β=2
  const span = (groups.length) * spacing;
  refs.forEach((r) => {
    const y = r.beta * Y;
    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(span + 1.5, 4),
      new THREE.MeshBasicMaterial({ color: r.color, transparent: true, opacity: 0.10, side: THREE.DoubleSide })
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = y;
    g.add(plane);
    const lab = makeLabel(r.label, { color: '#' + r.color.toString(16).padStart(6, '0'), size: 28 });
    lab.position.set(x0 + span / 2 + 1.4, y, 0);
    g.add(lab);
  });

  return { group: g, update: null };
}

function buildBrody() {
  const g = new THREE.Group();
  const betas = [0, 0.5, 1, 1.5, 2];
  const betaColors = [0x4f8ef7, 0x7e6ff0, 0xf0a020, 0xff7a3c, 0x33d6a6];
  const sMax = 4.5, X = 7, Y = 3.2, depth = 2.4;
  const z0 = -((betas.length - 1) * depth) / 2;

  betas.forEach((b, k) => {
    const z = z0 + k * depth;
    const pts = [];
    for (let s = 0; s <= sMax; s += 0.05) {
      const p = brody(s, b);
      pts.push(new THREE.Vector3(map(s, 0, sMax, -X, X), p * Y, z));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    const tube = new THREE.Mesh(
      new THREE.TubeGeometry(curve, pts.length, 0.05, 8, false),
      new THREE.MeshStandardMaterial({ color: betaColors[k], emissive: betaColors[k], emissiveIntensity: 0.55, roughness: 0.45 })
    );
    g.add(tube);
    const lab = makeLabel(`β = ${b.toFixed(1)}`, { color: '#' + betaColors[k].toString(16).padStart(6, '0'), size: 30 });
    lab.position.set(-X - 1.4, 0.4, z);
    g.add(lab);
  });
  // s-axis tick
  [0, 1, 2, 3, 4].forEach((s) => {
    const lab = makeLabel(`${s}`, { color: '#5d6884', size: 26 });
    lab.position.set(map(s, 0, sMax, -X, X), -0.7, z0 - 1);
    g.add(lab);
  });
  const axisLab = makeLabel('nearest-neighbour spacing s', { color: '#6f7891', size: 26 });
  axisLab.position.set(0, -1.4, z0 - 1);
  g.add(axisLab);

  return { group: g, update: null };
}

function buildSpectral() {
  const g = new THREE.Group();
  const spec = RESEARCH.spectral; // dims 1..12
  const Y = 0.62, xSpacing = 0.5, zSpacing = 1.5;
  const z0 = -((spec.length - 1) * zSpacing) / 2;
  const maxEig = 5.5;

  spec.forEach((row, i) => {
    const z = z0 + i * zSpacing;
    row.top_eigs.forEach((eig, j) => {
      const x = (j - row.top_eigs.length / 2) * xSpacing;
      const h = (eig / maxEig) * 4.2;
      const c = inferno(clamp(eig / maxEig, 0, 1));
      const bar = new THREE.Mesh(
        new THREE.BoxGeometry(0.34, Math.max(h, 0.02), 0.34),
        new THREE.MeshStandardMaterial({
          color: new THREE.Color(c.r, c.g, c.b),
          emissive: new THREE.Color(c.r, c.g, c.b), emissiveIntensity: 0.3, roughness: 0.55,
        })
      );
      bar.position.set(x, Math.max(h, 0.02) / 2, z);
      g.add(bar);
    });
    // dim label
    const lab = makeLabel(`dim ${row.dim}  ·  rk ${row.effective_rank.toFixed(1)}`, { color: '#8a93a8', size: 26 });
    lab.position.set(7.0, 0.4, z);
    g.add(lab);
  });
  // eigenvalue-index axis label
  const ax = makeLabel('correlation-matrix eigenvalue  λ₁ … λ₁₂', { color: '#6f7891', size: 26 });
  ax.position.set(0, -1.2, z0 - 1.2);
  g.add(ax);

  return { group: g, update: null };
}

// ---------------------------------------------------------------------------
//  Approaches — interactive strategy map of the attack routes to RH
// ---------------------------------------------------------------------------

const APPROACH_STATUS_COLOR = {
  proven: 0x33d6a6,     // green  — theorem (some Lean-formalised)
  partial: 0xffcf5c,    // gold   — half of a criterion known
  numerical: 0x3fe0ff,  // cyan   — strong convergent numerics
  proposed: 0x7ea8ff,   // blue   — candidate route, untouched
  tool: 0xb08cff,       // violet — hypothesis generator
};

function buildApproaches() {
  const g = new THREE.Group();
  const ap = RESEARCH.approaches;
  const groups = ap.groups;
  const R = 7.2;
  const nGroups = groups.length;
  const nodes = [];

  // Ground guide rings
  [7.2, 4.8, 2.4].forEach((rr) => {
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(rr - 0.025, rr + 0.025, 128),
      new THREE.MeshBasicMaterial({ color: 0x152038, transparent: true, opacity: 0.6, side: THREE.DoubleSide })
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.002;
    g.add(ring);
  });

  // Central RH orb
  const rhOrb = new THREE.Mesh(
    new THREE.SphereGeometry(0.5, 32, 32),
    new THREE.MeshStandardMaterial({ color: 0xffcf5c, emissive: 0xffcf5c, emissiveIntensity: 1.3 })
  );
  g.add(rhOrb);
  const rhHalo = makeGlow(0xffcf5c, 3.1);
  g.add(rhHalo);
  const rhLabel = makeLabel('RH', { color: '#0d0a03', size: 58, bg: 'rgba(255,207,92,0.92)' });
  rhLabel.position.y = -1.15;
  g.add(rhLabel);

  const pickList = [];
  groups.forEach((grp, gi) => {
    const thetaC = (gi / nGroups) * Math.PI * 2 - Math.PI / 2; // group A at "north"
    const items = grp.items;
    const fan = Math.min(0.85, 0.5 + items.length * 0.06);

    // Group label, pulled slightly toward the centre
    const grpPos = new THREE.Vector3(Math.cos(thetaC) * R * 0.62, 0, Math.sin(thetaC) * R * 0.62);
    const glab = makeLabel(grp.name, { color: grp.color, size: 30 });
    glab.position.set(grpPos.x, 1.5, grpPos.z);
    g.add(glab);

    items.forEach((item, k) => {
      const frac = items.length === 1 ? 0 : k / (items.length - 1) - 0.5;
      const theta = thetaC + frac * fan;
      const pos = new THREE.Vector3(Math.cos(theta) * R, 0, Math.sin(theta) * R);
      const color = APPROACH_STATUS_COLOR[item.status] || 0x7ea8ff;

      // Beam from the centre to the node
      const beam = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0.04, 0),
          new THREE.Vector3(pos.x, 0.04, pos.z),
        ]),
        new THREE.LineBasicMaterial({ color: new THREE.Color(grp.color), transparent: true, opacity: 0.18 })
      );
      g.add(beam);

      const orb = new THREE.Mesh(
        new THREE.SphereGeometry(0.34, 24, 24),
        new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.85 })
      );
      orb.position.copy(pos);
      g.add(orb);

      const halo = makeGlow(color, 1.55);
      halo.position.copy(pos);
      g.add(halo);

      const lab = makeLabel(item.label, { color: '#dfe6f2', size: 26 });
      lab.position.set(pos.x, -0.9, pos.z);
      g.add(lab);

      const rec = { item, k, grp, orb, halo, beam, color, label: lab };
      pickList.push({ obj: orb, rec });
      nodes.push(rec);
    });
  });

  function paint() {
    nodes.forEach((r) => {
      const sel = r === selectedNode;
      const hov = r === hoverNode && !sel;
      r.halo.material.opacity = sel ? 0.95 : 0.72;
      r.halo.userData.r = sel ? 2.2 : hov ? 1.9 : 1.55; // target glow radius
      r.orb.material.emissiveIntensity = sel ? 1.5 : hov ? 1.25 : 0.85;
      r.beam.material.opacity = sel ? 0.6 : 0.18;
    });
  }

  const LEGEND =
    '<p class="cite">status&nbsp;· <span class="stat green">bewiesen</span> &nbsp;· ' +
    '<span class="stat gold">teilweise</span> &nbsp;· <span class="stat">numerisch</span> &nbsp;· ' +
    '<span style="color:#7ea8ff">Kandidat</span> &nbsp;· <span style="color:#b08cff">Werkzeug</span>' +
    '&nbsp;— klicke einen Knoten, um eine Herangehensweise zu lesen.</p>';

  function focus(rec) {
    selectedNode = rec;
    if (!rec) return;
    infoTitle.textContent = rec.item.title || rec.item.label;
    infoBody.innerHTML = rec.item.detail + LEGEND;
    infoBody.scrollTop = 0;
    paint();
  }

  g.userData = {
    pickable: pickList,
    focus,
    repaint: paint,
  };

  function update(dt, t) {
    const ps = 1 + 0.16 * Math.sin(t * 2.1);
    rhHalo.scale.setScalar(3.1 * ps);
    nodes.forEach((r) => {
      const target = (r.halo.userData.r || 1.55) * (1 + 0.08 * Math.sin(t * 2 + r.k));
      r.halo.scale.setScalar(THREE.MathUtils.lerp(r.halo.scale.x, target, dt * 5));
    });
  }

  return { group: g, update, defaultFocus: () => focus(nodes[0]) };
}

// ---------------------------------------------------------------------------
//  View registry
// ---------------------------------------------------------------------------

const VIEWS = {
  landscape: {
    title: 'ζ(s) Landscape — the critical strip',
    camera: { pos: [0, 11, 27], target: [0, 1.5, 0], autoRotate: true },
    info: `
      <p>The surface is <span class="stat">|ζ(σ + i t)|</span> over the critical strip
      <strong>0 ≤ σ ≤ 1</strong>, <strong>0 ≤ t ≤ 60</strong>, computed by Euler–Maclaurin
      summation. Height and colour encode magnitude.</p>
      <p>The bright <span class="stat">cyan line</span> is the <strong>critical line Re(s) = ½</strong>.
      The <span class="stat gold">golden orbs</span> are the first non-trivial zeros — points where the
      surface <em>touches zero</em>. If the Riemann Hypothesis is true, <strong>every</strong> such zero lies
      on that line.</p>
      <p>The tall spike at σ → 1 is the <strong>pole at s = 1</strong> of the zeta function.</p>
      <p class="cite">Bridge in this project: Cayley-graph eigenvalues → Hecke eigenvalues → L-functions → ζ(s).</p>
    `,
    build: buildLandscape,
  },
  critical: {
    title: 'The Critical Line — music of the primes',
    camera: { pos: [0, 7.5, 23], target: [0, 1.4, 0], autoRotate: false },
    info: `
      <p>A slice down the critical line: <span class="stat">|ζ(½ + i t)|</span> for
      <strong>0 ≤ t ≤ 80</strong>, evaluated live in your browser. Every dip to zero is a
      <span class="stat gold">non-trivial zero</span>.</p>
      <p>The spacing of these zeros is the deep link to random matrix theory. Montgomery's
      conjecture (1973) and Odlyzko's computations (height ~10²⁰) show the zeros repel each other
      <em>exactly</em> like eigenvalues of large random Hermitian (GUE) matrices.</p>
      <p>This project tested the same statistics on <span class="stat">63,844 LMFDB newforms</span> —
      and found they are <strong>not</strong> universal (see Dimension Split).</p>
    `,
    build: buildCritical,
  },
  dimension: {
    title: 'The Dimension Split — Poisson vs GUE',
    camera: { pos: [0, 7, 19], target: [0, 1.6, 0], autoRotate: false },
    info: `
      <p>The project's headline finding. Fitting <span class="stat">568,708</span> nearest-neighbour
      zero spacings to the Brody distribution gives a repulsion parameter <strong>β</strong>:</p>
      <ul>
        <li><span class="stat green">dim = 1 (CM forms)</span> → <strong>β ≈ 1.88</strong> — indistinguishable from GUE (β = 2) ✅</li>
        <li><span class="stat">dim ≥ 2 (non-CM)</span> → <strong>β ≈ 0.24</strong> — barely above Poisson (β = 0) ❌</li>
        <li><span class="stat gold">aggregate β ≈ 0.62</span> — a <em>mixing artifact</em>, not a real regime</li>
      </ul>
      <p>Separation is extreme: Cohen's <em>d</em> = <strong>8.81</strong>, <em>z</em> = 101.6σ. The
      Montgomery–Odlyzko law holds for CM forms and ζ(s), but <strong>not</strong> for generic non-CM
      L-functions.</p>
    `,
    build: buildDimension,
  },
  brody: {
    title: 'Phase Transition: Poisson → GUE',
    camera: { pos: [16, 9, 22], target: [0, 1.4, 0], autoRotate: false },
    info: `
      <p>The <strong>Brody distribution</strong> <code>P(s; β) ∝ s^β exp(−a s^{β+1})</code> interpolates
      between two universality classes:</p>
      <ul>
        <li><span class="stat">β = 0</span> — Poisson: zeros are uncorrelated (exponential spacing)</li>
        <li><span class="stat gold">β = 2</span> — GUE: quadratic level repulsion, like charged particles</li>
      </ul>
      <p>Non-CM L-functions (dim ≥ 2) sit near <strong>β = 0</strong>; CM forms sit near <strong>β = 2</strong>.
      The aggregate β ≈ 0.62 is simply ~15% GUE + ~85% Poisson. There is a genuine
      <strong>phase transition in arithmetic complexity</strong>.</p>
    `,
    build: buildBrody,
  },
  spectral: {
    title: 'L-Function Correlation Spectrum',
    camera: { pos: [17, 13, 23], target: [0, 1, 0], autoRotate: false },
    info: `
      <p>For each Hecke-field dimension, the top-12 eigenvalues of the L-function correlation matrix.
      As <strong>dim grows</strong>, the leading eigenvalue <span class="stat gold">fans upward</span>
      while the bulk collapses — the <strong>effective rank</strong> drops from 24.9 (dim 1) to ~12 (dim 12).</p>
      <p>This spectral concentration is the linear-algebra face of the dimension split: CM forms
      (dim 1) are spectrally rich and GUE-like; higher-dim forms are concentrated and Poisson-like.</p>
      <p class="cite">Data: data/phase_transition_spectral/spectral_analysis.json</p>
    `,
    build: buildSpectral,
  },
  approaches: {
    title: 'Herangehensweisen — the attack routes to RH',
    camera: { pos: [0, 15, 26], target: [0, 0, 0], autoRotate: true, autoRotateSpeed: 0.35 },
    info: `
      <p>Strategy map of the routes this project pursues toward the Riemann Hypothesis.
      <strong>Klicke einen Knoten</strong>, um die jeweilige Herangehensweise zu lesen;
      die Farbe kodiert den Status.</p>
      <ul>
        <li><span class="stat green">bewiesen</span> — Theorem (teils schon Lean-formalisiert)</li>
        <li><span class="stat gold">teilweise</span> — die halbe Äquivalenz ist bekannt</li>
        <li><span class="stat">numerisch</span> — starke, konvergente Numerik</li>
        <li style="color:#7ea8ff">Kandidat</li> — unberührte Angriffsroute
        <li style="color:#b08cff">Werkzeug</li> — Hypothese-Generator
      </ul>
      <p class="cite">Der goldene Kern ist RH; die cyan Gruppe A ist der aktive Hauptstrang (EPIC-4, Mayer-Transferoperator).</p>
    `,
    build: buildApproaches,
  },
};

// ---------------------------------------------------------------------------
//  Controller
// ---------------------------------------------------------------------------

function setView(name) {
  const view = VIEWS[name];
  if (!view) return;

  renderer.domElement.style.cursor = '';
  selectedNode = null;
  hoverNode = null;

  if (currentGroup) {
    scene.remove(currentGroup);
    currentGroup.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) {
        if (o.material.map) o.material.map.dispose();
        o.material.dispose();
      }
    });
    currentGroup = null;
    currentUpdate = null;
  }

  const built = view.build();
  currentGroup = built.group;
  currentUpdate = built.update;
  scene.add(currentGroup);

  if (built.defaultFocus) built.defaultFocus();

  const cam = view.camera;
  camera.position.set(...cam.pos);
  controls.target.set(...cam.target);
  controls.autoRotate = !!cam.autoRotate;
  controls.autoRotateSpeed = 0.5;
  controls.update();

  infoTitle.textContent = view.title;
  infoBody.innerHTML = view.info;
  infoBody.scrollTop = 0;

  document.querySelectorAll('.nav-btn').forEach((b) => b.classList.toggle('active', b.dataset.view === name));
}

// ---------------------------------------------------------------------------
//  Init + loop
// ---------------------------------------------------------------------------

function init() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05060a);
  scene.fog = new THREE.FogExp2(0x05060a, 0.012);

  camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 6;
  controls.maxDistance = 80;

  scene.add(new THREE.AmbientLight(0xb8c8ff, 0.55));
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(6, 14, 10);
  scene.add(dir);
  const fill = new THREE.PointLight(0x3fe0ff, 0.5, 120);
  fill.position.set(-12, 6, -8);
  scene.add(fill);

  glowTex = makeGlowTexture();
  clock = new THREE.Clock();

  // Picking for the Approaches scene (click / hover a node)
  const raycaster = new THREE.Raycaster();
  const pickPos = new THREE.Vector2();
  function handlePointer(e, click) {
    if (!currentGroup || !currentGroup.userData.pickable) return;
    const rect = renderer.domElement.getBoundingClientRect();
    pickPos.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    pickPos.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pickPos, camera);
    const entries = currentGroup.userData.pickable;
    const hits = raycaster.intersectObjects(entries.map((p) => p.obj));
    if (hits.length) {
      const entry = entries.find((p) => p.obj === hits[0].object);
      renderer.domElement.style.cursor = 'pointer';
      if (click) currentGroup.userData.focus(entry.rec);
      hoverNode = entry.rec;
    } else {
      renderer.domElement.style.cursor = '';
      hoverNode = null;
    }
    if (currentGroup.userData.repaint) currentGroup.userData.repaint();
  }
  renderer.domElement.addEventListener('pointermove', (e) => handlePointer(e, false));
  renderer.domElement.addEventListener('pointerdown', (e) => handlePointer(e, true));

  // UI wiring
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => setView(btn.dataset.view));
  });
  const infoToggle = document.getElementById('info-toggle');
  infoToggle.addEventListener('click', () => {
    infoPanel.classList.toggle('collapsed');
    infoToggle.textContent = infoPanel.classList.contains('collapsed') ? '⟩' : '⟨';
  });

  window.addEventListener('resize', onResize);
  animate();
}

function onResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
  requestAnimationFrame(animate);
  const dt = clock.getDelta();
  const t = clock.elapsedTime;
  controls.update();
  if (currentGroup && currentUpdate) currentUpdate(dt, t);
  renderer.render(scene, camera);
}

async function loadData() {
  try {
    const res = await fetch('assets/zeta-data.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    zetaData = await res.json();
  } catch (e) {
    console.error('zeta-data.json load failed:', e);
    loadingEl.querySelector('.loading-text').textContent =
      'Could not load ζ data (need a web server). Other views still work.';
    zetaData = { zeros: RESEARCH.zeta.firstZerosImag, ts: [], sigmas: [], magnitude: [], t_max: 60, zmax: 12 };
    return;
  }
  loadingEl.classList.add('hidden');
  setTimeout(() => loadingEl.remove(), 900);
}

// ---------------------------------------------------------------------------
//  Boot
// ---------------------------------------------------------------------------

init();
loadData().then(() => {
  // Deep-link support: ?view=approaches&node=<index> opens a scene directly
  const params = new URLSearchParams(location.search);
  const want = params.get('view');
  setView(VIEWS[want] ? want : 'landscape');
  const nodeIdx = Number(params.get('node'));
  if (currentGroup && currentGroup.userData.focus && Number.isInteger(nodeIdx) && nodeIdx >= 0) {
    const pick = currentGroup.userData.pickable;
    if (nodeIdx < pick.length) currentGroup.userData.focus(pick[nodeIdx].rec);
  }
  footText.textContent = 'GNN × Number Theory → Riemann Hypothesis';
});
