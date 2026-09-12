# Lean Proof Agent Brief — Riemann TransferOperator

You are killing a `sorry` in this repo. Read this BEFORE writing Lean code.

## Build & test loop

```bash
cd lean && export PATH=$HOME/.elan/bin:$PATH
lake build Riemann.<Module> 2>&1 | tr '\r' '\n' | grep -B1 -A8 '^error' | head -40
```

- The TRUE build is `lake build Riemann` (whole lib, ~19 oleans). Module-scoped builds are faster.
- `sorry` is a WARNING, not an error — a green build does NOT mean the sorry is gone.
- The gate runs `lean/fleet-gate.sh` — it fails on any remaining `sorry` in your scope files.

## Environment facts

- mathlib source is at `lean/.lake/packages/mathlib/` — ALWAYS grep there for exact
  lemma names/signatures before using them:
  `grep -rn "theorem norm_cpow" .lake/packages/mathlib/Mathlib --include="*.lean" | head`
- Toolchain: Lean v4.33.0-rc1, mathlib pinned by `lean/lake-manifest.json`.
- This repo uses PLAIN imports (no mathlib `module`/`public import` system).

## Hard-won tactic lessons (do not rediscover these)

1. **Stuck typeclass `IsOrderedRing ?m`**: an elaboration left metavars. Culprits:
   lemma args inside `linarith [...]` lists; un-instantiated `rw` patterns.
   FIX: bind as typed `have`: `have hnn : (0:ℝ) ≤ (n:ℝ) := Nat.cast_nonneg n`.
2. **`positivity` cannot see hypotheses** (`hx : 0 < x` invisible to it).
   Use `linarith [hx.1.le]` with pre-bound real casts.
3. **binop% coercion trap**: `((n : ℝ) + 1 + x) ^ (s : ℂ)` coerces the base
   ATOM-WISE (`↑↑n + 1 + ↑x`), so lemmas expecting a single `ofReal` never match
   in `rw`. Fix the DEF to a single coe: `(((n : ℝ) + 1 + x : ℝ) : ℂ) ^ s`.
4. `Complex.norm_cpow_eq_rpow_re_of_pos (hx : 0 < x) (y : ℂ) : ‖(x:ℂ) ^ y‖ = x ^ y.re`
   lives in namespace **Complex**, file `Analysis/SpecialFunctions/Pow/Real.lean`.
5. This mathlib pin has **`Summable.mul_left` / `Summable.mul_right`**, NOT
   `Summable.mul_const`. `Summable` is an ∃-def here: dot-notation `.mul_const`
   resolves against `Exists` and breaks — use `Summable.mul_right c hf` explicitly.
6. `ContinuousMap.norm_coe_le_norm (f : C(α,β)) (x : α) : ‖f x‖ ≤ ‖f‖` — needs
   `import Mathlib.Topology.ContinuousMap.Compact` (also brings the `Norm` instance
   for `C(Set.Icc 0 1, ℂ)`).
7. `Summable.sum_le_tsum` 2nd arg is complement membership: `(fun i _ => h i)`.
8. Exponent spelling mismatches (`-(2 * σ)` vs `-2 * σ`): bridge with
   `rwa [show (-(2 * σ) : ℝ) = -2 * σ from by ring] at h`.
9. Hoist tactic proofs out of `rw`-chain terms into typed `have`s — term-mode
   elaboration against metavars mis-instantiates.
10. Deprecated: `if_pos` → `simp [DefName, h]`; goal-changing `show` → `change`.
11. `push_cast; ring` normalizes cast-equalities (`Complex.ofReal_add` etc.).

## Rules

- NO `sorry`, NO `axiom` in the files you touch. If a step is genuinely hard,
  split it into a clearly-documented helper instead of hand-waving.
- Do not restate/rename existing theorems — extend the file in place.
- Commit your work (the gate checks the committed branch).
- `git status` must be clean before the gate: the gate pushes the branch HEAD.
