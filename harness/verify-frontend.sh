#!/usr/bin/env bash
# GDSS frontend harness: the externalized frontend definition of done.
#
# Implements the three frontend layers (mirrors the backend three-layer hierarchy
# in harness/verify.sh). Each layer gates the next:
#   Layer F1 (static):     eslint (+jsx-a11y) + tsc + token_fitness
#   Layer F2 (component):  vitest + jest-axe
#   Layer F3 (end-to-end): Playwright a11y/CLS + size-limit (optional)
#
# Every sensor degrades gracefully (skip with WHAT/WHY/FIX) when the JS toolchain
# is absent, so this gate stays runnable on a Python-only machine. Install deps
# to make each sensor a hard gate.
#
# Exits non-zero on the first failing layer. "Code is written" is never enough.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1
here="harness/sensors/frontend"

section() { printf '\n=== %s ===\n' "$1"; }

# ---------- Layer F1: static ----------
section "Layer F1 / static: eslint (+ jsx-a11y)"
bash "$here/lint.sh" || { echo "verify-frontend: stopped at F1 (lint)."; exit 1; }

section "Layer F1 / static: typecheck"
bash "$here/typecheck.sh" || { echo "verify-frontend: stopped at F1 (typecheck)."; exit 1; }

section "Layer F1 / static: token fitness"
python3 "$here/token_fitness.py" || { echo "verify-frontend: stopped at F1 (token fitness)."; exit 1; }

# ---------- Layer F2: component ----------
section "Layer F2 / component: vitest + jest-axe"
bash "$here/component_tests.sh" || { echo "verify-frontend: stopped at F2 (component tests)."; exit 1; }

# ---------- Layer F3: end-to-end (optional) ----------
section "Layer F3 / end-to-end: playwright a11y/CLS + size-limit"
bash "$here/e2e.sh" || { echo "verify-frontend: stopped at F3 (e2e)."; exit 1; }

section "RESULT"
echo "verify-frontend: ALL FRONTEND LAYERS GREEN (or skipped cleanly). Frontend work meets the definition of done."
exit 0
