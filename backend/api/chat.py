"""Teacher dialogue chat endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agents.dialogue_agent import run_dialogue_agent
from backend.agents.tools import build_tool_definitions
from backend.models.chat import ChatMessage, ChatRequest, MessageRole

router = APIRouter(prefix="/api/projects/{project_id}/chat", tags=["chat"])

_history: dict[str, list[dict]] = {}  # project_id -> conversation


@router.post("")
async def chat(project_id: str, body: ChatRequest) -> dict:
    """Send a message to the teacher dialogue agent."""
    tools = build_tool_definitions(["graph", "integration", "evidence"])
    history = _history.setdefault(project_id, [])

    # Get graph context for selected nodes
    graph_context = None
    if body.context_node_ids:
        from backend.api.graph import get_or_create_store
        store = get_or_create_store(project_id)
        graph_context = {
            "nodes": [store.get_node(nid) for nid in body.context_node_ids if store.get_node(nid)],
            "edges": store.get_all_edges(),
        }

    result = await run_dialogue_agent(
        project_id=project_id,
        teacher_message=body.message,
        context_node_ids=body.context_node_ids,
        conversation_history=history,
        tools=tools,
        graph_context=graph_context,
    )

    # Build and store messages
    teacher_msg = ChatMessage(
        id=f"msg_{len(history)}",
        project_id=project_id,
        role=MessageRole.TEACHER,
        content=body.message,
    )
    tool_calls = result.get("tool_calls", [])
    tool_results = await _execute_tool_calls(project_id, tool_calls)

    agent_msg = ChatMessage(
        id=f"msg_{len(history) + 1}",
        project_id=project_id,
        role=MessageRole.AGENT,
        content=result["content"] or _summarize_tool_results(tool_results),
    )

    history.append({"role": "user", "content": teacher_msg.content})
    history.append({"role": "assistant", "content": agent_msg.content})

    return {
        "message": agent_msg.model_dump(mode="json", by_alias=True),
        "toolCalls": tool_calls,
        "toolResults": tool_results,
        "modelUsed": result.get("model_used"),
    }


async def _execute_tool_calls(project_id: str, tool_calls: list[dict]) -> list[dict]:
    """Execute deterministic backend tools requested by the dialogue agent."""
    results: list[dict] = []
    if not tool_calls:
        return results

    from backend.api.decisions import accept_decision, reject_decision
    from backend.api.graph import get_or_create_store
    from backend.graph.tools import (
        add_edge,
        merge_nodes,
        rebuild_scope,
        remove_edge,
        restore_node,
        split_node,
        update_definition,
    )
    from backend.processing.rag_index import search_chunks

    store = get_or_create_store(project_id)
    for call in tool_calls:
        fn = call.get("function", {})
        name = fn.get("name", "")
        args = fn.get("arguments", {}) or {}
        try:
            if name == "merge_nodes":
                payload = merge_nodes(store, args.get("node_ids", []), args.get("canonical_name", ""), args.get("reason", ""))
            elif name == "split_node":
                payload = split_node(store, args.get("node_id", ""), args.get("new_nodes", []), args.get("reason", ""))
            elif name == "add_edge":
                payload = add_edge(
                    store,
                    source=args.get("source", ""),
                    target=args.get("target", ""),
                    relation=args.get("relation", "related_to"),
                    evidence=[{"quote": args["evidence_quote"]}] if args.get("evidence_quote") else [],
                    confidence=args.get("confidence", 0.5),
                )
            elif name == "remove_edge":
                payload = remove_edge(store, args.get("source", ""), args.get("target", ""), args.get("reason", ""))
            elif name == "update_definition":
                payload = update_definition(store, args.get("node_id", ""), args.get("definition", ""), args.get("reason", ""))
            elif name == "restore_node":
                payload = restore_node(store, args.get("node_id", ""), args.get("reason", ""))
            elif name == "rebuild_scope":
                payload = rebuild_scope(store, args.get("material_ids", []), args.get("reason", ""))
            elif name == "accept_decision":
                payload = await accept_decision(project_id, args.get("decision_id", ""), {"note": args.get("note")})
            elif name == "reject_decision":
                payload = await reject_decision(project_id, args.get("decision_id", ""), {"reason": args.get("reason", "")})
            elif name == "search_chunks":
                payload = {"results": await search_chunks(project_id, args.get("query", ""), args.get("top_k", 5))}
            else:
                payload = {"error": f"Unsupported tool: {name}"}
        except HTTPException as exc:
            payload = {"error": exc.detail, "status_code": exc.status_code}
        except Exception as exc:
            payload = {"error": str(exc)}
        results.append({"toolCallId": call.get("id"), "name": name, "result": payload})

    return results


def _summarize_tool_results(tool_results: list[dict]) -> str:
    if not tool_results:
        return ""
    succeeded = [r for r in tool_results if not r.get("result", {}).get("error")]
    failed = [r for r in tool_results if r.get("result", {}).get("error")]
    return f"已执行 {len(succeeded)} 个图谱工具调用，{len(failed)} 个失败。"
