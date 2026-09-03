#!/usr/bin/env node
// Data integrity tests for the Riemann Hypothesis visualization site.
// Pure Node.js — no browser required. Validates data.js structure,
// connection-graph consistency, zeta data, and index.html nav wiring.
//
// Usage: node tests/data_check.mjs
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { execFileSync } from 'node:child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const DOCS = path.join(ROOT, 'docs');
let passed = 0, failed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; } else { failed++; console.log('  FAIL ' + name + (detail ? ' — ' + detail : '')); }
}

// ── 1. Syntax ──
for (const f of ['assets/data.js', 'assets/viz.js', 'assets/zeta.js']) {
  try { execFileSync(process.execPath, ['--check', path.join(DOCS, f)], { stdio: 'pipe' }); check('syntax: ' + f, true); }
  catch (e) { check('syntax: ' + f, false, String(e.stderr || e.message).slice(0, 200)); }
}

// ── 2. Load data.js in a VM sandbox (data.js is a classic <script>, RESEARCH is global) ──
let R = null;
try {
  const src = fs.readFileSync(path.join(DOCS, 'assets/data.js'), 'utf-8').replace('const RESEARCH =', 'var RESEARCH =');
  const ctx = {}; vm.createContext(ctx); vm.runInContext(src, ctx); R = ctx.RESEARCH;
  check('RESEARCH global defined', !!R);
} catch (e) { check('RESEARCH global defined', false, e.message); }

// ── 3. Top-level keys ──
const KEYS = ['dimensionSplit', 'ml', 'cayley', 'farey', 'zeta', 'provenance', 'approaches', 'spectral'];
for (const k of KEYS) check('RESEARCH.' + k + ' exists', !!R && !!R[k]);

// ── 4. zeta ──
const z = R && R.zeta;
check('zeta.criticalLine defined', z && z.criticalLine !== undefined);
check('zeta.poleAt defined', z && z.poleAt !== undefined);
check('zeta.firstZerosImag is array', Array.isArray(z && z.firstZerosImag));
check('zeta.firstZerosImag >= 10 entries', z && z.firstZerosImag && z.firstZerosImag.length >= 10);
if (Array.isArray(z && z.firstZerosImag)) {
  check('zeta.firstZerosImag all positive numbers', z.firstZerosImag.every((t) => typeof t === 'number' && t > 0));
  check('zeta.firstZerosImag strictly increasing', z.firstZerosImag.every((t, i) => i === 0 || t > z.firstZerosImag[i - 1]));
  check('first zero ≈ 14.134725', Math.abs(z.firstZerosImag[0] - 14.134725141734693) < 1e-9);
}

// ── 5. approaches ──
const ap = R && R.approaches;
check('approaches.target.label defined', ap && ap.target && typeof ap.target.label === 'string' && ap.target.label.length > 0);
check('approaches.target.detail defined', ap && ap.target && typeof ap.target.detail === 'string' && ap.target.detail.length > 0);
check('approaches.groups is array of 4', Array.isArray(ap && ap.groups) && ap.groups.length === 4);
const groupItems = [];
if (Array.isArray(ap && ap.groups)) {
  ap.groups.forEach((grp, gi) => {
    check('group ' + gi + ' has name', grp && typeof grp.name === 'string' && grp.name.length > 0);
    check('group ' + gi + ' has color (hex)', grp && typeof grp.color === 'string' && /^#[0-9a-f]{6}$/.test(grp.color));
    check('group ' + gi + ' items is non-empty array', grp && Array.isArray(grp.items) && grp.items.length > 0);
    groupItems.push(grp ? (grp.items ? grp.items.length : 0) : 0);
    (grp && grp.items || []).forEach((item, ki) => {
      const id = gi + '-' + ki;
      check('item ' + id + ' .label', item && typeof item.label === 'string' && item.label.length > 0);
      check('item ' + id + ' .status', item && typeof item.status === 'string' && item.status.length > 0);
      check('item ' + id + ' .title', item && typeof item.title === 'string' && item.title.length > 0);
      check('item ' + id + ' .detail', item && typeof item.detail === 'string' && item.detail.length > 0);
    });
  });
}

// ── 6. connections ──
const TYPES = ['prerequisite', 'evidence', 'tool', 'formalization', 'independent'];
const conns = ap && ap.connections;
check('connections is array of 15', Array.isArray(conns) && conns.length === 15);
function nodeExists(id) {
  if (id === 'RH') return true;
  const m = /^(\d+)-(\d+)$/.exec(id || '');
  if (!m) return false;
  const gi = Number(m[1]), ki = Number(m[2]);
  return gi >= 0 && gi < groupItems.length && ki >= 0 && ki < groupItems[gi];
}
if (Array.isArray(conns)) {
  conns.forEach((c, i) => {
    check('connection ' + i + ': type valid', TYPES.includes(c && c.type), c && c.type);
    check('connection ' + i + ': label defined', c && typeof c.label === 'string' && c.label.length > 0);
    check('connection ' + i + ': detail defined', c && typeof c.detail === 'string' && c.detail.length > 0);
    check('connection ' + i + ": from '" + (c && c.from) + "' exists", nodeExists(c && c.from));
    check('connection ' + i + ": to '" + (c && c.to) + "' exists", nodeExists(c && c.to));
    check('connection ' + i + ': no self-loop', c && c.from !== c.to);
  });
  const seen = {}; let dup = false;
  conns.forEach((c) => { const key = [c.from, c.to].sort().join('|'); if (seen[key]) dup = true; seen[key] = true; });
  check('no duplicate connections', !dup);
}

// ── 7. index.html nav wiring ──
const html = fs.readFileSync(path.join(DOCS, 'index.html'), 'utf-8');
const navViews = (html.match(/data-view="([^"]+)"/g) || []).map((m) => m.replace(/.*data-view="([^"]+)"/, '$1'));
const EXPECTED = ['hommage', 'connections', 'landscape', 'approaches', 'critical', 'dimension', 'brody', 'spectral'];
check('index.html: 8 nav buttons', navViews.length === 8, 'got ' + navViews.length);
check('index.html: nav order matches VIEWS', JSON.stringify(navViews) === JSON.stringify(EXPECTED), navViews.join(','));
check('index.html: hommage button active', /class="nav-btn active" data-view="hommage"/.test(html));
check('index.html: exactly one active button', (html.match(/nav-btn active/g) || []).length === 1);

// ── Summary ──
console.log('\ndata_check: ' + passed + '/' + (passed + failed) + ' checks passed');
if (failed > 0) { console.log('FAILED: ' + failed); process.exit(1); }
console.log('OK');
