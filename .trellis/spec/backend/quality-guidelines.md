# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend code must pass lint, type-check, and tests before being considered done. Agents output structured decisions — they never mutate state directly. Graph tools must be deterministic, testable, logged, and reversible. Model calls only happen through `core/model_clients.py`.

---

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Calling DeepSeek or ModelScope from outside `core/model_clients.py` | All model calls must go through unified fallback/retry/audit logic |
| Direct graph mutation outside `graph/tools.py` | All mutations must be logged and trigger WebSocket push |
| Committing API keys or `.env` to git | Security — keys live in environment only |
| Hardcoding file paths | Use `core/storage.py` helpers |
| Using `print()` instead of `logging` | No stdout debug output in production code |
| Bare `except:` without logging | Silently swallowing errors hides bugs |
| Prebuilding/caching graph or RAG artifacts for user-supplied materials | Product requirement — system must build from scratch |
| Returning raw LLM output without validation | LLM output must be parsed against Pydantic schemas |
| Blocking I/O in async routes (`open()`, `requests`) | Use `aiofiles`, `httpx`, or `run_in_executor` |
| Calling model providers from browser | Backend is the sole model gateway |

---

## Required Patterns

| Pattern | Where |
|---------|-------|
| All model calls through `core/model_clients.py` with fallback logic | Every LLM/embedding call |
| All graph mutations through `graph/tools.py` deterministic functions | Graph operations |
| Pydantic models for all API request/response types | `models/` directory |
| Operation log append on every graph mutation | `graph/store.py` |
| WebSocket push after graph state changes | `graph/tools.py` → `api/graph.py` |
| Progress reporting for long-running tasks | `processing/` pipelines via `core/jobs.py` |
| Configuration from environment variables via `core/config.py` | All settings |

---

## Testing Requirements

- **Unit tests**: all `graph/tools.py` functions, `processing/` pipeline steps, `loaders/` parsers
- **Model client tests**: mock DeepSeek/ModelScope responses, test fallback/retry logic
- **API smoke tests**: each endpoint with happy path + error cases
- **Integration tests**: full build flow (upload → parse → chunk → embed → graph → report)
- Test files mirror source structure: `tests/test_graph_tools.py`, `tests/test_chunking.py`
- Use `pytest` with `pytest-asyncio` for async tests

```python
# Example: testing a deterministic graph tool
async def test_merge_nodes_preserves_provenance():
    store = GraphStore()
    store.add_node("n1", type="concept", label="炎症")
    store.add_node("n2", type="concept", label="炎症反应")
    
    result = merge_nodes(store, node_ids=["n1", "n2"], canonical_name="炎症")
    
    assert result["merged"] is True
    assert store.has_node(result["canonical_id"])
    assert len(store.get_operation_log()) == 1
```

---

## Code Review Checklist

- [ ] Model calls go through `core/model_clients.py` (not called directly)
- [ ] Graph mutations use `graph/tools.py` (not raw NetworkX calls)
- [ ] All API endpoints have Pydantic request/response models
- [ ] Long-running operations report progress
- [ ] Errors return the standard `{"error": {"code": ..., "message": ...}}` format
- [ ] No secrets, file paths, or textbook content leaked in log messages
- [ ] Async I/O used in route handlers (no blocking calls)
- [ ] Fallback model usage is logged and, for high-impact tasks, flagged with `requiresReview`
- [ ] Operation log is appended after every graph mutation
- [ ] Tests cover both happy path and error cases for new code

---

## Common Mistakes

- **Calling `requests.get()` in an async route** — use `httpx.AsyncClient`
- **Parsing LLM JSON output without try/except and schema validation** — always validate against Pydantic
- **Forgetting to append operation log after graph mutation** — the log is the audit trail for teacher review
- **Storing graph in ChromaDB or vectors in NetworkX** — each backend has exactly one purpose
- **Returning 500 for validation errors** — use 422 with field-level details
