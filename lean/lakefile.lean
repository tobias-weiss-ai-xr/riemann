import Lake
open Lake DSL

package «Riemann» where
  version := v!"0.1.0"
  description := "Formalization of SL(2,F_p) Cayley graph spectral properties and connections to the Riemann hypothesis"

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git"

lean_lib «Riemann» where
  roots := #[`Riemann]

@[default_target]
lean_exe «riemann» where
  root := `Main
