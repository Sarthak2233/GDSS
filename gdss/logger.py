"""Centralized structured logging subsystem for GDSS.

Provides zero-dependency logging infrastructure adhering to Two-Brain purity
and layer direction invariants across all GDSS modules and CI workflows.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_DATE_FORMAT = "%H:%M:%S"
_CONFIGURED = False


def is_ci_environment() -> bool:
    """Return True if running in a known CI environment (e.g. GitHub Actions)."""
    return os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("CI") == "true"


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger under the 'gdss' root hierarchy."""
    if not name.startswith("gdss.") and name != "gdss":
        name = f"gdss.{name}"
    return logging.getLogger(name)


def configure_logging(
    level: str | int | None = None,
    log_file: Path | str | None = None,
    json_format: bool = False,
) -> None:
    """Configure GDSS logging handlers, formatters, and root level.

    Resolution for log level:
      1. Explicit `level` argument
      2. Environment variable `GDSS_LOG_LEVEL`
      3. Default: INFO if running in CI, else WARNING
    """
    global _CONFIGURED

    if level is None:
        env_level = os.environ.get("GDSS_LOG_LEVEL")
        if env_level:
            level = env_level.upper()
        elif is_ci_environment():
            level = "INFO"
        else:
            level = "WARNING"

    if isinstance(level, str):
        level_val = getattr(logging, level.upper(), logging.INFO)
    else:
        level_val = level

    root_logger = logging.getLogger("gdss")
    root_logger.setLevel(level_val)
    root_logger.propagate = False

    # Remove existing GDSS handlers to prevent duplicate messages
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Console / Stderr handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level_val)
    if json_format:
        console_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    else:
        console_formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Optional File handler
    file_target = log_file or os.environ.get("GDSS_LOG_FILE")
    if file_target:
        f_path = Path(file_target).resolve()
        f_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(f_path), encoding="utf-8")
        file_handler.setLevel(level_val)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    _CONFIGURED = True


@contextmanager
def ci_group(title: str) -> Iterator[None]:
    """Emit a collapsible log group in GitHub Actions or a clean header locally."""
    in_ci = is_ci_environment()
    if in_ci:
        sys.stdout.write(f"::group::{title}\n")
        sys.stdout.flush()  # dsa:ignore
    try:
        yield
    finally:
        if in_ci:
            sys.stdout.write("::endgroup::\n")
            sys.stdout.flush()  # dsa:ignore
