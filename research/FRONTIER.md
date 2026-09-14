# FRONTIER — What is actually proven, what is a model, and where the honesty boundary sits

**Date**: 2026-09-14 · **Status**: honesty pass (RH-22) · **Scope**: `lean/Riemann/TransferOperator/`, `lean/Riemann/PrimeNumberTheorem.lean`

This document is the corrective record of the formalization. The narrative files
(`research/README.md` — "RH PROVEN", `paper/transfer-operator-rh.tex`, and the
various `*_COMPLETE.md` status sheets) overstate what the Lean code establishes.
Below is the machine-checked reality: which identities are **definitional**,
which results are **proven for real**, and where the **frontier** — the honest
research step — sits. Every claim cites `file:line` in the verified modules.
The companion machine-readable record is `lean/Riemann/AxiomAudit.lean`
(`#print axioms` dependency bill for every load-bearing declaration).

---

## 1. The chain is circular at its two load-bearing points

Both pillars of the "transfer-operator proof of RH" are explicit analytic
models — definitions chosen so that the wanted identities hold *by unfolding*,
not theorems about the true operator/determinant.

### 1a. The Fredholm determinant is definitional

`lean/Riemann/TransferOperator/Complete.lean:61-63`:

```lean
noncomputable def fredholmDet (s : ℂ) : ℂ :=
  (mayer_correction s)⁻¹ * riemannZeta (2 * s)
```

`fredholmDet` **is** `ζ(2s)/C(s)` by definition. It is *not* `det(1 − L_s)`.
The file's own docstring (Complete.lean:49-53) calls it an "EXPLICIT ANALYTIC
MODEL": the true object is the trace-class Fredholm determinant
`exp(∫ tr(L_s)/n...)` of `transferOperatorBounded`, whose construction is still
open. Every "theorem" that follows is a definitional consequence:

| Declaration | Line | Why it is a tautology, not a discovery |
|---|---|---|
| `mayer_identity` — "ζ(2s) = C(s)·det(1−L_s)" | Complete.lean:105 | Holds **by construction**: `unfold fredholmDet; rw [mul_inv_cancel₀ (mayer_correction_ne_zero …), one_mul]`. Nothing about Mayer's operator. |
| `det_eq_zero_iff_zeta_eq_zero` | Complete.lean:112 | Immediate from the definition (`fredholmDet s = 0 ↔ ζ(2s) = 0`), *inside* Re s > 1/2 where `C(s) ≠ 0` is proven. Not a spectral statement. |
| `fredholmDet_ne_zero_of_one_lt_half` | Complete.lean:158 | `ζ(2s) ≠ 0` (Euler region) pushed through the definitional iff. |862 |

### 1b. The leading eigenvalue is a model, not the spectrum

`lean/Riemann/TransferOperator/Theorem3_3.lean:66-68`:

```lean
noncomputable def modelLeadingEigenvalue (s : ℂ) : ℂ :=
  Complex.exp ((1 / 2 : ℂ) - s)
```

`modelLeadingEigenvalue = exp(1/2 − s)` is a **model** — an entire function
chosen so that the wanted inequalities hold by elementary calculus. It is *not*
the spectral radius / Perron root of `transferOperatorBounded s hs`; the file's
docstring (Theorem3_3.lean:46-65) is explicit that Krein–Rutman simplicity and
ρ(L_s) = |λ₁(s)| are "still open" and that "mathlib has no Krein–Rutman
theorem in this pin". Consequently:

