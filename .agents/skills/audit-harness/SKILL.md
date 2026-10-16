---
name: audit-harness
description: Apply the ratchet principle - turn a recurring agent mistake into a permanent guide or sensor so it cannot recur. Use when the same mistake happens more than once, after a defect slips through, or when reviewing and strengthening the GDSS harness.
---

# Audit / Strengthen the Harness

The harness only tightens, never loosens. Every recurring mistake becomes a permanent fix.

## When to use

- The same class of mistake happened twice.
- A defect reached review that a sensor should have caught.
- A new convention emerged that agents keep missing.

## Decide: guide or sensor?

```
Did the agent KNOW the rule?
  No  -> add a GUIDE   (a .cursor/rules/*.mdc line or an AGENTS.md line)
  Yes -> add a SENSOR  (a hook, a lint rule, or a check in architecture_fitness.py)
```

Guides influence (~followed most of the time). Sensors enforce (~100%). A constraint that
must hold every time belongs in a sensor. A new constraint usually enters as a sensor first,
a guide second.

## Workflow

```
[ ] 1. Name the failure precisely (what went wrong, where, why it matters)
[ ] 2. Pick guide vs sensor using the decision above
[ ] 3a. GUIDE:  add a concise line to the right rule file; one concern per rule
[ ] 3b. SENSOR: add the check; write the message as WHAT / WHY / FIX
[ ] 4. Make the failure reproducible, then confirm the new control catches it
[ ] 5. If you added a computational sensor, wire it into harness/verify.sh
[ ] 6. Record the change in harness/state/progress.md
```

## Rules for added controls

- Every guide line and sensor must trace to a **real** failure. No aspirational rules.
- Keep guides short and actionable; put detail in skills or docs, not in always-on rules.
- Sensor messages must tell the next agent how to fix, not just that it failed.
- Never silence a sensor to make a build pass; fix the cause.

## Where controls live

- Guides: `AGENTS.md`, `.cursor/rules/*.mdc`, `.cursor/skills/*`
- Sensors: `.cursor/hooks/*` (agent lifecycle), `harness/sensors/*` + `harness/verify.sh`
  (pipeline), `harness/sensors/architecture_fitness.py` (structural)
