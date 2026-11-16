"""Guarded local application of validated suggestions (Phase 6a).

Provides preflight security, AST symbol validation, atomic patch application,
automatic syntax verification rollback, and manual undo without Git mutations.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gdss.ai.suggestion_store import load_suggestion
from gdss.core.ast_parser import ASTParser
from gdss.logger import get_logger
from gdss.validation.syntax import validate_file_syntax

logger = get_logger("gdss.validation.apply")
ROLLBACK_DIR = Path(".gdss") / "rollback"
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_GIT_RE = re.compile(r"^diff --git a/(.+?) b/(.+)")
_DIFF_OLD_RE = re.compile(r"^--- (?:a/)?(.+)")
_DIFF_NEW_RE = re.compile(r"^\+\+\+ (?:b/)?(.+)")


@dataclass
class PreflightResult:
    valid: bool
    target_file: Path | None = None
    symbol_id: str | None = None
    strategy: str | None = None
    patch_text: str | None = None
    error: str | None = None
    what: str = ""
    why: str = ""
    fix: str = ""


@dataclass
class ApplyResult:
    success: bool
    suggestion_id: str
    target_file: str
    strategy: str
    diff: str = ""
    rollback_id: str | None = None
    error: str | None = None
    what: str = ""
    why: str = ""
    fix: str = ""


@dataclass
class RollbackResult:
    success: bool
    suggestion_id: str
    target_file: str
    restored: bool = False
    error: str | None = None
    what: str = ""
    why: str = ""
    fix: str = ""


def get_git_head_sha(repo_root: Path) -> str:
    """Return the current HEAD commit SHA, or empty string if git fails."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def get_rollback_dir(repo_root: str | Path) -> Path:
    """Return the directory storing rollback backups."""
    return Path(repo_root).resolve() / ROLLBACK_DIR


def verify_symbol_present(file_path: Path, expected_symbol_id: str) -> bool:
    """Check if the target symbol_id exists in the file via AST parsing."""
    try:
        symbols = ASTParser().parse_file(str(file_path))
        for sym in symbols:
            if sym.symbol_id == expected_symbol_id:
                return True
            if sym.name and expected_symbol_id.endswith(f"::{sym.name}"):
                return True
        return False
    except Exception:
        return False


def _format_error(what: str, why: str, fix: str) -> str:
    return f"WHAT: {what}\nWHY:  {why}\nFIX:  {fix}"


def _fail_preflight(what: str, why: str, fix: str) -> PreflightResult:
    return PreflightResult(
        valid=False,
        what=what,
        why=why,
        fix=fix,
        error=_format_error(what, why, fix),
    )


def _fail_apply(
    suggestion_id: str,
    target_file: str,
    strategy: str,
    what: str,
    why: str,
    fix: str,
) -> ApplyResult:
    return ApplyResult(
        success=False,
        suggestion_id=suggestion_id,
        target_file=target_file,
        strategy=strategy,
        what=what,
        why=why,
        fix=fix,
        error=_format_error(what, why, fix),
    )


def _fail_rollback(
    suggestion_id: str,
    what: str,
    why: str,
    fix: str,
) -> RollbackResult:
    return RollbackResult(
        success=False,
        suggestion_id=suggestion_id,
        target_file="",
        what=what,
        why=why,
        fix=fix,
        error=_format_error(what, why, fix),
    )


