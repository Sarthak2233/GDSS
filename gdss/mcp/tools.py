"""Deterministic analysis tools exposed by GDSS MCP server."""

from __future__ import annotations

import ast
import re
from collections.abc import Hashable
from pathlib import Path
from typing import Any

from gdss.conflict.commutativity import CommutativityClass, classify
from gdss.conflict.merge_order import plan_merge_order
from gdss.conflict.rebase_plan import build_transport_plan
from gdss.core.ast_parser import ASTParser
from gdss.core.trajectory import extract_trajectory_operators
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import SemanticOperator
from gdss.drift.context import AnalysisContextError, build_analysis_context, iter_contact_pairs
from gdss.graph.graph_builder import build_code_graph_from_repo
from gdss.logger import get_logger
from gdss.watcher.git_observer import GitObserver

logger = get_logger("gdss.mcp.tools")


def find_collisions(
    reference_branch: str = "main",
    repo_path: str = ".",
    branches: list[str] | None = None,
    exclude_branches: list[str] | None = None,
) -> dict[str, Any]:
    """Compute pairwise branch collision matrix (Omega_ij) and integration risk with concrete AST contacts."""
    path = str(Path(repo_path).resolve())
    logger.debug(
        "mcp.find_collisions: repo=%s, ref=%s, branches=%s, exclude=%s",
        path,
        reference_branch,
        branches,
        exclude_branches,
    )
    try:
        context = build_analysis_context(
            path,
            reference_branch,
            branches=branches,
            exclude_branches=exclude_branches,
        )
    except AnalysisContextError as e:
        logger.warning("mcp.find_collisions context error: %s", e)
        return {
            "error": str(e),
            "reference_branch": reference_branch,
            "collisions": [],
            "total_risk_score": 0.0,
        }
    except Exception as e:
        logger.error("mcp.find_collisions failed: %s", e, exc_info=True)
        return {
            "error": f"Failed to analyze repository: {e}",
            "reference_branch": reference_branch,
            "collisions": [],
            "total_risk_score": 0.0,
        }

    collisions: list[dict[str, Any]] = []
    for (i, j), entry in sorted(context.tensor.entries.items(), key=lambda item: item[1].omega, reverse=True):
        if i == j:
            continue

        conflicts_detail: list[dict[str, Any]] = []
        conflicting_files: set[str] = set()
        conflicting_symbols: set[str] = set()  # dsa:ignore

        for left, right in iter_contact_pairs(context, entry):
            file = left.file or right.file
            sym = left.get_target_name() or right.get_target_name()
            if file:
                conflicting_files.add(file)
            if sym:
                conflicting_symbols.add(sym)
            commutes = classify(left, right) == CommutativityClass.COMMUTE
            conflicts_detail.append({
                "file": file,
                "symbol": sym,
                "branch_a_operator": left.operator.value,
                "branch_b_operator": right.operator.value,
                "commutes": commutes,
                "symbol_id": left.symbol_id or right.symbol_id,
            })

        collisions.append({
            "branch_a": entry.i,
            "branch_b": entry.j,
            "collision_score": round(entry.omega, 3),
            "reasons": list(entry.reasons),
            "conflicting_files": sorted(conflicting_files),
            "conflicting_symbols": sorted(conflicting_symbols),
            "conflicts": conflicts_detail[:25],
            "summary": f"Collision between {entry.i} and {entry.j} (risk: {entry.omega:.2f}) due to {', '.join(entry.reasons)}",
        })

    return {
        "reference_branch": reference_branch,
        "total_risk_score": round(context.tensor.merge_risk, 3),
        "branch_count": len(context.branches),
        "branches": list(context.branches),
        "collision_count": len(collisions),
        "collisions": collisions,
        "drift_magnitudes": {
            b: round(mag, 3) for b, mag in context.drift_magnitudes.items()
        },
    }


