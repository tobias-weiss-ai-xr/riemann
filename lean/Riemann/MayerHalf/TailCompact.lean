import Riemann.MayerHalf.Operator
import Riemann.MayerHalf.CompactLimit
import Riemann.MayerHalf.CompactSummand
import Mathlib.Topology.Instances.NNReal.Lemmas
import Mathlib.Topology.UniformSpace.Ascoli

/-!
# The compact tail of the Mayer transfer operator

RH-42, T5: assembly of the compactness pipeline.

* `mayerPartial k` sums the summands `1, …, k` (`summandOp (n + 1)`);
  `mayerTail` is the full Mayer operator minus its `n = 0` summand.
* `tendsto_mayerPartial` : the partial sums converge to the tail in operator
  norm, with the tail of `Σ 1/(n+1)²` as the rate (`norm_mayerTail_sub_partial_op`).
* `isCompactOperator_mayerTail` : if every summand `n ≥ 1` is a compact operator
  (each `n ≥ 1` branch maps into the interior — Ascoli, T3), then `mayerTail`
  is compact, via `isCompactOperator_of_tendsto_nat` (T4).

The `n = 0` branch is *not* compact (its branch does not land in the interior),
so `mayerTail` — not `mayerOperatorCLM` — is the honest compact object of
RH-42: `mayerOperatorCLM = summandOp 0 + mayerTail` (`mayerOperator_eq`).
-/

namespace Riemann

open Metric Set Filter Finset Topology
open scoped Classical

noncomputable section

/-! ### Pointwise linearity of a single summand (subtype-valued) -/

