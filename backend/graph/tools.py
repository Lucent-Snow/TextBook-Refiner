"""Deterministic graph operation tools.

Every tool: mutates GraphStore → saves → logs → returns result.
These are the ONLY functions allowed to mutate graph state.
"""

from __future__ import annotations

import uuid
import logging

from backend.graph.store import GraphStore
from backend.graph.schemas import GraphEdge, GraphNode

logger = logging.getLogger(__name__)


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def merge_nodes(
    store: GraphStore,
    node_ids: list[str],
    canonical_name: str,
    reason: str = "",
) -> dict:
    """Merge multiple nodes into one canonical node preserving provenance.

    The first node_id becomes the canonical node; others are marked as merged.
    All edges from merged nodes are rewired to the canonical node.
    """
    if len(node_ids) < 2:
        return {"error": "Need at least 2 node IDs to merge", "merged": False}

    valid = [nid for nid in node_ids if store.has_node(nid)]
    if len(valid) < 2:
        return {"error": "Less than 2 valid nodes found", "merged": False}

    canonical_id = valid[0]
    merged_into = valid[1:]

    # Collect sources from merged nodes
    all_sources: list[str] = list(store.get_node(canonical_id).get("sources", []))  # type: ignore[union-attr]
    for nid in merged_into:
        node = store.get_node(nid)
        if node:
            for src in node.get("sources", []):
                if src not in all_sources:
                    all_sources.append(src)

    # Update canonical node
    store.update_node_attr(
        canonical_id,
        label=canonical_name,
        sources=all_sources,
        frequency=len(all_sources),
    )

    # Rewire edges: all edges to/from merged nodes → canonical
    for nid in merged_into:
        for pred in list(store.graph.predecessors(nid)):
            if pred != canonical_id and pred not in valid:
                edge_data = store.get_edge(pred, nid)
                if edge_data:
                    store.add_edge(GraphEdge(
                        id=_new_id("e_"),
                        source=pred,
                        target=canonical_id,
                        relation=edge_data.get("relation", "related_to"),
                        evidence=edge_data.get("evidence", []),
                        confidence=edge_data.get("confidence", 0.5),
                    ))
        for succ in list(store.graph.successors(nid)):
            if succ != canonical_id and succ not in valid:
                edge_data = store.get_edge(nid, succ)
                if edge_data:
                    store.add_edge(GraphEdge(
                        id=_new_id("e_"),
                        source=canonical_id,
                        target=succ,
                        relation=edge_data.get("relation", "related_to"),
                        evidence=edge_data.get("evidence", []),
                        confidence=edge_data.get("confidence", 0.5),
                    ))

    # Mark merged nodes
    for nid in merged_into:
        store.update_node_attr(nid, merge_status=f"merged_into_{canonical_id}")

    store.commit("merge_nodes", {
        "node_ids": node_ids,
        "canonical_name": canonical_name,
        "reason": reason,
    })

    logger.info(
        "Graph merge completed",
        extra={
            "project_id": store.project_id,
            "operation": "merge_nodes",
            "node_ids": node_ids,
            "canonical": canonical_id,
        },
    )

    return {
        "merged": True,
        "canonical_id": canonical_id,
        "merged_ids": merged_into,
        "source_count": len(all_sources),
    }


def split_node(
    store: GraphStore,
    node_id: str,
    new_nodes: list[dict],
    reason: str = "",
) -> dict:
    """Split a node into multiple new nodes. Original node is removed."""
    if not store.has_node(node_id):
        return {"error": f"Node {node_id} not found", "split": False}

    original = store.get_node(node_id)
    new_ids = []
    for nn in new_nodes:
        nid = nn.get("id", _new_id("n_"))
        store.add_node(GraphNode(
            id=nid,
            type=nn.get("type", original.get("type", "concept")),
            label=nn["label"],
            definition=nn.get("definition", ""),
            sources=nn.get("sources", original.get("sources", [])),
        ))
        new_ids.append(nid)

    # Rewire: each predecessor of original connects to the first new node
    for pred in list(store.graph.predecessors(node_id)):
        edge_data = store.get_edge(pred, node_id)
        if edge_data:
            store.add_edge(GraphEdge(
                id=_new_id("e_"),
                source=pred,
                target=new_ids[0],
                relation=edge_data.get("relation", "related_to"),
                evidence=edge_data.get("evidence", []),
                confidence=edge_data.get("confidence", 0.5),
            ))

    store.remove_node(node_id)
    store.commit("split_node", {
        "node_id": node_id,
        "new_nodes": new_nodes,
        "reason": reason,
    })

    return {"split": True, "original_id": node_id, "new_ids": new_ids}


