"""IntegrationAgent: analyzes cross-textbook overlap, complementarity, gaps, and conflicts."""

from __future__ import annotations

import logging

from backend.core.model_clients import deepseek_chat

logger = logging.getLogger(__name__)

INTEGRATION_AGENT_SYSTEM = """You are a cross-textbook knowledge integration agent. Your job is to analyze knowledge points from multiple textbooks and produce structured integration decisions.

You have access to tool functions for searching and making decisions. Use them.

Key rules:
- GRAIN: knowledge points must be independently teachable units (1-3 sentences)
- DUPLICATE: two points are duplicates if they share teaching objective, core definition, similar prerequisites, and non-conflicting context
- FLOW: teaching order constrained by prerequisite edges first, then chapter order, cross-textbook frequency, importance
- RATIO: compression target is 30% by simple character count

Always provide detailed reasoning in Chinese. Always cite evidence from the textbooks."""


async def run_integration_agent(
    project_id: str,
    concept_summaries: list[dict],
    candidate_pairs: list[dict],
    tools: list[dict],
) -> dict:
    """Run the integration agent to analyze cross-textbook knowledge points.

    Args:
        project_id: Current project ID
        concept_summaries: All concept nodes with label, definition, textbook
        candidate_pairs: High-similarity pairs to analyze
        tools: Available tool definitions

    Returns:
        Agent response with content and any tool calls
    """
    # Build concept catalog
    catalog = "\n".join(
        f"[{c['id']}] {c['label']} ({c.get('textbook', '?')}): {c.get('definition', '')[:200]}"
        for c in concept_summaries[:200]
    )

    # Build candidate list
    pairs_text = "\n".join(
        f"Pair {i+1}: [{p['node_a']}] vs [{p['node_b']}] (similarity={p.get('similarity', 0):.3f})"
        for i, p in enumerate(candidate_pairs[:50])
    )

    messages = [
        {"role": "system", "content": INTEGRATION_AGENT_SYSTEM},
        {"role": "user", "content": (
            f"Project: {project_id}\n\n"
            f"Knowledge points catalog:\n{catalog}\n\n"
            f"High-similarity candidate pairs to analyze:\n{pairs_text}\n\n"
            f"Analyze these pairs. For each, determine if they are duplicate, complementary, "
            f"or conflicting. Provide structured integration decisions with reasons and evidence."
        )},
    ]

    result = await deepseek_chat(
        messages=messages,
        tools=tools,
        max_tokens=16384,
        high_impact=True,
    )

    return {
        "content": result["content"],
        "tool_calls": result.get("tool_calls", []),
        "model_used": result.get("model_used"),
        "requires_review": result.get("requires_review", False),
    }
