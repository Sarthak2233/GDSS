#!/usr/bin/env bash
# GDSS frontend harness Layer F2 sensor: component + accessibility tests
# (vitest + Testing Library + jest-axe). Degrades gracefully when deps absent.
set -uo pipefail

web_dir="$(cd "$(dirname "$0")/../../.." && pwd)/web"

if ! command -v pnpm >/dev/null 2>&1 && ! command -v npm >/dev/null 2>&1; then
  echo "frontend/component_tests: SKIP (no pnpm/npm found)."
  echo "  WHY: vitest is the frontend component/a11y sensor; without a JS toolchain behavior is unchecked."
  echo "  FIX: install Node + pnpm, then 'cd web && pnpm install'."
  exit 0
fi

if [[ ! -d "$web_dir/node_modules" ]]; then
  echo "frontend/component_tests: SKIP (web/node_modules missing)."
  echo "  WHY: vitest/jest-axe are not installed, so the component sensor cannot run."
  echo "  FIX: cd web && pnpm install   (then re-run to enforce)."
  exit 0
fi

cd "$web_dir" || exit 1
pm="pnpm"; command -v pnpm >/dev/null 2>&1 || pm="npm"

echo "frontend/component_tests: running vitest (+ jest-axe)..."
if $pm run test; then
  echo "frontend/component_tests: OK"
  exit 0
fi

echo "frontend/component_tests: FAIL"
echo "  WHY: component behavior or accessibility (jest-axe) tests failed."
echo "  FIX: address the failures above; assert behavior through public interfaces and add axe assertions."
exit 1
