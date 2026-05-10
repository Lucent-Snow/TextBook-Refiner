# Error Handling

> How errors are handled in this project.

---

## Overview

The backend is the model gateway — all DeepSeek and ModelScope calls go through it. Errors must be caught, logged safely (no secrets), and returned in a consistent API format. Long-running build jobs use a state machine that records per-stage failures so a partial build still surfaces what succeeded.

---

## Current Implementation

There is **no `core/exceptions.py` module** — the codebase uses a small set of specific exceptions plus FastAPI's `HTTPException`. New errors should follow the same lightweight pattern: subclass `Exception` (or `ValueError`) where the error originates, register a `@app.exception_handler` in `main.py` if it needs a custom HTTP shape.

| Exception | Defined in | When raised |
|-----------|------------|-------------|
| `StoragePathError` | `core/storage.py:14` | Storage ID fails `^[A-Za-z0-9_-]+$` (path-traversal guard). Mapped to `400` with `code=invalid_storage_id` by `main.py:60`. |
| `HTTPException` | FastAPI | Used directly in `api/*` routes for 400/404 (`api/projects.py:45`, `api/decisions.py:60`, etc.). |
| `RuntimeError` | `core/model_clients.py:121` | Raised after both primary and fallback DeepSeek models fail. |
| Bare `Exception` | various | Caught and re-raised or logged at module boundaries. The global handler in `main.py:73` returns `500` with `code=internal_error` and a sanitized message. |

---

## API Error Response Format

Defined by the global handlers in `backend/main.py`:

```json
{
    "error": {
        "code": "invalid_storage_id",
        "message": "Invalid project_id"
    }
}
```

- `code` is a stable machine-readable string (`invalid_storage_id`, `internal_error`, or — for `HTTPException` — the FastAPI default shape with `detail`).
- `message` is human-readable, safe for display.
- `details` is **not** part of the current shape; if you need field-level errors, add them under `error.details` and update the frontend `lib/api.ts` error parser.
- **Never** include API keys, raw model responses with textbook text, or stack traces in responses.

The unhandled-exception handler logs `error_type` and request path but returns only `"An internal error occurred"` to the client.

---

## Model Call Fallback

Implemented in `core/model_clients.py:39-121` (`deepseek_chat`):

1. Try `settings.deepseek_model` (default `deepseek-v4-pro`).
2. On **any** exception, log a warning with `model`/`error_type`/`attempt` and immediately try `settings.deepseek_fallback_model` (default `deepseek-v4-flash`). There is no retry of the primary model — failure is treated as "switch tier".
3. If the fallback also fails, raise `RuntimeError(f"All DeepSeek model attempts failed: {last_error}")`.
4. When `high_impact=True` (cross-textbook integration, missing-point detection, essence/report generation) and the fallback was used, the result dict carries `requires_review=True`. Callers should propagate this to the UI/log so a teacher can confirm.
5. Streaming variant `deepseek_chat_stream` (`model_clients.py:124-168`) does the same primary→fallback for the stream itself.

ModelScope embedding (`modelscope_embed`, `model_clients.py:171-194`) has **no fallback** — failures bubble up. The build job stage will be marked `FAILED` so the rest of the pipeline can continue (see `api/build.py:138-147`).

---

## Build Job Errors

State machine lives in `core/jobs.py`:

- Stage statuses: `PENDING → RUNNING → COMPLETED | FAILED`. Job statuses: `PENDING → RUNNING → COMPLETED | FAILED | PARTIAL`.
- Each stage's `try/except` is in `api/build.py:_run_build` — failure of one stage calls `job.stage_fail(name, str(exc))` and sets job status to `PARTIAL`. Other stages keep running.
- After all stages, if any stage is `FAILED` the job stays `PARTIAL`; otherwise `complete()` flips it to `COMPLETED`.
- KG and RAG stages run in parallel via `asyncio.gather(run_kg(), run_rag())` — independent failure of either leaves the other intact.
- **No per-scope retry endpoint exists yet.** A failed build is currently re-run by calling `POST /api/projects/{id}/build` again, which creates a new job and rebuilds from scratch. If you need scoped retry, extend the `body` payload accepted in `api/build.py:51-58`.
- WebSocket subscribers receive every state change via `_broadcast(job.to_dict(), project_id)` after each transition.

---

## FastAPI Exception Handlers

Registered in `backend/main.py:59-90`:

```python
@app.exception_handler(StoragePathError)
async def storage_path_error_handler(request: Request, exc: StoragePathError):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "invalid_storage_id", "message": str(exc)}},
    )

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={"method": request.method, "path": request.url.path,
               "error_type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error",
                          "message": "An internal error occurred"}},
    )
```

If you introduce a new domain exception that should map to a non-500 response, add it as a sibling handler in `main.py`. Don't try to centralize the mapping in a separate file unless we accumulate >5 such cases.

---

## Common Mistakes

- **Don't** catch bare `Exception` and return 500 silently — at minimum log `error_type` and path, mirroring `global_error_handler`.
- **Don't** include API keys, textbook content, or raw model responses in error messages.
- **Don't** treat ModelScope embedding errors as fatal at build time — let the stage fail to `PARTIAL` so KG construction can still progress.
- **Don't** use `assert` for input validation — raise `HTTPException(status_code=422, ...)` or a domain-specific exception with a registered handler.
- **Don't** assume primary→retry→fallback. Reality is primary→fallback, single attempt each. If you want retry, add it explicitly in `model_clients.py` with a clear backoff comment.
