"""Compressed essence generation and RATIO calculation."""

from __future__ import annotations

import logging

from backend.core.model_clients import deepseek_chat
from backend.graph.store import GraphStore

logger = logging.getLogger(__name__)

ESSENCE_SYSTEM = """You are a knowledge essence generator. Create a compressed teaching essence from integrated knowledge graph data.

The essence must:
1. Organize content in a logical teaching order (respect prerequisite edges)
2. Remove redundant explanations across textbooks (DUPLICATE rule applied)
3. Keep only the clearest definition for each concept
4. Maintain all essential knowledge but concise
5. Be suitable for a teacher to review and teach from

Target compression: output should be roughly 30% of the original character count.
Output valid JSON only. Schema:
{
  "essence": "the compressed teaching essence text",
  "topics_covered": ["topic1", "topic2"],
  "teaching_order_summary": "brief explanation of the teaching flow"
}"""


async def generate_essence(
    project_id: str,
    store: GraphStore,
    original_text: str,
    teaching_flow: list[dict],
    decisions_accepted: int = 0,
) -> dict:
    """Generate a compressed essence version of the integrated textbooks.

    Args:
        project_id: Current project ID
        store: GraphStore with all nodes/edges
        original_text: Full original parsed text from all materials
        teaching_flow: Ordered teaching steps from topological sort
        decisions_accepted: Number of integration decisions accepted

    Returns:
        dict with essence, topics_covered, teaching_order_summary, char counts
    """
    # Build context: concept names with definitions
    concepts = [n for n in store.get_all_nodes() if n.get("type") == "concept"]
    concept_summary = "\n".join(
        f"- {c['label']}: {c.get('definition', '')[:200]}"
        for c in concepts[:100]  # cap for prompt size
    )

    # Teaching flow as ordered concept list
    flow_summary = "\n".join(
        f"{i+1}. {step.get('concept_label', step.get('concept_id', '?'))}"
        for i, step in enumerate(teaching_flow[:100])
    )

    messages = [
        {"role": "system", "content": ESSENCE_SYSTEM},
        {"role": "user", "content": (
            f"Original character count: {len(original_text)}\n"
            f"Target compression: 30% (~{int(len(original_text) * 0.3)} chars)\n\n"
            f"Integrated concepts ({len(concepts)}):\n{concept_summary}\n\n"
            f"Teaching flow:\n{flow_summary}\n\n"
            f"Accepted integration decisions: {decisions_accepted}\n\n"
            f"Generate the compressed teaching essence."
        )},
    ]

    try:
        result = await deepseek_chat(
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=16384,
            high_impact=True,
        )
        import json
        data = json.loads(result["content"])
    except Exception as exc:
        logger.error(f"Essence generation failed: {exc}")
        return {
            "essence": "",
            "topics_covered": [],
            "teaching_order_summary": "",
            "original_char_count": len(original_text),
            "essence_char_count": 0,
            "compression_ratio": 0.0,
        }

    essence_text = data.get("essence", "")
    original_count = len(original_text)
    essence_count = len(essence_text)
    ratio = calculate_compression_ratio(original_count, essence_count)

    logger.info(
        "Essence generated",
        extra={
            "project_id": project_id,
            "original_chars": original_count,
            "essence_chars": essence_count,
            "ratio": ratio,
            "model_used": result.get("model_used"),
        },
    )

    return {
        "essence": essence_text,
        "topics_covered": data.get("topics_covered", []),
        "teaching_order_summary": data.get("teaching_order_summary", ""),
        "original_char_count": original_count,
        "essence_char_count": essence_count,
        "compression_ratio": ratio,
    }


def calculate_compression_ratio(original_char_count: int, essence_char_count: int) -> float:
    """Calculate compression ratio using simple character counts (RATIO rule)."""
    if original_char_count <= 0:
        return 0.0
    return round(essence_char_count / original_char_count, 4)
