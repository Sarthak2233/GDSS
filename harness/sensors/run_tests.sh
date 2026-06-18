#!/usr/bin/env bash
# GDSS harness Layer 2 sensor: runtime verification with pytest.
set -uo pipefail

if ! command -v pytest >/dev/null 2>&1 && ! python3 -c "import pytest" >/dev/null 2>&1; then
  echo "tests: FAIL (pytest not installed)."
  echo "  WHY: the runtime layer cannot run without pytest; behavior is unverified."
  echo "  FIX: pip install pytest   (or run: bash harness/init.sh)."
  exit 1
fi

echo "tests: running pytest..."
if python3 -m pytest -q; then
  echo "tests: OK"
  exit 0
fi

echo "tests: FAIL"
echo "  WHY: one or more behaviors are broken (assertions above)."
echo "  FIX: fix the behavior, not the test, unless the test encoded the wrong expectation."
exit 1
