"""Tests for Universal Stack-Agnostic Migration Reducer."""

from __future__ import annotations

from gdss.core.transform_types import OperatorType
from gdss.reducers.migration_reducer import MigrationDAGReducer


def test_migration_reducer_universal_timestamp_any_stack() -> None:
    """Verifies that Knex, TypeORM, Sequelize, Goose timestamps (14 digits) are detected."""
    reducer = MigrationDAGReducer()

    # Knex / TypeORM / Sequelize: 20261104120000_create_users.ts
    path = "src/migrations/20261104120000_create_users.ts"
    assert reducer.can_handle(path)
    ops = reducer.extract_operators(path, None, "export class CreateUsers {}", "sha1")
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert "20261104120000" in ops[0].name
    assert "20261104120000" in ops[0].symbol_id


def test_migration_reducer_universal_sequence_plain_sql() -> None:
    """Verifies that sequential migrations (001_create_orders.sql or 0001.up.sql) are detected."""
    reducer = MigrationDAGReducer()

    # Golang-migrate / Goose / plain SQL: 000001_init.up.sql
    path = "database/migrations/000001_init.up.sql"
    assert reducer.can_handle(path)
    ops = reducer.extract_operators(path, None, "CREATE TABLE orders (id INT);", "sha2")
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert "000001" in ops[0].symbol_id or "1" in ops[0].symbol_id


def test_migration_reducer_framework_hint_non_standard_dir() -> None:
    """Verifies that framework hint enables detection in completely non-standard directories."""
    # Custom directory "db_patches" without migration in name, but framework="alembic"
    reducer = MigrationDAGReducer(framework="alembic")
    path = "db_patches/patch_42.py"
    content = "down_revision = 'base'\nrevision = 'rev42'\n"
    assert reducer.can_handle(path, content=content)
    ops = reducer.extract_operators(path, None, content, "sha3")
    assert len(ops) == 1
    assert ops[0].details.get("framework") == "alembic"
    assert ops[0].details.get("revision") == "rev42"


def test_migration_reducer_custom_path_universal_stem_fallback() -> None:
    """Verifies that custom_paths handles any stack with stem fallback even without timestamp."""
    reducer = MigrationDAGReducer(custom_paths=["custom/sql/scripts/**"])
    path = "custom/sql/scripts/add_search_index.sql"
    assert reducer.can_handle(path)
    ops = reducer.extract_operators(path, None, "CREATE INDEX ...", "sha4")
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert "add_search_index" in ops[0].symbol_id
