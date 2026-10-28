"""Unit tests for DomainReducerRegistry (Dual-stage routing: advisory path + content sniffer + lexical fallback)."""

from __future__ import annotations

from gdss.reducers.lexical_reducer import UniversalLexicalReducer
from gdss.reducers.manifest_reducer import ManifestReducer
from gdss.reducers.markdown_reducer import MarkdownSectionReducer
from gdss.reducers.migration_reducer import MigrationDAGReducer
from gdss.reducers.registry import DomainReducerRegistry
from gdss.reducers.sql_reducer import SQLSchemaReducer


def test_registry_advisory_path_dispatch():
    registry = DomainReducerRegistry()

    assert isinstance(registry.get_reducer("package.json"), ManifestReducer)
    assert isinstance(registry.get_reducer("Cargo.toml"), ManifestReducer)
    assert isinstance(registry.get_reducer("alembic/versions/001_init.py"), MigrationDAGReducer)
    assert isinstance(
        registry.get_reducer("prisma/migrations/20231012/migration.sql"), MigrationDAGReducer
    )
    assert isinstance(registry.get_reducer("schema.sql"), SQLSchemaReducer)
    assert isinstance(registry.get_reducer("README.md"), MarkdownSectionReducer)
    # Standard code file without domain role returns None so core ASTParser processes it
    assert registry.get_reducer("src/auth.py") is None


def test_registry_content_first_sniffer():
    registry = DomainReducerRegistry()

    # Bespoke path with manifest content
    odd_manifest = '{"name": "bespoke", "dependencies": {"axios": "1.0"}}'
    assert isinstance(
        registry.get_reducer("custom/tooling/deps.data", content=odd_manifest), ManifestReducer
    )

    # Bespoke path with migration content
    odd_migration = "revision = '002'\ndown_revision = '001'\n"
    assert isinstance(
        registry.get_reducer("custom/db/run.py", content=odd_migration), MigrationDAGReducer
    )

    # Bespoke path with SQL DDL
    odd_sql = "CREATE TABLE products (id INT, title TEXT);"
    assert isinstance(registry.get_reducer("db_setup.txt", content=odd_sql), SQLSchemaReducer)


def test_registry_lexical_fallback_for_unknown():
    registry = DomainReducerRegistry()

    # Arbitrary config or YAML file falls back to UniversalLexicalReducer
    reducer = registry.get_reducer(".github/workflows/ci.yml", content="name: CI\non: push\n")
    assert isinstance(reducer, UniversalLexicalReducer)

    reducer_env = registry.get_reducer(".env.production", content="SECRET=xyz\n")
    assert isinstance(reducer_env, UniversalLexicalReducer)
