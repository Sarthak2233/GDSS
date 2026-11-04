# Implementation Plan: Phase 1 Remediation of Configuration and Validation Layer Bugs

## Goal Description
Following the comprehensive audit in [`docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md`](docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md), this plan implements **Phase 1: Immediate Critical Fixes (P0)** to resolve the core defects in GDSS's validation sandbox, configuration loaders, and CLI options:
1. **Wire `syntax_command` into Gate 1 of `ValidationSandbox`**: Ensure user-configured linters (`ruff check .`, `eslint`, etc.) actually execute and gate candidate patches, rather than being parsed and ignored.
2. **Implement `{file}` placeholder substitution in `typechecker.py` and `test_runner.py`**: Enable targeted typechecking commands like `mypy {file}` and `javac {file}` to execute against the changed files instead of failing on the literal string `"{file}"`.
3. **Handle Pytest Exit Code 5 (no tests collected)**: Prevent false rejections of valid patches when targeted test execution finds no matching tests for modified symbols.
4. **Plumb `radar.concurrency_limit` and `radar.condensation` in `pr_audit.py`**: Enable GitHub Actions CI to respect configured parallel worker limits and condensation strategies from `.gdss.yml` instead of hardcoding defaults.
5. **Fix CLI Parameter Shadowing of `validation.timeout_seconds`**: Allow `gdss suggest` to inherit `.gdss.yml` timeout values when the `--sandbox-timeout` CLI option is omitted.
6. **Clean `.gdss.yml.example`**: Remove duplicate `model:` definitions, add `radar.base_url`, and add `validation.syntax_command`.

---

## User Review Required

> [!NOTE]
> All changes are strictly within the validation layer (`gdss/validation/`), CLI option handling (`gdss/cli/main.py`), and configuration examples. Deterministic AST core logic, commutativity algebra, and privacy invariants remain 100% untouched.

> [!IMPORTANT]
> **Syntax Check Gate Behavior**:
> In `ValidationSandbox.validate_patch`, Gate 1 will now execute `syntax_command` (if configured and non-empty) inside the ephemeral worktree. If `syntax_command` fails (exit code $\ne 0$), the patch fails with `ValidationStatus.FAILED_SYNTAX` and captures the linter output. If unconfigured or after the command passes, in-process Tree-sitter / AST parsing continues to run as a safety baseline.

---

## Proposed Changes

### Component: Validation Sandbox (`gdss/validation/`)

#### [MODIFY] `gdss/validation/sandbox.py`
- In `ValidationSandbox.__init__`: Load `ValidationConfig` via `load_validation_config(self.repo_path)` or allow passing a config.
- In Gate 1 (`validate_patch`):
  - Check if `config.syntax_command` is provided and non-empty (`cmd.strip() != ""`).
  - If provided, substitute `{file}` with changed files (or run across the worktree).
  - Execute the command via `subprocess.run` inside `wt_path` with `timeout=self.timeout_seconds`.
  - If the syntax command fails (returncode != 0), log and return `ValidationReport(status=ValidationStatus.FAILED_SYNTAX, error_summary=f"Syntax command failed: {output}", ...)`.
  - Also run `validate_file_syntax` on each changed file to ensure AST validity.

#### [MODIFY] `gdss/validation/typechecker.py`
- In `run_targeted_typecheck`:
  - Before executing `proc = subprocess.run(cmd, ...)`:
  - If `"{file}" in cmd`:
    - If `changed_files`: replace `"{file}"` with `" ".join(f'"{f}"' for f in changed_files)`
    - Else: replace `"{file}"` with `"."`

#### [MODIFY] `gdss/validation/test_runner.py`
- In `run_targeted_tests`:
  - Also support `"{file}"` in addition to `"{test_file}"`: replace `"{file}"` with changed files if present.
  - When evaluating `passed = proc.returncode == 0`:
    - Add check: `or (proc.returncode == 5 and ("pytest" in cmd.lower() or tool_name == "pytest"))`
    - In Pytest, exit code 5 means "no tests were collected". When this occurs, log an informational notice and treat it as passing rather than failing the patch.

#### [MODIFY] `gdss/validation/pr_audit.py`
- In `load_radar_config`:
  - Parse `concurrency_limit`: `int(radar_data.get("concurrency_limit", default_config.get("concurrency_limit", 4)))`
  - Parse `condensation`: `str(radar_data.get("condensation", default_config.get("condensation", "lossless")))`
  - Return both in the radar config dictionary.
- In `audit_pull_request`:
  - When creating `ConvergenceState(...)`:
  - Pass `concurrency_limit=int(config.get("concurrency_limit", 4))`
  - Pass `condensation_mode=str(config.get("condensation", "lossless"))`
  - Pass `sandbox_timeout=float(config.get("timeout_seconds", 30))` if `timeout_seconds` is in validation config.

---

### Component: CLI Interface (`gdss/cli/`)

#### [MODIFY] `gdss/cli/main.py`
- In `suggest`:
  - Change `sandbox_timeout: int = typer.Option(30, ...)` to `sandbox_timeout: int | None = typer.Option(None, ...)`.
  - When resolving the timeout for `get_suggestions`:
    ```python
    val_config = load_validation_config(repo)
    resolved_timeout = (
        float(sandbox_timeout)
        if sandbox_timeout is not None
        else float(val_config.timeout_seconds)
    )
    ```
  - Pass `resolved_timeout` to `get_suggestions(sandbox_timeout=resolved_timeout)`.

---

### Component: Configuration & Templates

#### [MODIFY] `.gdss.yml.example` and `gdss-radar/.gdss.yml.example`
- Remove the duplicate `model:` definition (keep only the recommended default `model: "openrouter/free"`).
- Add `radar.base_url` commented example for custom OpenAI-compatible endpoints.
- Add `radar.concurrency_limit: 4` and `radar.condensation: "lossless"`.
- Add `validation.syntax_command` example:
  ```yaml
  validation:
    # Optional custom syntax or linter command (e.g. "ruff check {file}" or "eslint {file}")
    # If omitted, GDSS runs built-in Tree-sitter AST syntax parsing.
    # syntax_command: "ruff check {file}"
  ```

---

### Component: Test Suite (`tests/validation/`)

#### [NEW] `tests/validation/test_validation_config_remediation.py`
- Test 1: `test_sandbox_executes_syntax_command_success_and_failure` (proves `syntax_command` is executed in `wt_path` and fails when linter returns error).
- Test 2: `test_typechecker_replaces_file_placeholder` (proves `mypy {file}` replaces `{file}` with actual file path rather than failing with literal `{file}`).
- Test 3: `test_pytest_exit_code_5_treated_as_passed` (proves exit code 5 from pytest is treated as `passed=True` with no tests collected notice).
- Test 4: `test_pr_audit_loads_concurrency_and_condensation` (proves `load_radar_config` extracts both keys from `.gdss.yml`).
- Test 5: `test_cli_suggest_inherits_validation_timeout_when_unspecified` (proves CLI uses `.gdss.yml` timeout when `--sandbox-timeout` is omitted).

---

## Verification Plan

### Automated Tests
1. **Unit tests for the new fixes**:
   ```bash
   .venv/bin/pytest tests/validation/test_validation_config_remediation.py -v
   ```
2. **Full test suite**:
   ```bash
   bash harness/sensors/run_tests.sh
   ```
3. **Full Three-Layer Verification Gate**:
   ```bash
   bash harness/verify.sh
   ```

### Manual Verification
- Run the 8 reproduction scripts from Section 4 of `docs/CONFIGURATION_VALIDATION_AUDIT_REPORT.md` to verify that the previously failing behaviors now succeed.
