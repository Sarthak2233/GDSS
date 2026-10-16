"""Architecture: conflict (layer 7) must not import drift (layer 8)."""

import ast
from pathlib import Path

CONFLICT_ROOT = Path(__file__).resolve().parents[2] / "gdss" / "conflict"


def test_conflict_does_not_import_drift():
    violations: list[str] = []
    for path in CONFLICT_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "gdss.drift" or alias.name.startswith("gdss.drift."):
                        violations.append(f"{path.name}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "gdss.drift" or mod.startswith("gdss.drift."):
                    violations.append(f"{path.name}:{node.lineno} from {mod}")
    assert violations == [], f"conflict→drift upward imports: {violations}"
