"""End-to-End Integration Tests for Semantic Impact Closure & Complementary Code Surgery.

Validates the full closed-loop convergence lifecycle:
1. AST Call-Site Pinpointing in untouched downstream test files (0 Git diff hunks).
2. Ephemeral Sandbox Diagnostic Extraction (E_k traces: failing line, error type, test case).
3. Agentic Refinement Multi-File Patch Synthesis spanning collision files & test files.
4. Anti-Gaming Invariant Defense protecting test assertions against deletion/trivialization.
5. Atomic Multi-File Guarded Apply and Full Rollback without Git repository corruption.
6. MCP Protocol closed-loop parity for IDE agents (Cursor, Claude Code, Copilot).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from gdss.ai.prompt_builder import build_refinement_prompt
from gdss.ai.types import (
    ConflictTopology,
    PatchCombination,
    Suggestion,
    SuggestionAnchor,
)
from gdss.core.ast_parser import ASTParser
from gdss.graph.code_graph import CodeGraph
from gdss.graph.impact_closure import (
    ImpactClosureConfig,
    compute_semantic_impact_closure,
)
from gdss.mcp.server import MCPServer
from gdss.validation.diagnostic_extractor import (
    AntiGamingCheckResult,
    DiagnosticPayload,
    inspect_test_diff_anti_gaming,
    parse_test_diagnostics,
)
from gdss.validation.guarded_apply import (
    apply_suggestion,
    parse_multi_file_unified_diff,
    preflight_check,
    rollback_suggestion,
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def surgery_git_repo(tmp_path: Path) -> tuple[Path, str]:
    """Create a pristine Git repository containing an auth module and downstream tests."""
    repo_dir = tmp_path / "surgery_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "surgery-test@gdss.dev"],
        cwd=repo_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Surgery Test Agent"],
        cwd=repo_dir,
        check=True,
    )

    auth_code = (
        "def login(user: str) -> bool:\n"
        "    if not user:\n"
        "        return False\n"
        "    return True\n"
        "\n"
        "def logout(user: str) -> bool:\n"
        "    return True\n"
    )
    (repo_dir / "auth.py").write_text(auth_code, encoding="utf-8")

    tests_dir = repo_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_auth_code = (
        "import auth\n"
        "\n"
        "def test_logout():\n"
        "    assert auth.logout('alice') is True\n"
        "\n"
        "def test_login_valid():\n"
        "    res = auth.login('alice')\n"
        "    assert res is True\n"
        "\n"
        "def test_oauth_stub():\n"
        "    assert True\n"
    )
    (tests_dir / "test_auth.py").write_text(test_auth_code, encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit: auth service and tests"],
        cwd=repo_dir,
        check=True,
    )

    head_rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    return repo_dir, head_rev


# ==============================================================================
# Integration Test Cases
# ==============================================================================


def test_ast_callsite_pinpointing_in_untouched_test_file(
    surgery_git_repo: tuple[Path, str],
) -> None:
    """1. Verify that AST CodeGraph pinpoints the exact test function and coordinates

    in a downstream test file that has zero prior Git diff hunks.
    """
    repo_dir, _ = surgery_git_repo

    parser = ASTParser()
    auth_symbols = parser.parse_file(str(repo_dir / "auth.py"))
    test_symbols = parser.parse_file(str(repo_dir / "tests" / "test_auth.py"))

    # Ensure symbol identities and file bindings
    for s in auth_symbols:
        s.ensure_identity("auth.py")
    for s in test_symbols:
        s.ensure_identity("tests/test_auth.py")

    graph = CodeGraph()
    graph.add_file_symbols("auth.py", auth_symbols)
    graph.add_file_symbols("tests/test_auth.py", test_symbols)
    graph.resolve_calls()

    login_sym = next(s for s in auth_symbols if s.name == "login")
    assert login_sym.symbol_id is not None

    # Compute 2-hop Semantic Impact Closure starting from the collided symbol ID
    closure = compute_semantic_impact_closure(
        graph,
        conflict_symbols=[login_sym.symbol_id],
        config=ImpactClosureConfig(max_hops=2, token_budget=4000),
    )

    # Assertions on Semantic Impact Envelope
    assert login_sym.symbol_id in closure.conflict_symbols
    assert "tests/test_auth.py" in closure.implicated_files
    assert "tests/test_auth.py" in closure.target_tests

    test_login_sym = next(s for s in test_symbols if s.name == "test_login_valid")
    test_logout_sym = next(s for s in test_symbols if s.name == "test_logout")

    # Pinpoint exact affected test: test_login_valid MUST be implicated at Hop 1
    login_test_nodes = [
        node
        for node in closure.closure_nodes
        if node.symbol_id == test_login_sym.symbol_id
    ]
    assert len(login_test_nodes) == 1, (
        "Expected test_login_valid to be isolated in impact closure"
    )

    node = login_test_nodes[0]
    assert node.file_path == "tests/test_auth.py"
    assert node.node_type == "test"
    assert node.hop_distance == 1
    assert node.implicated_by == login_sym.symbol_id

    # Unrelated tests must NOT be implicated
    logout_test_nodes = [
        node
        for node in closure.closure_nodes
        if node.symbol_id == test_logout_sym.symbol_id
    ]
    assert len(logout_test_nodes) == 0, (
        "test_logout should not be in the closure for auth.py::login"
    )

    # Retrieve physical AST coordinates of test_login_valid
    assert test_login_sym.start_line == 6
    assert test_login_sym.end_line == 8
    assert "login" in test_login_sym.calls


def test_sandbox_diagnostic_trace_pinpointing_ek() -> None:
    """2. Verify that running an ephemeral sandbox validator produces structured

    diagnostic traces (E_k) with exact failure coordinates and symbol context.
    """
    raw_pytest_failure = (
        "============================= test session starts ==============================\n"
        "collected 3 items\n\n"
        "tests/test_auth.py .F.                                                    [100%]\n\n"
        "=================================== FAILURES ===================================\n"
        "_______________________________ test_login_valid _______________________________\n\n"
        "    def test_login_valid():\n"
        ">       res = auth.login('alice')\n"
        "E       TypeError: login() missing 1 required positional argument: 'tenant_id'\n\n"
        "tests/test_auth.py:7: TypeError\n"
        "=========================== short test summary info ============================\n"
        "FAILED tests/test_auth.py::test_login_valid - TypeError: login() missing 1 required positional argument: 'tenant_id'\n"
        "========================= 1 failed, 2 passed in 0.08s ==========================\n"
    )

    payload = parse_test_diagnostics(
        tool_name="pytest",
        raw_output=raw_pytest_failure,
        exit_code=1,
    )

    assert isinstance(payload, DiagnosticPayload)
    assert payload.status == "VALIDATION_FAILED"
    assert payload.total_failed == 1
    assert len(payload.diagnostics) == 1

    diag = payload.diagnostics[0]
    assert diag.test_file == "tests/test_auth.py"
    assert diag.test_case == "test_login_valid"
    assert diag.line_number == 7
    assert diag.failure_type == "TypeError"
    assert "login" in diag.implicated_symbols
    assert any("missing 1 required positional argument" in line for line in diag.traceback)


def test_agentic_refinement_multi_file_patch_synthesis() -> None:
    """3. Verify that agentic refinement prompt construction consumes diagnostic

    traces (E_k) and unified diff parser decomposes multi-file surgery patches.
    """
    suggestion = Suggestion(
        kind="modify_function",
        file_path="auth.py",
        line_start=1,
        line_end=4,
        symbol_id="auth.py::login",
        operator="modify_function",
        action="reconcile signature addition",
        rationale="Branch A added tenant_id, Branch B modified auth timeout",
        reason=("auth.py::login", "tests/test_auth.py::test_login_valid"),
        confidence=0.95,
        rank=1,
        topology=ConflictTopology(
            kind="intersection",
            symbol_id="auth.py::login",
            operator_i="modify_function",
            operator_j="modify_function",
            commutativity="interfere",
            justification="Signature mismatch with downstream call site",
        ),
        patch_combinations=(
            PatchCombination(
                label="reconcile_tenant",
                strategy="signature_adaptation",
                patch_text="def login(user: str, tenant_id: str = 'default') -> bool:\n    return True\n",
                validated=False,
                validation_status="rejected",
                validation_error="tests/test_auth.py:7: TypeError: login() missing 1 required positional argument: 'tenant_id'",
            ),
        ),
        anchor=SuggestionAnchor(file_path="auth.py", line_start=1, line_end=4),
    )

    prompt = build_refinement_prompt(
        suggestion=suggestion,
        strategy_label="signature_adaptation",
        previous_patch=suggestion.patch_combinations[0].patch_text,
        validation_error=suggestion.patch_combinations[0].validation_error or "",
        repo="my-org/gdss-app",
        ref="main",
        anchored_symbol_block="def test_login_valid():\n    res = auth.login('alice')\n    assert res is True\n",
        output_format="unified_diff",
    )

    # Prompt verification
    assert "--- VALIDATION FAILURE TRACE ---" in prompt
    assert "tests/test_auth.py:7: TypeError" in prompt
    assert "TASK REFINEMENT OBJECTIVE:" in prompt
    assert "Output ONLY the corrected standard Unified Diff." in prompt

    # Multi-file patch synthesized for both auth.py and untouched tests/test_auth.py
    multi_file_patch = (
        "diff --git a/auth.py b/auth.py\n"
        "--- a/auth.py\n"
        "+++ b/auth.py\n"
        "@@ -1,4 +1,4 @@\n"
        "-def login(user: str) -> bool:\n"
        "+def login(user: str, tenant_id: str = 'default') -> bool:\n"
        "     if not user:\n"
        "         return False\n"
        "diff --git a/tests/test_auth.py b/tests/test_auth.py\n"
        "--- a/tests/test_auth.py\n"
        "+++ b/tests/test_auth.py\n"
        "@@ -6,3 +6,3 @@\n"
        " def test_login_valid():\n"
        "-    res = auth.login('alice')\n"
        "+    res = auth.login('alice', tenant_id='test-tenant')\n"
        "     assert res is True\n"
    )

    diff_map = parse_multi_file_unified_diff(multi_file_patch, default_file="auth.py")
    assert "auth.py" in diff_map
    assert "tests/test_auth.py" in diff_map
    assert "tenant_id: str = 'default'" in diff_map["auth.py"]
    assert "tenant_id='test-tenant'" in diff_map["tests/test_auth.py"]


def test_anti_gaming_defense_on_complementary_test_patch() -> None:
    """4. Verify that Anti-Gaming Sensor defends test assertions against cheating

    (deletion/trivialization) while allowing legitimate call-site adaptations.
    """
    orig_test = (
        "import auth\n"
        "\n"
        "def test_login_valid():\n"
        "    res = auth.login('alice')\n"
        "    assert res is True\n"
        "    assert len(auth.active_sessions()) == 1\n"
    )

    # Legitimate call-site adaptation (preserves both assertions)
    legit_test = (
        "import auth\n"
        "\n"
        "def test_login_valid():\n"
        "    res = auth.login('alice', tenant_id='corp')\n"
        "    assert res is True\n"
        "    assert len(auth.active_sessions()) == 1\n"
    )
    res_legit = inspect_test_diff_anti_gaming(
        original_content=orig_test,
        patched_content=legit_test,
        file_path="tests/test_auth.py",
        strict=True,
        allow_callsite_updates=True,
    )
    assert isinstance(res_legit, AntiGamingCheckResult)
    assert res_legit.passed is True
    assert res_legit.deleted_assertions_count == 0
    assert res_legit.modified_assertions_count == 0
    assert len(res_legit.warnings) == 0

    # Gaming Attack 1: Deleting second assertion to force green
    adversarial_delete = (
        "import auth\n"
        "\n"
        "def test_login_valid():\n"
        "    res = auth.login('alice', tenant_id='corp')\n"
        "    assert res is True\n"
    )
    res_delete = inspect_test_diff_anti_gaming(
        original_content=orig_test,
        patched_content=adversarial_delete,
        file_path="tests/test_auth.py",
        strict=True,
    )
    assert res_delete.passed is False
    assert res_delete.deleted_assertions_count == 1
    assert any("ANTI_GAMING_WARNING" in w for w in res_delete.warnings)
    assert any("deleted" in w.lower() or "removed" in w.lower() for w in res_delete.warnings)

    # Gaming Attack 2: Weakening assertion to trivial truth (assert True)
    adversarial_trivial = (
        "import auth\n"
        "\n"
        "def test_login_valid():\n"
        "    res = auth.login('alice', tenant_id='corp')\n"
        "    assert res is True\n"
        "    assert True\n"
    )
    res_trivial = inspect_test_diff_anti_gaming(
        original_content=orig_test,
        patched_content=adversarial_trivial,
        file_path="tests/test_auth.py",
        strict=True,
    )
    assert res_trivial.passed is False
    assert any("trivial" in w.lower() for w in res_trivial.warnings)


def test_atomic_multi_file_guarded_apply_and_revalidation(
    surgery_git_repo: tuple[Path, str],
) -> None:
    """5. Verify atomic multi-file application spanning collision file and untouched

    test file, verifying zero repository corruption and exact byte rollback.
    """
    repo_dir, head_sha = surgery_git_repo

    multi_file_patch = (
        "diff --git a/auth.py b/auth.py\n"
        "--- a/auth.py\n"
        "+++ b/auth.py\n"
        "@@ -1,4 +1,4 @@\n"
        "-def login(user: str) -> bool:\n"
        "+def login(user: str, tenant_id: str = 'default') -> bool:\n"
        "     if not user:\n"
        "         return False\n"
        "diff --git a/tests/test_auth.py b/tests/test_auth.py\n"
        "--- a/tests/test_auth.py\n"
        "+++ b/tests/test_auth.py\n"
        "@@ -6,3 +6,3 @@\n"
        " def test_login_valid():\n"
        "-    res = auth.login('alice')\n"
        "+    res = auth.login('alice', tenant_id='test-tenant')\n"
        "     assert res is True\n"
    )

    # Persist candidate suggestion in .gdss/suggestions/
    sug_dir = repo_dir / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True, exist_ok=True)
    suggestion_id = "sug_multi_surgery_001"
    suggestion_data = {
        "id": suggestion_id,
        "file_path": "auth.py",
        "line_start": 1,
        "line_end": 4,
        "symbol_id": "auth.py::login",
        "target_commit": head_sha,
        "patch_combinations": [
            {
                "label": "reconcile_with_downstream_test",
                "strategy": "reconcile_with_downstream_test",
                "patch_text": multi_file_patch,
            }
        ],
    }
    (sug_dir / f"{suggestion_id}.json").write_text(
        json.dumps(suggestion_data, indent=2), encoding="utf-8"
    )

    # Step 1: Preflight validation
    preflight = preflight_check(
        suggestion_data=suggestion_data,
        repo_root=repo_dir,
        strategy_name="reconcile_with_downstream_test",
        current_head_sha=head_sha,
    )
    assert preflight.valid is True
    assert preflight.strategy == "reconcile_with_downstream_test"

    orig_auth = (repo_dir / "auth.py").read_text(encoding="utf-8")
    orig_test = (repo_dir / "tests" / "test_auth.py").read_text(encoding="utf-8")

    # Step 2: Atomic apply
    apply_res = apply_suggestion(
        suggestion_id=suggestion_id,
        repo_root=repo_dir,
        strategy_name="reconcile_with_downstream_test",
    )
    assert apply_res.success is True, f"Apply failed: {apply_res.error}"

    # Verify disk contents modified for BOTH files
    patched_auth = (repo_dir / "auth.py").read_text(encoding="utf-8")
    patched_test = (repo_dir / "tests" / "test_auth.py").read_text(encoding="utf-8")

    assert "tenant_id: str = 'default'" in patched_auth
    assert "tenant_id='test-tenant'" in patched_test
    assert patched_auth != orig_auth
    assert patched_test != orig_test

    # Step 3: Atomic rollback restores pristine byte content
    rb_res = rollback_suggestion(suggestion_id=suggestion_id, repo_root=repo_dir)
    assert rb_res.success is True, f"Rollback failed: {rb_res.error}"
    assert rb_res.restored is True

    restored_auth = (repo_dir / "auth.py").read_text(encoding="utf-8")
    restored_test = (repo_dir / "tests" / "test_auth.py").read_text(encoding="utf-8")

    assert restored_auth == orig_auth
    assert restored_test == orig_test


def test_mcp_full_closed_loop_code_surgery(
    surgery_git_repo: tuple[Path, str],
) -> None:
    """6. Verify that IDE agents (Cursor, Claude Code, Copilot) can execute

    Semantic Impact Closure, Anti-Gaming Checks, and Multi-File Patch Validation
    over the MCP JSON-RPC protocol.
    """
    repo_dir, _ = surgery_git_repo
    server = MCPServer()

    # 1. gdss_get_impact_closure via MCP
    req_impact = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/call",
        "params": {
            "name": "gdss_get_impact_closure",
            "arguments": {
                "symbol": "login",
                "file_path": "auth.py",
                "repo_path": str(repo_dir),
                "max_hops": 2,
            },
        },
    }
    resp_impact = server.handle_request(req_impact)
    assert resp_impact is not None
    assert not resp_impact["result"]["isError"]
    impact_data = json.loads(resp_impact["result"]["content"][0]["text"])
    assert "closure_nodes" in impact_data
    assert "target_tests" in impact_data

    # 2. gdss_check_anti_gaming via MCP (Clean call site modification)
    clean_test_diff = (
        "--- a/tests/test_auth.py\n"
        "+++ b/tests/test_auth.py\n"
        "@@ -6,3 +6,3 @@\n"
        " def test_login_valid():\n"
        "-    res = auth.login('alice')\n"
        "+    res = auth.login('alice', tenant_id='test-tenant')\n"
        "     assert res is True\n"
    )
    req_anti_clean = {
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "gdss_check_anti_gaming",
            "arguments": {
                "patch": clean_test_diff,
                "file_path": "tests/test_auth.py",
                "repo_path": str(repo_dir),
            },
        },
    }
    resp_anti_clean = server.handle_request(req_anti_clean)
    assert resp_anti_clean is not None
    anti_clean_data = json.loads(resp_anti_clean["result"]["content"][0]["text"])
    assert anti_clean_data["passed"] is True
    assert anti_clean_data["clean"] is True

    # 3. gdss_check_anti_gaming via MCP (Adversarial assertion deletion)
    bad_test_diff = (
        "--- a/tests/test_auth.py\n"
        "+++ b/tests/test_auth.py\n"
        "@@ -6,4 +6,3 @@\n"
        " def test_login_valid():\n"
        "     res = auth.login('alice')\n"
        "-    assert res is True\n"
        "+    pass\n"
    )
    req_anti_bad = {
        "jsonrpc": "2.0",
        "id": 103,
        "method": "tools/call",
        "params": {
            "name": "gdss_check_anti_gaming",
            "arguments": {
                "patch": bad_test_diff,
                "file_path": "tests/test_auth.py",
                "repo_path": str(repo_dir),
            },
        },
    }
    resp_anti_bad = server.handle_request(req_anti_bad)
    assert resp_anti_bad is not None
    anti_bad_data = json.loads(resp_anti_bad["result"]["content"][0]["text"])
    assert anti_bad_data["passed"] is False
    assert anti_bad_data["deleted_assertions_count"] >= 1

    # 4. gdss_validate_patch via MCP with multi-file diff
    multi_patch = (
        "diff --git a/auth.py b/auth.py\n"
        "--- a/auth.py\n"
        "+++ b/auth.py\n"
        "@@ -1,4 +1,4 @@\n"
        "-def login(user: str) -> bool:\n"
        "+def login(user: str, tenant_id: str = 'default') -> bool:\n"
        "     if not user:\n"
        "         return False\n"
        "diff --git a/tests/test_auth.py b/tests/test_auth.py\n"
        "--- a/tests/test_auth.py\n"
        "+++ b/tests/test_auth.py\n"
        "@@ -6,3 +6,3 @@\n"
        " def test_login_valid():\n"
        "-    res = auth.login('alice')\n"
        "+    res = auth.login('alice', tenant_id='test-tenant')\n"
        "     assert res is True\n"
    )
    req_val_multi = {
        "jsonrpc": "2.0",
        "id": 104,
        "method": "tools/call",
        "params": {
            "name": "gdss_validate_patch",
            "arguments": {
                "patch": multi_patch,
                "repo_path": str(repo_dir),
            },
        },
    }
    resp_val_multi = server.handle_request(req_val_multi)
    assert resp_val_multi is not None
    val_data = json.loads(resp_val_multi["result"]["content"][0]["text"])
    assert val_data["valid"] is True
    assert val_data["syntax_valid"] is True
    assert "auth.py" in val_data["files_validated"]
    assert "tests/test_auth.py" in val_data["files_validated"]
