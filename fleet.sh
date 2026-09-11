#!/usr/bin/env bash
# fleet.sh — distribute Riemann Lean build/verify jobs across the fleet.
#
# Usage:
#   ./fleet.sh pull            # git pull on all workers
#   ./fleet.sh verify          # full lake build on all workers (independent checks)
#   ./fleet.sh build <module>  # lake build <module> on all workers
#   ./fleet.sh status          # show background build progress on each host
#   ./fleet.sh tally           # summary of last verify results
#
# Hosts: legion (local) + ai1 + ai2 + v77986.1blu.de
# Keys: ~/.ssh/id_ed25519_ansible (VPN)

set -u
cd "$(dirname "$0")/.."

WORKERS="ai1 ai2 v77986.1blu.de"
LEAN_DIR="git/riemann/lean"
RESULTS_DIR="/tmp/riemann-fleet"
mkdir -p "$RESULTS_DIR"

rsh() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$1" "$2" 2>/dev/null
}

run_remote() {
  local h="$1" cmd="$2"
  rsh "$h" "export PATH=\$HOME/.elan/bin:\$PATH; cd \$HOME/$LEAN_DIR && $cmd" &
}

case "${1:-}" in
  pull)
    for h in $WORKERS; do
      run_remote "$h" "cd \$HOME/git/riemann && git pull origin master 2>&1 | tail -1" &
    done
    wait
    ;;
  verify)
    echo ">>> Dispatching independent lake build to: $WORKERS (legion runs locally)"
    # Local legion build
    ( cd "$(dirname "$0")/../lean" && export PATH="$HOME/.elan/bin:$PATH" && \
      lake build > "$RESULTS_DIR/legion.log" 2>&1; \
      echo "exit=$? ARCH=x86_64 HOST=legion $(date -u +%H:%M)" > "$RESULTS_DIR/legion.result" ) &
    # Remote workers
    for h in $WORKERS; do
      ( rsh "$h" "export PATH=\$HOME/.elan/bin:\$PATH; cd \$HOME/git/riemann/lean && \
          lake build > /tmp/fleet-verify.log 2>&1; \
          echo \"exit=\$? HOST=$h \$(date -u +%H:%M)\" " > "$RESULTS_DIR/$h.result" ) &
    done
    wait
    echo ">>> done. Results:"
    cat "$RESULTS_DIR"/*.result 2>/dev/null
    ;;
  build)
    # ./fleet.sh build Riemann.TransferOperator.Operator
    local mod="${2:?usage: fleet.sh build <module>}"
    echo ">>> lake build $mod on legion + workers"
    ( cd "$(dirname "$0")/../lean" && export PATH="$HOME/.elan/bin:$PATH" && lake build "$mod" 2>&1 | tail -3 ) &
    for h in $WORKERS; do
      ( rsh "$h" "export PATH=\$HOME/.elan/bin:\$PATH; cd \$HOME/git/riemann/lean && \
          lake build $mod 2>&1 | tail -3" ) &
    done
    wait
    ;;
  status)
    for h in ai1 ai2 v77986.1blu.de; do
      echo "=== $h ==="
      rsh "$h" "tail -3 /tmp/lu.log 2>/dev/null || echo '(no log — idle)'"
    done
    ;;
  tally)
    for f in "$RESULTS_DIR"/*.result; do
      [ -f "$f" ] && echo "$(basename "$f"): $(cat "$f")"
    done
    ;;
  *)
    echo "usage: $0 {pull|verify|build <module>|status|tally}"
    ;;
esac
