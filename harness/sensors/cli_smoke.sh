#!/usr/bin/env bash
# GDSS harness Layer 3 sensor: end-to-end smoke test.
# Builds a throwaway git fixture repo and runs the gdss CLI over it, exercising
# the full pipeline (git observer -> AST parser -> transform extractor -> graph
# -> CLI rendering) together. Catches cross-component boundary defects that unit
# tests miss. Creates no lasting state and never touches global git config.
set -uo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo "cli-smoke: FAIL (git not installed)."
  echo "  WHY: the end-to-end layer drives gdss over a real git repo."
  echo "  FIX: install git, then re-run."
  exit 1
fi

# How to invoke the CLI: prefer the installed entrypoint, else import the app.
if command -v gdss >/dev/null 2>&1; then
  run_gdss() { gdss "$@"; }
elif python3 -c "import gdss" >/dev/null 2>&1; then
  run_gdss() { python3 -c 'from gdss.cli.main import app; app()' "$@"; }
else
  echo "cli-smoke: FAIL (gdss is not importable/installed)."
  echo "  WHY: cannot run the CLI end-to-end."
  echo "  FIX: bash harness/init.sh   (installs gdss in editable mode)."
  exit 1
fi

fixture="$(mktemp -d)"
cleanup() { rm -rf "$fixture"; }
trap cleanup EXIT

GIT() { git -C "$fixture" -c user.email=harness@gdss.local -c user.name=GDSSHarness "$@"; }

fail() {
  echo "cli-smoke: FAIL"
  echo "  WHAT: $1"
  echo "  WHY: an end-to-end CLI run errored; a component boundary is likely broken."
  echo "  FIX: reproduce with the printed command on the fixture and inspect the traceback."
  exit 1
}

# 1) Build the fixture repo with a base commit on the default branch.
GIT init -q || fail "git init failed"
base="$(GIT symbolic-ref --short HEAD 2>/dev/null || echo main)"

cat > "$fixture/sample.py" <<'PY'
def process_payment(amount):
    return amount


def helper():
    return process_payment(10)
PY
GIT add -A || fail "git add failed"
GIT commit -q -m "base: add payment" || fail "base commit failed"

# 2) Diverge on a feature branch: modify a function body + add a function.
#    This drives the full pipeline including downstream-impact propagation
#    (helper depends on process_payment).
GIT checkout -q -b feature-work || fail "branch create failed"
cat > "$fixture/sample.py" <<'PY'
def process_payment(amount):
    # apply a processing fee
    return amount * 2


def helper():
    return process_payment(10)


def audit(amount):
    return amount > 0
PY
GIT commit -qam "feature: change fee logic, add audit" || fail "feature commit failed"

echo "cli-smoke: running CLI over fixture ($base -> feature-work)..."

run_gdss --help >/dev/null 2>&1 || fail "gdss --help"
run_gdss status --repo "$fixture" --ref "$base" >/dev/null 2>&1 \
  || fail "gdss status --repo $fixture --ref $base"
run_gdss log --repo "$fixture" -n 5 >/dev/null 2>&1 \
  || fail "gdss log --repo $fixture -n 5"

# 3) Synchronized path: status on the reference branch itself.
GIT checkout -q "$base" || fail "checkout base failed"
run_gdss status --repo "$fixture" --ref "$base" >/dev/null 2>&1 \
  || fail "gdss status (reference branch)"

echo "cli-smoke: OK"
exit 0
