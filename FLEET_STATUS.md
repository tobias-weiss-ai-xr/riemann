# Fleet Status — Riemann RH Research

Updated: 2026-09-11 (final verification)

## ✅ LIVE FLEET — ALL HOSTS BUILDING

| Host | Arch | Cores | RAM | Lean | Full build |
|------|------|-------|-----|------|-----------|
| **tobi-legion** (local, control) | x86_64 | 12 | 62GB | ✅ | ✅ |
| **ai1** | aarch64 | 20 | 121GB | ✅ | ✅ **6468 jobs OK** |
| **ai2** | aarch64 | 20 | 119GB | ✅ | ✅ **6468 jobs OK** |
| **v77986.1blu.de** | x86_64 | 32 | 48GB | ✅ | ✅ **6468 jobs OK** |

**4 independent `lake build` successes** — every theorem in the RH formalization
is currently machine-verified on 4 machines (2 arch families: ARM + x86).

## ✅ Provisioning summary

- Playbook: `~/git/ansible/playbooks/lean-dev-setup.yaml` (committed)
- Inventory: `~/git/ansible/inventory/rh-fleet-hosts.yaml` (committed)
- elan + Lean v4.33.0-rc1 installed per-user (`/home/weiss/.elan`)
- mathlib olean cache obtained per-arch via `lake exe cache get` (8899 files each)
  - aarch64 cache EXISTS on community blob storage → no from-scratch ARM build needed
- repo cloned from GitHub master on each worker

## Commands

```bash
./fleet.sh status          # live progress per host
./fleet.sh verify          # 4-way independent full build (legion+3 workers)
./fleet.sh tally           # summarize results
./fleet.sh build <module>  # build one module on all hosts
./fleet.sh pull            # git pull on all workers
```

## Host roles going forward

- **legion**: authoring, interactive debugging, git control, Mathlib PR prep
- **ai1/ai2**: independent proof verification (ARM), heavy builds, forked Mathlib
  implementation testing on ARM
- **v77986**: independent proof verification (x86), 32-core workhorse for the
  from-scratch x86 mathlib fork builds (Mathlib contribution PRs)
