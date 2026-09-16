/-
Copyright (c) 2026 Tobias Weiss. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
-/
import Mathlib.Analysis.Complex.LocallyUniformLimit
import Mathlib.Topology.ContinuousMap.Algebra
import Mathlib.Topology.UniformSpace.LocallyUniformConvergence
import Mathlib.Topology.UniformSpace.UniformConvergence

/-!
# The disc algebra (Mayer analytic class, phase 1)

The **disc algebra**: complex-valued continuous functions on the closed unit
disc that are holomorphic on its interior, as a closed complete subalgebra of
`C(closedBall (0:ℂ) 1, ℂ)` with the sup norm, and evaluation at interior
points as a norm-one continuous linear functional.

This is the analytic class on which Mayer's transfer operator for the Gauss
map will be realized (where compactness holds, unlike on `C([0,1])` — see
`research/FRONTIER.md` §3b).  Phase 1 provides the space; the operator and
its compactness are future phases.

## Main definitions and results

* `Riemann.toHol`: view a continuous function on the closed disc as a plain
  function `ℂ → ℂ` (values on the disc, zero outside).
* `Riemann.discAlgebra`: the subalgebra of `C(closedBall (0:ℂ) 1, ℂ)` whose
  elements are holomorphic on the interior.
* `Riemann.isClosed_carrier`: the disc algebra is closed in the sup norm —
  the Weierstrass theorem: uniform limits of holomorphic functions are
  holomorphic (`TendstoLocallyUniformlyOn.differentiableOn`).
* `Riemann.discAlgebra_complete`: hence the disc algebra is a Banach space.
* `Riemann.discAlgebraEval`, `Riemann.norm_discAlgebraEval_le`: evaluation at
  an interior point is a continuous functional of norm ≤ 1.

## TODO

* Phase 2: the Mayer transfer operator on `discAlgebra` (image of a function
  under the Gauss-map inverse-branch potentials), boundedness, and
  compactness via Montel/Arzelà–Ascoli.
-/

open Metric Set Filter Complex Topology
open scoped Classical

namespace Riemann

noncomputable section

variable {f g : C(closedBall (0 : ℂ) 1, ℂ)} {u : ℕ → C(closedBall (0 : ℂ) 1, ℂ)} {z : ℂ}

/-- View a continuous function on the closed unit disc as a plain complex
function on `ℂ`: values on the disc, zero outside. -/
def toHol (f : C(closedBall (0 : ℂ) 1, ℂ)) : ℂ → ℂ := fun z =>
  if h : z ∈ closedBall (0 : ℂ) 1 then f ⟨z, h⟩ else 0

theorem toHol_apply (f : C(closedBall (0 : ℂ) 1, ℂ)) (z : ℂ)
    (hz : z ∈ closedBall (0 : ℂ) 1) : toHol f z = f ⟨z, hz⟩ := by
  unfold toHol
  exact dif_pos hz

theorem toHol_apply_mem (f : C(closedBall (0 : ℂ) 1, ℂ)) (hz : z ∈ ball (0 : ℂ) 1) :
    toHol f z = f ⟨z, mem_closedBall.mpr hz.le⟩ :=
  toHol_apply f z (mem_closedBall.mpr hz.le)

theorem toHol_apply_of_not_mem (f : C(closedBall (0 : ℂ) 1, ℂ)) (hz : z ∉ closedBall (0 : ℂ) 1) :
    toHol f z = 0 := by
  unfold toHol
  exact dif_neg hz

theorem toHol_add (a b : C(closedBall (0 : ℂ) 1, ℂ)) (w : ℂ) (hw : w ∈ closedBall (0 : ℂ) 1) :
    toHol (a + b) w = (toHol a + toHol b) w := by
  rw [toHol_apply (a + b) w hw, ContinuousMap.coe_add]
  simp only [Pi.add_apply, toHol_apply a w hw, toHol_apply b w hw]

theorem toHol_mul (a b : C(closedBall (0 : ℂ) 1, ℂ)) (w : ℂ) (hw : w ∈ closedBall (0 : ℂ) 1) :
    toHol (a * b) w = (toHol a * toHol b) w := by
  rw [toHol_apply (a * b) w hw, ContinuousMap.coe_mul]
  simp only [Pi.mul_apply, toHol_apply a w hw, toHol_apply b w hw]

theorem toHol_const (c : ℂ) (w : ℂ) (hw : w ∈ closedBall (0 : ℂ) 1) :
    toHol (algebraMap ℂ C(closedBall (0 : ℂ) 1, ℂ) c) w = c := by
  rw [toHol_apply _ w hw]
  simp

/-- The disc algebra: continuous functions on the closed unit disc that are
holomorphic on the open unit disc. -/
def discAlgebra : Subalgebra ℂ C(closedBall (0 : ℂ) 1, ℂ) where
  carrier := {f | DifferentiableOn ℂ (toHol f) (ball (0 : ℂ) 1)}
  add_mem' {a b} ha hb := by
    refine DifferentiableOn.congr (ha.add hb) fun w hw => ?_
    exact toHol_add a b w (mem_closedBall.mpr hw.le)
  mul_mem' {a b} ha hb := by
    refine DifferentiableOn.congr (ha.mul hb) fun w hw => ?_
    exact toHol_mul a b w (mem_closedBall.mpr hw.le)
  algebraMap_mem' c := by
    refine DifferentiableOn.congr (differentiableOn_const c) fun w hw => ?_
    exact toHol_const c w (mem_closedBall.mpr hw.le)
  zero_mem' := by
    refine DifferentiableOn.congr (differentiableOn_const (0 : ℂ)) fun w hw => ?_
    have := toHol_const 0 w (mem_closedBall.mpr hw.le)
    rwa [map_zero] at this
  one_mem' := by
    refine DifferentiableOn.congr (differentiableOn_const (1 : ℂ)) fun w hw => ?_
    have := toHol_const 1 w (mem_closedBall.mpr hw.le)
    rwa [map_one] at this

