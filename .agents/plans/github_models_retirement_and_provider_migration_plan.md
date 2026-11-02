# Plan: Purge Retired GitHub Models & Formalize Modern Provider Architecture

## 1. Executive Summary & Context

On **July 30, 2026**, GitHub officially shut down **GitHub Models**—including its AI model playground, model catalog, inference endpoints (`models.github.ai` and `models.inference.ai.azure.com`), and Bring-Your-Own-Key (BYOK) service ([GitHub Changelog Announcement](https://github.blog/changelog/2026-07-01-github-models-is-being-fully-retired-on-July-30-2026/)).

### Consequences for GDSS
1. **Dead Inference Endpoint**: Any request directed to `https://models.inference.ai.azure.com` fails with `HTTP 410 Gone` or `HTTP 404 Not Found`.
2. **Misleading Token Instructions**: Instructions prompting users to generate a GitHub Personal Access Token (`GH_MODELS_PAT`) for AI patch synthesis are defunct.
3. **Broken CI Default**: Defaulting `radar.provider: "github"` with runner `GITHUB_TOKEN` attempts to send completions to a non-existent endpoint.

### Primary Goals
1. **Document the Official Successor**: Detail the migration path for developers wanting to run models in the Microsoft/GitHub ecosystem (**Microsoft Azure AI Foundry**).
2. **Promote Zero-Cost Drop-In Alternatives for CI**: Establish **OpenRouter Free Tier** (`qwen/qwen-2.5-coder-32b-instruct`) and **Groq LPU** as the recommended zero-cost cloud providers, alongside **Local Ollama** for offline zero-cost development.
3. **Preserve Zero-Cost Deterministic Fallback**: Emphasize that GDSS operates with **$0 token cost** using its deterministic AST collision radar even when no AI key is provided.
4. **Codebase & Asset Cleansing**: Systematically purge outdated references, update provider routing logic in `gdss/ai/openai_provider.py`, update configuration defaults in `gdss/validation/pr_audit.py`, update test suites, docs, and SVG diagrams.

---

## 2. Model Provider Matrix & Replacement Strategy

| Provider | Status / Tier | Base URL | Auth Key | Recommended Model | Best Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Microsoft Azure AI Foundry** *(Official MS Successor)* | Enterprise / BYOK | `https://<resource>.openai.azure.com/openai/v1` | `AZURE_OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `phi-4` | Teams requiring Microsoft Azure compliance, data sovereignty, and SLA |
| **OpenRouter Free Tier** | Free ($0) | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `qwen/qwen-2.5-coder-32b-instruct` | Zero-cost CI in GitHub Actions, open-source repositories |
| **Groq LPU** | Fast Free Tier | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | Ultra-fast (< 2s) patch synthesis in CI |
| **Local Ollama** | Free ($0, Offline) | `http://localhost:11434/v1` | None required | `qwen2.5-coder:7b` | Offline local development, strict zero-data-leakage environments |
| **Deterministic Mode** | Free ($0 Compute) | N/A (No LLM) | None | N/A | Default CI collision radar, topology explanations, merge order recommendations |
| ~~**GitHub Models**~~ | **RETIRED (July 30, 2026)** | ~~`models.inference.ai.azure.com`~~ | ~~`GH_MODELS_PAT`~~ | *N/A (HTTP 410 Gone)* | *Decommissioned* |

---

## 3. Detailed Scope of Changes

```mermaid
flowchart TD
    subgraph Phase 1: Code & Provider Logic
        P1A["gdss/ai/openai_provider.py<br/>Remove dead endpoint default<br/>Add Azure AI Foundry support<br/>Add graceful retirement warning"]
        P1B["gdss/validation/pr_audit.py<br/>Default provider to openrouter/deterministic<br/>Decouple GITHUB_TOKEN from LLM calls"]
    end

    subgraph Phase 2: Test Suite
        P2A["tests/ai/test_openai_provider.py<br/>Remove tests asserting models.inference.ai.azure.com<br/>Add Azure AI & OpenRouter routing tests<br/>Test retirement warning behavior"]
        P2B["tests/validation/test_pr_audit.py<br/>Verify radar audit completes cleanly without LLM key"]
    end

    subgraph Phase 3: Documentation & Configs
        P3A["README.md & PRODUCT_SPEC.md<br/>Purge GitHub Models references<br/>Update zero-token CI narrative"]
        P3B["docs/CONFIGURATION_GUIDE.md<br/>Replace Recipe D with Azure AI Foundry<br/>Highlight OpenRouter Free Tier"]
        P3C["docs/GITHUB_ACTIONS_GUIDE.md & USER_GUIDE.md<br/>Clarify GITHUB_TOKEN vs OPENROUTER_API_KEY"]
        P3D[".gdss.yml.example & sync to gdss-radar/"]
    end

    subgraph Phase 4: Visual Assets
        P4A["Update 4 SVG Architecture Diagrams<br/>assets/ci/github_actions_flow.svg<br/>assets/product/ai_layer.svg<br/>assets/contributing/two_brain_architecture.svg<br/>assets/convergence/convergence_lifecycle.svg"]
    end

    Phase 1 --> Phase 2 --> Phase 3 --> Phase 4
```

### 3.1. Code Layer Changes

#### `gdss/ai/openai_provider.py`
- **Deprecate `https://models.inference.ai.azure.com`**:
  - Remove dead endpoint fallback when only `GITHUB_TOKEN` is present.
  - If a user configures `provider: "github"` or attempts to use `models.inference.ai.azure.com`, log an explicit warning:
    > `WARNING: GitHub Models (models.inference.ai.azure.com) was retired on July 30, 2026. GITHUB_TOKEN can no longer be used as an AI inference key. Please configure OPENROUTER_API_KEY, AZURE_OPENAI_API_KEY, or local Ollama.`
- **Add First-Class Microsoft Azure AI Foundry Support**:
  - Detect `AZURE_OPENAI_API_KEY` or `AZURE_OPENAI_ENDPOINT`.
  - Support standard Azure OpenAI `/openai/deployments/{deployment_id}/chat/completions` or serverless Foundry `/openai/v1/chat/completions`.
- **Sensible Provider Precedence**:
  1. Explicit `base_url` / `api_key` passed in constructor.
  2. `OPENROUTER_API_KEY` -> `https://openrouter.ai/api/v1` (Default model: `qwen/qwen-2.5-coder-32b-instruct`).
  3. `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_BASE_URL` -> Azure AI Foundry.
  4. `OPENAI_API_KEY` / `OPENAI_BASE_URL` -> `https://api.openai.com/v1` (Default model: `gpt-4o-mini`).
  5. `OLLAMA_HOST` -> `http://localhost:11434/v1`.

#### `gdss/validation/pr_audit.py`
- In `load_radar_config(repo_path)`:
  - Change default provider from `"github"` to `"openrouter"` (or `"deterministic"`).
  - Clarify that `context.github_token` is exclusively used for repository management (fetching PR metadata, reading PR files, posting sticky PR comments). It is never sent to an LLM provider as an authorization bearer unless explicitly mirrored by the user.

### 3.2. Test Suite Updates
- `tests/ai/test_openai_provider.py`:
  - Replace `test_openai_compatible_provider_defaults_to_github_models` with:
    - `test_openai_compatible_provider_azure_ai_foundry`: Validates Azure AI Foundry configuration.
    - `test_openai_compatible_provider_openrouter_defaults`: Validates OpenRouter base URL and headers (`HTTP-Referer`, `X-Title`).
    - `test_openai_compatible_provider_retired_github_models_warning`: Validates that referencing the retired endpoint emits the deprecation warning and handles gracefully.
- Re-run full test suite (`pytest`) ensuring 353+ tests pass.

### 3.3. Documentation Updates
1. **`README.md`**:
   - Update quickstart section: Replace GitHub Models examples with OpenRouter Free Tier and Azure AI Foundry.
   - Update CI section: State clearly that PR collision detection is 100% deterministic and free, and patch synthesis uses OpenRouter Free Tier or Azure AI Foundry.
2. **`docs/CONFIGURATION_GUIDE.md` & `gdss-radar/docs/CONFIGURATION_GUIDE.md`**:
   - Transform "Recipe D" from deprecated GitHub Models into **Recipe D: Microsoft Azure AI Foundry (Official MS Successor)**.
   - Expand **Recipe E: OpenRouter Free Tier (Zero-Cost CI)** with step-by-step GitHub Secrets configuration.
   - Update table of model providers and error troubleshooting codes (mentioning HTTP 410 Gone for the retired endpoint).
3. **`docs/GITHUB_ACTIONS_GUIDE.md`**:
   - Update workflow snippet:
     ```yaml
     - name: Run GDSS PR Collision Radar
       run: gdss audit-pr --repo .
       env:
         GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }} # strictly for PR comments & diffs
         OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }} # optional, for AI patches
     ```
4. **`docs/USER_GUIDE.md` & `docs/SUGGESTION_AND_CONVERGENCE_GUIDE.md`**:
   - Clarify the separation between the deterministic suggester (always active, $0) and probabilistic LLM synthesis.
5. **`PRODUCT_SPEC.md` & `docs/DISTRIBUTION_PLAN.md`**:
   - Update distribution and architectural sections describing zero-cost CI compute.

### 3.4. SVG Diagram Updates
Modify text elements in the following architectural SVGs to replace "GitHub Models" with "Azure AI / OpenRouter":
1. `assets/ci/github_actions_flow.svg`
2. `assets/product/ai_layer.svg`
3. `assets/contributing/two_brain_architecture.svg`
4. `assets/convergence/convergence_lifecycle.svg`

---

## 4. Verification Gate & Acceptance Criteria

To satisfy the **Three-Layer Validation Hierarchy** defined in `AGENTS.md`:

1. **Layer 1 - Static Analysis**:
   - `bash harness/sensors/lint.sh` (`ruff check .`) passes with 0 errors.
   - `bash harness/sensors/typecheck.sh` (`mypy gdss`) passes with 0 errors.
   - `python harness/sensors/architecture_fitness.py` passes (ensures Two-Brain purity: deterministic core never imports probabilistic layers).
2. **Layer 2 - Test Suite**:
   - `bash harness/sensors/run_tests.sh` passes all 353+ tests.
3. **Layer 3 - End-to-End CLI Smoke**:
   - `bash harness/sensors/cli_smoke.sh` passes without errors.
   - `gdss audit-pr --help` runs cleanly.

---

## 5. Next Steps

Upon your approval of this plan:
1. Update `gdss/ai/openai_provider.py` and `gdss/validation/pr_audit.py`.
2. Update unit tests in `tests/ai/test_openai_provider.py`.
3. Update documentation files (`README.md`, `docs/*.md`, `.gdss.yml.example`).
4. Update SVG assets.
5. Execute `bash harness/verify.sh` to confirm all validation sensors are green.
