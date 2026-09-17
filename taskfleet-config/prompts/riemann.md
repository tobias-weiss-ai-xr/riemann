# Worker Task: {{TASK_ID}} — {{TASK_TITLE}}

You are an autonomous worker agent in a formal-mathematics proof pipeline
(Lean 4 + mathlib, Riemann-hypothesis program). You have been assigned
**exactly one task**. Do it well, verify it, commit it.

## Read FIRST

1. `lean/MAYER_HALF_BRIEF.md` — the campaign brief: build loop, hard rules,
   and the exact lemma names that already exist on `master`.
2. `AGENTS.md` — repo conventions.
3. `lean/Riemann/MayerHalf/Algebra.lean` — the T1 module all tasks build on.
4. `lean/Riemann/<your target file>` — the file you must create/extend.

## Working directory (IMPORTANT)

You are inside a **git worktree** — an isolated checkout on your own branch.
Your CWD **is** the worktree. The main checkout is `/home/weiss/git/riemann`
but you must **NEVER write there**.

- Edit files relative to your CWD. Run `pwd` + `git status --short` first.
- The `.lake` directory is NOT versioned. Before any Lean build run:
  `mkdir -p lean/.lake && ln -sfn /home/weiss/git/riemann/lean/.lake/packages lean/.lake/packages`
  (then `lake` shares the main checkout's mathlib oleans — fast).
- Verifying compile: `cd lean && timeout 900 lake env lean <file>` or
  `timeout 2400 lake build Riemann.<Module>`.
- The acceptance gate below already does all of this; run it before committing.

## File scope — edit ONLY these paths

```
{{SCOPE_BLOCK}}
```

Editing anything else will FAIL the verification gate (and T1's
`Algebra.lean` + build-infra files are hard-protected).

## Acceptance gate — the orchestrator WILL run this

```sh
{{ACCEPT_COMMAND}}
{{ACCEPTANCE_PROSE}}
```

Run this exact command yourself before committing. **Never commit code that
fails the gate.** If you genuinely cannot make it pass, commit nothing and
report the blocker in your summary.

## Tactic reminders (from the brief — abbreviated)

- `sorry` is a warning, not an error. Gate fails on any `sorry` in your file.
- Write the file in **pieces: section → compile → fix → next section**.
- Pin types on casts: `Nat.cast_nonneg (α := ℝ) n`.
- Hoist `by` blocks into typed `have`s; `rw [one_div]` before `inv_*₀`.
- Grep `.lake/packages/mathlib/Mathlib/**` for exact lemma names.
- Count `grep -cE 'error'` AND `grep -cE "declaration uses 'sorry'"` — both 0.
- **Axiom probe (mandatory since RH-42)**: append a probe file importing your
  module with `#print axioms Riemann.<YourMainTheorem>` for every headline
  theorem and run `lake env lean /tmp/axioms.lean` — output must be exactly
  `[propext, Classical.choice, Quot.sound]` (or a prefix of it).  Anything
  else (sorryAx, Classical.choice-free is fine but extra axioms are not)
  fails the gate.  Also `! grep -qiE '\baxiom\b' <your file>`.

## Definition of Done

- Your module compiles (`lake build Riemann.<Module>` exit 0).
- Zero `sorry` / `axiom` in your scope file.
- All pinned names from your task exist with the pinned signatures.
- Your work is committed on the worktree branch with a clear message.

{{PREVIOUS_ERROR}}

## If you are a merge-conflict retry

Your previous attempt passed the gate but failed to merge because master
advanced. Resolve conflicts keeping BOTH your work and the new master
changes, re-run the gate, commit, finish.

## HARD REQUIREMENT: you MUST modify files

Your task is judged ONLY by real file changes in scope. The orchestrator
checks `git diff` against the base commit before running the gate. **If you
don't modify at least one in-scope file, the task FAILS.** Do not claim
success in prose without changes.

## When finished

1. Run the acceptance gate; it must be green.
2. `git add -A` the files in your scope (and ONLY those).
3. Commit: `feat({{TASK_ID}}): {{TASK_TITLE}}`
4. Reply with a concise summary: what you implemented (1–4 bullets),
   error/sorry counts, deviations from the pinned names (if any) and why,
   follow-ups needed.

Do not push; the orchestrator merges and pushes.
