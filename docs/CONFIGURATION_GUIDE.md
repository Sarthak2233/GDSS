# ⚙️ GDSS Repository Configuration Guide (`.gdss.yml`)

> **The Definitive Guide to Configuring `.gdss.yml` for Predictable Models, Explicit Context Windows, Agentic Refinement Loops, and CI/CD Collision Radar.**

---

## 📑 Table of Contents
- [Overview: Why Explicit Configuration Matters](#-overview-why-explicit-configuration-matters)
- [The Golden Rule: Avoid Unintended Fallbacks](#-the-golden-rule-avoid-unintended-fallbacks)
- [Complete Production `.gdss.yml` Template](#-complete-production-gdssyml-template)
- [Detailed Schema Reference](#-detailed-schema-reference)
  - [`radar` (AI Convergence & CI Radar)](#1-radar-ai-convergence--ci-radar)
  - [`validation` (Ephemeral Sandbox Worktrees)](#2-validation-ephemeral-sandbox-worktrees)
  - [`ast` (Multi-Language & DSL Tracking)](#3-ast-multi-language--dsl-tracking)
- [Provider-Specific Recipes](#-provider-specific-recipes)
  - [GitHub Actions / GitHub Models (Default CI)](#a-github-actions--github-models-default-ci)
  - [OpenAI Direct](#b-openai-direct)
  - [OpenRouter (Multi-Model Gateway)](#c-openrouter-multi-model-gateway)
  - [Local Ollama (Offline Developer Workstation)](#d-local-ollama-offline-developer-workstation)
  - [Local or Private vLLM Cluster](#e-local-or-private-vllm-cluster)
- [What to Expect After Integration](#-what-to-expect-after-integration)
  - [In Pull Requests (GitHub Actions CI)](#1-in-pull-requests-github-actions-ci)
  - [In Local Development (CLI)](#2-in-local-development-cli)
  - [In IDEs (Cursor / Claude Code / Copilot MCP)](#3-in-ides-cursor--claude-code--copilot-mcp)

---

## 🎯 Overview: Why Explicit Configuration Matters

GDSS is designed to be **Zero-Config by Default**: out of the box, it inspects your Git DAG, parses syntax trees across dozens of programming languages, and uses multi-tier fallbacks to guess model context windows and locate build descriptors.

However, in production repositories and team workflows, **explicit configuration in `.gdss.yml` is strongly recommended**. 

Committing a `.gdss.yml` to the root of your repository ensures that:
1. **Every Developer and CI Runner Shares Identical Settings**: No discrepancy between local laptop runs (`gdss suggest`) and GitHub Actions (`gdss audit-pr`).
2. **Context Budgets Are Exact**: The symbol condensation engine allocates up to 45% of your declared context window (up to 96,000 characters) for rich symbol implementations, caller/callee graphs, and commit histories.
3. **Agentic Self-Correction Bounds Are Defined**: You control exactly how many times the agent iterates against compiler and test traces before presenting a solution to humans.

---

## 🛡️ The Golden Rule: Avoid Unintended Fallbacks

GDSS includes a 3-tier dynamic discovery system for context window sizing:
- **Tier 1**: User configuration (`.gdss.yml` `context_window` or CLI `--context-window`).
- **Tier 2**: Dynamic discovery via provider API (`/models` or `/api/show`).
- **Tier 3**: Pattern matching heuristics (`gpt-4o` ➔ 128k, `claude-3` ➔ 200k, fallback ➔ 16k).

### Why You Should NOT Rely on Tier 2 or Tier 3 Fallbacks

| Risk with Fallbacks | What Happens in Practice | How Explicit `.gdss.yml` Solves It |
| :--- | :--- | :--- |
| **API Gateway Inconsistencies** | Custom enterprise proxies, Azure OpenAI, or self-hosted gateways frequently omit `context_length` from `/models` responses. | Setting `context_window` guarantees the exact token ceiling without querying gateway metadata. |
| **Conservative 16k Fallback** | If an unfamiliar or fine-tuned model name is used (e.g. `my-team-coder-v2`), Tier 3 defaults to a conservative 16,384 tokens, severely constricting the code symbol budget. | Explicit configuration unlocks the full 32k, 64k, or 128k+ capacity of your fine-tuned model. |
| **Unnecessary Latency** | Querying `/models` or `/api/show` introduces extra HTTP round trips on every CLI command or CI job. | Pre-configured values are resolved instantaneously in memory ($0\text{ ms}$ overhead). |
| **Unexpected Truncation** | Heuristic estimates can lead to unexpected ellipsis condensation (`/* ... N lines condensed ... */`) if a model's true window is larger than the heuristic. | Full functions, interfaces, and cross-file callers fit into the prompt cleanly. |

> [!IMPORTANT]
> **Always declare `model`, `context_window`, and `max_refinements` explicitly in `.gdss.yml`.** Do not let your CI pipeline rely on heuristic fallbacks or network discovery.

---

## 📋 Complete Production `.gdss.yml` Template

Copy and paste this template into `.gdss.yml` at the root of your repository:

```yaml
# .gdss.yml - GDSS Semantic Repository Intelligence Configuration
# Check this file into Git root so CI, CLI, and IDE agents share identical rules.

# ==============================================================================
# 1. AI Convergence & PR Collision Radar
# ==============================================================================
radar:
  # The model to invoke for semantic patch reconciliation
  # Examples: "gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "qwen2.5-coder:7b"
  model: "gpt-4o"

  # Explicit context window size in tokens (MANDATORY BEST PRACTICE)
  # Unlocks full code condensation budget without relying on heuristic fallbacks
  # - gpt-4o / o1 / o3: 128000
  # - claude-3-5-sonnet: 200000
  # - deepseek-coder: 64000
  # - qwen2.5-coder: 32768
  context_window: 128000

  # Inference provider backend
  # Options: "github" (GitHub Models via GITHUB_TOKEN), "openai", "openrouter", "ollama", "vllm"
  provider: "github"

  # Maximum agentic self-correction iterations when sandboxed validation fails
  # If the initial patch fails syntax, typecheck, or tests, the error trace is fed
  # back to the model up to this limit to iteratively heal the patch.
  # Default: 2 (Recommended: 2 or 3)
  max_refinements: 2

  # Collision risk cutoff score between 0.0 and 1.0 (Omega_ij)
  # Collisions at or above this threshold trigger alerts and suggestions
  # Default: 0.8 (Critical / High Risk)
  risk_threshold: 0.8

  # CI Merge Gate Behavior
  # - false: Informational mode (posts sticky radar comment with 1-click suggestions without blocking CI)
  # - true: Enforcing mode (fails CI check with exit code 1 if Omega_ij >= risk_threshold)
  fail_on_collision: false

# ==============================================================================
# 2. Ephemeral Sandbox Validation
# ==============================================================================
validation:
  # Command used for targeted unit test execution in ephemeral worktrees
  # {test_file} placeholder is automatically substituted with matching test files
  test_command: "pytest {test_file}"

  # Command used for static type verification in ephemeral worktrees
  typecheck_command: "mypy ."

  # Command used for custom linting or syntax checks
  syntax_command: "ruff check ."

  # Execution timeout in seconds for validation commands
  # Default: 30 (Use 60-120s for larger test suites)
  timeout_seconds: 45

# ==============================================================================
# 3. AST Parsing & Multi-Language Scanning
# ==============================================================================
ast:
  # Additional file extensions to track in collision radar and dependency graphs
  # Standard extensions (.py, .ts, .js, .go, .rs, .java, .c, .cpp, .cs, .rb, etc.)
  # are tracked automatically. Use this for web frameworks, templates, or DSLs.
  additional_extensions:
    - .vue
    - .svelte
    - .sol
    - .zig
```

---

## 🔍 Detailed Schema Reference

### 1. `radar` (AI Convergence & CI Radar)

| Directive | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `radar.model` | `string` | `"gpt-4o-mini"` | The exact model identifier dispatched for code reconciliation. |
| `radar.context_window` | `integer` | *Dynamic* | **Required best practice.** The exact context window capacity in tokens (e.g. `128000`). Precludes fallback guessing and optimizes the code condensation budget. |
| `radar.provider` | `string` | `"auto"` | Target provider: `"github"`, `"openai"`, `"openrouter"`, `"ollama"`, or `"vllm"`. |
| `radar.max_refinements` | `integer` | `2` | Number of automated self-correction retries inside the ephemeral sandbox worktree before halting. |
| `radar.risk_threshold` | `float` | `0.8` | Semantic interaction threshold ($\Omega_{ij} \in [0.0, 1.0]$) determining when a collision is flagged. |
| `radar.fail_on_collision` | `boolean` | `false` | When `true`, exits with status `1` on high-risk collisions to block PR merges until resolved. |

### 2. `validation` (Ephemeral Sandbox Worktrees)

| Directive | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `validation.test_command` | `string` | *Auto-detected* | Shell command to execute targeted regression tests. Supports `{test_file}` replacement. |
| `validation.typecheck_command` | `string` | *Auto-detected* | Shell command to execute static typechecking (`mypy`, `tsc --noEmit`, `cargo check`). |
| `validation.syntax_command` | `string` | *Auto-detected* | Shell command to execute syntax checks or linters. |
| `validation.timeout_seconds` | `integer` | `30` | Worktree execution timeout in seconds. Prevents hanging tests from stalling CI. |

### 3. `ast` (Multi-Language & DSL Tracking)

| Directive | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `ast.additional_extensions` | `list[str]` | `[]` | List of custom file extensions (e.g. `[.vue, .sol]`) mapped into symbol extraction. |

---

## 🛠 Provider-Specific Recipes

### A. GitHub Actions / GitHub Models (Default CI)
Uses repository-native `GITHUB_TOKEN` entitlements with zero third-party API accounts:

```yaml
radar:
  provider: "github"
  model: "gpt-4o"
  context_window: 128000
  max_refinements: 2
  fail_on_collision: false
```

### B. OpenAI Direct
Requires `OPENAI_API_KEY` set in developer environment or GitHub Secrets:

```yaml
radar:
  provider: "openai"
  model: "gpt-4o"
  context_window: 128000
  max_refinements: 3
  risk_threshold: 0.75
```

### C. OpenRouter (Multi-Model Gateway)
Requires `OPENAI_API_KEY` or `OPENROUTER_API_KEY` set to your OpenRouter secret:

```yaml
radar:
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"
  context_window: 200000
  max_refinements: 2
```

### D. Local Ollama (Offline Developer Workstation)
100% offline, zero cloud calls, zero token costs:

```yaml
radar:
  provider: "ollama"
  model: "qwen2.5-coder:7b"
  context_window: 32768
  max_refinements: 2
```

### E. Local or Private vLLM Cluster
High-throughput private inference on localhost or internal network:

```yaml
radar:
  provider: "vllm"
  model: "Qwen/Qwen2.5-Coder-7B-Instruct"
  context_window: 32768
  max_refinements: 2
```

---

## 🌟 What to Expect After Integration

Once `.gdss.yml` and the workflow `.github/workflows/gdss-radar.yml` are in place, the entire multi-branch intelligence pipeline activates automatically. Here is exactly what happens across your engineering workflows:

### 1. In Pull Requests (GitHub Actions CI)

When an engineer pushes a branch or opens a pull request:

```
[PR #42: Feature Billing] ───────┐
                                 ├─► GDSS Radar (CI)
[PR #41: Feature Auth]    ───────┘          │
                                            ▼
                           1. Pairwise Collision Tensor (Ω_42,41)
                           2. Developer Intent & Commit Ingestion
                           3. Ephemeral Sandbox Validation
                           4. Agentic Self-Correction Loop
                                            │
                                            ▼
                           Sticky Radar Comment on PR #42:
                           ┌──────────────────────────────────────────────┐
                           │ 🛰️ GDSS PR Collision Radar                   │
                           │ Status: ⚠️ Collision detected with PR #41   │
                           │ Topology: ⚡ Intersection on auth.py::login   │
                           │ Tested in ephemeral sandbox: syntax OK,      │
                           │ types OK (refined in 1 attempt)             │
                           │                                              │
                           │ ```suggestion                                │
                           │ def login(user, timeout=30, oauth=True): ... │
                           │ ```                                          │
                           │ [ Commit suggestion ]  <-- 1-Click Landing   │
                           └──────────────────────────────────────────────┘
```

#### Step-by-Step CI Execution Lifecycle:
1. **Concurrent PR Discovery**: Scans all open pull requests targeting `main`. Detects that PR #42 and PR #41 both touch `auth.py`.
2. **Developer Intent & Commit Pairing**:
   - Fetches PR #42 intent (*"Add timeout to login"*) and commit logs (`git log base..head`).
   - Fetches PR #41 intent (*"Add OAuth2 tokens"*) and commit logs.
   - Pairs intent with Tree-sitter AST nodes so the AI agent understands *why* changes occurred.
3. **Adaptive Context Window Budgeting**:
   - Reads `context_window: 128000` directly from `.gdss.yml`.
   - Allocates ~45% of the token window (~57,000 tokens / up to 96,000 characters) for the code block. Both implementations, surrounding callers, and method signatures fit without being condensed into ellipsis comments.
4. **Isolated Sandbox Verification**:
   - GDSS checks out an isolated, temporary Git worktree (`/tmp/gdss-sandbox-...`).
   - Evaluates the synthesized patch against multi-language AST syntax, `typecheck_command`, and `test_command`.
5. **Agentic Self-Correction Loop**:
   - If `mypy` detects a type mismatch (e.g. `timeout` passed as string instead of int), GDSS does **not** fail or post broken code.
   - It captures the error trace and invokes `refine_step`, asking the model to fix the exact type error.
   - If clean on attempt 1, it records `refined in 1 self-correction attempt(s)`.
6. **Sticky PR Comment & 1-Click Commit**:
   - Posts or updates the single sticky comment with an audited table, topology badge (`⚡ Intersection`), and native GitHub ` ```suggestion ` block.
   - Reviewers click **"Commit suggestion"** to immediately merge the reconciled patch directly in GitHub's web UI.

---

### 2. In Local Development (CLI)

Developers can run the exact same analysis locally before even pushing their branch:

```bash
# 1. Preview collision radar and intent prompts without making network calls
gdss suggest --repo . --ref main --as-prompt

# 2. Run local convergence with sandbox testing and agentic refinement
gdss suggest --repo . --ref main --validate --llm

# Output:
# Suggestion 1: modify_function on services/auth.py (Confidence: 0.95) (ID: sug_8f2a91c3)
# Rationale: Reconciles concurrent signature changes on login()
# Action: Merge signature timeout with OAuth token handler
#   ℹ Refined through 1 self-correction attempt(s)
#   - Strategy: compose [✓ Sandbox Validated]
#
# 3. Apply the verified patch safely to your working tree
gdss apply sug_8f2a91c3

# 4. Review changes with git diff, or rollback instantly if desired
git diff
gdss apply sug_8f2a91c3 --rollback
```

---

### 3. In IDEs (Cursor / Claude Code / Copilot MCP)

- Developers running Cursor or Claude Code connect to the local GDSS MCP server:
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
- IDE chat models call deterministic GDSS tools (`gdss_find_collisions`, `gdss_get_merge_order`, `gdss_validate_patch`) through stdio JSON-RPC 2.0 with **$0 token cost** to GDSS.
- The IDE model utilizes the developer's own chat session to display the collision radar and guide refactorings interactively.

---

## 🔒 Absolute Guarantees

1. **Zero Auto-Merge**: GDSS calculates, diagnoses, and proves; humans always make the decision to land code.
2. **Zero Proprietary Token Cost**: Runs on native repository GitHub entitlements or local workstations.
3. **Zero Untracked State**: Ephemeral worktrees are cleanly erased upon completion.
