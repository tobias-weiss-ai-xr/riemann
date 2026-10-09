/-
Copyright (c) 2026 Tobias Weiss
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Tobias Weiss
-/
import Mathlib.NumberTheory.LSeries.Dirichlet

/-!
# The 3-4-1 lemma — first brick of the de la Vallée Poussin zero-free region

For `σ > 1` and `t ∈ ℝ` the classical trigonometric inequality
`3 + 4 cos θ + cos 2θ = 2 (1 + cos θ)² ≥ 0`, applied termwise to the von
Mangoldt Dirichlet series `Σ Λ(n) n⁻ˢ` (absolutely convergent on `Re s > 1`),
gives

    3 · Re Λ(σ) + 4 · Re Λ(σ + it) + Re Λ(σ + 2it)
      = 2 · Σₙ Λ(n) n⁻σ (1 + cos (t log n))²  ≥  0.

Via mathlib's `LSeries_vonMangoldt_eq_deriv_riemannZeta_div` this reads
`−3 Re (ζ'/ζ)(σ) − 4 Re (ζ'/ζ)(σ+it) − Re (ζ'/ζ)(σ+2it) ≥ 0`, the seed
inequality of every proof of a zero-free region for ζ.  The continuation
towards the zero-free region itself is **not** formalized here; see
`research/MATHLIB_GAPS.md` for the gap analysis.

## References

* Titchmarsh, *The Theory of the Riemann Zeta-Function*, §3.5 (3-4-1 lemma)
* Montgomery–Vaughan, *Multiplicative Number Theory I*, Ch. 6
* Platt–Trudgian, *The zero-free region of the Riemann zeta-function* (2021)
-/

open Real
open scoped LSeries.notation ArithmeticFunction.vonMangoldt
open Complex (I)

set_option maxHeartbeats 1000000

namespace Riemann

/-! ### Termwise real-part lemmas -/

/-- The von Mangoldt term at a complex point `σ + it`: its real part is
`Λ(n) · n⁻σ · cos (t log n)`. -/
private lemma re_vonMangoldt_term (n : ℕ) (hn : 1 ≤ n) (σ t : ℝ) :
    ((↗Λ n : ℂ) / (n:ℂ) ^ ((σ:ℂ) + (t:ℂ)*I)).re
        = Λ n * (n:ℝ) ^ (-σ) * cos (t * log n) := by
  have hpos : (0:ℝ) < n := by positivity
  have hn0 : (n:ℂ) ≠ 0 := by
    exact_mod_cast (show n ≠ 0 by omega)
  have hΛ : (↗Λ n : ℂ) = ((Λ n : ℝ) : ℂ) := rfl
  have hlog : Complex.log (n:ℂ) = ((Real.log n : ℝ) : ℂ) := (Complex.ofReal_log hpos.le).symm
  have hrpow : (n:ℝ) ^ (-σ) = Real.exp ((-σ) * Real.log n) := by
    rw [Real.rpow_def_of_nonneg hpos.le, if_neg (by positivity : (n:ℝ) ≠ 0),
      mul_comm (Real.log n) (-σ)]
  have harg : ((Real.log n : ℝ) : ℂ) * (-((σ:ℂ) + (t:ℂ)*I))
      = (((-σ * Real.log n : ℝ) : ℂ)) + (((-(t * Real.log n) : ℝ) : ℂ)) * I := by
    refine Complex.ext ?_ ?_
    · simp only [Complex.mul_re, Complex.neg_re, Complex.neg_im, Complex.add_re,
        Complex.add_im, Complex.ofReal_re, Complex.ofReal_im, Complex.I_re,
        Complex.I_im, mul_zero, sub_zero, add_zero, zero_mul, neg_zero]
      ring
    · simp only [Complex.mul_im, Complex.neg_re, Complex.neg_im, Complex.add_re,
        Complex.add_im, Complex.ofReal_re, Complex.ofReal_im, Complex.I_re,
        Complex.I_im, mul_zero, sub_zero, add_zero, zero_mul, neg_zero]
      ring
  have hinv : ((n:ℂ) ^ ((σ:ℂ) + (t:ℂ)*I))⁻¹ = (n:ℂ) ^ (-((σ:ℂ) + (t:ℂ)*I)) := by
    rw [Complex.cpow_def_of_ne_zero hn0, Complex.cpow_def_of_ne_zero hn0, mul_neg,
      Complex.exp_neg]
  rw [div_eq_inv_mul, hΛ, hinv, Complex.cpow_def_of_ne_zero hn0, hlog, harg,
    Complex.exp_add_mul_I, ← Complex.ofReal_exp, ← Complex.ofReal_cos,
    ← Complex.ofReal_sin, Real.cos_neg, Real.sin_neg]
  simp only [Complex.mul_re, Complex.mul_im, Complex.add_re, Complex.add_im,
    Complex.ofReal_re, Complex.ofReal_im, Complex.I_re, Complex.I_im,
    mul_zero, sub_zero, add_zero, zero_mul]
  rw [hrpow]
  ring