| Declaration | Line | Truth about |
|---|---|---|
| `modelLeadingEigenvalue_norm` — `‖λ₁(s)‖ = exp(1/2 − Re s)` | Theorem3_3.lean:75 | the model (calculus) |
| `modelLeadingEigenvalue_at_half` — `‖λ₁(1/2+it)‖ = 1` | Theorem3_3.lean:82 | the model |
| `modelLeadingEigenvalue_simple` — `‖λ₁(s)‖ < 1` for Re s > 1/2 | Theorem3_3.lean:130 | the model |
| `spectral_radius_lt_one` — "Theorem 3.3" | Theorem3_3.lean:226 | **the model**, not ρ(L_s) |
| `spectralRadius_le_modelLeadingEigenvalue_norm` — "ρ(L_s) ≤ |λ₁|" | Theorem3_3.lean:204 | proof is `exact modelLeadingEigenvalue_simple …` — it proves nothing about the genuine spectral radius; the name overclaims |
| `transferOperator_irreducible` | Theorem3_3.lean:104 | `0 < |model|` — an earlier injectivity placeholder was rejected as false (docstring, Theorem3_3.lean:96-103) |
| `one_not_mem_spectrum` — "det(1−L_s) ≠ 0" | Theorem3_3.lean:234 | the model (exponential ≠ 1); the true statement on `transferOperatorBounded` is not expressed |

**Net effect.** The slogan "the transfer operator proves RH" is *not* what
these files establish. What is rigorously established is an analytic skeleton —
an explicit model that saturates the wanted unit-disk/zero-free inequalities —
plus two unfilled upward steps (see §3). The `fleet`-level folklore around
"Fleet 5 proven" and "Theorem 3.3 proven" (e.g. Theorem3_3.lean docstring
lines 26-35, calling them "proven") must be read as *model-form* provenance.

---

## 2. What is genuinely proven

These are real, non-circular, machine-checked results (all confirmed by
`#print axioms`: each depends only on `[propext, Classical.choice, Quot.sound]`,
see `AxiomAudit.lean`).

### 2a. The Gauss-map / Ruelle transfer operator on C([0,1], ℂ) is bounded

- `transferOperatorBounded s hs` — the operator `(L_s f)(x) = Σₙ wₙ(x)·f(Iₙ(x))`
  assembled via the M-test as a continuous linear map: `Operator.lean:244-290`.
- **Boundedness with explicit constant**: `‖L_s‖ ≤ Σ (n+1)^{−2·Re s} = ζ(2·Re s) < ∞`
  — `transferOperatorBounded_norm_le_rpow`, `Operator.lean:361-367`.
- Summability foundation (p-series comparison): `sum_inverse_pow_converges`,
  `BasicProofs.lean:49`; `transferOperator_weight_norm_summable`,
  `Operator.lean:98`; `transferOperatorSummandCm_norm_summable`, `Operator.lean:227`.

### 2b. Uniform convergence — and why compactness is NOT proven (it is false here)

- `transferOperator_uniform_convergence`, `Operator.lean:317`: partial sums
  converge to `L_s f` in the sup norm, uniformly in `x`.
- **Compactness is provably false on C([0,1], ℂ).** The module note
  `Operator.lean:46-63` gives the counterexample: the `n = 0` branch already
  maps the unit ball into a non-precompact (non-equicontinuous) family, so by
  Arzelà–Ascoli `IsCompactOperator (transferOperatorBounded s hs)` fails. This
  corrects the "bounded + **compact**" phrasing: the bounded part is proven,
  the compact part is *disproven on this space*. Compactness on Mayer's
  analytic classes (disc algebra, where Ruelle operators are compact and
  Krein–Rutman applies) is **not** formalized anywhere in this pin — that
  formalization is itself an open item of §3.

### 2c. Euler-region nonvanishing (trivial-classical, machine-checked)

- `ζ(s) ≠ 0` for `Re s > 1`: mathlib's `riemannZeta_ne_zero_of_one_lt_re`, used
  at `Complete.lean:161` and `PrimeNumberTheorem.lean:178,194`.
- `ζ(s) ≠ 0` for `Re s ≥ 1`: mathlib's `riemannZeta_ne_zero_of_one_le_re`, used
  at `PrimeNumberTheorem.lean:90`.
