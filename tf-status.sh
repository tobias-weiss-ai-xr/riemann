#!/usr/bin/env bash
# tf-status.sh — quick taskfleet status for the riemann RH pipeline
TF=/home/weiss/git/taskfleet
RIEMANN=/home/weiss/git/riemann
echo "== orchestrator: $(pgrep -fc 'bash ./orchestrator.sh' || echo 0) proc(s)"
echo "== tasks:"
jq -r 'to_entries[] | "  \(.key): \(.value.status // "?") (attempts \(.value.attempts // 0))"' \
  "$RIEMANN/.tf-state/task-status.json" 2>/dev/null
echo "== last log lines:"
tail -5 "$RIEMANN/.tf-state/orchestrator.log" 2>/dev/null
echo "== worktree changes:"
for t in RH-1 RH-2 RH-3 RH-4 RH-5; do
  n=$(git -C "$RIEMANN/.tf-worktrees/$t" status --porcelain 2>/dev/null | wc -l)
  echo "  $t: $n changed"
done
echo "== gate hosts (elan ready?):"
for h in mac tobi-yoga contextual-intelligence.org chemie-lernen.org tobias-weiss.org; do
  timeout 8 ssh -o BatchMode=yes -o ConnectTimeout=5 "$h" \
    "test -x \$HOME/.elan/bin/lake && echo \"  $h: lake OK\" || echo \"  $h: NO lake\"" 2>/dev/null \
    | grep -E "OK|NO" || echo "  $h: unreachable"
done