/-- The coefficient `Λ(n) · n⁻σ` is summable for `σ > 1` — extracted from the
absolute convergence of the von Mangoldt `L`-series on the real axis. -/
private lemma summable_vonMangoldt_coeff (σ : ℝ) (hσ : 1 < σ) :
    Summable fun n : ℕ => Λ n * (n:ℝ) ^ (-σ) := by
  have h := ArithmeticFunction.LSeriesSummable_vonMangoldt (s := (σ:ℂ)) hσ
  have hnorm : ∀ n : ℕ, ‖LSeries.term ↗Λ (σ:ℂ) n‖ = |Λ n * (n:ℝ) ^ (-σ)| := by
    intro n
    rw [LSeries.norm_term_eq]
    by_cases h0 : n = 0
    · subst h0
      simp [ArithmeticFunction.vonMangoldt_apply]
    · have hpos : (0:ℝ) < n := by positivity
      rw [if_neg h0]
      norm_num
      rw [abs_of_nonneg ArithmeticFunction.vonMangoldt_nonneg,
        abs_of_nonneg (Real.rpow_nonneg (by positivity) (-σ)), div_eq_inv_mul,
        Real.rpow_neg hpos.le]
      ring
  exact (h.norm.congr hnorm).of_abs

/-- Nonnegative coefficients times a bounded factor stay summable. -/
private lemma summable_mul_bounded {c : ℕ → ℝ} (hc : Summable c)
    (hnn : ∀ n, 0 ≤ c n) (f : ℕ → ℝ) (hf : ∀ n, |f n| ≤ 1) :
    Summable fun n : ℕ => c n * f n := by
  have habs : Summable fun n : ℕ => |c n * f n| :=
    hc.of_nonneg_of_le (fun n => by positivity) fun n => by
      rw [abs_mul, abs_of_nonneg (hnn n)]
      simpa using mul_le_mul_of_nonneg_left (hf n) (hnn n)
  exact habs.of_abs

/-! ### The 3-4-1 lemma -/

