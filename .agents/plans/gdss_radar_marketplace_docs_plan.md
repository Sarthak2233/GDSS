# Implementation Plan: `gdss-radar` Documentation & Configuration Overhaul

## Goal Description
Enhance the **`gdss-radar`** repository (the public GitHub Marketplace Action repo at `gdss-radar/`) with comprehensive, production-grade documentation. The overhaul will clearly guide external developers on:
1. **What GDSS Does & How It Works:** A minimal, accessible explanation of the 7 core intelligence layers (from Git DAG trajectory discovery to sandboxed candidate patch convergence) without leaking proprietary IP.
2. **Which Configuration File to Set:** The canonical `.gdss.yml` placed at the root of the user's repository.
3. **The Recommended Best Approach:** Explicit configuration of `model`, `context_window` (to avoid unintended 16k fallbacks), `risk_threshold`, `max_refinements`, and validation commands based on `docs/CONFIGURATION_GUIDE.md`.
4. **Copy-Paste Starter Template:** A production-ready `.gdss.yml.example` included directly in the repo for instant onboarding.

---

## Status: Completed ✅

All changes have been implemented, verified, and committed cleanly to `gdss-radar` on branch `main` (commit `52c417b`).

---

## What Was Completed:
1. **Clarification on GitHub Packages:**
   - Explained why the screenshot showed "No packages published" (it was taken before commit `560d7d6` was pushed, which added the automatic push trigger on `main`).
   - Verified that Docker image labels link the package directly to `Sarthak2233/GDSS`.
2. **`gdss-radar/README.md` Overhaul:**
   - **Hero & Problem Statement:** Single-PR isolation blindness vs. Air Traffic Control radar.
   - **The 7 Engine Layers (In Brief):** Cleanly documented the 7 layers from Git DAG discovery to ephemeral worktree sandbox and AI convergence without leaking proprietary IP.
   - **The Canonical Configuration File:** Explicitly presented `.gdss.yml` committed at the target repository root.
   - **The Recommended Best Approach:** Explaining the Golden Rule of declaring `context_window: 128000` to prevent conservative 16k fallback constriction and unlock up to 45% (96k chars) of code symbol budget.
   - **Stack-Specific Recipes:** TypeScript/Node.js, Python, and Go configurations.
   - **Merge Gate:** Branch protection gating with `fail_on_collision: true`.
3. **`gdss-radar/.gdss.yml.example`:**
   - Complete annotated starter template ready to copy into any repo root.
4. **Verification & Clean Isolation:**
   - Checked `git status` in both repositories.
   - Ran `lint.sh` and `architecture_fitness.py` in parent `GDSS` (all green).


---

## Proposed Changes

### `gdss-radar` Marketplace Repository (`/home/sarakb/projects/GDSS/gdss-radar/`)

#### [MODIFY] `gdss-radar/README.md`
Overhaul the Marketplace README with:
- **Hero & Problem Statement:** Single-PR isolation vs. Air Traffic Control collision radar.
- **The 7 Engine Layers (In Brief):**
  1. *Layer 1 — Git DAG Observer:* Discovers concurrent open PRs targeting the same base.
  2. *Layer 2 — 3-Tier Multi-Language AST Parser:* Extracts structured functions, classes, and signatures across Python, TS/JS, Go, Rust, Java, C/C++, etc.
  3. *Layer 3 — Semantic Transform Algebra:* Detects atomic code mutations ($dC$) rather than raw text line shifts.
  4. *Layer 4 — Dependency & Blast Radius Graph:* Computes in-memory caller/callee relationships to trace impact.
  5. *Layer 5 — Pairwise Collision Radar ($\Omega_{ij}$):* Calculates non-commutative operator interference $[T_i, T_j] \ne 0$ between concurrent PRs.
  6. *Layer 6 — Ephemeral Worktree Sandbox:* Compiles and tests proposed patches in isolated Git worktrees against syntax, static types, and unit tests.
  7. *Layer 7 — AI Convergence Assistant:* Reconciles differences with developer intent injection and compiler error trace self-healing loops.
- **The Recommended Configuration (`.gdss.yml`):**
  - Why `.gdss.yml` is the single source of truth.
  - The Golden Rule: avoiding 16k fallback constriction with explicit `context_window`.
  - Production templates for TypeScript/JavaScript, Python, and Multi-language Monorepos.
  - Explanation of key parameters (`risk_threshold`, `max_refinements`, `same_base_only`, `validation`).
- **Quickstart Workflows:**
  - Standard non-blocking informational radar.
  - Strict branch-protection gating (`fail_on_collision: true`).
- **Security & Privacy (BYOC):**
  - Runs on user's GitHub Actions runner. Zero code sent to external servers.

---

#### [NEW] `gdss-radar/.gdss.yml.example`
Provide an annotated template file that users can copy directly into their repository root as `.gdss.yml`:
```yaml
# .gdss.yml - Place at repository root
radar:
  model: "gpt-4o"
  context_window: 128000  # Recommended: declare explicitly to unlock full code budget
  provider: "github"      # Uses free GitHub Models via GITHUB_TOKEN
  risk_threshold: 0.1     # Collision intensity threshold (0.0 to 1.0)
  max_refinements: 2      # Sandbox self-correction attempts
  fail_on_collision: false

validation:
  test_command: "npm test -- {test_file}"
  typecheck_command: "npx tsc --noEmit"
  timeout_seconds: 60

hierarchy:
  reference_branch: "main"
  same_base_only: true
  exclude:
    - "dependabot/*"
    - "renovate/*"
    - "spike/*"
```

---

## Verification Plan

### Automated Checks
- Verify Markdown formatting and linting.
- Ensure parent `GDSS` git status remains clean and `gdss-radar/` remains properly ignored by `.gitignore`.
- Inside `gdss-radar/`, commit the changes cleanly on `main`.

### Manual Inspection
- Review rendered `README.md` structure against GitHub Marketplace presentation standards.
