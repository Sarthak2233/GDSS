"""Unit tests for SQLSchemaReducer (DDL schema extraction)."""

from __future__ import annotations

from gdss.core.transform_types import OperatorType
from gdss.reducers.sql_reducer import SQLSchemaReducer


def test_sql_reducer_can_handle():
    reducer = SQLSchemaReducer()
    assert reducer.can_handle("schema.sql")
    assert reducer.can_handle("db/init.sql")
    assert reducer.can_handle("models.ddl")
    assert not reducer.can_handle("app.py")


def test_sql_create_table():
    reducer = SQLSchemaReducer()
    sql = """
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    ops = reducer.extract_operators("schema.sql", None, sql)
    # Emits table operator + column operators
    table_ops = [op for op in ops if op.operator == OperatorType.SCHEMA_ADD_TABLE]
    col_ops = [op for op in ops if op.operator == OperatorType.SCHEMA_ADD_COLUMN]

    assert len(table_ops) == 1
    assert table_ops[0].name == "table::users"

    col_names = {op.name for op in col_ops}
    assert "column::users.id" in col_names
    assert "column::users.email" in col_names
    assert "column::users.created_at" in col_names


def test_sql_alter_table():
    reducer = SQLSchemaReducer()
    sql = """
    ALTER TABLE users ADD COLUMN phone VARCHAR(50);
    ALTER TABLE users DROP COLUMN old_flag;
    """
    ops = reducer.extract_operators("schema.sql", None, sql)
    add_cols = [op for op in ops if op.operator == OperatorType.SCHEMA_ADD_COLUMN]
    drop_cols = [op for op in ops if op.operator == OperatorType.SCHEMA_DROP_COLUMN]

    assert len(add_cols) == 1
    assert add_cols[0].name == "column::users.phone"

    assert len(drop_cols) == 1
    assert drop_cols[0].name == "column::users.old_flag"
