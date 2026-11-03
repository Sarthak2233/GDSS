# Implementation Plan: Clarify "Deterministic Core (0 Tokens) + Bring Your Own Key (BYOK)" Across Documentation & Rules

## 1. Executive Summary & Problem Definition

### The Problem
Throughout the documentation and codebase rules, the phrase **"Zero Token Bleed"** or **"$0 Tokens"** has been used to describe GDSS's operational architecture. While this was intended to mean *"GDSS the platform hosts no paid LLM servers and incurs $0 token liability"*, it causes serious confusion for end-users, team leads, and developers:
- Users may mistakenly believe GDSS provides **free hosted AI inference** or magical zero-cost LLM code synthesis without needing any credentials.
- Integrating teams are confused about **who pays for tokens**, **where API keys must be configured**, and **whether every developer needs an individual key in their GitHub account**.

### The Reality & Solution
GDSS operates on a clean two-layer model:
1. **Deterministic Algorithmic Core (100% Free, 0 Tokens, CPU-Only):**
   - Repository AST parsing, dependency graph extraction, symbol impact analysis.
   - Pairwise PR collision tensor ($\Omega_{ij}$), trajectory drift tracking, topological optimal merge ordering.
   - Sandboxed verification in ephemeral worktrees (syntax checking, type checking, test suites).
   - **Cost:** **Literal $0 and 0 tokens**. Runs purely on CPU. **Requires no API key of any kind**. Any team can run the full collision radar in CI without an LLM.
2. **AI Convergence Assistant (Strict Bring Your Own Key / Bring Your Own Compute — BYOK / BYOC):**
   - Natural-language collision explanations and auto-synthesized reconciliation patches.
   - GDSS **does not** host, proxy, subsidize, or charge markups on LLM inference.
   - Integrating teams and developers **bring their own keys or models**:
     - **In GitHub Actions (CI):** The repository administrator adds their team's key (e.g. `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, or `AZURE_OPENAI_API_KEY`) **once** in GitHub Repository Secrets (`Settings > Secrets and variables > Actions`). Individual team members opening PRs do **not** need separate keys.
     - **In IDEs (MCP Server via Cursor, Claude Code, VS Code Copilot):** Developers connect GDSS as an MCP tool server. The developer's own IDE client/subscription powers the chat; GDSS serves deterministic inspection tools over `stdio` ($0 tokens to GDSS).
     - **In Local CLI:** Offline and deterministic by default. For AI patches, developers export their own personal key (`export OPENAI_API_KEY=...`) or point to local free compute (Ollama, vLLM, llama.cpp).
     - **Zero Cloud Proxies:** Source code and ASTs are never sent to GDSS servers; API calls go directly from the user's runner/machine to their chosen provider.

---

## 2. Answers to Team Integration Questions

| Question | Architectural Answer |
| :--- | :--- |
| **Is only `.github/workflows/gdss-radar.yml` needed in `.github`?** | **Yes.** A single workflow file triggers on `pull_request` (`opened`, `synchronize`, `reopened`) and executes `sarthak2233/gdss-radar@v1`. |
| **Is `.gdss.yml` needed at the repo root?** | **Optional, but strongly recommended.** If omitted, GDSS uses sensible defaults (`threshold: 0.1`, deterministic mode). If present, it centralizes thresholds, test commands (`pnpm test`), and AI provider choices (`provider: "openai"`, `model: "gpt-4o"`). |
| **Do team members need separate API keys in their personal GitHub accounts?** | **No.** In GitHub Actions, secrets are set **at the repository level** (`Settings > Secrets and variables > Actions > Repository secrets`) by the repository maintainer. When any developer opens a PR, GitHub Actions automatically passes the repository's secret to the runner. Developers do not touch or manage keys in GitHub. |
| **When do developers use their own credentials?** | Only when working **locally**: (1) Inside their IDE (Cursor/Claude Code), their IDE subscription covers chat reasoning; (2) In their local terminal, if they choose to run `gdss suggest --llm`, they supply their own environment variable or local Ollama. |

---

## 3. Standardized Terminology Shift

Across all documentation, guides, diagrams, and rules, we will systematically replace confusing phrasing:

| Old / Ambiguous Phrasing | New Standardized Terminology | Meaning to User |
| :--- | :--- | :--- |
| `Zero Token Bleed` | **Deterministic Algorithmic Core (0 Tokens)** + **Bring Your Own Key (BYOK) AI** | Deterministic analysis uses 0 tokens; AI features require your own key. |
| `$0 API Cost & Zero Token Bleed Core` | **100% Free Deterministic Core ($0 & 0 Tokens)** | AST and collision tensor run on CPU for free. |
| `Zero Token Bleed Guarantee` (in MCP) | **Zero-Inference MCP Tool Server (0 GDSS Tokens)** | GDSS provides local tools; your IDE subscription powers the chat. |
| `Zero Token Bleed Lockfile Reconciliation` | **Deterministic Native Lockfile Reconciliation** | Package managers run natively in ephemeral worktrees without LLM hallucination. |
| `Zero Proprietary Token Cost` | **Strict BYOK / BYOC (Zero Token Markups or Hosted LLM Costs)** | GDSS does not sell or host LLMs; you connect directly to your own provider. |