def get_merge_order(
    reference_branch: str = "main",
    repo_path: str = ".",
    branches: list[str] | None = None,
    exclude_branches: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate optimal merge sequence across active branches minimizing drift and friction."""
    path = str(Path(repo_path).resolve())
    try:
        context = build_analysis_context(
            path,
            reference_branch,
            branches=branches,
            exclude_branches=exclude_branches,
        )
    except AnalysisContextError as e:
        return {
            "error": str(e),
            "reference_branch": reference_branch,
            "recommended_order": [],
            "steps": [],
        }
    except Exception as e:
        return {
            "error": f"Failed to compute merge order: {e}",
            "reference_branch": reference_branch,
            "recommended_order": [],
            "steps": [],
        }

    if not context.branches:
        return {
            "reference_branch": reference_branch,
            "recommended_order": [],
            "steps": [],
            "message": "No diverging branches found to merge.",
        }

    costs: dict[tuple[Hashable, Hashable], float] = {}
    for (i, j), entry in context.tensor.entries.items():
        costs[(i, j)] = entry.omega
        costs[(j, i)] = entry.omega

    plan = plan_merge_order(list(context.branches), costs)
    ordered_branches = [str(b) for b in plan.order]

    steps: list[dict[str, Any]] = []
    for idx, b in enumerate(ordered_branches, 1):
        drift = context.drift_magnitudes.get(b, 0.0)
        col_step = plan.steps[idx - 2].omega if idx > 1 and len(plan.steps) >= idx - 1 else 0.0
        rationale = (
            f"Step {idx}: Merge '{b}' first (low initial collision friction {col_step:.2f}, drift: {drift:.2f})."
            if idx == 1
            else f"Step {idx}: Merge '{b}' (transition collision cost: {col_step:.2f})."
        )
        steps.append({
            "step": idx,
            "branch": b,
            "drift_magnitude": round(drift, 3),
            "transition_omega": round(col_step, 3),
            "rationale": rationale,
        })

    return {
        "reference_branch": reference_branch,
        "recommended_order": ordered_branches,
        "steps": steps,
        "baseline_cost": round(plan.baseline_cost, 3),
        "optimized_cost": round(plan.proposed_cost, 3),
        "heuristic": plan.heuristic,
    }


def inspect_symbol_impact(symbol: str, reference_branch: str = "main", repo_path: str = ".") -> dict[str, Any]:
    """Inspect dependency graph to find downstream callers and modifying branches for a symbol."""
    path = str(Path(repo_path).resolve())
    graph = build_code_graph_from_repo(path)
    impact_ids = graph.get_downstream_impact(symbol)

    observer = GitObserver(path)
    parser = ASTParser()
    extractor = TransformExtractor()
    modifying_branches: list[str] = []

    if observer.is_valid() and observer.repo:
        local_branches = observer.list_local_branches()
        for branch in local_branches:
            if branch == reference_branch:
                continue
            try:
                ops = extract_trajectory_operators(
                    observer, parser, extractor, ref_branch=reference_branch, head=branch
                )
                for op in ops:
                    name = op.get_target_name()
                    if name == symbol or (op.symbol_id and symbol in op.symbol_id):
                        modifying_branches.append(branch)
                        break
            except Exception:
                continue

    node_data: dict[str, Any] = {}
    resolved_id = graph.find_node_by_name(symbol)
    if resolved_id and resolved_id in graph.g:
        raw_data = dict(graph.g.nodes[resolved_id])
        node_data = {
            "node_id": resolved_id,
            "name": raw_data.get("name", symbol),
            "type": raw_data.get("type", "unknown"),
            "file": raw_data.get("chart_location") or raw_data.get("file", ""),
            "signature": raw_data.get("signature", ""),
        }

    return {
        "symbol": symbol,
        "node_info": node_data,
        "downstream_impact_count": len(impact_ids),
        "downstream_impact": sorted(list(impact_ids))[:100],
        "modifying_branches": sorted(modifying_branches),
    }


def _serialize_op(op: SemanticOperator) -> dict[str, Any]:
    return {
        "operator": op.operator.value,
        "file": op.file,
        "name": op.name,
        "symbol_id": op.symbol_id,
        "from_name": op.from_name,
        "to_name": op.to_name,
    }


def plan_semantic_rebase(
    source_branch: str,
    target_branch: str,
    reference_branch: str = "main",
    repo_path: str = ".",
    branches: list[str] | None = None,
    exclude_branches: list[str] | None = None,
) -> dict[str, Any]:
    """Compute semantic rebase plan: identifies cleanly commuting vs blocked operators."""
    path = str(Path(repo_path).resolve())
    effective_branches = branches
    if effective_branches is not None:
        effective_branches = list(set(effective_branches) | {source_branch, target_branch})
    try:
        context = build_analysis_context(
            path,
            reference_branch,
            branches=effective_branches,
            exclude_branches=exclude_branches,
        )
    except AnalysisContextError as e:
        return {"error": str(e), "source_branch": source_branch, "target_branch": target_branch}
    except Exception as e:
        return {"error": f"Failed to plan rebase: {e}", "source_branch": source_branch, "target_branch": target_branch}

    ops_source = list(context.branch_operators.get(source_branch, ()))
    ops_target = list(context.branch_operators.get(target_branch, ()))

    plan = build_transport_plan(ops_source, ops_target)
    return {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "total_source_operators": len(ops_source),
        "cleanly_applicable_count": len(plan.kept),
        "cleanly_applicable": [_serialize_op(op) for op in plan.kept],  # dsa:ignore
        "already_applied_count": len(plan.already_applied),
        "already_applied": [_serialize_op(op) for op in plan.already_applied],  # dsa:ignore
        "blocked_by_interference_count": len(plan.blocked),
        "blocked_by_interference": [_serialize_op(op) for op in plan.blocked],  # dsa:ignore
        "file_remaps": dict(plan.file_remaps),
    }


def _apply_unified_diff(
    original_text: str, patch_text: str
) -> tuple[bool, str, str | None, int, int]:
    """Apply a unified diff in-memory to text. Returns (success, patched_text, error, added_count, removed_count)."""
    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    lines = patch_text.splitlines()
    orig_lines = original_text.splitlines()

    hunk_indices = [idx for idx, line in enumerate(lines) if hunk_re.match(line)]
    if not hunk_indices:
        return False, "", "No @@ hunk headers found in patch.", 0, 0

    num_orig_lines = len(orig_lines)
    orig_idx = 0
    result_lines: list[str] = []
    added = 0
    removed = 0

    for i, h_idx in enumerate(hunk_indices):
        header_line = lines[h_idx]
        m = hunk_re.match(header_line)
        if not m:
            continue
        old_start = int(m.group(1))
        target_orig_idx = max(0, old_start - 1)

        while orig_idx < target_orig_idx and orig_idx < num_orig_lines:
            result_lines.append(orig_lines[orig_idx])
            orig_idx += 1

        next_h_idx = hunk_indices[i + 1] if i + 1 < len(hunk_indices) else len(lines)
        hunk_body = lines[h_idx + 1 : next_h_idx]

        for line in hunk_body:
            if not line:
                continue
            marker = line[0]
            content = line[1:]
            if marker == " ":
                if orig_idx < num_orig_lines:
                    if orig_lines[orig_idx] != content:
                        return (
                            False,
                            "",
                            f"Hunk at line {old_start} context mismatch: expected '{content}', but base file has '{orig_lines[orig_idx]}'.",
                            added,
                            removed,
                        )
                    result_lines.append(orig_lines[orig_idx])
                    orig_idx += 1
                else:
                    result_lines.append(content)
            elif marker == "-":
                if orig_idx < num_orig_lines:
                    if orig_lines[orig_idx] != content:
                        return (
                            False,
                            "",
                            f"Hunk at line {old_start} delete mismatch: expected '{content}', but base file has '{orig_lines[orig_idx]}'.",
                            added,
                            removed,
                        )
                    orig_idx += 1
                    removed += 1
                else:
                    return (
                        False,
                        "",
                        f"Hunk at line {old_start} delete exceeds base file length.",
                        added,
                        removed,
                    )
            elif marker == "+":
                result_lines.append(content)
                added += 1
            elif marker == "\\":
                continue

    while orig_idx < num_orig_lines:
        result_lines.append(orig_lines[orig_idx])
        orig_idx += 1

    patched_text = "\n".join(result_lines)
    if original_text.endswith("\n") or not original_text:
        patched_text += "\n"

    return True, patched_text, None, added, removed


def validate_patch(patch: str, file_path: str, repo_path: str = ".") -> dict[str, Any]:
    """Validate unified diff patch syntax and target boundaries in a sandbox."""
    hunk_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    lines = patch.splitlines()
    hunks = [line for line in lines if hunk_re.match(line)]  # dsa:ignore
    if not hunks and not any(line.startswith("+++ ") for line in lines):
        return {
            "valid": False,
            "file_path": file_path,
            "error": "Patch format error: not a valid unified diff (missing hunks or diff headers).",
        }

    full_path = Path(repo_path) / file_path
    if full_path.exists() and full_path.is_file():
        original_text = full_path.read_text(encoding="utf-8", errors="ignore")
    else:
        implied_lines: list[str] = []
        in_hunk = False
        for line in lines:
            if hunk_re.match(line):  # dsa:ignore
                in_hunk = True
                continue
            if in_hunk and (line.startswith(" ") or line.startswith("-")):
                implied_lines.append(line[1:])
        original_text = "\n".join(implied_lines) + ("\n" if implied_lines else "")

    success, patched_text, err, added, removed = _apply_unified_diff(original_text, patch)
    if not success:
        return {
            "valid": False,
            "file_path": file_path,
            "error": err or "Failed to apply patch hunks.",
        }

    # If it is a Python file, verify that the resulting patched text has zero syntax errors
    if Path(file_path).suffix == ".py":
        try:
            ast.parse(patched_text)
        except SyntaxError as e:
            return {
                "valid": False,
                "file_path": file_path,
                "error": f"Patched code produces Python syntax error at line {e.lineno}: {e.msg}",
            }

    return {
        "valid": True,
        "file_path": file_path,
        "error": None,
        "hunks_applied": len(hunks),
        "lines_added": added,
        "lines_removed": removed,
        "syntax_valid": True,
        "message": "Patch validated successfully: applied cleanly and passed syntax verification.",
    }


def sandbox_validate_patch(
    patch: str,
    repo_path: str = ".",
    target_branch: str = "HEAD",
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Execute dry-run sandboxed patch validation in an ephemeral Git worktree."""
    from gdss.validation.sandbox import validate_patch as run_sandbox_validate

    report = run_sandbox_validate(
        repo_path=repo_path,
        patch_content=patch,
        target_branch=target_branch,
        timeout_seconds=timeout_seconds,
    )
    return {
        "status": report.status.value,
        "clean": report.is_clean,
        "patch_applied": report.patch_applied,
        "duration_ms": round(report.duration_ms, 2),
        "error_summary": report.error_summary,
        "syntax": {
            "valid": report.syntax.valid,
            "language": report.syntax.language,
            "error_message": report.syntax.error_message,
            "line_number": report.syntax.line_number,
        },
        "types": {
            "checked": report.types.checked,
            "passed": report.types.passed,
            "tool": report.types.tool,
            "output": report.types.output,
        },
        "tests": {
            "executed": report.tests.executed,
            "passed": report.tests.passed,
            "tool": report.tests.tool,
            "tests_run": report.tests.tests_run,
            "tests_passed": report.tests.tests_passed,
            "tests_failed": report.tests.tests_failed,
            "output": report.tests.output,
        },
    }
