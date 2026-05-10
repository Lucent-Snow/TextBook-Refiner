# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

This project uses **no traditional relational database**. Persistence is split across three storage backends:

| Backend | Purpose | Interface |
|---------|---------|-----------|
| ChromaDB | Vector embeddings for RAG retrieval | `chromadb` client |
| NetworkX + JSON files | Knowledge graph state, operation log, report drafts | `networkx` + `json` |
| Local filesystem | Uploaded materials, parsed text, graph JSON, ChromaDB data, exported reports | `storage.py` |

No ORM is used. No SQLite or Postgres is required for the current scope.

---

## ChromaDB (Vector Store)

- Collection naming: `{project_id}_chunks`
- Metadata per chunk: `chunk_id`, `textbook`, `chapter`, `page_start`, `page_end`, `text`
- Embedding dimension: 4096 (from ModelScope Qwen3-Embedding-8B)
- Embedding format: `float`
- ChromaDB data lives under the project's storage directory

### Query Pattern

```python
collection = chroma_client.get_or_create_collection(
    name=f"{project_id}_chunks",
    metadata={"hnsw:space": "cosine"}
)
results = collection.query(
    query_embeddings=[query_vector],
    n_results=top_k,
    include=["documents", "metadatas", "distances"]
)
```

### Batch Indexing

```python
collection.add(
    ids=chunk_ids,
    embeddings=vectors,
    documents=[c.text for c in chunks],
    metadatas=[c.citation_metadata() for c in chunks]
)
```

---

## NetworkX + JSON (Knowledge Graph)

- Graph is a `networkx.DiGraph` (directed — prerequisite edges have direction)
- Persisted as JSON alongside an append-only operation log
- Every mutation writes: updated NetworkX state → JSON snapshot + operation log entry
- JSON files stored under `{project_dir}/graph/`

### Node Types

- `textbook` — source material
- `chapter` — textbook chapter/section
- `concept` — extracted knowledge point

### Edge Types

- Structural: `contains` (textbook→chapter, chapter→concept)
- Semantic: `prerequisite`, `parallel`, `containment`, `application`
- Integration: `duplicate`, `complementary`, `missing`

### JSON Schema

```python
# graph.json
{
    "nodes": [
        {"id": "n1", "type": "concept", "label": "...", "definition": "...", "sources": [...], "frequency": 3}
    ],
    "edges": [
        {"source": "n1", "target": "n2", "relation": "prerequisite", "evidence": [...], "confidence": 0.9}
    ]
}
```

---

## Local Filesystem Storage

Structure under `DATA_ROOT` (or per-project directory):

```
{data_root}/
└── projects/
    └── {project_id}/
        ├── materials/       # Original uploaded files
        ├── parsed/          # Parsed text (common document model JSON)
        ├── chunks/          # Section-scoped chunks JSON
        ├── graph/           # graph.json, operation_log.jsonl
        ├── chroma/          # ChromaDB persistent data
        ├── reports/         # Generated integration reports
        └── project.json     # Project metadata
```

---

## Naming Conventions

- ChromaDB collections: `{project_id}_chunks` (snake_case, prefixed by project)
- Graph JSON files: `graph.json`, `operation_log.jsonl`
- Directory names: lowercase, underscore-separated
- Project storage paths: always use `storage.py` helpers, never hardcode paths

---

## Common Mistakes

- **Don't** store embeddings or vectors in JSON files — they go in ChromaDB only
- **Don't** use ChromaDB for graph traversal — use NetworkX
- **Don't** hardcode file paths — always go through `core/storage.py`
- **Don't** commit ChromaDB data, graph JSON, or uploaded files to git
- **Don't** store API keys, full textbook text, or embeddings in operation logs
