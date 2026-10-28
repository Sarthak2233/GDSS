# 📖 GDSS User & Integrator Guide

> **A Practical Guide to Using GDSS as Your PR Collision Radar, IDE Assistant, and Automated Convergence Engine.**

---

## 📑 Table of Contents

- [What is GDSS? (And What It Isn't)](#-what-is-gdss-and-what-it-isnt)
- [Installation & Quickstart](#-installation--quickstart)
- [The 4 Ways to Use GDSS](#-the-4-ways-to-use-gdss)
  - [Mode 1: AI IDEs via Model Context Protocol (MCP)](#mode-1-ai-ides-via-model-context-protocol-mcp-zero-token-cost)
  - [Mode 2: Local CLI & Interactive Shell](#mode-2-local-cli--interactive-terminal-shell)
  - [Mode 3: Automated GitHub Actions CI/CD](#mode-3-automated-github-actions-cicd)
  - [Mode 4: Web Visual Dashboard (Next.js 14)](#mode-4-web-visual-dashboard-nextjs-14)
- [The Safe Landing Lifecycle: Guarded Apply & Rollback](#-the-safe-landing-lifecycle-guarded-apply--rollback)
- [Repository Configuration (`.gdss.yml`) Overview](#-repository-configuration-gdssyml-overview)
- [Bring Your Own Compute (BYOC) & Privacy](#-bring-your-own-compute-byoc--privacy)

---

## 🎯 What is GDSS? (And What It Isn't)

### The Core Concept: Air Traffic Control for Pull Requests

Traditional version control systems (like Git) only see code as static text lines. When two branches touch different files or separate sections of the same file, Git reports a "clean merge" even if one branch changed a function signature that the other branch calls.

GDSS builds a **deterministic semantic intelligence layer above Git**:

```
                       [ Attractor / Base Branch: main ]
                                 ▲        ▲
                     Trajectory  │        │  Trajectory
                         γ_A(t)  │        │  γ_B(t)
                                 │        │
                         [ Branch A ]  [ Branch B ]
                                 ▲
                                 │  Trajectory γ_C(t)
                         [ Branch C (stacked/child) ]
```

- **Air Traffic Control Radar:** Unlike GitHub Copilot (which assists with the file you are currently typing in), GDSS continuously monitors all branch flight paths across the entire repository to detect semantic and architectural collisions **before merge**.
- **$0 Token Cost Core:** The core analysis (AST parsing, call/import dependency graphs, collision matrix $\Omega_{ij}$, commutativity algebra, and optimal merge ordering) runs **100% locally on CPU at literal 0 token cost**.
- **Ephemeral Sandbox Validation:** When candidate patches are synthesized, they are tested inside temporary Git worktrees (checking syntax, types, and running targeted unit tests) before you ever review them.
- **Strict Developer Agency:** GDSS **never auto-merges or auto-commits**. You always review and approve candidate resolutions.

---

## 📦 Installation & Quickstart

### Prerequisites
- **Python 3.11+** installed
- **Git 2.25+** installed
- *(Optional for Web UI)* **Node.js 18+** & **pnpm**

### Local Installation
```bash
# Clone the repository
git clone https://github.com/Sarthak2233/GDSS.git
cd GDSS

# Bootstrap environment (creates venv and installs editable CLI)
bash harness/init.sh

# Verify installation
gdss --help
```

---

## 🚀 The 4 Ways to Use GDSS

---

### Mode 1: AI IDEs via Model Context Protocol (MCP) [Zero Token Cost]

This is the primary delivery interface for developers using **Cursor**, **Claude Code**, or **GitHub Copilot**. 

GDSS runs as a local MCP server exposing deterministic analysis tools over standard JSON-RPC 2.0. The IDE's model queries GDSS for ground truth facts while powering the conversation with your existing IDE account. **GDSS incurs zero API fees and sends zero private code to third parties.**

```
┌────────────────────────────────────────────────────────┐
│  Developer AI IDE (Cursor / Claude Code / Copilot)     │
│  Runs in developer's existing account (Zero GDSS fee)  │
└──────────────────────────┬─────────────────────────────┘
                           │ Standard MCP Protocol (JSON-RPC)
┌──────────────────────────▼─────────────────────────────┐
│  GDSS Deterministic MCP Server (`gdss mcp`)            │
│  100% Deterministic Local Core (ASTs, Graphs, Git)     │
│  Literally 0 tokens & runs entirely on local CPU       │
└────────────────────────────────────────────────────────┘
```

#### Setup in Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "gdss": {
      "command": "gdss",
      "args": ["mcp"]
    }
  }
}
```

#### Setup in Claude Code (`~/.claude.json` or project `.mcp.json`)
```json
{
  "mcpServers": {
    "gdss": {
      "command": "gdss",
      "args": ["mcp"]
    }
  }
}
```

#### Available MCP Tools
- `gdss_find_collisions`: Scans for semantic collisions across active local branches (supports `branches` and `exclude_branches` parameters).
- `gdss_get_merge_order`: Computes the mathematically optimal merge sequence to minimize conflicts (supports `branches` and `exclude_branches`).
- `gdss_inspect_symbol_impact`: Traces callers and dependents affected by a change.
- `gdss_plan_semantic_rebase`: Generates a rebase plan classifying kept, remapped, and blocked operators (supports `branches` and `exclude_branches`).
- `gdss_validate_patch`: Dry-run validates candidate patch diffs against syntax and type checkers.

#### Branch Scoping in MCP Tool Invocations
When pairing with Cursor or Claude Code, your assistant can filter branches to focus on relevant PRs and ignore experimental spikes:

```json
{
  "name": "gdss_find_collisions",
  "arguments": {
    "repo_path": ".",
    "reference_branch": "main",
    "branches": ["feature/auth", "feature/billing"],
    "exclude_branches": ["spike/*", "dependabot/*"]
  }
}
```

#### 🤖 How MCP Autonomous Tool Execution Works (Zero Manual Prompt Typing)

Developers **never need to type out long prompt templates or AST definitions manually**.

The interaction in Cursor, Claude Code, or Copilot is conversational:
1. **Natural Language Input:** You type a standard request in your IDE chat:
   > *"Check if my branch `feature/auth` has any collisions with `develop`, and help me resolve them."*
2. **Autonomous Background Tool Calling:** The IDE's AI assistant inspects the registered GDSS tool definitions and automatically executes the pipeline in the background:
   - Calls `gdss_find_collisions(reference_branch='develop', branches=['feature/auth'])`
   - Calls `gdss_inspect_symbol_impact(symbol='login')`
   - Synthesizes the candidate patch using the pre-extracted 3-way AST context
   - Calls `gdss_sandbox_validate_patch(patch=...)` to test syntax and unit tests inside an ephemeral worktree
3. **Verified Suggestion:** The assistant presents only the verified patch along with sandbox execution evidence (e.g. *"Tested in sandbox worktree: syntax OK, 14 tests passing"*).

#### 📋 Alternative: One-Click Prompt Templates & Web Model Paste
- **MCP Prompt Templates:** Under the Model Context Protocol standard (`prompts/get`), IDEs that support slash commands (such as Claude Desktop or Cursor) allow you to trigger prompt shortcuts directly from the UI.
- **Air-Gapped / Web LLM Mode:** If you use web models (ChatGPT, Claude.ai) without a local MCP connection, run:
  ```bash
  gdss suggest --as-prompt
  ```
  GDSS prints the complete, self-contained 3-way prompt directly to your terminal for one-click copy and paste.

---

### Mode 2: Local CLI & Interactive Terminal Shell

GDSS provides an interactive terminal shell and subcommands for repository analysis:

#### 1. Interactive Shell & Runtime Configuration
```bash
gdss start
```
Displays branch status indicators, uncommitted semantic deltas, and live collision alerts. You can persist branch scoping and hierarchy preferences directly in `.gdss/runtime.db`:

```
gdss (main)> config hierarchy main develop staging
Updated priority chain in database: ['main', 'develop', 'staging']

gdss (main)> config branches include feature/* fix/*
Added 2 include branch pattern(s) to runtime database.

gdss (main)> config branches exclude spike/* archive/*
Added 2 exclude branch pattern(s) to runtime database.

gdss (main)> hierarchy
Attractor: main
Priority Chain: ['main', 'develop', 'staging']
Active Branch Filters:
  Include: ['feature/*', 'fix/*']
  Exclude: ['spike/*', 'archive/*']

gdss (main)> tensor
# Computes Omega_ij ONLY across branches matching include patterns!

gdss (main)> config branches clear
Cleared branch filters from runtime database.
```

#### 2. Checking Collision Status
```bash
gdss status --ref main
```
Reports active branch trajectories, uncommitted semantic operators, and drift distance from `main`.

#### 3. PR Collision Matrix ($\Omega_{ij}$) with Branch Scoping
```bash
# Unconstrained evaluation across all local branches
gdss tensor --ref main

# Targeted evaluation between specific feature branches only
gdss tensor --ref main --branches feature/auth --branches feature/billing

# Tensor evaluation excluding experimental or archived spikes
gdss tensor --ref main --exclude "spike/*" --exclude "archive/*"
```

#### 4. Semantic Drift Tracking with Scoping
```bash
# Track drift for specific feature branches only
gdss drift --ref main --branches "feature/*" --exclude "spike/*"
```

#### 5. Requesting Assisted Suggestions
```bash
# Model-Free (Deterministic Algebraic Strategies) on specific branches
gdss suggest --repo . --ref main -b feature/auth -b feature/billing

# With Local LLM (Ollama or vLLM) + Sandbox Validation
gdss suggest --repo . --ref main --llm --provider ollama --model qwen2.5-coder:7b --validate

# With Cloud Provider (OpenRouter, OpenAI, or GitHub Models)
export OPENROUTER_API_KEY="sk-or-..."
gdss suggest --repo . --ref main --llm --provider openrouter --model anthropic/claude-3.5-sonnet --validate
```

---

### Mode 3: Automated GitHub Actions CI/CD

GDSS audits incoming pull requests for semantic collisions against all concurrently open PRs on GitHub, posting a sticky collision radar report with 1-click **"Commit suggestion"** buttons.

<p align="center">
  <img src="../assets/ci/github_actions_flow.svg" alt="GDSS GitHub Actions Flow" width="100%">
</p>

#### 🔀 Multi-PR Batch Handling: How 1 CI Run Audits Multiple Concurrent PRs

When an incoming pull request (e.g., PR #42) is opened while 5 other PRs are concurrently open (#39, #40, #41, #43, #44), **GDSS processes all 5 PRs in a single workflow run**:

1. **Autonomous Discovery:** `fetch_concurrent_prs()` automatically lists all open pull requests targeting the same base attractor (`main`).
2. **Pairwise 3-Way Triangles (One Concurrent PR at a Time):**
   Instead of dumping all 5 branches into an unpredictable $N$-way monolithic prompt, GDSS evaluates each concurrent PR pairwise:
   - **Triangle 1:** Base (`main`) vs Incoming PR #42 vs Concurrent PR #39
   - **Triangle 2:** Base (`main`) vs Incoming PR #42 vs Concurrent PR #40
   - **Triangle 3:** Base (`main`) vs Incoming PR #42 vs Concurrent PR #41
   - ... and so on for each concurrent PR.
3. **Isolated Reconciliation & Ephemeral Sandboxing:**
   For each pair with significant collision ($\Omega_{ij} > 0.1$):
   - GDSS extracts the exact 3-way symbol representation ($V_{base}, V_{incoming}, V_{concurrent}$) and impacted callers.
   - The convergence engine drafts the reconciled definition with zero cross-PR pollution.
   - An ephemeral Git worktree sandbox compiles and tests the candidate patch against syntax and unit tests.
4. **Aggregated Sticky Radar Report:**
   All detected collisions and validated patches across all concurrent PRs are aggregated into a single, clean markdown comment posted to the incoming PR:

| Colliding PR | Author | Target File | Overlapping Symbol | Risk ($\Omega_{ij}$) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **#39** (feature-auth) | @alice | `auth/login.py` | `login()` | `0.85` | ⚡ Tested in sandbox (syntax: OK, 12 tests passed) |
| **#41** (billing-v2) | @bob | `billing/pay.py` | `process()` | `0.64` | ⚡ Tested in sandbox (syntax: OK, 8 tests passed) |

This pairwise 3-way batching guarantees that adding 5 or 50 concurrent PRs never creates prompt explosion or cross-feature hallucination.

## ⚙️ Repository Configuration (`.gdss.yml`) Overview

GDSS is **zero-config by default**. However, placing a `.gdss.yml` in the root of your repository ensures consistent behavior across developer laptops and CI runners:

```yaml
# .gdss.yml - Project-level semantic intelligence configuration

radar:
  model: "gpt-4o"
  context_window: 128000
  provider: "github"
  max_refinements: 2
  risk_threshold: 0.8
  fail_on_collision: false

validation:
  test_command: "pytest {test_file}"
  typecheck_command: "mypy {file}"
  timeout_seconds: 60

ast:
  additional_extensions:
    - .vue
    - .svelte
    - .sol
    
hierarchy:
  reference_branch: "main"
  priority_chain:
    - "main"
    - "develop"
  # Only audit PRs that share the exact same base landing branch (eliminates cross-target false alarms)
  same_base_only: true
  include:
    - "feature/*"
    - "fix/*"
  exclude:
    - "spike/*"
    - "dependabot/*"
  target_bases:
    - "main"
    - "develop"
```

#### 2. Drop-in Workflow (`.github/workflows/gdss-radar.yml`)
Add this workflow to your repository to activate automated PR audits:

```yaml
name: GDSS PR Collision Radar

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  collision-radar:
    name: Audit Cross-Branch PR Collisions
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install gdss
      - name: Run Collision Audit
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
          GITHUB_REPOSITORY: ${{ github.repository }}
        # Can use .gdss.yml defaults or override on CLI:
        run: gdss audit-pr --branches "feature/*" --exclude "dependabot/*" --same-base-only
```

> 📖 **Full CI/CD Guide:** See [`docs/GITHUB_ACTIONS_GUIDE.md`](GITHUB_ACTIONS_GUIDE.md) for blocking vs. informational modes, fork handling, and configuration options.

---

### Mode 4: Web Visual Dashboard (Next.js 14) & REST API

GDSS includes a web dashboard in `web/` and a local REST API that provides an interactive geometric view of repository health:

```bash
# 1. Start the GDSS local REST API server
gdss serve --repo . --port 8000

# 2. Start the Next.js visual dashboard
cd web
pnpm install
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) to view:
- **Interactive Branch Scope Filter:** Click the **"Scope: All branches"** popover in the top navigation bar to interactively filter which branches participate in drift and tensor calculations.
- **Collision Radar Matrix:** Live heatmap of $\Omega_{ij}$ scores across selected branches.
- **Interactive Constellation & Code Graph:** 2D/3D symbol projection and caller/callee graphs powered by React Flow.
- **Merge Order Visualizer:** Recommended sequence for landing open branches.

#### REST API Branch Filtering Endpoints
You can also query or automate the dashboard backend programmatically:
```bash
# Query Conflict Tensor with branch scoping
curl "http://localhost:8000/v1/tensor?ref=main&branches=feature/auth,feature/billing&exclude=spike-*"

# Query Drift with branch scoping
curl "http://localhost:8000/v1/drift?ref=main&branches=feature/auth"

# Inspect and dynamically update priority chain and filters
curl "http://localhost:8000/v1/hierarchy"
curl -X POST "http://localhost:8000/v1/hierarchy" \
  -H "Content-Type: application/json" \
  -d '{"priority_chain": ["main", "develop"], "include": ["feature/*"], "exclude": ["spike/*"]}'
```

---

## 🔒 The Safe Landing Lifecycle: Guarded Apply & Rollback

Once candidate suggestions are generated and audited (saved under `.gdss/suggestions/<id>.json`), developers can preview, apply, and rollback patches with complete safety:

```bash
# 1. Preview changes as a colorized unified diff (Zero risk, disk untouched)
gdss apply sug_8f2a91c3 --strategy adapt_signature --dry-run

# 2. Apply the approved suggestion to your working tree
gdss apply sug_8f2a91c3 --strategy adapt_signature

# 3. Instantly undo an applied suggestion
gdss apply sug_8f2a91c3 --rollback
```

### Safety Invariants of `gdss apply`
1. **Preflight HEAD Freshness:** Rejects suggestions if your local Git `HEAD` has drifted from the commit SHA the suggestion was calculated against.
2. **Canonical Path Protection:** Blocks any path traversal (`../`) outside the repository root.
3. **AST Symbol Verification:** Confirms target symbol is still present and matches expected boundaries before touching disk.
4. **Self-Healing Rollback:** Snapshots original file content to `.gdss/rollback/<id>.json`. If post-apply multi-language AST syntax validation fails, GDSS **automatically rolls back disk changes** immediately.
5. **Zero Git State Mutation:** Modifies only the target working tree file. GDSS **never** executes `git merge`, `git rebase`, `git add`, `git commit`, or `git push`.

---



> 📖 **Full Configuration Guide:** See [`docs/CONFIGURATION_GUIDE.md`](CONFIGURATION_GUIDE.md) for detailed directives, provider-specific recipes (Ollama, vLLM, OpenRouter, OpenAI, GitHub Models), and context window allocation strategies.

---

## 🛡️ Bring Your Own Compute (BYOC) & Privacy

GDSS is engineered around transparent compute ownership and privacy:
- **No Token Markup:** GDSS does not sell or proxy LLM tokens. You bring your existing IDE subscription, your repository's native `GITHUB_TOKEN`, or local offline models.
- **Zero Source Code Leaks:** In model-free mode and IDE MCP mode, zero source code is transmitted outside your local machine.
- **Zero PII or Telemetry Bleed:** All internal telemetry is strictly metadata-only with a complete opt-out mechanism.
