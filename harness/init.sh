#!/usr/bin/env bash
# GDSS harness: session bootstrap + health check (Lifecycle subsystem).
# Idempotent. Run at the start of every session. Reports whether the environment
# is healthy enough to begin work.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

ok=0
warn=0

pass() { echo "  [ok]   $1"; }
note() { echo "  [warn] $1"; warn=$((warn + 1)); }
bad()  { echo "  [FAIL] $1"; ok=1; }

echo "GDSS harness init"
echo "-----------------"

# 1) Python.
echo "Python:"
if command -v python3 >/dev/null 2>&1; then
  pass "python3 $(python3 --version 2>&1 | awk '{print $2}')"
else
  bad "python3 not found (required)."
fi

# 2) Editable install of the gdss package.
echo "Package:"
if python3 -c "import gdss" >/dev/null 2>&1; then
  pass "gdss importable"
else
  echo "  installing gdss (editable)..."
  if python3 -m pip install -e . >/dev/null 2>&1; then
    pass "installed gdss in editable mode"
  else
    note "could not auto-install. FIX: python3 -m pip install -e ."
  fi
fi

# 3) CLI entrypoint.
echo "CLI:"
if command -v gdss >/dev/null 2>&1 && gdss --help >/dev/null 2>&1; then
  pass "gdss --help works"
elif python3 -c "from gdss.cli.main import app" >/dev/null 2>&1; then
  pass "gdss CLI importable (entrypoint not on PATH)"
else
  bad "gdss CLI not runnable. FIX: python3 -m pip install -e ."
fi

# 4) Runtime deps.
echo "Dependencies:"
for mod in git tree_sitter networkx typer rich httpx; do
  if python3 -c "import $mod" >/dev/null 2>&1; then
    pass "$mod"
  else
    note "$mod missing. FIX: python3 -m pip install -r requirements.txt"
  fi
done

# 5) Test runner (Layer 2 sensor).
echo "Sensors:"
if python3 -c "import pytest" >/dev/null 2>&1 || command -v pytest >/dev/null 2>&1; then
  pass "pytest available"
else
  note "pytest missing. FIX: python3 -m pip install pytest"
fi
command -v ruff  >/dev/null 2>&1 && pass "ruff available"  || note "ruff missing (lint will skip). FIX: pip install ruff"
command -v mypy  >/dev/null 2>&1 && pass "mypy available"  || note "mypy missing (typecheck will skip). FIX: pip install mypy"
command -v git   >/dev/null 2>&1 && pass "git available"   || bad "git missing (end-to-end layer needs it)."
command -v jq    >/dev/null 2>&1 && pass "jq available (hooks)" || note "jq missing; Cursor hooks need it. FIX: install jq"

# 6) State files.
echo "State:"
for f in harness/state/feature_list.json harness/state/progress.md harness/state/session-handoff.md; do
  [[ -f "$f" ]] && pass "$f" || note "$f missing"
done

echo "-----------------"
if [[ $ok -ne 0 ]]; then
  echo "init: UNHEALTHY (fix [FAIL] items above before working)."
  exit 1
fi
if [[ $warn -ne 0 ]]; then
  echo "init: READY with $warn warning(s). Optional tools missing; core flow works."
else
  echo "init: HEALTHY. Next: read harness/state/progress.md, pick one feature, work test-first."
fi
exit 0
