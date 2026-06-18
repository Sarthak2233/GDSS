#!/usr/bin/env bash
# GDSS harness observability: append a record of executed shell commands.
# Event: afterShellExecution. Pure observer; never blocks.
set -euo pipefail

input="$(cat)"

log_dir="harness/state"
log_file="$log_dir/audit.log"
mkdir -p "$log_dir"

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
command="$(printf '%s' "$input" | jq -r '.command // empty')"
exit_code="$(printf '%s' "$input" | jq -r '.exit_code // .exitCode // "?"')"

if [[ -n "$command" ]]; then
  printf '%s\texit=%s\t%s\n' "$ts" "$exit_code" "$command" >> "$log_file"
fi

echo '{}'
exit 0
