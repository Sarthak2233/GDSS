# gdss/core/transform_types.py
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SymbolType(str, Enum):
    """Types of code symbols that can be tracked"""
    FUNCTION = "function"
    CLASS = "class"
    IMPORT = "import"
    VARIABLE = "variable"
    CONSTANT = "constant"


class OperatorType(str, Enum):
    """Semantic transformation operators"""
    ADD_FUNCTION = "add_function"
    DELETE_FUNCTION = "delete_function"
    RENAME_FUNCTION = "rename_function"
    MODIFY_FUNCTION = "modify_function"

    ADD_CLASS = "add_class"
    DELETE_CLASS = "delete_class"
    RENAME_CLASS = "rename_class"
    MODIFY_CLASS = "modify_class"

    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MODIFY_DEPENDENCY = "modify_dependency"
    MODIFY_VARIABLE = "modify_variable"
    MODIFY_CONSTANT = "modify_constant"

    ADD_IMPORT = "add_import"
    REMOVE_IMPORT = "remove_import"

    ADD_FILE = "add_file"
    DELETE_FILE = "delete_file"
    RENAME_FILE = "rename_file"


@dataclass
class BodyBlock:
    """Sub-symbolic scope inside a function or class body."""
    block_id: str
    node_type: str
    start_line: int
    end_line: int
    structural_tokens: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BodyBlock:
        return cls(**d)


