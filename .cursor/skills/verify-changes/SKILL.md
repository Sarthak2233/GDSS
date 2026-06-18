---
name: verify-changes
description: Run and interpret the GDSS verification pipeline (the three-layer validation gate). Use before declaring any change done, when verify.sh fails, or when deciding whether work is complete.
---

# Verify Changes

`bash harness/verify.sh` is the externalized definition of done. Run it before claiming any
work is complete. Do not rely on your own confidence.

## The three layers (each gates the next)

1. **Static (Layer 1)** - `ruff`, `mypy`, `architecture_fitness.py`. Cheapest, must pass
   first.
2. **Runtime (Layer 2)** - `pytest`. Proves behavior runs, not just compiles.
3. **End-to-end (Layer 3)** - `gdss` CLI over a fixture repo. Catches cross-component
   (parser -> extractor -> graph -> CLI) boundary defects that unit tests miss.

## Usage

```bash
bash harness/verify.sh          # full gate; exits non-zero on first failing layer

# Iterate on one layer while fixing:
bash harness/sensors/lint.sh
bash harness/sensors/typecheck.sh
python harness/sensors/architecture_fitness.py
bash harness/sensors/run_tests.sh
bash harness/sensors/cli_smoke.sh
```

## Interpreting failures

Sensor output is written for agents: WHAT failed / WHY / FIX. Apply the FIX, then re-run the
**whole** gate (a later fix can re-break an earlier layer).

- Lint/type failure -> fix the code; do not silence the rule.
- Architecture failure -> a layer/two-brain boundary was crossed; move code to the correct
  layer or invert the dependency. Do not weaken the sensor to pass.
- Test failure -> read the assertion; fix behavior, not the test, unless the test encoded the
  wrong behavior.
- CLI failure -> a real end-to-end break; reproduce with the printed `gdss` command.

## Done means

All three layers green. If you changed cross-component behavior, the end-to-end layer passing
is mandatory, not optional.