---

## 4. Proposed Changes Across Target Files

### 4.1 Internal Rules & Architecture
1. **`AGENTS.md`**:
   - Update section heading `Deployment & Inference Architecture (Zero Token Bleed)` to `Deployment & Inference Architecture (Deterministic Core + BYOK)`.
   - Explicitly define the two tiers: Deterministic Core (0 tokens, CPU-only) and AI Convergence (Bring Your Own Key / BYOC).
2. **`.agents/rules/00-gdss-context.md`**:
   - Update `Zero-Token-Bleed Inference` section to reflect `Deterministic Core (0 Tokens) + Bring Your Own Key (BYOK)`.

### 4.2 Root Documentation (`docs/`, `README.md`, `CONTRIBUTING.md`)
1. **`README.md`**:
   - Update architecture badges: `Deterministic Core: 0 Tokens` and `AI Convergence: Bring Your Own Key (BYOK)`.
   - Update Architecture section: Make the distinction between deterministic CPU operations ($0/0 tokens) and BYOK AI convergence unmistakable.
2. **`docs/CONFIGURATION_GUIDE.md`**:
   - Update credentials matrix: add a prominent section **"Team Secrets in GitHub Actions vs. Individual Developer Credentials"**.
   - Clarify the MCP section: explain why MCP tools require 0 tokens/keys while the IDE chat uses the developer's IDE account.
3. **`docs/GITHUB_ACTIONS_GUIDE.md`**:
   - Add a dedicated subsection: **"Credential Setup & The BYOK Model"**.
   - Show how repository administrators configure `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in GitHub Secrets.
   - Clarify that individual PR authors do not need personal keys.
   - Show how the workflow behaves with zero keys (100% deterministic collision radar) vs. with an API key (auto-synthesizing AI patches).
4. **`docs/STANDALONE_BINARY_AND_MCP_GUIDE.md`**:
   - Update section `## 🛡️ Privacy & Zero Token Bleed ($0 Cost)` to `## 🛡️ Privacy, Deterministic Core ($0 Tokens) & BYOK Model`.
   - Detail how MCP provides deterministic tools without requiring an API key.
5. **`docs/SUGGESTION_AND_CONVERGENCE_GUIDE.md`**:
   - Update section title and text to reflect the BYOK model.
6. **`docs/UNIVERSAL_MULTI_ASSET_GUIDE.md`**:
   - Update callout note on native lockfile reconciliation.
7. **`CONTRIBUTING.md`**:
   - Clarify the MCP zero-inference invariant.

### 4.3 Public Action Repository (`gdss-radar/`)
1. **`gdss-radar/README.md`**:
   - Update badges: Change `Core-Deterministic $0 Tokens` to include explicit BYOK badge or link.
   - Update Section 1: `### 1. 💰 Deterministic Algorithmic Core ($0 & 0 Tokens)`.
   - Update Section 2: `### 2. 🤖 Bring Your Own Key (BYOK) AI Convergence`.
   - Add a callout box in Section 2:
     > **💡 How Team Credentials Work:**  
     > The repository administrator adds the API key (e.g., `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, or `OPENROUTER_API_KEY`) **once** in GitHub Repository Secrets. Team members opening PRs do **not** need separate API keys. If no key is configured, GDSS runs purely in deterministic mode ($0 tokens, 0 keys) and generates full collision matrices and merge orders without AI text generation.
   - Update Section `## 🛡️ Privacy, Deterministic Core & Bring Your Own Key (BYOK)`.
2. **`gdss-radar/action.yml`**:
   - Add helpful comments on how `env:` forwards repo secrets (e.g. `OPENAI_API_KEY`, `OPENROUTER_API_KEY`) to the runner.
3. **`gdss-radar/docs/`**:
   - Synchronize all updated guide files (`CONFIGURATION_GUIDE.md`, `GITHUB_ACTIONS_GUIDE.md`, `STANDALONE_BINARY_AND_MCP_GUIDE.md`, `UNIVERSAL_MULTI_ASSET_GUIDE.md`).

---

## 5. Verification & Acceptance Criteria

1. **Linting & Boundaries:**
   - Run `bash harness/sensors/lint.sh` to ensure Python and Markdown integrity.
   - Run `python harness/sensors/architecture_fitness.py` to ensure boundary purity.
2. **Terminology Consistency:**
   - Run `grep -rn "Zero Token Bleed" .` to confirm that every occurrence has either been clarified into the explicit "Deterministic Core (0 Tokens) + BYOK" formulation or updated with proper context.
3. **Git Cleanliness:**
   - Commit changes cleanly in `GDSS` and push to remote.
   - Commit synchronized documentation in `gdss-radar` and push to remote.

---

## 6. Feedback & Proceed
Please review this plan. Upon your approval, we will proceed to execute the documentation and rules updates across both repositories.
