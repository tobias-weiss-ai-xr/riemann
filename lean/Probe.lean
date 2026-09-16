import Riemann.MayerHalf.CompactSummand
import Mathlib.Topology.MetricSpace.Isometry
import Mathlib.Topology.ContinuousMap.Bounded.ArzelaAscoli
open BoundedContinuousFunction
open Complex Riemann Topology

lemma isCompact_closure_of_bijective_isometry {X Y : Type*} [MetricSpace X] [MetricSpace Y]
    (f : X → Y) (hf : Isometry f) (g : Y → X)
    (hfg : ∀ x, g (f x) = x) (hgf : ∀ y, f (g y) = y) {s : Set X}
    (h : IsCompact (closure (f '' s))) : IsCompact (closure s) := by
  let e : Homeomorph X Y := ⟨⟨f, g, hfg, hgf⟩, hf.continuous, (hf.right_inv hgf).continuous⟩
  have hcl : f '' (closure s) = closure (f '' s) := e.image_closure s
  have hc : IsCompact (e '' closure s) := by
    change IsCompact (f '' closure s)
    rw [hcl]
    exact h
  convert hc.image e.symm.continuous using 1
  rw [← Set.image_comp]
  rw [show (e.symm ∘ e) = id by ext x; exact e.left_inv x]
  simpa

set_option maxHeartbeats 2000000 in
theorem isCompactOperator_transferSummandCLM (n : ℕ) (hn : 0 < n) :
    IsCompactOperator (transferSummandCLM n) := by
  have hA : IsCompact (closure
      ((fun f : C(↥halfDisc, ℂ) => mkOfCompact f) '' ((transferSummandCLM n) '' Metric.closedBall 0 1))) := by
    let s : Set ℂ := Metric.closedBall (0 : ℂ) (1 / ((n : ℝ) + 1) ^ 2)
    have hs : IsCompact s := isCompact_closedBall _ _
    refine BoundedContinuousFunction.arzela_ascoli s hs
        ((fun f : C(↥halfDisc, ℂ) => mkOfCompact f) '' ((transferSummandCLM n) '' Metric.closedBall 0 1)) ?_ ?_
    · intro g x hgA
      rcases hgA with ⟨h, hh, rfl⟩
      rcases hh with ⟨f, hf1, rfl⟩
      have hnT : ‖(mkOfCompact ((transferSummandCLM n) f) : ↥halfDisc →ᵇ ℂ)‖ ≤ 1 / ((n : ℝ) + 1) ^ 2 := by
        have hnT' : ‖(transferSummandCLM n) f‖ ≤ 1 / ((n : ℝ) + 1) ^ 2 := by
          calc
            ‖(transferSummandCLM n) f‖ ≤ ‖(f : C(↥halfDisc, ℂ))‖ / ((n : ℝ) + 1) ^ 2 := norm_transferSummandCLM_le n f
            _ ≤ 1 / ((n : ℝ) + 1) ^ 2 := by
              have h00 : 0 ≤ ((n : ℝ) + 1) ^ 2 := sq_nonneg _
              exact (div_le_div_of_nonneg_right (by simpa using hf1) h00)
        simpa using hnT'
      have hnorm : ‖(mkOfCompact ((transferSummandCLM n) f) x : ℂ)‖ ≤ 1 / ((n : ℝ) + 1) ^ 2 :=
        (BoundedContinuousFunction.norm_coe_le_norm (mkOfCompact ((transferSummandCLM n) f)) x).trans hnT
      simpa [s, mem_closedBall, dist_eq_norm, ← sub_eq_add_neg] using hnorm
    · intro z₀
      rw [Metric.equicontinuousAt_iff_right]
      intro ε ε0
      have hz : EquicontinuousAt (fun (f : {g : halfDiscAlgebra // ‖g‖ ≤ 1}) (z : ↥halfDisc) =>
          (transferSummandCLM n f.1) z) z₀ := equicontinuous_transferSummand n hn z₀
      rw [Metric.equicontinuousAt_iff_right] at hz
      have hz' := hz ε ε0
      filter_upwards [hz'] with x hx
      intro a
      rcases a.property with ⟨h, hh, hM⟩
      rcases hh with ⟨f, hf1, rfl⟩
      have hpoint : a.1 z₀ = (transferSummandCLM n f) z₀ := by
        rw [← hM]
        rfl
      have hpointx : a.1 x = (transferSummandCLM n f) x := by
        rw [← hM]
        rfl
      have hb := hx ⟨f, (by simpa using hf1)⟩
      simpa [hpoint, hpointx] using hb
  have hIsom : Isometry (fun f : C(↥halfDisc, ℂ) => mkOfCompact f) := by
    refine Isometry.of_dist_eq ?_
    intro a b
    rw [dist_eq_norm, dist_eq_norm]
    calc
      ‖mkOfCompact a - mkOfCompact b‖ = ‖mkOfCompact (a - b)‖ := by rw [← mkOfCompact_sub]
      _ = ‖a - b‖ := rfl
  have hfg : ∀ f : C(↥halfDisc, ℂ), BoundedContinuousFunction.toContinuousMap (mkOfCompact f) = f := by
    intro f; ext z; rfl
  have hgf : ∀ g : ↥halfDisc →ᵇ ℂ, mkOfCompact (BoundedContinuousFunction.toContinuousMap g) = g := by
    intro g; ext z; rfl
  have hS : IsCompact (closure ((transferSummandCLM n) '' Metric.closedBall 0 1)) :=
    isCompact_closure_of_bijective_isometry (fun f : C(↥halfDisc, ℂ) => mkOfCompact f) hIsom
      BoundedContinuousFunction.toContinuousMap hfg hgf hA
  exact (isCompactOperator_iff_isCompact_closure_image_closedBall
      (transferSummandCLM n) (by norm_num : 0 < (1 : ℝ))).2 (by simpa using hS)