@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, import, etc.)"""
    name: str
    type: SymbolType
    start_line: int
    end_line: int
    start_column: int = 1
    end_column: int = 1
    signature: str = ""
    body: str = ""
    docstring: str | None = None
    parent_class: str | None = None
    module: str | None = None
    imported_names: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    structural_tokens: list[str] = field(default_factory=list)
    body_blocks: list[BodyBlock] = field(default_factory=list)
    language: str = "python"
    chart_location: str | None = None
    symbol_id: str | None = None

    def ensure_identity(self, file_path: str | None = None) -> None:
        """Populate symbol_id and chart_location when missing."""
        if file_path and not self.chart_location:
            self.chart_location = file_path
        if not self.symbol_id:
            from gdss.core.symbol_identity import compute_symbol_id

            self.symbol_id = compute_symbol_id(self, language=self.language)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["body_blocks"] = [b.to_dict() for b in self.body_blocks]
        return data

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CodeSymbol:
        blocks = [BodyBlock.from_dict(b) for b in d.pop("body_blocks", [])]
        d["type"] = SymbolType(d["type"])
        return cls(**d, body_blocks=blocks)


@dataclass
class SemanticOperator:
    """
    Executable semantic transformation operator.
    Supports serialization for CLI/storage and apply/invert on CodeGraph.
    """
    operator: OperatorType
    file: str
    commit: str = ""
    name: str | None = None
    from_name: str | None = None
    to_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime | None = field(default_factory=datetime.now)
    author: str | None = None
    symbol_id: str | None = None
    from_symbol_id: str | None = None
    to_symbol_id: str | None = None

    def get_target_name(self) -> str | None:
        """Primary symbol name for display and impact queries."""
        if self.name:
            return self.name
        if self.to_name:
            return self.to_name
        if self.from_name:
            return self.from_name
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator": self.operator.value,
            "file": self.file,
            "commit": self.commit,
            "name": self.name,
            "from_name": self.from_name,
            "to_name": self.to_name,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "author": self.author,
            "symbol_id": self.symbol_id,
            "from_symbol_id": self.from_symbol_id,
            "to_symbol_id": self.to_symbol_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SemanticOperator:
        return cls(
            operator=OperatorType(d["operator"]),
            file=d["file"],
            commit=d.get("commit", ""),
            name=d.get("name"),
            from_name=d.get("from_name"),
            to_name=d.get("to_name"),
            details=d.get("details", {}),
            timestamp=datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else datetime.now(),
            author=d.get("author"),
            symbol_id=d.get("symbol_id"),
            from_symbol_id=d.get("from_symbol_id"),
            to_symbol_id=d.get("to_symbol_id"),
        )

    def get_display_name(self) -> str:
        names = {
            OperatorType.ADD_FUNCTION: "Add Function",
            OperatorType.DELETE_FUNCTION: "Delete Function",
            OperatorType.RENAME_FUNCTION: "Rename Function",
            OperatorType.MODIFY_FUNCTION: "Modify Function",
            OperatorType.ADD_CLASS: "Add Class",
            OperatorType.DELETE_CLASS: "Delete Class",
            OperatorType.RENAME_CLASS: "Rename Class",
            OperatorType.MODIFY_CLASS: "Modify Class",
            OperatorType.ADD_DEPENDENCY: "Add Dependency",
            OperatorType.REMOVE_DEPENDENCY: "Remove Dependency",
            OperatorType.MODIFY_DEPENDENCY: "Modify Dependency",
            OperatorType.ADD_IMPORT: "Add Import",
            OperatorType.REMOVE_IMPORT: "Remove Import",
            OperatorType.ADD_FILE: "Add File",
            OperatorType.DELETE_FILE: "Delete File",
            OperatorType.RENAME_FILE: "Rename File",
        }
        return names.get(self.operator, self.operator.value.replace("_", " ").title())

    def get_icon(self) -> str:
        icons = {
            OperatorType.ADD_FUNCTION: "➕",
            OperatorType.DELETE_FUNCTION: "➖",
            OperatorType.RENAME_FUNCTION: "🔀",
            OperatorType.MODIFY_FUNCTION: "✏️",
            OperatorType.ADD_CLASS: "📦",
            OperatorType.DELETE_CLASS: "🗑️",
            OperatorType.RENAME_CLASS: "🔄",
            OperatorType.MODIFY_CLASS: "🔧",
            OperatorType.ADD_DEPENDENCY: "🔗",
            OperatorType.REMOVE_DEPENDENCY: "🔗",
            OperatorType.MODIFY_DEPENDENCY: "🔗",
            OperatorType.MODIFY_VARIABLE: "📦",
            OperatorType.MODIFY_CONSTANT: "💎",
            OperatorType.ADD_IMPORT: "📥",
            OperatorType.REMOVE_IMPORT: "📤",
            OperatorType.ADD_FILE: "📄",
            OperatorType.DELETE_FILE: "🗑️",
            OperatorType.RENAME_FILE: "📝",
        }
        if self.operator == OperatorType.ADD_DEPENDENCY:
            return "➕"
        if self.operator == OperatorType.REMOVE_DEPENDENCY:
            return "➖"
        if self.operator == OperatorType.MODIFY_DEPENDENCY:
            return "📝"
        return icons.get(self.operator, "•")

    def get_color(self) -> str:
        colors = {
            OperatorType.ADD_FUNCTION: "bold green",
            OperatorType.DELETE_FUNCTION: "bold red",
            OperatorType.RENAME_FUNCTION: "bold blue",
            OperatorType.MODIFY_FUNCTION: "bold yellow",
            OperatorType.ADD_CLASS: "bold green",
            OperatorType.DELETE_CLASS: "bold red",
            OperatorType.RENAME_CLASS: "bold blue",
            OperatorType.MODIFY_CLASS: "bold yellow",
            OperatorType.ADD_DEPENDENCY: "bold cyan",
            OperatorType.REMOVE_DEPENDENCY: "bold red",
            OperatorType.MODIFY_DEPENDENCY: "bold yellow",
            OperatorType.MODIFY_VARIABLE: "bold white",
            OperatorType.MODIFY_CONSTANT: "bold magenta",
            OperatorType.ADD_IMPORT: "bold cyan",
            OperatorType.REMOVE_IMPORT: "bold red",
            OperatorType.ADD_FILE: "bold green",
            OperatorType.DELETE_FILE: "bold red",
            OperatorType.RENAME_FILE: "bold blue",
        }
        return colors.get(self.operator, "white")
