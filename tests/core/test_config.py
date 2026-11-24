"""Tests for Phase 2: Schema Unification & Loader Consolidation."""

from __future__ import annotations

from pathlib import Path

from gdss.core.ast_parser import get_source_extensions
from gdss.core.config import (
    GDSSConfig,
    is_path_excluded,
    load_gdss_config,
)
from gdss.drift.context import _load_repo_hierarchy_config
from gdss.reducers.migration_reducer import MigrationDAGReducer
from gdss.validation.discovery import load_validation_config
from gdss.validation.pr_audit import load_radar_config


def test_load_gdss_config_defaults(tmp_path: Path) -> None:
    """Verifies default values when no .gdss.yml is present."""
    cfg = load_gdss_config(tmp_path)
    assert isinstance(cfg, GDSSConfig)
    assert cfg.radar.provider == "openrouter"
    assert cfg.radar.model == "openrouter/free"
    assert cfg.radar.risk_threshold == 0.1
    assert cfg.radar.concurrency_limit == 4
    assert cfg.radar.condensation == "lossless"
    assert cfg.validation.timeout_seconds == 30
    assert cfg.validation.anti_gaming_strict is True
    assert cfg.validation.allow_callsite_updates is True
    assert cfg.impact_closure.max_hops == 2
    assert cfg.impact_closure.relevance_threshold == 0.70
    assert cfg.impact_closure.token_budget == 4000
    assert cfg.impact_closure.test_patterns == ()
    assert cfg.impact_closure.contract_patterns == ()
    assert cfg.hierarchy.reference_branch == "main"
    assert cfg.hierarchy.same_base_only is True
    assert cfg.ast.additional_extensions == ()
    assert cfg.ast.exclude_patterns == ()
    assert cfg.migrations.paths == ()


def test_load_gdss_config_from_yaml(tmp_path: Path) -> None:
    """Verifies that all sections of .gdss.yml are correctly parsed and normalized."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  provider: "openai"
  model: "gpt-4o"
  base_url: "https://api.openai.com/v1"
  context_window: 64000
  risk_threshold: 0.25
  max_refinements: 3
  concurrency_limit: 8
  condensation: "ast_minimal"
  fail_on_collision: true

validation:
  test_command: "pytest {test_file}"
  typecheck_command: "mypy {file}"
  syntax_command: "ruff check {file}"
  timeout_seconds: 45
  anti_gaming_strict: false
  allow_callsite_updates: true

impact_closure:
  max_hops: 3
  relevance_threshold: 0.85
  token_budget: 6000
  test_patterns:
    - "custom_tests/**"
    - "e2e/**/*.spec.ts"
  contract_patterns:
    - "proto/**"
    - "custom_interfaces/**"

hierarchy:
  reference_branch: "develop"
  priority_chain:
    - "develop"
    - "main"
  same_base_only: false
  include:
    - "feature/*"
  exclude:
    - "hotfix/*"
  target_bases:
    - "develop"

ast:
  additional_extensions:
    - "vue"
    - ".svelte"
  exclude_patterns:
    - "dist/**"
    - "node_modules/**"
    - "*.min.js"

migrations:
  paths:
    - "custom/db/migrations"
    - "services/*/db/versions"
""",
        encoding="utf-8",
    )

    cfg = load_gdss_config(tmp_path)
    assert cfg.radar.provider == "openai"
    assert cfg.radar.model == "gpt-4o"
    assert cfg.radar.base_url == "https://api.openai.com/v1"
    assert cfg.radar.context_window == 64000
    assert cfg.radar.risk_threshold == 0.25
    assert cfg.radar.max_refinements == 3
    assert cfg.radar.concurrency_limit == 8
    assert cfg.radar.condensation == "ast_minimal"
    assert cfg.radar.fail_on_collision is True

    assert cfg.validation.test_command == "pytest {test_file}"
    assert cfg.validation.typecheck_command == "mypy {file}"
    assert cfg.validation.syntax_command == "ruff check {file}"
    assert cfg.validation.timeout_seconds == 45
    assert cfg.validation.anti_gaming_strict is False
    assert cfg.validation.allow_callsite_updates is True

    assert cfg.impact_closure.max_hops == 3
    assert cfg.impact_closure.relevance_threshold == 0.85
    assert cfg.impact_closure.token_budget == 6000
    assert cfg.impact_closure.test_patterns == ("custom_tests/**", "e2e/**/*.spec.ts")
    assert cfg.impact_closure.contract_patterns == ("proto/**", "custom_interfaces/**")

    assert cfg.hierarchy.reference_branch == "develop"
    assert cfg.hierarchy.priority_chain == ("develop", "main")
    assert cfg.hierarchy.same_base_only is False
    assert cfg.hierarchy.include == ("feature/*",)
    assert cfg.hierarchy.exclude == ("hotfix/*",)
    assert cfg.hierarchy.target_bases == ("develop",)

    # Extensions normalized to have leading dot
    assert cfg.ast.additional_extensions == (".vue", ".svelte")
    assert cfg.ast.exclude_patterns == ("dist/**", "node_modules/**", "*.min.js")
    assert cfg.migrations.paths == ("custom/db/migrations", "services/*/db/versions")


