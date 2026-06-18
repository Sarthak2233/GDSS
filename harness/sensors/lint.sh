#!/usr/bin/env bash
# GDSS harness Layer 1 sensor: lint with ruff.
# Degrades gracefully (skip, not fail) when ruff is not installed, so the gate
# is adoptable out-of-the-box. Install ruff to make this a hard gate.
set -uo pipefail

if ! command -v ruff >/dev/null 2>&1; then
  echo "lint: SKIP (ruff not installed)."
  echo "  WHY: ruff is the lint sensor; without it style/quality is unchecked."
  echo "  FIX: pip install ruff   (then re-run to enforce gdss/, tests/, harness/)."
  exit 0
fi

echo "lint: running ruff..."
if ruff check .; then
  echo "lint: OK"
  exit 0
fi

echo "lint: FAIL"
echo "  WHY: code violates project style/quality rules (ruff.toml)."
echo "  FIX: address the issues above; 'ruff check --fix .' handles autofixable ones."
exit 1
