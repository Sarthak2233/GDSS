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
    assert len(tool_names) == 6
    assert "gdss_find_collisions" in tool_names
    assert "gdss_get_merge_order" in tool_names
    assert "gdss_inspect_symbol_impact" in tool_names
    assert "gdss_plan_semantic_rebase" in tool_names
    assert "gdss_validate_patch" in tool_names
    assert "gdss_sandbox_validate_patch" in tool_names
    assert "gdss_suggest_resolutions" not in tool_names


def test_mcp_validate_patch_valid() -> None:
    server = MCPServer()
    patch_text = (
        "--- a/test.py\n"
        "+++ b/test.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-def old(): pass\n"
        "+def new(): pass\n"
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
        "--- a/test.py\n"
        "+++ b/test.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-def old(): pass\n"
        "+def broken(: pass\n"
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
    patch_text = (
        "--- a/mod.py\n"
        "+++ b/mod.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-x = 999\n"
        "+x = 20\n"
    )
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


def test_mcp_plan_semantic_rebase() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "gdss_plan_semantic_rebase",
            "arguments": {
                "source_branch": "main",
                "target_branch": "main",
                "repo_path": ".",
            },
        },
    }
    resp = server.handle_request(req)
    assert resp is not None
    assert not resp["result"]["isError"]
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "cleanly_applicable_count" in content
    assert "blocked_by_interference_count" in content


def test_mcp_find_collisions() -> None:
    server = MCPServer()
    req = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "gdss_find_collisions",
            "arguments": {
                "reference_branch": "main",
                "repo_path": ".",
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