def test_is_path_excluded() -> None:
    """Verifies glob matching for excluded file paths."""
    patterns = ("dist/**", "node_modules/**", "*.min.js", "vendor/*")

    assert is_path_excluded("dist/bundle.js", patterns) is True
    assert is_path_excluded("dist/sub/app.js", patterns) is True
    assert is_path_excluded("node_modules/pkg/index.js", patterns) is True
    assert is_path_excluded("src/utils/app.min.js", patterns) is True
    assert is_path_excluded("vendor/lib.py", patterns) is True

    assert is_path_excluded("src/index.ts", patterns) is False
    assert is_path_excluded("gdss/core/ast_parser.py", patterns) is False
    assert is_path_excluded("package.json", patterns) is False


def test_backward_compatibility_delegations(tmp_path: Path) -> None:
    """Verifies that existing loader functions correctly delegate to load_gdss_config."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  model: "claude-3-5-sonnet"
  provider: "openrouter"
  risk_threshold: 0.15
  concurrency_limit: 6
  condensation: "ast_minimal"

validation:
  test_command: "npm test"
  timeout_seconds: 50

hierarchy:
  reference_branch: "master"
  same_base_only: false
  include:
    - "feat/*"

ast:
  additional_extensions:
    - ".sol"
""",
        encoding="utf-8",
    )

    # 1. get_source_extensions
    exts = get_source_extensions(tmp_path)
    assert ".sol" in exts

    # 2. load_validation_config
    val_cfg = load_validation_config(tmp_path)
    assert val_cfg.test_command == "npm test"
    assert val_cfg.timeout_seconds == 50

    # 3. load_radar_config
    radar_dict = load_radar_config(tmp_path)
    assert radar_dict.get("model") == "claude-3-5-sonnet"
    assert radar_dict.get("risk_threshold") == 0.15
    assert radar_dict.get("concurrency_limit") == 6
    assert radar_dict.get("condensation") == "ast_minimal"
    assert radar_dict.get("same_base_only") is False
    assert radar_dict.get("include") == ["feat/*"]

    # 4. _load_repo_hierarchy_config
    h_dict = _load_repo_hierarchy_config(str(tmp_path))
    assert h_dict.get("reference_branch") == "master"
    assert h_dict.get("same_base_only") is False


def test_migration_reducer_custom_paths() -> None:
    """Verifies MigrationDAGReducer recognizes custom configured migration paths."""
    reducer = MigrationDAGReducer(custom_paths=["custom/db/versions/*", "backend/migrations/**"])

    # Matches custom path
    assert reducer.can_handle("custom/db/versions/001_initial.py") is True
    assert reducer.can_handle("backend/migrations/2026_01_01.sql") is True

    # Standard path still matches
    assert reducer.can_handle("src/db/migrations/0002_add_users.py") is True

    # Non-migration unrelated file does not match
    assert reducer.can_handle("src/services/billing.py", content="def pay(): pass") is False


