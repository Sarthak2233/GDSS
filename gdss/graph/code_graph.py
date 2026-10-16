from typing import Any

import networkx as nx

from gdss.core.symbol_identity import is_graph_symbol_type
from gdss.core.transform_types import CodeSymbol, SymbolType


class CodeGraph:
    """
    Dependency Graph Builder using NetworkX.
    Uses stable symbol_id as node identity; file path is chart_location metadata.
    """

    def __init__(self):
        self.g = nx.DiGraph()
        self._file_nodes: dict[str, set[str]] = {}
        self._symbol_index: dict[str, set[str]] = {}
        self._symbol_id_index: dict[str, str] = {}

    def add_file_symbols(self, file_path: str, symbols: list[CodeSymbol]):
        """Add or update symbols for a file using stable symbol IDs."""
        incoming_ids: set[str] = set()
        for sym in symbols:
            if is_graph_symbol_type(sym.type):
                sym.ensure_identity(file_path)
                incoming_ids.add(sym.symbol_id or "")

        self._remove_stale_chart_nodes(file_path, incoming_ids)

        if file_path not in self._file_nodes:
            self.g.add_node(file_path, type="file", file=file_path, chart_location=file_path)
            self._file_nodes[file_path] = {file_path}

        for sym in symbols:
            if sym.type == SymbolType.CLASS:
                self._upsert_class(file_path, sym)
            elif sym.type == SymbolType.FUNCTION:
                self._upsert_function(file_path, sym)
            elif sym.type == SymbolType.IMPORT:
                self._add_import(file_path, sym)

    def _remove_stale_chart_nodes(self, file_path: str, keep_ids: set[str]) -> None:
        if file_path not in self._file_nodes:
            return
        stale = []
        for node_id in list(self._file_nodes[file_path]):
            if node_id == file_path:
                continue
            data = self.g.nodes.get(node_id, {})
            if data.get("type") in {"function", "class"}:
                sid = data.get("symbol_id")
                if sid and sid not in keep_ids:
                    stale.append(node_id)
        for node_id in stale:
            self._remove_node(node_id)

    def _upsert_class(self, file_path: str, sym: CodeSymbol) -> None:
        sym.ensure_identity(file_path)
        node_id = sym.symbol_id
        assert node_id is not None

        if node_id in self.g:
            self.g.nodes[node_id].update(
                {
                    "name": sym.name,
                    "file": file_path,
                    "chart_location": file_path,
                    "signature": sym.signature,
                    "structural_tokens": sym.structural_tokens,
                }
            )
            self._reindex_file_membership(node_id, file_path)
        else:
            self.g.add_node(
                node_id,
                type="class",
                name=sym.name,
                file=file_path,
                chart_location=file_path,
                symbol_id=node_id,
                signature=sym.signature,
                structural_tokens=sym.structural_tokens,
            )
            self.g.add_edge(file_path, node_id, relation="defines")
            self._symbol_id_index[node_id] = node_id
            self._symbol_index.setdefault(sym.name, set()).add(node_id)

        self._file_nodes.setdefault(file_path, {file_path}).add(node_id)

    def _upsert_function(self, file_path: str, sym: CodeSymbol) -> None:
        sym.ensure_identity(file_path)
        node_id = sym.symbol_id
        assert node_id is not None
        body_blocks = [b.to_dict() for b in sym.body_blocks]

        if node_id in self.g:
            self.g.nodes[node_id].update(
                {
                    "name": sym.name,
                    "file": file_path,
                    "chart_location": file_path,
                    "parent_class": sym.parent_class,
                    "signature": sym.signature,
                    "calls": sym.calls,
                    "structural_tokens": sym.structural_tokens,
                    "body_blocks": body_blocks,
                }
            )
            self._reindex_file_membership(node_id, file_path)
        else:
            self.g.add_node(
                node_id,
                type="function",
                name=sym.name,
                file=file_path,
                chart_location=file_path,
                symbol_id=node_id,
                parent_class=sym.parent_class,
                signature=sym.signature,
                calls=sym.calls,
                structural_tokens=sym.structural_tokens,
                body_blocks=body_blocks,
            )
            parent_id = self._parent_node_id(file_path, sym.parent_class)
            self.g.add_edge(parent_id, node_id, relation="defines")
            self._symbol_id_index[node_id] = node_id
            self._symbol_index.setdefault(sym.name, set()).add(node_id)

        self._file_nodes.setdefault(file_path, {file_path}).add(node_id)

    def _reindex_file_membership(self, node_id: str, file_path: str) -> None:
        old_file = self.g.nodes[node_id].get("file")
        if old_file and old_file != file_path and old_file in self._file_nodes:
            self._file_nodes[old_file].discard(node_id)
        self._file_nodes.setdefault(file_path, {file_path}).add(node_id)

    def _parent_node_id(self, file_path: str, parent_class: str | None) -> str:
        if not parent_class:
            return file_path
        for node_id, data in self.g.nodes(data=True):
            if (
                data.get("type") == "class"
                and data.get("name") == parent_class
                and data.get("chart_location") == file_path
            ):
                return node_id
        return f"{file_path}::{parent_class}"

    def _add_import(self, file_path: str, sym: CodeSymbol) -> None:
        module = sym.module or sym.name
        self.g.add_node(module, type="module_dependency")
        self.g.add_edge(
            file_path,
            module,
            relation="imports",
            imported_names=sym.imported_names,
        )

    def _remove_node(self, node_id: str) -> None:
        if node_id not in self.g:
            return
        data = self.g.nodes[node_id]
        name = data.get("name")
        file_path = data.get("file") or data.get("chart_location")
        symbol_id = data.get("symbol_id")
        if name and name in self._symbol_index:
            self._symbol_index[name].discard(node_id)
            if not self._symbol_index[name]:
                del self._symbol_index[name]
        if file_path and file_path in self._file_nodes:
            self._file_nodes[file_path].discard(node_id)
        if symbol_id and symbol_id in self._symbol_id_index:
            del self._symbol_id_index[symbol_id]
        self.g.remove_node(node_id)

    def find_node_by_name(
        self,
        name: str | None,
        file_path: str | None = None,
        parent_class: str | None = None,
    ) -> str | None:
        if not name:
            return None
        candidates = self._symbol_index.get(name, set())
        for node_id in candidates:
            data = self.g.nodes.get(node_id, {})
            if file_path and data.get("chart_location") != file_path:
                continue
            if parent_class is not None and data.get("parent_class") != parent_class:
                continue
            if data.get("type") in {"function", "class"}:
                return node_id
        return None

    def get_display_id(self, node_id: str) -> str:
        """Human-readable chart_location::name for CLI output."""
        if node_id not in self.g:
            return node_id
        data = self.g.nodes[node_id]
        if data.get("type") == "file":
            return node_id
        chart = data.get("chart_location") or data.get("file") or ""
        name = data.get("name") or node_id
        parent = data.get("parent_class")
        if parent:
            return f"{chart}::{parent}::{name}"
        return f"{chart}::{name}"

    def resolve_calls(self):
        stale_call_edges = [
            (u, v) for u, v, d in self.g.edges(data=True) if d.get("relation") == "calls"
        ]
        self.g.remove_edges_from(stale_call_edges)

        functions = {
            node: data for node, data in self.g.nodes(data=True) if data.get("type") == "function"
        }

        empty_set: set[str] = set()
        for func_id, func_data in functions.items():
            file_path = func_data.get("chart_location") or func_data.get("file")
            calls = func_data.get("calls", [])
            parent_class = func_data.get("parent_class")

            for callee in calls:
                resolved = False

                if parent_class:
                    target = self.find_node_by_name(callee, file_path, parent_class)
                    if target:
                        self.g.add_edge(func_id, target, relation="calls")
                        resolved = True

                if not resolved:
                    target = self.find_node_by_name(callee, file_path, None)
                    if target:
                        self.g.add_edge(func_id, target, relation="calls")
                        resolved = True

                if not resolved and file_path:
                    import_edges = [
                        (v, d) for u, v, d in self.g.out_edges(file_path, data=True)
                        if d.get("relation") == "imports"
                    ]
                    for imported_module, import_data in import_edges:
                        imported_names = import_data.get("imported_names", [])
                        if callee in imported_names or not imported_names:
                            candidates = self._symbol_index.get(callee, empty_set)
                            for target_node in candidates:
                                target_data = self.g.nodes[target_node]
                                if target_data.get("type") == "function":
                                    target_file = target_data.get("chart_location") or target_data.get("file", "")
                                    if target_file.startswith(imported_module) or imported_module in target_file:
                                        self.g.add_edge(func_id, target_node, relation="calls")
                                        resolved = True
                                        break
                        if resolved:
                            break

                if not resolved:
                    candidates = self._symbol_index.get(callee, empty_set)
                    for target_node in candidates:
                        if target_node != func_id and self.g.nodes[target_node].get("type") == "function":
                            self.g.add_edge(func_id, target_node, relation="calls")
                            break

    def get_downstream_impact(self, node_id: str) -> set[str]:
        if node_id not in self.g:
            resolved = self.find_node_by_name(node_id)
            if resolved:
                node_id = resolved
            else:
                return set()
        g_rev = self.g.reverse(copy=False)
        return nx.descendants(g_rev, node_id)

    def snapshot(self) -> dict[str, Any]:
        """Lightweight graph snapshot for operator identity tests."""
        nodes = {}
        for node_id, data in self.g.nodes(data=True):
            nodes[node_id] = {
                "type": data.get("type"),
                "name": data.get("name"),
                "chart_location": data.get("chart_location") or data.get("file"),
                "parent_class": data.get("parent_class"),
                "signature": data.get("signature"),
            }
        edges = [(u, v, d.get("relation")) for u, v, d in self.g.edges(data=True)]
        return {"nodes": nodes, "edges": edges}

    def get_summary(self) -> dict[str, Any]:
        summary = {
            "total_nodes": self.g.number_of_nodes(),
            "total_edges": self.g.number_of_edges(),
            "node_types": {},
            "edge_relations": {},
        }
        for _, data in self.g.nodes(data=True):
            ntype = data.get("type", "unknown")
            summary["node_types"][ntype] = summary["node_types"].get(ntype, 0) + 1
        for _, _, data in self.g.edges(data=True):
            relation = data.get("relation", "unknown")
            summary["edge_relations"][relation] = summary["edge_relations"].get(relation, 0) + 1
        return summary
