#!/usr/bin/env node
// Headless smoke test for the Riemann Hypothesis visualization site.
//
// Self-contained: starts its own HTTP server (with correct MIME types for
// ES modules), spawns Chrome/Edge headless, connects over CDP, and runs
// interaction + rendering checks that plain data tests cannot cover:
//   - page boots, loading overlay disappears
//   - default view is 'hommage', info panel populated
//   - all 8 views switch via nav clicks, titles update
//   - scene actually renders (screenshot has substantial content)
//   - deep links ?view=…&node=… work
//   - no console errors (SwiftShader GPU-stall warnings are filtered)
//
// Usage:  node tools/headless_check.mjs [--keep]
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';

const KEEP = process.argv.includes('--keep');
const DOCS = path.resolve(import.meta.dirname, '..', 'docs');

// Chrome/Edge discovery
const CANDIDATES = [
  process.env.CHROME,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium',
];
const CHROME = CANDIDATES.find((c) => c && fs.existsSync(c));
if (!CHROME) { console.error('headless_check: no Chrome/Edge binary found (set CHROME env).'); process.exit(1); }

// HTTP server — correct MIME types are REQUIRED for ES modules
const PORT = 8123;
const TYPES = {
  '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
  '.json': 'application/json', '.css': 'text/css', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.ico': 'image/x-icon',
};
const server = http.createServer((req, res) => {
  let p = req.url.split('?')[0];
  if (p === '/') p = '/index.html';
  fs.readFile(path.join(DOCS, p), (err, data) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(p).toLowerCase()] || 'application/octet-stream' });
    res.end(data);
  });
});
server.listen(PORT);

// Chrome spawn + CDP wiring
const DEBUG_PORT = 9341;
const PROFILE = fs.mkdtempSync(path.join(os.tmpdir(), 'ri-test-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--enable-unsafe-swiftshader',
  '--remote-debugging-port=' + DEBUG_PORT, '--user-data-dir=' + PROFILE,
  '--window-size=1280,800', 'about:blank',
], { stdio: ['ignore', 'ignore', 'ignore'] });

let ws, idc = 0;
const pending = new Map();
const errors = [];

function send(method, params) {
  return new Promise((resolve, reject) => {
    const id = ++idc;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('CDP timeout: ' + method)); } }, 10000);
  });
}

function evalExpr(expression) {
  return send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    .then((r) => (r.exceptionDetails ? undefined : r.result && r.result.value));
}

