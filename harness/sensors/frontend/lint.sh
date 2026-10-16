#!/usr/bin/env bash
# GDSS frontend harness Layer F1 sensor: eslint (+ eslint-plugin-jsx-a11y).
# Degrades gracefully (skip, not fail) when pnpm/node are absent, mirroring the
# backend harness/sensors/lint.sh pattern. Install deps to make this a hard gate.
set -uo pipefail

web_dir="$(cd "$(dirname "$0")/../../.." && pwd)/web"

if ! command -v pnpm >/dev/null 2>&1 && ! command -v npm >/dev/null 2>&1; then
  echo "frontend/lint: SKIP (no pnpm/npm found)."
  echo "  WHY: eslint is the frontend lint sensor; without a JS toolchain style/a11y is unchecked."
  echo "  FIX: install Node + pnpm (npm i -g pnpm), then 'cd web && pnpm install'."
  exit 0
fi

if [[ ! -d "$web_dir/node_modules" ]]; then
  echo "frontend/lint: SKIP (web/node_modules missing)."
  echo "  WHY: eslint deps are not installed, so the lint sensor cannot run."
  echo "  FIX: cd web && pnpm install   (then re-run to enforce)."
  exit 0
fi

cd "$web_dir" || exit 1
pm="pnpm"; command -v pnpm >/dev/null 2>&1 || pm="npm"

echo "frontend/lint: running eslint (+ jsx-a11y)..."
if $pm run lint; then
  echo "frontend/lint: OK"
  exit 0
fi

echo "frontend/lint: FAIL"
echo "  WHY: code violates eslint rules (incl. jsx-a11y accessibility rules)."
echo "  FIX: address the issues above; 'cd web && $pm run lint -- --fix' for autofixable ones."
exit 1
