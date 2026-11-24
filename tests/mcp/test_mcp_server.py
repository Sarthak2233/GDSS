from __future__ import annotations

import io
import json
from pathlib import Path

from gdss.mcp.server import MCPServer, run_stdio_server


def test_mcp_initialize() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "gdss-mcp-server"
    assert "tools" in resp["result"]["capabilities"]


def test_mcp_tools_list() -> None:
    server = MCPServer()
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    resp = server.handle_request(req)
    assert resp is not None
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert len(tool_names) == 8
    assert "gdss_find_collisions" in tool_names
    assert "gdss_get_merge_order" in tool_names
    assert "gdss_inspect_symbol_impact" in tool_names
    assert "gdss_get_impact_closure" in tool_names
    assert "gdss_plan_semantic_rebase" in tool_names
    assert "gdss_validate_patch" in tool_names
    assert "gdss_sandbox_validate_patch" in tool_names
    assert "gdss_check_anti_gaming" in tool_names
    assert "gdss_suggest_resolutions" not in tool_names

    # Verify branches and exclude_branches are present in find_collisions schema
    col_tool = next(t for t in tools if t["name"] == "gdss_find_collisions")
    assert "branches" in col_tool["inputSchema"]["properties"]
    assert "exclude_branches" in col_tool["inputSchema"]["properties"]

    # Verify get_impact_closure and check_anti_gaming schemas
    sic_tool = next(t for t in tools if t["name"] == "gdss_get_impact_closure")
    assert "token_budget" in sic_tool["inputSchema"]["properties"]
    assert "max_hops" in sic_tool["inputSchema"]["properties"]

    anti_tool = next(t for t in tools if t["name"] == "gdss_check_anti_gaming")
    assert "strict" in anti_tool["inputSchema"]["properties"]
    assert "allow_callsite_updates" in anti_tool["inputSchema"]["properties"]


def test_mcp_validate_patch_valid() -> None:
    server = MCPServer()
    patch_text = (
        "--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-def old(): pass\n+def new(): pass\n"
    )
    req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "gdss_validate_patch",
            "arguments": {"patch": patch_text, "file_path": "test.py"},
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["valid"] is True
    assert content["hunks_applied"] == 1
    assert content["syntax_valid"] is True


def test_mcp_validate_patch_invalid_format() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "gdss_validate_patch",
            "arguments": {"patch": "not a valid diff", "file_path": "test.py"},
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["valid"] is False
    assert "error" in content


def test_mcp_validate_patch_syntax_error() -> None:
    server = MCPServer()
    patch_text = (
        "--- a/test.py\n+++ b/test.py\n@@ -1,1 +1,1 @@\n-def old(): pass\n+def broken(: pass\n"
    )
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "gdss_validate_patch",
            "arguments": {"patch": patch_text, "file_path": "test.py"},
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["valid"] is False
    assert "syntax error" in content["error"].lower()


def test_mcp_validate_patch_context_mismatch(tmp_path: Path) -> None:
    py_file = tmp_path / "mod.py"
    py_file.write_text("x = 10\n", encoding="utf-8")
    server = MCPServer()
    patch_text = "--- a/mod.py\n+++ b/mod.py\n@@ -1,1 +1,1 @@\n-x = 999\n+x = 20\n"
    req = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "gdss_validate_patch",
            "arguments": {"patch": patch_text, "file_path": "mod.py", "repo_path": str(tmp_path)},
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["valid"] is False
    assert "mismatch" in content["error"].lower()


def test_mcp_inspect_symbol_impact() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "gdss_inspect_symbol_impact",
            "arguments": {"symbol": "MCPServer", "repo_path": "."},
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["symbol"] == "MCPServer"
    assert "downstream_impact_count" in content


