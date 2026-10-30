"""Semantic Reducer for SQL DDL schemas (tables, columns, indexes)."""

from __future__ import annotations

import re

from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.reducers.sql")

_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[\"`\[]?\w+[\"`\]]?\.)?[\"`\[]?(?P<table>\w+)[\"`\]]?\s*\((?P<body>.*?)\);",
    re.IGNORECASE | re.DOTALL,
)

_ALTER_ADD_COL_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:[\"`\[]?\w+[\"`\]]?\.)?[\"`\[]?(?P<table>\w+)[\"`\]]?\s+ADD\s+(?:COLUMN\s+)?[\"`\[]?(?P<col>\w+)[\"`\]]?",
    re.IGNORECASE,
)

_ALTER_DROP_COL_RE = re.compile(
    r"ALTER\s+TABLE\s+(?:[\"`\[]?\w+[\"`\]]?\.)?[\"`\[]?(?P<table>\w+)[\"`\]]?\s+DROP\s+(?:COLUMN\s+)?[\"`\[]?(?P<col>\w+)[\"`\]]?",
    re.IGNORECASE,
)


class SQLSchemaReducer:
    """Extracts DDL schema operators (tables, columns) from SQL files."""

    def can_handle(self, file_path: str, content: str | None = None) -> bool:
        lower = file_path.lower()
        if lower.endswith((".sql", ".ddl")):
            return True
        if content:
            upper = content.upper()
            if "CREATE TABLE" in upper or "ALTER TABLE" in upper:
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
        operators: list[SemanticOperator] = []

        # 1. Parse CREATE TABLE statements
        for m in _CREATE_TABLE_RE.finditer(text):
            tbl = m.group("table")
            operators.append(
                SemanticOperator(
                    operator=OperatorType.SCHEMA_ADD_TABLE,
                    file=file_path,
                    commit=commit_sha,
                    name=f"table::{tbl}",
                    details={"table": tbl},
                    symbol_id=f"sql::{file_path}::table_{tbl}",
                )
            )

            body = m.group("body")
            # Parse column lines
            for raw_col in body.split(","):
                col_line = raw_col.strip()
                if not col_line or col_line.upper().startswith(
                    ("PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT", "CHECK", "UNIQUE", "INDEX")
                ):
                    continue
                col_parts = col_line.split()
                if col_parts:
                    col_name = col_parts[0].strip('"`[]')
                    col_type = col_parts[1].strip() if len(col_parts) > 1 else "TEXT"
                    operators.append(
                        SemanticOperator(
                            operator=OperatorType.SCHEMA_ADD_COLUMN,
                            file=file_path,
                            commit=commit_sha,
                            name=f"column::{tbl}.{col_name}",
                            details={"table": tbl, "column": col_name, "type": col_type},
                            symbol_id=f"sql::{file_path}::col_{tbl}_{col_name}",
                        )
                    )

        # 2. Parse ALTER TABLE ADD COLUMN
        for m in _ALTER_ADD_COL_RE.finditer(text):
            tbl = m.group("table")  # dsa:ignore
            col = m.group("col")  # dsa:ignore
            operators.append(
                SemanticOperator(
                    operator=OperatorType.SCHEMA_ADD_COLUMN,
                    file=file_path,
                    commit=commit_sha,
                    name=f"column::{tbl}.{col}",
                    details={"table": tbl, "column": col},
                    symbol_id=f"sql::{file_path}::col_{tbl}_{col}",
                )
            )

        # 3. Parse ALTER TABLE DROP COLUMN
        for m in _ALTER_DROP_COL_RE.finditer(text):
            tbl = m.group("table")  # dsa:ignore
            col = m.group("col")  # dsa:ignore
            operators.append(
                SemanticOperator(
                    operator=OperatorType.SCHEMA_DROP_COLUMN,
                    file=file_path,
                    commit=commit_sha,
                    name=f"column::{tbl}.{col}",
                    details={"table": tbl, "column": col},
                    symbol_id=f"sql::{file_path}::col_{tbl}_{col}",
                )
            )

        return operators