- Corollary on the model: `fredholmDet_ne_zero_of_one_lt_half`, `Complete.lean:158`.

### 2d. Zeta on the critical line `Re s = 1` (PNT), modulo what it does not use

- `riemannZeta_ne_zero_of_re_eq_one`, `PrimeNumberTheorem.lean:86-90`:
  `s.re = 1 ∧ s ≠ 1 → ζ(s) ≠ 0` (Hadamard–de la Vallée Poussin, inherited from
  mathlib's closed-half-plane theorem — fully proven, axiom-clean).
- Trivial-zero exclusion: `riemannZeta_zero_of_re_nonpos`, `PrimeNumberTheorem.lean:132`
  — `ζ(ρ) = 0 ∧ Re ρ ≤ 0 → ρ = −2(n+1)`, fully proven (FE reflection +
  cos-zero analysis). This is the "PNT line theorem modulo the strip lemma":
  it is *complete on its own*, but the overall `riemannHypothesis`
  (`PrimeNumberTheorem.lean:186-201`) reaches RH only by routing the
  critical-strip case through `riemannHypothesis_criticalStrip`
  (`PrimeNumberTheorem.lean:68`), which calls the open strip lemma — see §3.

### 2e. Functional-equation reflection

- `functionalEquation_reflection`, `PrimeNumberTheorem.lean:49-66`:
  `ζ(ρ) = 0`, `0 < Re ρ < 1 → ζ(1−ρ) = 0`, proven from mathlib's
  `riemannZeta_one_sub`. Axiom-clean. This is what makes zeros symmetric
  across `Re = 1/2` and what turns the half-strip statement into RH (see §3).

---

## 3. THE FRONTIER — the honest research step

```lean
-- Complete.lean:144-152
theorem no_zeros_right_half_plane (ρ : ℂ) (hρ : riemannZeta ρ = 0)
    (hRe : 1 / 2 < ρ.re ∧ ρ.re < 1) : False := by
  -- ... the single open placeholder lives here (line 152)
  sorry
```

**This is the only open placeholder in the formalization.** Every other file
builds. The declaration states: *ζ has no zero with real part strictly between
1/2 and 1* — i.e. the hard half of the Riemann hypothesis.

### 3a. `no_zeros_right_half_plane` is EQUIVALENT to the RH hard half

- **Forward** is the statement itself.
- **Backward**: by the functional-equation reflection (§2e), a zero with
  `0 < Re ρ < 1/2` reflects to the zero `1−ρ` with `1/2 < Re(1−ρ) < 1`;
  hence "no zeros in (1/2, 1)" ⇔ "no zeros in (0, 1/2)", and the
  combination with §2c/§2d (nothing above or on Re = 1) forces every nontrivial
  zero onto `Re = 1/2` — RH. This equivalence is exactly the glue already
  implemented in `riemannHypothesis_criticalStrip`
  (`PrimeNumberTheorem.lean:68-83`): it reduces RH to the one open statement.

### 3b. The transfer-operator form of the frontier: Re s > 1/4, not Re s > 1/2

A zero `ρ` of ζ with `1/2 < Re ρ < 1` corresponds, through the (would-be)
Mayer identity, to `det(1 − L_{ρ/2}) = 0` with `Re(ρ/2) ∈ (1/4, 1/2)`.
Therefore:

> **ρ(L_s) < 1 for Re s > 1/4 on the analytic class would imply RH**
> (via det(1 − L_s) ≠ 0 ⇔ ρ(L_s) < 1 and ζ(2s) = C(s)·det(1−L_s)).

**And it is exactly as hard as RH.** The difficulty runs in precisely the
strip `1/4 < Re s < 1/2`: nothing in the current files reaches below Re s = 1/2.

- The *definitional* correspondence `det_eq_zero_iff_zeta_eq_zero`
  (`Complete.lean:112`) is proven only where `mayer_correction_ne_zero`
  (`Complete.lean:72`) is proven — Re s > 1/2. At `s = ρ/2` with
  `1/2 < Re ρ < 1` this is exactly the crossing into (1/4, 1/2).
- The *model* spectral-radius bound (`spectral_radius_lt_one`,
  `Theorem3_3.lean:226`) is proven only for Re s > 1/2. A genuine
  `ρ(L_s) < 1` statement on `transferOperatorBounded` does not exist anywhere.
- The `no_zeros_right_half_plane` sorry's own comment (`Complete.lean:147-150`)
  states this precisely: the correspondence "applies at `s = ρ/2` only when
  `Re ρ / 2 > 1/2`, i.e. exactly in the Euler region `Re ρ > 1`", where the
  classical proof already works. The region that matters — (1/4, 1/2) — is
  unreachable by every theorem currently formalized.

So the honest upgrade path is, in order: (1) formalize Mayer's analytic class
(disc algebra / bounded holomorphic functions on a Banach space) and
`transferOperatorBounded` on it — where compactness (§2b) becomes true; (2)
prove the trace-class Fredholm determinant `det(1 − L_s)` and Mayer's identity
for it (replacing the definitional `fredholmDet` of §1a); (3) prove
Krein–Rutman / `ρ(L_s) < 1` down to Re s > 1/4; (4) invoke §3a. Steps 2–4 are
each exactly as hard as the corresponding half of RH — there is no free lunch,
and this document says so instead of claiming a completed proof.

---

### 3c. Krein–Rutman on C(X, ℝ) — existence is the honest frontier

(`lean/Riemann/KreinRutman.lean`, RH-24/25 state)

The file proves the cone scaffolding, the real spectral-value lemma
`|μ| = ρ(T)` (Fredholm alternative over ℝ), the positivity transfer
`T |f| ≥ ρ(T) |f|`, the full strong form `kreinRutman_strong` (geometric
simplicity — uniqueness up to positive scalar under strong positivity), and
reduces the weak theorem `kreinRutman` to a **single admitted existence
statement**

```lean
theorem kreinRutman_core {T : C(X, ℝ) →L[ℝ] C(X, ℝ)} (hTpos : IsPositive T)
    (hTcomp : IsCompactOperator T) (hρ : 0 < spectralRadius ℝ T) :
    ∃ f : C(X, ℝ), f ∈ positiveCone ∧ f ≠ 0 ∧
      T f = (spectralRadius ℝ T).toReal • f := by
  sorry
```

**False-lemma trap (corrected RH-25):** an earlier commit admitted a sharper
"collapse" lemma — `ρ(T) • f ≤ T f` on the cone forces equality.  That
statement is **false**: on a two-point `X` (`C(X,ℝ) ≅ ℝ²`), `T = [[2,1],[0,2]]`
is positive and compact with `ρ(T) = 2`, and `f = (0,1)` satisfies
`2f = (0,2) < (1,2) = T f` strictly without being an eigenvector.  The
stronger false lemma has been **removed**; the honest frontier is exactly the
classical existence theorem, and the strict-domination collapse is **proved**
only under strong positivity (inside `kreinRutman_strong`).  Any future code
must not re-admit the collapse version.

**RH-26 progress (route 1 advanced):** the proved scaffold now includes
`exists_eigenvector_with_domination`: for compact positive `T` with
`0 < ρ(T)` there is a nonzero real `v`, a real eigenvalue `μ` with
`|μ| = (spectralRadius ℝ T).toReal`, `T v = μ • v`, and pointwise
domination `(spectralRadius ℝ T).toReal • |v(x)| ≤ (T |v|)(x)` for all `x`.
This is precisely the starting point of the Gelfand-orbit strategy: it
produces a nonzero `|v|` on the positive cone with `T |v| ≥ ρ(T) |v|`,
ready to normalize and pass to a cluster point via compactness.  Gate
passed with `MAX_SORRY=1` (KreinRutman.lean has exactly one sorry =
`kreinRutman_core`; no admits; no weakened statements).  It was discovered
mid-round that a worker-agent can smuggle `admit` past a `sorry`-only gate
— all merges must also grep for `admit`.

Three routes would close `kreinRutman_core`; all are absent from mathlib
over the real field: (1) Gelfand's spectral-radius formula over ℝ (complex
only), (2) Neumann/resolvent positivity on `(ρ(T), ∞)`, (3) the
spectral-radius identity between a real operator and its complexification.
The proved scaffold (`mem_spectrum_abs_eq_spectralRadius`,
`positive_abs_ge`, `exists_eigenvector_with_domination`,
`resolvent_neumann_series`, `resolvent_positivity_at_norm`) lies on routes 1
and 2 and is retained.  **RH-28 (merged) proved the hard free half of route
2**: for `IsPositive T`, `0 < λ`, `‖T‖ < λ`, the resolvent
`Ring.inverse (λ • 1 - T)` is itself positive, via the Neumann series
`HasSum (fun n => (λ⁻¹)ⁿ⁺¹ • Tⁿ) (Ring.inverse (λ • 1 - T))`
(`HasSummableGeomSeries` + `NormedRing.inverse_one_sub`; `E →L[ℝ] E` is a
`NormedRing`).  Extending positivity from `λ > ‖T‖` down to `λ > ρ(T)` is
the remaining route-2 step.

