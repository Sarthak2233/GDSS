# Master Implementation Plan: Complete Resolution of Remaining Audit Report Phases & Backlog

> **Document Scope & Authority:**  
> This master plan consolidates **all remaining phases and backlogged items** from [`docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md`](docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md):
> - **Phase 3**: Worktree Dependency Lifecycle & Sandboxing (P1)
> - **Phase 4**: Monorepo & Multi-Package Intelligence (P2)
> - **Remaining Backlog Items**: `migrations.framework` (Matrix Item 26) & CLI Configuration Cascades
>
> **Core Guarantee**: Strict two-brain purity, 0 LLM token bleed (100% deterministic local/CI execution), and no auto-merges without human approval.

---

## 1. Backlog Inventory & Gap Analysis

Following the successful deployment and verification of **Phase 1 (Immediate P0 Fixes)** and **Phase 2 (Schema Unification P1)**, the remaining audit report items to be implemented are:

| Audit Phase / ID | Feature / Directive | Root Cause & Failure Mode | Proposed Resolution |
|---|---|---|---|
| **Phase 3.1** | `validation.install_command` | Ephemeral clean worktrees lack `node_modules` or `.venv`; implicit discovery fails with exit code 127 (`tsc: not found`). | Add `install_command` execution in `ValidationSandbox.validate_patch` post-checkout before type/test gates. |
| **Phase 3.2** | Worktree Dependency Symlinking | Re-running package installation in ephemeral worktrees is slow and heavy on local disk/network. | In `ephemeral_worktree`, automatically symlink existing parent `node_modules`, `.venv`, and `vendor` when package manifests are untouched. |
| **Phase 3.3** | `validation.mode` Toggle | Repositories cannot choose between targeted file testing vs full regression suite. | Add `mode: "targeted" \| "full_suite"` (default: `"targeted"`) to `ValidationConfig` and wire into `test_runner.py`. |
| **Phase 4.1** | Monorepo Subdirectory Manifests | `detect_test_command` and `detect_typecheck_command` inspect only repo root; monorepo packages (`web/`, `backend/`) silently bypass validation. | Integrate `find_project_root_for_file` and `group_files_by_package_root` to identify affected packages. |
| **Phase 4.2** | Package-Scoped Validation Execution | Multi-package patches execute in the wrong working directory, unable to find local tsconfig/pytest configs. | Execute typechecks and tests with `cwd=package_root`, formatting `{file}` relative to `package_root`. Aggregate per-package results. |
| **Phase 4.3** | Root `version` Schema Validation | Root `version: 1` key is treated as inert text with zero schema checking. | Add `version: int = 1` to `GDSSConfig` with forward-compatibility warning logs on invalid/unsupported versions. |
| **Backlog Item 26** | `migrations.framework` | Framework hint in `.gdss.yml` is never read by `MigrationDAGReducer`. | Add `framework: str \| None` to `MigrationsConfig` and wire into `MigrationDAGReducer` sniffer logic. |

---

## 2. Architecture & Execution Flow

