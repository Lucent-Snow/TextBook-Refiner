# Logging Guidelines

> How logging is done in this project.

---

## Overview

Use Python `logging` with structured log messages. The backend logs through standard `logging.getLogger(__name__)` — configure format and level in `core/config.py`. All model calls, build stages, graph operations, and errors must be logged.

---

## Log Levels

| Level | When to Use |
|-------|-------------|
| `DEBUG` | Detailed pipeline internals: chunk counts, graph node/edge counts, embedding batch sizes |
| `INFO` | Key events: build stage start/complete, model call start/end, graph operation executed, report generated |
| `WARN` | Recoverable issues: fallback model used, retry succeeded, chunk too large for embedding, low confidence decision |
| `ERROR` | Failures: model call failed after retries, build stage failed, graph operation rejected, file parse failed |

---

## Structured Logging

Use `extra` dict for structured fields:

```python
logger.info(
    "Model call completed",
    extra={
        "model": "deepseek-v4-pro",
        "duration_ms": 1234,
        "token_usage": {"prompt": 500, "completion": 200},
        "request_id": "req_abc123",
        "purpose": "kg_extraction"
    }
)
```

Required fields per log category:

| Category | Required Fields |
|----------|----------------|
| Model call | `model`, `duration_ms`, `token_usage`, `request_id`, `purpose` |
| Build stage | `project_id`, `stage`, `status`, `duration_ms` |
| Graph operation | `project_id`, `operation`, `node_ids`, `success` |
| Embedding call | `model`, `batch_size`, `duration_ms`, `request_id` |

---

## What to Log

- Every model call: model name, duration, token usage, error type (if failed), request id
- Every build stage: stage name, status (started/completed/failed), duration
- Every graph operation: operation type, affected node/edge IDs, success/failure
- File operations: file path, file type, byte size, parse status
- API requests: method, path, status code, duration (use FastAPI middleware)

---

## What NOT to Log

- **API keys** — never log `DEEPSEEK_API_KEY`, `MODELSCOPE_API_KEY`, or any auth header
- **Full textbook content** — log chunk counts and byte sizes, not the text itself
- **User-uploaded file contents** — log file metadata only
- **Raw model responses containing textbook text** — log token counts, not content
- **Personal data** — no PII in logs

Sanitize log context before emitting:

```python
def safe_extra(extra: dict) -> dict:
    forbidden_keys = {"api_key", "textbook_text", "file_content", "raw_response"}
    return {k: v for k, v in extra.items() if k not in forbidden_keys}
```

---

## FastAPI Request Logging

Use a middleware for consistent request logging:

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 1)
        }
    )
    return response
```

---

## Common Mistakes

- **Don't** use `print()` — always use `logging.getLogger(__name__)`
- **Don't** log at `INFO` inside tight loops — use `DEBUG`
- **Don't** log API keys, even in `DEBUG` level
- **Don't** log full model responses that may contain textbook excerpts
- **Don't** skip logging for fallback model usage — it's a critical signal
