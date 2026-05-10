"""Cross-textbook integration: duplicate/complement/missing/conflict detection."""

from __future__ import annotations

import json
import logging
import math
import uuid

from backend.core.model_clients import deepseek_chat, modelscope_embed_single
from backend.graph.store import GraphStore
from backend.models.decision import DecisionType, IntegrationDecision

logger = logging.getLogger(__name__)

INTEGRATION_SYSTEM = """You are a cross-textbook knowledge integration analyst. Analyze knowledge points from multiple textbooks and identify integration opportunities.

Output valid JSON only. Schema:
{
  "decisions": [
    {
      "type": "duplicate | complementary | missing | conflict",
      "node_ids": ["id1", "id2"],
      "reason": "detailed reasoning in Chinese",
      "confidence": 0.85,
      "suggested_operation": {
        "operation": "merge_nodes | add_edge | split_node | update_definition",
        "params": {}
      }
    }
  ]
}

Decision types:
- duplicate (DUPLICATE rule): two nodes represent the same teaching objective, core definition, and prerequisite structure. They should be merged.
- complementary: two nodes cover different aspects of the same topic and should be linked.
- missing: a topic typically taught between existing nodes is absent from all textbooks.
- conflict: two nodes have contradictory prerequisite edges, definitions, or classification.
"""


async def detect_cross_textbook(
    project_id: str,
    store: GraphStore,
) -> list[IntegrationDecision]:
    """Detect integration candidates across all textbooks in the graph.

    1. Embed all concept node definitions
    2. Find candidate pairs by embedding similarity
    3. LLM validates and produces IntegrationDecisions
    """
    # Collect all concept nodes
    all_nodes = store.get_all_nodes()
    concepts = [n for n in all_nodes if n.get("type") == "concept"]
    if len(concepts) < 2:
        logger.info("Not enough concepts for integration", extra={"project_id": project_id})
        return []

    # Build embedding-based candidate pairs (top similar pairs)
    definitions = [n.get("definition", n.get("label", "")) for n in concepts]
    concept_ids = [n["id"] for n in concepts]

    # Embed all definitions
    embeddings = []
    for d in definitions:
        try:
            vec = await modelscope_embed_single(d)
            embeddings.append(vec)
        except Exception:
            embeddings.append([0.0] * 4096)

    # Find candidate pairs by cosine similarity
    candidates = _find_candidate_pairs(concept_ids, definitions, embeddings)

    if not candidates:
        return []

    # Build prompt for LLM
    node_map = {n["id"]: n for n in concepts}
    candidate_texts: list[str] = []
    for a, b, sim in candidates:
        na = node_map[a]
        nb = node_map[b]
        candidate_texts.append(
            f"Pair (similarity={sim:.3f}):\n"
            f"  Node A [{a}]: {na['label']} — {na.get('definition', '')}\n"
            f"  Node B [{b}]: {nb['label']} — {nb.get('definition', '')}\n"
        )

    messages = [
        {"role": "system", "content": INTEGRATION_SYSTEM},
        {"role": "user", "content": "Analyze these candidate knowledge point pairs:\n\n" + "\n".join(candidate_texts)},
    ]

    try:
        result = await deepseek_chat(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=8192,
            high_impact=True,
        )
        data = json.loads(result["content"])
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"Integration detection failed: {exc}")
        return []

    decisions: list[IntegrationDecision] = []
    for d in data.get("decisions", []):
        decisions.append(IntegrationDecision(
            id=f"dec_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            type=DecisionType(d.get("type", "complementary")),
            involved_node_ids=d.get("node_ids", []),
            reason=d.get("reason", ""),
            confidence=d.get("confidence", 0.5),
            suggested_operation=d.get("suggested_operation"),
        ))

    logger.info(
        "Integration detection done",
        extra={
            "project_id": project_id,
            "candidates": len(candidates),
            "decisions": len(decisions),
            "model_used": result.get("model_used"),
            "requires_review": result.get("requires_review", False),
        },
    )

    return decisions


MISSING_SYSTEM = """You are a medical education knowledge analyst. Identify missing knowledge points that should logically exist between prerequisite-connected concepts but are absent from all provided textbooks.

A missing knowledge point satisfies:
1. It bridges two concepts where one is a prerequisite of the other
2. The gap is large enough that a teacher would expect an intermediate concept
3. The missing point is independently teachable (GRAIN rule: 1-3 sentences)

Output valid JSON only. Schema:
{
  "missing_points": [
    {
      "label": "name of the missing concept",
      "definition": "1-3 sentence definition",
      "between_nodes": ["prereq_node_id", "target_node_id"],
      "reason": "why this concept should exist here"
    }
  ]
}"""


async def detect_missing_points(
    project_id: str,
    store: GraphStore,
) -> list:
    """Detect missing knowledge points in prerequisite chains.

    Analyzes prerequisite edges where the conceptual gap between nodes
    suggests an intermediate concept should exist but is absent.
    """
    concepts = [n for n in store.get_all_nodes() if n.get("type") == "concept"]
    if len(concepts) < 2:
        return []

    concept_ids = {n["id"] for n in concepts}

    # Find prerequisite edges with large definition gaps
    gaps: list[dict] = []
    for s, t in store.graph.edges:
        if s not in concept_ids or t not in concept_ids:
            continue
        relation = store.graph.edges[s, t].get("relation", "")
        if relation == "prerequisite":
            node_s = store.get_node(s)
            node_t = store.get_node(t)
            if node_s and node_t:
                gaps.append({
                    "source_id": s,
                    "source_label": node_s.get("label", s),
                    "source_def": node_s.get("definition", "")[:200],
                    "target_id": t,
                    "target_label": node_t.get("label", t),
                    "target_def": node_t.get("definition", "")[:200],
                })

    if not gaps:
        return []

    gaps_text = "\n".join(
        f"Gap {i+1}: [{g['source_label']}] → [{g['target_label']}]\n"
        f"  Prereq: {g['source_def']}\n"
        f"  Target: {g['target_def']}"
        for i, g in enumerate(gaps[:30])
    )

    messages = [
        {"role": "system", "content": MISSING_SYSTEM},
        {"role": "user", "content": (
            f"Analyze these prerequisite gaps for missing intermediate concepts:\n\n{gaps_text}"
        )},
    ]

    try:
        result = await deepseek_chat(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=4096,
            high_impact=True,
        )
        import json
        data = json.loads(result["content"])
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"Missing point detection failed: {exc}")
        return []

    missing = []
    for mp in data.get("missing_points", []):
        missing.append({
            "label": mp.get("label", ""),
            "definition": mp.get("definition", ""),
            "between_nodes": mp.get("between_nodes", []),
            "reason": mp.get("reason", ""),
            "type": "missing",
        })

    logger.info(
        "Missing points detected",
        extra={
            "project_id": project_id,
            "gaps_analyzed": len(gaps),
            "missing_found": len(missing),
        },
    )

    return missing


def _find_candidate_pairs(
    ids: list[str],
    definitions: list[str],
    embeddings: list[list[float]],
    threshold: float = 0.75,
    max_pairs: int = 50,
) -> list[tuple[str, str, float]]:
    """Find concept pairs with high cosine similarity."""
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            sim = _cosine_sim(embeddings[i], embeddings[j])
            if sim >= threshold:
                pairs.append((ids[i], ids[j], sim))

    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs[:max_pairs]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