def preflight_check(
    suggestion_data: dict[str, Any],
    repo_root: str | Path,
    strategy_name: str | None = None,
    current_head_sha: str | None = None,
) -> PreflightResult:
    """Run guarded preflight checks before applying any suggestion."""
    root_path = Path(repo_root).resolve()
    suggestion_id = suggestion_data.get("id", "unknown")

    # 1. Repository root verification
    if not (root_path / ".git").exists():
        what = f"Invalid repository root: {root_path}"
        why = "Directory does not contain a .git directory."
        fix = "Ensure gdss apply is executed from or pointed to a valid Git repository root."
        return _fail_preflight(what, why, fix)

    # 2. Canonical path & Path traversal protection
    rel_path_str = suggestion_data.get("file_path", "")
    if not rel_path_str:
        what = "Missing file_path in suggestion"
        why = "Suggestion metadata does not specify a target file."
        fix = "Regenerate suggestion using 'gdss suggest'."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    target_file = (root_path / rel_path_str).resolve()
    try:
        target_file.relative_to(root_path)
    except ValueError:
        what = f"Path traversal detected: {rel_path_str}"
        why = f"Resolved path '{target_file}' is outside repository root '{root_path}'."
        fix = "Suggestions can only modify files strictly contained within the repository."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    # 3. Target file existence
    if not target_file.is_file():
        what = f"Target file '{rel_path_str}' not found"
        why = "The target file does not exist in the local working tree."
        fix = "Check out the correct branch or verify the file path."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    # 4. Freshness check against Git HEAD
    active_head = current_head_sha or get_git_head_sha(root_path)
    target_commit = suggestion_data.get("target_commit", "")
    if (
        target_commit
        and active_head
        and target_commit.strip().lower() != active_head.strip().lower()
    ):
        what = f"Stale suggestion '{suggestion_id}'"
        why = f"Suggestion was calculated for commit {target_commit[:10]}, but current HEAD is {active_head[:10]}."
        fix = "Run 'gdss suggest' to regenerate fresh candidate suggestions against current HEAD."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    # 5. AST Symbol Presence check
    symbol_id = suggestion_data.get("symbol_id", "")
    if symbol_id and not verify_symbol_present(target_file, symbol_id):
        what = f"Symbol '{symbol_id}' not found in {rel_path_str}"
        why = "The target symbol has been modified, renamed, or deleted in the working tree."
        fix = "Run 'gdss suggest' to analyze updated symbol locations."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    # 6. Strategy selection and patch content
    combinations = suggestion_data.get("patch_combinations", [])
    num_combos = len(combinations)
    if num_combos == 0:
        what = "No resolution strategies found in suggestion"
        why = "The suggestion does not contain any candidate patches."
        fix = "Run 'gdss suggest' with an AI provider or deterministic combinator."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    avail_names = [str(c.get("strategy") or c.get("label") or "") for c in combinations]
    avail_str = ", ".join(name for name in avail_names if name)

    selected_combo: dict[str, Any] | None = None
    if strategy_name:
        for c in combinations:
            if c.get("strategy") == strategy_name or c.get("label") == strategy_name:
                selected_combo = c
                break
        if not selected_combo:
            what = f"Unknown strategy '{strategy_name}'"
            why = f"Available strategies for this suggestion: {avail_str}"
            fix = "Pass an available strategy name via --strategy <NAME>."
            return _fail_preflight(what, why, fix)  # dsa:ignore
    else:
        if num_combos == 1:
            selected_combo = combinations[0]
        else:
            what = "Multiple resolution strategies available"
            why = f"Suggestion has {num_combos} strategies: {avail_str}"
            fix = "Specify which strategy to apply via --strategy <NAME>."
            return _fail_preflight(what, why, fix)  # dsa:ignore

    assert selected_combo is not None
    patch_text = selected_combo.get("patch_text")
    if not patch_text or not patch_text.strip():
        what = f"Strategy '{selected_combo.get('strategy')}' has no patch content"
        why = "The selected strategy does not contain executable diff or code text."
        fix = "Regenerate suggestion or choose an alternate strategy."
        return _fail_preflight(what, why, fix)  # dsa:ignore

    return PreflightResult(
        valid=True,
        target_file=target_file,
        symbol_id=symbol_id,
        strategy=selected_combo.get("strategy") or selected_combo.get("label") or "default",
        patch_text=patch_text,
    )


