"""LLM concept/relation extraction → NetworkX graph."""

from __future__ import annotations

import json
import logging
import uuid

from backend.core.model_clients import deepseek_chat
from backend.graph.store import GraphStore
from backend.graph.schemas import GraphEdge, GraphNode
from backend.models.material import Chunk

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a medical knowledge graph builder. Extract knowledge points (concepts) and their relationships from the provided textbook section.

A knowledge point must satisfy the GRAIN rule: the smallest teachable unit that can be independently explained by a teacher, can have prerequisites, can be applied to examples/cases, and can be explained in 1-3 sentences.

Output valid JSON only. Schema:
{
  "nodes": [
    {
      "label": "concept name (short, precise)",
      "definition": "1-3 sentence clear definition",
      "type": "concept"
    }
  ],
  "edges": [
    {
      "source": "concept label (must match a node label exactly)",
      "target": "concept label (must match a node label exactly)",
      "relation": "prerequisite | parallel | containment | application | causes | belongs_to | manifests_as | located_in | related_to"
    }
  ]
}

Relation types:
- prerequisite: source must be learned before target
- parallel: source and target can be learned in any order
- containment: target is a sub-concept or component of source
- application: source applies or manifests in target
- causes: source causes or triggers target
- belongs_to: target belongs to the category defined by source
- manifests_as: source manifests clinically or practically as target
- located_in: source is physically located in target
- related_to: general semantic relationship when no specific type fits
"""


async def build_single_graph(
    store: GraphStore,
    textbook: str,
    sections_chunks: list[tuple[str, str, list[Chunk]]],
) -> dict:
    """Build a knowledge graph for a single textbook.

    Args:
        store: GraphStore instance
        textbook: name of the textbook
        sections_chunks: list of (section_id, chapter_name, chunks)

    Returns:
        dict with node_count, edge_count
    """
    # Add textbook root node
    textbook_node = GraphNode(
        id=f"tb_{uuid.uuid4().hex[:12]}",
        type="textbook",
        label=textbook,
    )
    store.add_node(textbook_node)

    total_nodes = 1
    total_edges = 0

    for section_id, chapter_name, chunks in sections_chunks:
        # Add chapter node
        chapter_node = GraphNode(
            id=f"ch_{uuid.uuid4().hex[:12]}",
            type="chapter",
            label=chapter_name,
        )
        store.add_node(chapter_node)
        store.add_edge(GraphEdge(
            id=f"e_{uuid.uuid4().hex[:12]}",
            source=textbook_node.id,
            target=chapter_node.id,
            relation="contains",
        ))
        total_nodes += 1
        total_edges += 1

        # Combine chunk text for this chapter
        chapter_text = "\n\n".join(c.text for c in chunks)
        if not chapter_text.strip():
            continue

        # Extract concepts and relations via LLM
        concepts, relations = await _extract_concepts(chapter_text, chunks)

        # Track label → node_id mapping
        label_to_id: dict[str, str] = {}

        for concept in concepts:
            node_id = f"cn_{uuid.uuid4().hex[:12]}"
            store.add_node(GraphNode(
                id=node_id,
                type="concept",
                label=concept["label"],
                definition=concept.get("definition", ""),
                sources=[c.id for c in chunks],
            ))
            label_to_id[concept["label"]] = node_id

            # Link concept to chapter
            store.add_edge(GraphEdge(
                id=f"e_{uuid.uuid4().hex[:12]}",
                source=chapter_node.id,
                target=node_id,
                relation="contains",
            ))
            total_nodes += 1
            total_edges += 1

        for rel in relations:
            src_id = label_to_id.get(rel["source"])
            tgt_id = label_to_id.get(rel["target"])
            if src_id and tgt_id:
                store.add_edge(GraphEdge(
                    id=f"e_{uuid.uuid4().hex[:12]}",
                    source=src_id,
                    target=tgt_id,
                    relation=rel["relation"],
                    confidence=0.7,
                ))
                total_edges += 1

    store.save()
    logger.info(
        "Single textbook graph built",
        extra={
            "project_id": store.project_id,
            "textbook": textbook,
            "nodes": total_nodes,
            "edges": total_edges,
        },
    )

    return {"textbook": textbook, "node_count": total_nodes, "edge_count": total_edges}


async def _extract_concepts(
    chapter_text: str,
    chunks: list[Chunk],
) -> tuple[list[dict], list[dict]]:
    """Call DeepSeek to extract concepts and relations from chapter text."""
    # Truncate if too long (rough 1M context guard)
    max_input = 80000
    if len(chapter_text) > max_input:
        chapter_text = chapter_text[:max_input] + "\n\n[Text truncated...]"

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM},
        {"role": "user", "content": f"Section text:\n\n{chapter_text}"},
    ]

    try:
        result = await deepseek_chat(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=8192,
        )
        data = json.loads(result["content"])
        return data.get("nodes", []), data.get("edges", [])
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning(f"Concept extraction failed: {exc}")
        return [], []
