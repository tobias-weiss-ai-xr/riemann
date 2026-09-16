# ForMathlib — mathlib contribution staging

Self-contained staging copies of the real Krein–Rutman / Gelfand-for-positive-
operators results, prepared for upstream contribution to mathlib
(`https://github.com/leanprover-community/mathlib4`).

**Status (2026-09-16): all four modules compile with 0 errors / 0 sorries
against mathlib only — no `Riemann.*` project code.** Built by the default
`lake build` glob (module names `Riemann.ForMathlib.*`); the `namespace
Riemann` wrapper is a placeholder retained from the project source — a mathlib
PR will dissolve it into appropriate upstream namespaces
(e.g. `Analysis.KreinRutman`, `Order.PositiveOperators`).

## Modules (dependency order)

| Module | Origin | Contents |
|---|---|---|
| `GelfandReal.lean` | `Riemann/RealGelfand.lean` | Real Gelfand spectral-radius formula ingredients; the `Complex.I` counterexample that killed the earlier admitted (and false) `realGelfandUpperBound`. |
| `KreinRutman.lean` | `Riemann/KreinRutman.lean` | Cone scaffolding on `C(X, ℝ)` (`positiveCone`, `IsPositive`, strong positivity), real spectral value `\|μ\| = ρ(T)` via the Fredholm alternative, resolvent Neumann series + positivity (`at_norm` and `at_radius`), Gelfand bound, and the route-1 seed `exists_eigenvector_with_domination`. |
| `GelfandPositive.lean` | `Riemann/GelfandPositive.lean` | The real Gelfand formula for positive operators (`gelfand_formula_of_isPositive`, RH-38: positivity telescope `‖Tⁿ‖ = ‖Tⁿ1‖` + pointwise domination + density-contradiction limsup bound) and `resolvent_positivity_of_gt_spectralRadius`. |
| `KreinRutmanExistence.lean` | `Riemann/KreinDichotomy.lean` | The existence theorem itself: `exists_positive_eigenvector_of_superharmonic` via **direct resolvent blow-up** (RH-39), plus `kreinRutman`, `kreinRutman_core'`, `kreinRutman_strong` (geometric simplicity). Includes the inlined helper `norm_le_of_nonneg_le` (originally `Riemann/OrbitClosure.lean:172`). |

## Before opening a mathlib PR

1. **Dissolve the `Riemann` namespace** and relocate: cone API →
   `Mathlib.Topology.ContinuousMap` territory; Krein–Rutman → new
   `Mathlib.Analysis.KreinRutman`; Gelfand → near
   `Mathlib.Analysis.Normed.Algebra.GelfandFormula`.
2. **Generalize**: the current statements pin `C(X, ℝ)` with
   `CompactSpace X`. Upstream-friendly versions should be phrased for a
   Riesz space / Banach lattice with a closed positive cone wherever the
   proof only uses order + compactness facts (check per lemma; the
   sup-norm-dependent steps genuinely need `C(X)`).
3. **Split by PR size**: GelfandReal + cone API is one PR; Gelfand formula
   for positive operators one; Krein–Rutman existence one.
4. **Naming/style**: run the mathlib linter suite (`lake build` + style
   checks in mathlib CI); adapt docstring conventions (`## Notes`,
   `### TODO`, references).
5. Drop project-flavored references (RH, FRONTIER) from docstrings — keep
   the mathematics references (Krein–Rutman 1948, Schaefer III.7).

## Provenance

Developed in the riemann formalization project; see `research/FRONTIER.md`
§3c (RH-24 through RH-39) for the machine-checked provenance chain and the
audit history (two previously admitted false lemmas caught and removed with
formal counterexamples — RH-25, RH-32).
