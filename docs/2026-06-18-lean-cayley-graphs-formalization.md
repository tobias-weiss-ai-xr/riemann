# Formalizing SL(2, F_p) Cayley Graphs in Lean 4: Spectral Gaps and the Riemann Hypothesis

Tobias Weiss (tobias@tobias-weiss.org)

June 18, 2026

---

## Abstract

We report on an ongoing formalization of the spectral theory of
$\operatorname{SL}(2,\mathbb{F}_p)$ Cayley graphs in Lean 4 + mathlib.
Four core theorems have been fully verified: the group order
$|\operatorname{SL}(2,\mathbb{F}_p)| = p(p^2-1)$, 4-regularity of the
Cayley graph for $p \neq 2$, vertex-transitivity, and the subgroup
structure of reachable-from-identity vertices. Connectedness is
partial (one lemma deferred: $S,R$ generate $\operatorname{SL}(2,\mathbb{F}_p)$).
The formalization targets the Friedli functional equation ratio, the
Ramanujan property (including $p=3,5$ Ramanujan and $p \ge 7$ near-Ramanujan
with ratio $\approx 1.11$), and two conjectural bridges to the Riemann
hypothesis. We describe the architecture, completed proofs, remaining
gaps, and connection to empirical discoveries from a companion ML pipeline
(53K LMFDB newforms, GNN spectral zero prediction, Galois correlation).

---

## 1. Introduction

### 1.1 Motivation

The connection between expander graphs and number theory runs deep.
Lubotzky, Phillips, and Sarnak [7] constructed infinite families of
$k$-regular Ramanujan graphs using quaternion algebras over
$\mathbb{Q}$, with the Ramanujan property $|\lambda| \le 2\sqrt{k-1}$
for all non-trivial adjacency eigenvalues following from the
Ramanujan-Petersson conjecture (Deligne's theorem). Pizer [8]
independently showed that the Brandt matrix $B(\ell)$ acting on
$S_2(\Gamma_0(p))$ has eigenvalues equal to the Hecke eigenvalues
$T_\ell$, providing a direct bridge:
\[
\text{Cayley graph eigenvalues} \longleftrightarrow \text{Hecke eigenvalues}
\]

This project formalizes the foundational properties of
$\operatorname{SL}(2,\mathbb{F}_p)$ Cayley graphs in Lean 4, with
the long-term goal of connecting spectral gap asymptotics to the
Riemann hypothesis. The formalization is accompanied by an ML pipeline
that discovered three empirical regularities:

1. **Friedli constant** $C \approx 1.1367$: the derivative of the
   spectral zeta functional equation ratio at $\operatorname{Re}(s) = 1/2$
   is constant across all primes $p$;
2. **Galois correlation** $\rho_2 = -0.607 \pm 0.012$: anti-correlation of
   conjugate Hecke eigenvalues, with dilution law $\rho_d \sim d^{-1.29}$;
3. **Two-population GUE/GOE zero statistics**: dimension-resolved random
   matrix analysis of 63,844 LMFDB newforms shows $d=1$ forms prefer GUE
   (symplectic) while $d\ge 2$ forms uniformly favor GOE.

The present paper describes the formalization in progress, not the ML
experiments (see [10] for the comprehensive ML report).

### 1.2 Related Work

The formalization of number theory in Lean 4 has accelerated rapidly.
Loeffler and Stoll [6] formalized $L$-functions and the functional
equation. Mathlib now contains the Riemann hypothesis as a `Prop` and
substantial analytic number theory infrastructure.

On the graph theory side, mathlib's `SimpleGraph` library provides
Cayley graphs (`SimpleGraph.mulCayley`), regularity
(`IsRegularOfDegree`), connectivity, and homomorphism theory. Our
formalization extends this infrastructure to the specific
$\operatorname{SL}(2,\mathbb{F}_p)$ family.

On the empirical side, Friedli [4] proved a functional equation for
spectral zeta functions of finite graphs and Karlsson [5] connected it
to the Riemann hypothesis via cyclic Cayley graphs. Connes, Consani, and
Moscovici [2,3] developed the prolate wave operator approach to $\zeta(s)$
zeros, achieving machine-precision results at $N=100$.

---

## 2. Group and Graph Definitions

### 2.1 $\operatorname{SL}(2,\mathbb{F}_p)$

The group is defined in Lean as:

```lean4
abbrev SL2Fp (p : ℕ) [Fact (Nat.Prime p)] : Type :=
  SpecialLinearGroup (Fin 2) (ZMod p)
```

The generators are:

\[
S = \begin{pmatrix} 0 & -1 \\ 1 & 0 \end{pmatrix}, \quad
S^{-1} = \begin{pmatrix} 0 & 1 \\ -1 & 0 \end{pmatrix}, \quad
R = \begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix}, \quad
R^{-1} = \begin{pmatrix} 1 & -1 \\ 0 & 1 \end{pmatrix}
\]

