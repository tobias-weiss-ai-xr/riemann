/-
Copyright (c) 2026 Tobias Weiss
Gauss-Map Transfer Operator on the DISK (Ruelle space)

This file moves the Ruelle transfer operator of the Gauss map onto the closed
disks: for `E := C(closedBall 0 2, ℂ)` (sup norm) and fixed `s : ℂ` with
`1/2 < s.re`, we define

    (L_s f)(z) := ∑' n, (n + 3 + z)^(-2s) · f(1/(n + 3 + z))

The branches are indexed with a shift of `+3`: the na�ve branches `1/(n+1+z)`
for `n = 0, 1` develop zeros at `z = -1` (inside the disk) and `z = -2` (on
the boundary), so they do NOT define continuous weights on the whole closed
ball (cpow has no continuous branch across a zero).  Shifting to
`1/(n+3+z)` gives `‖n + 3 + z‖ ≥ n + 1 ≥ 1` everywhere on the disk, which is
exactly the hypothesis the cpow branch and the M-test need (this is the
"NEVER n = 0" / shift convention of the disk operator).

Author: Tobias Weiss
References:
- Mayer, G. (1990). "The Riemann zeta function and the transfer operator"
- Baladi, V. (2000). "Positive Transfer Operators and Decay of Correlations"
-/

import Mathlib.Analysis.Complex.Basic
import Mathlib.Analysis.Normed.Group.FunctionSeries
import Mathlib.Analysis.Normed.Operator.Basic
import Mathlib.Analysis.SpecialFunctions.Pow.Continuity
import Mathlib.Topology.ContinuousMap.Algebra
import Mathlib.Topology.ContinuousMap.Compact
import Riemann.TransferOperator.Operator
import Riemann.TransferOperator.BasicProofs

/-!
# The Disk Transfer Operator (Ruelle Space)

## Main Definitions

- `Disk`: the closed disk `Metric.closedBall (0 : ℂ) 2`
- `DiskSpace`: `C(Disk, ℂ)` with sup norm (the Ruelle space)
- `diskWeight s n z`: the branch weight `(n + 3 + z)^(-2s)` (cpow)
- `diskInverseBranch n z`: the branch point `1/(n + 3 + z)`
- `diskSummandCm s f n`: the n-th summand as a continuous map
- `transferOperatorDisk s hs`: `L_s : DiskSpace →L[ℂ] DiskSpace` (the main theorem)

## Main Theorems

- `diskWeight_norm_le`: x-free bound `‖(n+3+z)^(-2s)‖ ≤ (n+1)^(-2·Re s) · exp(2π|Im s|)`
- `diskSummandCm_norm_summable`: the M-test (series of sup norms converges)
- `transferOperatorDisk_tsum` / `transferOperatorDisk_apply`: the tsum equations
- `diskOperator_uniform_convergence`: partial sums converge to `L_s f` uniformly on the disk

## A note on compactness

The disk is the natural Ruelle space for determinant theories, and `L_s` is a
bounded operator here.  However, `IsCompactOperator (transferOperatorDisk s hs)`
is FALSE on `C(closedBall 0 2, ℂ)` — the same phenomenon recorded for
`transferOperator` on `C([0,1], ℂ)` in `Riemann.TransferOperator.Operator`.

