"""Semantic Reducer for dependency manifests (package.json, pyproject.toml, Cargo.toml)."""

from __future__ import annotations

import json
import re
from typing import Any

from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.reducers.manifest")

_MANIFEST_FILENAMES = frozenset({"package.json", "cargo.toml", "pyproject.toml"})
_DEP_SECTIONS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


class ManifestReducer:
    """Extracts dependency operators from package.json, Cargo.toml, pyproject.toml."""

    def can_handle(self, file_path: str, content: str | None = None) -> bool:
        lower = file_path.lower()
        base_name = lower.split("/")[-1]
        if base_name in _MANIFEST_FILENAMES:
            return True
        if content:
            stripped = content.strip()
            if stripped.startswith("{") and '"dependencies"' in stripped:
                return True
            if "[dependencies]" in stripped or "[project.dependencies]" in stripped:
                return True
        return False

    def extract_operators(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str = "",
    ) -> list[SemanticOperator]:
        lower = file_path.lower()
        if lower.endswith(".json") or (new_content and new_content.strip().startswith("{")):
            return self._extract_json(file_path, old_content, new_content, commit_sha)
        if lower.endswith("pyproject.toml") or (new_content and "[project" in new_content):
            return self._extract_pyproject(file_path, old_content, new_content, commit_sha)
        if lower.endswith("cargo.toml") or (new_content and "[dependencies]" in new_content):
            return self._extract_cargo(file_path, old_content, new_content, commit_sha)
        return []

    def _extract_json(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str,
    ) -> list[SemanticOperator]:
        try:
            old_data = json.loads(old_content) if old_content else {}
        except Exception:
            old_data = {}
        try:
            new_data = json.loads(new_content) if new_content else {}
        except Exception:
            return []

        operators: list[SemanticOperator] = []

        for section in _DEP_SECTIONS:
            old_deps: dict[str, Any] = (
                old_data.get(section, {}) if isinstance(old_data, dict) else {}
            )
            new_deps: dict[str, Any] = (
                new_data.get(section, {}) if isinstance(new_data, dict) else {}
            )
            if not isinstance(old_deps, dict):
                old_deps = {}
            if not isinstance(new_deps, dict):
                new_deps = {}

            all_pkgs = set(old_deps.keys()) | set(new_deps.keys())
            for pkg in sorted(all_pkgs):
                old_ver = old_deps.get(pkg)
                new_ver = new_deps.get(pkg)
                old_str = str(old_ver) if old_ver is not None else ""
                new_str = str(new_ver) if new_ver is not None else ""

                if old_ver is None and new_ver is not None:
                    operators.append(
                        SemanticOperator(
                            operator=OperatorType.ADD_DEPENDENCY,
                            file=file_path,
                            commit=commit_sha,
                            name=pkg,
                            details={"version": new_str, "section": section},
                            symbol_id=f"manifest::{file_path}::{section}.{pkg}",
                        )
                    )
                elif old_ver is not None and new_ver is None:
                    operators.append(
                        SemanticOperator(
                            operator=OperatorType.REMOVE_DEPENDENCY,
                            file=file_path,
                            commit=commit_sha,
                            name=pkg,
                            details={"old_version": old_str, "section": section},
                            symbol_id=f"manifest::{file_path}::{section}.{pkg}",
                        )
                    )
                elif old_ver != new_ver:
                    operators.append(
                        SemanticOperator(
                            operator=OperatorType.MODIFY_DEPENDENCY,
                            file=file_path,
                            commit=commit_sha,
                            name=pkg,
                            details={
                                "old_version": old_str,
                                "new_version": new_str,
                                "section": section,
                            },
                            symbol_id=f"manifest::{file_path}::{section}.{pkg}",
                        )
                    )

        return operators

    def _extract_pyproject(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str,
    ) -> list[SemanticOperator]:
        old_deps = self._parse_pyproject_deps(old_content or "")
        new_deps = self._parse_pyproject_deps(new_content or "")
        return self._diff_dep_dicts(file_path, old_deps, new_deps, commit_sha, "dependencies")

    def _parse_pyproject_deps(self, content: str) -> dict[str, str]:
        deps: dict[str, str] = {}
        # Parse standard PEP 621 dependencies = [ "package>=1.0", ... ]
        in_deps = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("dependencies = ["):
                in_deps = True
                continue
            if in_deps:
                if line.startswith("]"):
                    in_deps = False
                    continue
                cleaned = line.strip("\",'")
                if cleaned:
                    parts = re.split(r"([><=~^!]+.*)", cleaned, maxsplit=1)
                    pkg = parts[0].strip()
                    ver = parts[1].strip() if len(parts) > 1 else "*"
                    if pkg:
                        deps[pkg] = ver
        return deps

    def _extract_cargo(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str,
    ) -> list[SemanticOperator]:
        old_deps = self._parse_cargo_deps(old_content or "")
        new_deps = self._parse_cargo_deps(new_content or "")
        return self._diff_dep_dicts(file_path, old_deps, new_deps, commit_sha, "dependencies")

    def _parse_cargo_deps(self, content: str) -> dict[str, str]:
        deps: dict[str, str] = {}
        in_deps = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("[dependencies]") or line.startswith("[dev-dependencies]"):
                in_deps = True
                continue
            if line.startswith("[") and in_deps:
                in_deps = False
                continue
            if in_deps and "=" in line:
                pkg, val = [p.strip() for p in line.split("=", 1)]
                clean_val = val.strip("\",'")
                if clean_val.startswith("{"):
                    # Table form: tokio = { version = "1.0", ... }
                    m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', clean_val)
                    deps[pkg] = m.group(1) if m else "*"
                else:
                    deps[pkg] = clean_val
        return deps

    def _diff_dep_dicts(
        self,
        file_path: str,
        old_deps: dict[str, str],
        new_deps: dict[str, str],
        commit_sha: str,
        section: str,
    ) -> list[SemanticOperator]:
        operators: list[SemanticOperator] = []
        all_pkgs = set(old_deps.keys()) | set(new_deps.keys())
        for pkg in sorted(all_pkgs):
            old_ver = old_deps.get(pkg)
            new_ver = new_deps.get(pkg)
            if old_ver is None and new_ver is not None:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.ADD_DEPENDENCY,
                        file=file_path,
                        commit=commit_sha,
                        name=pkg,
                        details={"version": new_ver, "section": section},
                        symbol_id=f"manifest::{file_path}::{section}.{pkg}",
                    )
                )
            elif old_ver is not None and new_ver is None:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.REMOVE_DEPENDENCY,
                        file=file_path,
                        commit=commit_sha,
                        name=pkg,
                        details={"old_version": old_ver, "section": section},
                        symbol_id=f"manifest::{file_path}::{section}.{pkg}",
                    )
                )
            elif old_ver != new_ver:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.MODIFY_DEPENDENCY,
                        file=file_path,
                        commit=commit_sha,
                        name=pkg,
                        details={
                            "old_version": old_ver,
                            "new_version": new_ver,
                            "section": section,
                        },
                        symbol_id=f"manifest::{file_path}::{section}.{pkg}",
                    )
                )
        return operators
