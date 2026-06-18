# gdss/core/transform_types.py
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime

class SymbolType(str, Enum):
    """Types of code symbols that can be tracked"""
    FUNCTION = "function"
    CLASS = "class"
    IMPORT = "import"
    VARIABLE = "variable"
    CONSTANT = "constant"

class OperatorType(str, Enum):
    """Semantic transformation operators - CRITICAL MISSING PIECE"""
    # Function operators
    ADD_FUNCTION = "add_function"
    DELETE_FUNCTION = "delete_function"
    RENAME_FUNCTION = "rename_function"
    MODIFY_FUNCTION = "modify_function"
    
    # Class operators
    ADD_CLASS = "add_class"
    DELETE_CLASS = "delete_class"
    RENAME_CLASS = "rename_class"
    MODIFY_CLASS = "modify_class"
    
    # Dependency/Variable operators
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MODIFY_DEPENDENCY = "modify_dependency"
    MODIFY_VARIABLE = "modify_variable"
    MODIFY_CONSTANT = "modify_constant"
    
    # Import operators
    ADD_IMPORT = "add_import"
    REMOVE_IMPORT = "remove_import"
    
    # File-level operators
    ADD_FILE = "add_file"
    DELETE_FILE = "delete_file"
    RENAME_FILE = "rename_file"

@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, import, etc.)"""
    name: str
    type: SymbolType
    start_line: int
    end_line: int
    signature: str = ""
    body: str = ""
    docstring: Optional[str] = None
    parent_class: Optional[str] = None
    module: Optional[str] = None
    imported_names: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CodeSymbol":
        d["type"] = SymbolType(d["type"])
        return cls(**d)

@dataclass
class SemanticOperator:
    """
    A semantic transformation operator - Tracks what changed between two versions
    This is the HEART of the GDSS system!
    """
    operator: OperatorType
    file: str
    commit: str = ""
    name: Optional[str] = None
    from_name: Optional[str] = None
    to_name: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = field(default_factory=datetime.now)
    author: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator": self.operator.value,
            "file": self.file,
            "commit": self.commit,
            "name": self.name,
            "from_name": self.from_name,
            "to_name": self.to_name,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "author": self.author
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SemanticOperator":
        return cls(
            operator=OperatorType(d["operator"]),
            file=d["file"],
            commit=d.get("commit", ""),
            name=d.get("name"),
            from_name=d.get("from_name"),
            to_name=d.get("to_name"),
            details=d.get("details", {}),
            timestamp=datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else datetime.now(),
            author=d.get("author")
        )
    
    def get_display_name(self) -> str:
        """Get user-friendly display name for the operator"""
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
        """Get icon for the operator type"""
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
        # Fallback for variable-like dependency changes
        if self.operator == OperatorType.ADD_DEPENDENCY: return "➕"
        if self.operator == OperatorType.REMOVE_DEPENDENCY: return "➖"
        if self.operator == OperatorType.MODIFY_DEPENDENCY: return "📝"
        
        return icons.get(self.operator, "•")
    
    def get_color(self) -> str:
        """Get color for the operator type"""
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