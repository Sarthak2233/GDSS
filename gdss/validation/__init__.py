"""GDSS Layer 10: Validation Sandbox.

Ephemeral worktree sandboxing, multi-language syntax verification,
targeted typechecking, and regression testing for candidate patches.
"""

from __future__ import annotations

from gdss.validation.discovery import (
    ValidationConfig,
    find_project_root_for_file,
    get_sandbox_timeout,
    load_validation_config,
)
from gdss.validation.languages import (
    LanguageDefinition,
    LanguageRegistry,
    get_default_registry,
)
from gdss.validation.pr_audit import (
    STICKY_SIGNATURE,
    PRAuditContext,
    PRCollisionDetail,
    PRCollisionResult,
    audit_pr_collisions,
    fetch_concurrent_prs,
    generate_pr_convergence_patch,
    load_radar_config,
    parse_github_env,
    post_or_update_sticky_comment,
    render_radar_markdown,
    run_pr_audit,
)
from gdss.validation.sandbox import ValidationSandbox, validate_patch
from gdss.validation.syntax import validate_file_syntax, validate_source_syntax
from gdss.validation.test_runner import find_targeted_test_files, run_targeted_tests
from gdss.validation.typechecker import run_targeted_typecheck
from gdss.validation.types import (
    SyntaxCheckResult,
    TestExecutionResult,
    TypeCheckResult,
    ValidationReport,
    ValidationStatus,
)
from gdss.validation.worktree import (
    ephemeral_worktree,
    is_git_repo,
    is_shallow_repo,
)

__all__ = [
    "LanguageDefinition",
    "LanguageRegistry",
    "PRAuditContext",
    "PRCollisionDetail",
    "PRCollisionResult",
    "STICKY_SIGNATURE",
    "SyntaxCheckResult",
    "TestExecutionResult",
    "TypeCheckResult",
    "ValidationConfig",
    "ValidationReport",
    "ValidationSandbox",
    "ValidationStatus",
    "audit_pr_collisions",
    "ephemeral_worktree",
    "fetch_concurrent_prs",
    "find_project_root_for_file",
    "find_targeted_test_files",
    "generate_pr_convergence_patch",
    "get_default_registry",
    "get_sandbox_timeout",
    "is_git_repo",
    "is_shallow_repo",
    "load_radar_config",
    "load_validation_config",
    "parse_github_env",
    "post_or_update_sticky_comment",
    "render_radar_markdown",
    "run_pr_audit",
    "run_targeted_tests",
    "run_targeted_typecheck",
    "validate_file_syntax",
    "validate_patch",
    "validate_source_syntax",
]
