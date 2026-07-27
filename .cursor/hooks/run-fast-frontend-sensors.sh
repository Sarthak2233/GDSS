#!/usr/bin/env bash
# GDSS frontend harness sensor: fast feedback after a frontend file edit.
# Event: afterFileEdit. Runs cheap checks on the edited web/**/*.{tsx,ts,css}
# file and returns LLM-optimized guidance as additional_context (positive prompt
# injection). Mirrors .cursor/hooks/run-fast-sensors.sh for the backend.
set -euo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.file_path // .path // empty')"

# Only act on frontend source files inside web/.
case "$file" in
  */web/*.tsx|*/web/*.ts|*/web/*.css) ;;
  *) echo '{}'; exit 0 ;;
esac

[[ -f "$file" ]] || { echo '{}'; exit 0; }

messages=()

# 1) Token fitness (pure Python, always available) on the single edited file.
root="$(cd "$(dirname "$0")/.." && pwd)"
rel="${file#$root/}"
if out="$(python3 "$root/harness/sensors/frontend/token_fitness.py" 2>&1)" \
  && [[ "$out" == *"FAIL"* ]]; then
  messages+=("WHAT: token-fitness violations in $rel. WHY: raw hex/ms/linear or missing reduced-motion breaks the single-source-of-truth rule. FIX: use tokens from web/lib/tokens.ts and web/lib/motion.ts:"$'\n'"$out")
fi

# 2) eslint on the changed file (only if installed; otherwise stay silent).
if command -v pnpm >/dev/null 2>&1 || command -v npm >/dev/null 2>&1; then
  web_dir="$root/web"
  if [[ -d "$web_dir/node_modules" ]]; then
    cd "$web_dir" || true
    pm="pnpm"; command -v pnpm >/dev/null 2>&1 || pm="npx"
    rel_in_web="${file#$web_dir/}"
    if ! out="$($pm exec eslint "$rel_in_web" 2>&1)"; then
      messages+=("WHAT: eslint reported issues in $rel. WHY: violates frontend lint/a11y rules. FIX: address these then re-run:"$'\n'"$out")
    fi
  fi
fi

if [[ ${#messages[@]} -eq 0 ]]; then
  echo '{}'
  exit 0
fi

joined="$(printf '%s\n\n' "${messages[@]}")"
jq -n --arg ctx "GDSS frontend fast sensors flagged the last edit:"$'\n\n'"$joined" \
  '{ additional_context: $ctx }'
exit 0
