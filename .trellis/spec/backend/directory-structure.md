# Directory Structure

> How backend code is organized in this project.

---

## Overview

Backend is a FastAPI application in `backend/`. All model calls (DeepSeek, ModelScope) route through the backend — the frontend never calls model providers directly.

---

## Directory Layout

```
backend/
├── main.py                  # FastAPI app entry, lifespan, router registration
├── api/                     # Route handlers (thin — delegate to services)
│   ├── __init__.py
│   ├── projects.py          # POST/GET /api/projects
│   ├── materials.py         # POST/GET /api/projects/{id}/materials
│   ├── build.py             # POST /api/projects/{id}/build, GET build status, WS
│   ├── graph.py             # GET /api/projects/{id}/graph, WS graph push
│   ├── decisions.py         # GET decisions, POST accept/reject
│   ├── chat.py              # POST /api/projects/{id}/chat
│   ├── ask.py               # POST /api/projects/{id}/ask (RAG cited answer)
│   └── report.py            # POST generate, GET report
├── core/                    # Shared infrastructure
│   ├── __init__.py
│   ├── config.py            # Settings from env vars (DEEPSEEK_*, MODELSCOPE_*, DATA_ROOT)
│   ├── model_clients.py     # DeepSeek chat client, ModelScope embedding client, fallback logic
│   ├── storage.py           # Local file storage for uploads, parsed text, graph JSON, exports
│   └── jobs.py              # Build job state machine, progress tracking
├── loaders/                 # Format-specific document parsers
│   ├── __init__.py
│   ├── base.py              # Common document model (sections, pages, text)
│   ├── pdf.py               # PDF → common document model
│   ├── markdown.py          # Markdown → common document model
│   ├── word.py              # Word (.docx) → common document model
│   └── excel.py             # Excel (.xlsx) → common document model
├── processing/              # Data processing pipelines
│   ├── __init__.py
│   ├── sectioning.py        # Chapter/section recognition (uses Document.chapters from loaders)
│   ├── chunking.py          # Section-scoped chunking (chunk_size=500, overlap=100, sentence-boundary)
│   ├── rag_index.py         # Chunk → ModelScope embedding → ChromaDB (HttpClient or PersistentClient)
│   ├── graph_builder.py     # LLM concept/relation extraction → NetworkX graph (per-chapter)
│   ├── integration.py       # Cross-textbook duplicate detection (cosine sim ≥0.75) + missing detection (prereq gaps)
│   ├── flow.py              # Teaching flow generation via topological sort (FLOW rule) + cycle/conflict detection
│   └── essence.py           # Compressed essence generation, RATIO calculation (char count)
├── agents/                  # LLM-powered agents (output decisions, never mutate state directly)
│   ├── __init__.py
│   ├── integration_agent.py # Cross-textbook analysis → IntegrationDecision list
│   ├── dialogue_agent.py    # Teacher NL → GraphOperation or cited answer
│   ├── report_agent.py      # Teaching flow, essence, integration report
│   └── tools.py             # Agent tool definitions (OpenAI function-call schemas)
├── graph/                   # Knowledge graph with NetworkX
│   ├── __init__.py
│   ├── store.py             # NetworkX graph CRUD, JSON persistence, operation log
│   ├── tools.py             # Deterministic graph operations (merge, split, add/remove edge, etc.)
│   └── schemas.py           # Graph node/edge type definitions
├── models/                  # Shared Pydantic schemas (all inherit CamelModel — snake_case in Python, camelCase in JSON)
│   ├── __init__.py
│   ├── base.py              # CamelModel base — alias_generator=to_camel, populate_by_name=True
│   ├── project.py           # Project, BuildJob, BuildStatus enum, StageProgress
│   ├── material.py          # Material, Section, Chunk, FileType enum, ParseStatus enum
│   ├── graph.py             # KnowledgeNode, KnowledgeEdge, Evidence, GraphOperation, NodeType/RelationType enums
│   ├── decision.py          # IntegrationDecision, DecisionType/DecisionStatus enums
│   ├── chat.py              # ChatMessage, ChatRequest, AskRequest, ToolCall, MessageRole enum
│   └── report.py            # IntegrationReport, TeachingFlowStep
└── tests/                   # pytest with pytest-asyncio
    ├── test_health.py
    ├── test_storage.py
    ├── test_pdf_loader.py
    ├── test_sectioning.py
    ├── test_graph_tools.py
    ├── test_rag_index.py
    ├── test_build.py
    ├── test_chat.py
    └── test_integration.py
```

---

## Module Organization

- **api/** routes are thin: parse request, call service/agent, return response. No business logic.
- **core/** has no knowledge of textbook domain logic.
- **loaders/** share a common document model defined in `loaders/base.py`.
- **processing/** pipelines are stateless: they take input, return output.
- **agents/** call LLMs and output structured decisions/operations. They never mutate graph or DB state directly.
- **graph/tools.py** is the sole mutation point for knowledge graph state.
- **models/** Pydantic models are the source of truth for API contracts and internal data shapes.

---

## Naming Conventions

- Files: `snake_case.py`
- Route files named after resource: `projects.py`, `materials.py`, `graph.py`
- Processing modules named by pipeline stage: `chunking.py`, `graph_builder.py`
- Agent files: `{role}_agent.py`
- Model files named after domain entity: `project.py`, `material.py`

---

## Examples

- `api/projects.py` — thin route handlers, in-memory dict + JSON persistence via `core/storage.py`
- `api/build.py:69-169` — orchestrates the 7-stage pipeline (parsing→sectioning→chunking→KG+RAG parallel→integration→essence) with WebSocket progress broadcasts
- `api/chat.py:69-129` — receives DeepSeek tool calls, dispatches to `graph/tools.py` mutators
- `graph/store.py:151-159` — `commit()` is the single point that saves+logs+broadcasts after every mutation
- `graph/tools.py` — all graph mutations centralized here; every function calls `store.commit(...)` at the end
- `loaders/pdf.py` — implements the common `Document` model from `loaders/base.py` (uses PyMuPDF)
- `core/model_clients.py:39-121` — DeepSeek call with primary→fallback (no retry on primary), tags `requires_review=True` when high-impact task fell back
- `models/base.py` — `CamelModel` is the foundation; every model inherits it for camelCase JSON output
