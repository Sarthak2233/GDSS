"""Audited suggestion store and persistence for GDSS convergence suggestions.

Saves verified suggestion metadata and candidate patches to .gdss/suggestions/
without mutating Git state, files, or branches.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from gdss.ai.types import Suggestion

SUGGESTIONS_DIR = Path(".gdss") / "suggestions"


def get_suggestions_dir(repo_root: str | Path) -> Path:
    """Return the absolute suggestions directory path for a repository."""
    return Path(repo_root).resolve() / SUGGESTIONS_DIR


def save_suggestion(
    suggestion: Suggestion,
    repo_root: str | Path,
    target_commit: str = "",
) -> Path:
    """Save suggestion metadata and patch text to .gdss/suggestions/<id>.json."""
    store_dir = get_suggestions_dir(repo_root)
    store_dir.mkdir(parents=True, exist_ok=True)

    data = suggestion.to_local_source()
    data["target_commit"] = target_commit.strip()
    data["saved_at"] = time.time()

    target_file = store_dir / f"{suggestion.suggestion_id}.json"
    target_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return target_file


def load_suggestion(
    suggestion_id: str,
    repo_root: str | Path,
) -> dict[str, Any] | None:
    """Load audited suggestion data by suggestion_id, or None if not found."""
    target_file = get_suggestions_dir(repo_root) / f"{suggestion_id}.json"
    if not target_file.is_file():
        return None
    try:
        return json.loads(target_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_suggestions(repo_root: str | Path) -> list[dict[str, Any]]:
    """List all cached suggestions in the repository."""
    store_dir = get_suggestions_dir(repo_root)
    if not store_dir.is_dir():
        return []

    summaries: list[dict[str, Any]] = []
    for file_path in store_dir.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            summaries.append(
                {
                    "id": data.get("id", file_path.stem),
                    "file_path": data.get("file_path", ""),
                    "symbol_id": data.get("symbol_id", ""),
                    "operator": data.get("operator", ""),
                    "action": data.get("action", ""),
                    "target_commit": data.get("target_commit", ""),
                    "confidence": data.get("confidence", 0.0),
                    "validated": data.get("validated", False),
                    "saved_at": data.get("saved_at", 0.0),
                }
            )
        except Exception:
            continue

    # Sort newest first
    summaries.sort(key=lambda s: s.get("saved_at", 0.0), reverse=True)
    return summaries


def is_suggestion_stale(
    suggestion: dict[str, Any] | Suggestion,
    current_head_sha: str,
) -> bool:
    """Check if a suggestion was calculated for a commit older than current HEAD."""
    if isinstance(suggestion, Suggestion):
        target_commit = getattr(suggestion, "target_commit", "")
    else:
        target_commit = suggestion.get("target_commit", "")

    if not target_commit or not current_head_sha:
        return True

    return target_commit.strip().lower() != current_head_sha.strip().lower()
