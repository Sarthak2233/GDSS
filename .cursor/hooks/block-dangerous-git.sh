#!/usr/bin/env bash
# GDSS harness sensor: block destructive git commands before they run.
# Event: beforeShellExecution. Returns a Cursor permission decision on stdout.
set -euo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.command // empty')"

# Patterns considered destructive / history-rewriting / irreversible.
patterns=(
  'git[[:space:]].*push'
  'git[[:space:]].*reset[[:space:]]+--hard'
  'git[[:space:]].*clean[[:space:]]+-[a-z]*f'
  'git[[:space:]].*branch[[:space:]]+-D'
  'git[[:space:]].*checkout[[:space:]]+\.'
  'git[[:space:]].*restore[[:space:]]+\.'
  'git[[:space:]].*rebase'
  'git[[:space:]].*filter-branch'
  'git[[:space:]].*update-ref[[:space:]]+-d'
)

for p in "${patterns[@]}"; do
  if [[ "$command" =~ $p ]]; then
    jq -n --arg cmd "$command" '{
      permission: "deny",
      user_message: "GDSS harness blocked a destructive git command.",
      agent_message: ("BLOCKED destructive git command: \"" + $cmd + "\". WHY: this can rewrite history or discard work irreversibly, which the GDSS harness forbids (never auto-destroy state). FIX: use a non-destructive alternative (e.g. git revert instead of reset --hard, git stash instead of checkout .) or ask the human to run it explicitly.")
    }'
    exit 0
  fi
done

echo '{ "permission": "allow" }'
exit 0
