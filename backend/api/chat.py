"""Teacher dialogue chat endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agents.dialogue_agent import run_dialogue_agent
from backend.agents.tools import build_tool_definitions
from backend.core.config import settings
from backend.models.chat import ChatMessage, ChatRequest, MessageRole
from backend.processing.rag_index import search_chunks
from backend.core.model_clients import deepseek_chat

router = APIRouter(prefix="/api/projects/{project_id}/chat", tags=["chat"])

_history: dict[str, list[dict]] = {}  # project_id -> conversation


@router.post("")
async def chat(project_id: str, body: ChatRequest) -> dict:
    """Send a message to the teacher dialogue agent."""
    if settings.rag_only_mode and project_id == settings.rag_only_project_id:
        return await _rag_only_chat(project_id, body)

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
            elif name == "get_node_evidence":
                node = store.get_node(args.get("node_id", ""))
                if not node:
                    payload = {"error": "Node not found"}
                else:
                    payload = {
                        "node": node,
                        "source_chunk_ids": node.get("sources", []),
                    }
            elif name == "answer_with_citations":
                payload = {
                    "answer": args.get("answer", ""),
                    "citations": args.get("citations", []),
                }
            elif name == "revise_decision":
                payload = _revise_decision(
                    project_id,
                    decision_id=args.get("decision_id", ""),
                    revised_operation=args.get("revised_operation", {}),
                    reason=args.get("reason", ""),
                )
            else:
                payload = {"error": f"Unsupported tool: {name}"}
        except HTTPException as exc:
            payload = {"error": exc.detail, "status_code": exc.status_code}
        except Exception as exc:
            payload = {"error": str(exc)}
        results.append({"toolCallId": call.get("id"), "name": name, "result": payload})

    return results


def _revise_decision(
    project_id: str,
    decision_id: str,
    revised_operation: dict,
    reason: str,
) -> dict:
    """Revise an integration decision without applying it."""
    from backend.api.decisions import get_project_decisions
    from backend.models.decision import DecisionStatus

    decision = get_project_decisions(project_id).get(decision_id)
    if decision is None:
        return {"error": "Decision not found", "revised": False}
    decision.suggested_operation = revised_operation
    decision.reason = reason or decision.reason
    decision.status = DecisionStatus.REVISED
    return {
        "revised": True,
        "decisionId": decision_id,
        "suggestedOperation": revised_operation,
    }


def _summarize_tool_results(tool_results: list[dict]) -> str:
    if not tool_results:
        return ""
    succeeded = [r for r in tool_results if not r.get("result", {}).get("error")]
    failed = [r for r in tool_results if r.get("result", {}).get("error")]
    return f"已执行 {len(succeeded)} 个图谱工具调用，{len(failed)} 个失败。"


async def _rag_only_chat(project_id: str, body: ChatRequest) -> dict:
    history = _history.setdefault(project_id, [])
    results = await search_chunks(project_id, body.message, top_k=settings.lexical_rag_top_k)
    if not results:
        content = "未找到相关教材内容。请确认已完成快速 RAG 索引。"
        model_used = None
    else:
        context_parts = []
        for result in results:
            meta = result["metadata"]
            context_parts.append(
                f"[{meta.get('textbook', '?')}, {meta.get('chapter', '?')}, "
                f"p.{meta.get('page_start', '?')}]\n{result['text']}"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是医学教材问答助手。只基于给定教材片段回答，回答要中文、直接、适合教师验收。"
                    "每个关键结论后标注来源，例如[生理学, 第3章, p.42]。"
                    "如果片段不足以回答，就说明证据不足。"
                ),
            },
            {
                "role": "user",
                "content": f"教材片段：\n\n{chr(10).join(context_parts)}\n\n问题：{body.message}",
            },
        ]
        result = await deepseek_chat(messages=messages, max_tokens=2048)
        content = result["content"]
        model_used = result.get("model_used")

    agent_msg = ChatMessage(
        id=f"msg_{len(history) + 1}",
        project_id=project_id,
        role=MessageRole.AGENT,
        content=content,
        evidence=[r["chunk_id"] for r in results],
    )
    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": content})
    return {
        "message": agent_msg.model_dump(mode="json", by_alias=True),
        "toolCalls": [],
        "toolResults": [],
        "modelUsed": model_used,
    }
