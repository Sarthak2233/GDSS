# Product Specification: GDSS (Gate Distributive Semantic Synopsis)

**Subtitle:** Semantic Branch Intelligence & PR Collision Radar  
**Document Version:** 2.0.0  
**Status:** Approved for Implementation  
**Target:** Root Architecture & Pivot Roadmap  

---

## Problem Statement

Modern software engineering teams operating at velocity face severe coordination friction when multiple branches and pull requests evolve concurrently:

1. **Silent Semantic Collisions:** Standard Git detects merge conflicts strictly by textual overlap (lines of text). When Branch A changes a function's signature or contract (`process_payment(user, card, timeout=30)`), and Branch B introduces new callers to the old signature across three other files, Git reports a "clean merge" while CI or production silently breaks.
2. **Late Conflict Discovery:** Developers only discover collisions at merge time or after a rebase against `main`, forcing expensive, stressful context-switching and rework.
3. **Inference Cost & Privacy Traps:** Contemporary AI merge-assistants either indiscriminately dump entire codebases into expensive hosted LLMs (bleeding token costs and leaking private code) or require developers to maintain high-overhead local GPU servers (Ollama/vLLM) that cannot run in standard CI runners or across team fleets.
4. **Cognitive Overload in Monorepos & High-PR Teams:** When dozens of PRs are open simultaneously, engineering leads lack visibility into which branches interfere, what order they should be integrated in, and which changes can be deployed concurrently without risk.

---

## Solution

GDSS evolves from a theoretical differential-geometry exercise into a **pragmatic, production-ready Semantic Branch Intelligence and Merge Assistance Platform**.

GDSS sits as an intelligent layer above Git, combining:
1. **Deterministic Repository Intelligence:** Tree-sitter AST parsing, semantic transformation tracking (`ADD`, `RENAME`, `MODIFY`), and dependency call/import graph analysis to detect semantic collisions across branches before merge.
2. **Pairwise Branch Collision Radar ($\Omega$):** A real-time matrix calculating interference between all active branch pairs based on concrete structural overlap, broken callers, and non-commutative operations.
3. **Zero-Token-Cost Inference Architecture:**
   - **Interactive IDEs (Cursor, Claude Code, Copilot):** Exposed as a **Model Context Protocol (MCP)** tool server. The developer's own AI client powers the conversational reasoning; GDSS provides deterministic facts and diffs with **$0 token cost** to GDSS.
   - **Automated CI (GitHub Actions):** Leverages GitHub's built-in Copilot CLI/SDK with repo entitlements or user-configured API keys.
   - **Local Dev / Air-Gapped:** Retains optional local inference (Ollama/vLLM) for fully offline teams.
4. **Sandboxed Convergence Assistant:** Generates minimal, intent-preserving resolution patches and runs automated verification (syntax, typechecking, targeted unit tests) in isolated temporary worktrees before any human approval.

---

## User Stories

### Category 1: Branch Collision Detection & Radar
1. As a developer working on a feature branch, I want GDSS to alert me if another active branch modifies functions or classes I depend on, so that I can coordinate with my teammate before we both attempt to merge.
2. As a developer running `gdss status`, I want to see an immediate summary of semantic drift from the main branch, so that I know how far my branch has diverged architecturally.
3. As a developer running `gdss collisions`, I want to view a ranked list of branch pairs with high interference, so that I understand where the greatest integration risks lie.
4. As an engineering manager reviewing 20 open PRs, I want a collision matrix showing which PRs are independent vs. overlapping, so that I can safely fast-track independent PRs.
5. As a developer modifying an internal API, I want to see a list of downstream symbols affected across all open branches, so that I do not unknowingly break pending work.
6. As a team practicing trunk-based development, I want GDSS to detect when two branches edit disjoint lines in the same file that violate contract assumptions, so that we prevent silent runtime bugs.
7. As a developer, I want collision reports to provide human-readable explanations (e.g., "Branch A renamed `pay()` which Branch B calls in `checkout.py`") rather than raw mathematical tensor values, so that I can immediately act on the information.

