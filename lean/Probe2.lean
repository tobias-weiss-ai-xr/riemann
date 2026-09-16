import Riemann.MayerHalf.CompactSummand
import Mathlib.Topology.ContinuousMap.Bounded.ArzelaAscoli
import Mathlib.Topology.MetricSpace.Isometry
open BoundedContinuousFunction
open Complex Riemann

set_option maxHeartbeats 1000000

noncomputable lemma test_hIsom :
    Isometry (fun f : C(↥halfDisc, ℂ) => mkOfCompact f) := by
  refine Isometry.of_dist_eq ?_
  intro a b
  rw [dist_eq_norm, dist_eq_norm]
  calc
    ‖mkOfCompact a - mkOfCompact b‖ = ‖mkOfCompact (a - b)‖ := by rw [← mkOfCompact_sub]
    _ = ‖a - b‖ := rfl

noncomputable lemma test_hfg : ∀ f : C(↥halfDisc, ℂ), BoundedContinuousFunction.toContinuousMap (mkOfCompact f) = f := by
  intro f; ext z; rfl

example : True := by trivial