**RH-29 (merged) reduced the whole frontier to ONE razor-thin admission** in
new file `lean/Riemann/RealGelfand.lean` (generic, mathlib-PR-ready):
`realSpectralRadius_le_liminf_pow_nnnorm_pow_one_div` is **proved** (mathlib's
field-general lower bound at 𝕜 = ℝ), `realGelfandFormula` is **proved** from
the two bounds, and the single documented sorry is exactly
`realGelfandUpperBound`: `limsup ‖aⁿ‖₊^(1/n) ≤ spectralRadius ℝ a`.  Mathlib
has only the complex upper bound (complex-analytic power-series radius); the
docstring names the two PR paths (generalize to `NontriviallyNormedField`, or
an intrinsic real Beurling–Gelfand argument).  Once that one bound exists,
`kreinRutman_core` closes by the Gelfand-orbit/cluster-point argument built on
RH-26's domination + RH-28's resolvent positivity.

**RH-30 (merged) closed route 2 all the way to the spectral radius**: for
`IsPositive T`, `0 < λ`, `(spectralRadius ℝ T).toReal < λ`, the resolvent
`Ring.inverse (λ • 1 - T)` is provably positive
(`resolvent_positivity_at_radius`).  The bridge is the bounded-orbit estimate
`eventually_pow_norm_le` (`‖Tⁿ‖ ≤ C · ((ρ.toReal) + ε)ⁿ` from
`realGelfandFormula`, converted through ENNReal to an eventual power bound,
the finitely many early terms absorbed into `C`) and the Neumann series at the
radius `resolvent_neumann_series_at_radius` (geometric summability with ratio
`(ρ + ε)/λ < 1`; telescoping + continuity of left/right multiplication in the
`NormedRing` `E →L[ℝ] E` give the two-sided inverse).  KreinRutman.lean
remains at exactly one sorry (`kreinRutman_core`); zero new sorries added.