### Category 2: Merge Order Optimization & Planning
8. As a release engineer preparing a staging integration, I want GDSS to recommend an optimal merge sequence that minimizes total integration friction, so that our deployment pipeline does not fail repeatedly on rebases.
9. As a developer managing stacked PRs, I want GDSS to identify commutative branch changes that can be integrated in any order, so that I do not spend time debating merge sequences unnecessarily.
10. As a tech lead, I want GDSS to explain the rationale behind a recommended merge order (e.g., "Merge DB migration in PR #12 first to satisfy schema requirements of PR #15"), so that our team can make informed merge decisions.
11. As a CI engineer, I want GDSS to identify completely disjoint branch subgraphs, so that our merge queue can bundle multiple PRs into a single speculative CI run safely.

### Category 3: Model Context Protocol (MCP) & Coding Agent Integration
12. As a Cursor user, I want GDSS running as an MCP server, so that I can ask Cursor's chat agent `@gdss analyze collisions` without configuring separate API keys.
13. As a Claude Code user, I want GDSS to expose read-only analysis tools (`gdss_find_collisions`, `gdss_get_symbol_impact`), so that Claude can inspect my repo's branch state with 100% deterministic accuracy.
14. As an MCP client user, I want tool calls to return compact, structured JSON evidence rather than unformatted chat logs, so that my coding agent's context window is preserved.
15. As a security-conscious engineer, I want the GDSS MCP server to be strictly read-only by default, so that an AI client cannot mutate my Git working tree without explicit user confirmation.
16. As a developer who pays for a personal Cursor/Copilot plan, I want GDSS to leverage my existing AI subscription for explanations, so that I am not double-billed for token usage.

### Category 4: Automated Pull Request & GitHub Actions Workflow
17. As a GitHub repository maintainer, I want a GDSS GitHub Action that triggers on PR events, so that every incoming pull request is automatically audited for semantic collisions against other open PRs.
18. As a PR reviewer, I want GDSS to post an informational sticky comment outlining affected symbols and shared dependencies, so that I know what integration tests need to be run.
19. As a developer whose PR conflicts with another open PR, I want the bot comment to mention the author of the conflicting PR, so that we can collaborate on a resolution early.
20. As a repository administrator, I want to configure risk thresholds in `.gdss.yml` that turn collision warnings into blocking CI checks only when critical architectural boundaries are violated.
21. As a team operating in GitHub Actions, I want GDSS to use the native `GITHUB_TOKEN` with Copilot CLI/Models permissions, so that we do not have to distribute proprietary third-party API keys to our CI environment.
22. As an open-source maintainer, I want PR collision checks on external forks to run in a safe, read-only mode without exposing secrets or write access, so that our CI remains secure.

### Category 5: AI-Assisted Resolution & Sandboxed Validation
23. As a developer facing a complex semantic collision, I want GDSS to generate a candidate resolution diff that preserves both branches' intents, so that I do not have to manually piece together disparate edits.
24. As a developer evaluating an AI-generated patch, I want GDSS to test the patch in an isolated temporary worktree before showing it to me, so that I am never presented with code that fails basic syntax or type checks.
25. As a developer reviewing a proposed patch, I want to see clear validation evidence (e.g., "AST parsed: OK; types: OK; 4 unit tests passed"), so that I know exactly how trustworthy the suggestion is.
26. As a developer, I want to review candidate patches through a side-by-side diff in my terminal or editor before applying, so that human control is strictly preserved.
27. As a developer, I want an explicit `apply` command that safely applies the validated patch to my working directory with automatic rollback capability if something goes wrong.
28. As a developer, I want GDSS to synthesize targeted regression tests that specifically exercise the overlapping boundary of the conflicting branches, so that our test suite permanently protects against future regressions.

