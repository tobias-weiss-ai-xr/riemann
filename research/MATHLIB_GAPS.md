# mathlib Gap Analysis for F1 — Spectral Theory of the Mayer L_s Operator

**Date:** 2026-10-09 · **mathlib pin:** `d13f23b723b8a846827a245b89c10fc7d3f11612` (pinned in `lean/lakefile`)
**Scope:** Which pieces of the F1 program (true spectral theory of L_s on the analytic class → RH bridge) are already in mathlib, which are missing, and what was shipped as the first concrete deliverable.

---

## 1. Verdict up front

**The full F1 statement ("L_s is compact on the analytic class; ρ(L_s) < 1 ⟺ ζ(2s) ≠ 0") is not one-session feasible and not near-feasible in this mathlib pin.** Four load-bearing walls are absent (§3). What *is* feasible — and now done — is the first brick of the classical alternative route to a zero-free region: the **3-4-1 lemma** on the von Mangoldt L-series (§2). The honest gap between that lemma and the zero-free region is stated in §4.

---

## 2. Shipped today: `Riemann/ZeroFreeRegion/ThreeFourOne.lean`

**Axiom bill:** `[propext, Classical.choice, Quot.sound]` — no `sorryAx`, no project axioms. Full `lake build` green (6422 jobs).

```lean
theorem threeFourOne (σ t : ℝ) (hσ : 1 < σ) :
    0 ≤ 3 * (LSeries ↗Λ ((σ:ℂ))).re
      + 4 * (LSeries ↗Λ ((σ:ℂ) + (t:ℂ)*I)).re
      + (LSeries ↗Λ ((σ:ℂ) + ((2*t : ℝ) : ℂ)*I)).re
```

Termwise from `3 + 4 cos θ + cos 2θ = 2(1 + cos θ)² ≥ 0`, applied to the absolutely
convergent series `Σ Λ(n) n⁻ʷ` for `Re w > 1`. Building blocks proved inside the module:

* `re_vonMangoldt_term` — `Re (Λ(n)·n⁻⁽σ⁺ⁱᵗ⁾) = Λ(n)·n⁻σ·cos(t log n)` (cpow/pow/log choreography, `Complex.exp_add_mul_I`)
* `summable_vonMangoldt_coeff` — `Summable (Λ n · n⁻σ)` for `σ > 1`, extracted from `LSeriesSummable_vonMangoldt` via `LSeries.norm_term_eq` + `Summable.norm.congr + of_abs`
* `lseries_re_eq` — `Re (L ↗Λ (σ+it)) = Σ Λ(n) n⁻σ cos(t log n)` via `Complex.reCLM.map_tsum` + `LSeries.term_of_ne_zero'`
* the 3·0-term / 2t-term trig identity, `Summable` bundling via `HasSum.add`/`tsum_eq` + `tsum_mul_left`, final `tsum_nonneg`

**Corollary (trivial, not yet added):** by `LSeries_vonMangoldt_eq_deriv_riemannZeta_div`
(`L ↗Λ s = −ζ'(s)/ζ(s)`, `Mathlib/NumberTheory/LSeries/Dirichlet.lean:436`) this reads
`−3 Re(ζ'/ζ)(σ) − 4 Re(ζ'/ζ)(σ+it) − Re(ζ'/ζ)(σ+2it) ≥ 0`.

---

## 3. What mathlib has (the good news)

Everything verified by direct grep against the pinned package (`grep -rn` over `.lake/packages/mathlib`).

### 3.1 Spectral / operator theory (usable today)

| Item | Location | Note |
|---|---|---|
| Riesz–Schauder theory | `Mathlib/Analysis/OperatorTheory/FredholmAlternative.lean` L54/L164/L221 | spectrum of `K + compact`, eigenspace finiteness |
| Compact operators, spectral radius | `Mathlib/Analysis/OperatorTheory/Compact/Basic.lean` L71, L160–196 | `spectralRadius_lt_one` fragments |
| Fredholm index | `Mathlib/Analysis/OperatorTheory/...` | index theory present |
| Strictly-by-finite-rank perturbation | `Mathlib/Analysis/OperatorTheory/Perturbation/StrictByFinite.lean` | finite-rank reduction |
| `IsCompactOperator` API | `Mathlib/Analysis/OperatorTheory/Compact/Basic.lean` | continuity + relative compactness |

