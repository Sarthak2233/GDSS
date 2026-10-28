"""Tests for gdss.validation.languages (Pluggable Language Registry)."""

from __future__ import annotations

from gdss.validation.languages import (
    LanguageDefinition,
    LanguageRegistry,
    get_default_registry,
)


def test_default_registry_has_core_languages():
    registry = get_default_registry()

    assert registry.is_supported("services/auth.py") is True
    assert registry.is_supported("components/button.tsx") is True
    assert registry.is_supported("utils/helper.js") is True
    assert registry.is_supported("cmd/server/main.go") is True

    py_lang = registry.get_for_file("test.py")
    assert py_lang is not None
    assert py_lang.name == "python"

    ts_lang = registry.get_for_file("test.ts")
    assert ts_lang is not None
    assert ts_lang.name == "typescript"


def test_custom_language_registration():
    registry = LanguageRegistry()
    assert registry.is_supported("main.rs") is False

    rust_def = LanguageDefinition(
        name="rust",
        extensions=[".rs"],
        default_test_cmd="cargo test",
        default_typecheck_cmd="cargo check",
    )
    registry.register(rust_def)

    assert registry.is_supported("src/main.rs") is True
    lang = registry.get_for_file("src/main.rs")
    assert lang is not None
    assert lang.name == "rust"
    assert lang.default_test_cmd == "cargo test"


def test_unsupported_language_graceful_fallback():
    registry = get_default_registry()
    assert registry.is_supported("script.unknownext") is False
    assert registry.get_for_file("script.unknownext") is None
