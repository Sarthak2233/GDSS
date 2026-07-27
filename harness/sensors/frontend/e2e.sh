#!/usr/bin/env bash
# GDSS frontend harness Layer F3 sensor: end-to-end a11y + CLS + bundle budget.
# Optional and fully degrades gracefully:
#   - Playwright + axe-core: keyboard nav + a11y, and CLS ~ 0 (no layout shift).
#   - size-limit: bundle budget.
# Skips cleanly (exit 0) if browsers/deps are not installed, so the gate stays
# runnable on a Python-only machine. Install deps to make this a hard gate.
set -uo pipefail

web_dir="$(cd "$(dirname "$0")/../../.." && pwd)/web"

if ! command -v pnpm >/dev/null 2>&1 && ! command -v npm >/dev/null 2>&1; then
  echo "frontend/e2e: SKIP (no pnpm/npm found)."
  echo "  WHY: Playwright/size-limit are the frontend e2e sensors; without a JS toolchain they cannot run."
  echo "  FIX: install Node + pnpm, then 'cd web && pnpm install'."
  exit 0
fi

if [[ ! -d "$web_dir/node_modules" ]]; then
  echo "frontend/e2e: SKIP (web/node_modules missing)."
  echo "  WHY: e2e deps are not installed, so the e2e sensor cannot run."
  echo "  FIX: cd web && pnpm install   (then re-run to enforce)."
  exit 0
fi

cd "$web_dir" || exit 1
pm="pnpm"; command -v pnpm >/dev/null 2>&1 || pm="npm"
status=0

# --- Bundle budget (size-limit) ---
if $pm ls @size-limit/preset-app >/dev/null 2>&1 || $pm ls @size-limit/preset-size >/dev/null 2>&1; then
  echo "frontend/e2e: building Next.js app for size-limit..."
  if ! $pm run build; then
    echo "frontend/e2e: FAIL (build required for bundle budget)"
    echo "  WHY: size-limit measures .next chunks; next build failed so the budget cannot be checked."
    echo "  FIX: cd web && $pm run build   and resolve the build errors above."
    status=1
  else
    echo "frontend/e2e: running size-limit (bundle budget)..."
    if ! $pm run size; then
      echo "frontend/e2e: FAIL (bundle budget)"
      echo "  WHY: a route/component exceeded its size-limit budget (web/package.json size-limit / web/.size-limit.json)."
      echo "  FIX: code-split heavy views (Three.js/D3/R3F), tree-shake imports, or raise the budget with justification."
      status=1
    fi
  fi
else
  echo "frontend/e2e: SKIP size-limit (not installed)."
  echo "  WHY: bundle budget sensor not installed."
  echo "  FIX: cd web && $pm add -D @size-limit/preset-app size-limit   to enforce bundle budgets."
fi

# --- Playwright (a11y + CLS) ---
# Specs live under web/e2e/ so Playwright never picks up vitest component tests.
shopt -s nullglob
e2e_specs=("$web_dir"/e2e/**/*.spec.ts "$web_dir"/e2e/*.spec.ts)
shopt -u nullglob
if [[ ${#e2e_specs[@]} -eq 0 ]]; then
  echo "frontend/e2e: SKIP Playwright (no e2e specs under web/e2e/)."
  echo "  WHY: axe-core/CLS e2e sensor needs Playwright specs; none are authored yet."
  echo "  FIX: add web/e2e/*.spec.ts and 'cd web && $pm exec playwright install --with-deps'."
elif [[ ! -d "$web_dir/node_modules/@playwright/test" ]]; then
  echo "frontend/e2e: SKIP Playwright (not installed)."
  echo "  WHY: a11y/CLS e2e sensor not installed."
  echo "  FIX: cd web && $pm add -D @playwright/test axe-playwright   to enforce e2e a11y + CLS."
elif [[ ! -d "$web_dir/node_modules/.cache/ms-playwright" ]] && [[ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ]]; then
  echo "frontend/e2e: SKIP Playwright (browsers not installed)."
  echo "  WHY: axe-core/CLS e2e sensor needs Playwright browsers."
  echo "  FIX: cd web && $pm exec playwright install --with-deps   to enforce a11y + CLS."
else
  echo "frontend/e2e: running Playwright (axe-core a11y + CLS)..."
  if ! $pm run playwright; then
    echo "frontend/e2e: FAIL (Playwright a11y/CLS)"
    echo "  WHY: e2e found accessibility violations or cumulative layout shift (CLS > 0)."
    echo "  FIX: fix axe violations and reserve space for async content (skeletons/fixed-aspect) to reach CLS ~ 0."
    status=1
  fi
fi

if [[ $status -eq 0 ]]; then
  echo "frontend/e2e: OK (or skipped cleanly)"
fi
exit $status