Reason: a bounded-weight composition piece `f ↦ w_n · (f ∘ T n)`, where
`T n z = 1/(n+3+z)` is a homeomorphism of the disk onto an infinite set, is
not compact on `C(X)`: the sup-norm unit ball is not equicontinuous (the
functions `f_k(z) = sin(k·Re z)` oscillate at high frequency), so by
Arzelà–Ascoli its image under any nontrivial branch piece is not relatively
compact, and neither is the image under `L_s`.  Compactness of the Gauss-map
transfer operator is a theorem about holomorphic (disc-algebra) or Lipschitz
classes (Mayer's setting), not about all continuous functions.  The genuinely
provable content here, uniform convergence of the Ruelle series on the disk,
is recorded in `diskOperator_uniform_convergence`.
-/

namespace Riemann.DiskOperator

noncomputable section

open Complex BigOperators
open scoped ContinuousMap Topology Real

/-- The closed disk of radius 2 about 0 in ℂ, as a type. -/
abbrev Disk := Metric.closedBall (0 : ℂ) 2

/-- The Ruelle space: continuous functions on the closed disk with sup norm. -/
abbrev DiskSpace := C(Disk, ℂ)

/-- For `z` in the closed disk of radius 2, `‖z‖ ≤ 2`. -/
lemma diskNormBound (z : Disk) : ‖(z : ℂ)‖ ≤ 2 := by
  have h : dist (z : ℂ) 0 ≤ 2 := z.2
  rw [dist_eq_norm] at h
  simpa using h

/-! ## The shifted branch bases -/

/-- The real part of the branch base `n + 3 + z` is positive on the disk:
`Re(n+3+z) = n + 3 + Re z ≥ n + 1 ≥ 1`. -/
theorem diskBase_re_pos (n : ℕ) (z : Disk) : 0 < ((n : ℂ) + 3 + (z : ℂ)).re := by
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have h1 : |(z : ℂ).re| ≤ ‖(z : ℂ)‖ := Complex.abs_re_le_norm (z : ℂ)
  have h2 : -(‖(z : ℂ)‖) ≤ (z : ℂ).re := (abs_le.mp h1).1
  have hre : (-2 : ℝ) ≤ (z : ℂ).re := by nlinarith [h2, diskNormBound z]
  have hred : ((n : ℂ) + 3 + (z : ℂ)).re = (n : ℝ) + 3 + (z : ℂ).re := by simp
  rw [hred]
  nlinarith [hnn, hre]

/-- The branch base is nonzero on the disk (positive real part). -/
theorem diskBase_ne_zero (n : ℕ) (z : Disk) : (n : ℂ) + 3 + (z : ℂ) ≠ 0 := by
  intro h
  have hre : ((n : ℂ) + 3 + (z : ℂ)).re = 0 := congrArg Complex.re h
  have hpos : 0 < ((n : ℂ) + 3 + (z : ℂ)).re := diskBase_re_pos n z
  linarith

/-- Lower bound on the branch base on the disk: `‖n + 3 + z‖ ≥ n + 1 ≥ 1`. -/
theorem diskBase_norm_ge (n : ℕ) (z : Disk) :
    (n : ℝ) + 1 ≤ ‖(n : ℂ) + 3 + (z : ℂ)‖ := by
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have h1 : |(z : ℂ).re| ≤ ‖(z : ℂ)‖ := Complex.abs_re_le_norm (z : ℂ)
  have h2 : -(‖(z : ℂ)‖) ≤ (z : ℂ).re := (abs_le.mp h1).1
  have hre : (-2 : ℝ) ≤ (z : ℂ).re := by nlinarith [h2, diskNormBound z]
  have hmain : (n : ℝ) + 3 + (z : ℂ).re ≤ ‖(n : ℂ) + 3 + (z : ℂ)‖ := by
    calc
      (n : ℝ) + 3 + (z : ℂ).re = ((n : ℂ) + 3 + (z : ℂ)).re := by simp
      _ ≤ ‖(n : ℂ) + 3 + (z : ℂ)‖ := Complex.re_le_norm _
  nlinarith [hnn, hre]

/-- The branch `z ↦ 1/(n + 3 + z)` maps the disk into itself:
`‖1/(n+3+z)‖ ≤ 2` since `‖n+3+z‖ ≥ 1`. -/
theorem mem_disk_of_branch (n : ℕ) (z : Disk) :
    ((n : ℂ) + 3 + (z : ℂ))⁻¹ ∈ Metric.closedBall (0 : ℂ) 2 := by
  rw [Metric.mem_closedBall]
  rw [dist_eq_norm]
  simp
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have hw : 1 ≤ ‖(n : ℂ) + 3 + (z : ℂ)‖ := by
    have h := diskBase_norm_ge n z
    nlinarith [hnn]
  have hwne : (n : ℂ) + 3 + (z : ℂ) ≠ 0 := diskBase_ne_zero n z
  have hwpos : 0 < ‖(n : ℂ) + 3 + (z : ℂ)‖ := norm_pos_iff.mpr hwne
  have h : ‖(n : ℂ) + 3 + (z : ℂ)‖⁻¹ ≤ 1 := (inv_le_one₀ hwpos).2 hw
  linarith

/-! ## The weight and its x-free bound -/

/-- The n-th branch weight on the disk: `(n + 3 + z)^(-2s)` (cpow, well-defined
on the disk since the base has positive real part). -/
noncomputable def diskWeight (s : ℂ) (n : ℕ) (z : ℂ) : ℂ :=
  ((n : ℂ) + 3 + z) ^ (-(2 * s))

/-- The x-free M-test bound on the n-th weight:
`(n + 1)^(-2·Re s) · exp(2π·|Im s|)`.  The exponential factor absorbs the
argument term of the cpow branch (`‖z^w‖ = ‖z‖^(Re w) / exp(arg z · Im w)`). -/
noncomputable def diskWeightBound (s : ℂ) (n : ℕ) : ℝ :=
  ((n : ℝ) + 1) ^ (-(2 * s.re)) * Real.exp (2 * π * |s.im|)

/-- The x-free bound is nonnegative. -/
theorem diskWeightBound_nonneg (s : ℂ) (n : ℕ) : 0 ≤ diskWeightBound s n := by
  unfold diskWeightBound
  exact mul_nonneg (Real.rpow_nonneg (by positivity) _) (Real.exp_pos _).le

/-- Norm of the n-th weight, bounded by the x-free bound:
`‖(n + 3 + z)^(-2s)‖ ≤ (n + 1)^(-2·Re s) · exp(2π·|Im s|)` on the whole disk. -/
theorem diskWeight_norm_le (s : ℂ) (hs : 1 / 2 < s.re) (n : ℕ) (z : Disk) :
    ‖diskWeight s n (z : ℂ)‖ ≤ diskWeightBound s n := by
  unfold diskWeight diskWeightBound
  let w : ℂ := (n : ℂ) + 3 + (z : ℂ)
  have hσ : 0 < 2 * s.re := by linarith
  have hnn : (0 : ℝ) ≤ (n : ℝ) := Nat.cast_nonneg n
  have hnp1 : 0 ≤ (n : ℝ) + 1 := by positivity
  have hnp1pos : 0 < (n : ℝ) + 1 := by positivity
  have hwpos : 0 < ‖w‖ := norm_pos_iff.mpr (by simpa [w] using diskBase_ne_zero n z)
  have hr : ((n : ℝ) + 1) ^ (2 * s.re) ≤ ‖w‖ ^ (2 * s.re) := by
    simpa [w] using Real.rpow_le_rpow hnp1 (diskBase_norm_ge n z) (le_of_lt hσ)
  have hX : ‖w‖ ^ (-(2 * s.re)) ≤ ((n : ℝ) + 1) ^ (-(2 * s.re)) := by
    rw [Real.rpow_neg hnp1, Real.rpow_neg (norm_nonneg _)]
    exact (inv_le_inv₀ (Real.rpow_pos_of_pos hwpos _) (Real.rpow_pos_of_pos hnp1pos _)).2 hr
  have harg : |w.arg| ≤ π := Complex.abs_arg_le_pi w
  have hle0 : w.arg * s.im ≤ |w.arg| * |s.im| := by
    calc
      w.arg * s.im ≤ |w.arg * s.im| := le_abs_self _
      _ = |w.arg| * |s.im| := by rw [abs_mul]
  have hle : 2 * w.arg * s.im ≤ 2 * π * |s.im| := by
    calc
      2 * w.arg * s.im = 2 * (w.arg * s.im) := by ring
      _ ≤ 2 * (|w.arg| * |s.im|) := by
        exact mul_le_mul_of_nonneg_left hle0 (by norm_num)
      _ ≤ 2 * (π * |s.im|) := by
        exact mul_le_mul_of_nonneg_left
          (mul_le_mul_of_nonneg_right harg (abs_nonneg s.im)) (by norm_num)
      _ = 2 * π * |s.im| := by ring
  have hEinv : (Real.exp (w.arg * (-(2 * s.im))))⁻¹ ≤ Real.exp (2 * π * |s.im|) := by
    rw [← Real.exp_neg]
    rw [show -(w.arg * (-(2 * s.im))) = 2 * w.arg * s.im by ring]
    exact Real.exp_le_exp.mpr hle
  calc
    ‖((n : ℂ) + 3 + (z : ℂ)) ^ (-(2 * s))‖
        = Real.rpow ‖w‖ (-(2 * s.re)) / Real.exp (w.arg * (-(2 * s.im))) := by
          rw [Complex.norm_cpow_of_ne_zero (by simpa [w] using diskBase_ne_zero n z) (-(2 * s))]
          simp [w]
    _ = Real.rpow ‖w‖ (-(2 * s.re)) * (Real.exp (w.arg * (-(2 * s.im))))⁻¹ := by
          rw [div_eq_mul_inv]
    _ ≤ Real.rpow ((n : ℝ) + 1) (-(2 * s.re)) * (Real.exp (w.arg * (-(2 * s.im))))⁻¹ := by
          exact mul_le_mul_of_nonneg_right hX (inv_nonneg.mpr (Real.exp_pos _).le)
    _ ≤ Real.rpow ((n : ℝ) + 1) (-(2 * s.re)) * Real.exp (2 * π * |s.im|) := by
          exact mul_le_mul_of_nonneg_left hEinv (Real.rpow_nonneg (by positivity) _)

/-! ## Summands and pointwise summability -/

/-- The n-th inverse branch point: `1/(n + 3 + z)`. -/
noncomputable def diskInverseBranch (n : ℕ) (z : ℂ) : ℂ :=
  ((n : ℂ) + 3 + z)⁻¹

/-- The n-th summand of the Ruelle series, evaluated at `z`. -/
noncomputable def diskSummand (s : ℂ) (f : DiskSpace) (n : ℕ) (z : Disk) : ℂ :=
  diskWeight s n (z : ℂ) * f ⟨diskInverseBranch n (z : ℂ), mem_disk_of_branch n z⟩

/-! ## Continuous-map summands (M-test scaffolding) -/

/-- The n-th weight as a continuous function on the disk (cpow over a slit-plane-free
base: `Re(n+3+z) ≥ 1 > 0`). -/
noncomputable def diskWeightCm (s : ℂ) (n : ℕ) : C(Disk, ℂ) :=
  ⟨fun z => diskWeight s n (z : ℂ), by
    unfold diskWeight
    exact Continuous.cpow
      ((continuous_const.add continuous_id).comp continuous_subtype_val)
      continuous_const
      (fun z => by
        rw [Complex.mem_slitPlane_iff]
        exact Or.inl (diskBase_re_pos n z))
  ⟩

/-- The n-th inverse branch as a continuous self-map of the disk. -/
theorem diskInverseBranch_continuous (n : ℕ) :
    Continuous fun z : Disk => diskInverseBranch n (z : ℂ) := by
  change Continuous fun z : Disk => (((n : ℂ) + 3 + (z : ℂ)) : ℂ)⁻¹
  have hden : Continuous fun z : Disk => (n : ℂ) + 3 + (z : ℂ) :=
    (continuous_const.add continuous_id).comp continuous_subtype_val
  exact hden.inv₀ (fun z => diskBase_ne_zero n z)

/-- The n-th inverse branch as an element of `C(Disk, Disk)`. -/
noncomputable def diskInverseBranchCm (n : ℕ) : C(Disk, Disk) :=
  ⟨fun z => ⟨diskInverseBranch n (z : ℂ), mem_disk_of_branch n z⟩,
    Continuous.subtype_mk (diskInverseBranch_continuous n) (fun z => mem_disk_of_branch n z)⟩

/-- The n-th summand as a continuous map on the disk. -/
noncomputable def diskSummandCm (s : ℂ) (f : DiskSpace) (n : ℕ) : DiskSpace :=
  diskWeightCm s n * (f.comp (diskInverseBranchCm n))

/-- The pointwise value of the continuous-map summand agrees with the original. -/
theorem diskSummandCm_apply (s : ℂ) (f : DiskSpace) (n : ℕ) (z : Disk) :
    diskSummandCm s f n z = diskSummand s f n z := by
  unfold diskSummandCm diskWeightCm diskInverseBranchCm
  rfl

/-- The sup norm of the n-th weight is bounded by the x-free bound. -/
theorem diskWeightCm_norm_le (s : ℂ) (hs : 1 / 2 < s.re) (n : ℕ) :
    ‖diskWeightCm s n‖ ≤ diskWeightBound s n := by
  exact (ContinuousMap.norm_le (diskWeightCm s n) (diskWeightBound_nonneg s n)).2 (by
    intro z
    simpa [diskWeightCm] using diskWeight_norm_le s hs n z)

/-- Composition by a continuous self-map of the disk cannot increase the sup norm. -/
lemma disk_comp_norm_le (f : DiskSpace) (g : C(Disk, Disk)) : ‖f.comp g‖ ≤ ‖f‖ := by
  exact (ContinuousMap.norm_le (f.comp g) (norm_nonneg _)).2 (by
    intro z
    simpa using (ContinuousMap.norm_coe_le_norm f (g z) : ‖f (g z)‖ ≤ ‖f‖))

/-- The uniform (sup-norm) bound on each summand: `‖wₙ·(f∘Iₙ)‖ ≤ Bₙ·‖f‖`. -/
theorem diskSummandCm_norm_le (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace) (n : ℕ) :
    ‖diskSummandCm s f n‖ ≤ diskWeightBound s n * ‖f‖ := by
  calc
    ‖diskSummandCm s f n‖ = ‖diskWeightCm s n * (f.comp (diskInverseBranchCm n))‖ := rfl
    _ ≤ ‖diskWeightCm s n‖ * ‖f.comp (diskInverseBranchCm n)‖ := norm_mul_le _ _
    _ ≤ ‖diskWeightCm s n‖ * ‖f‖ :=
        mul_le_mul_of_nonneg_left (disk_comp_norm_le f _) (norm_nonneg _)
    _ ≤ diskWeightBound s n * ‖f‖ :=
        mul_le_mul_of_nonneg_right (diskWeightCm_norm_le s hs n) (norm_nonneg _)

/-- Summability of the x-free bounds: `∑ (n+1)^(-2·Re s)` converges for
`Re s > 1/2` (the p-series), hence so does `∑ Bₙ`. -/
theorem diskWeightBound_summable (s : ℂ) (hs : 1 / 2 < s.re) :
    Summable fun n : ℕ => diskWeightBound s n := by
  unfold diskWeightBound
  simpa using Summable.mul_right (Real.exp (2 * π * |s.im|))
    (Riemann.TransferOperator.sum_inverse_pow_converges s.re 0 hs (by norm_num) :
      Summable fun n : ℕ => ((n : ℝ) + 1 + 0) ^ (-2 * s.re))

/-- Pointwise summability of the summands (via the M-test bound). -/
theorem diskSummand_summable (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace) (z : Disk) :
    Summable fun n : ℕ => diskSummand s f n z := by
  refine Summable.of_norm ?_
  refine Summable.of_nonneg_of_le (fun n => norm_nonneg _) ?_
    (Summable.mul_right ‖f‖ (diskWeightBound_summable s hs))
  intro n
  rw [diskSummand, norm_mul]
  exact mul_le_mul (diskWeight_norm_le s hs n z) (ContinuousMap.norm_coe_le_norm f _)
    (norm_nonneg _) (diskWeightBound_nonneg s n)

/-- The sup norms of the summands are summable (the M-test): for `Re s > 1/2`
the series of `Bₙ·‖f‖` converges and dominates every summand. -/
theorem diskSummandCm_norm_summable (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace) :
    Summable fun n : ℕ => ‖diskSummandCm s f n‖ :=
  Summable.of_nonneg_of_le (fun _ => norm_nonneg _) (diskSummandCm_norm_le s hs f)
    (Summable.mul_right ‖f‖ (diskWeightBound_summable s hs))

/-- The summands themselves are summable as continuous maps (`C(Disk, ℂ)` is complete). -/
theorem diskSummandCm_summable (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace) :
    Summable fun n : ℕ => diskSummandCm s f n :=
  (diskSummandCm_norm_summable s hs f).of_norm

/-! ## The bounded operator -/

/-- Bounded-operator construction: `L_s` on the disk `C(closedBall 0 2, ℂ)`.

`(L_s f)(z) = ∑' n, wₙ(z)·f(Iₙ(z))`, assembled via the M-test
(`diskSummandCm_norm_summable`) and `LinearMap.mkContinuous`, with operator
norm `≤ ∑' n, Bₙ`.  This is the Ruelle space operator on which the eventual
Fredholm determinant theory lives. -/
noncomputable def transferOperatorDisk (s : ℂ) (hs : 1 / 2 < s.re) :
    DiskSpace →L[ℂ] DiskSpace := by
  have hsum : ∀ f : DiskSpace, Summable fun n : ℕ => diskSummandCm s f n :=
    fun f => diskSummandCm_summable s hs f
  have hnorm : ∀ f : DiskSpace, Summable fun n : ℕ => ‖diskSummandCm s f n‖ :=
    fun f => diskSummandCm_norm_summable s hs f
  let op (f : DiskSpace) : DiskSpace := ∑' n : ℕ, diskSummandCm s f n
  have hold : ∀ f : DiskSpace, ‖op f‖ ≤ (∑' n : ℕ, diskWeightBound s n) * ‖f‖ := by
    intro f
    calc
      ‖op f‖ ≤ ∑' n : ℕ, ‖diskSummandCm s f n‖ := norm_tsum_le_tsum_norm (hnorm f)
      _ ≤ ∑' n : ℕ, diskWeightBound s n * ‖f‖ :=
          (hnorm f).tsum_le_tsum (diskSummandCm_norm_le s hs f)
            (Summable.mul_right ‖f‖ (diskWeightBound_summable s hs))
      _ = (∑' n : ℕ, diskWeightBound s n) * ‖f‖ :=
          (diskWeightBound_summable s hs).tsum_mul_right ‖f‖
  let lin : DiskSpace →ₗ[ℂ] DiskSpace :=
  { toFun := op
    map_add' := by
      intro f g
      unfold op
      rw [← (hsum f).tsum_add (hsum g)]
      apply tsum_congr
      intro n
      ext z
      unfold diskSummandCm
      simp [mul_add]
    map_smul' := by
      intro a f
      ext z
      unfold op
      change (∑' n : ℕ, diskSummandCm s (a • f) n) z =
        (a • (∑' n : ℕ, diskSummandCm s f n)) z
      rw [← ContinuousMap.tsum_apply (hsum (a • f)) z]
      rw [show (a • (∑' n : ℕ, diskSummandCm s f n)) z =
          a • ((∑' n : ℕ, diskSummandCm s f n) z) by simp [smul_eq_mul]]
      rw [← ContinuousMap.tsum_apply (hsum f) z]
      calc
        (∑' n : ℕ, (diskSummandCm s (a • f) n) z)
            = ∑' n : ℕ, a * (diskSummandCm s f n) z := by
              apply tsum_congr
              intro n
              unfold diskSummandCm
              simp [smul_eq_mul, mul_comm]
        _ = a * (∑' n : ℕ, (diskSummandCm s f n) z) := by
              rw [tsum_mul_left]
        _ = a • (∑' n : ℕ, (diskSummandCm s f n) z) := by
              simp [smul_eq_mul]
  }
  exact LinearMap.mkContinuous lin (∑' n : ℕ, diskWeightBound s n) hold

/-- `L_s f` is the infinite sum of the continuous-map summands (tsum equation). -/
theorem transferOperatorDisk_tsum (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace) :
    (∑' n : ℕ, diskSummandCm s f n) = transferOperatorDisk s hs f := by
  simp [transferOperatorDisk]

/-- Pointwise action formula: `(L_s f)(z) = ∑' n, diskSummand s f n z`. -/
theorem transferOperatorDisk_apply (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace)
    (z : Disk) :
    transferOperatorDisk s hs f z = ∑' n : ℕ, diskSummand s f n z := by
  rw [← transferOperatorDisk_tsum s hs f]
  rw [← ContinuousMap.tsum_apply (diskSummandCm_summable s hs f) z]
  apply tsum_congr
  intro n
  exact diskSummandCm_apply s f n z

/-- Uniform convergence of the Ruelle series on the disk: the partial sums
`∑ i < N, wᵢ·(f∘Iᵢ)` converge to `L_s f` in the sup norm of `C(closedBall 0 2, ℂ)`,
uniformly in `z`.  This is the analytic content that a compactness claim was
meant to capture on the Ruelle space (see the module docstring: `IsCompactOperator`
fails on all of `C(closedBall 0 2, ℂ)`, so the corrected statement records the
guaranteed convergence instead). -/
theorem diskOperator_uniform_convergence (s : ℂ) (hs : 1 / 2 < s.re) (f : DiskSpace) :
    Filter.Tendsto (fun N : ℕ => ∑ i ∈ Finset.range N, diskSummandCm s f i)
      Filter.atTop (𝓝 (transferOperatorDisk s hs f)) := by
  rw [← transferOperatorDisk_tsum s hs f]
  exact (diskSummandCm_summable s hs f).hasSum.tendsto_sum_nat

/-- Operator-norm bound (tsum-based): `‖L_s‖ ≤ ∑' n, Bₙ`. -/
theorem transferOperatorDisk_norm_le (s : ℂ) (hs : 1 / 2 < s.re) :
    ‖transferOperatorDisk s hs‖ ≤ ∑' n : ℕ, diskWeightBound s n := by
  refine ContinuousLinearMap.opNorm_le_bound _ ?_ ?_
  · exact tsum_nonneg fun n => diskWeightBound_nonneg s n
  · intro f
    calc
      ‖transferOperatorDisk s hs f‖ = ‖∑' n : ℕ, diskSummandCm s f n‖ := by
          rw [transferOperatorDisk_tsum s hs f]
      _ ≤ ∑' n : ℕ, ‖diskSummandCm s f n‖ := by
          exact norm_tsum_le_tsum_norm (diskSummandCm_norm_summable s hs f)
      _ ≤ ∑' n : ℕ, diskWeightBound s n * ‖f‖ := by
          exact (diskSummandCm_norm_summable s hs f).tsum_le_tsum
            (diskSummandCm_norm_le s hs f)
            (Summable.mul_right ‖f‖ (diskWeightBound_summable s hs))
      _ = (∑' n : ℕ, diskWeightBound s n) * ‖f‖ := by
          exact (diskWeightBound_summable s hs).tsum_mul_right ‖f‖

end -- noncomputable section

end Riemann.DiskOperator
