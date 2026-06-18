import networkx as nx
from typing import Dict, List, Set, Any
from gdss.core.transform_types import CodeSymbol, SymbolType

class CodeGraph:
    """
    Dependency Graph Builder using NetworkX.
    Represents the codebase as a directed semantic graph (Files, Classes, Functions)
    and tracks import, define, and static call relationships.
    """

    def __init__(self):
        self.g = nx.DiGraph()
        self._file_nodes: Dict[str, Set[str]] = {}  # Index: file_path -> Set of node IDs
        self._symbol_index: Dict[str, Set[str]] = {} # Index: symbol_name -> Set of node IDs

    def add_file_symbols(self, file_path: str, symbols: List[CodeSymbol]):
        """
        Adds or updates a file's symbols and structural relations in the graph.
        Removes any stale nodes/edges associated with this file first to allow clean incremental updates.
        """
        # 0. Clean stale nodes using the index
        if file_path in self._file_nodes:
            stale_nodes = self._file_nodes[file_path]
            # Also remove from symbol index
            for node_id in stale_nodes:
                data = self.g.nodes.get(node_id, {})
                name = data.get("name")
                if name and name in self._symbol_index:
                    self._symbol_index[name].discard(node_id)
            
            self.g.remove_nodes_from(stale_nodes)
            del self._file_nodes[file_path]

        # Add base file node
        self.g.add_node(file_path, type="file", file=file_path)
        self._file_nodes[file_path] = {file_path}

        # 1. Add definitions first
        for sym in symbols:
            node_id = None
            if sym.type == SymbolType.CLASS:
                node_id = f"{file_path}::{sym.name}"
                self.g.add_node(
                    node_id,
                    type="class",
                    name=sym.name,
                    file=file_path,
                    signature=sym.signature
                )
                self.g.add_edge(file_path, node_id, relation="defines")

            elif sym.type == SymbolType.FUNCTION:
                class_prefix = f"{sym.parent_class}::" if sym.parent_class else ""
                node_id = f"{file_path}::{class_prefix}{sym.name}"
                
                self.g.add_node(
                    node_id,
                    type="function",
                    name=sym.name,
                    file=file_path,
                    parent_class=sym.parent_class,
                    signature=sym.signature,
                    calls=sym.calls
                )
                
                parent_id = f"{file_path}::{sym.parent_class}" if sym.parent_class else file_path
                self.g.add_edge(parent_id, node_id, relation="defines")

            if node_id:
                self._file_nodes[file_path].add(node_id)
                if sym.name not in self._symbol_index:
                    self._symbol_index[sym.name] = set()
                self._symbol_index[sym.name].add(node_id)

        # 2. Add imports
        for sym in symbols:
            if sym.type == SymbolType.IMPORT:
                # Add import edge from file to imported module
                self.g.add_node(sym.module, type="module_dependency")
                self.g.add_edge(
                    file_path,
                    sym.module,
                    relation="imports",
                    imported_names=sym.imported_names
                )
                # Note: we don't track module_dependency in _file_nodes as it might be shared

    def resolve_calls(self):
        """
        Statically resolves call graph edges by matching 'calls' list in function nodes
        with other defined functions in the graph (local file or imported modules).
        """
        # Remove any stale call relations
        stale_call_edges = [
            (u, v) for u, v, d in self.g.edges(data=True)
            if d.get("relation") == "calls"
        ]
        self.g.remove_edges_from(stale_call_edges)

        # Gather all defined functions
        functions = {
            node: data for node, data in self.g.nodes(data=True)
            if data.get("type") == "function"
        }

        # Resolve call strings
        empty_set = set()
        for func_id, func_data in functions.items():
            file_path = func_data.get("file")
            calls = func_data.get("calls", [])
            parent_class = func_data.get("parent_class")

            for callee in calls:
                resolved = False

                # Scenario 1: Local call in the same class (for methods)
                if parent_class:
                    local_method_id = f"{file_path}::{parent_class}::{callee}"
                    if local_method_id in self.g:
                        self.g.add_edge(func_id, local_method_id, relation="calls")
                        resolved = True

                # Scenario 2: Local call in the same file (file-level function)
                if not resolved:
                    local_func_id = f"{file_path}::{callee}"
                    if local_func_id in self.g:
                        self.g.add_edge(func_id, local_func_id, relation="calls")
                        resolved = True

                # Scenario 3: Imported call
                if not resolved:
                    # Check what modules the current file imports
                    import_edges = [
                        (v, d) for u, v, d in self.g.out_edges(file_path, data=True)
                        if d.get("relation") == "imports"
                    ]
                    for imported_module, import_data in import_edges:
                        imported_names = import_data.get("imported_names", [])
                        
                        # Direct symbol import (e.g. from utils import helper)
                        if callee in imported_names or not imported_names:
                            # Use symbol index for O(1) candidate lookup
                            candidates = self._symbol_index.get(callee, empty_set)
                            for target_node in candidates:
                                target_data = self.g.nodes[target_node]
                                if target_data.get("type") == "function":
                                    target_file = target_data.get("file", "")
                                    if target_file.startswith(imported_module) or imported_module in target_file:
                                        self.g.add_edge(func_id, target_node, relation="calls")
                                        resolved = True
                                        break
                        
                        if resolved:
                            break

                # Scenario 4: Global/fallback search by name matching
                if not resolved:
                    candidates = self._symbol_index.get(callee, empty_set)
                    for target_node in candidates:
                        if target_node != func_id:
                            target_data = self.g.nodes[target_node]
                            if target_data.get("type") == "function":
                                self.g.add_edge(func_id, target_node, relation="calls")
                                break

    def get_downstream_impact(self, node_id: str) -> Set[str]:
        """
        Computes the complete set of downstream nodes impacted by a change in `node_id`.
        This is calculated by performing a reachability traversal on the REVERSED graph
        (since a change in A affects anything that imports/defines/calls A).
        """
        if node_id not in self.g:
            return set()

        # Reverse the graph so directed dependencies point to dependents
        # Use copy=False to avoid expensive full graph copy
        g_rev = self.g.reverse(copy=False)
        
        # Use NetworkX reachability
        impacted_nodes = nx.descendants(g_rev, node_id)
        return impacted_nodes

    def get_summary(self) -> Dict[str, Any]:
        """Returns node and edge type counts for debugging or status checking."""
        summary = {
            "total_nodes": self.g.number_of_nodes(),
            "total_edges": self.g.number_of_edges(),
            "node_types": {},
            "edge_relations": {}
        }
        for _, data in self.g.nodes(data=True):
            ntype = data.get("type", "unknown")
            summary["node_types"][ntype] = summary["node_types"].get(ntype, 0) + 1

        for _, _, data in self.g.edges(data=True):
            relation = data.get("relation", "unknown")
            summary["edge_relations"][relation] = summary["edge_relations"].get(relation, 0) + 1

        return summary
