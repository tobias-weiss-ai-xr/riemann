#!/usr/bin/env bash
# fleet-gate.sh — taskfleet acceptance gate: build a Lean module on a designated
# fleet host (mac / tobi-yoga / contextual-intelligence.org / chemie-lernen.org /
# tobias-weiss.org). Pushes the current worktree branch to the host, builds there.
#
# usage: fleet-gate.sh <module> <host> [file-with-no-sorry ...]
#   e.g. fleet-gate.sh Riemann.TransferOperator.Operator mac \
#          lean/Riemann/TransferOperator/Operator.lean
#
# Gate passes (exit 0) iff:
#   1. worktree has no uncommitted changes (agent must commit),
#   2. pushed branch builds on the host (lake build <module>),
#   3. total 'sorry' count across the listed files ≤ MAX_SORRY (default 0).
# Falls back to a local legion build (copy of lean/.lake) if the host is not ready.
set -u
set -o pipefail

MOD="${1:?usage: fleet-gate.sh <module> <host> [files...]}"
HOST="${2:?usage: fleet-gate.sh <module> <host> [files...]}"
MAX_SORRY="${MAX_SORRY:-0}"
shift 2
NOSORRY_FILES=("$@")

GATE_TIMEOUT="${GATE_TIMEOUT:-2400}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LEANDIR="$ROOT/lean"

echo "=== fleet-gate: module=$MOD host=$HOST"

# --- 1. worktree must be committed (auto-commit agent's uncommitted work) ---
if [ -n "$(git -C "$ROOT" status --porcelain)" ]; then
  echo "--- uncommitted changes present; auto-committing for the gate"
  git -C "$ROOT" add -A
  git -C "$ROOT" commit -q -m "gate: auto-commit uncommitted agent work" || true
fi

# --- 1b. branch must not touch build-infra files ----------------------------
INFRA=$(git -C "$ROOT" diff --name-only "master...HEAD" -- lean/lake-manifest.json lean/lean-toolchain lean/lakefile.lean 2>/dev/null)
if [ -n "$INFRA" ]; then
  echo "GATE-FAIL: branch modifies build-infra files (out of scope) — revert them: git checkout master -- $INFRA"
  exit 1
fi

# --- helper: sorry-count check on the committed tree -------------------------
check_nosorry() {
  local total=0 c f
  for f in "${NOSORRY_FILES[@]:-}"; do
    [ -f "$ROOT/$f" ] || continue
    c=$(grep -c "sorry" "$ROOT/$f" 2>/dev/null || true)
    total=$((total + c))
    [ "$c" -gt 0 ] && echo "--- $f: $c sorries remaining"
  done
  echo "--- total sorries: $total (max allowed: $MAX_SORRY)"
  [ "$total" -le "$MAX_SORRY" ]
}

# --- 2. remote build on the assigned host -----------------------------------
BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
BR="tf-gate-${BRANCH}-$(date +%s)"

if git -C "$ROOT" push --force -q "ssh://weiss@$HOST/home/weiss/git/riemann" \
     "$BRANCH:$BR" 2>/dev/null; then
  echo "--- pushed $BRANCH to $HOST as $BR; building remotely"
  ssh -o BatchMode=yes -o ConnectTimeout=10 "weiss@$HOST" "
    set -u
    cd ~/git/riemann/lean
    export PATH=\$HOME/.elan/bin:\$PATH
    git checkout -f $BR >/dev/null 2>&1
    timeout $GATE_TIMEOUT lake build $MOD > /tmp/tf-gate.log 2>&1
    rc=\$?
    tr '\r' '\n' < /tmp/tf-gate.log | grep -E '^(error|Build completed|error: build)' | head -20
    exit \$rc" 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    echo "--- remote build OK on $HOST"
  else
    echo "--- remote build FAILED on $HOST (rc=$rc); log: ~/git/riemann (host) /tmp/tf-gate.log"
  fi
else
  echo "--- push to $HOST failed; falling back to local legion build"
  # ponytail: fallback copies 6.5G .lake per gate — fine at fleet scale, revisit if
  # >2 concurrent local fallbacks (disk + IO). Upgrade: pre-seeded gate worktrees.
  git -C "$ROOT" worktree add -f /tmp/tf-gate-wt "$BRANCH" >/dev/null 2>&1
  rm -rf /tmp/tf-gate-wt/lean/.lake
  cp -r "$LEANDIR/.lake" /tmp/tf-gate-wt/lean/.lake
  ( cd /tmp/tf-gate-wt/lean && export PATH="$HOME/.elan/bin:$PATH" && \
    timeout "$GATE_TIMEOUT" lake build "$MOD" > /tmp/tf-gate.log 2>&1 )
  rc=$?
  tr '\r' '\n' < /tmp/tf-gate.log | grep -E '^(error|Build completed)' | head -20
  git -C "$ROOT" worktree remove --force /tmp/tf-gate-wt >/dev/null 2>&1
fi

# --- 3. sorry audit ----------------------------------------------------------
check_nosorry || rc=1

[ $rc -eq 0 ] && echo "=== GATE-PASS" || echo "=== GATE-FAIL"
exit $rc