def add_edge(
    store: GraphStore,
    source: str,
    target: str,
    relation: str,
    evidence: list[dict] | None = None,
    confidence: float = 0.5,
) -> dict:
    """Add a typed edge between two existing nodes."""
    if not store.has_node(source):
        return {"error": f"Source node {source} not found", "added": False}
    if not store.has_node(target):
        return {"error": f"Target node {target} not found", "added": False}

    edge_id = _new_id("e_")
    store.add_edge(GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        relation=relation,
        evidence=evidence or [],
        confidence=confidence,
    ))

    store.commit("add_edge", {
        "source": source, "target": target,
        "relation": relation, "confidence": confidence,
    })

    return {"added": True, "edge_id": edge_id}


def remove_edge(
    store: GraphStore,
    source: str,
    target: str,
    reason: str = "",
) -> dict:
    """Remove an edge between two nodes."""
    if not store.graph.has_edge(source, target):
        return {"error": f"Edge {source}→{target} not found", "removed": False}

    store.remove_edge(source, target)
    store.commit("remove_edge", {"source": source, "target": target, "reason": reason})

    return {"removed": True, "source": source, "target": target}


def restore_node(
    store: GraphStore,
    node_id: str,
    reason: str = "",
) -> dict:
    """Restore a node that was merged into another (undo merge for this node)."""
    node = store.get_node(node_id)
    if not node:
        return {"error": f"Node {node_id} not found", "restored": False}

    merge_status = node.get("merge_status", "")
    if not merge_status.startswith("merged_into_"):
        return {"error": "Node is not in merged state", "restored": False}

    canonical_id = merge_status.replace("merged_into_", "")
    store.update_node_attr(node_id, merge_status=None)
    store.commit("restore_node", {"node_id": node_id, "canonical_id": canonical_id, "reason": reason})

    return {"restored": True, "node_id": node_id, "was_merged_into": canonical_id}


def update_definition(
    store: GraphStore,
    node_id: str,
    definition: str,
    reason: str = "",
) -> dict:
    """Update a knowledge node's definition (e.g. teacher override)."""
    if not store.has_node(node_id):
        return {"error": f"Node {node_id} not found", "updated": False}

    store.update_node_attr(node_id, definition=definition)
    store.commit("update_definition", {"node_id": node_id, "reason": reason})

    return {"updated": True, "node_id": node_id}


def rebuild_scope(
    store: GraphStore,
    material_ids: list[str],
    reason: str = "",
) -> dict:
    """Trigger a partial rebuild: removes nodes/edges sourced from specified materials
    so they can be re-extracted. Returns count of removed items."""
    removed_nodes = 0
    removed_edges = 0

    nodes_to_remove = []
    for nid in store.graph.nodes:
        node = store.get_node(nid)
        if node:
            node_material = set(node.get("sources", []))
            if node_material & set(material_ids):
                nodes_to_remove.append(nid)

    for nid in nodes_to_remove:
        removed_edges += len(list(store.graph.predecessors(nid))) + len(list(store.graph.successors(nid)))
        store.remove_node(nid)
        removed_nodes += 1

    store.commit("rebuild_scope", {
        "material_ids": material_ids,
        "reason": reason,
        "removed_nodes": removed_nodes,
        "removed_edges": removed_edges,
    })

    return {
        "rebuilt": True,
        "removed_nodes": removed_nodes,
        "removed_edges": removed_edges,
        "material_ids": material_ids,
    }
