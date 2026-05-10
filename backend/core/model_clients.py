"""DeepSeek chat and ModelScope embedding clients with fallback logic."""

from __future__ import annotations

import logging
import time
from typing import Optional

from openai import AsyncOpenAI

from backend.core.config import settings

logger = logging.getLogger(__name__)

_deepseek_client: Optional[AsyncOpenAI] = None
_modelscope_client: Optional[AsyncOpenAI] = None


def _get_deepseek() -> AsyncOpenAI:
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _deepseek_client


def _get_modelscope() -> AsyncOpenAI:
    global _modelscope_client
    if _modelscope_client is None:
        _modelscope_client = AsyncOpenAI(
            api_key=settings.modelscope_api_key,
            base_url=settings.modelscope_base_url,
        )
    return _modelscope_client


async def deepseek_chat(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    response_format: dict | None = None,
    max_tokens: int = 8192,
    high_impact: bool = False,
    stream: bool = False,
) -> dict:
    """Call DeepSeek chat with automatic fallback on failure.

    Returns:
        dict with keys: content, tool_calls, model_used, requires_review, usage, request_id
    """
    client = _get_deepseek()
    models_to_try = [settings.deepseek_model]
    if settings.deepseek_fallback_model != settings.deepseek_model:
        models_to_try.append(settings.deepseek_fallback_model)

    last_error = None
    for attempt, model in enumerate(models_to_try):
        try:
            start = time.monotonic()
            kwargs: dict = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "reasoning_effort": settings.deepseek_reasoning_effort,
                "extra_body": settings.deepseek_extra_body,
                "stream": stream,
            }
            if tools:
                kwargs["tools"] = tools
            if response_format:
                kwargs["response_format"] = response_format

            response = await client.chat.completions.create(**kwargs)
            duration_ms = (time.monotonic() - start) * 1000

            choice = response.choices[0]
            usage = response.usage

            logger.info(
                "DeepSeek call completed",
                extra={
                    "model": model,
                    "duration_ms": round(duration_ms, 1),
                    "token_usage": {
                        "prompt": usage.prompt_tokens if usage else 0,
                        "completion": usage.completion_tokens if usage else 0,
                    },
                    "request_id": getattr(response, "id", None),
                    "purpose": _infer_purpose(messages),
                    "fallback": attempt > 0,
                },
            )

            return {
                "content": choice.message.content or "",
                "tool_calls": _normalize_tool_calls(choice.message.tool_calls),
                "model_used": model,
                "requires_review": high_impact and attempt > 0,
                "usage": {
                    "prompt": usage.prompt_tokens if usage else 0,
                    "completion": usage.completion_tokens if usage else 0,
                },
                "request_id": getattr(response, "id", None),
            }

        except Exception as exc:
            last_error = exc
            logger.warning(
                "DeepSeek call failed",
                extra={
                    "model": model,
                    "error_type": type(exc).__name__,
                    "attempt": attempt,
                },
            )
            if attempt == 0:
                continue  # try fallback

    raise RuntimeError(f"All DeepSeek model attempts failed: {last_error}")


async def deepseek_chat_stream(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    high_impact: bool = False,
):
    """Stream DeepSeek chat response chunks."""
    client = _get_deepseek()
    model = settings.deepseek_model
    start = time.monotonic()

    try:
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "reasoning_effort": settings.deepseek_reasoning_effort,
            "extra_body": settings.deepseek_extra_body,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "DeepSeek stream completed",
            extra={
                "model": model,
                "duration_ms": round(duration_ms, 1),
                "purpose": _infer_purpose(messages),
            },
        )
    except Exception:
        logger.warning(
            "DeepSeek stream failed, trying fallback",
            extra={"model": model, "error_type": "stream_error"},
        )
        kwargs["model"] = settings.deepseek_fallback_model
        kwargs["stream"] = True
        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk


async def modelscope_embed(texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts. Returns list of float vectors (4096-dim)."""
    client = _get_modelscope()
    start = time.monotonic()

    response = await client.embeddings.create(
        model=settings.modelscope_embedding_model,
        input=texts,
        encoding_format="float",
    )

    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "ModelScope embedding completed",
        extra={
            "model": settings.modelscope_embedding_model,
            "batch_size": len(texts),
            "duration_ms": round(duration_ms, 1),
            "request_id": getattr(response, "id", None),
        },
    )

    vectors = [item.embedding for item in response.data]
    return vectors


async def modelscope_embed_single(text: str) -> list[float]:
    """Get embedding for a single text."""
    results = await modelscope_embed([text])
    return results[0]


def _normalize_tool_calls(tool_calls) -> list[dict]:
    """Convert OpenAI tool call objects to plain dicts."""
    if not tool_calls:
        return []
    result = []
    for tc in tool_calls:
        import json
        result.append({
            "id": tc.id,
            "type": tc.type,
            "function": {
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {},
            },
        })
    return result


def _infer_purpose(messages: list[dict]) -> str:
    """Infer call purpose from system message for logging."""
    for m in messages:
        if m.get("role") == "system":
            content = str(m.get("content", ""))[:80]
            if "extract" in content.lower() or "knowledge" in content.lower():
                return "kg_extraction"
            if "integration" in content.lower():
                return "integration"
            if "teaching" in content.lower() or "essence" in content.lower():
                return "report"
            if "teacher" in content.lower() or "dialogue" in content.lower():
                return "dialogue"
    return "chat"
