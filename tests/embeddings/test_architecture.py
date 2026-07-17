"""Two-brain: deterministic packages must not import embeddings."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DETERMINISTIC = {"core", "graph", "watcher"}


def test_deterministic_brain_does_not_import_embeddings():
    pkg = ROOT / "gdss"
    offenders = []
    for path in pkg.rglob("*.py"):
        rel = path.relative_to(pkg)
        if len(rel.parts) < 2:
            continue
        sub = rel.parts[0]
        if sub not in DETERMINISTIC:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("gdss.embeddings"):
                        offenders.append(f"{path}:{node.lineno}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith("gdss.embeddings"):
                    offenders.append(f"{path}:{node.lineno}")
    assert offenders == [], f"deterministic brain imported embeddings: {offenders}"