async function waitFor(fn, ms, label) {
  const t0 = Date.now();
  while (Date.now() - t0 < (ms || 25000)) {
    try { const v = await fn(); if (v) return v; } catch (e) { /* retry */ }
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error('timeout waiting for: ' + (label || 'condition'));
}

let passed = 0, failed = 0;
function check(name, ok, detail) {
  if (ok) { passed++; } else { failed++; console.log('  FAIL ' + name + (detail ? ' — ' + detail : '')); }
}

const PAGE = 'http://127.0.0.1:' + PORT + '/';
const VIEWS = ['hommage', 'connections', 'landscape', 'approaches', 'critical', 'dimension', 'brody', 'spectral'];
const TITLE_SUBSTR = {
  hommage: 'Hommage', connections: 'Verbindungen', landscape: 'Landscape',
  approaches: 'Herangehensweisen', critical: 'Critical Line', dimension: 'Dimension Split',
  brody: 'Phase Transition', spectral: 'L-Function',
};

async function navigate(url) {
  await send('Page.navigate', { url });
  await new Promise((r) => setTimeout(r, 3000)); // wait for page load + loadData + setView + render
}

async function main() {
  // Wait for the debugger endpoint, then connect
  let target = null;
  for (let i = 0; i < 100 && !target; i++) {
    try {
      const list = await (await fetch('http://127.0.0.1:' + DEBUG_PORT + '/json')).json();
      const page = (list || []).find((t) => t.type === 'page' && !t.url.startsWith('devtools'));
      if (page) target = page.webSocketDebuggerUrl;
    } catch (e) { /* chrome not ready */ }
    if (!target) await new Promise((r) => setTimeout(r, 250));
  }
  if (!target) throw new Error('chrome debugger not reachable');

  ws = new WebSocket(target);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id); pending.delete(msg.id);
      msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result);
    }
    if (msg.method === 'Runtime.exceptionThrown') errors.push('EXCEPTION: ' + (msg.params.exceptionDetails && msg.params.exceptionDetails.text));
    if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
      const text = msg.params.args.map((a) => a.value || a.description || '').join(' ');
      if (text.indexOf('GPU stall') < 0) errors.push('CONSOLE: ' + text);
    }
    if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
      const etext = msg.params.entry.text || '';
      if (etext.indexOf('GPU stall') < 0 && etext.indexOf('favicon') < 0 && etext.indexOf('404') < 0 && etext.indexOf('Failed to load resource') < 0) errors.push('LOG: ' + etext);
    }
  };
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Log.enable');

  // ── 1. Boot: default view is hommage ──
  console.log('boot & default view');
  await navigate(PAGE);
  const active = await evalExpr('document.querySelector(".nav-btn.active") ? document.querySelector(".nav-btn.active").dataset.view : null');
  check('default view is hommage', active === 'hommage', String(active));
  const title = await evalExpr('document.querySelector(".info-title") ? document.querySelector(".info-title").textContent : null');
  check('info title populated', typeof title === 'string' && title.indexOf('Hommage') >= 0, String(title));
  const bodyLen = await evalExpr('document.querySelector(".info-body") ? (document.querySelector(".info-body").innerHTML || "").length : 0');
  check('info body populated', bodyLen > 100, String(bodyLen));
  const navViews = await evalExpr('Array.prototype.map.call(document.querySelectorAll(".nav-btn"), function (b) { return b.dataset.view; })');
  check('8 nav buttons in order', JSON.stringify(navViews) === JSON.stringify(VIEWS), JSON.stringify(navViews));

  // ── 2. Data globals (data.js is a classic <script>, RESEARCH is on window) ──
  console.log('data globals');
  const connCount = await evalExpr('RESEARCH.approaches.connections.length');
  check('15 connections visible in page', connCount === 15, String(connCount));
  const zetaZeros = await evalExpr('RESEARCH.zeta.firstZerosImag.length');
  check('zeta zeros visible in page', zetaZeros >= 10, String(zetaZeros));

  // ── 3. Scene renders (screenshot has substantial content) ──
  console.log('rendering');
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  const bytes = shot && shot.data ? Buffer.from(shot.data, 'base64').length : 0;
  // A rendered three.js scene yields >30KB PNG; a blank/black one stays <10KB.
  check('scene renders (screenshot > 30KB)', bytes > 30000, bytes + ' bytes');

  // ── 4. Switch through every view ──
  console.log('view switching');
  for (const v of VIEWS) {
    await evalExpr(`var btn = document.querySelector('.nav-btn[data-view="${v}"]'); if (btn) btn.click();`);
    await new Promise((r) => setTimeout(r, 1200));
    const t = await evalExpr('document.querySelector(".info-title") ? document.querySelector(".info-title").textContent : null');
    check('view "' + v + '" title', typeof t === 'string' && t.indexOf(TITLE_SUBSTR[v]) >= 0, String(t));
    const act = await evalExpr('document.querySelector(".nav-btn.active") ? document.querySelector(".nav-btn.active").dataset.view : null');
    check('view "' + v + '" sets active class', act === v, String(act));
  }

  // ── 5. Deep links ──
  console.log('deep links');
  await navigate(PAGE + '?view=connections');
  check('deep link ?view=connections', (await evalExpr('document.querySelector(".nav-btn.active") ? document.querySelector(".nav-btn.active").dataset.view : null')) === 'connections');
  await navigate(PAGE + '?view=approaches&node=0');
  check('deep link ?view=approaches&node=0', (await evalExpr('document.querySelector(".nav-btn.active") ? document.querySelector(".nav-btn.active").dataset.view : null')) === 'approaches');
  await navigate(PAGE + '?view=nonsense');
  check('unknown deep link falls back to hommage', (await evalExpr('document.querySelector(".nav-btn.active") ? document.querySelector(".nav-btn.active").dataset.view : null')) === 'hommage');

  // ── 6. Console errors (SwiftShader GPU-stall warnings and favicon 404s are filtered) ──
  const realErrors = errors.filter((e) => e.indexOf('favicon') < 0);
  check('no console errors', realErrors.length === 0, realErrors.slice(0, 3).join(' | '));

  // ── Summary ──
  console.log('\nheadless_check: ' + passed + '/' + (passed + failed) + ' checks passed');
  chrome.kill(); server.close();
  if (!KEEP) { try { fs.rmSync(PROFILE, { recursive: true, force: true }); } catch (e) { /* noop */ } }
  if (failed > 0) { console.log('FAILED: ' + failed); process.exit(1); }
  console.log('OK');
  process.exit(0);
}

main().catch((e) => {
  console.error('FATAL:', e.message || e);
  try { chrome.kill(); server.close(); } catch (e2) { /* noop */ }
  process.exit(1);
});