### Category 6: Local & Privacy-Preserving Operations
29. As an offline developer on an airplane, I want all AST extraction, dependency analysis, collision ranking, and drift monitoring to run completely offline without an internet connection, so that my workflow is never interrupted.
30. As an enterprise developer working with proprietary source code, I want the option to connect GDSS to an on-premise Ollama or vLLM server, so that zero source code or metadata leaves our corporate firewall.
31. As a developer who does not have a local LLM or API key configured, I want the entire deterministic core of GDSS to remain 100% functional, so that I still get collision radar and impact analysis for free.

---

## Implementation Decisions

### 1. Jargon Demotion & Public Terminology Policy
* **Decision:** We establish a strict separation between **Internal Algorithmic Rigor** and **External Product Terminology**.
* **External Surface (CLI, Reports, UI, Docs):**
  - "Continuous manifold synchronizer" $\rightarrow$ **"Semantic Branch Intelligence & Collision Radar"**
  - "Conflict Tensor $\Omega_{ij}$" $\rightarrow$ **"Branch Collision Matrix" / "Interference Score"**
  - "Tangent vector $dC$ / Trajectory $\gamma(t)$" $\rightarrow$ **"Branch Deltas & Commit History"**
  - "Attractor trajectory" $\rightarrow$ **"Target / Base Branch" (`main` or `dev`)**
  - "Geodesic merge order" $\rightarrow$ **"Recommended Integration Sequence"**
* **Internal Codebase:** Retain mathematical constructs where they model exact discrete behavior ($[\mathcal{T}_i, \mathcal{T}_j] = 0$ for commutativity, $\Omega_{ij}$ for matrix index math, `OperatorType` for discrete transforms). Completely purge speculative continuous geometry (Ricci curvature, Christoffel symbols, smooth derivations on discrete ASTs).

### 2. Roadmap Restructuring: Freezing Theoretical Geometry
* **Decision:** Deprecate Phase 4a–4e (Riemannian metric $G$, parallel transport $P$, rank-$N$ octopus tensors) from the core product path.
* **Action:** Move them to an auxiliary research namespace (`Phase R: Geometric Research`). They will **never block** product releases or agent workflows.
* **The New Core Roadmap:**
  - **Phase A (Foundation):** AST parsing, operator algebra, code graph, embeddings (Status: **Done**).
  - **Phase B (Collision Radar):** Pairwise branch interaction matrix, affected symbol/caller reporting, deterministic risk scoring (Status: **Done**).
  - **Phase C (Convergence Assistant & Sandbox):** Provider-neutral AI adapter, laser-focused conflict prompts, temporary worktree patch validation, guarded local apply (Status: **Done**).
  - **Phase D (Delivery Interfaces):** MCP server implementation for Cursor/Claude/Copilot, followed by GitHub Actions PR audit workflow with 1-click commit suggestions (Status: **Done**).
  - **Phase E (Visual Dashboard UI):** Next.js 14 web dashboard with collision heatmaps, 3D constellation, and validation evidence (Status: **Active Priority**).
  - **Phase F (Bespoke IDE Extension):** Dedicated VS Code / Copilot extension (Status: **Deferred** until MCP adoption is proven).

### 3. Provider-Neutral, Zero-Token-Bleed Inference Architecture
* **Decision:** Decouple GDSS from hardcoded local-only servers (`localhost:8000` / `localhost:11434`).
* **Implementation:**
  - Maintain the existing `LLMProvider(Protocol)` interface.
  - Implement an `OpenAICompatibleProvider` supporting any OpenAI-spec endpoint:
    - GitHub Models (`https://models.inference.ai.azure.com`) via `GITHUB_TOKEN`
    - Hosted commercial APIs (OpenAI, Anthropic via adapter, Groq, OpenRouter)
    - Local self-hosted vLLM/Ollama
  - **Inference Ownership Rules:**
    1. **MCP Mode:** GDSS tools execute deterministically and return structured facts. The calling agent (Cursor/Copilot) pays for the conversation tokens. GDSS incurs zero cost.
    2. **CI Mode:** Uses GitHub Copilot CLI/Models with repo credentials or user-supplied API secrets.
    3. **CLI Mode:** Uses configured API key or local daemon if available; defaults gracefully to deterministic reports if no model is present.

