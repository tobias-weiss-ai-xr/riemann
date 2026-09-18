# Lean Proof Agent Brief — MayerHalf campaign (RH-41/42, phase 2)

> **STATUS (post-phase-2, 2026-09-17).** ALL FIVE phase-2 modules are LANDED
> and gate-clean on master: T1 `Algebra.lean` (c9fa9b9), T2 `Operator.lean`
> (75ec7ca), T3 `CompactSummand.lean` (4fa0bb3 + b85a10f), T4
> `CompactLimit.lean` (f39c7d0), T5 `TailCompact.lean` (08a1297 + b85a10f).
> Landed: `equicontinuous_transferSummand`, `norm_transferSummandCLM_le`,
> `summandOp`, `mayerPartial`, `mayerTail`, `mayerOperator_eq`,
> `tendsto_mayerPartial`, `norm_mayerTail_sub_partial_op`,
> `isCompactOperator_of_tendsto_nat`, and the **surgical Montel reduction**
> `isCompactOperator_transferSummandCLM_of_pointwiseRelCompact` /
> `isCompactOperator_summandOp_of_pointwiseRelCompact` /
> `isCompactOperator_mayerTail_of_pointwiseRelCompact` — the tail is compact
> modulo ONE normal-families hypothesis (Montel/Vitali–Porter, not in
> mathlib); the final packaging (`07a31d1`) reduces that hypothesis to a
> bare `IsClosed` statement per summand:
> `isCompactOperator_mayerTail_of_piClosed` — pointwise limits of the
> uniformly bounded transfer family are continuous, nothing else.  **Do NOT
> re-derive these.**  Phase 3 = prove that `IsClosed` (Vitali–Porter), then
> the Fredholm determinant.  Current frontier: `research/FRONTIER.md`
> §RH-41/42.

You are formalizing part of the **Mayer transfer operator on the half-disc
algebra** (Riemann hypothesis program). Read this BEFORE writing Lean code,
then read the template file(s) your task names.

## Reading order

1. `AGENTS.md` (repo root) — overall conventions
2. `lean/Riemann/MayerHalf/Algebra.lean` — **T1, already merged: THE source of truth**.
   Defines: `halfDisc`, `isClosed_halfDisc`, `isCompact_halfDisc`,
   `CompactSpace ↥halfDisc`, `mem_interior_halfDisc`,
   `ball_subset_interior_halfDisc`, `gaussBranch n z = ((n:ℂ)+1+z)⁻¹`,
   `gaussBranch_ne_zero`, `branch_norm_le` (‖gaussBranch n z‖ ≤ 1/((n:ℝ)+1)),
   `branch_re_eq`, `branch_re_pos`, `branchMapsTo_halfDisc` (all n),
   `branchMapsTo_interior` (needs `0 < n`), `branch_image_ball_subset_interior`
   (needs `0 < n`; z-free radius `1/(2*((n:ℝ)+2)^2)`), `toHalfHol`
   (zero-extension), `halfDiscAlgebra` (Subalgebra of `C(↥halfDisc,ℂ)`,
   holomorphic on `interior halfDisc`), `mem_halfDiscAlgebra`,
   `tendstoUniformlyOn_toHalfHol`, `isSeqClosed_halfDiscAlgebra`,
   `isClosed_halfDiscAlgebra`, `halfDiscAlgebra_complete` (Banach),
   `norm_deriv_toHalfHol_le` (‖deriv (toHalfHol f) w‖ ≤ 2·‖f‖/R on interior balls).
3. `lean/Riemann/MayerAnalyticClass.lean` — the phase-1 disc-algebra file
   (older, simpler; good style template).
4. `lean/MayerHalf/` — your new file + sibling modules.

## Build & test loop

```bash
cd lean && export PATH=$HOME/.elan/bin:/usr/local/bin:$PATH
# fast module-scoped check (uses .lake, shared via symlink):
timeout 600 lake env lean Riemann/MayerHalf/<YourFile>.lean 2>&1 | head -40
# or the real module build:
timeout 2400 lake build Riemann.MayerHalf.<YourModule>
```

- `sorry` is a **warning, not an error** — a green build does NOT mean the
  sorry is gone. The gate fails on any `sorry` in your scope file.
- Count BOTH: `grep -cE 'error'` and `grep -cE "declaration uses 'sorry'"`.
  Both must be 0.
- **Write your Lean file in PIECES**: append a section, compile it, fix errors,
  then append the next. Large single-pass writes produce garbled tails.

## Hard rules

- **NO `sorry`, NO `axiom`.** If a substep is genuinely blocked, stop and
  report the blocker in your summary (partial work on a compiling branch is
  acceptable; `sorry` is not).
- NEVER modify `lean/lake-manifest.json`, `lean/lean-toolchain`,
  `lean/lakefile.lean`.
- Edit ONLY the file(s) in your `scope`. Do not touch T1's Algebra.lean or
  any sibling module.
- Use the pinned statement names from your task — nothing more is imported by
  the assembly step; an unpinned name is dead code.
- Keep the `namespace Riemann` + `noncomputable section` structure, `end` (bare)
  before `end Riemann`, `open Metric Set Filter Complex Topology` +
  `open scoped Classical`.
- Commit your work (the gate runs on the committed branch). Clean `git status`
  before finishing.

## Proven tactics (from T1 — trust, don't rediscover)

1. **Mathlib source of truth**: `lean/.lake/packages/mathlib/Mathlib/**` —
   ALWAYS `grep -rn "theorem X"` there before using a name. This pin is
   `Lean v4.33.0-rc1`; names differ from the Lean 4 website.
