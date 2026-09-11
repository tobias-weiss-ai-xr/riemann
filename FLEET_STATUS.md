# Fleet Status — Riemann RH Research

Updated: 2026-09-11

## Live Status

| Host | Arch | Cores | RAM | Lean | Mathlib | Status |
|------|------|-------|-----|------|---------|--------|
| **tobi-legion** (local) | x86_64 | 12 | 62GB | ✅ | ✅ (prebuilt) | **Control + authoring** |
| **ai1** | aarch64 | 20 | 121GB | ✅ | ✅ cache | ✅ **FULL BUILD 6468 jobs OK** |
| **ai2** | aarch64 | 20 | 119GB | ✅ | ⏳ extracting | cache get in progress |
| **v77986.1blu.de** | x86_64 | 32 | 48GB | ✅ | ⏳ cloning | lake update in progress |
| chemie-lernen.org | x86_64 | 6 | 16GB | ❌ apt broken | — | skipped |
| tobias-weiss.org | x86_64 | 4 | 8GB | ❌ | — | skipped (too small) |

## Key Findings

1. **aarch64 mathlib cache EXISTS** — ai1 downloaded all 8899 oleans from the
   community cache in ~10 min. NO from-scratch ARM build needed. 
2. **ai1 full project build: SUCCESS (6468 jobs)** — the entire Riemann lean_lib
   compiles on ARM. Both ARM hosts are now usable build/verify workers.
3. **Arch caveat confirmed**: olean caches are per-arch. x86_64 (legion/v77986)
   form one cache family; aarch64 (ai1/ai2) another. Do not mix.
4. **v77986 = 32 cores** (not 16) — best x86 worker, shares legion's x86 cache.

## Commands

```bash
# status snapshot
./fleet.sh status

# verify on all workers (independent builds)
./fleet.sh verify          # → legend + ai1 + ai2 + v77986

# tally results
./fleet.sh tally

# per-host progress
ssh ai1 "tr '\r' '\n' < /tmp/build-full.log | tail -5"
ssh ai2 "tail -2 /tmp/cache-get.log"
ssh v77986.1blu.de "tr '\r' '\n' < /tmp/lu.log | tail -3"
```

## Next

1. Finish ai2 cache extract → run full build → confirm 2nd ARM success
2. Finish v77986 setup (mathlib clone ~10 min) → full build → x86 2nd verification
3. Then: 4-host verdicts on every theorem (legion + ai1 + ai2 + v77986)