### 3.2 L-series / ζ machinery (excellent — this is what made §2 possible)

| Item | Location |
|---|---|
| `LSeries` def + `term` + junk value | `LSeries/Basic.lean:164` (`LSeries_def₀`, `term_def`, `term_zero = rfl`, `term_of_ne_zero'`, `norm_term_eq`) |
| `LSeriesSummable` + congruence | `LSeries/Basic.lean` (`LSeriesSummable_vonMangoldt` at `Dirichlet.lean:381`) |
| `L ↗Λ s = −ζ'(s)/ζ(s)` for Re s > 1 | `Dirichlet.lean:436` `LSeries_vonMangoldt_eq_deriv_riemannZeta_div`; `:429` `LSeries_vonMangoldt_eq` |
| `Λ ≥ 0`, `Λ 1 = 0`, `IsPrimePow` | `VonMangoldt.lean:80` (`vonMangoldt_nonneg`), `:39–158` |
| **`RiemannHypothesis : Prop`** | `RiemannZeta.lean:185` |
| ζ nonvanishing on Re s = 1 (Hadamard–de la V.) | `LSeries/Nonvanishing.lean` (exists — but *qualitative only*, see §4) |
| **No ζ′-specific theorems in `RiemannZeta.lean`** | — | all ζ′ access routes through the LSeries layer (Dirichlet.lean) |

### 3.3 Infinite-sum / functional-analytic glue (battle-tested in §2)

| Item | Location |
|---|---|
| `ContinuousLinearMap.map_tsum` | `InfiniteSum/Module.lean:134` |
| `tsum_mul_left` (unconditional) | `InfiniteSum/Ring.lean:114` |
| `Summable.of_abs`, `Summable.norm`, `Summable.of_nonneg_of_le`, `HasSum.add`, `HasSum.tsum_eq`, `Summable.hasSum` | `InfiniteSum/Order.lean`, `Defs.lean` |
| `summable_mul_left_iff` | `InfiniteSum/Ring.lean:106` |
| `tsum_nonneg`, `tsum_congr` | `InfiniteSum/Order.lean` |
| `Real.abs_cos_le_one`, `Complex.exp_add_mul_I`, `exp_mul_I` | `Analysis/Complex/Trigonometric.lean:511/514`, `:677` |
| `Complex.cpow_def_of_ne_zero`, `ofReal_log`, `ofReal_exp` | `Pow/Complex.lean:38`, `Log.lean:71`, `Exponential.lean:191` |
| `RCLike.norm_ofReal` | `Analysis/RCLike/Basic.lean:246` (careful: instance path — `norm_num` is more robust on ℂ) |

---

## 4. What mathlib lacks (the hard blockers for full F1)

### 4.1 Krein–Rutman theorem — **absent**
No `KreinRutman` anywhere. Needed for: positive compact operator ⟹ spectral radius is a positive eigenvalue (Mayer: the leading eigenvalue exists and is simple). Multi-week formalization project on its own (requires cone theory + Schauder fixed point or the Kreĭn–Milman-style argument).

### 4.2 Analytic-function-space toolkit — **absent**
* **Disc algebra A(D)**: no Banach algebra of continuous-on-closure/holomorphic-inside functions. L_s acts on a Bergman/Hardy-type space on the disk; the compactness proof (Cauchy estimates + Montel) needs this home.
* **Hardy / Bergman spaces**: absent (`grep -ri hardy` → only Hardy inequalities `Analysis/HardyInequalities` — unrelated).
* **Complex Montel theorem / normal families**: `grep -ri montel` → only *Montel's theorem on curves* (`Complex/CauchyIntegral`-adjacent), **not** the normal-family compactness theorem. This is the single missing piece in the standard compactness argument for integral operators on holomorphic functions.
* **`Mathlib/OperatorTheory/`** as a directory exists but has no Schatten-class or trace-ideal tower.

### 4.3 Fredholm / trace-class determinant — **absent**
* No `FredholmDeterminant` (det(I − zK)), no `TraceClass`, no Schatten `p`-norms as operator ideals.
* Our own `Riemann/FredholmDeterminants.lean` + `FredholmFiniteRank.lean` cover only the finite-rank stubs needed for the RH-44 ledger.
* Without this, "ρ(L_s) < 1 ⟺ ζ(2s) ≠ 0" cannot even be *stated* as `fredholmDet L_s ≠ 0`, which is exactly the circularity already documented in `FRONTIER.md`.

