"""Model Context Protocol (MCP) server for GDSS."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from gdss.logger import get_logger
from gdss.mcp.tools import (
    check_anti_gaming,
    find_collisions,
    get_impact_closure,
    get_merge_order,
    inspect_symbol_impact,
    plan_semantic_rebase,
    sandbox_validate_patch,
    validate_patch,
)

logger = get_logger("gdss.mcp.server")

SERVER_NAME = "gdss-mcp-server"
SERVER_VERSION = "0.2.0"
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
                "branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset of branch names or wildcard patterns to include (e.g. ['feature/*'])",
                },
                "exclude_branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional branch names or wildcard patterns to exclude (e.g. ['spike/*', 'wip/*'])",
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
                "branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset of branch names or wildcard patterns to include",
                },
                "exclude_branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional branch names or wildcard patterns to exclude",
                },
            },
        },
    },
    {
        "name": "gdss_inspect_symbol_impact",
        "description": "Inspects dependency call graph to report downstream callers, verifying tests, and modifying branches for a symbol (powered by 2-hop Semantic Impact Closure).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Name or ID of the function/class/variable to inspect",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional relative file path being analyzed",
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
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum transitive caller depth (default: 2)",
                    "default": 2,
                },
                "token_budget": {
                    "type": "integer",
                    "description": "Maximum token budget for context assembly (default: 4000)",
                    "default": 4000,
                },
                "relevance_threshold": {
                    "type": "number",
                    "description": "Edge weight cutoff for transitive propagation (default: 0.70)",
                    "default": 0.70,
                },
            },
        },
    },
    {
        "name": "gdss_get_impact_closure",
        "description": "Calculates transitive 2-hop Semantic Impact Closure (SIC): discovers callers, API contracts, and verifying test suites within a token budget.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Primary symbol name or ID to compute closure from",
                },
                "file_path": {
                    "type": "string",
                    "description": "Target file path to compute closure for (if symbol omitted)",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of multiple root symbols to compute joint closure for",
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
                "max_hops": {
                    "type": "integer",
                    "description": "Maximum transitive caller depth (default: 2)",
                    "default": 2,
                },
                "token_budget": {
                    "type": "integer",
                    "description": "Maximum token budget for context assembly (default: 4000)",
                    "default": 4000,
                },
                "relevance_threshold": {
                    "type": "number",
                    "description": "Edge weight cutoff for transitive propagation (default: 0.70)",
                    "default": 0.70,
                },
            },
        },
    },
    {
        "name": "gdss_validate_patch",
        "description": "Validates unified diff patch syntax and target boundaries across multi-file diffs in any supported language without touching the working tree.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff patch string to validate",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional relative file path being patched (inferred from diff headers if omitted)",
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                    "default": ".",
                },
            },
            "required": ["patch"],
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
                "branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional subset of branch names or wildcard patterns to include",
                },
                "exclude_branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional branch names or wildcard patterns to exclude",
                },
            },
            "required": ["source_branch", "target_branch"],
        },
    },
    {
        "name": "gdss_sandbox_validate_patch",
        "description": "Applies a candidate patch in an ephemeral Git worktree and validates multi-language AST syntax, targeted typechecking, regression tests, and anti-gaming invariants, returning structured diagnostic traces.",
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
    {
        "name": "gdss_check_anti_gaming",
        "description": "Audits proposed test file modifications against assertion-preservation invariants, detecting deleted assertions or trivial replacements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "Unified diff patch or hunk applied to the test file",
                },
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the test file being checked",
                },
                "repo_path": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                    "default": ".",
                },
                "strict": {
                    "type": "boolean",
                    "description": "Enforce strict zero assertion net decrease (default: true)",
                    "default": True,
                },
                "allow_callsite_updates": {
                    "type": "boolean",
                    "description": "Permit argument updates inside assertions when signature changes (default: true)",
                    "default": True,
                },
            },
            "required": ["patch", "file_path"],
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
        branches = arguments.get("branches")
        exclude_branches = arguments.get("exclude_branches")
        if name == "gdss_find_collisions":
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return find_collisions(
                reference_branch=ref,
                repo_path=repo,
                branches=branches,
                exclude_branches=exclude_branches,
            )
        elif name == "gdss_get_merge_order":
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return get_merge_order(
                reference_branch=ref,
                repo_path=repo,
                branches=branches,
                exclude_branches=exclude_branches,
            )
        elif name == "gdss_inspect_symbol_impact":
            sym = arguments.get("symbol", "")
            fpath = arguments.get("file_path", "")
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            hops_val = int(arguments.get("max_hops", 2))
            budget_val = int(arguments.get("token_budget", 4000))
            rel_val = float(arguments.get("relevance_threshold", 0.70))
            return inspect_symbol_impact(
                symbol=sym,
                reference_branch=ref,
                repo_path=repo,
                file_path=fpath,
                max_hops=hops_val,
                token_budget=budget_val,
                relevance_threshold=rel_val,
            )
        elif name == "gdss_get_impact_closure":
            sym = arguments.get("symbol", "")
            fpath = arguments.get("file_path", "")
            symbols = arguments.get("symbols")
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            closure_hops = int(arguments.get("max_hops", 2))
            closure_budget = int(arguments.get("token_budget", 4000))
            closure_rel = float(arguments.get("relevance_threshold", 0.70))
            return get_impact_closure(
                symbol=sym,
                file_path=fpath,
                symbols=symbols,
                reference_branch=ref,
                repo_path=repo,
                max_hops=closure_hops,
                token_budget=closure_budget,
                relevance_threshold=closure_rel,
            )
        elif name == "gdss_plan_semantic_rebase":
            src = arguments.get("source_branch", "")
            tgt = arguments.get("target_branch", "")
            ref = arguments.get("reference_branch", "main")
            repo = arguments.get("repo_path", ".")
            return plan_semantic_rebase(
                source_branch=src,
                target_branch=tgt,
                reference_branch=ref,
                repo_path=repo,
                branches=branches,
                exclude_branches=exclude_branches,
            )
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
        elif name == "gdss_check_anti_gaming":
            patch = arguments.get("patch", "")
            fpath = arguments.get("file_path", "")
            repo = arguments.get("repo_path", ".")
            strict = arguments.get("strict", True)
            allow_updates = arguments.get("allow_callsite_updates", True)
            return check_anti_gaming(
                patch=patch,
                file_path=fpath,
                repo_path=repo,
                strict=bool(strict),
                allow_callsite_updates=bool(allow_updates),
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
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {e}"},
                }
            )
            continue

        resp = server.handle_request(req)
        if resp is not None:
            _send(resp)
