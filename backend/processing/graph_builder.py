"""LLM concept/relation extraction → NetworkX graph."""

from __future__ import annotations

import json
import logging
import uuid
import asyncio

from backend.core.config import settings
from backend.core.model_clients import deepseek_chat
from backend.graph.store import GraphStore
from backend.graph.schemas import GraphEdge, GraphNode
from backend.models.material import Chunk

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a medical knowledge graph builder. Extract knowledge points (concepts) and their relationships from the provided textbook section.

A knowledge point must satisfy the GRAIN rule: the smallest teachable unit that can be independently explained by a teacher, can have prerequisites, can be applied to examples/cases, and can be explained in 1-3 sentences.

Extract only the most important teachable concepts in this section. Prefer core terms, mechanisms, classifications, and clinically useful applications. Avoid front matter, duplicated table-of-contents lines, image captions with no teaching value, and tiny formatting fragments.

Output valid JSON only. Keep the output compact:
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


def _extraction_user_prompt(chapter_text: str) -> str:
    return f"""Limits:
- Max concepts: {settings.kg_max_concepts_per_section}
- Max relations: {settings.kg_max_edges_per_section}
- Relation types must be one of the allowed values.
- Each concept label should be short and reusable across textbooks.

Section text:

{chapter_text}"""


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

    extraction_results = await _extract_sections_concurrently(sections_chunks)

    label_to_id_by_textbook: dict[str, str] = {}

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

        concepts, relations = extraction_results.get(section_id, ([], []))

        # Track label → node_id mapping
        label_to_id: dict[str, str] = {}

        for concept in concepts:
            label = _clean_label(concept.get("label", ""))
            if not label:
                continue
            node_id = label_to_id_by_textbook.get(label)
            if node_id is None:
                node_id = f"cn_{uuid.uuid4().hex[:12]}"
                label_to_id_by_textbook[label] = node_id
                store.add_node(GraphNode(
                    id=node_id,
                    type="concept",
                    label=label,
                    definition=concept.get("definition", ""),
                    sources=[c.id for c in chunks],
                ))
                total_nodes += 1
            else:
                existing = store.get_node(node_id)
                existing_sources = set(existing.get("sources", [])) if existing else set()
                merged_sources = sorted(existing_sources | {c.id for c in chunks})
                store.update_node_attr(node_id, sources=merged_sources, frequency=len(merged_sources))
            label_to_id[label] = node_id

            # Link concept to chapter
            if not store.get_edge(chapter_node.id, node_id):
                store.add_edge(GraphEdge(
                    id=f"e_{uuid.uuid4().hex[:12]}",
                    source=chapter_node.id,
                    target=node_id,
                    relation="contains",
                ))
                total_edges += 1

        for rel in relations:
            src_id = label_to_id.get(_clean_label(rel["source"]))
            tgt_id = label_to_id.get(_clean_label(rel["target"]))
            relation = _normalize_relation(rel.get("relation", "related_to"))
            if src_id and tgt_id and src_id != tgt_id and not store.get_edge(src_id, tgt_id):
                store.add_edge(GraphEdge(
                    id=f"e_{uuid.uuid4().hex[:12]}",
                    source=src_id,
                    target=tgt_id,
                    relation=relation,
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


async def _extract_sections_concurrently(
    sections_chunks: list[tuple[str, str, list[Chunk]]],
) -> dict[str, tuple[list[dict], list[dict]]]:
    semaphore = asyncio.Semaphore(max(1, settings.kg_extract_concurrency))
    results: dict[str, tuple[list[dict], list[dict]]] = {}

    async def run(section_id: str, chunks: list[Chunk]) -> None:
        chapter_text = _prepare_chapter_text(chunks)
        if len(chapter_text) < settings.kg_min_section_chars:
            results[section_id] = ([], [])
            return
        async with semaphore:
            results[section_id] = await _extract_concepts(chapter_text)

    await asyncio.gather(*(run(section_id, chunks) for section_id, _, chunks in sections_chunks))
    return results


def _prepare_chapter_text(chunks: list[Chunk]) -> str:
    text = "\n\n".join(c.text.strip() for c in chunks if c.text.strip())
    max_input = settings.kg_max_section_input_chars
    if len(text) <= max_input:
        return text

    head_budget = int(max_input * 0.65)
    tail_budget = max_input - head_budget
    return (
        text[:head_budget].rstrip()
        + "\n\n[Middle content omitted for KG extraction budget]\n\n"
        + text[-tail_budget:].lstrip()
    )


async def _extract_concepts(
    chapter_text: str,
) -> tuple[list[dict], list[dict]]:
    """Call DeepSeek to extract concepts and relations from chapter text."""
    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM},
        {"role": "user", "content": _extraction_user_prompt(chapter_text)},
    ]

    try:
        result = await deepseek_chat(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=settings.kg_extraction_max_tokens,
        )
        data = json.loads(result["content"])
        nodes = _limit_nodes(data.get("nodes", []))
        edges = _limit_edges(data.get("edges", []), {node["label"] for node in nodes if node.get("label")})
        return nodes, edges
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("Concept extraction failed", extra={"error_type": type(exc).__name__})
        return [], []


def _limit_nodes(nodes: list[dict]) -> list[dict]:
    result: list[dict] = []
    seen: set[str] = set()
    for node in nodes:
        label = _clean_label(node.get("label", ""))
        if not label or label in seen:
            continue
        seen.add(label)
        result.append({
            "label": label,
            "definition": str(node.get("definition", ""))[:300],
            "type": "concept",
        })
        if len(result) >= settings.kg_max_concepts_per_section:
            break
    return result


def _limit_edges(edges: list[dict], valid_labels: set[str]) -> list[dict]:
    result: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for edge in edges:
        source = _clean_label(edge.get("source", ""))
        target = _clean_label(edge.get("target", ""))
        relation = _normalize_relation(edge.get("relation", "related_to"))
        key = (source, target, relation)
        if not source or not target or source == target or source not in valid_labels or target not in valid_labels:
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append({"source": source, "target": target, "relation": relation})
        if len(result) >= settings.kg_max_edges_per_section:
            break
    return result


def _clean_label(label: str) -> str:
    return " ".join(str(label).strip().split())[:80]


def _normalize_relation(relation: str) -> str:
    allowed = {
        "prerequisite",
        "parallel",
        "containment",
        "application",
        "causes",
        "belongs_to",
        "manifests_as",
        "located_in",
        "related_to",
    }
    return relation if relation in allowed else "related_to"
