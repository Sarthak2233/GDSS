#!/usr/bin/env bash
# GDSS harness: the externalized definition of done.
#
# Implements the three-layer validation hierarchy. Each layer gates the next:
#   Layer 1 (static):     ruff + mypy + architecture fitness
#   Layer 2 (runtime):    pytest
#   Layer 3 (end-to-end): gdss CLI over a fixture repo
#
# Exits non-zero on the first failing layer. "Code is written" is never enough;
# only a green run here counts as done.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1
here="harness/sensors"

section() { printf '\n=== %s ===\n' "$1"; }

# ---------- Layer 1: static ----------
section "Layer 1 / static: lint"
bash "$here/lint.sh" || exit 1

section "Layer 1 / static: typecheck"
bash "$here/typecheck.sh" || exit 1

section "Layer 1 / static: architecture fitness"
python3 "$here/architecture_fitness.py" || {
  echo "verify: stopped at Layer 1 (architecture). Fix violations above."
  exit 1
}

section "Layer 1 / static: DSA fitness"
python3 "$here/dsa_fitness.py" || {
  echo "verify: stopped at Layer 1 (DSA fitness). Fix violations above."
  exit 1
}

# ---------- Layer 2: runtime ----------
section "Layer 2 / runtime: tests"
bash "$here/run_tests.sh" || {
  echo "verify: stopped at Layer 2 (tests)."
  exit 1
}

# ---------- Layer 3: end-to-end ----------
section "Layer 3 / end-to-end: cli smoke"
bash "$here/cli_smoke.sh" || {
  echo "verify: stopped at Layer 3 (end-to-end)."
  exit 1
}

# ---------- Frontend harness (only when web/ exists) ----------
if [[ -d "web" ]]; then
  section "Frontend harness: verify-frontend.sh"
  bash "harness/verify-frontend.sh" || {
    echo "verify: stopped at the frontend harness."
    exit 1
  }
else
  section "Frontend harness"
  echo "verify: SKIP frontend harness (web/ does not exist)."
fi

section "RESULT"
echo "verify: ALL LAYERS GREEN. Work meets the definition of done."
exit 0