theorem mem_discAlgebra (f : C(closedBall (0 : ℂ) 1, ℂ)) :
    f ∈ discAlgebra ↔ DifferentiableOn ℂ (toHol f) (ball (0 : ℂ) 1) :=
  ⟨fun h => h, fun h => h⟩

/-- Uniform limits in `C(closed unit disc)` restrict to uniformly convergent
sequences of the holomorphic extensions, on the closed disc. -/
theorem tendstoUniformlyOn_toHol {x : C(closedBall (0 : ℂ) 1, ℂ)}
    (hu : Tendsto u atTop (𝓝 x)) :
    TendstoUniformlyOn (fun n => toHol (u n)) (toHol x) atTop (closedBall (0 : ℂ) 1) := by
  rw [tendstoUniformlyOn_iff]
  intro ε hε
  obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp hu ε hε)
  refine Filter.Eventually.mono (Filter.eventually_ge_atTop N) fun n hn => ?_
  intro w hw
  have hdist : dist (u n) x < ε := hN n hn
  by_cases hw' : w ∈ closedBall (0 : ℂ) 1
  · rw [toHol_apply x w hw', toHol_apply (u n) w hw', dist_eq_norm]
    calc ‖x ⟨w, hw'⟩ - u n ⟨w, hw'⟩‖ = ‖(u n - x) ⟨w, hw'⟩‖ := by
          rw [ContinuousMap.sub_apply, norm_sub_rev]
      _ ≤ ‖u n - x‖ := ContinuousMap.norm_coe_le_norm _ _
      _ = dist (u n) x := (dist_eq_norm (u n) x).symm
      _ < ε := hdist
  · rw [toHol_apply_of_not_mem x hw', toHol_apply_of_not_mem (u n) hw', dist_self]
    exact hε

/-- **Weierstrass theorem for the disc algebra.** The disc algebra is
sequentially closed in `C(closed unit disc)`: uniform limits of holomorphic
functions on the open disc are holomorphic
(`TendstoLocallyUniformlyOn.differentiableOn`). -/
theorem isSeqClosed_carrier :
    IsSeqClosed (discAlgebra : Set C(closedBall (0 : ℂ) 1, ℂ)) := by
  intro u p hu hx
  refine (mem_discAlgebra p).mpr ?_
  have hunif := tendstoUniformlyOn_toHol hx
  have hunifBall : TendstoUniformlyOn (fun n => toHol (u n)) (toHol p) atTop (ball (0 : ℂ) 1) :=
    hunif.mono fun w hw => mem_closedBall.mpr hw.le
  exact TendstoLocallyUniformlyOn.differentiableOn hunifBall.tendstoLocallyUniformlyOn
    (Eventually.of_forall fun n => (mem_discAlgebra (u n)).mp (hu n)) isOpen_ball

/-- The disc algebra is closed in `C(closed unit disc)`. -/
theorem isClosed_carrier : IsClosed (discAlgebra : Set C(closedBall (0 : ℂ) 1, ℂ)) :=
  isSeqClosed_iff_isClosed.mp isSeqClosed_carrier

/-- **The disc algebra is a Banach space.** -/
instance discAlgebra_complete : CompleteSpace discAlgebra := by
  rw [completeSpace_iff_isComplete_univ, Subtype.isComplete_iff]
  have himg : ((↑) '' (univ : Set discAlgebra)) =
      (discAlgebra : Set C(closedBall (0 : ℂ) 1, ℂ)) := by
    ext y
    constructor
    · rintro ⟨y', -, rfl⟩
      exact SetLike.mem_coe.mpr y'.2
    · intro hy
      exact ⟨⟨y, hy⟩, mem_univ _, rfl⟩
  rw [himg]
  exact isClosed_carrier.isComplete

/-- Evaluation at an interior point is a continuous linear functional on the
disc algebra. -/
def discAlgebraEval (z : ball (0 : ℂ) 1) : discAlgebra →L[ℂ] ℂ :=
  (ContinuousMap.evalCLM ℂ ⟨z.val, mem_closedBall.mpr z.2.le⟩).comp
    (Submodule.subtypeL discAlgebra.toSubmodule)

theorem discAlgebraEval_apply (z : ball (0 : ℂ) 1) (f : discAlgebra) :
    discAlgebraEval z f = f.val ⟨z.val, mem_closedBall.mpr z.2.le⟩ := rfl

theorem norm_discAlgebraEval_le (z : ball (0 : ℂ) 1) : ‖discAlgebraEval z‖ ≤ 1 := by
  refine ContinuousLinearMap.opNorm_le_bound _ zero_le_one fun f => ?_
  rw [discAlgebraEval_apply, one_mul]
  refine le_trans (ContinuousMap.norm_coe_le_norm _ _) ?_
  exact le_refl _

end

end Riemann
