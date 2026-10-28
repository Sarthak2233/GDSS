#!/usr/bin/env python3
"""GDSS architecture fitness sensor (computational, deterministic).

Enforces the two structural invariants of GDSS by statically analyzing imports
across ``gdss/``:

1. Two-brain purity: the deterministic brain (core, graph, watcher) must never
   import the probabilistic brain (ai, embeddings).
2. Layer direction: a module may only import equal-or-lower layers. Entrypoints
   (cli, api, daemon) may import any layer.

This sensor never modifies code; it only reads it. Failures are written for
agents as WHAT / WHY / FIX so they can self-correct. Exit code 0 = clean,
1 = violations found.

Tighten this sensor (add layers/rules) via the ratchet principle as the codebase
grows; see .cursor/skills/audit-harness.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Layer rank: higher number = higher layer. A module may import only
# equal-or-lower ranks. Packages not listed are skipped by the layer check
# (keeps the sensor precise with zero false positives).
LAYER_RANK: dict[str, int] = {
    "watcher": 2,
    "core": 4,
    "reducers": 4,
    "graph": 5,
    "embeddings": 6,
    "conflict": 7,
    "drift": 8,
    "ai": 9,
    "validation": 10,
}

# Entrypoints / wiring packages may depend on anything.
ENTRYPOINTS: set[str] = {"cli", "api", "daemon", "mcp"}

# Two-brain partition: deterministic brain must never import probabilistic brain.
DETERMINISTIC: set[str] = {"core", "reducers", "graph", "watcher", "mcp"}
PROBABILISTIC: set[str] = {"ai", "embeddings"}

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "gdss"


def subpackage_of(path: Path) -> str | None:
    """Return the top-level gdss subpackage for a file, e.g. 'core'."""
    try:
        rel = path.relative_to(PKG)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2:  # gdss/<sub>/<file>.py
        return parts[0]
    return None  # a file directly under gdss/ (e.g. __init__.py)


def imported_subpackages(tree: ast.AST) -> list[tuple[str, int]]:
    """Yield (gdss_subpackage, lineno) for every gdss.* import in the module."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                sub = _gdss_sub(alias.name)
                if sub:
                    found.append((sub, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative imports stay within the same package
            sub = _gdss_sub(node.module or "")
            if sub:
                found.append((sub, node.lineno))
    return found


def _gdss_sub(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 2 and parts[0] == "gdss":
        return parts[1]
    return None


def check() -> list[str]:
    violations: list[str] = []
    if not PKG.is_dir():
        return violations

    for py in sorted(PKG.rglob("*.py")):
        src_sub = subpackage_of(py)
        if src_sub is None:
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:  # surfaced clearly; lint/tests will also catch it
            violations.append(
                f"WHAT: {py.relative_to(ROOT)} failed to parse (line {exc.lineno}).\n"
                f"  WHY: the fitness sensor cannot analyze unparsable code.\n"
                f"  FIX: fix the syntax error: {exc.msg}"
            )
            continue

        rel = py.relative_to(ROOT)
        for dst_sub, lineno in imported_subpackages(tree):
            if dst_sub == src_sub:
                continue

            # Rule 1: two-brain purity (hard rule).
            if src_sub in DETERMINISTIC and dst_sub in PROBABILISTIC:
                violations.append(
                    f"WHAT: {rel}:{lineno} imports gdss.{dst_sub} from the deterministic "
                    f"brain (gdss.{src_sub}).\n"
                    f"  WHY: two-brain purity requires the deterministic brain "
                    f"(core/graph/watcher) to stay independent of the probabilistic brain "
                    f"(ai/embeddings) so its results remain trusted.\n"
                    f"  FIX: remove this import. If AI assistance is needed, invert the "
                    f"dependency so gdss.{dst_sub} depends on gdss.{src_sub} instead."
                )

            # Rule 2: layer direction (only when both sides are ranked and the
            # importer is not an entrypoint).
            if src_sub in ENTRYPOINTS:
                continue
            src_rank = LAYER_RANK.get(src_sub)
            dst_rank = LAYER_RANK.get(dst_sub)
            if src_rank is not None and dst_rank is not None and dst_rank > src_rank:
                violations.append(
                    f"WHAT: {rel}:{lineno} imports gdss.{dst_sub} (layer {dst_rank}) from "
                    f"gdss.{src_sub} (layer {src_rank}).\n"
                    f"  WHY: dependencies must flow downward; a lower layer must not depend "
                    f"on a higher one.\n"
                    f"  FIX: move the shared code to an equal-or-lower layer, or invert the "
                    f"dependency so the higher layer (gdss.{dst_sub}) depends on "
                    f"gdss.{src_sub}."
                )

    return violations


def main() -> int:
    violations = check()
    if violations:
        print("Architecture fitness: FAIL", file=sys.stderr)
        for v in violations:
            print("- " + v, file=sys.stderr)
        print(
            f"\n{len(violations)} violation(s). See .cursor/rules/10-architecture-invariants.mdc.",
            file=sys.stderr,
        )
        return 1
    print("Architecture fitness: OK (layer direction + two-brain purity hold).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
