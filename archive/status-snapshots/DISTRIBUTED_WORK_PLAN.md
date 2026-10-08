# Distributed Work Allocation — RH Research (REAL FLEET)

Verified fleet map (Sept 2026). Control machine = **tobi-legion** (this machine).

## 🖥️ Real Fleet Inventory

| Host | IP (VPN) | Arch | Cores | RAM | Disk free | Lean | Role |
|------|----------|------|-------|-----|-----------|------|------|
| **tobi-legion** (local) | .42 | x86_64 | 12 | 62GB | — | ✅ (already built mathlib) | **Control + authoring + final verify** |
| **ai1** | 192.168.42.2 | aarch64 | 20 | 121GB | 1.2TB | ✅ provisioned, building | **ARM build worker / long proofs** |
| **ai2** | 192.168.42.3 | aarch64 | 20 | 119GB | 223GB | ✅ provisioned, building | **ARM build worker / long proofs** |
| **v77986.1blu.de** (contextual-intelligence.org) | 192.168.42.20 | x86_64 | 32 | 48GB | 1.1TB | ✅ provisioned | **x86 build worker / numerics** |
| chemie-lernen.org | .10 | x86_64 | 6 | 16GB | — | ❌ apt broken | (skip — marginal) |
| tobias-weiss.org | .1 | x86_64 | 4 | 8GB | 32GB | ❌ | (skip — too small) |
| tobi-yoga | .11 | x86_64 | 8 | 15GB | 36GB | ❌ | (optional light user) |

**Note on arch split (critical):** `ai1`/`ai2` are **ARM64 (Grace ARM, NVIDIA GB10)**.
Mathlib `.olean` **caches are architecture-independent** (Lean envs) but **native `.c`/leanc objects and binaries are arch-specific**. Therefore:
- Each arch maintains its **own** mathlib checkout in `~/.lake/packages/mathlib`.
- x86_64 hosts (legion + v77986) can share legion's already-built mathlib via `lake exe cache`/rsync.
- ARM hosts (ai1/ai2) build mathlib once each from scratch (~45-90 min on 20 cores).

## 🎯 Task → Host Assignment (real)

### Critical path (sequential, then parallelizable)

| # | Task | Primary host | Support | Why |
|---|------|--------------|---------|-----|
| 0.1 | Fix FloorRing ℝ + topology imports | **legion** (interactive) | — | Fast feedback, interactive debugging |
| 1.1 | Complete Gauss map proofs (6 lemmas) | **legion** | ai1 (check) | Authoring here, verify on ARM |
| 2.1-2.4 | Transfer operator: def, linear, bounded, compact | **legion** (author) | **ai1** (verify build) | Heavy compile → ARM GB10 |
| 3.1 | **Theorem 3.3** spectral radius (hardest) | **legion** (author) | **ai1+ai2** (verify) | 20c each, 120GB RAM = fast `lake build` |
| 3.2 | Fredholm determinants | **v77986** (32c x86) | legion | x86 shares legion's cache — fastest warmup |
| 4.1 | Mayer's identity | **legion** | ai2 | Authoring + ARM verify |
| 4.2 | Zero propagation lemma | **v77986** | ai1 | Independent build |
| 5.1 | Final RH assembly | **legion** | all | Coordination here |
| 5.2 | **Full independent verification** | **ai1 + ai2 + v77986** | legion | 3 independent `lake build` runs = 3× proof check |

### Parallel verification strategy (Fleet 5.2)
Every theorem gets **independently verified on 3 remote hosts** — each host runs
`lake build` from its own checkout. 3 agreeing builds = 3× machine-verified trust.
This is the "absolute, rigid, waterproof" multiplier.

## ⚙️ Provisioning status

Provisioning playbook: `~/git/ansible/playbooks/lean-dev-setup.yaml`
Fleet inventory: `~/git/ansible/inventory/rh-fleet-hosts.yaml`

- ✅ ai1: elan + lean v4.33.0-rc1 (aarch64) + repo cloned; `lake update` running
- ✅ ai2: elan + lean v4.33.0-rc1 (aarch64) + repo cloned; `lake update` running
- ✅ v77986.1blu.de: elan + repo cloned (x86_64, 32c); needs toolchain+mathlib
- ⚠️ chemie-lernen.org: apt update fails (network) — skipped

## 🔄 Workflow

```bash
# 1. Author on legion
cd /home/weiss/git/riemann/lean
lake build            # local check

# 2. Push to git
git add -A && git commit -m "..." && git push origin master

# 3. Deploy to workers (each pulls)
for h in ai1 ai2 v77986.1blu.de; do
  ssh $h "cd /home/weiss/git/riemann && git pull origin master"
done

# 4. Verify on each worker independently
ssh ai1   "export PATH=\$HOME/.elan/bin:\$PATH; cd /home/weiss/git/riemann/lean && lake build --wfail > /tmp/verify.log 2>&1 && echo VERIFY_OK"
ssh ai2   "... same ..."
ssh v77986.1blu.de "... same ..."

# 5. Collect results
#   All three echo VERIFY_OK  → theorem is 3× machine-verified
```

## 📡 Quick commands

```bash
# Monitor mathlib build progress on ARM workers
ssh ai1 "tail -3 /tmp/lu.log"
ssh ai2 "tail -3 /tmp/lu.log"

# v77986: check background setup
ssh v77986.1blu.de "tail -3 /tmp/lu.log 2>/dev/null"
```

## 🚨 Known constraints

1. **ARM vs x86**: never rsync `.lake/packages/mathlib` across arch — rebuild per arch.
   A single lean checkout's mathlib takes ~1.1GB source + oleans per arch.
2. **v77986 = OpenVZ**: parallel SSH degrades — use serial/`-f 1` for ansible, keep jobs single `lake build` (32c in-process is fine).
3. **chemie-lernen.org**: apt broken; skip unless needed for docs-only.
4. **ai1/ai2 are shared**: vLLM cluster runs DeepSeek V4 Flash (ai1 :8888). Lean builds are CPU-bound; GPU stays for vLLM. Don't disturb vLLM services.
5. VPN required: all remote access via `192.168.42.x` (tun0). Keys: `~/.ssh/id_ed25519_ansible`.

## 🏁 Acceptance: 100% formal proof

```bash
# On ALL of: legion, ai1, ai2, v77986
cd /home/weiss/git/riemann/lean && lake build        # zero errors
grep -rn "sorry\|axiom" Riemann --include=*.lean     # zero matches in final files
```

4 independent `lake build` successes = the waterproof claim.
