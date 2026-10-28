"""Semantic Reducer for Database Migrations (Alembic, Django, Prisma, Drizzle, Flyway, Rails)."""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.reducers.migration")

_MIGRATION_DIR_SEGMENTS = frozenset(
    {"migrations", "migration", "migrate", "versions", "drizzle", "alembic", "flyway", "prisma"}
)

_ALEMBIC_DOWN_RE = re.compile(r"down_revision\s*[:=]\s*(?:None|['\"](?P<rev>[^'\"]+)['\"])")
_ALEMBIC_REV_RE = re.compile(r"revision\s*[:=]\s*['\"](?P<rev>[^'\"]+)['\"]")
_DJANGO_DEP_RE = re.compile(r"dependencies\s*=\s*\[(?P<deps>[^\]]*)\]", re.DOTALL)
_PRISMA_TIMESTAMP_RE = re.compile(r"(?:^|/)(\d{14})_[^/]+/migration\.sql$")
_FLYWAY_RE = re.compile(r"(?:^|/)V(?P<ver>\d+)(?:__|\b)")
_RAILS_TIMESTAMP_RE = re.compile(r"(?:^|/)(\d{14})_[^/]+\.rb$")


class MigrationDAGReducer:
    """Extracts DAG sequencing and revision operators from database migration files."""

    def can_handle(self, file_path: str, content: str | None = None) -> bool:
        norm = PurePosixPath(file_path)
        parts = {p.lower() for p in norm.parts}

        # 1. Directory pattern check
        if parts & _MIGRATION_DIR_SEGMENTS:
            return True
        if norm.name == "_journal.json" or "meta" in parts:
            return True

        # 2. Content-first sniffer for non-standard paths
        if content:
            if "down_revision" in content:
                return True
            if "from django.db import migrations" in content:
                return True
            if '"entries":' in content and '"dialect":' in content:
                return True

        return False

    def extract_operators(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str = "",
    ) -> list[SemanticOperator]:
        text = new_content or old_content or ""
        norm_path = file_path.replace("\\", "/")

        # 1. Drizzle Metadata Journal (_journal.json)
        if norm_path.endswith("_journal.json"):
            return self._extract_drizzle_journal(file_path, old_content, new_content, commit_sha)

        # 2. Prisma Migrations (timestamp directory)
        prisma_match = _PRISMA_TIMESTAMP_RE.search(norm_path)
        if prisma_match:
            timestamp = prisma_match.group(1)
            return [
                SemanticOperator(
                    operator=OperatorType.MIGRATION_STEP,
                    file=file_path,
                    commit=commit_sha,
                    name=f"migration_timestamp::{timestamp}",
                    details={"framework": "prisma", "timestamp": timestamp},
                    symbol_id=f"migration::prisma::{timestamp}",
                )
            ]

        # 3. Flyway Versioned Migrations (V1__...sql)
        flyway_match = _FLYWAY_RE.search(norm_path)
        if flyway_match:
            ver = flyway_match.group("ver")
            return [
                SemanticOperator(
                    operator=OperatorType.MIGRATION_STEP,
                    file=file_path,
                    commit=commit_sha,
                    name=f"migration_version::V{ver}",
                    details={"framework": "flyway", "version": ver},
                    symbol_id=f"migration::flyway::V{ver}",
                )
            ]

        # 4. Rails / ActiveRecord Migrations (YYYYMMDDHHMMSS_*.rb)
        rails_match = _RAILS_TIMESTAMP_RE.search(norm_path)
        if rails_match:
            timestamp = rails_match.group(1)
            return [
                SemanticOperator(
                    operator=OperatorType.MIGRATION_STEP,
                    file=file_path,
                    commit=commit_sha,
                    name=f"migration_timestamp::{timestamp}",
                    details={"framework": "rails", "timestamp": timestamp},
                    symbol_id=f"migration::rails::{timestamp}",
                )
            ]

        # 5. Alembic Migrations (down_revision = '...')
        if "down_revision" in text:
            m_down = _ALEMBIC_DOWN_RE.search(text)
            m_rev = _ALEMBIC_REV_RE.search(text)
            parent = (m_down.group("rev") or "base") if m_down else "base"
            child = m_rev.group("rev") if m_rev else norm_path.split("/")[-1].replace(".py", "")
            return [
                SemanticOperator(
                    operator=OperatorType.MIGRATION_STEP,
                    file=file_path,
                    commit=commit_sha,
                    name=f"migration_parent::{parent}",
                    details={
                        "framework": "alembic",
                        "revision": child,
                        "parent_revision": parent,
                    },
                    symbol_id=f"migration::alembic::{child}",
                )
            ]

        # 6. Django Migrations (dependencies = [...])
        if "django.db" in text or "migrations.Migration" in text:
            m_deps = _DJANGO_DEP_RE.search(text)
            dep_names: list[str] = []
            if m_deps:
                raw_deps = m_deps.group("deps")
                # Find ('app_name', '0001_initial')
                tuples = re.findall(
                    r"\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)", raw_deps
                )
                dep_names = [f"{app}.{mig}" for app, mig in tuples]

            parent_id = dep_names[0] if dep_names else "initial"
            child_name = norm_path.split("/")[-1].replace(".py", "")
            return [
                SemanticOperator(
                    operator=OperatorType.MIGRATION_STEP,
                    file=file_path,
                    commit=commit_sha,
                    name=f"migration_parent::{parent_id}",
                    details={
                        "framework": "django",
                        "revision": child_name,
                        "dependencies": dep_names,
                    },
                    symbol_id=f"migration::django::{child_name}",
                )
            ]

        return []

    def _extract_drizzle_journal(
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

        old_entries: list[dict[str, Any]] = (
            old_data.get("entries", []) if isinstance(old_data, dict) else []
        )
        new_entries: list[dict[str, Any]] = (
            new_data.get("entries", []) if isinstance(new_data, dict) else []
        )

        old_indices = {e.get("idx") for e in old_entries if isinstance(e, dict)}
        added_entries = [
            e for e in new_entries if isinstance(e, dict) and e.get("idx") not in old_indices  # dsa:ignore
        ]

        operators: list[SemanticOperator] = []
        for e in added_entries:
            idx = e.get("idx")
            tag = e.get("tag", str(idx))
            operators.append(
                SemanticOperator(
                    operator=OperatorType.MIGRATION_STEP,
                    file=file_path,
                    commit=commit_sha,
                    name=f"drizzle_journal_idx::{idx}",
                    details={"framework": "drizzle", "idx": idx, "tag": tag},
                    symbol_id=f"migration::drizzle::idx_{idx}",
                )
            )

        return operators