def parse_multi_file_unified_diff(
    patch_text: str, default_file: str = ""
) -> dict[str, str]:
    """Parse a unified diff string, potentially containing hunks for multiple files.

    Returns a dict mapping relative file path to its individual unified diff text.
    """
    lines = patch_text.splitlines(keepends=True)
    file_diffs: dict[str, list[str]] = {}
    current_file: str | None = None

    idx = 0
    num_lines = len(lines)
    while idx < num_lines:
        line = lines[idx]
        m_git = _DIFF_GIT_RE.match(line)
        if m_git:
            current_file = m_git.group(1).strip()
            file_diffs.setdefault(current_file, []).append(line)
            idx += 1
            continue

        m_old = _DIFF_OLD_RE.match(line)
        if m_old and idx + 1 < num_lines and _DIFF_NEW_RE.match(lines[idx + 1]):
            matched_file = m_old.group(1).strip()
            if matched_file == "/dev/null":
                m_new = _DIFF_NEW_RE.match(lines[idx + 1])
                matched_file = m_new.group(1).strip() if m_new else ""
            if not current_file or current_file != matched_file:
                current_file = matched_file

            file_diffs.setdefault(current_file, []).append(line)
            file_diffs[current_file].append(lines[idx + 1])
            idx += 2
            continue

        if current_file:
            file_diffs[current_file].append(line)
        idx += 1

    if not file_diffs:
        target = default_file or "target"
        return {target: patch_text}

    return {k: "".join(v) for k, v in file_diffs.items() if k and "".join(v).strip()}


def apply_unified_diff(original_text: str, patch_text: str) -> str:
    """Apply a unified diff string to original_text, returning modified text.

    Raises ValueError with diagnostic details if hunks fail to match.
    """
    orig_lines = original_text.splitlines(keepends=True)
    patch_lines = patch_text.splitlines(keepends=True)

    hunks: list[tuple[int, int, int, int, list[str]]] = []
    current_hunk: list[str] | None = None
    old_start = old_count = new_start = new_count = 0

    for pline in patch_lines:
        m = _HUNK_RE.match(pline)
        if m:
            if current_hunk is not None:
                hunks.append((old_start, old_count, new_start, new_count, current_hunk))
            old_start = int(m.group(1))
            old_count = int(m.group(2) or "1")
            new_start = int(m.group(3))
            new_count = int(m.group(4) or "1")
            current_hunk = []
        elif current_hunk is not None:
            if pline.startswith(("--- ", "+++ ")):
                continue
            current_hunk.append(pline)

    if current_hunk is not None:
        hunks.append((old_start, old_count, new_start, new_count, current_hunk))

    if not hunks:
        raise ValueError("Patch has no unified diff hunks")

    result_lines: list[str] = []
    cursor = 0  # 0-indexed in orig_lines
    total_orig = len(orig_lines)

    for h_old_start, _, _, _, h_lines in hunks:
        target_idx = max(0, h_old_start - 1)
        while cursor < target_idx and cursor < total_orig:
            result_lines.append(orig_lines[cursor])
            cursor += 1

        for line in h_lines:
            if not line:
                continue
            prefix = line[0]
            if prefix == "\\":
                continue

            content = line[1:]
            if not content.endswith("\n"):
                content += "\n"
            content_clean = content.rstrip("\r\n")

            if prefix == " ":
                if cursor < total_orig:
                    if orig_lines[cursor].rstrip("\r\n") != content_clean:
                        raise ValueError(
                            f"Context mismatch at line {cursor + 1}: expected '{content.strip()}', found '{orig_lines[cursor].strip()}'"
                        )
                    result_lines.append(orig_lines[cursor])
                    cursor += 1
                else:
                    result_lines.append(content)
            elif prefix == "-":
                if cursor < total_orig:
                    if orig_lines[cursor].rstrip("\r\n") != content_clean:
                        raise ValueError(
                            f"Deletion mismatch at line {cursor + 1}: expected '{content.strip()}', found '{orig_lines[cursor].strip()}'"
                        )
                    cursor += 1
                else:
                    raise ValueError(f"Unexpected end of file while deleting at line {cursor + 1}")
            elif prefix == "+":
                result_lines.append(content)

    while cursor < total_orig:
        result_lines.append(orig_lines[cursor])
        cursor += 1

    return "".join(result_lines)