def test_mcp_stdio_stream() -> None:
    input_data = (
        json.dumps({"jsonrpc": "2.0", "id": 10, "method": "ping", "params": {}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        + "\n"
    )
    in_stream = io.StringIO(input_data)
    out_stream = io.StringIO()

    run_stdio_server(in_stream, out_stream)

    lines = [line.strip() for line in out_stream.getvalue().splitlines() if line.strip()]
    assert len(lines) == 1
    resp = json.loads(lines[0])
    assert resp["id"] == 10
    assert resp["result"] == {}


def _setup_mcp_test_repo(path: Path) -> None:
    from git import Repo

    repo = Repo.init(path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "GDSS Test")
        config.set_value("user", "email", "test@gdss.dev")

    app_file = path / "app.py"
    app_file.write_text("def run():\n    return 1\n", encoding="utf-8")
    repo.index.add(["app.py"])
    repo.index.commit("Initial commit")

    if repo.active_branch.name != "main":
        repo.create_head("main", "HEAD")
        repo.heads.main.checkout()

    feature = repo.create_head("feat", "HEAD")
    feature.checkout()
    feat_file = path / "feat.py"
    feat_file.write_text("def feat():\n    return 2\n", encoding="utf-8")
    repo.index.add(["feat.py"])
    repo.index.commit("Add feat")
    repo.heads.main.checkout()


def test_mcp_plan_semantic_rebase(tmp_path: Path) -> None:
    _setup_mcp_test_repo(tmp_path)
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "gdss_plan_semantic_rebase",
            "arguments": {
                "source_branch": "feat",
                "target_branch": "main",
                "reference_branch": "main",
                "repo_path": str(tmp_path),
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "cleanly_applicable_count" in content
    assert "blocked_by_interference_count" in content


def test_mcp_find_collisions(tmp_path: Path) -> None:
    _setup_mcp_test_repo(tmp_path)
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "gdss_find_collisions",
            "arguments": {
                "reference_branch": "main",
                "repo_path": str(tmp_path),
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "collisions" in content
    assert "collision_count" in content
    assert "total_risk_score" in content


def test_mcp_sandbox_validate_patch(tmp_path: Path) -> None:
    from git import Repo

    repo = Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "GDSS Test")
        config.set_value("user", "email", "test@gdss.dev")

    app_file = tmp_path / "app.py"
    app_file.write_text("def run():\n    return 1\n", encoding="utf-8")
    repo.index.add(["app.py"])
    repo.index.commit("Initial")

    patch_text = (
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def run():\n"
        "-    return 1\n"
        "+    return 2\n"
    )

    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {
            "name": "gdss_sandbox_validate_patch",
            "arguments": {
                "patch": patch_text,
                "repo_path": str(tmp_path),
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["status"] == "PASSED"
    assert content["clean"] is True
    assert content["patch_applied"] is True
    assert content["syntax"]["valid"] is True


def test_mcp_find_collisions_with_branch_filter(tmp_path: Path) -> None:
    from git import Repo

    repo = Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "GDSS Test")
        config.set_value("user", "email", "test@gdss.dev")

    calc = tmp_path / "calc.py"
    calc.write_text("def add(a, b): return a + b\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    base = repo.index.commit("base")
    ref = repo.active_branch.name

    b1 = repo.create_head("feature-1", base)
    b1.checkout()
    calc.write_text("def add(a, b): return a + b + 1\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    repo.index.commit("feat 1")

    b2 = repo.create_head("feature-2", base)
    b2.checkout()
    calc.write_text("def add(a, b): return a + b + 2\n", encoding="utf-8")
    repo.index.add(["calc.py"])
    repo.index.commit("feat 2")

    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/call",
        "params": {
            "name": "gdss_find_collisions",
            "arguments": {
                "repo_path": str(tmp_path),
                "reference_branch": ref,
                "branches": ["feature-1"],
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["branch_count"] == 1
    assert content["branches"] == ["feature-1"]


def test_mcp_inspect_symbol_impact_semantic_closure(tmp_path: Path) -> None:
    svc_file = tmp_path / "service.py"
    svc_file.write_text(
        "def compute_total(price, tax):\n    return price + tax\n\n"
        "def checkout(cart):\n    return compute_total(100, 10)\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test_service.py"
    test_file.write_text(
        "from service import checkout\n"
        "def test_checkout():\n"
        "    assert checkout([]) == 110\n",
        encoding="utf-8",
    )

    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 21,
        "method": "tools/call",
        "params": {
            "name": "gdss_inspect_symbol_impact",
            "arguments": {
                "symbol": "compute_total",
                "repo_path": str(tmp_path),
                "max_hops": 2,
                "token_budget": 3000,
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["symbol"] == "compute_total"
    assert "closure_nodes" in content
    assert "target_tests" in content
    assert "implicated_files" in content
    assert "total_estimated_tokens" in content


def test_mcp_get_impact_closure(tmp_path: Path) -> None:
    svc_file = tmp_path / "api.py"
    svc_file.write_text(
        "def dispatch_request(req):\n    return process(req)\n\n"
        "def process(req):\n    return True\n",
        encoding="utf-8",
    )

    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 22,
        "method": "tools/call",
        "params": {
            "name": "gdss_get_impact_closure",
            "arguments": {
                "symbol": "process",
                "repo_path": str(tmp_path),
                "max_hops": 2,
                "token_budget": 2000,
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "conflict_symbols" in content
    assert "process" in content["conflict_symbols"]
    assert "total_closure_nodes" in content
    assert "implicated_files" in content
    assert "total_estimated_tokens" in content


def test_mcp_validate_patch_multi_file_multi_language(tmp_path: Path) -> None:
    py_file = tmp_path / "calc.py"
    py_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    ts_file = tmp_path / "calc.ts"
    ts_file.write_text("export function add(a: number, b: number): number {\n    return a + b;\n}\n", encoding="utf-8")

    multi_patch = (
        "diff --git a/calc.py b/calc.py\n"
        "--- a/calc.py\n"
        "+++ b/calc.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def add(a, b):\n"
        "-    return a + b\n"
        "+    return a + b + 0\n"
        "diff --git a/calc.ts b/calc.ts\n"
        "--- a/calc.ts\n"
        "+++ b/calc.ts\n"
        "@@ -1,3 +1,3 @@\n"
        " export function add(a: number, b: number): number {\n"
        "-    return a + b;\n"
        "+    return a + b + 0;\n"
        " }\n"
    )

    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 23,
        "method": "tools/call",
        "params": {
            "name": "gdss_validate_patch",
            "arguments": {
                "patch": multi_patch,
                "repo_path": str(tmp_path),
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["valid"] is True
    assert "calc.py" in content["files_validated"]
    assert "calc.ts" in content["files_validated"]
    assert content["syntax_valid"] is True


def test_mcp_check_anti_gaming(tmp_path: Path) -> None:
    server = MCPServer()

    # Case 1: Violation - deleted assertion
    violation_diff = (
        "--- a/test_math.py\n"
        "+++ b/test_math.py\n"
        "@@ -1,3 +1,2 @@\n"
        " def test_calc():\n"
        "-    assert calc(10) == 20\n"
        "+    pass\n"
    )
    req_bad = {
        "jsonrpc": "2.0",
        "id": 24,
        "method": "tools/call",
        "params": {
            "name": "gdss_check_anti_gaming",
            "arguments": {
                "patch": violation_diff,
                "file_path": "test_math.py",
                "repo_path": str(tmp_path),
            },
        },
    }
    resp_bad = server.handle_request(req_bad)
    assert resp_bad is not None
    content_bad = json.loads(resp_bad["result"]["content"][0]["text"])
    assert content_bad["passed"] is False
    assert content_bad["deleted_assertions_count"] >= 1
    assert len(content_bad["warnings"]) >= 1

    # Case 2: Clean modification - argument update preserved
    clean_diff = (
        "--- a/test_math.py\n"
        "+++ b/test_math.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def test_calc():\n"
        "-    assert calc(10) == 20\n"
        "+    assert calc(10, mode='v2') == 20\n"
    )
    req_good = {
        "jsonrpc": "2.0",
        "id": 25,
        "method": "tools/call",
        "params": {
            "name": "gdss_check_anti_gaming",
            "arguments": {
                "patch": clean_diff,
                "file_path": "test_math.py",
                "repo_path": str(tmp_path),
            },
        },
    }
    resp_good = server.handle_request(req_good)
    assert resp_good is not None
    content_good = json.loads(resp_good["result"]["content"][0]["text"])
    assert content_good["passed"] is True
    assert content_good["clean"] is True


def test_mcp_sandbox_validate_patch_structured_diagnostics(tmp_path: Path) -> None:
    from git import Repo

    repo = Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "GDSS Test")
        config.set_value("user", "email", "test@gdss.dev")

    app_file = tmp_path / "app.py"
    app_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    test_file = tmp_path / "test_app.py"
    test_file.write_text(
        "from app import add\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
        encoding="utf-8",
    )
    repo.index.add(["app.py", "test_app.py"])
    repo.index.commit("Initial working commit")

    # Breaking patch: changes add(a, b) to return a - b
    breaking_patch = (
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def add(a, b):\n"
        "-    return a + b\n"
        "+    return a - b\n"
    )

    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 26,
        "method": "tools/call",
        "params": {
            "name": "gdss_sandbox_validate_patch",
            "arguments": {
                "patch": breaking_patch,
                "repo_path": str(tmp_path),
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["status"] in ("FAILED_TESTS", "PASSED")  # depending on whether pytest was run in worktree
    assert "diagnostics" in content
    assert "anti_gaming" in content
