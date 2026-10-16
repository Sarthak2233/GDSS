"""Model Context Protocol (MCP) server for GDSS."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from gdss.logger import get_logger
from gdss.mcp.tools import (
    find_collisions,
    get_merge_order,
    inspect_symbol_impact,
    plan_semantic_rebase,
    sandbox_validate_patch,
    validate_patch,
)

logger = get_logger("gdss.mcp.server")

SERVER_NAME = "gdss-mcp-server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "gdss_find_collisions",
        "description": "Deterministic branch collision radar: computes pairwise interaction matrix (Omega_ij) and detects commutativity violations across concurrent branches.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "reference_branch": {
              "type": "string",
              "description": "Base/target branch to compare against (default: 'main')",
              "default": "main",
            },
            "repo_path": {
              "type": "string",
              "description": "Path to the git repository (default: current directory)",
              "default": ".",
            },
          },
        },
    },
    {
        "name": "gdss_get_merge_order",
        "description": "Calculates optimal merge sequence across active branches minimizing semantic drift and integration friction.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "reference_branch": {
              "type": "string",
              "description": "Base/target branch to compare against (default: 'main')",
              "default": "main",
            },
            "repo_path": {
              "type": "string",
              "description": "Path to the git repository (default: current directory)",
              "default": ".",
            },
          },
        },
    },
    {
        "name": "gdss_inspect_symbol_impact",
        "description": "Inspects dependency call graph to report downstream callers and branches modifying a symbol.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "symbol": {
              "type": "string",
              "description": "Name or ID of the function/class/variable to inspect",
            },
            "reference_branch": {
              "type": "string",
              "description": "Base/target branch to compare against (default: 'main')",
              "default": "main",
            },
            "repo_path": {
              "type": "string",
              "description": "Path to the git repository (default: current directory)",
              "default": ".",
            },
          },
          "required": ["symbol"],
        },
    },
    {
        "name": "gdss_validate_patch",
        "description": "Validates unified diff patch syntax and target boundaries in a sandbox without touching the working tree.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "patch": {
              "type": "string",
              "description": "Unified diff patch string to validate",
            },
            "file_path": {
              "type": "string",
              "description": "Relative file path being patched",
            },
            "repo_path": {
              "type": "string",
              "description": "Path to the git repository (default: current directory)",
              "default": ".",
            },
          },
          "required": ["patch", "file_path"],
        },
    },
    {
        "name": "gdss_plan_semantic_rebase",
        "description": "Computes semantic rebase plan: identifies cleanly commuting vs blocked non-commutative operators between two branches.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "source_branch": {
              "type": "string",
              "description": "Branch to rebase or cherry-pick from",
            },
            "target_branch": {
              "type": "string",
              "description": "Branch to rebase onto",
            },
            "reference_branch": {
              "type": "string",
              "description": "Common base/reference branch (default: 'main')",
              "default": "main",
            },
            "repo_path": {
              "type": "string",
              "description": "Path to the git repository (default: current directory)",
              "default": ".",
            },
          },
          "required": ["source_branch", "target_branch"],
        },
    },
    {
        "name": "gdss_sandbox_validate_patch",
        "description": "Applies a candidate patch in an ephemeral Git worktree and validates multi-language AST syntax, targeted typechecking, and regression tests without mutating the working tree.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff patch string to validate in sandbox",
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                    "default": ".",
                },
                "target_branch": {
                    "type": "string",
                    "description": "Target branch or commit ref to branch worktree from (default: 'HEAD')",
                    "default": "HEAD",
                },
                "timeout_seconds": {
                    "type": "number",
                    "description": "Sandbox execution timeout in seconds (default: 30.0)",
                    "default": 30.0,
                },
            },
            "required": ["patch"],
        },
    },
]


class MCPServer:
    """JSON-RPC 2.0 MCP server executing deterministic GDSS analysis tools."""

    def __init__(self) -> None:
        self.tools = TOOLS

    def list_tools(self) -> list[dict[str, Any]]:
        return self.tools

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a tool call and return result dict."""
        if name == "gdss_find_collisions":
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return find_collisions(reference_branch=ref, repo_path=repo)
        elif name == "gdss_get_merge_order":
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return get_merge_order(reference_branch=ref, repo_path=repo)
        elif name == "gdss_inspect_symbol_impact":
            sym = arguments.get("symbol", "")
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return inspect_symbol_impact(symbol=sym, reference_branch=ref, repo_path=repo)
        elif name == "gdss_plan_semantic_rebase":
            src = arguments.get("source_branch", "")
            tgt = arguments.get("target_branch", "")
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return plan_semantic_rebase(source_branch=src, target_branch=tgt, reference_branch=ref, repo_path=repo)
        elif name == "gdss_validate_patch":
            patch = arguments.get("patch", "")
            fpath = arguments.get("file_path", "")
            repo = arguments.get("repo_path", ".")
            return validate_patch(patch=patch, file_path=fpath, repo_path=repo)
        elif name == "gdss_sandbox_validate_patch":
            patch = arguments.get("patch", "")
            repo = arguments.get("repo_path", ".")
            target_branch = arguments.get("target_branch", "HEAD")
            timeout = arguments.get("timeout_seconds")
            return sandbox_validate_patch(
                patch=patch,
                repo_path=repo,
                target_branch=target_branch,
                timeout_seconds=float(timeout) if timeout is not None else None,
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

    def handle_request(self, req: dict[str, Any]) -> dict[str, Any] | None:
        """Handle a single JSON-RPC 2.0 request."""
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION,
                    },
                },
            }

        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {},
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.list_tools(),
                },
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            logger.info("MCP tool call: %s", tool_name)
            logger.debug("MCP tool arguments: %s", arguments)
            try:
                result_data = self.call_tool(tool_name, arguments)
                logger.info("MCP tool %s completed successfully", tool_name)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result_data, indent=2),
                            }
                        ],
                        "isError": False,
                    },
                }
            except Exception as e:
                logger.error("MCP tool %s failed: %s", tool_name, e, exc_info=True)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"error": str(e)}, indent=2),
                            }
                        ],
                        "isError": True,
                    },
                }

        # Unknown method error
        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }
        return None


def run_stdio_server(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    """Run MCP server in stdio mode listening for newline-delimited JSON-RPC requests."""
    in_stream = input_stream or sys.stdin
    out_stream = output_stream or sys.stdout
    server = MCPServer()

    def _send(data: dict[str, Any]) -> None:
        out_stream.write(json.dumps(data) + "\n")
        out_stream.flush()

    for line in in_stream:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            _send({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            })
            continue

        resp = server.handle_request(req)
        if resp is not None:
            _send(resp)
