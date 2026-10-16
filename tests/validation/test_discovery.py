"""Tests for gdss.validation.discovery (repo layout discovery and .gdss.yml parser)."""
from __future__ import annotations

from gdss.validation.discovery import (
    find_project_root_for_file,
    get_sandbox_timeout,
    load_validation_config,
)


def test_find_project_root_flat(tmp_path):
    repo_root = tmp_path
    pyproject = repo_root / "pyproject.toml"
    pyproject.write_text("[tool.pytest]\n", encoding="utf-8")

    file_path = repo_root / "app.py"
    file_path.write_text("print('hello')\n", encoding="utf-8")

    root = find_project_root_for_file(file_path, repo_root)
    assert root == repo_root


def test_find_project_root_nested_service(tmp_path):
    repo_root = tmp_path
    # Nested microservice / multi-package layout:
    # repo_root/services/auth/package.json
    service_dir = repo_root / "services" / "auth"
    service_dir.mkdir(parents=True)
    (service_dir / "package.json").write_text('{"name": "auth"}', encoding="utf-8")

    file_path = service_dir / "src" / "login.ts"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("export const login = () => {};\n", encoding="utf-8")

    root = find_project_root_for_file(file_path, repo_root)
    assert root == service_dir


def test_find_project_root_fallback_to_repo_root(tmp_path):
    repo_root = tmp_path
    file_path = repo_root / "some" / "deep" / "script.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("x = 1\n", encoding="utf-8")

    # No descriptor anywhere -> falls back to repo_root
    root = find_project_root_for_file(file_path, repo_root)
    assert root == repo_root


def test_load_validation_config_default(tmp_path):
    config = load_validation_config(tmp_path)
    assert config.timeout_seconds == 30
    assert config.test_command is None
    assert config.typecheck_command is None


def test_load_validation_config_from_yaml(tmp_path):
    yaml_content = """
validation:
  test_command: "pytest {test_file}"
  typecheck_command: "mypy {file}"
  timeout_seconds: 45
"""
    (tmp_path / ".gdss.yml").write_text(yaml_content, encoding="utf-8")
    config = load_validation_config(tmp_path)
    assert config.timeout_seconds == 45
    assert config.test_command == "pytest {test_file}"
    assert config.typecheck_command == "mypy {file}"


def test_get_sandbox_timeout_precedence(monkeypatch):
    # Default is 30
    assert get_sandbox_timeout() == 30

    # Config value
    assert get_sandbox_timeout(config_timeout=45) == 45

    # Env var overrides config
    monkeypatch.setenv("GDSS_SANDBOX_TIMEOUT", "60")
    assert get_sandbox_timeout(config_timeout=45) == 60

    # CLI flag overrides env var
    assert get_sandbox_timeout(config_timeout=45, cli_timeout=90) == 90
