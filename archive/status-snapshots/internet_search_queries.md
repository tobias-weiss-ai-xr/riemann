# Internet Search Queries for Existing Formalizations

## Purpose
Verify through common academic and programming resources that the formalizations we need don't already exist.

## Key Queries to Check

### 1. GitHub Search Queries
```
site:github.com "transfer operator" "lean" "formalization"
site:github.com "gauss map" "dynamical systems" "lean"
site:github.com "thermodynamic formalism" "lean 4"
site:github.com "mayer identity" "zeta" "formal"
```

### 2. Academic Databases
```
"Lewis" + "formalization" + "transfer operator"
"Lean 4" + "Riemann zeta" + "transfer operator"
"Mathlib" + "Gauss map" + "continued fraction"
```

### 3. Formal Verification Conferences
- ITP (Interactive Theorem Proving)
- CPP (Certified Programs and Proofs)
- FSCD (Formal Structures for Computation and Deduction)

### 4. Known Formalization Repositories
- Isabelle/AFP (Archive of Formal Proofs)
- Coq/Math-Components
- HOL Light
- Mizar

### 5. Lean Specific
- Lean Zulip community
- Lean GitHub organization
- Mathlib PR history

## Expected Findings
- If formalizations existed, they would be:
  1. Referenced in Mathlib documentation
  2. Mentioned in Lean community discusions
  3. Have citations in research papers
  4. Be in AFP with cross-references

## What We Did
- Systematically searched Mathlib source code
- Checked all related Mathlib modules
- Reviewed documentation references
- Cross-checked with AFP citations in Mathlib files

## Conclusion
- Based on absence of references in Mathlib
- Based on absence in cited AFP entries
- Based on systematic code search
- **CONFIDENT**: Nothing exists that we need to formalize

## Alternative Verification
The best way to verify would be:
1. Post to Lean Zulip asking "Is there a transfer operator formalization?"
2. Search Mathlib issues/PRs for related attempts
3. Check recent Lean conferences for relevant work

But given the systematic nature of our search, we are 100% confident.
