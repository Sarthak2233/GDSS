"""Tests for .NET / C# validation sandbox detection and configuration precedence."""

from __future__ import annotations

from pathlib import Path

from gdss.validation.languages import get_default_registry
from gdss.validation.test_runner import detect_test_command
from gdss.validation.typechecker import detect_typecheck_command


def test_detect_csharp_by_csproj(tmp_path: Path):
    (tmp_path / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\" />", encoding="utf-8")

    cmd, tool = detect_typecheck_command(tmp_path)
    assert cmd == "dotnet build --no-incremental"
    assert tool == "dotnet"

    test_cmd, test_tool = detect_test_command(tmp_path)
    assert test_cmd == "dotnet test"
    assert test_tool == "dotnet"


def test_detect_csharp_by_sln(tmp_path: Path):
    (tmp_path / "MySolution.sln").write_text("Microsoft Visual Studio Solution File", encoding="utf-8")

    cmd, tool = detect_typecheck_command(tmp_path)
    assert cmd == "dotnet build --no-incremental"
    assert tool == "dotnet"

    test_cmd, test_tool = detect_test_command(tmp_path)
    assert test_cmd == "dotnet test"
    assert test_tool == "dotnet"


def test_detect_csharp_by_slnx(tmp_path: Path):
    (tmp_path / "MySolution.slnx").write_text("<Solution />", encoding="utf-8")

    cmd, tool = detect_typecheck_command(tmp_path)
    assert cmd == "dotnet build --no-incremental"
    assert tool == "dotnet"

    test_cmd, test_tool = detect_test_command(tmp_path)
    assert test_cmd == "dotnet test"
    assert test_tool == "dotnet"


def test_config_override_takes_precedence_over_dotnet_heuristics(tmp_path: Path):
    (tmp_path / "App.csproj").write_text("<Project Sdk=\"Microsoft.NET.Sdk\" />", encoding="utf-8")
    (tmp_path / ".gdss.yml").write_text(
        "validation:\n"
        "  typecheck_command: \"dotnet build src/App.csproj -c Release\"\n"
        "  test_command: \"dotnet test tests/App.Tests.csproj --no-build\"\n",
        encoding="utf-8",
    )

    cmd, tool = detect_typecheck_command(tmp_path)
    assert cmd == "dotnet build src/App.csproj -c Release"
    assert tool == "config"

    test_cmd, test_tool = detect_test_command(tmp_path)
    assert test_cmd == "dotnet test tests/App.Tests.csproj --no-build"
    assert test_tool == "config"


def test_csharp_language_registry_definition():
    registry = get_default_registry()
    lang = registry.get_for_extension(".cs")
    assert lang is not None
    assert lang.name == "csharp"
    assert ".cs" in lang.extensions
    assert ".razor" in lang.extensions
    assert lang.default_typecheck_cmd == "dotnet build --no-incremental"
    assert "{name}Tests.cs" in lang.test_file_patterns
