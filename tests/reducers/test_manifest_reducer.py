"""Unit tests for ManifestReducer (package.json, pyproject.toml, Cargo.toml)."""

from __future__ import annotations

import json

from gdss.core.transform_types import OperatorType
from gdss.reducers.manifest_reducer import ManifestReducer


def test_manifest_can_handle():
    reducer = ManifestReducer()
    assert reducer.can_handle("package.json")
    assert reducer.can_handle("subproject/package.json")
    assert reducer.can_handle("Cargo.toml")
    assert reducer.can_handle("pyproject.toml")
    assert not reducer.can_handle("main.py")
    assert not reducer.can_handle("README.md")


def test_package_json_add_dependency():
    reducer = ManifestReducer()
    old_data = {"name": "app", "version": "1.0.0", "dependencies": {"express": "^4.18.2"}}
    new_data = {
        "name": "app",
        "version": "1.0.0",
        "dependencies": {"express": "^4.18.2", "axios": "^1.6.0"},
    }

    ops = reducer.extract_operators(
        "package.json",
        json.dumps(old_data),
        json.dumps(new_data),
        commit_sha="c1",
    )

    assert len(ops) == 1
    assert ops[0].operator == OperatorType.ADD_DEPENDENCY
    assert ops[0].name == "axios"
    assert ops[0].file == "package.json"
    assert ops[0].details.get("version") == "^1.6.0"
    assert ops[0].details.get("section") == "dependencies"


def test_package_json_modify_version_constraint():
    reducer = ManifestReducer()
    old_data = {"dependencies": {"express": "^4.18.2"}}
    new_data = {"dependencies": {"express": "^5.0.0"}}

    ops = reducer.extract_operators(
        "package.json",
        json.dumps(old_data),
        json.dumps(new_data),
    )

    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MODIFY_DEPENDENCY
    assert ops[0].name == "express"
    assert ops[0].details.get("old_version") == "^4.18.2"
    assert ops[0].details.get("new_version") == "^5.0.0"


def test_package_json_remove_dependency():
    reducer = ManifestReducer()
    old_data = {"dependencies": {"express": "^4.18.2", "lodash": "^4.17.21"}}
    new_data = {"dependencies": {"express": "^4.18.2"}}

    ops = reducer.extract_operators(
        "package.json",
        json.dumps(old_data),
        json.dumps(new_data),
    )

    assert len(ops) == 1
    assert ops[0].operator == OperatorType.REMOVE_DEPENDENCY
    assert ops[0].name == "lodash"


def test_pyproject_toml_dependencies():
    reducer = ManifestReducer()
    old_toml = """
[project]
name = "gdss"
dependencies = [
    "gitpython>=3.1.0",
]
"""
    new_toml = """
[project]
name = "gdss"
dependencies = [
    "gitpython>=3.1.0",
    "rich>=13.0",
]
"""
    ops = reducer.extract_operators("pyproject.toml", old_toml, new_toml)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.ADD_DEPENDENCY
    assert ops[0].name == "rich"


def test_cargo_toml_dependencies():
    reducer = ManifestReducer()
    old_toml = """
[dependencies]
serde = "1.0"
"""
    new_toml = """
[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }
"""
    ops = reducer.extract_operators("Cargo.toml", old_toml, new_toml)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.ADD_DEPENDENCY
    assert ops[0].name == "tokio"


def test_malformed_manifest_handles_gracefully():
    reducer = ManifestReducer()
    ops = reducer.extract_operators("package.json", "invalid json {{{", "}")
    assert ops == []
