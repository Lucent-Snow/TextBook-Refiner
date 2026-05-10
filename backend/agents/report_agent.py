"""ReportAgent: generates teaching flow, compressed essence, and integration report."""

from __future__ import annotations

import json
import logging

from backend.core.model_clients import deepseek_chat

logger = logging.getLogger(__name__)

REPORT_AGENT_SYSTEM = """You are a knowledge integration report agent. Generate teaching flows, compressed essence, and integration reports from knowledge graph data.

Key rules:
- FLOW rule: teaching order is constrained by prerequisite edges first, then chapter order, cross-textbook frequency, and importance
- RATIO rule: compression ratio = essence_char_count / original_char_count; target is ≤30%
- All output must be in Chinese
- Include textbook citations for every teaching step

Output valid JSON when asked for structured data."""


async def run_report_agent(
    project_id: str,
    store_snapshot: dict,
    all_text: str,
    decisions: list[dict],
    accepted_count: int,
    rejected_count: int,
    flow_result: dict | None = None,
) -> dict:
    """Generate the integration report with teaching flow and essence.

    Args:
        project_id: Current project ID
        store_snapshot: Full graph snapshot (nodes + edges)
        all_text: Concatenated original text from all textbooks
        decisions: All integration decisions with their status
        accepted_count: Number of accepted decisions
        rejected_count: Number of rejected decisions

    Returns:
        Report data: teaching_flow, essence, decisions_summary, compression_ratio
    """
    concepts = [n for n in store_snapshot.get("nodes", []) if n.get("type") == "concept"]
    edges = store_snapshot.get("edges", [])

    # Build prerequisite graph summary for flow generation
    prereq_edges = [e for e in edges if e.get("relation") == "prerequisite"]
    flow_hints = "\n".join(
        f"- {e['source']} → {e['target']}"
        for e in prereq_edges[:50]
    )

    concept_list = "\n".join(
        f"[{c['id']}] {c.get('label', '?')}: {c.get('definition', '')[:200]}"
        for c in concepts[:150]
    )

    decision_summary = f"Accepted: {accepted_count}, Rejected: {rejected_count}, Total: {len(decisions)}"

    messages = [
        {"role": "system", "content": REPORT_AGENT_SYSTEM},
        {"role": "user", "content": (
            f"Project: {project_id}\n"
            f"Original character count: {len(all_text)}\n"
            f"Target compression: 30% (~{int(len(all_text) * 0.3)} chars)\n\n"
            f"Concepts ({len(concepts)}):\n{concept_list}\n\n"
            f"Prerequisite edges:\n{flow_hints}\n\n"
            f"Integration decisions: {decision_summary}\n\n"
            f"Generate:\n"
            f"1. An ordered teaching flow (respect prerequisites)\n"
            f"2. A compressed teaching essence (target 30% of original)\n"
            f"3. A decisions summary\n\n"
            f"Output valid JSON with: teaching_flow, essence, decisions_summary"
        )},
    ]

    result = await deepseek_chat(
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=16384,
        high_impact=True,
    )

    try:
        data = json.loads(result["content"])
    except json.JSONDecodeError:
        data = {"teaching_flow": [], "essence": "", "decisions_summary": {}}

    essence_text = data.get("essence", "")
    compression_ratio = round(len(essence_text) / len(all_text), 4) if all_text else 0.0

    return {
        "teaching_flow": data.get("teaching_flow", []),
        "essence": essence_text,
        "decisions_summary": data.get("decisions_summary", {
            "accepted": accepted_count,
            "rejected": rejected_count,
            "total": len(decisions),
        }),
        "original_char_count": len(all_text),
        "essence_char_count": len(essence_text),
        "compression_ratio": compression_ratio,
        "model_used": result.get("model_used"),
        "requires_review": result.get("requires_review", False),
    }