/-- A single transfer summand is additive on the half-disc algebra. -/
theorem transferSummand_add (n : ℕ) (a b : halfDiscAlgebra) :
    transferSummand n ((a + b : halfDiscAlgebra) : C(↥halfDisc, ℂ))
        = transferSummand n (a : C(↥halfDisc, ℂ))
          + transferSummand n (b : C(↥halfDisc, ℂ)) := by
  ext z
  change (gaussBranch n z.1) ^ 2 *
    ((a + b : halfDiscAlgebra) : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ =
    (gaussBranch n z.1) ^ 2 * (a : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ +
    (gaussBranch n z.1) ^ 2 * (b : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩
  simp
  ring

/-- A single transfer summand is ℂ-homogeneous on the half-disc algebra. -/
theorem transferSummand_smul (n : ℕ) (c : ℂ) (a : halfDiscAlgebra) :
    transferSummand n ((c • a : halfDiscAlgebra) : C(↥halfDisc, ℂ))
        = c • transferSummand n (a : C(↥halfDisc, ℂ)) := by
  ext z
  change (gaussBranch n z.1) ^ 2 *
    ((c • a : halfDiscAlgebra) : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩ =
    c • ((gaussBranch n z.1) ^ 2 *
      (a : C(↥halfDisc, ℂ)) ⟨gaussBranch n z.1, branchMapsTo_halfDisc n z.2⟩)
  simp
  ring

/-! ### The summand operators -/

/-- The `n`-th Mayer summand as a linear map on the half-disc algebra. -/
def summandOpL (n : ℕ) : halfDiscAlgebra →ₗ[ℂ] halfDiscAlgebra where
  toFun f := ⟨transferSummand n (f : C(↥halfDisc, ℂ)), transferSummandMem n f⟩
  map_add' a b := Subtype.ext (transferSummand_add n a b)
  map_smul' c a := Subtype.ext (transferSummand_smul n c a)

theorem summandOpL_bound (n : ℕ) (f : halfDiscAlgebra) :
    ‖summandOpL n f‖ ≤ (1 / ((n : ℝ) + 1) ^ 2) * ‖f‖ := by
  show ‖(transferSummand n (f : C(↥halfDisc, ℂ)) : C(↥halfDisc, ℂ))‖
      ≤ (1 / ((n : ℝ) + 1) ^ 2) * ‖f‖
  rw [one_div, mul_comm]
  exact norm_transferSummand_le n f

/-- The `n`-th Mayer summand as a bounded operator on the half-disc algebra. -/
def summandOp (n : ℕ) : halfDiscAlgebra →L[ℂ] halfDiscAlgebra :=
  (summandOpL n).mkContinuous (1 / ((n : ℝ) + 1) ^ 2) (summandOpL_bound n)

/-! ### Partial sums and the tail -/

/-- The `k`-th partial Mayer operator: the sum of summands `1, …, k`. -/
def mayerPartial (k : ℕ) : halfDiscAlgebra →L[ℂ] halfDiscAlgebra :=
  ∑ n ∈ Finset.range k, summandOp (n + 1)

/-- CLM sums applied pointwise. -/
theorem mayerPartial_apply (k : ℕ) (x : halfDiscAlgebra) :
    (mayerPartial k x : C(↥halfDisc, ℂ))
        = ∑ j ∈ Finset.range k, transferSummand (j + 1) (x : C(↥halfDisc, ℂ)) := by
  induction k with
  | zero => simp [mayerPartial]
  | succ k ih =>
      have hsplit : mayerPartial (k + 1) = mayerPartial k + summandOp (k + 1) := by
        simp only [mayerPartial, Finset.sum_range_succ]
      calc (mayerPartial (k + 1) x : C(↥halfDisc, ℂ))
          = (mayerPartial k x + summandOp (k + 1) x : C(↥halfDisc, ℂ)) := by
              rw [hsplit, add_apply, Subalgebra.coe_add]
        _ = (mayerPartial k x : C(↥halfDisc, ℂ))
              + (summandOp (k + 1) x : C(↥halfDisc, ℂ)) := rfl
        _ = ∑ j ∈ Finset.range k, transferSummand (j + 1) (x : C(↥halfDisc, ℂ))
              + (summandOp (k + 1) x : C(↥halfDisc, ℂ)) := by rw [ih]
        _ = ∑ j ∈ Finset.range (k + 1), transferSummand (j + 1) (x : C(↥halfDisc, ℂ)) := by
              rw [Finset.sum_range_succ]
              exact congrArg (fun u : C(↥halfDisc, ℂ) =>
                ∑ j ∈ Finset.range k, transferSummand (j + 1) (x : C(↥halfDisc, ℂ)) + u) rfl

/-- Shifted weight summability in the canonical `j + k + 1` index form. -/
theorem summable_mayerWeights_shifted (k : ℕ) :
    Summable fun j : ℕ => ((↑(j + k + 1) + 1 : ℝ) ^ 2)⁻¹ := by
  have hbridge : (fun j : ℕ => ((↑(j + k + 1) + 1 : ℝ) ^ 2)⁻¹)
      = fun j : ℕ => 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 := by
    funext j
    simp [one_div]
  have hbridge2 : (fun j : ℕ => 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2)
      = fun j : ℕ => 1 / (((j + (k + 1) : ℕ) : ℝ) + 1) ^ 2 := by
    funext j
    simp only [Nat.cast_add, Nat.cast_one]
    ring
  rw [hbridge, hbridge2]
  exact (summable_nat_add_iff (k + 1) (f := fun n : ℕ => 1 / ((n : ℝ) + 1) ^ 2)).mpr
    summable_mayerWeights

/-- Shifted norm summability: `Σ' ‖T_{j+k+1} f‖` converges. -/
theorem summable_shifted_norm (k : ℕ) (f : halfDiscAlgebra) :
    Summable fun j : ℕ => ‖transferSummand (j + k + 1) (f : C(↥halfDisc, ℂ))‖ := by
  refine Summable.of_nonneg_of_le (fun b => norm_nonneg _)
    (fun j => norm_transferSummand_le (j + k + 1) f) ?_
  exact Summable.mul_left ‖(f : C(↥halfDisc, ℂ))‖ (summable_mayerWeights_shifted k)

/-- The shifted Mayer series `Σ' T_{j+k+1} f` lands in the half-disc algebra. -/
private theorem mayerShiftSum_mem (k : ℕ) (f : halfDiscAlgebra) :
    (∑' j : ℕ, transferSummand (j + k + 1) (f : C(↥halfDisc, ℂ))) ∈ halfDiscAlgebra := by
  have hhasSum : HasSum (fun j : ℕ => transferSummand (j + k + 1) (f : C(↥halfDisc, ℂ)))
      (∑' j : ℕ, transferSummand (j + k + 1) (f : C(↥halfDisc, ℂ))) :=
    (Summable.of_norm (summable_shifted_norm k f)).hasSum
  have htend := hhasSum.tendsto_sum_nat
  have pmem : ∀ N : ℕ,
      (∑ i ∈ Finset.range N, transferSummand (i + k + 1) (f : C(↥halfDisc, ℂ))) ∈ halfDiscAlgebra := by
    intro N
    induction N with
    | zero => simp only [Finset.range_zero, Finset.sum_empty]; exact zero_mem halfDiscAlgebra
    | succ N ih =>
        rw [Finset.sum_range_succ]
        exact Subalgebra.add_mem _ ih (transferSummandMem _ f)
  exact isSeqClosed_halfDiscAlgebra pmem htend

/-- Pointwise evaluation of the full Mayer operator. -/
theorem mayerOperatorCLM_apply (f : halfDiscAlgebra) :
    (mayerOperatorCLM f : C(↥halfDisc, ℂ))
        = ∑' n : ℕ, transferSummand n (f : C(↥halfDisc, ℂ)) := rfl

/-- The **Mayer tail**: the full operator minus the `n = 0` summand. -/
def mayerTail : halfDiscAlgebra →L[ℂ] halfDiscAlgebra :=
  mayerOperatorCLM - summandOp 0

theorem mayerOperator_eq : mayerOperatorCLM = summandOp 0 + mayerTail := by
  rw [mayerTail]; abel

theorem mayerTail_apply (f : halfDiscAlgebra) :
    (mayerTail f : C(↥halfDisc, ℂ))
        = ∑' i : ℕ, transferSummand (i + 1) (f : C(↥halfDisc, ℂ)) := by
  have hsplit := (Summable.of_norm (summable_transferSummand_norm f)).sum_add_tsum_nat_add 1
  have h0 : ((summandOp 0 f : C(↥halfDisc, ℂ)))
      = transferSummand 0 (f : C(↥halfDisc, ℂ)) := rfl
  show ((mayerOperatorCLM f : C(↥halfDisc, ℂ)) - (summandOp 0 f : C(↥halfDisc, ℂ)))
      = ∑' i : ℕ, transferSummand (i + 1) (f : C(↥halfDisc, ℂ))
  rw [mayerOperatorCLM_apply, ← hsplit, Finset.sum_range_one, h0]
  abel

theorem mayerTail_sub_partial_apply (k : ℕ) (x : halfDiscAlgebra) :
    mayerTail x - mayerPartial k x
        = ⟨∑' j : ℕ, transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ)),
            mayerShiftSum_mem k x⟩ := by
  refine Subtype.ext ?_
  have hsplit := (Summable.of_norm (summable_shifted_norm 0 x)).sum_add_tsum_nat_add k
  show ((mayerTail x : C(↥halfDisc, ℂ)) - (mayerPartial k x : C(↥halfDisc, ℂ)))
      = ∑' j : ℕ, transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))
  rw [mayerTail_apply, mayerPartial_apply, ← hsplit]
  abel

/-- Operator-norm decay rate: the tail of `Σ 1/(n+1)²`. -/
theorem norm_mayerTail_sub_partial_le (k : ℕ) (x : halfDiscAlgebra) :
    ‖mayerTail x - mayerPartial k x‖
        ≤ (∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2) * ‖x‖ := by
  rw [mayerTail_sub_partial_apply]
  show ‖∑' j : ℕ, transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))‖
      ≤ (∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2) * ‖(x : C(↥halfDisc, ℂ))‖
  have h1 : ‖∑' j : ℕ, transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))‖
      ≤ ∑' j : ℕ, ‖transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))‖ :=
    norm_tsum_le_tsum_norm (summable_shifted_norm k x)
  have h2 : ∑' j : ℕ, ‖transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))‖
      ≤ ∑' j : ℕ, ‖(x : C(↥halfDisc, ℂ))‖ / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 :=
    Summable.tsum_le_tsum (fun j => norm_transferSummand_le (j + k + 1) x)
      (summable_shifted_norm k x)
      (by exact Summable.mul_left ‖(x : C(↥halfDisc, ℂ))‖ (summable_mayerWeights_shifted k))
  have h3 : ∑' j : ℕ, ‖(x : C(↥halfDisc, ℂ))‖ / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2
      = (∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2) * ‖(x : C(↥halfDisc, ℂ))‖ := by
    simp only [div_eq_mul_inv, tsum_mul_left]
    ring
  calc ‖∑' j : ℕ, transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))‖
      ≤ ∑' j : ℕ, ‖transferSummand (j + k + 1) (x : C(↥halfDisc, ℂ))‖ := h1
    _ ≤ ∑' j : ℕ, ‖(x : C(↥halfDisc, ℂ))‖ / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 := h2
    _ = (∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2) * ‖(x : C(↥halfDisc, ℂ))‖ := h3

theorem norm_mayerTail_sub_partial_op (k : ℕ) :
    ‖mayerTail - mayerPartial k‖ ≤ ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 := by
  have hS0 : 0 ≤ ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 :=
    tsum_nonneg fun j => by positivity
  exact ContinuousLinearMap.opNorm_le_of_ball (ε := 1) one_pos hS0
    fun x _ => norm_mayerTail_sub_partial_le k x

/-! ### The tail of the p-series tends to zero -/

/-- The `p = 2` weight as a nonnegative real. -/
private def tailW (i : ℕ) : NNReal := ⟨1 / ((i : ℝ) + 1) ^ 2, by positivity⟩

private theorem tailW_coe (i : ℕ) : (tailW i : ℝ) = 1 / ((i : ℝ) + 1) ^ 2 := rfl

/-- `Σ' j, 1/((j+k+1)+1)² → 0` as `k → ∞`. -/
private theorem tendsto_shifted_tail :
    Tendsto (fun k : ℕ => ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2) atTop (𝓝 0) := by
  have hshift : Tendsto (fun k : ℕ => (∑' j : ℕ, tailW (j + (k + 1)) : NNReal))
      atTop (𝓝 (0 : NNReal)) :=
    (tendsto_add_atTop_iff_nat 1).mpr (NNReal.tendsto_sum_nat_add tailW)
  have hcoe : Tendsto (fun k : ℕ => ((∑' j : ℕ, tailW (j + (k + 1)) : NNReal) : ℝ)) atTop (𝓝 0) :=
    NNReal.tendsto_coe.mpr hshift
  have hfun : (fun k : ℕ => ((∑' j : ℕ, tailW (j + (k + 1)) : NNReal) : ℝ))
      = fun k : ℕ => ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 := by
    funext k
    rw [NNReal.coe_tsum]
    exact congrArg (fun g : ℕ → ℝ => ∑' j : ℕ, g j) (funext fun j => by simp [tailW_coe]; ring)
  exact hcoe.congr fun k => congrFun hfun k

/-- The partial Mayer operators converge to the tail in operator norm. -/
theorem tendsto_mayerPartial : Tendsto mayerPartial atTop (𝓝 mayerTail) := by
  have hmp : ∀ ε > (0 : ℝ), ∃ N : ℕ, ∀ k ≥ N,
      dist (∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2) (0 : ℝ) < ε :=
    Metric.tendsto_atTop.mp tendsto_shifted_tail
  have key : ∀ ε > (0 : ℝ), ∃ N : ℕ, ∀ k ≥ N, dist (mayerPartial k) mayerTail < ε := by
    intro ε hε
    obtain ⟨N, hN⟩ := hmp (ε / 2) (half_pos hε)
    refine ⟨N, fun k hk => ?_⟩
    have hrev : ‖mayerTail - mayerPartial k‖ ≤ ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 :=
      norm_mayerTail_sub_partial_op k
    have hstep : ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 < ε / 2 := by
      have h := hN k hk
      rw [Real.dist_eq, sub_zero, abs_of_nonneg (tsum_nonneg fun j => by positivity)] at h
      exact h
    have hle : ‖mayerPartial k - mayerTail‖ ≤ ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 := by
      rw [norm_sub_rev (mayerPartial k) mayerTail]
      exact hrev
    have hdist : dist (mayerPartial k) mayerTail = ‖mayerPartial k - mayerTail‖ :=
      dist_eq_norm (mayerPartial k) mayerTail
    have hle2 : dist (mayerPartial k) mayerTail ≤ ∑' j : ℕ, 1 / (((j + k + 1 : ℕ) : ℝ) + 1) ^ 2 := by
      rw [hdist]
      exact hle
    have hfinal : dist (mayerPartial k) mayerTail < ε :=
      lt_of_le_of_lt hle2 (lt_of_lt_of_le hstep (by linarith))
    exact hfinal
  exact Metric.tendsto_atTop.mpr key

/-! ### Compactness -/

/-- **The compact tail of the Mayer operator** (RH-42): if every summand
`n ≥ 1` is compact — the Ascoli content of T3, since those branches map the
half-disc into its interior — then the Mayer tail is a compact operator.
This is the honest entry point: `mayerOperatorCLM = summandOp 0 + mayerTail`
and the `n = 0` branch is not compact. -/
theorem isCompactOperator_mayerTail (hS : ∀ n : ℕ, 0 < n → IsCompactOperator (summandOp n)) :
    IsCompactOperator mayerTail := by
  have hfinite : ∀ k : ℕ, IsCompactOperator ⇑(mayerPartial k) := by
    intro k
    induction k with
    | zero =>
        simp only [mayerPartial, Finset.range_zero, Finset.sum_empty]
        exact isCompactOperator_zero
    | succ k ih =>
        have hsplit : mayerPartial (k + 1) = mayerPartial k + summandOp (k + 1) := by
          simp only [mayerPartial, Finset.sum_range_succ]
        rw [hsplit]
        exact IsCompactOperator.add ih (hS (k + 1) (Nat.succ_pos k))
  exact isCompactOperator_of_tendsto_nat tendsto_mayerPartial hfinite

/-- The summand operator `summandOp n` is compact under the surgical Montel
hypothesis: the coe `halfDiscAlgebra → C(↥halfDisc, ℂ)` is an isometry
(`rfl` — the subalgebra norm is the ambient coe norm), hence a closed
embedding, and preimages of compact sets under closed embeddings are compact.
Pointwise, `↑(summandOp n f) = transferSummandCLM n f` holds by `rfl`. -/
theorem isCompactOperator_summandOp_of_pointwiseRelCompact (n : ℕ) (hn : 0 < n)
    (hrc : IsCompact (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ))) :
    IsCompactOperator (summandOp n) := by
  obtain ⟨K, hK, hKf⟩ := isCompactOperator_transferSummandCLM_of_pointwiseRelCompact n hn hrc
  have hcemb : IsClosedEmbedding
      (Subtype.val : {x : C(↥halfDisc, ℂ) // x ∈ halfDiscAlgebra} → C(↥halfDisc, ℂ)) :=
    Isometry.isClosedEmbedding fun _a _b => rfl
  refine ⟨Subtype.val ⁻¹' K, IsClosedEmbedding.isCompact_preimage hcemb hK, ?_⟩
  have hpre : (summandOp n) ⁻¹' (Subtype.val ⁻¹' K)
      = (transferSummandCLM n) ⁻¹' K := by
    ext f
    exact Iff.rfl
  rw [hpre]
  exact hKf

/-- **The honest unconditional shape of RH-42**: the Mayer tail is a compact
operator as soon as the single normal-families input holds for every
`n ≥ 1` — the pointwise image of the transfer family on the unit ball is
relatively compact in `↥halfDisc → ℂ` (Montel / Vitali–Porter, phase-3
frontier).  This chains the surgical T3 reduction through
`isCompactOperator_summandOp_of_pointwiseRelCompact` into the T5 assembly. -/
theorem isCompactOperator_mayerTail_of_pointwiseRelCompact
    (hrc : ∀ n : ℕ, 0 < n → IsCompact (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ))) :
    IsCompactOperator mayerTail :=
  isCompactOperator_mayerTail fun n hn =>
    isCompactOperator_summandOp_of_pointwiseRelCompact n hn (hrc n hn)

/-- **The honest shape of the phase-3 frontier**: if for every `n ≥ 1` the
pointwise image of the unit-ball transfer family is CLOSED in the product
topology of `↥halfDisc → ℂ` — the pure Vitali–Porter fact that pointwise
limits of uniformly bounded holomorphic maps are holomorphic, with no
topology left in the hypotheses — then the Mayer tail is a compact operator.
This composes `isCompactOperator_transferSummandCLM_of_piClosed` (T3) with
the `isCompactOperator_summandOp_of_pointwiseRelCompact` transfer and the T5
assembly. -/
theorem isCompactOperator_mayerTail_of_piClosed
    (hclosed : ∀ n : ℕ, 0 < n → IsClosed (ContinuousMap.toFun ''
      ((fun f : {g : halfDiscAlgebra // ‖g‖ ≤ 1} => transferSummandCLM n f.1) '' univ))) :
    IsCompactOperator mayerTail :=
  isCompactOperator_mayerTail fun n hn =>
    isCompactOperator_summandOp_of_pointwiseRelCompact n hn
      (IsCompact.of_isClosed_subset (isCompact_piClosure_transferImage n) (hclosed n hn)
        subset_closure)

end

end Riemann
