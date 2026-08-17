import Lake
open Lake DSL

package «Riemann» where
  version := v!"0.1.0"
  description := "Formalization of the Riemann hypothesis via transfer operators"

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git"

-- Use local mathlib fork for development (commented out for now)
-- require mathlib from "../path/to/local/mathlib4"

lean_lib «Riemann» where
  -- Only include core files that compile
  roots := #[`Riemann]

@[default_target]
lean_exe «riemann» where
  root := `Main
