"""Teaching flow generation using topological sort (FLOW rule).

Order constraints (in priority):
1. Prerequisite edges → primary constraint
2. Chapter order within textbooks
3. Cross-textbook frequency (concepts appearing in more textbooks are more important)
4. Node importance (frequency + edge count)
5. Conflicts (cycles / contradictory edges) flagged for teacher review
"""

from __future__ import annotations

import logging
from collections import deque

from backend.graph.store import GraphStore

logger = logging.getLogger(__name__)


def generate_teaching_flow(store: GraphStore) -> dict:
    """Generate an ordered teaching sequence from the knowledge graph.

    Returns:
        dict with:
        - steps: ordered list of {concept_id, concept_label, prerequisites_met}
        - conflicts: list of {type, nodes, description} for teacher review
        - unplaced: concept IDs that couldn't be placed due to cycles
    """
    concepts = [n for n in store.get_all_nodes() if n.get("type") == "concept"]
    if not concepts:
        return {"steps": [], "conflicts": [], "unplaced": []}

    concept_ids = {n["id"] for n in concepts}

    # Build prerequisite graph (only edges between concepts)
    prereq_of: dict[str, list[str]] = {}  # node -> list of nodes that depend on it
    depends_on: dict[str, list[str]] = {}  # node -> list of nodes it depends on
    for nid in concept_ids:
        prereq_of[nid] = []
        depends_on[nid] = []

    for s, t in store.graph.edges:
        if s not in concept_ids or t not in concept_ids:
            continue
        relation = store.graph.edges[s, t].get("relation", "")
        if relation in ("prerequisite",):
            prereq_of.setdefault(s, []).append(t)
            depends_on.setdefault(t, []).append(s)

    # Detect conflicts: cycles and contradictory edges
    conflicts = _detect_conflicts(concept_ids, depends_on, store)

    # Topological sort (Kahn's algorithm)
    in_degree = {nid: len(depends_on.get(nid, [])) for nid in concept_ids}
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])

    # Sort by chapter order / frequency for deterministic ordering
    ordered: list[str] = []
    unplaced: list[str] = []

    # Node metadata for tie-breaking
    node_meta = {
        n["id"]: {
            "label": n.get("label", n["id"]),
            "frequency": n.get("frequency", 1),
            "degree": len(store.graph.in_edges(n["id"])) + len(store.graph.out_edges(n["id"])),
        }
        for n in concepts
    }

    while queue:
        # Sort queue: higher frequency + degree first (more important concepts)
        batch = sorted(queue, key=lambda nid: (
            node_meta[nid]["frequency"] + node_meta[nid]["degree"]
        ), reverse=True)
        for nid in batch:
            queue.remove(nid)
            ordered.append(nid)
            for dependent in prereq_of.get(nid, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    # Nodes still in cycles
    for nid, deg in in_degree.items():
        if deg > 0:
            unplaced.append(nid)

    # Build step list
    steps = []
    for i, nid in enumerate(ordered):
        node = store.get_node(nid) or {}
        prerequisites = depends_on.get(nid, [])
        steps.append({
            "order": i + 1,
            "concept_id": nid,
            "concept_label": node.get("label", nid),
            "textbook_refs": node.get("sources", []),
            "prerequisite_ids": prerequisites,
            "prerequisites_met": all(
                pid in ordered[:i] for pid in prerequisites if pid in concept_ids
            ),
        })

    logger.info(
        "Teaching flow generated",
        extra={
            "project_id": store.project_id,
            "steps": len(steps),
            "unplaced": len(unplaced),
            "conflicts": len(conflicts),
        },
    )

    return {"steps": steps, "conflicts": conflicts, "unplaced": unplaced}


def _detect_conflicts(
    concept_ids: set[str],
    depends_on: dict[str, list[str]],
    store: GraphStore,
) -> list[dict]:
    """Detect conflicts: cycles and contradictory prerequisite pairs."""
    conflicts: list[dict] = []

    # Detect contradictory edges: A→B and B→A both marked as prerequisite
    visited_pairs: set[tuple[str, str]] = set()
    for s, t in store.graph.edges:
        if s not in concept_ids or t not in concept_ids:
            continue
        relation = store.graph.edges[s, t].get("relation", "")
        if relation == "prerequisite":
            pair = tuple(sorted([s, t]))
            if pair in visited_pairs:
                continue
            # Check reverse edge
            if store.graph.has_edge(t, s):
                rev_rel = store.graph.edges[t, s].get("relation", "")
                if rev_rel == "prerequisite":
                    visited_pairs.add(pair)
                    node_s = store.get_node(s) or {}
                    node_t = store.get_node(t) or {}
                    conflicts.append({
                        "type": "contradictory_prerequisite",
                        "nodes": [s, t],
                        "description": (
                            f"Contradictory prerequisite: "
                            f"'{node_s.get('label', s)}' ↔ '{node_t.get('label', t)}' "
                            f"both marked as prerequisites of each other"
                        ),
                    })

    # Detect cycles ≥3 nodes via DFS on prerequisite subgraph
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in concept_ids}
    parent: dict[str, str | None] = {nid: None for nid in concept_ids}

    def dfs_cycle(nid: str) -> list[str] | None:
        color[nid] = GRAY
        for neighbor in depends_on.get(nid, []):
            if color.get(neighbor) == GRAY:
                # Found cycle, reconstruct path
                cycle = [neighbor, nid]
                curr = nid
                while parent.get(curr) and parent[curr] != neighbor:
                    curr = parent[curr]
                    cycle.append(curr)
                cycle.append(neighbor)
                return cycle[::-1]
            if color.get(neighbor) == WHITE:
                parent[neighbor] = nid
                result = dfs_cycle(neighbor)
                if result:
                    return result
        color[nid] = BLACK
        return None

    for nid in concept_ids:
        if color[nid] == WHITE:
            cycle = dfs_cycle(nid)
            if cycle and len(cycle) >= 3:
                node_labels = []
                for cid in cycle:
                    node = store.get_node(cid) or {}
                    node_labels.append(node.get("label", cid))
                conflicts.append({
                    "type": "prerequisite_cycle",
                    "nodes": cycle,
                    "description": (
                        f"Circular prerequisite chain detected: "
                        f"{' → '.join(node_labels)}"
                    ),
                })
                break  # Report first cycle

    return conflicts
