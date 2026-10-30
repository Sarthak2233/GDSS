"""Tests for the unified GDSS logging subsystem."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from gdss.logger import ci_group, configure_logging, get_logger, is_ci_environment


def test_get_logger_prefix() -> None:
    logger = get_logger("gdss.validation.pr_audit")
    assert logger.name == "gdss.validation.pr_audit"

    # Test that prefixing is applied automatically if omitted
    short_logger = get_logger("ai.condensation")
    assert short_logger.name == "gdss.ai.condensation"


def test_configure_logging_levels() -> None:
    # Test setting DEBUG level
    configure_logging(level="DEBUG")
    root_gdss = logging.getLogger("gdss")
    assert root_gdss.level == logging.DEBUG

    # Test setting INFO level
    configure_logging(level="INFO")
    assert root_gdss.level == logging.INFO

    # Test setting WARNING level
    configure_logging(level="WARNING")
    assert root_gdss.level == logging.WARNING


def test_configure_logging_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GDSS_LOG_LEVEL", "DEBUG")
    configure_logging(level=None)
    root_gdss = logging.getLogger("gdss")
    assert root_gdss.level == logging.DEBUG


def test_configure_logging_file_output(tmp_path: Path) -> None:
    log_file = tmp_path / "gdss_test.log"
    configure_logging(level="INFO", log_file=log_file)

    logger = get_logger("gdss.test.file")
    logger.info("Verification message for file logging")

    # Flush handlers
    for h in logging.getLogger("gdss").handlers:
        h.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Verification message for file logging" in content
    assert "gdss.test.file" in content


def test_ci_group_in_github_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    stream = io.StringIO()

    with patch("sys.stdout", stream):
        with ci_group("Test Phase In CI"):
            print("Running step inside group")

    output = stream.getvalue()
    assert "::group::Test Phase In CI" in output
    assert "Running step inside group" in output
    assert "::endgroup::" in output


def test_ci_group_in_local_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert not is_ci_environment()
    stream = io.StringIO()

    with patch("sys.stdout", stream):
        with ci_group("Test Phase Local"):
            print("Step executed")

    output = stream.getvalue()
    # Should not produce GitHub Actions workflow commands
    assert "::group::" not in output
    assert "::endgroup::" not in output
    assert "Step executed" in output
