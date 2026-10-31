"""Domain reducers subsystem for non-code assets and universal repository intelligence."""

from gdss.reducers.base import DomainReducer
from gdss.reducers.lexical_reducer import UniversalLexicalReducer
from gdss.reducers.manifest_reducer import ManifestReducer
from gdss.reducers.markdown_reducer import MarkdownSectionReducer
from gdss.reducers.migration_reducer import MigrationDAGReducer
from gdss.reducers.registry import DomainReducerRegistry
from gdss.reducers.sql_reducer import SQLSchemaReducer

__all__ = [
    "DomainReducer",
    "DomainReducerRegistry",
    "ManifestReducer",
    "MigrationDAGReducer",
    "SQLSchemaReducer",
    "MarkdownSectionReducer",
    "UniversalLexicalReducer",
]
