"""Tests for deterministic generated code exclusion policy (Ticket 04)."""

from __future__ import annotations

from gdss.core.config import DEFAULT_GENERATED_EXCLUDE_PATTERNS, is_generated_or_excluded


def test_default_generated_exclude_patterns_cover_ecosystems():
    patterns = set(DEFAULT_GENERATED_EXCLUDE_PATTERNS)
    # .NET
    assert "*.Designer.cs" in patterns
    assert "*.g.cs" in patterns
    assert "*.AssemblyInfo.cs" in patterns
    assert "bin/**" in patterns
    assert "obj/**" in patterns
    # Go
    assert "*.pb.go" in patterns
    assert "*.gen.go" in patterns
    # Web / JS
    assert "*.min.js" in patterns
    assert "*.min.css" in patterns


def test_is_generated_or_excluded():
    # Excluded files
    assert is_generated_or_excluded("src/Forms/MainForm.Designer.cs") is True
    assert is_generated_or_excluded("src/Models/User.g.cs") is True
    assert is_generated_or_excluded("src/Models/User.g.i.cs") is True
    assert is_generated_or_excluded("Properties/AssemblyInfo.cs") is True
    assert is_generated_or_excluded("pkg/proto/service.pb.go") is True
    assert is_generated_or_excluded("assets/styles.min.css") is True
    assert is_generated_or_excluded("bin/Debug/net8.0/Api.dll") is True
    assert is_generated_or_excluded("obj/Debug/net8.0/Api.g.cs") is True
    assert is_generated_or_excluded("target/debug/app") is True

    # Real human source files (must NOT be excluded)
    assert is_generated_or_excluded("src/Forms/MainForm.cs") is False
    assert is_generated_or_excluded("src/Models/User.cs") is False
    assert is_generated_or_excluded("pkg/proto/service.go") is False
    assert is_generated_or_excluded("assets/styles.css") is False
    assert is_generated_or_excluded("src/main.py") is False


def test_is_generated_or_excluded_with_user_excludes():
    user_excludes = ["custom_gen/**", "*.mock.ts"]
    assert is_generated_or_excluded("custom_gen/code.py", user_excludes=user_excludes) is True
    assert is_generated_or_excluded("tests/user.mock.ts", user_excludes=user_excludes) is True
    assert is_generated_or_excluded("src/Forms/MainForm.Designer.cs", user_excludes=user_excludes) is True
    assert is_generated_or_excluded("src/regular.ts", user_excludes=user_excludes) is False