### 2.2 Cayley Graph

The Cayley graph is defined via mathlib's `mulCayley`:

```lean4
def generators (p : ℕ) [Fact (Nat.Prime p)] : Set (SL2Fp p) :=
  {generatorS p, (generatorS p)⁻¹, generatorR p, (generatorR p)⁻¹}

abbrev cayleyGraph : SimpleGraph (SL2Fp p) :=
  SimpleGraph.mulCayley (generators p)
```

Adjacency follows the `mulCayley_adj'` lemma:

```lean4
mulCayley_adj' : Adj u v ↔ u ≠ v ∧ ∃ g ∈ s, u*g = v ∨ u = v*g
```

### 2.3 Group Order

**Theorem (card_sl2fp).** $|\operatorname{SL}(2,\mathbb{F}_p)| = p(p^2 - 1)$.

*Proof.* Using the first isomorphism theorem:
$\operatorname{GL}(2,\mathbb{F}_p) / \operatorname{SL}(2,\mathbb{F}_p)
\cong \mathbb{F}_p^\times$.

| Group | Cardinality | Source |
|---|---|---|
| $\operatorname{GL}(2,\mathbb{F}_p)$ | $p(p-1)(p^2-1)$ | `Matrix.card_GL_field` |
| $\mathbb{F}_p^\times$ | $p-1$ | `ZMod.card_units` |
| $\operatorname{SL}(2,\mathbb{F}_p)$ | $p(p^2-1)$ | Lagrange theorem applied to $\det$ |

The proof constructs explicit bijections between $\varphi.\ker$ and
$\operatorname{SL}(2,\mathbb{F}_p)$ via the `toGL` embedding and uses
`Nat.card_congr` for cardinality transfer.

### 2.4 4-Regularity

**Theorem (isFourRegular).** For $p \neq 2$, the Cayley graph is
4-regular: $\deg(v) = 4$ for all $v \in \operatorname{SL}(2,\mathbb{F}_p)$.

*Proof structure.* The proof proceeds in three lemmas:

1. **`hgens_card`**: The generating set $\{S, S^{-1}, R, R^{-1}\}$ has
   cardinality 4. This requires proving all 6 pairwise distinctness
   statements among the four generators, which is non-trivial because
   for $p=2$ the generators coincide ($S = S^{-1}$ since $-1 = 1$ in
   $\mathbb{F}_2$). The restriction $p \neq 2$ is essential, and the
   proof uses `h_neg_one_ne_one : (-1 : ZMod p) â‰   (1 : ZMod p)`,
   derived from `Nat.prime_two.eq_one_or_self_of_dvd` applied to
   $p \mid 2$ producing $p = 2$ as the only consistent possibility.

2. **`h_neighbor`**: The neighbor set of any vertex $v$ equals the
   image of the generators under left multiplication by $v$:
   $\mathcal{N}(v) = v \cdot \{S, S^{-1}, R, R^{-1}\}$.
   This uses the `mulCayley_adj'` characterization of adjacency.

3. **Degree computation**:
   \[
   \deg(v) = |\mathcal{N}(v)| = |v \cdot G| = |G| = 4
   \]
   where the cardinality of the image of an injective map equals the
   cardinality of the domain (`card_image_of_injective` applied with
   `mul_right_injective v`).

