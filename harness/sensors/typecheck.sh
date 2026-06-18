#!/usr/bin/env bash
# GDSS harness Layer 1 sensor: static type check with mypy.
# Degrades gracefully (skip, not fail) when mypy is not installed.
set -uo pipefail

if ! command -v mypy >/dev/null 2>&1; then
  echo "typecheck: SKIP (mypy not installed)."
  echo "  WHY: mypy is the type sensor; without it type errors go undetected."
  echo "  FIX: pip install mypy   (config is in mypy.ini)."
  exit 0
fi

echo "typecheck: running mypy..."
if mypy --config-file mypy.ini; then
  echo "typecheck: OK"
  exit 0
fi

echo "typecheck: FAIL"
echo "  WHY: static type errors detected (see mypy.ini)."
echo "  FIX: correct the annotations/usages reported above; do not add blanket # type: ignore."
exit 1
