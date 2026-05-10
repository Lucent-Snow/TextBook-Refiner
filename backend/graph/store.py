"""NetworkX graph store with JSON persistence and operation log."""

from __future__ import annotations

import uuid
from typing import Callable

import networkx as nx

from backend.core.storage import append_jsonl, ensure_project_dirs, load_json, save_json
from backend.graph.schemas import GraphData, GraphEdge, GraphNode


class GraphStore:
    """Manages a NetworkX DiGraph with JSON persistence and append-only operation log."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.graph = nx.DiGraph()
        dirs = ensure_project_dirs(project_id)
        self._graph_dir = dirs["graph"]
        self._graph_path = self._graph_dir / "graph.json"
        self._log_path = self._graph_dir / "operation_log.jsonl"
        self._on_change: Callable[[dict], None] | None = None

        # Load existing if present
        if self._graph_path.exists():
            self._load()

    def on_change(self, callback: Callable[[dict], None]) -> None:
        """Register a callback invoked after every mutation (e.g. WebSocket push)."""
        self._on_change = callback

    # -- Node CRUD --

    def add_node(self, node: GraphNode) -> str:
        self.graph.add_node(
            node.id,
            type=node.type,
            label=node.label,
            definition=node.definition,
            sources=node.sources,
            frequency=node.frequency,
            merge_status=node.merge_status,
            teacher_overrides=node.teacher_overrides,
        )
        return node.id

    def get_node(self, node_id: str) -> dict | None:
        if node_id not in self.graph:
            return None
        return {"id": node_id, **self.graph.nodes[node_id]}

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self.graph:
            return False
        self.graph.remove_node(node_id)
        return True

    def has_node(self, node_id: str) -> bool:
        return node_id in self.graph

    def update_node_attr(self, node_id: str, **attrs) -> bool:
        if node_id not in self.graph:
            return False
        self.graph.nodes[node_id].update(attrs)
        return True

    # -- Edge CRUD --

    def add_edge(self, edge: GraphEdge) -> str:
        self.graph.add_edge(
            edge.source,
            edge.target,
            id=edge.id,
            relation=edge.relation,
            evidence=edge.evidence,
            confidence=edge.confidence,
        )
        return edge.id

    def get_edge(self, source: str, target: str) -> dict | None:
        if not self.graph.has_edge(source, target):
            return None
        return dict(self.graph.edges[source, target])

    def remove_edge(self, source: str, target: str) -> bool:
        if not self.graph.has_edge(source, target):
            return False
        self.graph.remove_edge(source, target)
        return True

    # -- Query --

    def get_all_nodes(self) -> list[dict]:
        return [{"id": n, **self.graph.nodes[n]} for n in self.graph.nodes]

    def get_all_edges(self) -> list[dict]:
        return [
            {"id": self.graph.edges[s, t].get("id", f"e_{s}_{t}"),
             "source": s, "target": t, **self.graph.edges[s, t]}
            for s, t in self.graph.edges
        ]

    def get_neighbors(self, node_id: str) -> list[str]:
        return list(self.graph.successors(node_id)) + list(self.graph.predecessors(node_id))

    # -- Persistence --

    def save(self) -> None:
        data = GraphData(
            nodes=self.get_all_nodes(),
            edges=self.get_all_edges(),
        )
        save_json(self._graph_path, {"nodes": data.nodes, "edges": data.edges})

    def _load(self) -> None:
        data = load_json(self._graph_path)
        for n in data.get("nodes", []):
            node_id = n.pop("id")
            self.graph.add_node(node_id, **n)
        for e in data.get("edges", []):
            source = e.pop("source")
            target = e.pop("target")
            self.graph.add_edge(source, target, **e)

    def log_operation(self, operation: str, params: dict, success: bool, error: str | None = None) -> None:
        entry = {
            "id": f"op_{uuid.uuid4().hex[:12]}",
            "operation": operation,
            "params": params,
            "success": success,
            "error": error,
        }
        append_jsonl(self._log_path, entry)

    def get_operation_log(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        result = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            import json
            for line in f:
                line = line.strip()
                if line:
                    result.append(json.loads(line))
        return result

    # -- Commit pattern for deterministic tools --

    def commit(self, operation: str, params: dict, error: str | None = None) -> dict:
        """Save state, log operation, fire callback. Called by graph tools after mutation."""
        success = error is None
        self.save()
        self.log_operation(operation, params, success, error)
        snapshot = {"nodes": self.get_all_nodes(), "edges": self.get_all_edges()}
        if self._on_change:
            self._on_change(snapshot)
        return snapshot
