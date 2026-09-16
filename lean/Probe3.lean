import Riemann.MayerHalf.CompactSummand
import Mathlib.Topology.ContinuousMap.Bounded.ArzelaAscoli
import Mathlib.Topology.MetricSpace.Isometry
open BoundedContinuousFunction
open Complex Riemann

set_option maxHeartbeats 2000000

noncomputable lemma test_hA (n : ℕ) (hn : 0 < n) :
    IsCompact (closure ((fun f : C(↥halfDisc, ℂ) => mkOfCompact f) '' ((transferSummandCLM n) '' Metric.closedBall 0 1))) := by
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
    exact (BoundedContinuousFunction.norm_coe_le_norm _ x).trans hnT
  · -- H : Equicontinuous (fun x => ⇑(↑x)) on A
    -- EquicontinuousAt at each z₀, reindex from equicontinuous_transferSummand
    intro z₀
    rw [Metric.equicontinuousAt_iff_right]
    intro ε ε0
    have hz : EquicontinuousAt (fun (f : {g : halfDiscAlgebra // ‖g‖ ≤ 1}) (z : ↥halfDisc) =>
        (transferSummandCLM n f.1) z) z₀ := equicontinuous_transferSummand n hn z₀
    rw [Metric.equicontinuousAt_iff_right] at hz
    rcases hz ε ε0 with ⟨U, hU, hUbdd⟩
    refine ⟨U, hU, ?_⟩
    intro a z hzU
    rcases a.property with ⟨h, hh, hM⟩
    rcases hh with ⟨f, hf1, rfl⟩
    have hpoint : a.1 z = (transferSummandCLM n f) z := by
      rw [← hM]
      rfl
    have hpoint0 : a.1 z₀ = (transferSummandCLM n f) z₀ := by
      rw [← hM]
      rfl
    have hb := hUbdd z hzU ⟨f, (by simpa using hf1)⟩
    simpa [hpoint, hpoint0] using hb