def test_trajectory_operators_respect_exclude_patterns(tmp_path: Path) -> None:
    """Verifies that extract_trajectory_operators skips files matching exclude_patterns."""
    import subprocess

    from gdss.core.ast_parser import ASTParser
    from gdss.core.trajectory import extract_trajectory_operators
    from gdss.core.transform_extractor import TransformExtractor
    from gdss.watcher.git_observer import GitObserver

    # Init git repo
    subprocess.run(["git", "init", "-b", "main"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), check=True)

    # Base commit on main
    (tmp_path / ".gdss.yml").write_text(
        """
ast:
  exclude_patterns:
    - "dist/**"
""",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def run(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True)

    # Feature branch with changes in src/app.py and dist/bundle.js
    subprocess.run(["git", "checkout", "-b", "feature-1"], cwd=str(tmp_path), check=True, capture_output=True)
    (tmp_path / "src" / "app.py").write_text("def run(): return 42\n", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "bundle.js").write_text("function bundled() { return 1; }\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "feature work"], cwd=str(tmp_path), check=True)

    observer = GitObserver(str(tmp_path))
    parser = ASTParser()
    extractor = TransformExtractor()

    ops = extract_trajectory_operators(
        observer=observer,
        parser=parser,
        extractor=extractor,
        ref_branch="main",
        head="feature-1",
    )

    # Should contain operators for src/app.py, but none for dist/bundle.js
    affected_files = {op.file for op in ops}
    assert "src/app.py" in affected_files
    assert not any("dist" in f for f in affected_files)


def test_load_env_file_auto_discovery(tmp_path: Path) -> None:
    """Verifies that .env files are automatically discovered and populated into os.environ."""
    import os

    from gdss.core.config import load_env_file

    env_file = tmp_path / ".env"
    env_file.write_text(
        """
# Comment line
TEST_GDSS_VAR_ONE=value1
TEST_GDSS_VAR_TWO="quoted_value2"
TEST_GDSS_VAR_THREE='single_quoted3'
INVALID_LINE_WITHOUT_EQUALS
""",
        encoding="utf-8",
    )

    # Ensure clean state
    for k in ("TEST_GDSS_VAR_ONE", "TEST_GDSS_VAR_TWO", "TEST_GDSS_VAR_THREE"):
        os.environ.pop(k, None)

    loaded = load_env_file(tmp_path)
    assert loaded["TEST_GDSS_VAR_ONE"] == "value1"
    assert loaded["TEST_GDSS_VAR_TWO"] == "quoted_value2"
    assert loaded["TEST_GDSS_VAR_THREE"] == "single_quoted3"

    assert os.environ.get("TEST_GDSS_VAR_ONE") == "value1"
    assert os.environ.get("TEST_GDSS_VAR_TWO") == "quoted_value2"
    assert os.environ.get("TEST_GDSS_VAR_THREE") == "single_quoted3"

    # Pre-existing environment variables must not be overwritten
    os.environ["TEST_GDSS_VAR_ONE"] = "existing_shell_value"
    loaded_second = load_env_file(tmp_path)
    assert "TEST_GDSS_VAR_ONE" not in loaded_second
    assert os.environ.get("TEST_GDSS_VAR_ONE") == "existing_shell_value"

    # Cleanup
    for k in ("TEST_GDSS_VAR_ONE", "TEST_GDSS_VAR_TWO", "TEST_GDSS_VAR_THREE"):
        os.environ.pop(k, None)


def test_branch_filtering_bidirectional_synchronization(tmp_path: Path) -> None:
    """Verifies that branch inclusion/exclusion filters synchronize between radar and hierarchy."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  include:
    - "feature/*"
  exclude:
    - "spike/*"
""",
        encoding="utf-8",
    )

    cfg = load_gdss_config(tmp_path)
    assert cfg.radar.include == ("feature/*",)
    assert cfg.radar.exclude == ("spike/*",)
    # Hierarchy must inherit from radar when omitted
    assert cfg.hierarchy.include == ("feature/*",)
    assert cfg.hierarchy.exclude == ("spike/*",)


