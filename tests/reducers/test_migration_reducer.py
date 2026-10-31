"""Unit tests for MigrationDAGReducer across Alembic, Django, Prisma, Drizzle, and Flyway."""

from __future__ import annotations

import json

from gdss.core.transform_types import OperatorType
from gdss.reducers.migration_reducer import MigrationDAGReducer


def test_migration_can_handle_paths():
    reducer = MigrationDAGReducer()
    # Directory patterns
    assert reducer.can_handle("alembic/versions/0001_init.py")
    assert reducer.can_handle("migrations/0001_initial.py")
    assert reducer.can_handle("src/app/migration/0002_add_roles.py")
    assert reducer.can_handle("db/migrate/20231028120000_create_users.rb")
    assert reducer.can_handle("prisma/migrations/20231012140500_init/migration.sql")
    assert reducer.can_handle("drizzle/0000_init.sql")
    assert reducer.can_handle("drizzle/meta/_journal.json")
    assert reducer.can_handle("db/migrations/meta/_journal.json")
    assert reducer.can_handle("sql/migrations/V1__init.sql")

    # Content-based sniffer on non-standard paths
    custom_content = """
    # custom db script
    revision = '0023_add_roles'
    down_revision = '0022_initial'
    """
    assert reducer.can_handle("src/custom/scripts/patch.py", content=custom_content)
    assert not reducer.can_handle("src/models/user.py", content="class User: pass")


def test_alembic_migration_parent_extraction():
    reducer = MigrationDAGReducer()
    code = """
\"\"\"add roles\"\"\"
revision = '0023_add_roles'
down_revision = '0022_initial'

def upgrade():
    pass
"""
    ops = reducer.extract_operators(
        "alembic/versions/0023_add_roles.py", None, code, commit_sha="c1"
    )
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert ops[0].name == "migration_parent::0022_initial"
    assert ops[0].details.get("framework") == "alembic"
    assert ops[0].details.get("revision") == "0023_add_roles"
    assert ops[0].details.get("parent_revision") == "0022_initial"


def test_django_migration_dependency_extraction():
    reducer = MigrationDAGReducer()
    code = """
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('auth_app', '0001_initial'),
    ]
    operations = []
"""
    ops = reducer.extract_operators("apps/auth_app/migrations/0002_roles.py", None, code)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert ops[0].name == "migration_parent::auth_app.0001_initial"
    assert ops[0].details.get("framework") == "django"


def test_prisma_migration_timestamp_extraction():
    reducer = MigrationDAGReducer()
    sql = "CREATE TABLE users (id INT PRIMARY KEY);"
    ops = reducer.extract_operators(
        "prisma/migrations/20231012140500_init/migration.sql", None, sql
    )
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert ops[0].name == "migration_timestamp::20231012140500"
    assert ops[0].details.get("framework") == "prisma"


def test_drizzle_journal_index_extraction():
    reducer = MigrationDAGReducer()
    old_journal = {
        "version": "5",
        "dialect": "pg",
        "entries": [
            {"idx": 0, "version": "5", "when": 1000, "tag": "0000_init", "breakpoints": True}
        ],
    }
    new_journal = {
        "version": "5",
        "dialect": "pg",
        "entries": [
            {"idx": 0, "version": "5", "when": 1000, "tag": "0000_init", "breakpoints": True},
            {"idx": 1, "version": "5", "when": 2000, "tag": "0001_add_users", "breakpoints": True},
        ],
    }

    ops = reducer.extract_operators(
        "drizzle/meta/_journal.json",
        json.dumps(old_journal),
        json.dumps(new_journal),
    )
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert ops[0].name == "drizzle_journal_idx::1"
    assert ops[0].details.get("idx") == 1
    assert ops[0].details.get("tag") == "0001_add_users"


def test_flyway_version_extraction():
    reducer = MigrationDAGReducer()
    sql = "CREATE TABLE orders (id INT);"
    ops = reducer.extract_operators("db/migration/V2__add_orders.sql", None, sql)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.MIGRATION_STEP
    assert ops[0].name == "migration_version::V2"
    assert ops[0].details.get("version") == "2"
