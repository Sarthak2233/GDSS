# GDSS Developer Documentation

Welcome to the GDSS Developer Hub. GDSS separates documentation based on whether you are **integrating GDSS into your projects** or **contributing to the GDSS codebase**:

---

## 🚀 1. Using GDSS in Your Projects & Workflows

If you are a software engineer, tech lead, or DevOps engineer looking to integrate GDSS into your daily development, IDE, or CI/CD pipelines:

- **[User & Integrator Manual (`docs/USER_GUIDE.md`)](docs/USER_GUIDE.md)**:
  - Setup in AI IDEs via Model Context Protocol (`gdss mcp`) with Cursor, Claude Code, and Copilot ($0 token cost).
  - Local CLI & Interactive Terminal Shell (`gdss status`, `gdss suggest`, `gdss apply`, `gdss drift`).
  - Automated PR Collision Radar in GitHub Actions CI/CD with 1-click commit suggestions.
  - Next.js Web Dashboard for visual collision heatmaps and 3D constellation analysis.
  - Safe Landing Lifecycle (`gdss apply` preflight checks, dry-run diffs, and automatic rollback).
- **[Repository Configuration Guide (`docs/CONFIGURATION_GUIDE.md`)](docs/CONFIGURATION_GUIDE.md)**:
  - Full schema reference for `.gdss.yml`.
  - Context window discovery tiers and why explicit configuration is crucial.
  - Real-world recipes: Monorepos, Rust workspaces, Python, TypeScript, and Web3.
- **[GitHub Actions Guide (`docs/GITHUB_ACTIONS_GUIDE.md`)](docs/GITHUB_ACTIONS_GUIDE.md)**:
  - Drop-in CI workflow YAML, permissions, sticky comments, and Bring Your Own Compute (BYOC) token economics.

---

## 🛠️ 2. Contributing to the GDSS Codebase

If you are an engineer or researcher contributing code, fixing bugs, or adding language parsers/sensors to GDSS:

- **[Contributor & Architecture Guide (`CONTRIBUTING.md`)](CONTRIBUTING.md)**:
  - Contributor Quickstart (`bash harness/init.sh` and editable package install).
  - Two-Brain Purity architecture and the 10-layer hierarchy.
  - The Three-Layer Verification Gate (`bash harness/verify.sh` & `bash harness/verify-frontend.sh`).
  - Test-Driven Development (TDD) workflow and the Ratchet principle.
  - Adding a new semantic operator or AST parser language.
  - Pull request submission checklist and engineering discipline.
- **[Operating Manual (`AGENTS.md`)](AGENTS.md)**:
  - Feedforward guide for AI coding agents and automated workflows in this repository.
- **[Product Specification (`PRODUCT_SPEC.md`)](PRODUCT_SPEC.md)**:
  - Canonical specification, 31 user stories, implementation decisions, and roadmap status.
- **[Product Intent & Philosophy (`docs/PRODUCT_INTENT.md`)](docs/PRODUCT_INTENT.md)**:
  - North Star goals, non-goals, and two-brain honesty rules.
