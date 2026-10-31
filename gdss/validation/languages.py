"""Pluggable multi-language registry for GDSS validation.

Enables GDSS to easily extend validation, syntax parsing, typechecking,
and testing to any programming language beyond the core defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LanguageDefinition:
    """Configuration and defaults for a supported programming language."""

    name: str
    extensions: list[str]
    default_test_cmd: str | None = None
    default_typecheck_cmd: str | None = None
    default_syntax_cmd: str | None = None
    test_file_patterns: list[str] = field(default_factory=list)


class LanguageRegistry:
    """Registry mapping file extensions to language definitions."""

    def __init__(self) -> None:
        self._by_extension: dict[str, LanguageDefinition] = {}

    def register(self, lang: LanguageDefinition) -> None:
        for ext in lang.extensions:
            normalized = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            self._by_extension[normalized] = lang

    def get_for_extension(self, ext: str) -> LanguageDefinition | None:
        normalized = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        return self._by_extension.get(normalized)

    def get_for_file(self, path: Path | str) -> LanguageDefinition | None:
        ext = Path(path).suffix.lower()
        return self.get_for_extension(ext)

    def is_supported(self, path: Path | str) -> bool:
        return self.get_for_file(path) is not None


_DEFAULT_REGISTRY: LanguageRegistry | None = None


def get_default_registry() -> LanguageRegistry:
    """Return the global default language registry preloaded with core languages."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is not None:
        return _DEFAULT_REGISTRY

    registry = LanguageRegistry()

    # Python
    registry.register(
        LanguageDefinition(
            name="python",
            extensions=[".py", ".pyi"],
            default_test_cmd="pytest {test_file}",
            default_typecheck_cmd="mypy {file}",
            test_file_patterns=["test_{name}.py", "{name}_test.py"],
        )
    )

    # TypeScript / JavaScript
    registry.register(
        LanguageDefinition(
            name="typescript",
            extensions=[".ts", ".tsx"],
            default_test_cmd="pnpm test {test_file}",
            default_typecheck_cmd="tsc --noEmit",
            test_file_patterns=[
                "{name}.test.ts",
                "{name}.test.tsx",
                "{name}.spec.ts",
                "{name}.spec.tsx",
            ],
        )
    )
    registry.register(
        LanguageDefinition(
            name="javascript",
            extensions=[".js", ".jsx", ".mjs", ".cjs"],
            default_test_cmd="pnpm test {test_file}",
            default_typecheck_cmd=None,
            test_file_patterns=["{name}.test.js", "{name}.test.jsx", "{name}.spec.js"],
        )
    )

    # Go
    registry.register(
        LanguageDefinition(
            name="go",
            extensions=[".go"],
            default_test_cmd="go test -v ./...",
            default_typecheck_cmd="go vet ./...",
            test_file_patterns=["{name}_test.go"],
        )
    )

    # Rust
    registry.register(
        LanguageDefinition(
            name="rust",
            extensions=[".rs"],
            default_test_cmd="cargo test",
            default_typecheck_cmd="cargo check",
            test_file_patterns=["test_{name}.rs", "{name}_test.rs"],
        )
    )

    # Java / Kotlin
    registry.register(
        LanguageDefinition(
            name="java",
            extensions=[".java"],
            default_test_cmd="./gradlew test",
            default_typecheck_cmd="javac {file}",
            test_file_patterns=["{name}Test.java", "Test{name}.java"],
        )
    )

    # C#
    registry.register(
        LanguageDefinition(
            name="csharp",
            extensions=[".cs"],
            default_test_cmd="dotnet test {test_file}",
            default_typecheck_cmd="dotnet build --no-build-incrementally",
            test_file_patterns=["{name}Tests.cs", "Test{name}.cs"],
        )
    )

    # C
    registry.register(
        LanguageDefinition(
            name="c",
            extensions=[".c"],
            default_test_cmd="gcc -o {test_file} {test_file}",
            default_typecheck_cmd="gcc -fsyntax-only {file}",
            test_file_patterns=["test_{name}.c", "{name}_test.c"],
        )
    )
    _DEFAULT_REGISTRY = registry
    return _DEFAULT_REGISTRY
