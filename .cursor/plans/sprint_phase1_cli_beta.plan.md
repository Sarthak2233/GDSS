---
name: GDSS Sprint - Product Phase 1 (CLI Beta)
overview: "Sprint roadmap for Product Phase 1: CLI Beta. This sprint focuses on establishing the core technical foundation and distributing the initial CLI agent. No AI/SaaS features are included in this phase."
todos:
  - id: sp1-telemetry
    content: ""
    status: pending
  - id: sp1-distribution
    content: ""
    status: pending
  - id: sp1-cicd
    content: ""
    status: pending
  - id: sp1-dsa-harness
    content: ""
    status: done
  - id: sp1-bug-rename
    content: ""
    status: pending
isProject: false
---

# Sprint Roadmap: Product Phase 1 (CLI Beta)

**Goal:** Establish the core technical foundation (AST/dep-graph) and distribute the initial CLI agent to developers.
**Milestone:** v1.0 CLI released on PyPI/Homebrew. 500 dev installations.

> [!NOTE]
> This sprint corresponds to **Product Phase 1** from the North Star `research.md`. It assumes the core semantic structural foundation (Sub-Phase 1.1) is mostly complete and focuses on hardening, telemetry, and distribution.

## Active Sub-Phases

### Sub-Phase: Telemetry & Privacy Integration

*See `research.md` Section 4 for requirements.*

- Implement opt-out telemetry flag (`gdss config --telemetry off`).
- Define telemetry payload schema (strictly metadata: OS/version, CLI version, generic drift score).
- Ensure all API endpoints for telemetry default to HTTPS/TLS.
- Add one-time consent notice on first CLI run.

### Sub-Phase: CLI Stabilization & Distribution

*See `research.md` Section 3 for requirements.*

- Generate PyPI `setup.py`/`pyproject.toml` distribution configuration (Note: keep additive to harness where possible).
- Create Homebrew tap script template.
- Add `gdss init` command logic to install git hooks locally.
- Draft README installation instructions for `pip` and `brew`.

### Sub-Phase: CI/CD Pipeline

*See `research.md` Section 6 for requirements.*

- Add GitHub Actions workflow for running the 3-layer verification gate (`harness/verify.sh`).
- Automate python wheel builds on tag push.
- Add dependency caching to speed up CI runs.

### Sub-Phase: DSA Optimization Harness

- Create `.cursor/rules/35-dsa-optimization.mdc` (feedforward guide)
- Create `.cursor/skills/dsa-optimize/SKILL.md` (on-demand workflow)
- Create `harness/sensors/dsa_fitness.py` (feedback sensor)
- Wire sensor into `harness/verify.sh`
- Document 6 existing anti-patterns as harness findings

### Sub-Phase: Harness Fixes & Backlog

> [!WARNING]
> **PENDING BUG FIX:** `rename-downstream-crash`.
>
> - **Where:** `gdss/cli/main.py:228` (status command, Downstream Change Impact section).
> - **What:** `TypeError: 'in <string>' requires string as left operand, not NoneType`.
> - **Fix:** Guard against `None` / use `op.to_name` or `op.from_name` for rename operators before the membership test. (Requires source change).

- Execute `rename-downstream-crash` bug fix (test-driven).
- Review any new static analysis warnings from the updated harness hooks.

