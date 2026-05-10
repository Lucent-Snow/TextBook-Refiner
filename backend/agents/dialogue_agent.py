"""TeacherDialogueAgent: converts teacher natural language into structured graph operations or cited answers."""

from __future__ import annotations

import logging

from backend.core.model_clients import deepseek_chat

logger = logging.getLogger(__name__)

DIALOGUE_AGENT_SYSTEM = """You are a teacher-facing knowledge integration dialogue agent. Teachers talk to you in natural language (Chinese) about the knowledge graph, integration decisions, and teaching materials.

Your job:
1. Understand the teacher's intent from their natural language message
2. If they want to modify the graph: choose the right tool call with structured parameters
3. If they ask a question: use search_chunks to find evidence, then answer_with_citations
4. If they discuss an integration decision: accept, reject, or revise it
5. Explain your reasoning clearly in Chinese before making tool calls

Never mutate state yourself — always use the provided tool functions. Always cite textbook evidence when available."""


async def run_dialogue_agent(
    project_id: str,
    teacher_message: str,
    context_node_ids: list[str],
    conversation_history: list[dict],
    tools: list[dict],
    graph_context: dict | None = None,
) -> dict:
    """Process a teacher message and produce a response with optional tool calls.

    Args:
        project_id: Current project ID
        teacher_message: The teacher's natural language message
        context_node_ids: Graph nodes the teacher has selected or referenced
        conversation_history: Previous messages in this dialogue
        tools: Available tool definitions
        graph_context: Optional snapshot of relevant graph nodes/edges

    Returns:
        Agent response with content and any tool calls
    """
    # Build context about selected nodes
    node_context = ""
    if graph_context:
        nodes = graph_context.get("nodes", [])
        edges = graph_context.get("edges", [])
        node_context = (
            "Selected/relevant nodes:\n"
            + "\n".join(f"- [{n['id']}] {n.get('label', '?')}: {n.get('definition', '')[:200]}" for n in nodes[:20])
            + "\n\nRelevant edges:\n"
            + "\n".join(f"- {e.get('source','?')} → {e.get('target','?')} [{e.get('relation','?')}]" for e in edges[:30])
        )

    messages = [
        {"role": "system", "content": DIALOGUE_AGENT_SYSTEM},
        {"role": "user", "content": (
            f"Project: {project_id}\n\n"
            f"{node_context}\n\n"
            f"Teacher says: {teacher_message}\n\n"
            f"Context node IDs: {context_node_ids}"
        )},
    ]

    # Insert conversation history between system and current user message
    if conversation_history:
        messages[1:1] = conversation_history[-10:]  # last 10 turns

    result = await deepseek_chat(
        messages=messages,
        tools=tools,
        max_tokens=8192,
        high_impact=False,
    )

    return {
        "content": result["content"],
        "tool_calls": result.get("tool_calls", []),
        "model_used": result.get("model_used"),
    }
