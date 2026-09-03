#!/usr/bin/env bash
# Run all frontend tests for the riemann visualization site.
#   1/2  tests/data_check.mjs     — pure Node data integrity (fast, no browser)
#   2/2  tools/headless_check.mjs — headless Chrome render + interaction suite
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0

echo "── 1/2  data integrity ──────────────────────────"
if node tests/data_check.mjs; then
  echo
else
  fail=1
fi

echo "── 2/2  headless render ─────────────────────────"
if node tools/headless_check.mjs; then
  echo
else
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "✓ ALL TEST SUITES PASSED"
else
  echo "✗ TEST FAILURES — see above"
fi
exit "$fail"