2. **Stuck typeclass `IsOrderedRing ?m` / `Preorder ?m`**: an elaboration left
   metavars. Culprits: lemma args inside `linarith [...]` lists;
   `Nat.cast_nonneg n` leaves α a metavar — write
   `Nat.cast_nonneg (α := ℝ) n`. Same for any `cast_*` with an underdetermined
   type: pin the type with `(α := ℝ)`.
3. **`positivity` cannot see hypotheses**; `linarith` cannot use a `Nat`
   hypothesis for an `ℝ` goal — bridge with
   `have hn1 : (1 : ℝ) ≤ (n : ℝ) := by exact_mod_cast (Nat.succ_le_of_lt hn)`
   or `Nat.one_le_cast hn`.
4. **`1/x` vs `x⁻¹`**: syntactic mismatch. `rw [one_div]` before
   `inv_le_inv₀` / `inv_le_one₀` / `inv_lt_one₀`.
5. **Hoist tactic proofs out of term positions** into typed `have`s
   (`have h : (0:ℝ) < (n:ℝ)+1 := by linarith [...]`). Inline `by`
   blocks as lemma ARGUMENTS fail against metavars.
6. **`mem_closedBall.mpr` wants a `dist` fact** — for balls centered at 0 use
   `mem_closedBall_zero_iff.mpr` (wants `‖·‖ ≤ r`).
7. **`|x|` in linarith**: prefer `abs_le` decomposition
   (`(abs_le.mp habs).1 : -b ≤ a`, `.2 : a ≤ b`) over lone `abs_nonneg`.
8. **DifferentiableOn on a subtype-codomain function**: to prove the summands
   are holomorphic on the interior, prove the pointwise function
   `fun z => (gaussBranch n z)^2 * f ⟨gaussBranch n z, ...⟩` is
   `DifferentiableOn ℂ f (interior halfDisc)` via
   `DifferentiableAt.inv₀`/`inv₀` (denominator ≠ 0 by `gaussBranch_ne_zero`),
   `DifferentiableAt.pow`, `DifferentiableAt.mul`, `DifferentiableOn.comp`
   (needs `MapsTo` from `branchMapsTo_halfDisc` / interior variants),
   `DifferentiableOn.add`. Then `DifferentiableOn.congr` to tie to
   `toHalfHol (transferSummand n f)`.
9. **A note on the n=0 branch**: `branchMapsTo_interior` requires `0 < n`
   (T1). For holomorphicity you also need the branch to map the INTERIOR to
   the interior for **all** n, incl. n=0. Add
   `branch_interior (n : ℕ) (z : ℂ) (hz : z ∈ interior halfDisc) :
    gaussBranch n z ∈ interior halfDisc` — prove via `mem_interior_halfDisc`
   and the same numerics as `branchMapsTo_halfDisc` (for n=0: `|1+z|² =
   1 + 2·z.re + |z|² > 1` when `0 < z.re`, and `(1+z).re = 1 + z.re > 0`).
10. **CompleteSpace / closedness**: reuse T1's `isSeqClosed_halfDiscAlgebra`
    and `halfDiscAlgebra_complete` — do NOT re-prove Weierstrass.
11. **Summability of the weight series**: `Real.summable_one_div_nat_pow` /
    `summable_nat_add_iff` — grep exact names; for
    `∑' n, 1/((n:ℝ)+1)^2` use a shift (n+1 ↔ Nat.succ).
12. `ContinuousMap.norm_coe_le_norm f x : ‖f x‖ ≤ ‖f‖` — from
    `Mathlib.Topology.ContinuousMap.Compact`.
13. Norm of a product `‖a*b‖ ≤ ‖a‖*‖b‖` is `norm_mul_le` (or
    `ContinuousMap`-level: `ContinuousMap.norm_mul_le` — grep).

## What mathlib already gives you (verified in this pin)

- `Mathlib.Analysis.Normed.Operator.Compact` defines `IsCompactOperator`
  (with `IsCompactOperator.image_ball_subset_compact`,
  `IsCompactOperator.clm_comp` (compact∘continuous),
  `IsCompactOperator.comp_clm` (continuous∘compact? check arg order),
  `ContinuousLinearMap.mkOfIsCompactOperator`,
  `isCompactOperator_iff_image_ball_subset_compact`,
  `isCompactOperator_iff_image_closedBall_subset_compact`), and **
  `isCompactOperator_of_tendsto {ι} ... {F : ι → M₁ →SL[σ₁₂] M₂} {f : ...}
  (hf : Tendsto F l (𝓝 f)) (hF : ∀ᶠ i in l, IsCompactOperator (F i)) :
  IsCompactOperator f`** — closure of compact operators under operator-norm
  limits. Import header likely `Mathlib.Analysis.Normed.Operator.Compact`.
- Ascoli (if needed): `Mathlib.Topology.UniformSpace.Ascoli` —
  `ArzelaAscoli.isCompact_of_equicontinuous (S : Set C(X, α))
  (hS1 : IsCompact (ContinuousMap.toFun '' S))
  (hS2 : Equicontinuous ((↑) : S → X → α)) : IsCompact S` where X must be
  `[CompactSpace]`. Equicontinuity of a Lipschitz family:
  `equicontinuous_of_lipschitz` / `Equicontinuous` from `LipschitzWith` —
  grep names.
- `ContinuousMap.completeSpace` for `C(↥halfDisc, ℂ)` (domain compact, target
  complete).
- `Complex.normSq_eq_norm_sq`, `Complex.normSq_pos`, `Complex.norm_natCast`,
  `Complex.norm_one`, `norm_pow`/`pow_le_pow_left₀`, `norm_add_le`,
  `norm_sub_le`, `norm_mul_le`.
