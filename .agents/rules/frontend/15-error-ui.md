---
description: Error UI for GDSS frontend
globs: web/**
alwaysApply: false
---

# Error UI

Errors must be recoverable and explained, mirroring the backend harness's
agent-oriented WHAT/WHY/FIX format.

## Error anatomy

```
WHAT happened -> WHY it is wrong -> FIX (action to recover)
```

## Rules

- A failing widget must not take down the whole dashboard; isolate errors with
  an error boundary that renders an inline error card.
- Provide a retry action where the operation is idempotent.
- Use `danger` color for destructive/unrecoverable errors; `warning` for
  recoverable ones.
- Never expose raw stack traces to end users; log them, show a friendly message.
- Errors are a state in the 8-state machine (see `05-state-transitions`).

## Forms / input errors

- Inline, adjacent to the field, on blur and on submit (not on every keystroke).
- Pair the message with an icon; do not rely on color alone.
- `aria-invalid` and `aria-describedby` linking field to its error message.

## Network / async

- Distinguish transient (retry) from permanent (contact/reconfigure) errors.
- Show the last-known-good data with a stale indicator where possible, rather
  than blanking the view.
