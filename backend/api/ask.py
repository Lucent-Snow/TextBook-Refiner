"""RAG cited-answer endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.core.model_clients import deepseek_chat
from backend.models.chat import AskRequest
from backend.processing.rag_index import search_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/ask", tags=["ask"])

CITED_ANSWER_SYSTEM = """You are a teaching assistant answering questions based on textbook content.
Answer the teacher's question using the provided textbook excerpts as evidence.
Cite your sources: include [textbook name, chapter, page range] for each claim.
If the provided excerpts don't contain the answer, say so — don't make things up.
Respond in Chinese."""


@router.post("")
async def ask(project_id: str, body: AskRequest) -> dict:
    """Answer a question with citations from the textbook corpus."""
    # Search for relevant chunks
    results = await search_chunks(project_id, body.question, top_k=body.top_k)

    if not results:
        return {
            "answer": "未找到相关教材内容，请先上传教材并完成索引构建。",
            "citations": [],
        }

    # Build context from retrieved chunks
    context_parts: list[str] = []
    for r in results:
        meta = r["metadata"]
        context_parts.append(
            f"[{meta.get('textbook', '?')}, {meta.get('chapter', '?')}, "
            f"pp.{meta.get('page_start', '?')}-{meta.get('page_end', '?')}]\n"
            f"{r['text']}"
        )
    context = "\n\n".join(context_parts)

    messages = [
        {"role": "system", "content": CITED_ANSWER_SYSTEM},
        {"role": "user", "content": (
            f"Textbook excerpts:\n\n{context}\n\n"
            f"Teacher question: {body.question}"
        )},
    ]

    result = await deepseek_chat(
        messages=messages,
        max_tokens=4096,
        high_impact=False,
    )

    # Build citation list
    citations: list[dict] = []
    for r in results:
        meta = r["metadata"]
        citations.append({
            "textbook": meta.get("textbook", ""),
            "chapter": meta.get("chapter", ""),
            "page_range": f"{meta.get('page_start', '')}-{meta.get('page_end', '')}",
            "quote": r["text"][:300],
            "score": round(r["score"], 3),
        })

    return {
        "answer": result["content"],
        "citations": citations,
        "modelUsed": result.get("model_used"),
    }