def apply_suggestion(
    suggestion_id: str,
    repo_root: str | Path,
    strategy_name: str | None = None,
    dry_run: bool = False,
) -> ApplyResult:
    """Safely apply an approved, validated suggestion to the local working tree."""
    root_path = Path(repo_root).resolve()
    suggestion_data = load_suggestion(suggestion_id, root_path)

    if not suggestion_data:
        what = f"Suggestion '{suggestion_id}' not found in store"
        why = f"File .gdss/suggestions/{suggestion_id}.json does not exist."
        fix = "Run 'gdss suggest' to regenerate suggestions, or check the suggestion ID."
        return _fail_apply(suggestion_id, "", "", what, why, fix)

    # 1. Run guarded preflight check
    logger.info(
        "Executing guarded apply for suggestion '%s' (strategy=%s, dry_run=%s)",
        suggestion_id,
        strategy_name,
        dry_run,
    )
    preflight = preflight_check(
        suggestion_data=suggestion_data,
        repo_root=root_path,
        strategy_name=strategy_name,
    )
    if not preflight.valid or preflight.target_file is None or preflight.patch_text is None:
        logger.warning(
            "Preflight check rejected apply for suggestion '%s': %s", suggestion_id, preflight.what
        )
        return ApplyResult(
            success=False,
            suggestion_id=suggestion_id,
            target_file=str(preflight.target_file or ""),
            strategy=preflight.strategy or "",
            what=preflight.what,
            why=preflight.why,
            fix=preflight.fix,
            error=preflight.error,
        )

    target_file = preflight.target_file
    rel_path = str(target_file.relative_to(root_path))

    # 2. Parse potential multi-file diff hunks
    file_diff_map = parse_multi_file_unified_diff(
        preflight.patch_text, default_file=rel_path
    )

    original_contents: dict[str, str] = {}
    new_contents: dict[str, str] = {}
    diff_parts: list[str] = []

    for f_rel, f_patch in file_diff_map.items():
        f_target = (root_path / f_rel).resolve()
        try:
            f_target.relative_to(root_path)
        except ValueError:
            what = f"Path traversal detected in patch for file '{f_rel}'"
            why = f"Resolved path '{f_target}' is outside repository root '{root_path}'."
            fix = "Multi-file patches can only modify files strictly contained within repository."
            return _fail_apply(suggestion_id, f_rel, preflight.strategy or "", what, why, fix)

        if not f_target.is_file():
            what = f"Target file '{f_rel}' not found"
            why = "One of the files modified by this multi-file patch does not exist."
            fix = "Verify file paths in suggestion metadata."
            return _fail_apply(suggestion_id, f_rel, preflight.strategy or "", what, why, fix)

        orig_text = f_target.read_text(encoding="utf-8")
        original_contents[f_rel] = orig_text

        try:
            patched_text = apply_unified_diff(orig_text, f_patch)
            new_contents[f_rel] = patched_text
        except Exception as e:
            what = f"Failed to apply patch hunks to '{f_rel}'"
            why = str(e)
            fix = "The target file may have diverged. Run 'gdss suggest' to refresh candidate patches."
            logger.warning("Unified diff application failed for '%s': %s", f_rel, e)
            return _fail_apply(suggestion_id, f_rel, preflight.strategy or "", what, why, fix)

        orig_lines = orig_text.splitlines(keepends=True)
        new_lines = patched_text.splitlines(keepends=True)
        diff_parts.append(
            "".join(
                difflib.unified_diff(
                    orig_lines,
                    new_lines,
                    fromfile=f"a/{f_rel}",
                    tofile=f"b/{f_rel}",
                )
            )
        )

    combined_diff = "\n".join(diff_parts)

    if dry_run:
        logger.info("Dry-run apply simulated successfully for suggestion '%s'", suggestion_id)
        return ApplyResult(
            success=True,
            suggestion_id=suggestion_id,
            target_file=", ".join(new_contents.keys()),
            strategy=preflight.strategy or "",
            diff=combined_diff,
        )

    # 3. Atomic application with multi-file rollback snapshot
    rollback_dir = get_rollback_dir(root_path)
    rollback_dir.mkdir(parents=True, exist_ok=True)
    rb_snapshot = {
        "suggestion_id": suggestion_id,
        "files": original_contents,
        "file_path": rel_path,
        "original_content": original_contents.get(rel_path, ""),
        "applied_at": time.time(),
        "strategy": preflight.strategy,
    }
    rb_file = rollback_dir / f"{suggestion_id}.json"
    rb_file.write_text(json.dumps(rb_snapshot, indent=2), encoding="utf-8")
    logger.debug("Saved rollback snapshot to %s", rb_file)

    # Write all patched contents to working tree
    for f_rel, patched_text in new_contents.items():
        (root_path / f_rel).resolve().write_text(patched_text, encoding="utf-8")

    # 4. Post-apply AST syntax validation across ALL modified files
    for f_rel in new_contents:
        f_target = (root_path / f_rel).resolve()
        syntax_res = validate_file_syntax(f_target)
        if not syntax_res.valid:
            # Automatic rollback on syntax corruption across ALL files!
            for roll_rel, roll_orig in original_contents.items():
                (root_path / roll_rel).resolve().write_text(roll_orig, encoding="utf-8")
            rb_file.unlink(missing_ok=True)

            what = f"Post-apply syntax validation failed on '{f_rel}'"
            why = syntax_res.error_message or "Applied patch resulted in invalid language syntax."
            fix = "The entire multi-file patch was automatically rolled back. No files were modified."
            logger.error(
                "Post-apply syntax check failed on %s. All %d files automatically rolled back.",
                f_rel,
                len(original_contents),
            )
            return _fail_apply(suggestion_id, f_rel, preflight.strategy or "", what, why, fix)

    all_targets_str = ", ".join(new_contents.keys())
    logger.info("Successfully applied suggestion '%s' across [%s]", suggestion_id, all_targets_str)
    return ApplyResult(
        success=True,
        suggestion_id=suggestion_id,
        target_file=all_targets_str,
        strategy=preflight.strategy or "",
        diff=combined_diff,
        rollback_id=suggestion_id,
    )


