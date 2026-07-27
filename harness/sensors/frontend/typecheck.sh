#!/usr/bin/env bash
# GDSS frontend harness Layer F1 sensor: TypeScript type checking (tsc --noEmit).
# Degrades gracefully (skip, not fail) when pnpm/node are absent.
set -uo pipefail

web_dir="$(cd "$(dirname "$0")/../../.." && pwd)/web"

if ! command -v pnpm >/dev/null 2>&1 && ! command -v npm >/dev/null 2>&1; then
  echo "frontend/typecheck: SKIP (no pnpm/npm found)."
  echo "  WHY: tsc is the frontend type sensor; without a JS toolchain types are unchecked."
  echo "  FIX: install Node + pnpm, then 'cd web && pnpm install'."
  exit 0
fi

if [[ ! -d "$web_dir/node_modules" ]]; then
  echo "frontend/typecheck: SKIP (web/node_modules missing)."
  echo "  WHY: typescript is not installed, so the type sensor cannot run."
  echo "  FIX: cd web && pnpm install   (then re-run to enforce)."
  exit 0
fi

cd "$web_dir" || exit 1
pm="pnpm"; command -v pnpm >/dev/null 2>&1 || pm="npm"

echo "frontend/typecheck: running tsc --noEmit..."
if $pm run typecheck; then
  echo "frontend/typecheck: OK"
  exit 0
fi

echo "frontend/typecheck: FAIL"
echo "  WHY: TypeScript type errors in web/."
echo "  FIX: resolve the type errors above before considering the work done."
exit 1