```
                      Candidate Patch Application
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 3: Ephemeral Worktree Setup & Dependency Lifecycle            │
│ 1. git worktree add --detach <temp_dir> <base_ref>                  │
│ 2. Dependency Symlinking: If parent has node_modules/.venv and       │
│    manifests are untouched, symlink into worktree for instant speed │
│ 3. install_command: If defined in .gdss.yml, execute in worktree    │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Gate 1: Syntax & Linter Verification                                │
│ - Execute validation.syntax_command (if configured)                 │
│ - In-memory multi-language Tree-sitter AST parse on changed files   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Phase 4: Monorepo Package Grouping & Subdirectory Dispatch          │
│ group_files_by_package_root(worktree, changed_files)                │
│                                                                     │
│   ┌───────────────────────────────┐ ┌─────────────────────────────┐ │
│   │ Subpackage: web/              │ │ Subpackage: backend/        │ │
│   │ cwd: worktree/web             │ │ cwd: worktree/backend       │ │
│   │ - Typecheck (tsc --noEmit)    │ │ - Typecheck (mypy .)        │ │
│   │ - Tests (vitest / npm test)   │ │ - Tests (pytest)            │ │
│   └───────────────┬───────────────┘ └──────────────┬──────────────┘ │
│                   └───────────────┬────────────────┘                │
│                                   ▼                                 │
│                   Aggregate Results Across Packages                 │
│                   - Pass if all packages pass                       │
│                   - Fail if any package fails                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Implementation

### Component 1: Unified Configuration & Versioning (`gdss/core/config.py`)

1. **`GDSSConfig` Version Formalization**:
   - Add `version: int = 1` to `GDSSConfig`.
   - In `load_gdss_config`: Parse `data.get("version", 1)`. Validate that it is an integer. If unsupported (e.g., `version > 1` or non-integer), log:
     ```text
     Unsupported GDSS schema version %s. Supported version is 1. Parsing with best-effort compatibility.
     ```
2. **`ValidationConfig` Lifecycle Enhancements**:
   - Add `install_command: str | None = None`
   - Add `mode: str = "targeted"` (options: `"targeted"`, `"full_suite"`)
   - Add `symlink_dependencies: bool = True`
3. **`MigrationsConfig` Framework Hint**:
   - Add `framework: str | None = None` (e.g. `"alembic"`, `"django"`, `"prisma"`, `"drizzle"`, `"flyway"`, `"rails"`).
   - In `load_gdss_config`: Parse `m_data.get("framework")`.

---

### Component 2: Worktree Lifecycle & Symlinking (`gdss/validation/worktree.py`)

1. **Automatic Dependency Symlink Helper**:
   Implement `symlink_worktree_dependencies(parent_repo: Path, worktree_path: Path, manifest_modified: bool = False)`:
   - When `manifest_modified` is `False`, look for existing parent directories:
     - `node_modules/` $\to$ `worktree/node_modules`
     - `.venv/` $\to$ `worktree/.venv`
     - `vendor/` $\to$ `worktree/vendor`
     - Subdirectory dependencies: `web/node_modules/` $\to$ `worktree/web/node_modules`
   - Safely create symlinks (`os.symlink`) if the target does not already exist in the worktree.
2. **Lifecycle Integration**:
   - In `ephemeral_worktree`, provide clean cleanup of created symlinks before `git worktree remove`.

---

### Component 3: Validation Sandbox Pipeline (`gdss/validation/sandbox.py`)

1. **Execute `install_command` (Gate 0.5)**:
   - In `ValidationSandbox.validate_patch`, after `git apply` succeeds:
   - Check if `val_config.install_command` is configured.
   - If configured, run `subprocess.run(val_config.install_command, cwd=wt_str, timeout=effective_timeout)`.
   - If the installation fails, return `ValidationReport(status=ValidationStatus.FAILED_PATCH, error_summary=f"Install command failed: {output}")`.
2. **Fast-Path Symlink Invocation**:
   - If `val_config.symlink_dependencies` is True, invoke `symlink_worktree_dependencies(self.repo_path, wt_path, manifest_modified=...)`.

---

### Component 4: Monorepo Package Discovery (`gdss/validation/discovery.py`)

> [!IMPORTANT]
> **Monorepo Subdirectory Guarantee (Frontend + Backend Coexistence)**:
> In repositories containing both frontend (`web/`, `frontend/`, `client/`) and backend (`backend/`, `api/`, `services/*`), subdirectories **will never be excluded or skipped**. 
> - If a patch modifies `web/src/Button.tsx`, GDSS discovers `web/` and executes the frontend typecheck/test suite (`tsc`, `vitest`).
> - If a patch modifies `backend/app/auth.py`, GDSS discovers `backend/` and executes the backend suite (`mypy`, `pytest`).
> - If a patch touches **both** frontend and backend simultaneously, GDSS executes validation in **both subdirectories sequentially**, ensuring full end-to-end multi-service integrity. Both must pass.

1. **Implement `group_files_by_package_root`**:
   ```python
   def group_files_by_package_root(
       repo_root: Path,
       changed_files: Sequence[str] | None,
   ) -> dict[Path, list[str]]:
       """Group relative changed files by their nearest enclosing project descriptor directory.
       
       Returns mapping of {package_root_path: [file1, file2, ...]}.
       If no files or flat repository, returns {repo_root: list(changed_files or [])}.
       """
   ```
   - Uses `find_project_root_for_file` upward traversal.
   - Maps each changed file to its package root.

---

### Component 5: Package-Scoped Typechecking (`gdss/validation/typechecker.py`)

1. **Subdirectory Manifest Discovery in `detect_typecheck_command`**:
   - If root has no manifest, inspect package roots of `changed_files`.
2. **Package-Scoped Execution in `run_targeted_typecheck`**:
   - If root `custom_command` is provided, preserve single execution at `root`.
   - Otherwise, group `changed_files` with `group_files_by_package_root`.
   - For each `(pkg_root, pkg_files)`:
     - Detect typecheck command within `pkg_root`.
     - Substitute `{file}` with relative paths from `pkg_root`.
     - Execute subprocess with `cwd=str(pkg_root)`.
   - Aggregate `TypeCheckResult`:
     - `passed = all(r.passed for r in results)`
     - Combine error messages and tools across all packages.

---

### Component 6: Package-Scoped Test Execution & Mode Toggle (`gdss/validation/test_runner.py`)

1. **Subdirectory Manifest Discovery in `detect_test_command`**:
   - If root has no manifest, inspect package roots of `changed_files`.
2. **Package-Scoped Execution in `run_targeted_tests`**:
   - If root `custom_command` is provided, preserve single execution.
   - Otherwise, group `changed_files` with `group_files_by_package_root`.
   - Support `mode == "full_suite"`:
     - In `"full_suite"` mode, omit targeted `{test_file}` / `{file}` filtering and run the package's full test suite.
     - In `"targeted"` mode (default), filter by targeted test files.
   - For each package:
     - Execute with `cwd=str(pkg_root)`.
     - Handle Pytest exit code 5 per package.
   - Aggregate `TestExecutionResult`:
     - `tests_passed = sum(r.tests_passed for r in results)`
     - `tests_failed = sum(r.tests_failed for r in results)`
     - `passed = all(r.passed for r in results)`

---

### Component 7: Universal Stack-Agnostic Migration Reducer (`gdss/reducers/migration_reducer.py`)

> [!IMPORTANT]
> **Real-World Project Support (Zero-Stack-Lockin)**:
> Real-world projects use dozens of migration tools across diverse ecosystems (Knex, TypeORM, Sequelize, Liquibase, Golang-migrate, Goose, Atlas, GORM, Phinx, Hasura, Flyway, custom SQL patches). `MigrationDAGReducer` must never be restricted to a hardcoded set of 6 frameworks.

1. **Universal Multi-Stack Detection Hierarchy**:
   - **Tier 1 (Explicit Paths - Any Stack)**: Any file under paths configured in `migrations.paths` (e.g., `db/patches/**`, `database/changelogs/**`, `src/migrations/**`) is guaranteed to be handled by `MigrationDAGReducer`, regardless of file extension (`.sql`, `.ts`, `.js`, `.py`, `.go`, `.php`, `.xml`, `.yaml`).
   - **Tier 2 (Broad Directory Convention)**: Standardize matching for all common migration folder names: `migrations`, `migration`, `migrate`, `changelog`, `changelogs`, `versions`, `db/migrate`, `sql/patches`.
   - **Tier 3 (Universal File & Content Heuristics)**:
     - **Timestamp Migrations (Universal)**: Matches `(\d{10,14})` anywhere in the filename or parent directory (covers Rails, Prisma, TypeORM, Knex, Sequelize, Goose, GORM, Umzug).
     - **Sequential Migrations (Universal)**: Matches `^[vV]?(\d+)(?:__|_|\.|\b)` (covers Flyway, Golang-migrate, Liquibase, Django, plain SQL `001_*.sql`).
     - **Content Dependency Sniffing**: Inspects common comment headers (`-- depends_on:`, `-- parent:`, `-- requires:`, `down_revision`, `dependencies =`).
     - **Universal Fallback**: If a file is in a migration path but lacks an explicit DAG parent, extract the normalized file stem as a sequential step (`symbol_id=f"migration::step::{stem}"`). If two concurrent branches add a migration step, GDSS detects the concurrent database alteration collision!
2. **Framework Hint Extension (`migrations.framework`)**:
   - In `GDSSConfig.migrations`: parse optional `framework: str | None = None`.
   - If configured, provides priority to custom parser plugins (e.g. `alembic`, `django`, `liquibase`, `knex`, `typeorm`, `prisma`).

---

## 4. TDD Test Plan

### Test File 1: `tests/validation/test_worktree_dependency_lifecycle.py`
1. `test_sandbox_executes_install_command_success`: Verify `install_command` runs in `wt_path` and allows subsequent gates to pass.
2. `test_sandbox_install_command_failure_rejects_patch`: Verify non-zero exit in `install_command` fails validation with `FAILED_PATCH`.
3. `test_dependency_symlinking_creates_symlinks`: Verify `node_modules` and `.venv` are symlinked into the clean worktree when manifests are untouched.
4. `test_validation_mode_full_suite_vs_targeted`: Verify `"full_suite"` mode does not restrict test execution to changed files.

### Test File 2: `tests/validation/test_monorepo_validation.py`
1. `test_group_files_by_package_root`: Verify grouping across `web/` and `backend/`.
2. `test_monorepo_typechecker_executes_in_subpackage_cwd`: Verify `tsc` runs in `web/` when `web/tsconfig.json` exists and root has no manifest.
3. `test_monorepo_test_runner_executes_in_subpackage_cwd`: Verify `pytest` runs in `backend/` when `backend/pyproject.toml` exists.
4. `test_monorepo_multi_package_aggregate_reporting`: Verify that if one subpackage fails and another passes, the aggregate result reports failure with per-package outputs.
5. `test_package_scoped_file_substitution`: Verify `{file}` uses relative path from subpackage root.

### Test File 3: `tests/core/test_config_version_and_framework.py`
1. `test_root_version_default_and_parsing`: Verify `version: 1` parses and defaults to 1.
2. `test_root_version_unsupported_warning`: Verify invalid or future version logs warning and falls back safely.
3. `test_migrations_framework_hint_parsing`: Verify `migrations.framework: "alembic"` parses into `MigrationsConfig`.
4. `test_migration_reducer_respects_framework_hint`: Verify `MigrationDAGReducer` can handle non-standard directory paths when `framework="alembic"`.

---

## 5. Verification Gate (Definition of Done)

Following implementation, the complete three-layer verification gate must pass:
1. **Layer 1 (Static)**:
   - `ruff check .`
   - `mypy .` (all 100+ files clean)
   - `python harness/sensors/architecture_fitness.py` (layer direction and two-brain purity)
   - `python harness/sensors/dsa_fitness.py`
2. **Layer 2 (Runtime)**:
   - `pytest` (all existing 375+ tests + all new tests pass)
3. **Layer 3 (End-to-End)**:
   - `bash harness/sensors/cli_smoke.sh`
   - `bash harness/sensors/api_smoke.sh`
4. **Frontend Gate**:
   - `bash harness/verify-frontend.sh`