def rollback_suggestion(
    suggestion_id: str,
    repo_root: str | Path,
) -> RollbackResult:
    """Restore target file from saved rollback snapshot."""
    root_path = Path(repo_root).resolve()
    rb_file = get_rollback_dir(root_path) / f"{suggestion_id}.json"

    if not rb_file.is_file():
        what = f"No rollback record found for suggestion ID '{suggestion_id}'"
        why = "Suggestion was not applied locally or was already rolled back."
        fix = "Check working tree status using 'git status' or 'git diff'."
        logger.warning("Rollback failed: snapshot not found at %s", rb_file)
        return _fail_rollback(suggestion_id, what, why, fix)

    try:
        data = json.loads(rb_file.read_text(encoding="utf-8"))
        rb_file.unlink(missing_ok=True)
        files_map = data.get("files")
        if files_map and isinstance(files_map, dict):
            for rel_file, orig_content in files_map.items():
                target_file = (root_path / rel_file).resolve()
                target_file.write_text(orig_content, encoding="utf-8")
            restored_str = ", ".join(files_map.keys())
            logger.info(
                "Successfully restored [%s] from rollback snapshot for suggestion '%s'",
                restored_str,
                suggestion_id,
            )
            return RollbackResult(
                success=True,
                suggestion_id=suggestion_id,
                target_file=restored_str,
                restored=True,
            )

        rel_path = data.get("file_path", "")
        original_content = data.get("original_content", "")
        target_file = (root_path / rel_path).resolve()
        target_file.write_text(original_content, encoding="utf-8")
        logger.info(
            "Successfully restored '%s' from rollback snapshot for suggestion '%s'",
            rel_path,
            suggestion_id,
        )
        return RollbackResult(
            success=True,
            suggestion_id=suggestion_id,
            target_file=rel_path,
            restored=True,
        )
    except Exception as e:
        what = f"Rollback failed for '{suggestion_id}'"
        why = str(e)
        fix = "Manually inspect target file and Git working tree."
        return _fail_rollback(suggestion_id, what, why, fix)  # dsa:ignore