**RH-31 (merged) proved the whole orbit-closure half** in new file
`lean/Riemann/OrbitClosure.lean` (zero sorries, zero admits):
`superharmonicOrbit T ρ w n := (ρ⁻¹)ⁿ • Tⁿ w` with proved `_mem` (stays on
the cone), `_nonzero`, `_mono` (pointwise increasing), `_navigation`
(`T orbitₙ = ρ • orbitₙ₊₁`), a generic `norm_le_of_nonneg_le`, AND (beyond
the hypothesis-form contract) a **proved** `orbit_bounded` — but only under
the extra hypothesis that a dominating eigenvector `v` (`w ≤ v`, `T v = ρ•v`)
already exists (`0 ≤ orbitₙ ≤ v`).  The main theorem
`bounded_orbit_yields_positive_eigenvector` then closes: a norm-bounded orbit
plus compact `T` gives a converging subsequence via
`IsCompact.tendsto_subseq`, the monotone orbit is pointwise majorised by the
limit `f` (closed-`Ici` argument), and continuity of `T` passes the
navigation identity through the limit to give `T f = ρ • f` with `f ∈ cone`,
`f ≠ 0`.  The orbit is increasing from `w` and converges **in norm** (all
terms between `w` and `f` squeeze), which is the classical cluster-point
machine.