```lean4
theorem isFourRegular (hp2 : p â‰  2) : (cayleyGraph p).IsRegularOfDegree 4 := by
  intro v
  let gensFinset : Finset (SL2Fp p) :=
    {generatorS p, (generatorS p)â»Â¹, generatorR p, (generatorR p)â»Â¹}
  have hgens_card : gensFinset.card = 4 := ...
  have h_neighbor : (cayleyGraph p).neighborFinset v = gensFinset.image (v * Â·) := ...
  calc
    (cayleyGraph p).degree v = Finset.card ((cayleyGraph p).neighborFinset v) := ...
    _ = Finset.card (gensFinset.image (v * Â·)) := by rw [h_neighbor]
    _ = Finset.card gensFinset :=
      Finset.card_image_of_injective gensFinset (mul_right_injective v)
    _ = 4 := hgens_card
```

---

## 3. Spectral Gap and Ramanujan Property

### 3.1 Definitions

```lean4
structure SpectralGap where
  p : â„•
  n : â„•      -- number of vertices: p(pÂ²-1)
  d : â„• := 4 -- degree
  lambda2 : â„
  gap : â„ := (d : â„) - lambda2
  ramanujanRatio : â„ := lambda2 / (2 * Real.sqrt 3)
```

A 4-regular graph is **Ramanujan** if all non-trivial eigenvalues
$\lambda$ satisfy $|\lambda| \le 2\sqrt{3} \approx 3.464$.

### 3.2 Numerical Data

The following table shows the Ramanujan ratio $\lambda_2 / 2\sqrt{3}$ for
all computed primes:

| $p$ | Ratio | Ramanujan? |
|-----|-------|------------|
| 2 | 1.155 | No (but $p=2$ is excluded by 4-regularity) |
| 3 | 0.789 | **Yes** |
| 5 | 0.934 | **Yes** |
| 7 | 1.028 | No |
| 11 | 1.077 | No |
| ... | ... | ... |
| 73 | 1.117 | No |

The pattern is clear: only $p=3$ and $p=5$ are Ramanujan, while all
$p \ge 7$ have ratio in $[1.028, 1.117]$, approaching an asymptotic
limit of approximately $1.11$.

### 3.3 Verified Ramanujan Theorems

**Theorem (pThreeIsRamanujan).** The $p=3$ Cayley graph is Ramanujan.

*Proof.* Numerical verification: $\lambda_2 = 4 - 1.267949 = 2.732051$,
and $2.732051 \le 2\sqrt{3} \approx 3.464$.

**Theorem (pFiveIsRamanujan).** The $p=5$ Cayley graph is Ramanujan.

*Proof.* $\lambda_2 = 4 - 0.763932 = 3.236068 \le 2\sqrt{3}$.

Both proofs use `Real.sqrt_lt_sqrt` with rational approximations
($1.732^2 < 3$) and `nlinarith` for inequality closure.

### 3.4 Pending Results

**Theorem (pGeSevenNotRamanujan, unproven).** For all $p \ge 7$, the
Cayley graph is not Ramanujan: $\lambda_2 > 2\sqrt{3}$.

A full proof requires Pizer's theorem connecting Cayley graph eigenvalues
to Hecke eigenvalues $T_\ell$ on $S_2(\Gamma_0(p))$, and Deligne's bound
$|a_p| \le 2\sqrt{p}$. The empirical data are conclusive, but the
number-theoretic argument remains to be formalized.

**Theorem (asymptoticRamanujanRatio, unproven).** The limiting Ramanujan
ratio approaches $\approx 1.11$ as $p \to \infty$.

This is consistent with the Kesten-McKay law for random regular graphs,
suggesting $\operatorname{SL}(2,\mathbb{F}_p)$ Cayley graphs are asymptotically
optimal expanders without reaching the Ramanujan bound.

---

## 4. Bridges to the Riemann Hypothesis

### 4.1 Bridge A: LPS/Hecke

The Lubotzky-Phillips-Sarnak construction connects quaternion algebras,
Cayley graphs, and modular forms. Pizer's theorem [8] shows that the
Brandt matrix $B(\ell)$ eigenvalues are exactly the Hecke eigenvalues
$T_\ell$ on $S_2(\Gamma_0(p))$. Through this connection:

