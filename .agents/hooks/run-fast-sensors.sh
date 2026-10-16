#!/usr/bin/env bash
# GDSS harness sensor: fast feedback after a file edit (keep quality left).
# Event: afterFileEdit. Runs cheap checks on the edited .py file and returns
# LLM-optimized guidance as additional_context (a positive prompt injection).
set -euo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.file_path // .path // empty')"

# Only act on Python source files inside the project.
case "$file" in
  *.py) ;;
  *) echo '{}'; exit 0 ;;
esac

[[ -f "$file" ]] || { echo '{}'; exit 0; }

messages=()

# 1) Syntax check (always available).
if ! err="$(python3 -m py_compile "$file" 2>&1)"; then
  messages+=("WHAT: $file has a syntax error. WHY: it will not import or run. FIX: $err")
fi

# 2) Lint (only if ruff is installed; otherwise stay silent to avoid noise).
if command -v ruff >/dev/null 2>&1; then
  if ! out="$(ruff check "$file" 2>&1)"; then
    messages+=("WHAT: ruff reported lint issues in $file. WHY: violates project style/quality rules. FIX: address these then re-run, or 'ruff check --fix $file' for autofixable ones:"$'\n'"$out")
  fi
fi

# 3) Two-brain reminder: deterministic brain must not import probabilistic brain.
case "$file" in
  gdss/core/*|gdss/graph/*|gdss/watcher/*)
    if grep -Eq '^[[:space:]]*(from|import)[[:space:]]+gdss\.(ai|embeddings)' "$file"; then
      messages+=("WHAT: $file (deterministic brain) imports the probabilistic brain (gdss.ai/gdss.embeddings). WHY: it breaks two-brain purity; deterministic code must stay trusted and independent. FIX: remove the import; if AI is needed, invert the dependency so the ai/embeddings layer depends on core.")
    fi
    ;;
esac

if [[ ${#messages[@]} -eq 0 ]]; then
  echo '{}'
  exit 0
fi

joined="$(printf '%s\n\n' "${messages[@]}")"
jq -n --arg ctx "GDSS fast sensors flagged the last edit:"$'\n\n'"$joined" \
  '{ additional_context: $ctx }'
exit 0
