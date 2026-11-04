# Implementation Plan: Phase 2 Schema Unification & Loader Consolidation

## Executive Summary

Following the completion of **Phase 1 (Immediate Critical Validation & Timeout Fixes)**, this plan outlines the architecture and execution steps for **Phase 2: Schema Unification & Loader Consolidation (P1)** as defined in [`docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md`](file:///home/sarakb/projects/GDSS/docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md).

Currently, four separate modules in GDSS independently read and parse `.gdss.yml` via raw `yaml.safe_load`:
- `gdss/core/ast_parser.py` (reads `ast.additional_extensions`)
- `gdss/drift/context.py` (reads `hierarchy`)
- `gdss/validation/discovery.py` (reads `validation`)
- `gdss/validation/pr_audit.py` (reads `radar` and `hierarchy`)

This fragmentation causes documented configuration keys (`ast.exclude_patterns`, `hierarchy.reference_branch`, `radar.base_url`, and custom migration paths) to be ignored or desynchronized across commands.

**Phase 2 Goal:** Centralize all repository configuration into a single authoritative module `gdss/core/config.py`, wire the dormant configuration keys (`ast.exclude_patterns`, `migrations.paths`, and `hierarchy` cascading defaults), and maintain 100% backward compatibility.

---

## Architectural Compliance & Invariants

1. **Two-Brain Purity Invariant**:
   - `gdss/core/config.py` lives in `gdss/core/` (Layer 4, deterministic core).
   - It **must never** import `gdss.ai` or `gdss.embeddings`.
   - Both the deterministic brain (`core`, `graph`, `drift`, `reducers`, `watcher`) and entrypoints/validation can import `gdss.core.config`.
2. **Layer Direction Invariant**:
   - `core` is Rank 4. Higher layers (`conflict`, `drift`, `ai`, `validation`, `cli`) may import `core`, but `core` never imports higher layers.
3. **Zero Token Bleed / BYOK Invariant**:
   - Configuration loading is 100% deterministic, offline, and free ($0 / 0 tokens).

---

## Proposed Changes

### 1. New Module: Authoritative Configuration Engine (`gdss/core/config.py`)

Create strongly-typed, immutable dataclasses representing the full `.gdss.yml` schema:

```python
@dataclass(frozen=True)
class RadarConfig:
    provider: str = "openrouter"
    model: str = "openrouter/free"
    base_url: str | None = None
    context_window: int = 128_000
    risk_threshold: float = 0.1
    max_refinements: int = 2
    concurrency_limit: int = 4
    condensation: str = "lossless"
    fail_on_collision: bool = False
    same_base_only: bool = True
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    target_bases: tuple[str, ...] = ()

@dataclass(frozen=True)
class ValidationConfig:
    test_command: str | None = None
    typecheck_command: str | None = None
    syntax_command: str | None = None
    install_command: str | None = None
    timeout_seconds: int = 30

@dataclass(frozen=True)
class HierarchyConfig:
    reference_branch: str = "main"
    priority_chain: tuple[str, ...] = ("main", "develop")
    same_base_only: bool = True
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    target_bases: tuple[str, ...] = ()

@dataclass(frozen=True)
class ASTConfig:
    additional_extensions: tuple[str, ...] = ()
    exclude_patterns: tuple[str, ...] = ()

@dataclass(frozen=True)
class MigrationsConfig:
    paths: tuple[str, ...] = ()

@dataclass(frozen=True)
class GDSSConfig:
    radar: RadarConfig = field(default_factory=RadarConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    hierarchy: HierarchyConfig = field(default_factory=HierarchyConfig)
    ast: ASTConfig = field(default_factory=ASTConfig)
    migrations: MigrationsConfig = field(default_factory=MigrationsConfig)
    raw_data: dict[str, Any] = field(default_factory=dict)
```

Implement `load_gdss_config(repo_root: Path | str | None = None) -> GDSSConfig`:
- Discovers `.gdss.yml` (falling back to `.gdss.yaml`).
- Safely parses and normalizes extensions (e.g. prefixing `.` if omitted).
- Applies clean fallbacks and defaults if config is absent or invalid.
- Provides helper `is_path_excluded(rel_path: str, exclude_patterns: Sequence[str]) -> bool` using `fnmatch`.

---

### 2. Backward-Compatible Consolidation in Existing Loaders

Refactor scattered loaders to delegate directly to `load_gdss_config`:

- **`gdss/core/ast_parser.py`**:
  `get_source_extensions(repo_root)` calls `load_gdss_config(repo_root).ast.additional_extensions`.
- **`gdss/drift/context.py`**:
  `_load_repo_hierarchy_config(repo_path)` calls `load_gdss_config(repo_path).hierarchy`.
- **`gdss/validation/discovery.py`**:
  `load_validation_config(repo_root)` delegates to `load_gdss_config(repo_root).validation`.
- **`gdss/validation/pr_audit.py`**:
  `load_radar_config(repo_path)` delegates to `load_gdss_config(repo_path)`.

---

### 3. Wire Dormant `ast.exclude_patterns` Filtering

- **`gdss/core/trajectory.py` (`extract_trajectory_operators`)**:
  - Accept `exclude_patterns: Sequence[str] = ()` (or load from `load_gdss_config(observer.repo.working_dir)`).
  - Filter out files matching `exclude_patterns` (e.g. `node_modules/**`, `dist/**`, `vendor/**`) before parsing ASTs or reducers.
- **`gdss/graph/graph_builder.py` (`build_code_graph`)**:
  - Filter out file paths and directories matching `load_gdss_config(root_path).ast.exclude_patterns`.

---

### 4. Wire Configurable Database Migration Paths (`migrations.paths`)

- **`gdss/reducers/migration_reducer.py` (`MigrationDAGReducer`)**:
  - Update `__init__(self, custom_paths: Sequence[str] | None = None)`.
  - In `can_handle(file_path, content)`:
    Check `custom_paths` in addition to default path segments (`**/migrations/**`, `_journal.json`, etc.).
- **`gdss/reducers/registry.py` (`DomainReducerRegistry`)**:
  - Pass configured `migrations.paths` from `GDSSConfig` into `MigrationDAGReducer`.

---

### 5. Wire Hierarchy Cascade & CLI Fallbacks

- **`gdss/cli/start.py` (`_resolve_candidate_branches`)**:
  - When `--reference` is not explicitly passed, consult `config.hierarchy.reference_branch`.
  - When branch filters are not overridden via CLI or runtime DB, apply `config.hierarchy.include` and `config.hierarchy.exclude`.
- **`gdss/cli/main.py` (`tensor`, `drift`, `suggest`)**:
  - Ensure all commands resolve parameters via `GDSSConfig` before falling back to hardcoded defaults.

---

## Verification Plan

### Automated Test Cases (`tests/core/test_config.py` & `tests/reducers/test_migration_reducer.py`)
1. **Config Loading**: Test loading from `.gdss.yml`, `.gdss.yaml`, missing config, and malformed syntax.
2. **Backward Compatibility**: Ensure `load_validation_config`, `load_radar_config`, and `_load_repo_hierarchy_config` return identical structures.
3. **AST Exclude Patterns**: Verify that `extract_trajectory_operators` and `build_code_graph` skip paths matching glob patterns (`dist/**`, `*.min.js`).
4. **Custom Migration Paths**: Verify that `MigrationDAGReducer` discovers migrations in non-standard paths (e.g. `src/db/custom_versions/001_init.py`).
5. **Hierarchy Defaults**: Verify CLI branch selection cascades from CLI flags $\to$ DB $\to$ `.gdss.yml` $\to$ default `main`.

### Full Gate Verification
Run `bash harness/verify.sh`:
- Layer 1: `ruff`, `mypy` (99+ files), `architecture_fitness.py` (2-brain purity), `dsa_fitness.py`.
- Layer 2: `pytest` (all unit & integration tests).
- Layer 3: CLI smoke & API smoke.
- Frontend: `verify-frontend.sh`.
