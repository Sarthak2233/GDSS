"""Domain Reducer Registry coordinating advisory paths, deep content sniffers, and fallbacks."""

from __future__ import annotations

from gdss.core.ast_parser import SOURCE_EXTENSIONS
from gdss.reducers.base import DomainReducer
from gdss.reducers.lexical_reducer import UniversalLexicalReducer
from gdss.reducers.manifest_reducer import ManifestReducer
from gdss.reducers.markdown_reducer import MarkdownSectionReducer
from gdss.reducers.migration_reducer import MigrationDAGReducer
from gdss.reducers.sql_reducer import SQLSchemaReducer


class DomainReducerRegistry:
    """Registry resolving file paths and contents to appropriate domain reducers."""

    def __init__(self) -> None:
        self.manifest_reducer = ManifestReducer()
        self.migration_reducer = MigrationDAGReducer()
        self.sql_reducer = SQLSchemaReducer()
        self.markdown_reducer = MarkdownSectionReducer()
        self.lexical_reducer = UniversalLexicalReducer()

    def get_reducer(self, file_path: str, content: str | None = None) -> DomainReducer | None:
        """
        Resolve a file path to its specialized DomainReducer.

        Returns None if the file is a standard programming language source file
        that should be processed by the Tree-sitter ASTParser.
        """
        # 1. Specialized Domain Reducers (take priority even over extension if migration/manifest)
        if self.manifest_reducer.can_handle(file_path, content):
            return self.manifest_reducer

        if self.migration_reducer.can_handle(file_path, content):
            return self.migration_reducer

        if self.sql_reducer.can_handle(file_path, content):
            return self.sql_reducer

        if self.markdown_reducer.can_handle(file_path, content):
            return self.markdown_reducer

        # 2. Standard Code Files -> Core AST Parser
        if file_path.endswith(SOURCE_EXTENSIONS):
            return None

        # 3. Universal Lexical Safety Net (Zero False Negatives)
        return self.lexical_reducer