/-- Real part of the von Mangoldt `L`-series as an explicit trigonometric
Dirichlet series. -/
private lemma lseries_re_eq (σ t : ℝ) (hσ : 1 < σ) :
    (LSeries ↗Λ ((σ:ℂ) + (t:ℂ)*I)).re
        = ∑' n : ℕ, Λ n * (n:ℝ) ^ (-σ) * cos (t * log n) := by
  have hw1 : 1 < (((σ:ℂ) + (t:ℂ)*I : ℂ)).re := by simpa using hσ
  have hw : (((σ:ℂ) + (t:ℂ)*I : ℂ)) ≠ 0 := by
    intro hc
    rw [hc] at hw1
    norm_num at hw1
  have hdef : LSeries ↗Λ ((σ:ℂ) + (t:ℂ)*I)
      = ∑' n : ℕ, LSeries.term ↗Λ ((σ:ℂ) + (t:ℂ)*I) n := rfl
  rw [hdef]
  show Complex.reCLM (∑' n : ℕ, LSeries.term ↗Λ ((σ:ℂ) + (t:ℂ)*I) n) = _
  rw [Complex.reCLM.map_tsum (ArithmeticFunction.LSeriesSummable_vonMangoldt hw1)]
  refine tsum_congr fun n => ?_
  rcases Nat.eq_zero_or_pos n with rfl | hn
  · rw [LSeries.term_of_ne_zero' hw]
    have hΛ0 : ((Λ 0 : ℝ) : ℂ) = 0 := by simp
    rw [hΛ0, Nat.cast_zero, Complex.zero_cpow hw, div_zero]
    simp [Real.log_zero, Real.zero_rpow (by linarith : σ ≠ 0)]
  · rw [LSeries.term_of_ne_zero' hw]
    exact re_vonMangoldt_term n (by omega : 1 ≤ n) σ t

/-- **The 3-4-1 lemma.**  For `σ > 1` and `t ∈ ℝ`,

    3 · Re Λ(σ) + 4 · Re Λ(σ + it) + Re Λ(σ + 2it) ≥ 0,

where `Σ Λ(n) n⁻ʷ` is the von Mangoldt Dirichlet series
(`= −ζ'(w)/ζ(w)` for `Re w > 1`, mathlib
`LSeries_vonMangoldt_eq_deriv_riemannZeta_div`).  This is the seed
inequality of the zero-free region; see the module header. -/
theorem threeFourOne (σ t : ℝ) (hσ : 1 < σ) :
    0 ≤ 3 * (LSeries ↗Λ ((σ:ℂ))).re
      + 4 * (LSeries ↗Λ ((σ:ℂ) + (t:ℂ)*I)).re
      + (LSeries ↗Λ ((σ:ℂ) + ((2*t : ℝ) : ℂ)*I)).re := by
  have hcs : Summable fun n : ℕ => Λ n * (n:ℝ) ^ (-σ) := summable_vonMangoldt_coeff σ hσ
  have hcnn : ∀ n : ℕ, 0 ≤ Λ n * (n:ℝ) ^ (-σ) := fun n =>
    mul_nonneg ArithmeticFunction.vonMangoldt_nonneg
      (Real.rpow_nonneg (by positivity) (-σ))
  have hw1 : 1 < (((σ:ℂ) + (t:ℂ)*I : ℂ)).re := by simpa using hσ
  have hw2 : 1 < (((σ:ℂ) + ((2*t : ℝ) : ℂ)*I : ℂ)).re := by simpa using hσ
  have r0 : (LSeries ↗Λ ((σ:ℂ))).re
      = ∑' n : ℕ, Λ n * (n:ℝ) ^ (-σ) * cos (0 * log n) := by
    have h0 : ((σ:ℂ) + (0:ℂ)*I) = (σ:ℂ) := by simp
    rw [← h0]
    exact lseries_re_eq σ 0 hσ
  rw [r0, lseries_re_eq σ t hσ, lseries_re_eq σ (2*t) hσ]
  -- pointwise trig identity: 3 + 4 cos θ + cos 2θ = 2 (1 + cos θ)²
  have htrig : ∀ n : ℕ,
      3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n))
        + 4 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (t * log n))
        + (Λ n * (n:ℝ) ^ (-σ)) * cos (2 * t * log n)
        = 2 * (Λ n * (n:ℝ) ^ (-σ)) * (1 + cos (t * log n)) ^ 2 := by
    intro n
    rw [zero_mul, Real.cos_zero, mul_assoc 2 t (log n), Real.cos_two_mul]
    ring
  -- summability of the three summand families
  have hA : Summable fun n : ℕ => 3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n)) := by
    have h3 : (fun n : ℕ => 3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n)))
        = fun n : ℕ => 3 * (Λ n * (n:ℝ) ^ (-σ)) := by
      funext n; rw [zero_mul, Real.cos_zero, mul_one]
    rw [h3]
    exact (summable_mul_left_iff (by norm_num : (3:ℝ) ≠ 0)).mpr hcs
  have hB : Summable fun n : ℕ => 4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n)) :=
    (summable_mul_left_iff (by norm_num : (4:ℝ) ≠ 0)).mpr
      (summable_mul_bounded hcs hcnn _ fun n => Real.abs_cos_le_one (t * log n))
  have hC : Summable fun n : ℕ => Λ n * (n:ℝ) ^ (-σ) * cos (2 * t * log n) :=
    summable_mul_bounded hcs hcnn _ fun n => Real.abs_cos_le_one (2 * t * log n)
  -- the combined summand is nonnegative
  have hGnn : ∀ n : ℕ, 0 ≤ 2 * (Λ n * (n:ℝ) ^ (-σ)) * (1 + cos (t * log n)) ^ 2 := fun n =>
    mul_nonneg (mul_nonneg (by norm_num) (hcnn n)) (sq_nonneg _)
  -- bundling: dominated by 8·cₙ, hence summable
  have hG : Summable fun n : ℕ => 2 * (Λ n * (n:ℝ) ^ (-σ)) * (1 + cos (t * log n)) ^ 2 := by
    have h4 : Summable fun n : ℕ => (8:ℝ) * (Λ n * (n:ℝ) ^ (-σ)) :=
      (summable_mul_left_iff (by norm_num : (8:ℝ) ≠ 0)).mpr hcs
    refine h4.of_nonneg_of_le hGnn fun n => ?_
    have hc1 := abs_le.mp (Real.abs_cos_le_one (t * log n))
    have h2 : (1 + cos (t * log n)) ^ 2 ≤ 4 := by
      nlinarith [hc1.1, hc1.2,
        mul_nonneg (sub_nonneg.mpr hc1.2) (sub_nonneg.mpr hc1.1)]
    nlinarith [h2, hcnn n]
  -- the combination
  have hAB : Summable fun n : ℕ =>
      3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n))
        + 4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n)) := hA.add hB
  have hABC : Summable fun n : ℕ =>
      (3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n))
        + 4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n)))
        + Λ n * (n:ℝ) ^ (-σ) * cos (2 * t * log n) := hAB.add hC
  have e2 : ∑' n : ℕ, (3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n))
      + 4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n)))
      = ∑' n : ℕ, (3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n)))
        + ∑' n : ℕ, (4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n))) :=
    (hA.hasSum.add hB.hasSum).tsum_eq
  have e3 : ∑' n : ℕ, ((3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n))
      + 4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n)))
      + Λ n * (n:ℝ) ^ (-σ) * cos (2 * t * log n))
      = ∑' n : ℕ, (3 * ((Λ n * (n:ℝ) ^ (-σ)) * cos (0 * log n))
        + 4 * (Λ n * (n:ℝ) ^ (-σ) * cos (t * log n)))
        + ∑' n : ℕ, (Λ n * (n:ℝ) ^ (-σ) * cos (2 * t * log n)) :=
    (hAB.hasSum.add hC.hasSum).tsum_eq
  rw [← tsum_mul_left (a := (3:ℝ)), ← tsum_mul_left (a := (4:ℝ)), ← e2, ← e3]
  · refine tsum_nonneg fun n => ?_
    rw [htrig n]
    exact hGnn n

end Riemann
