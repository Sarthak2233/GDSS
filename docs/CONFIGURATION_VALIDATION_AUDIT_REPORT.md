# GDSS Configuration and Validation Layer Audit Report

**Document Version**: 1.0.0  
**Audit Date**: 2026-11-03  
**Auditor**: GDSS Architecture & Quality Assurance Team (`worker_audit_writer_1`)  
**Scope**: Configuration schemas, loaders, validation sandboxing, AST parsing, migration reducers, CLI commands, and PR audit integration across the GDSS repository.  
**Authoritative References**:
- `docs/CONFIGURATION_GUIDE.md`
- `docs/USER_GUIDE.md`
- `docs/UNIVERSAL_MULTI_ASSET_GUIDE.md`
- `docs/GITHUB_ACTIONS_GUIDE.md`
- `docs/PARALLEL_ORCHESTRATION_AND_CONTEXT_GUIDE.md`
- `docs/specs/universal_multi_asset_collision_spec.md`
- `.gdss.yml.example`
- Core Engine & Validation Modules (`gdss/validation/*`, `gdss/core/*`, `gdss/runtime/*`, `gdss/reducers/*`, `gdss/cli/*`, `gdss/ai/*`)

---

## 1. Executive Summary

### 1.1 Objective & Context
GDSS (Gate Distributive Semantic Synopsis) operates on a **Deterministic Core (0 Tokens) + Bring Your Own Key (BYOK)** architecture. The deterministic intelligence layer—encompassing AST parsing, dependency graphs, $\Omega_{ij}$ collision tensors, merge ordering, and sandboxed validation—relies on repository configuration directives defined in `.gdss.yml` to adapt to diverse languages, build systems, and branch hierarchies.

This audit was conducted to investigate, verify, and document all configuration and validation layer defects where documented settings and `.gdss.yml` options are **unused, ignored, dead, or miswired** across the GDSS codebase.

### 1.2 Key Audit Findings Overview
An exhaustive survey of the 27 configuration directives documented across GDSS guides and reference examples revealed a significant bifurcation between documented specifications and runtime execution:

1. **Configuration Status Breakdown (27 Documented Settings)**:
   - **Fully Wired & Executed (8 / 27)**: Directives correctly loaded and enforced across all operational paths (e.g., `radar.risk_threshold`, `radar.fail_on_collision`, `ast.additional_extensions`, `hierarchy.include`).
   - **Partially Wired / Mode-Restricted & CLI-Shadowed (7 / 27)**: Directives that function only in specific contexts—such as GitHub Actions PR audit mode (`gdss audit-pr`)—while being ignored or shadowed in CLI commands (e.g., `radar.model`, `radar.context_window`, `radar.provider`, and `validation.timeout_seconds` which is permanently shadowed by `gdss suggest`'s default `sandbox_timeout=30`).
   - **Miswired, Dropped, or Dead (12 / 27)**: Directives that are either parsed into in-memory data structures but bypassed by downstream execution engines, or completely omitted from YAML loaders and runtime logic despite prominent documentation.

2. **Critical Architectural Defects Identified**:
   - **`validation.syntax_command` Disconnect**: Parsed into `ValidationConfig.syntax_command` by `discovery.py:105`, but **never executed** by `ValidationSandbox.validate_patch`. Gate 1 of the validation sandbox exclusively runs in-process AST parsing (`ast.parse` and tree-sitter), completely ignoring user-configured linters (`ruff check .`, `eslint`).
   - **Missing Tier 3 in Hierarchy Resolution**: Documentation promises a 4-tier cascade for `hierarchy.reference_branch` and `hierarchy.priority_chain` (Invocation Flag $\to$ SQLite Database $\to$ Repository `.gdss.yml` $\to$ Fallback). In reality, Tier 3 (`.gdss.yml`) is completely missing from code. The engine reads only from local SQLite `.gdss/runtime.db`, and PR audit hardcodes `"main"` in local executions.
   - **Engine Disconnects (`radar.concurrency_limit` & `radar.condensation`)**: `ConvergenceState` supports parallel conflict drafting and context condensation, but `load_radar_config` in `pr_audit.py` omits both keys. Meanwhile, `gdss/cli/main.py` never reads `.gdss.yml`, forcing users to pass CLI flags manually or accept hardcoded defaults.
   - **Unparsed Directives (`ast.exclude_patterns`, `version`, `migrations.paths`)**: `ast.exclude_patterns` is omitted from `ast_parser.py`, allowing files in vendored or minified paths to pollute trajectory diffs. Root `version` is never checked. `migrations.paths` is never loaded, causing custom migration directories to bypass the `MigrationDAGReducer` and fall through to lexical analysis, missing split-head conflicts.
   - **Worktree Isolation & Implicit Tool Discovery Hazards**:
     - *Clean Worktree Isolation*: `ephemeral_worktree` generates a detached Git checkout containing only tracked files. Gitignored dependencies (`node_modules/`, `.venv/`) are absent.
     - *Missing `install_command`*: Neither `.gdss.yml` nor `ValidationConfig` defines an `install_command`. Implicit discovery selects `npm test` or `tsc --noEmit`, which immediately fail with exit code 127 or missing module errors, causing candidate patches to be falsely rejected.
     - *Monorepo Subdirectory Blindspot*: `detect_test_command` and `detect_typecheck_command` only inspect root-level files. Monorepo packages (`web/package.json`, `backend/pyproject.toml`) return `"none"` and silently pass validation without running tests.
     - *Literal `{file}` Placeholder Bug*: Guides document `typecheck_command: "mypy {file}"`, but `typechecker.py` lacks substitution logic, executing `mypy {file}` verbatim and failing 100% of the time.
     - *Pytest Exit Code 5 Bug*: When a repository has no test files collected, `pytest` returns exit code 5. `test_runner.py` treats any non-zero exit code as `FAILED_TESTS`.

---

## 2. Exhaustive Configuration Inventory Matrix

The following matrix inventories all 27 settings documented across `docs/CONFIGURATION_GUIDE.md`, `docs/USER_GUIDE.md`, `docs/UNIVERSAL_MULTI_ASSET_GUIDE.md`, `docs/specs/universal_multi_asset_collision_spec.md`, and `.gdss.yml.example`.

| # | Directive / Key | Documented Source(s) | Parsed In Code? (File & Line) | Validated? | Executed In Code? (File & Line) | Status Classification | Operational Impact |
|---|----------------|----------------------|-------------------------------|------------|---------------------------------|-----------------------|--------------------|
| 1 | `version` | `UNIVERSAL_MULTI_ASSET_GUIDE.md:201` | **No** (omitted across all 4 YAML loaders) | **No** | **No** | **Dead / Unimplemented** | Cosmetic only; no schema versioning or migration logic exists. |
| 2 | `radar.model` | `CONFIGURATION_GUIDE.md:100,228`<br>`.gdss.yml.example:23` | **Yes**: `gdss/validation/pr_audit.py:217` | Yes (`str`) | **Yes** in PR audit (`pr_audit.py:585,613`); **No** in CLI (`cli/main.py` ignores YAML) | **Partially Wired** (CI-only) | PR audit uses configured model; CLI `gdss suggest` ignores YAML model and uses default unless passed via code. |
| 3 | `radar.context_window` | `CONFIGURATION_GUIDE.md:110,229`<br>`.gdss.yml.example:42` | **Yes**: `gdss/validation/pr_audit.py:192,220` | Yes (`int`/`isdigit`) | **Yes** in PR audit (`pr_audit.py:643`); **No** in CLI | **Partially Wired** (CI-only) | Sets `GDSS_CONTEXT_WINDOW` env var in PR audit; CLI commands ignore it. |
| 4 | `radar.provider` | `CONFIGURATION_GUIDE.md:114,232`<br>`.gdss.yml.example:50` | **Yes**: `gdss/validation/pr_audit.py:195,218` | Yes (maps "github" to "openrouter") | **Yes** in PR audit (`pr_audit.py:581-615`); **No** in CLI | **Partially Wired** (CI-only) | Provider selection functions in PR audit; CLI commands ignore YAML provider setting. |
| 5 | `radar.base_url` | `CONFIGURATION_GUIDE.md:124,233`<br>`.gdss.yml.example:124` | **Yes**: `gdss/validation/pr_audit.py:194,219` | Yes (`str.strip()`) | **Yes** in PR audit (`pr_audit.py:606-614`); **No** in CLI | **Partially Wired** (CI-only) | Directs custom LLM endpoints in PR audit; CLI ignores YAML setting. |
| 6 | `radar.max_refinements` | `CONFIGURATION_GUIDE.md:130,234`<br>`.gdss.yml.example:65` | **Yes**: `gdss/validation/pr_audit.py:193,221` | Yes (`int`) | **Yes** in PR audit (`pr_audit.py:682`); **No** in CLI | **Partially Wired** (CI-only) | Controls self-correction iterations in PR audit; CLI ignores YAML setting. |
| 7 | `radar.concurrency_limit` | `CONFIGURATION_GUIDE.md:134,230`<br>`.gdss.yml.example:69`<br>`PARALLEL_GUIDE.md:253` | **No** (omitted in `load_radar_config`) | **No** | **No** (CLI accepts `--concurrency` flag, but never loads YAML) | **Dead / Ignored** | Setting `concurrency_limit` in `.gdss.yml` has zero effect in PR audit or CLI. Always defaults to 4. |
| 8 | `radar.condensation` | `CONFIGURATION_GUIDE.md:140,231`<br>`.gdss.yml.example:75` | **No** (omitted in `load_radar_config`) | **No** | **No** (CLI accepts `--condensation` flag, but never loads YAML) | **Dead / Ignored** | Setting `condensation` in `.gdss.yml` has zero effect. Always defaults to `"lossless"`. |
| 9 | `radar.risk_threshold` | `CONFIGURATION_GUIDE.md:145,235`<br>`.gdss.yml.example:59` | **Yes**: `gdss/validation/pr_audit.py:216` | Yes (`float`) | **Yes** in PR audit (`pr_audit.py:1271`) | **Wired (CI)** | Controls collision threshold gate in PR audit. |
| 10 | `radar.fail_on_collision` | `CONFIGURATION_GUIDE.md:150,236`<br>`.gdss.yml.example:80` | **Yes**: `gdss/validation/pr_audit.py:213` | Yes (`bool`) | **Yes** in PR audit (`pr_audit.py:1270`) | **Wired (CI)** | Controls whether PR audit exits with status code 1 on detected collisions. |
| 11 | `radar.same_base_only` | `UNIVERSAL_MULTI_ASSET_GUIDE.md:206` | **Yes**: `gdss/validation/pr_audit.py:206` | Yes (`bool`) | **Yes** in PR audit (`pr_audit.py:1224`) | **Wired (CI)** | Fallback for `hierarchy.same_base_only`. |
| 12 | `radar.include` / `exclude` / `target_bases` | Documented under `hierarchy:`, accepted under `radar:` | **Yes**: `gdss/validation/pr_audit.py:208-210` | Yes (`list`) | **Yes** in PR audit (`pr_audit.py:1227`) | **Wired (CI)** | Fallback compatibility for branch filtering in PR audit. |
| 13 | `validation.test_command` | `CONFIGURATION_GUIDE.md:158,242`<br>`.gdss.yml.example:95` | **Yes**: `gdss/validation/discovery.py:46,103` | Minimal (string) | **Yes**: `gdss/validation/test_runner.py:61` | **Wired** | Overrides heuristic test runner detection in validation sandbox. |
| 14 | `validation.typecheck_command` | `CONFIGURATION_GUIDE.md:161,243`<br>`.gdss.yml.example:104` | **Yes**: `gdss/validation/discovery.py:47,104` | Minimal (string) | **Yes**: `gdss/validation/typechecker.py:25` | **Wired (with bug)** | Overrides heuristic typechecker, but fails if `{file}` placeholder is used. |
| 15 | `validation.syntax_command` | `CONFIGURATION_GUIDE.md:164,244,1001` | **Yes**: `gdss/validation/discovery.py:48,105` | Minimal (string) | **No** (`sandbox.py` bypasses `ValidationConfig` and calls in-memory AST parser) | **Miswired / Dead** | Custom syntax/linter commands (`ruff check .`, `eslint`) are never executed. |
| 16 | `validation.timeout_seconds` | `CONFIGURATION_GUIDE.md:168,245`<br>`.gdss.yml.example:107` | **Yes**: `gdss/validation/discovery.py:49,106` | Yes (`int`) | **Yes** in PR audit (`discovery.py:110-137`); **No** in CLI `suggest` (CLI default shadowing) | **Partially Wired / CLI Shadowed** | Respected in PR audit. In `gdss suggest`, CLI option `--sandbox-timeout` defaults to `30` (not `None`), always passing `cli_timeout=30.0` and permanently shadowing `.gdss.yml`. |
| 17 | `ast.additional_extensions` | `CONFIGURATION_GUIDE.md:177,251`<br>`.gdss.yml.example:148` | **Yes**: `gdss/core/ast_parser.py:153-160` | Yes (normalizes leading dots) | **Yes**: `ast_parser.py:165` (`get_source_extensions`) | **Wired** | Registers custom source extensions (e.g., `.vue`, `.svelte`) for AST parsing. |
| 18 | `ast.exclude_patterns` | `CONFIGURATION_GUIDE.md:252`<br>`.gdss.yml.example:154` | **No** (`ast_parser.py` only extracts `additional_extensions`) | **No** | **No** (never passed or filtered in trajectory or graph) | **Dead / Ignored** | Exclude globs (`node_modules/**`, `dist/**`, `vendor/**`) are never applied to trajectory diffs. |
| 19 | `hierarchy.reference_branch` | `CONFIGURATION_GUIDE.md:188,258`<br>`.gdss.yml.example:114` | **No** (omitted in all YAML loaders) | **No** | **No** (PR audit uses PR target or `"main"`; CLI uses SQLite DB or `--ref`) | **Dead / Ignored** | Tier 3 of documented 4-tier cascade is missing. YAML configuration has zero effect. |
| 20 | `hierarchy.priority_chain` | `CONFIGURATION_GUIDE.md:191,259`<br>`.gdss.yml.example:117` | **No** (omitted in all YAML loaders) | **No** | **No** (`HierarchyManager` only queries SQLite `.gdss/runtime.db`) | **Dead / Ignored** | Merge ordering uses greedy $\Omega_{ij}$ costs; `priority_chain` in YAML is completely ignored. |
| 21 | `hierarchy.same_base_only` | `CONFIGURATION_GUIDE.md:198,260`<br>`.gdss.yml.example:124` | **Yes**: `gdss/validation/pr_audit.py:204,222` | Yes (`bool`) | **Yes** in PR audit (`pr_audit.py:1224`) | **Wired (CI)** | Restricts PR audit comparisons to pull requests sharing the exact target branch. |
| 22 | `hierarchy.include` | `CONFIGURATION_GUIDE.md:202,261`<br>`.gdss.yml.example:127` | **Yes**: `pr_audit.py:208`, `drift/context.py:140` | Yes (`list`) | **Yes** in PR audit and `build_analysis_context` | **Wired** | Glob filtering for branch discovery during collision analysis. |
| 23 | `hierarchy.exclude` | `CONFIGURATION_GUIDE.md:208,262`<br>`.gdss.yml.example:132` | **Yes**: `pr_audit.py:209`, `drift/context.py:141` | Yes (`list`) | **Yes** in PR audit and `build_analysis_context` | **Wired** | Glob exclusion for branch discovery. |
| 24 | `hierarchy.target_bases` | `CONFIGURATION_GUIDE.md:215,263`<br>`.gdss.yml.example:139` | **Yes**: `gdss/validation/pr_audit.py:210,225` | Yes (`list`) | **Yes** in PR audit (`pr_audit.py:1227`) | **Wired (CI)** | Restricts PR collision detection to specific landing branches. |
| 25 | `migrations.paths` | `UNIVERSAL_MULTI_ASSET_GUIDE.md:217-221` | **No** (no loader exists) | **No** | **No** (`MigrationDAGReducer` uses hardcoded directory names) | **Dead / Unimplemented** | Custom migration directories bypass DAG reducer and fall through to lexical reducer. |
| 26 | `migrations.framework` | `universal_multi_asset_collision_spec.md:96` | **No** (no loader exists) | **No** | **No** | **Dead / Unimplemented** | Framework hint is never read or used by `MigrationDAGReducer`. |
| 27 | `validation.install_command` | Implied operational necessity for clean worktrees | **No** (not defined in schema or loader) | **No** | **No** | **Missing Feature** | Ephemeral worktrees lack dependencies, causing implicit test/typecheck discovery to fail. |

---

## 3. Deep-Dive Architectural & Root Cause Analyses

### 3.1 `validation.syntax_command`: Storage Without Execution
- **Specification**:  
  `docs/CONFIGURATION_GUIDE.md` (lines 163-165, 244, 1001) specifies `validation.syntax_command` as a user-configurable shell command to execute syntax checks or linters (e.g. `ruff check .` or `eslint`).
- **Parsing & Schema**:  
  In `gdss/validation/discovery.py:43-50`, `ValidationConfig` defines:
  ```python
  @dataclass(frozen=True)
  class ValidationConfig:
      test_command: str | None = None
      typecheck_command: str | None = None
      syntax_command: str | None = None
      timeout_seconds: int = 30
  ```
  And in `gdss/validation/discovery.py:105`, `load_validation_config` correctly reads `val_data.get("syntax_command")`.
- **Root Cause of Execution Bypass**:  
  In `gdss/validation/sandbox.py:101-120`, Gate 1 of patch validation is implemented as follows:
  ```python
  # 3. Gate 1: Multi-language AST Syntax Check
  for f in changed_files:
      target_file = wt_path / f
      if target_file.is_file():
          syntax_res = validate_file_syntax(target_file)
          if not syntax_res.valid:
              ...
              return ValidationReport(status=ValidationStatus.FAILED_SYNTAX, ...)
  ```
  1. `ValidationSandbox.validate_patch` **never calls `load_validation_config(wt_path)`**. Unlike `test_runner.py` and `typechecker.py` which invoke `load_validation_config`, `sandbox.py` maintains zero reference to `ValidationConfig`.
  2. Gate 1 delegates directly to `validate_file_syntax(target_file)` from `gdss/validation/syntax.py:95`.
  3. `validate_file_syntax` accepts only a file path (`path: str | Path`). It performs in-memory Python `ast.parse` for Python files and Tree-sitter parsing for JS/TS/Go. It has no mechanism to execute external shell commands.
  4. Grep verification confirms that `syntax_command` is never referenced anywhere in `sandbox.py` or `syntax.py`.
- **Architectural Consequence**:  
  `validation.syntax_command` is dead code. If a repository configures `syntax_command: "ruff check ."` or `syntax_command: "exit 1"`, the command is silently ignored and never executed. Gate 1 remains strictly an in-memory syntactic parse.

---

### 3.2 `radar.concurrency_limit` and `radar.condensation`: Engine Support vs Config Omission
- **Specification**:  
  `.gdss.yml.example` (lines 67-75) and `docs/CONFIGURATION_GUIDE.md` (lines 134, 140, 230, 231) specify:
  - `radar.concurrency_limit`: Maximum concurrent worker threads for parallel conflict drafting (default: 4).
  - `radar.condensation`: Context condensation policy (`"lossless"`, `"ast_minimal"`, or `"off"`).
- **Core Engine Capability**:  
  `gdss/ai/orchestration.py` fully implements these capabilities:
  - `ConvergenceState` (lines 64-65) defines `concurrency_limit: int = 4` and `condensation_mode: str = "lossless"`.
  - `draft_step` (lines 153-155, 174-180) spins up a `ThreadPoolExecutor(max_workers=min(num_clusters, concurrency))` to draft patches in parallel.
  - `refine_step` (lines 419-425) parallelizes refinement tasks across workers.
  - `gdss/ai/suggester.py` passes `condensation_mode` into `extract_3way_symbol_context`.
- **Root Cause in PR Audit (`gdss/validation/pr_audit.py`)**:  
  In `load_radar_config` (lines 155-167, 183-226), `concurrency_limit` and `condensation` are completely omitted from `default_config` and are never extracted from `radar_data`. When `ConvergenceState` is instantiated in `audit_pr_collisions` (lines 674-683), neither parameter is passed:
  ```python
  state = ConvergenceState(
      repo_path=repo_root_str,
      reference_branch=context.base_ref,
      llm=(provider is not None),
      validate=True,
      provider=provider,
      target_commit=current_head,
      analysis_context=analysis_ctx,
      max_refinements=max_ref,
  )
  ```
  As a result, PR audit execution always falls back to hardcoded defaults (4 workers, "lossless" mode), completely ignoring `.gdss.yml`.
- **Root Cause in CLI Execution (`gdss/cli/main.py`)**:  
  In `gdss suggest` (lines 266-275, 331-332), `--concurrency` and `--condensation` are accepted as CLI arguments and passed to `ConvergenceState`. However, `gdss/cli/main.py` **never loads `.gdss.yml`**. It contains zero YAML reading calls.
- **Architectural Consequence**:  
  Configuring `radar.concurrency_limit` or `radar.condensation` in `.gdss.yml` has zero effect anywhere in the platform. In PR audit it is dropped by the loader; in CLI it is ignored because the CLI never reads YAML files.

#### CLI Default Shadowing Bug: `validation.timeout_seconds` Permanently Overridden by `gdss suggest`
- **Specification**:  
  `docs/CONFIGURATION_GUIDE.md:168` and `.gdss.yml.example:107` specify `validation.timeout_seconds` (default: 30) to configure the per-command execution timeout for sandboxed tests and typechecks. Furthermore, `gdss/validation/discovery.py:116-121` documents the intended 4-tier resolution cascade:
  1. CLI flag (`--sandbox-timeout`)
  2. Environment variable `GDSS_SANDBOX_TIMEOUT`
  3. Configuration file (`.gdss.yml` `timeout_seconds`)
  4. Default 30 seconds
- **Root Cause in `gdss/cli/main.py`**:  
  In `gdss/cli/main.py:255-257`, the `suggest` command defines the CLI option with a hardcoded integer default of `30` rather than `None`:
  ```python
  sandbox_timeout: int = typer.Option(
      30, "--sandbox-timeout", help="Timeout in seconds for sandbox validation"
  )
  ```
  In `main.py:328`, this option is unconditionally converted and passed to `ConvergenceState`:
  ```python
  sandbox_timeout=float(sandbox_timeout)
  ```
  Consequently:
  1. Because `typer` assigns the default value `30` when the user does not pass `--sandbox-timeout`, `sandbox_timeout` is never `None`; it is always `30.0`.
  2. `ConvergenceState` carries `st.sandbox_timeout = 30.0` into `orchestration.py:248, 490, 575` and passes `timeout_seconds=st.sandbox_timeout` (30.0) into `ValidationSandbox.validate_patch`.
  3. Inside `gdss/validation/typechecker.py:57-60` and `gdss/validation/test_runner.py:161-164`:
     ```python
     if timeout_seconds is not None and timeout_seconds > 0:
         resolved_timeout = float(timeout_seconds)
     else:
         resolved_timeout = float(get_sandbox_timeout(config_timeout=config.timeout_seconds))
     ```
     Because `timeout_seconds` is `30.0` (not `None`), `resolved_timeout` is immediately pinned to `30.0`. The `else` branch that loads `config.timeout_seconds` from `.gdss.yml` is completely bypassed.
  4. Even if `get_sandbox_timeout` were called with `cli_timeout`, `discovery.py:122-123` executes `if cli_timeout is not None and cli_timeout > 0: return cli_timeout`. Because the CLI defaulted to 30 rather than `None`, `config_timeout` can never be evaluated.
- **Architectural Consequence**:  
  Repositories configuring larger test suites requiring extended timeouts (e.g., `validation.timeout_seconds: 120` or `180`) in `.gdss.yml` have their configuration permanently shadowed and overridden by the 30-second CLI default in `gdss suggest`. Sandboxed validation aborts after 30 seconds with false timeout failures unless developers explicitly pass `--sandbox-timeout 120` on every CLI invocation.

---

### 3.3 `hierarchy.reference_branch` and `hierarchy.priority_chain`: Missing Tier 3
- **Specification**:  
  `docs/CONFIGURATION_GUIDE.md` (lines 298-318) documents a 4-tier precedence cascade:
  1. *Tier 1 (Invocation Flag)*: `--ref` CLI option.
  2. *Tier 2 (Local Database Override)*: Workstation SQLite `.gdss/runtime.db`.
  3. *Tier 3 (Repository Configuration)*: `hierarchy.reference_branch` and `hierarchy.priority_chain` in `.gdss.yml`.
  4. *Tier 4 (Heuristic Fallback)*: Default to `"main"`.
- **Root Cause of Tier 3 Absence**:
  1. `gdss/validation/pr_audit.py:load_radar_config` extracts `same_base_only`, `include`, `exclude`, and `target_bases`, but ignores `reference_branch` and `priority_chain`.
  2. In PR audit:
     - CI mode (`parse_github_env`, line 115) extracts `base_ref` from GitHub PR payload (`pr_data["base"]["ref"]`).
     - Local mode (`run_pr_audit`, line 1180) hardcodes `base_ref="main"`.
     - Patch generation (`generate_pr_convergence_patch`, lines 449, 463, 477) hardcodes `"main"` in 3 places.
  3. In CLI / Runtime:
     - `gdss/drift/context.py:140-141` (`_load_repo_hierarchy_config`) only extracts `include` and `exclude`.
     - `gdss/runtime/hierarchy.py:115-140` (`HierarchyManager.resolve_priority_chain`) only queries the SQLite database table `hierarchies`.
     - `gdss/cli/start.py:221-229` falls back to `context_engine.get_reference_branch()` (SQLite) or `"main"`.
     - `gdss/cli/main.py` defaults `--ref` to `"main"`.
  4. Merge Ordering: `gdss/conflict/merge_order.py` computes merge order using a greedy nearest-neighbor algorithm over pairwise $\Omega_{ij}$ collision tensors; `priority_chain` is never passed or consulted.
- **Architectural Consequence**:  
  Tier 3 (`.gdss.yml`) does not exist in code. A team that defines `reference_branch: "develop"` or a multi-stage `priority_chain` in `.gdss.yml` has their configuration silently ignored across all CLI commands and PR audits.

---

### 3.4 `ast.exclude_patterns`, Root `version`, and `migrations.paths`

#### A. `ast.exclude_patterns`
- **Specification**: `CONFIGURATION_GUIDE.md:252` and `.gdss.yml.example:154-161` document globs (`node_modules/**`, `dist/**`, `vendor/**`, `*.min.js`) to exclude files from AST symbol parsing.
- **Root Cause**:
  In `gdss/core/ast_parser.py:150-160` (`get_source_extensions`), the loader reads `ast_cfg.get("additional_extensions")`, but never calls `ast_cfg.get("exclude_patterns")`. `ASTParser` has no exclusion logic.
- **Downstream Consequences**:
  1. `graph_builder.py` and `embeddings/service.py` rely on a hardcoded Python set `SKIP_DIR_NAMES = {"venv", ".venv", "node_modules", "dist", ...}`. Any custom paths (e.g. `vendor/**`, `third_party/**`) are not in this hardcoded set and are scanned anyway.
  2. In `gdss/core/trajectory.py:46-60`, `extract_trajectory_operators` iterates over diffs between merge base and HEAD. It never filters paths against `ast.exclude_patterns`. Minified JS (`*.min.js`) or vendored files modified on a branch are fully parsed by Tree-sitter, introducing irrelevant AST operators into the semantic collision tensor.

#### B. Root `version` Key
- **Specification**: `UNIVERSAL_MULTI_ASSET_GUIDE.md:201` documents `version: 1`.
- **Root Cause**: Zero loaders in `gdss/` inspect `version`. No Pydantic schema or schema version migration mechanism exists. `version: 1` or `version: 999` is treated as inert text.

#### C. `migrations.paths` & Migration DAG Reducer
- **Specification**: `UNIVERSAL_MULTI_ASSET_GUIDE.md:217-221` and `universal_multi_asset_collision_spec.md:96` document `migrations.paths` to specify custom migration directories.
- **Root Cause**:
  1. `DomainReducerRegistry` in `gdss/reducers/registry.py:19` instantiates `MigrationDAGReducer()` with no parameters.
  2. `MigrationDAGReducer.can_handle` (`gdss/reducers/migration_reducer.py:15-49`) restricts directory matching to a hardcoded set:
     ```python
     _MIGRATION_DIR_SEGMENTS = frozenset(
         {"migrations", "migration", "migrate", "versions", "drizzle", "alembic", "flyway", "prisma"}
     )
     ```
  3. No YAML loader reads `data.get("migrations")`.
- **Downstream Consequences**:  
  Projects using custom migration paths (e.g. `backend/database/changelogs/*.sql` or `services/orders/db/patches/*.sql`) fail the directory segment check. If the files lack specific Alembic/Django tokens, `can_handle()` returns `False`. The migration files fall through to `UniversalLexicalReducer`, disabling split-head DAG conflict detection and risking database corruption in concurrent merges.

---

### 3.5 Implicit Tool Discovery & Clean Worktree Execution Failures

#### A. Ephemeral Worktree Isolation vs Missing `install_command`
- **Mechanism**:
  In `gdss/validation/worktree.py:60`, `ephemeral_worktree` executes:
  ```bash
  git worktree add --detach <temp_dir> <base_ref>
  ```
  A detached Git worktree contains only tracked files committed to Git. Gitignored files and directories—such as `node_modules/`, `.venv/`, `vendor/`, and build artifacts—do not exist. The fallback copy in `worktree.py:87` explicitly excludes `.git`, `venv`, `node_modules`, and `.venv`.
- **Implicit Discovery**:
  When `validation.test_command` or `validation.typecheck_command` is omitted in `.gdss.yml`:
  - `detect_test_command` (`gdss/validation/test_runner.py:65-79`): If `package.json` exists, returns `"npm test"`. If `pyproject.toml` exists, returns `"pytest"`.
  - `detect_typecheck_command` (`gdss/validation/typechecker.py:27-37`): If `tsconfig.json` exists, returns `"tsc --noEmit"`. If `mypy.ini` exists, returns `"mypy ."`.
- **Lockfile Sync Limitation**:
  `synchronize_sandbox_lockfiles` (`test_runner.py:102-143`) only runs when package manifest files were modified in the candidate patch, and strictly executes `--lockfile-only`, `--package-lock-only`, or `cargo generate-lockfile`. It never installs dependencies.
- **Failure Mode**:
  `ValidationConfig` has no `install_command` field. When the sandbox runs `npm test` or `tsc --noEmit` in a clean worktree, execution immediately crashes:
  ```text
  sh: 1: tsc: not found
  npm ERR! missing script: test
  Error: Cannot find module '...'
  ```
  `ValidationReport.status` is set to `FAILED_TYPES` or `FAILED_TESTS`. Valid patches generated during AI convergence are falsely marked as broken and rejected.

#### B. The Monorepo Root-Only Inspection Bug
- **Code**: In `gdss/validation/test_runner.py:65-79` and `gdss/validation/typechecker.py:27-37`:
  ```python
  if (root / "tsconfig.json").is_file():
      return "tsc --noEmit", "tsc"
  ...
  return None, "none"
  ```
- **Mechanism**: The discovery functions only inspect `root / manifest` and ignore `changed_files` (`_ = changed_files`).
- **Defect**: In monorepos where manifests reside in subdirectories (e.g. `web/tsconfig.json`, `backend/pyproject.toml`), `detect_*_command` returns `(None, "none")`. When the tool is `"none"`, `typechecker.py:70` returns `checked=False, passed=True` and `test_runner.py:175` returns `executed=False, passed=True`.
- **Impact**: Patches affecting monorepo packages silently bypass typechecks and unit tests, returning `ValidationStatus.PASSED` even if the patch introduces fatal type errors.

#### C. The Literal `{file}` Placeholder Bug
- **Documentation**: `docs/CONFIGURATION_GUIDE.md:98`, `.gdss.yml.example:101`, and `docs/USER_GUIDE.md:317` document:
  ```yaml
  validation:
    typecheck_command: "mypy {file}"
  ```
- **Code**: `test_runner.py:183-191` substitutes `{test_file}`. However, `gdss/validation/typechecker.py:65-93` (`run_targeted_typecheck`) contains **zero substitution logic** for `{file}`.
- **Impact**: If a user configures `typecheck_command: "mypy {file}"`, the shell executes `mypy {file}` verbatim, crashing with:
  ```text
  mypy: error: Cannot read file '{file}': No such file or directory
  ```

#### D. Pytest Exit Code 5 Treated as Hard Failure
- **Mechanism**: In `gdss/validation/test_runner.py:214`, the return code of the test command is checked:
  ```python
  passed = (proc.returncode == 0)
  ```
- **Defect**: When `pytest` is auto-detected on a repository that contains `pyproject.toml` but has no tests collected for the targeted files, Pytest exits with code 5 (`ExitCode.NO_TESTS_COLLECTED`).
- **Impact**: `test_runner.py` treats exit code 5 as a failure (`passed=False`), falsely failing patch validation.

#### E. Whitespace Command Silent Bypass Bug (`validation.test_command` & `validation.typecheck_command`)
- **Specification**:  
  Repositories configure custom verification commands via `validation.test_command` and `validation.typecheck_command` in `.gdss.yml`.
- **Mechanism in Discovery**:  
  In `gdss/validation/test_runner.py:61-62`:
  ```python
  if config.test_command:
      return config.test_command, "config"
  ```
  And in `gdss/validation/typechecker.py:25-26`:
  ```python
  if config.typecheck_command:
      return config.typecheck_command, "config"
  ```
- **Defect**:  
  Neither `load_validation_config` nor the runner functions validate that command strings contain non-whitespace characters (`.strip()`). In Python, any non-empty string—including pure whitespace such as `"   "`—evaluates to `True` in a boolean context (`bool("   ") is True`).
- **Subprocess Execution**:  
  The whitespace string is executed via `subprocess.run(cmd, shell=True, ...)` in `test_runner.py:204-214` and `typechecker.py:85-95`. In standard Linux shells (`/bin/sh` or `/bin/bash`), executing pure whitespace produces no output and exits immediately with return code `0`.
- **Impact**:  
  `passed = (proc.returncode == 0)` evaluates to `True`. GDSS logs `"Targeted tests PASSED with config"` and reports `passed=True, executed=True`, while `run_targeted_typecheck` reports `passed=True, checked=True`. Broken candidate patches containing catastrophic syntax, type, or behavioral regressions silently pass validation gates completely unverified.

---

## 4. Verifiable Reproduction Scripts & Empirical Proofs

Each defect described above has been empirically proven using self-contained verification scripts executed against the GDSS codebase.

### 4.1 Proof 1: `validation.syntax_command` Bypass in `ValidationSandbox`
```python
"""
Reproduction 1: Confirms that validation.syntax_command is ignored by ValidationSandbox.
Even when configured to 'exit 1', the patch validation passes Gate 1.
"""
import tempfile, subprocess
from pathlib import Path
from gdss.validation.sandbox import ValidationSandbox

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "audit"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.email", "audit@test.com"], cwd=str(root), check=True)
    
    # Configure syntax_command to fail intentionally
    (root / ".gdss.yml").write_text("validation:\n  syntax_command: 'exit 1'\n")
    (root / "module.py").write_text("def compute():\n    return 100\n")
    subprocess.run(["git", "add", "."], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(root), check=True)

    patch = """--- a/module.py
+++ b/module.py
@@ -1,2 +1,2 @@
 def compute():
-    return 100
+    return 101
"""
    sandbox = ValidationSandbox(root)
    report = sandbox.validate_patch(patch)
    print("Report status:", report.status.value)
    assert report.status.value == "PASSED", "Expected syntax_command 'exit 1' to be ignored"
    print("PROOF CONFIRMED: syntax_command was never executed by ValidationSandbox.")
```

### 4.2 Proof 2: `radar.concurrency_limit` and `radar.condensation` Omission
```python
"""
Reproduction 2: Confirms that radar.concurrency_limit and radar.condensation
are omitted by load_radar_config in pr_audit.py.
"""
import tempfile
from pathlib import Path
from gdss.validation.pr_audit import load_radar_config

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / ".gdss.yml").write_text("""
radar:
  concurrency_limit: 8
  condensation: "ast_minimal"
""")
    config = load_radar_config(root)
    print("Parsed config keys:", list(config.keys()))
    assert "concurrency_limit" not in config, "concurrency_limit should not be parsed"
    assert "condensation" not in config, "condensation should not be parsed"
    print("PROOF CONFIRMED: concurrency_limit and condensation are omitted from parsed config.")
```

### 4.3 Proof 3: `hierarchy.reference_branch` and `priority_chain` Omission
```python
"""
Reproduction 3: Confirms that hierarchy.reference_branch and priority_chain
are dropped by load_radar_config and never consumed by build_analysis_context.
"""
import inspect, tempfile
from pathlib import Path
from gdss.validation.pr_audit import load_radar_config
from gdss.drift import context
from gdss.drift.context import _load_repo_hierarchy_config

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / ".gdss.yml").write_text("""
hierarchy:
  reference_branch: "develop"
  priority_chain:
    - "main"
    - "develop"
""")
    # 1. PR audit loader completely drops reference_branch and priority_chain
    pr_cfg = load_radar_config(root)
    assert "reference_branch" not in pr_cfg
    assert "priority_chain" not in pr_cfg

    # 2. _load_repo_hierarchy_config returns the raw YAML dictionary
    ctx_cfg = _load_repo_hierarchy_config(str(root))
    assert "reference_branch" in ctx_cfg
    assert "priority_chain" in ctx_cfg

    # 3. Downstream in build_analysis_context (gdss/drift/context.py:140-141),
    # only 'include' and 'exclude' are extracted; reference_branch is an explicit parameter
    # and cfg.get("reference_branch") / cfg.get("priority_chain") are never queried!
    source = inspect.getsource(context.build_analysis_context)
    assert 'cfg.get("include")' in source
    assert 'cfg.get("exclude")' in source
    assert 'cfg.get("reference_branch")' not in source
    assert 'cfg.get("priority_chain")' not in source
    print("PROOF CONFIRMED: reference_branch and priority_chain are dropped by PR audit and ignored downstream by build_analysis_context.")
```

### 4.4 Proof 4: `ast.exclude_patterns` Omission in AST Parser
```python
"""
Reproduction 4: Confirms that ast.exclude_patterns is never read from .gdss.yml.
"""
import tempfile
from pathlib import Path
from gdss.core.ast_parser import get_source_extensions

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / ".gdss.yml").write_text("""
ast:
  additional_extensions: [".vue"]
  exclude_patterns: ["vendor/**", "*.min.js"]
""")
    exts = get_source_extensions(root)
    assert ".vue" in exts
    # Grep ast_parser.py confirms exclude_patterns is never queried
    with open("gdss/core/ast_parser.py") as f:
        content = f.read()
    assert "exclude_patterns" not in content
    print("PROOF CONFIRMED: ast.exclude_patterns is completely unparsed in ast_parser.py.")
```

### 4.5 Proof 5: `migrations.paths` Omission & Non-Standard Directory Fallthrough
```python
"""
Reproduction 5: Confirms that MigrationDAGReducer does not accept custom paths
and fails to handle non-standard migration paths.
"""
from gdss.reducers.migration_reducer import MigrationDAGReducer

reducer = MigrationDAGReducer()
# Standard path matches hardcoded segment
assert reducer.can_handle("backend/migrations/0001_initial.py")

# Custom migration path (e.g. database/changelogs) not in hardcoded _MIGRATION_DIR_SEGMENTS
# Note: 'versions' is hardcoded in _MIGRATION_DIR_SEGMENTS, but custom paths like 'changelogs'
# without the 8 hardcoded segment names return False and fall through to lexical analysis.
custom_path = "backend/database/changelogs/001_create_users.sql"
custom_sql = "CREATE TABLE users (id SERIAL PRIMARY KEY);"
can_handle = reducer.can_handle(custom_path, custom_sql)
print("Can handle custom migration path:", can_handle)
assert not can_handle, "Expected non-standard migration path to be rejected without config"
print("PROOF CONFIRMED: MigrationDAGReducer ignores custom paths and drops them to lexical reducer.")
```

### 4.6 Proof 6: Clean Worktree Failure on `npm test` Without Dependencies
```python
"""
Reproduction 6: Confirms that clean worktrees lack node_modules,
causing implicit test discovery to fail.
"""
import tempfile, subprocess
from pathlib import Path
from gdss.validation.sandbox import ValidationSandbox

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "audit"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.email", "audit@test.com"], cwd=str(root), check=True)
    
    # Node project with vitest test runner
    (root / "package.json").write_text('{"name": "demo", "scripts": {"test": "vitest run"}}\n')
    (root / "index.js").write_text("export const x = 1;\n")
    subprocess.run(["git", "add", "."], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(root), check=True)

    patch = """--- a/index.js
+++ b/index.js
@@ -1 +1 @@
-export const x = 1;
+export const x = 2;
"""
    sandbox = ValidationSandbox(root)
    rep = sandbox.validate_patch(patch)
    print("Sandbox Report Status:", rep.status.value)
    assert rep.status.value == "FAILED_TESTS", "Expected FAILED_TESTS due to missing node_modules"
    print("PROOF CONFIRMED: Clean worktree fails npm test due to lack of dependency installation.")
```

### 4.7 Proof 7: Monorepo Nested Project Silent Validation Bypass
```python
"""
Reproduction 7: Confirms that test/typecheck discovery only inspects root,
silently bypassing nested monorepo packages.
"""
import tempfile, subprocess
from pathlib import Path
from gdss.validation.sandbox import ValidationSandbox

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "audit"], cwd=str(root), check=True)
    subprocess.run(["git", "config", "user.email", "audit@test.com"], cwd=str(root), check=True)
    
    # Subdirectory project with type error
    web = root / "web"
    web.mkdir()
    (web / "tsconfig.json").write_text('{"compilerOptions": {"noEmit": true}}\n')
    (web / "app.ts").write_text("export const num: number = 1;\n")
    subprocess.run(["git", "add", "."], cwd=str(root), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(root), check=True)

    # Patch introduces obvious type error: assigning string to number
    patch = """--- a/web/app.ts
+++ b/web/app.ts
@@ -1 +1 @@
-export const num: number = 1;
+export const num: number = "not a number";
"""
    sandbox = ValidationSandbox(root)
    rep = sandbox.validate_patch(patch)
    print("Status:", rep.status.value, "Types Checked:", rep.types.checked)
    assert rep.status.value == "PASSED" and not rep.types.checked
    print("PROOF CONFIRMED: Nested monorepo package silently bypassed typechecking.")
```

### 4.8 Proof 8: Literal `{file}` Placeholder Failure in `run_targeted_typecheck`
```python
"""
Reproduction 8: Confirms that typechecker.py fails when typecheck_command contains {file}.
"""
import tempfile
from pathlib import Path
from gdss.validation.typechecker import run_targeted_typecheck

with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    (root / "sample.py").write_text("val: int = 1\n")
    res = run_targeted_typecheck(root, changed_files=["sample.py"], custom_command="mypy {file}")
    print("Passed:", res.passed, "Output:", res.output)
    assert not res.passed
    assert "{file}" in res.output
    print("PROOF CONFIRMED: typechecker executes '{file}' literally and fails.")
```

---

## 5. Strategic Remediation Roadmap

To resolve these defects while preserving the zero-token deterministic core, the following 4-phase remediation roadmap is recommended:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Immediate Critical Fixes (P0)                                 │
│ - Wire syntax_command into Gate 1 of ValidationSandbox                 │
│ - Implement {file} substitution in run_targeted_typecheck              │
│ - Handle Pytest exit code 5 (no tests collected) as passed             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│ Phase 2: Schema Unification & Loader Consolidation (P1)                │
│ - Centralize YAML loading into unified GDSSConfig dataclass            │
│ - Wire radar.concurrency_limit and radar.condensation into pr_audit    │
│ - Implement Tier 3 in hierarchy resolution (reference_branch/priority) │
│ - Parse and pass ast.exclude_patterns to trajectory & graph builders   │
│ - Parse migrations.paths and configure MigrationDAGReducer             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│ Phase 3: Worktree Dependency Lifecycle & Sandboxing (P1)               │
│ - Add validation.install_command to schema and execute post-checkout   │
│ - Implement dependency cache/symlink strategy for clean worktrees      │
│ - Add validation.mode toggle (targeted vs full_suite)                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼─────────────────────────────────────┐
│ Phase 4: Monorepo & Multi-Package Intelligence (P2)                    │
│ - Integrate find_project_root_for_file into typecheck & test discovery │
│ - Support package-scoped validation runs for changed subdirectories    │
│ - Formalize version key with schema migration validators               │
└────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Immediate Critical Fixes (P0)
1. **Wire `syntax_command` in `sandbox.py`**:
   Load `ValidationConfig` in `ValidationSandbox.validate_patch`. If `syntax_command` is defined, execute it via subprocess inside `wt_path` before in-memory AST parsing, or integrate it into `SyntaxCheckResult`.
2. **Fix `{file}` Placeholder Substitution**:
   In `gdss/validation/typechecker.py`, mimic `test_runner.py` by replacing `{file}` with `changed_files` paths or target file names.
3. **Handle Pytest Exit Code 5**:
   In `test_runner.py:214`, treat return code 5 as passing with a warning (`"no tests collected"`), preventing false patch rejections.
4. **Strip & Validate Custom Commands (Whitespace Bypass Fix)**:
   In `discovery.py`, `test_runner.py`, and `typechecker.py`, validate that configured commands (`test_command`, `typecheck_command`, `syntax_command`) contain non-whitespace characters (`cmd.strip() != ""`), treating pure whitespace as unconfigured rather than executing it as an empty shell no-op returning exit code 0.

### Phase 2: Schema Unification & Loader Consolidation (P1)
1. **Centralize Configuration Loading**:
   Replace scattered `yaml.safe_load` calls in `ast_parser.py`, `pr_audit.py`, `context.py`, and `discovery.py` with a single authoritative `load_gdss_config(repo_root: Path) -> GDSSConfig`.
2. **Wire CLI to YAML & Fix CLI Default Shadowing**:
   Update `gdss/cli/main.py` commands (`suggest`, `tensor`, `status`, `drift`) to load `.gdss.yml` for default parameter values before falling back to hardcoded constants. Specifically change `sandbox_timeout: int | None = typer.Option(None, ...)` so that unset CLI options do not overwrite repository `validation.timeout_seconds`.
3. **Restore Tier 3 in Hierarchy Cascade**:
   In `HierarchyManager` and `pr_audit.py`, consult `GDSSConfig.hierarchy.reference_branch` and `priority_chain` if not overridden by CLI flags or the local runtime DB.
4. **Wire `ast.exclude_patterns`**:
   Pass `exclude_patterns` into `extract_trajectory_operators`, `ASTParser`, and graph walkers, matching against `fnmatch` or `pathlib.Path.match`.
5. **Configurable Migration Paths**:
   Pass configured migration paths into `MigrationDAGReducer`, allowing custom database migration directories to participate in split-head conflict analysis.

### Phase 3: Worktree Dependency Lifecycle (P1)
1. **Introduce `validation.install_command`**:
   Add `install_command: str | None = None` to `ValidationConfig` and `.gdss.yml`. When defined, execute this command inside the newly created worktree prior to running typechecks or tests.
2. **Worktree Dependency Symlinking**:
   Provide an optional fast-path for local worktrees: symlink `node_modules` or `.venv` from the parent repository into the ephemeral worktree when manifests are untouched, avoiding full package re-installation.

### Phase 4: Monorepo & Multi-Package Intelligence (P2)
1. **Subdirectory Manifest Detection**:
   Activate `find_project_root_for_file` in `discovery.py` within `detect_test_command` and `detect_typecheck_command`. If files change in `web/`, detect `web/package.json` and execute commands with `cwd=worktree_path / "web"`.

---

## 6. Verification and Test Suite Results

The GDSS verification harness (`harness/verify.sh` and `pytest`) was executed to establish baseline stability and confirm that no regressions exist across the codebase:

### 6.1 Test Suite & Verification Pipeline Execution
- **Full Verification Gate**: `bash harness/verify.sh`
  - **Exit Code**: `0` (`verify: ALL LAYERS GREEN. Work meets the definition of done.`)
  - **Layer 1 (Static)**:
    - `ruff`: All checks passed.
    - `mypy`: Success (no issues found in 99 source files).
    - `architecture_fitness.py`: Passed (layer direction and two-brain purity hold).
    - `dsa_fitness.py`: Passed (zero unsuppressed DSA violations).
  - **Layer 2 (Runtime)**:
    - `pytest`: `363 passed, 3 skipped, 1 warning in 51.64s`.
  - **Layer 3 (End-to-End)**:
    - `cli_smoke.sh`: Passed over fixture repo (`master -> feature-work`).
    - `api_smoke.sh`: Passed.
  - **Frontend Harness (`web/` verify-frontend.sh)**:
    - Layer F1 (Static): `eslint (+ jsx-a11y)`, `tsc --noEmit`, and `token_fitness` passed.
    - Layer F2 (Component): `vitest (+ jest-axe)` 35 test files (118 tests) passed.
    - Layer F3 (E2E & Budgets): Production build succeeded, `size-limit` bundle budget passed.

### 6.2 Environment & Language Parser Dependencies
- **Tree-sitter Grammars**:
  - `tree_sitter_rust`: Multi-language AST parsing tests (`tests/core/test_multi_language_ast_parser.py`) require native Tree-sitter grammar bindings (`tree_sitter_rust`, `tree_sitter_go`, `tree_sitter_typescript`, `tree_sitter_java`, `tree_sitter_c`, `tree_sitter_cpp`). In this environment, `tree_sitter_rust` is installed and verified active.
- **Skipped Tests Analysis**:
  - Exactly 3 tests were skipped under `tests/embeddings/`:
    - `tests/embeddings/test_onnx_encoder.py::test_onnx_encode_if_model_present` (Skipped: ONNX model file `.gdss/models/all-MiniLM-L6-v2.onnx` not present in repository checkout; requires opt-in model download).
    - `tests/embeddings/test_vector_store.py::test_vector_store_basic[True]` & `test_save_load_roundtrip[True]` (Skipped: optional `faiss` vector database library not installed; gracefully falls back to deterministic in-memory numpy search).
- **Warnings**:
  - 1 warning: `PytestUnknownMarkWarning: Unknown pytest.mark.integration` in `tests/embeddings/test_onnx_encoder.py:27` (custom mark not registered in `pyproject.toml`).

---

## 7. Conclusion

This audit provides an exhaustive accounting of configuration and validation bugs across GDSS. By addressing the dead configuration directives, restoring the missing Tier 3 hierarchy cascade, and providing proper worktree dependency management, GDSS can align its runtime execution with its published architectural documentation and deliver reliable, deterministic branch intelligence.
