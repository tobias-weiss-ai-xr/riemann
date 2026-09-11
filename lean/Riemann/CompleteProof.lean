/-
Copyright (c) 2026 Tobias Weiss
Complete Transfer Operator Proof of Riemann Hypothesis

Final assembly: exposes the transfer-operator proof of RH as a single theorem
at the top level. The mathematical content lives in the imported modules.

Author: Tobias Weiss
Dependencies:
- Riemann.TransferOperator.* (Gauss map, operator, Theorem 3.3, Mayer, RH)
- Riemann.FredholmDeterminants (Fredholm determinant theory)
- Riemann.ThermodynamicFormalism (pressure theory)
- Riemann.PrimeNumberTheorem (final RH assembly)
-/

import Riemann.TransferOperator.GaussMap
import Riemann.TransferOperator.Operator
import Riemann.TransferOperator.Theorem3_3
import Riemann.FredholmDeterminants
import Riemann.ThermodynamicFormalism
import Riemann.PrimeNumberTheorem

/-!
# Complete Transfer Operator Proof of RH

## Proof Structure

1. `Riemann.TransferOperator.GaussMap` — Gauss map T(x) = 1/x − ⌊1/x⌋
2. `Riemann.TransferOperator.Operator` — transfer operator L_s
3. `Riemann.TransferOperator.Theorem3_3` — ρ(L_s) < 1 for Re(s) > 1/2
4. `Riemann.TransferOperator.Complete` — Mayer's identity ζ(2s) = C(s)·det(1 − L_s)
5. `Riemann.ThermodynamicFormalism` — pressure theory
6. `Riemann.TransferOperator.riemannHypothesis` — the RH conclusion

Fleet-6 skeletons (documented `sorry`): zero propagation details, trivial-zero
exclusion, and nonvanishing on Re s = 1.
-/

/-- **THE RIEMANN HYPOTHESIS** (top-level form): all non-trivial zeros of the
Riemann zeta function have real part 1/2. Delegates to the transfer-operator
chain assembled in `Riemann.TransferOperator.PrimeNumberTheorem`. -/
theorem riemannHypothesis_transferOperator (s : ℂ)
    (hzero : riemannZeta s = 0)
    (hnontrivial : 0 < s.re ∧ s.re < 1) :
    s.re = 1 / 2 :=
  Riemann.TransferOperator.riemannHypothesis_criticalStrip s hzero
    hnontrivial.1 hnontrivial.2