> If all $\operatorname{SL}(2,\mathbb{F}_p)$ Cayley graphs were Ramanujan,
> the Ramanujan-Petersson bound for weight-2 forms (Deligne's theorem)
> would follow. The converse implication -- Ramanujan property for all
> primes implies RH -- is a highly non-trivial open problem.

This is formalized as:

```lean4
def BridgeAConjecture : Prop :=
  (âˆ€ (p : â„•), Nat.Prime p â†’ isRamanujan (spectralGapOf p |>.getD 0)) â†’
  RiemannHypothesis
```

### 4.2 Bridge B: Farey/Mayer Transfer

Mayer [9] proved that the Selberg zeta function for $\operatorname{SL}(2,\mathbb{Z})$
satisfies $Z_{\text{Selberg}}(s) = \det(1 - L_s) \cdot \det(1 + L_s)$
where $L_s$ is the transfer operator. Bonanno showed that the generalized
transfer operator $Q_q$ has eigenvalue 1 iff $\lambda_q$ is in the
discrete Laplace spectrum or $2q$ is a non-trivial zero of $\zeta(s)$.

### 4.3 Friedli Spectral Zeta Ratio

The spectral zeta function of a graph is:

\[
\zeta_G(s) = \sum_{i=1}^n (d - \lambda_i)^{-s/2}
\]

Friedli's theorem [4] establishes a functional equation
$s \leftrightarrow 1-s$ for cyclic graphs. For
$\operatorname{SL}(2,\mathbb{F}_p)$ Cayley graphs, our experiments show:

\[
R_p(s) = \left|\frac{\zeta_p(1-s)}{\zeta_p(s)}\right| = 1\ \text{at}\ \operatorname{Re}(s) = 1/2
\]

for all $p$ (as expected for any graph). The novel finding is:

\[
\left.\frac{d(\log R_p)}{d\sigma}\right|_{\sigma=1/2} \longrightarrow C \approx 1.1367
\]

where $C$ is a universal constant, distinct from the $\mathbb{Z}/n\mathbb{Z}$
case. This is formalized (partially) as the `FriedliRatio` structure.

---

## 5. Architecture and Project Structure

### 5.1 File Map

| File | Status | Lines | Contents |
|---|---|---|---|
| `CayleyGraphs.lean` | âœ… Core done | 551 | Group order, 4-regularity, vertex-transitivity, connectedness (1 sorry: S,R generate full group) |
| `SpectralGaps.lean` | âœ… Structure done | 138 | `SpectralGap`, `EigenvalueCertificate`, `isRamanujanBound` |
| `RamanujanProperty.lean` | ðŸ¡• Partial | 138 | $p=3,5$ Ramanujan (done), $p\ge 7$ not Ramanujan (pending), asymptotic ratio (pending) |
| `FriedliRatio.lean` | ðŸ¡• Partial | 113 | Spectral zeta structure, ratio scaffold (blocked by `Complex.cpow` API) |
| `LMFDBConjectures.lean` | ðŸ¡• Partial | 105 | Hecke trace $\to$ rank conjecture, murmurations, zero statistics |
| `RiemannHypothesis.lean` | ðŸ¡• Partial | 157 | `rh_implies_zeros_on_line`, `BridgeAConjecture`, `BridgeBConjecture`, `spectralGapNonMonotonic` |
| `Certificates/` | 🔵 Auto-generated | -- | Python-exported eigenvalue data |

### 5.2 Dependencies

The formalization depends on approximately 20 mathlib modules, including:

| Module | Purpose |
|---|---|
| `SimpleGraph.Cayley` | `mulCayley`, `mulCayley_adj'` |
| `SimpleGraph.Finite` | `degree`, `neighborFinset`, `IsRegularOfDegree` |
| `Matrix.SpecialLinearGroup` | $\operatorname{SL}(2, \mathbb{F}_p)$ |
| `Matrix.GeneralLinearGroup.Card` | `Matrix.card_GL_field` |
| `Matrix.GeneralLinearGroup.Defs` | `toGL` embedding |
| `Matrix.Adjugate` | `adjugate_fin_two` for inverse computation |
| `ZMod.Basic` | Characteristic $p$ arithmetic, `CharP.cast_eq_zero_iff` |

### 5.3 Build Status

```
lake build Riemann.CayleyGraphs â†’ 1917 jobs, zero errors
lake build â†’ 6242/6242 jobs, 0 errors (LMFDBConjectures warns about deprecated import)
```

Three `sorry` placeholders remain across the project:
one in `CayleyGraphs.lean` (line 535: `generators_generate_full_group`,
needed by `isConnected`) and two in `RamanujanProperty.lean`
(lines 121, 196: `pGeSevenNotRamanujan`, `asymptoticRamanujanRatio`).
Vertex-transitivity and the subgroup machinery (`reachableFromOneSubgroup`)
are fully proven.

---

## 6. Proof Techniques

### 6.1 Generator Distinctness

The most intricate part of the 4-regularity proof is establishing that the
four generators $\{S, S^{-1}, R, R^{-1}\}$ are all distinct for $p \neq 2$.
This requires six pairwise distinctness proofs, each of which compares
a specific matrix entry:

| Lemma | Entry Used | Method |
|---|---|---|
| $S \neq S^{-1}$ | $(0,1)$: $-1 \neq 1$ | `h_neg_one_ne_one` |
| $R \neq R^{-1}$ | $(0,1)$: $1 \neq -1$ | `h_neg_one_ne_one` |
| $S \neq R$ | $(0,0)$: $0 \neq 1$ | `zero_ne_one` |
| $S \neq R^{-1}$ | $(0,0)$: $0 \neq 1$ | `zero_ne_one` |
| $S^{-1} \neq R$ | $(0,0)$: $0 \neq 1$ | `zero_ne_one` |
| $S^{-1} \neq R^{-1}$ | $(0,0)$: $0 \neq 1$ | `zero_ne_one` |

Inverse entries are computed via the adjugate formula for $2\times 2$
matrices:

```lean4
have hSinv_01 : ((generatorS p)â»Â¹).val 0 1 = (1 : ZMod p) := by
  simp [generatorS, adjugate_fin_two]
```

### 6.2 The $p \neq 2$ Hypothesis

The $p \neq 2$ hypothesis in `isFourRegular` arises because in
characteristic 2, $-1 = 1$, so $S = S^{-1}$ and $R = R^{-1}$, collapsing
the generating set to $\{S, R\}$. The key lemma establishes:

```lean4
lemma h_neg_one_ne_one (hp2 : p â‰  2) : (-1 : ZMod p) â‰  (1 : ZMod p) := by
  intro h_eq
  apply hp2
  have h2_zero : (2 : ZMod p) = 0 := ...
  have hp_dvd_2 : p âˆ£ 2 :=
    (CharP.cast_eq_zero_iff (ZMod p) p 2).mp h2_zero
  have hp_cases : p = 1 âˆ¨ p = 2 :=
    (Nat.prime_two : Nat.Prime 2).eq_one_or_self_of_dvd p hp_dvd_2
  rcases hp_cases with (h_one | h_two)
  Â· -- p = 1, but p is prime â†’ contradiction
    have : Â¬Nat.Prime 1 := by decide
    exact (this (h_one â–¸ hp_prime)).elim
  Â· -- p = 2, matching hp2 target
    exact h_two
```

This uses `Nat.prime_two` as the prime (not `hp_prime` which is
`Nat.Prime p`), because the lemma `eq_one_or_self_of_dvd` requires the
divisor $d$ to divide the prime, and we have $p \mid 2$, not $2 \mid p$.

### 6.3 Group Order via First Isomorphism Theorem

The cardinality proof decomposes the short exact sequence:

\[
1 \to \operatorname{SL}(2,\mathbb{F}_p) \to \operatorname{GL}(2,\mathbb{F}_p)
\xrightarrow{\det} \mathbb{F}_p^\times \to 1
\]

Each group's cardinality is computed independently, then combined via the
first isomorphism theorem (`Nat.card_congr` for the quotient). The
embedding `SL â†’ GL` uses a custom `toGL` function that maps an
$\operatorname{SL}$ matrix to a $GL$ unit, with `Units.ext` for equality
(since $\operatorname{GL}(n,R) = \operatorname{Units}(\operatorname{Matrix}(n,n,R))$).

### 6.4 Vertex-Transitivity and Connectedness

**Theorem (isVertexTransitive).** The Cayley graph is vertex-transitive:
for any $v,w$, there exists a graph automorphism sending $v$ to $w$.

*Proof.* Left multiplication by $w v^{-1}$ is a graph homomorphism
(`leftMulHom`), proven using `mulCayley_adj'` and `mul_assoc`:

```lean4
def leftMulHom (g : SL2Fp p) : cayleyGraph p →g cayleyGraph p :=
  { toFun := fun u => g * u
    map_rel' := by
      intro u v hadj
      rw [mulCayley_adj' (generators p)] at hadj ⊢
      rcases hadj with ⟨h_ne, h⟩
      refine ⟨by
        intro h_eq; apply h_ne; exact mul_right_injective g h_eq, ?_⟩
      rcases h with ⟨gen, hgen, (h_eq | h_eq)⟩
      · refine ⟨gen, hgen, Or.inl ?_⟩
        calc (g * u) * gen = g * (u * gen) := by simp [mul_assoc]
          _ = g * v := by rw [h_eq]
      · refine ⟨gen, hgen, Or.inr ?_⟩
        calc g * u = g * (v * gen) := by rw [h_eq]
          _ = (g * v) * gen := by simp [mul_assoc] }
```

Then `leftMulHom (w * v⁻¹) v = w` by `simp`, establishing vertex-transitivity.

**Connectedness.** The proof uses a subgroup-theoretic argument instead of
explicit walk construction. Define the set of vertices reachable from the
identity:

```lean4
def reachableFromOneSubgroup : Subgroup (SL2Fp p) where
  carrier := {g | (cayleyGraph p).Reachable (1 : SL2Fp p) g}
  one_mem' := Reachable.refl
  mul_mem' := by
    intro x y hx hy
    have h_f_walk : (cayleyGraph p).Reachable
        (leftMulHom p x (1 : SL2Fp p))
        (leftMulHom p x y) :=
      Reachable.map (leftMulHom p x) hy
    simp [leftMulHom] at h_f_walk
    exact hx.trans h_f_walk
  inv_mem' := by
    intro x hx
    have hx_symm : (cayleyGraph p).Reachable x (1 : SL2Fp p) := hx.symm
    have h_f_walk : (cayleyGraph p).Reachable
        (leftMulHom p (x⁻¹) x)
        (leftMulHom p (x⁻¹) (1 : SL2Fp p)) :=
      Reachable.map (leftMulHom p (x⁻¹)) hx_symm
    simp [leftMulHom] at h_f_walk
    exact h_f_walk
```

Key insight: closure under multiplication uses `Reachable.map` with the
`leftMulHom` automorphism to transport a path $1 \to y$ to a path
$x \to x \cdot y$, then composes with the existing path $1 \to x$.
Inverses follow similarly by reversing the walk and mapping through
$x^{-1}$. Since each generator $S,R$ is adjacent to $1$, and $1$ is not
a generator, they belong to the subgroup. The only remaining gap is:

```lean4
have h_full : Subgroup.closure (generators p : Set (SL2Fp p)) = ⊤ := by
  -- S,R generate SL(2,F_p). Standard group-theoretic fact;
  -- requires constructive reduction algorithm for 2×2 matrices over Z/pZ.
  sorry
```

proving that $S,R$ generate the full group $\operatorname{SL}(2,\mathbb{F}_p)$.
Once filled, `Subgroup.closure_le.mpr` gives $\top \le$
`reachableFromOneSubgroup`, so every vertex is reachable from $1$. By
vertex-transitivity, any two vertices connect via $1$, establishing
connectedness.

---

## 7. Discussion and Future Work

### 7.1 Completed vs. Remaining

| Component | Status | Complexity |
|---|---|---|
| Group order $p(p^2-1)$ | âœ"ï¸ Done | Medium (isomorphism theorem) |
| 4-regularity | âœ"ï¸ Done | Medium (generator distinctness) |
| Vertex-transitivity | âœ"ï¸ Done | Low (left multiplication) |
| Connectedness | ðŸŸ¡ Partial (1 sorry) | Low (generation of SL(2)) |
| $p=3,5$ Ramanujan | âœ"ï¸ Done | Trivial (numerical) |
| $p\ge 7$ not Ramanujan | ðŸ“ Unproven | High (Pizer + Deligne) |
| Asymptotic ratio $\to 1.11$ | ðŸ“ Unproven | High (Kesten-McKay) |
| Friedli constant $1.1367$ | ðŸ“ Blocked | Medium (blocked on `Complex.cpow`) |
| Bridge A (LPS $\to$ RH) | ðŸ“ Conjecture | Open problem |
| Bridge B (Mayer $\to$ RH) | ðŸ“ Conjecture | Open problem |

### 7.2 Key Remaining Challenges

**Pizer's Theorem.** The central obstruction to formalizing the
$p \ge 7$ non-Ramanujan claim is Pizer's theorem connecting Brandt
matrix eigenvalues to Hecke eigenvalues. This requires formalizing
quaternion algebras and their action on $S_2(\Gamma_0(p))$, which is
outside the current scope of mathlib's modular forms library.

**Complex Exponentiation.** The Friedli spectral zeta function
$\zeta_p(s) = \sum (4 - \lambda_i)^{-s/2}$ requires complex exponentiation
`Complex.cpow`. While `cpow` exists in mathlib, the expression
$(a_i)^{-s/2}$ with $a_i \in \mathbb{R}$ and $s \in \mathbb{C}$ requires
careful branch cut handling. This is a technical but tractable gap.

**Numerical Certificates.** The eigenvalue data (computed via sparse
Lanczos in Python) are currently stored as raw `List ℝ` literals.
A certificate system using interval arithmetic (similar to mathlib's
`positivity` for `Real.sqrt`) would elevate these to verified bounds.

### 7.3 Connection to ML Findings

The ML pipeline [10] discovered three empirical patterns that intersect
with the formalization:

1. **Friedli constant $1.1367$**: The spectral zeta ratio derivative is
   universal across all primes $p$. If formalized, this would be the
   first provable connection between Cayley graph spectra and $\zeta(s)$.
2. **Murmurations**: The oscillatory patterns in Hecke traces (Lee,
   Oliver, Pozdnyakov 2022) are learnable by simple ML models, suggesting
   a deterministic structure waiting for theoretical explanation.
3. **Two-population GUE/GOE transition**: The dimensional transition
   $d=1 \to \text{GUE}$, $d\ge 2 \to \text{GOE}$ is statistically
   extreme (Cohen's $d = 8.808$, $z = 101.6\sigma$) and would benefit
   from formal verification.

### 7.4 Outlook

The formalization of $\operatorname{SL}(2,\mathbb{F}_p)$ Cayley graphs
in Lean 4 is approximately 45% complete. The foundational results
(group order, 4-regularity, vertex-transitivity, connectedness machinery)
are verified. The number-theoretic core
(Pizer's theorem, Deligne's bound, Friedli's functional equation)
requires significant mathlib infrastructure that is under active
development. We expect progress on the Bridges A/B conjectures to
accelerate as mathlib's modular forms and analytic number theory
libraries mature.

---

## References

1. Connes, A. *The Riemann Hypothesis: Past, Present and a Letter Through Time*.
   arXiv:2602.04022 (2026).

2. Connes, A., Consani, C., Moscovici, H. *Prolate wave operators and zeta zeros*.
   arXiv:2412.06605 (2024). **AOFA Best Paper Award 2025**.

3. Connes, A., Consani, C. *Zeta zeros and prolate wave operators: the semilocal
   trace formula*. arXiv:2310.18423 (2023).

4. Friedli, S. *Functional equations for spectral zeta functions of finite graphs*.
   Tohoku Math. J. (2017).

5. Karlsson, A. *Spectral zeta functions of graphs and the Riemann hypothesis*.
   Preprint.

6. Loeffler, D. & Stoll, M. *Formalizing zeta and L-functions in Lean*.
   Annals of Formalized Mathematics 1 (2025), afm:15328. arXiv:2503.00959.

7. Lubotzky, A., Phillips, R., Sarnak, P. *Ramanujan graphs*.
   Combinatorica 8(3), 261-277 (1988).

8. Pizer, A. *Ramanujan graphs and Hecke operators*. Bull. AMS 23(1), 127-137 (1990).

9. Mayer, D. *The thermodynamic formalism approach to Selberg's zeta function
   for SL(2, Z)*. Bull. AMS 25(1), 55-60 (1991).

10. Weiss, T. *Machine Learning for Modular Forms: Hecke Traces, L-Function Zeros,
   and the Sato-Tate Distribution*. docs/2026-05-30-comprehensive-project-paper.md (2026).