### 4. Sandboxed Worktree Validation Architecture
* **Decision:** GDSS must never mutate the user's active Git working directory during patch evaluation.
* **Implementation:**
  - When evaluating an AI resolution patch, GDSS creates an ephemeral Git worktree (`git worktree add -d /tmp/gdss_sandbox_<id> <commit>`).
  - The patch is applied in the sandbox.
  - The validation suite runs in the sandbox:
    1. AST syntax check (ensures clean parse across languages)
    2. Linter / typechecker (if available)
    3. Targeted test execution (running only tests that import the affected symbols)
  - The sandbox is torn down atomically (`git worktree remove --force`).
  - Results are packaged into a structured `ValidationResult` containing stdout, exit codes, and passed/failed checks.

### 5. Architectural Invariants & Two-Brain Purity
* **Invariant 1:** The deterministic engine (`core`, `graph`, `watcher`, `conflict`, `mcp`) must never depend on or import the generative/assistive engine (`ai`).
* **Invariant 2:** The AI layer can never execute a merge, commit, push, or file overwrite autonomously. All generative outputs are proposals subject to human approval.
* **Invariant 3:** All persisted or API-visible state must be strictly metadata and diffs; no raw proprietary source code or PII is ever collected or transmitted.

---

## Testing Decisions

### What Makes a Good Test
- **External Behavior Over Implementation Details:** Tests must verify public outputs (e.g., "Given two branches modifying `user.py`, `detect_collisions()` reports `process_user` as an affected symbol"), not internal private loop indexes.
- **Real File & Git Operations:** Prefer real temporary Git repositories (`git.Repo.init(tmp_path)`) and real Tree-sitter parsing over brittle mocks.
- **Zero Network Flakiness:** All AI provider tests must use in-memory stubs (`StubProvider`) or recorded VCR cassettes; no live external network calls in CI test suites.

### Modules Tested
1. **`gdss.conflict` (Collision Radar):**
   - Pairwise $\Omega$ calculation with 2, 5, and 10 branches.
   - Non-commutative operator interference tests (rename vs. modify, delete vs. call).
   - Dependency impact propagation tests (verifying downstream callers are flagged).
2. **`gdss.mcp` (Tool Server):**
   - Protocol compliance test: tool registration, JSON schema serialization, request routing.
   - Idempotence and read-only safety checks.
3. **`gdss.ai` (Convergence & Providers):**
   - `OpenAICompatibleProvider` request formatting and error handling.
   - Ephemeral worktree lifecycle: creation, atomic patch application, syntax check, teardown.
   - Validation engine: catching invalid syntax in LLM-generated diffs.

---

## Out of Scope

1. **Automatic Merging:** GDSS will **never** automatically execute `git merge`, `git rebase`, or push to remote branches without explicit human invocation.
2. **Smooth Manifold Mathematics:** Computing Christoffel symbols, Ricci curvature tensors, or continuous geodesic flow equations on codebases is formally declared out of scope.
3. **General-Purpose Code Autocomplete / Chatbot:** GDSS will not compete with Cursor, Copilot, or Claude Code as a general code-generation assistant; its scope is strictly cross-branch semantic interaction and collision resolution.
4. **Hosting a Proprietary Foundation Model:** GDSS will not train or host a proprietary multi-billion parameter foundation model; it will remain provider-neutral.

---

## Further Notes

* **Immediate Next Action:** Align the repository state files (`AGENTS.md`, `.agents/rules/`, `harness/state/feature_list.json`) with this specification so that all development agents operate with unified context and clear priorities.
