"""Tests for root version schema validation, validation lifecycle fields, and migrations framework hint."""

from __future__ import annotations

import logging
from pathlib import Path

from gdss.core.config import GDSSConfig, load_gdss_config


def test_config_version_default(tmp_path: Path) -> None:
    """Verifies that version defaults to 1 when omitted."""
    cfg = load_gdss_config(tmp_path)
    assert isinstance(cfg, GDSSConfig)
    assert cfg.version == 1


def test_config_version_explicit(tmp_path: Path) -> None:
    """Verifies that version: 1 parses cleanly."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
version: 1
validation:
  install_command: "pnpm install"
  mode: "full_suite"
  symlink_dependencies: false
migrations:
  framework: "alembic"
""",
        encoding="utf-8",
    )
    cfg = load_gdss_config(tmp_path)
    assert cfg.version == 1
    assert cfg.validation.install_command == "pnpm install"
    assert cfg.validation.mode == "full_suite"
    assert cfg.validation.symlink_dependencies is False
    assert cfg.migrations.framework == "alembic"


def test_config_unsupported_version_warning(tmp_path: Path, caplog) -> None:
    """Verifies that unsupported or invalid versions log warnings and fall back to 1."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
version: 999
migrations:
  framework: "django"
""",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        cfg = load_gdss_config(tmp_path)
    assert cfg.version == 999
    assert any("Unsupported GDSS schema version" in r.message for r in caplog.records)
    assert cfg.migrations.framework == "django"


def test_config_invalid_non_integer_version_falls_back(tmp_path: Path, caplog) -> None:
    """Verifies that non-integer versions fall back to 1 with a warning."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
version: "invalid_string"
""",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        cfg = load_gdss_config(tmp_path)
    assert cfg.version == 1
    assert any("Invalid 'version' value" in r.message for r in caplog.records)