So the *internal* Krein–Rutman reduction is complete: given a norm-bounded
orbit, everything else is proved.  Two steps remain to close
`kreinRutman_core` itself: (a) `realGelfandUpperBound`
(the single documented sorry — a mathlib gap, not ours), and (b) turning
`exists_eigenvector_with_domination`'s `w = |v|` with `T w ≥ ρ w` into actual
orbit boundedness — the deep strictness step, where a strict domination
`T w > ρ w` combined with resolvent positivity at the radius
(`resolvent_positivity_at_radius`, now proved) gives the `C`; the residual
non-strict case is the classical Krein–Rutman dichotomy.  **Route 3 was probed by a
fleet round (RH-27) and is now
confirmed blocked at the definition level**: mathlib has no
`Continuous.re`/`Continuous.im` for `C(X, ℂ)`, so the complexification
`T_C` of an operator cannot even be defined; the agent's output was a pure
skeleton (every def/theorem a `sorry`, including `def complexificationOp := sorry`)
and was **rejected** — merging it would reproduce the §1b
placeholder-model pattern.  Route 3 is dropped until mathlib grows
`Continuous.re/im` on `C(X, ℂ)`.  Route 2 (Neumann resolvent at λ > ‖T‖ as
a warm-up, using `NormedRing.inverse_one_sub` / `HasSummableGeomSeries`)
remains the most promising near-term attack.

---

## 4. One-line summary

- **Proven for real**: bounded Gauss-map operator on C([0,1],ℂ) (§2a), uniform
  Ruelle convergence (§2b, compactness *disproven* on C([0,1])), Euler-region
  nonvanishing (§2c), Re s = 1 nonvanishing + trivial-zero exclusion (§2d),
  FE reflection (§2e) — all axiom-clean.
- **Definitional / model**: `fredholmDet` (§1a) and `modelLeadingEigenvalue`
  (§1b) — the two "theorems" (Mayer identity, spectral-radius bound) are true
  of the models by construction.
- **Open frontier**: `no_zeros_right_half_plane` (Complete.lean:152) —
  equivalent to RH; a spectral `ρ(L_s) < 1` for Re s > 1/4 would imply it and
  is exactly as hard; the current formalization stops at Re s > 1/2.
- **Krein–Rutman (KreinRutman.lean + RealGelfand.lean)**: weak form reduces to
  one admitted existence statement `kreinRutman_core` (the classical theorem);
  strong form (geometric simplicity) fully proved; a previously admitted false
  "collapse" lemma was detected and removed (RH-25); route-1 scaffold extended
  with the proved `exists_eigenvector_with_domination` (RH-26); route-2
  resolvent positivity closed all the way to `λ > ρ(T)` (bounded-orbit
  estimate + Neumann series at the radius, RH-30); the Gelfand-orbit closure
  half proved in OrbitClosure.lean (RH-31, 0 sorries); the frontier is now
  exactly `realGelfandUpperBound` (RH-29, one documented sorry in
  RealGelfand.lean) plus the strictness turn into orbit boundedness;
  complexification route (RH-27) rejected as un-definable in current mathlib.