### 4.4 Quantitative zero-free region — **absent**
The literature zero-free region (de la Vallée Poussin 4/5-log-region; Platt–Trudgian improvement) needs:
* numerical bounds on `|ζ'(σ+it)|` for σ near 1 — no ζ′ estimates in the pin at all;
* the `3-4-1` + Borel–Carathéodory + a `exp(−C/ln T)` bound chain.
The 3-4-1 lemma is the seed; the region itself is multiple sessions out even with all of §3 present.

---

## 5. Feasibility matrix for the F1 continuation

| Step | Depends on | Status |
|---|---|---|
| 3-4-1 lemma (LSeries form) | §3.2 + §3.3 | ✅ **DONE** (this module) |
| 3-4-1 → `−ζ'/ζ` form | `LSeries_vonMangoldt_eq_deriv_riemannZeta_div` | trivial; add as `threeFourOne_zeta` corollary next session |
| Nonvanishing of ζ on Re s = 1 | `Nonvanishing.lean` (qualitative) | present, but see caveat |
| σ → 1⁺ limit argument (Re ζ'/ζ → −1/(σ−1)) | ζ′ asymptotics | ❌ absent — needs new mathlib work |
| L_s compact on analytic class | §4.2 (disc algebra + Montel) | ❌ absent — hard blocker |
| Krein–Rutman leading eigenvalue | §4.1 | ❌ absent — hard blocker |
| Fredholm determinant ⟺ zeta relation | §4.3 | ❌ absent (our finite-rank stub only) |

## 6. Recommendation

1. **Finish the trivial corollary** `threeFourOne_zeta` (next session, one `rw`).
2. **Stay off the analytic-class compactness track** until disc-algebra + Montel land in mathlib (track mathlib issues; revisit quarterly).
3. The **Keiper–Li ledger** (F3) and **NB density measurements** (F4) remain the highest-yield fronts for this repo's honesty-standard; F1's realistic contribution is the **audit layer** — this module is its first piece.
4. Worth upstreaming: the `re_vonMangoldt_term` + `lseries_re_eq` pair is a natural `Mathlib.NumberTheory.LSeries.VonMangoldt` addition (self-contained, no project axioms).

---

## 7. Compile-battle notes (for future Lean sessions on this module)

* `Real.rpow_def_of_nonneg` is an **if-form** (`if x = 0 then … else exp (log x * y)`); the clean route is `if_neg` + `mul_comm` after it.
* `exp_add_mul_I` in this pin produces **`↑(Complex.cos (↑x))`-form** for real `x`, i.e. the cast is around the complex cos/sin — the follow-up is `← Complex.ofReal_cos/sin`, **then** `Real.cos_neg`/`Real.sin_neg` on the inside. No `ofReal_neg` (negation is nested inside cos/sin args).
* `Complex.reCLM.map_tsum` needs the goal in `⇑reCLM (∑' …)` form — bridge with `show Complex.reCLM (∑' …) = _` (defeq to `.re` but not syntactic).
* `RCLike.norm_ofReal` fails to fire on `‖↑(Λ n)‖` on ℂ (norm-instance path mismatch) — use `norm_num` instead.
* `set c := … with hc` zeta-unfolds bodies during elaboration and **re-associates products** — write term families inline instead of using `set`.
* `tsum_add` does **not exist** for general T2 groups in this pin — use `(hA.hasSum.add hB.hasSum).tsum_eq` + `← rw` instead.
* `HasSum.add`, `Summable.hasSum`, `HasSum.tsum_eq` are the merging workhorses.
* `Real.neg_one_lt_cos` does not exist; derive bounds from `Real.abs_cos_le_one` + `abs_le.mp`.
* `pow_le_pow_left'` (Unbundled) needs `MulLeftMono` which doesn't synthesize on ℝ here — use explicit `mul_nonneg` product hints + `nlinarith`.
* `set_option maxHeartbeats` at **file top** (`set_option … in private lemma` is not parsed in this Lean version).
