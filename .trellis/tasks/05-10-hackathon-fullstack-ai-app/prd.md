# brainstorm: hackathon fullstack AI app architecture

## Goal

Design a fast, reliable, product-grade full-stack architecture and development workflow using Docker, Next.js, FastAPI, DeepSeek chat model access, and ModelScope Qwen embedding access.

## What I already know

* The project is for a Zhejiang University AI full-stack speed hackathon.
* The current sample data includes multiple medical textbook PDFs, but the product must support arbitrary user-provided textbooks instead of being hardcoded to these files.
* Development directory is `E:\Desktop\Program\TextBook Refiner`.
* External document/data directory is `E:\Desktop\大学\比赛\浙大AI全栈极速黑客松！`, including the competition PDF and sample `textbooks/` data.
* Preferred deployment shape: Dockerized full stack.
* Preferred frontend: Next.js.
* Preferred backend: FastAPI.
* Preferred chat LLM provider: DeepSeek via an OpenAI-compatible API surface.
* Preferred embedding provider: ModelScope `Qwen/Qwen3-Embedding-8B` via an OpenAI-compatible embeddings endpoint.
* Product direction: a Knowledge Integration Agent for non-technical judges and teachers, centered on textbook knowledge graph construction, cross-textbook integration, teacher dialogue, and compressed essence generation.
* Competition positioning: load multi-source teaching materials, construct per-textbook knowledge graphs, integrate cross-textbook knowledge, produce a compressed essence version, and iterate with teachers through multi-turn dialogue.
* Primary demo scenario: a user places textbooks into the app, the app builds and visualizes a knowledge graph from scratch at runtime, then answers questions with textbook/chapter/page citations.
* Important teacher-facing scenario: if a teacher says the chunking / graph construction is wrong, the app should allow immediate strategy adjustment and partial or full rebuild.
* Confirmed graph model: a two-layer graph with textbook/chapter structure as the outer layer and medical concepts/relations as the inner layer.
* Required input formats include PDF, Markdown, Word, and Excel.
* Required single-textbook graph relationship types include prerequisite, parallel, containment, and application relationships.
* Confirmed GRAIN rule: a knowledge point is the smallest teachable unit that can be independently explained by a teacher, can have prerequisites, can be applied to examples/cases, and can be explained in 1-3 sentences.
* Confirmed DUPLICATE rule: two knowledge points are duplicates if they share the same teaching objective, core definition, similar prerequisite structure, and non-conflicting application context.
* Confirmed FLOW rule: integrated teaching order is primarily constrained by prerequisite edges, then by original chapter order, cross-textbook frequency, and importance; prerequisite conflicts must be reported for teacher confirmation.
* Confirmed RATIO rule: calculate the 30% compression target by simple text length, comparing original parsed body character count with integrated essence character count.
* Preprocessing/cached prebuilt graph data is not allowed as a product strategy; the system must ingest and build from the supplied documents during use.
* User does not write or review code directly; implementation must be self-tested and validated by agents/tools.
* Chinese communication is required. Code comments and commit messages should be English.
* Secrets must be stored in environment variables and must not be committed.

## Assumptions (temporary)

* The app likely needs LLM generation plus retrieval/search over uploaded or seeded content.
* A monorepo with `frontend/`, `backend/`, and `docker-compose.yml` will be easier to coordinate than separate repos.
* SQLite or Postgres can be selected depending on whether persistence and vector retrieval are central to the demo.

## Open Questions

* How should merged knowledge-graph nodes appear visually and semantically: physically merged into one canonical node, or preserved as separate nodes connected by an equivalence edge?

## Requirements (evolving)

* Provide a Docker-first local development and product workflow.
* Keep provider credentials outside source control through `.env` and `.env.example`.
* Route all LLM and embedding calls through the backend, not directly from the browser.
* Support multi-agent development workflow with explicit roles for exploration, implementation, review, and verification.
* Prefer automated validation: tests, lint/typecheck, API smoke tests, and browser checks for UI changes.
* RAG chunks should include citation metadata: `chunk_id`, `textbook`, `chapter`, `page_start`, `page_end`, and `text`.
* RAG chunking should avoid crossing chapter boundaries so citation metadata remains accurate.
* Frontend must visibly demonstrate technical capability through dynamic knowledge graph visualization, not only a chat interface.
* Graph visualization must show both textbook/chapter structure and extracted medical concept relationships.
* RAG citation output must include textbook, chapter, page range, and supporting original text snippet.
* The system should expose rebuild controls for teacher feedback, including chunking parameters and graph construction thresholds where feasible.
* Long-running ingestion/build jobs must show progress instead of hiding latency. Performance should be improved with concurrency rather than fake precomputation.
* KG and RAG are separate pipelines sharing the same textbook source: KG serves dynamic visual integration and teacher correction; RAG serves cited retrieval and answer generation.
* After PDF parsing and chapter recognition, KG construction and RAG indexing should run in parallel so the graph can grow while vector indexing proceeds.
* KG updates must support teacher-driven natural-language feedback that is converted into structured graph operations.
* Teacher natural-language edits should be handled as agent tool calls: the agent chooses a graph operation and fills structured parameters, while deterministic backend functions perform the actual mutation.
* Cross-textbook integration must identify overlap, complementarity, and missing knowledge points across materials.
* Every integration decision must include a reason and support multi-turn teacher discussion.
* The system must produce an integration report and a compressed essence version no larger than 30% of the original material volume according to a defined calculation method.
* The primary product screen should be an Integration Workspace rather than a chatbot-only page or marketing landing page.

## Acceptance Criteria (evolving)

* [ ] Architecture decision includes frontend, backend, database/vector store, model gateway, and deployment shape.
* [ ] Product scope is explicit, including out-of-scope items.
* [ ] Agent workflow is explicit enough to split coding, review, and validation work.
* [ ] Secret handling plan prevents real keys from entering commits, logs, or browser bundles.
* [ ] Flow supports ingesting supplied textbook PDFs, building graph data from scratch, visualizing nodes/edges, asking cited questions, and rebuilding after parameter changes.
* [ ] Flow supports PDF, Markdown, Word, and Excel ingestion through a common document model.
* [ ] Per-textbook knowledge graphs include prerequisite, parallel, containment, and application relation types.
* [ ] Cross-textbook integration identifies duplicate, complementary, and missing knowledge points.
* [ ] Every integration suggestion includes a structured reason and can be discussed or revised through teacher dialogue.
* [ ] The product can generate an integration report and a compressed essence output with a visible compression ratio calculation.
* [ ] The main workspace follows the agreed reference layout: top status bar, left material/chapter panel, central graph canvas, right integration decision panel, teacher dialogue console, and build progress strip.

## Definition of Done (team quality bar)

* Tests added/updated where implementation changes behavior.
* Lint/typecheck pass for changed frontend/backend code.
* Docker compose build/start path is verified.
* UI changes are checked with browser automation when applicable.
* Docs/notes are updated when behavior or setup changes.

## Out of Scope (explicit)

* Committing real API keys or embedding them in source files.
* Prebuilding/caching final graph or RAG artifacts before user-supplied ingestion.

## Implementation Status (2026-05-10)

Skeleton has been generated locally (uncommitted in `backend/` + `frontend/`). The brainstorm-phase scope is now mostly real code, though only one stub remains in the backend and the frontend has one empty directory.

### Backend — substantially implemented

| Area | Status | Notes |
|------|--------|-------|
| FastAPI app, CORS, request logging, global exception handler | ✓ | `backend/main.py` registers all 8 routers + `/api/health`. |
| `core/config.py` env-driven settings | ✓ | `DEEPSEEK_*`, `MODELSCOPE_*`, `CHROMA_*`, `DATA_ROOT` all wired. |
| `core/model_clients.py` DeepSeek + ModelScope clients | ✓ | Primary→fallback (no retry), `requires_review` tagging, streaming variant, structured logging. |
| `core/storage.py` filesystem helpers | ✓ | Path-traversal guarded, project-dir scaffolding, JSON/JSONL helpers. |
| `core/jobs.py` BuildJob state machine | ✓ | 7 stages, in-memory store. |
| `api/projects.py` create/list/get | ✓ | In-memory + JSON-disk persistence. |
| `api/materials.py` upload + auto-parse on upload | ✓ | Dispatches to `loaders/*` by extension. |
| `api/build.py` orchestrated build + WebSocket progress | ✓ | KG and RAG run in parallel via `asyncio.gather`; per-stage failure → `PARTIAL`. |
| `api/graph.py` graph fetch + WebSocket push | ✓ | `_schedule_broadcast` registered as `GraphStore.on_change` callback. |
| `api/decisions.py` detect/list/accept/reject | ✓ | Accept dispatches to deterministic `graph/tools.py` mutators. |
| `api/chat.py` teacher dialogue + tool dispatch | ✓ | Routes DeepSeek tool calls to graph/integration/RAG functions. |
| `api/ask.py` cited RAG answer | ✓ | Search → DeepSeek answer with `[textbook, chapter, pp.X-Y]` citations. |
| `api/report.py` generate + persist report | ✓ | Topo-sort flow + LLM essence + char-count ratio. |
| `agents/integration_agent.py`, `dialogue_agent.py`, `report_agent.py`, `tools.py` | ✓ | Real prompts, GRAPH/INTEGRATION/EVIDENCE/REPORT tool schemas. |
| `processing/sectioning.py`, `chunking.py` | ✓ | Sentence-boundary chunking, no cross-chapter chunks. |
| `processing/rag_index.py` | ⚠ minor | One harmless `pass` at line 59 inside `try/except` for collection-delete idempotency. |
| `processing/graph_builder.py` | ✓ | LLM extraction per chapter, GRAIN-aware system prompt, 9 relation types. |
| `processing/integration.py` | ✓ | Embedding-based candidate pairs (cosine ≥0.75) → DeepSeek decisions; `detect_missing_points` for prereq gaps. |
| `processing/flow.py` | ✓ | Kahn topo sort, cycle/contradictory-prereq detection. |
| `processing/essence.py` | ✓ | LLM essence + `calculate_compression_ratio`. |
| `graph/store.py` NetworkX + JSON + operation log + `on_change` callback | ✓ | `commit()` is the single mutation barrier. |
| `graph/tools.py` deterministic mutators | ✓ | `merge_nodes`, `split_node`, `add_edge`, `remove_edge`, `update_definition`, `restore_node`, `rebuild_scope`. |
| `loaders/{pdf,markdown,word,excel}.py` | ✓ | All 4 formats via PyMuPDF / `python-docx` / `openpyxl`. |
| `models/*` Pydantic via `CamelModel` | ✓ | snake_case ↔ camelCase aliasing for frontend compatibility. |
| `tests/test_*.py` | ✓ | 9 files covering health/storage/PDF/sectioning/graph_tools/RAG/build/chat/integration. |

### Frontend — substantially implemented

| Area | Status | Notes |
|------|--------|-------|
| Next.js 16.2.6 + React 19 + Tailwind v4 + shadcn/ui v4 (`@base-ui/react`) + react-force-graph-2d | ✓ | `package.json` deps complete. |
| `app/page.tsx` project overview + create | ✓ | shadcn Cards, list + create form. |
| `app/projects/[projectId]/layout.tsx` + `workspace/page.tsx` + `report/page.tsx` | ✓ | Uses Next 16 `Promise<{...}>` params (`await` in Server, `use()` in Client). |
| `components/shell/{top-status-bar,workspace-layout}.tsx` | ✓ | 3-col grid `[332px / fluid / 374px]`. |
| `components/materials/left-material-panel.tsx` | ✓ | Filter, upload, textbook/chapter tree. |
| `components/graph/{graph-canvas,graph-toolbar,node-details}.tsx` | ✓ | Dynamic-imported react-force-graph-2d, custom canvas paint, highlight on click. |
| `components/decisions/right-integration-panel.tsx` | ✓ | Decision queue with optimistic accept/reject. |
| `components/chat/teacher-chat-console.tsx` | ✓ | Tool-call preview rows, send/ask. |
| `components/build/bottom-progress-bar.tsx` | ✓ | 5 visible pipeline steps, chunk-size sheet for rebuild. |
| `components/report/` | ❌ empty | Report UI lives inline in `app/projects/[projectId]/report/page.tsx`. Move to `components/report/` if it grows. |
| `lib/api.ts`, `lib/ws.ts`, `lib/types.ts`, `lib/graph-styles.ts`, `lib/utils.ts` | ✓ | Typed REST + WebSocket; types mirror backend `CamelModel` JSON. |
| `hooks/use-{project,materials,build,graph,decisions,chat}.ts` | ✓ | One hook per backend resource family; WebSocket cleanup wired. |

### Infra

| Area | Status | Notes |
|------|--------|-------|
| `docker-compose.yml` backend + chroma | ✓ | Frontend service is commented out — runs locally via `npm run dev` for hackathon iteration speed. |
| `backend/Dockerfile` | ✓ | Listed in compose. |
| `frontend/Dockerfile` | ❌ | Not yet authored. |
| `.env` / `.env.example` | unverified | Confirm `DATA_ROOT`, `TEXTBOOKS_DIR`, all `*_API_KEY` vars exist before demo. |
| Git commits | only 2 | `ecec890` init + `f47012e` backend review fix. The entire backend+frontend skeleton above is currently uncommitted. |

### Known gaps versus PRD

* `components/report/` is empty — the PRD calls for `ReportView` / `EssenceView`. Inline implementation in `report/page.tsx` is acceptable for v0.
* Backend has no per-scope retry endpoint; rebuild = new full job. PRD's "rebuild controls for teacher feedback" is implemented at the chunking-parameter level (the BottomProgressBar sheet) but not stage-scoped.
* No frontend `Dockerfile` — only backend is containerized. Demo path is `docker compose up` for backend+chroma + `npm run dev` for frontend.
* `agents/tools.py` defines `revise_decision` but `api/decisions.py` does not yet expose a revise endpoint.

## Technical Notes

* DeepSeek docs reference: https://api-docs.deepseek.com/zh-cn/
* ModelScope embedding reference: https://www.modelscope.cn/models/Qwen/Qwen3-Embedding-8B
* Model provider implementation guide: `docs/model-providers.md`.
* Deployment shape: Docker Compose with `frontend` (Next.js), `backend` (FastAPI), `chroma` (ChromaDB), and local storage volume.
* Backend is the only model gateway. Browser code must not call DeepSeek or ModelScope directly.
* Model provider configuration lives in the development directory `.env`; external document/data paths are also configured there via `DATA_ROOT` and `TEXTBOOKS_DIR`.
* DeepSeek chat configuration:
  * `DEEPSEEK_BASE_URL=https://api.deepseek.com`.
  * Primary model: `DEEPSEEK_MODEL=deepseek-v4-pro`.
  * Fallback model: `DEEPSEEK_FALLBACK_MODEL=deepseek-v4-flash`.
  * Use `reasoning_effort=high` and `extra_body={"thinking": {"type": "enabled"}}` by default.
  * Use `response_format={"type": "json_object"}` plus an explicit JSON schema prompt for structured extraction and graph operations.
  * DeepSeek handles LLM work: KG extraction, integration decisions, teacher dialogue, tool-call planning, cited answer generation, essence generation, and reports.
* ModelScope embedding configuration:
  * `MODELSCOPE_BASE_URL=https://api-inference.modelscope.cn/v1`.
  * `MODELSCOPE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B`.
  * Use OpenAI-compatible `client.embeddings.create(...)` with `encoding_format="float"`.
  * The embedding model handles vectorization only: RAG chunks, teacher queries, and duplicate-candidate retrieval.
  * Local connectivity testing confirmed a 4096-dimension embedding response.
* Persistence strategy:
  * ChromaDB for vector retrieval.
  * NetworkX + JSON files for knowledge graph state, operation log, and report drafts.
  * Local storage volume for uploaded materials, parsed text, graph JSON, Chroma data, and exported reports.
* Suggested backend module layout:
  * `api/`: projects, materials, build, graph, decisions, chat, report endpoints.
  * `core/`: config, model clients, storage, jobs.
  * `loaders/`: PDF, Markdown, Word, Excel loaders sharing a common document model.
  * `processing/`: sectioning, chunking, RAG index, graph builder, integration, essence generation.
  * `agents/`: integration agent, teacher dialogue agent, report agent, LangGraph flows.
  * `graph/`: NetworkX store, graph tools, graph schemas.
  * `models/`: shared Pydantic schemas.
* Suggested frontend module layout:
  * `app/page.tsx`: project overview.
  * `app/projects/[projectId]/workspace/page.tsx`: main integration workspace.
  * `app/projects/[projectId]/report/page.tsx`: report and essence output.
  * `components/shell/`: top status bar and workspace layout.
  * `components/materials/`: upload, material list, textbook/chapter tree.
  * `components/graph/`: graph canvas, graph toolbar, node details.
  * `components/decisions/`: integration decision queue, cards, evidence list.
  * `components/chat/`: teacher dialogue console and tool call preview.
  * `components/build/`: build progress strip.
  * `components/report/`: report and essence views.
  * `lib/`: API client, shared types, graph style helpers.
* RAG framing: semantic retrieval over textbook chunks followed by LLM answer generation with citations.
* Candidate RAG framework: LlamaIndex, using `VectorStoreIndex` and citation-oriented query flow.
* Candidate chunking strategy for Chinese textbooks: `chunk_size=500`, `chunk_overlap=100`, sentence-boundary splitting, no cross-chapter chunks.
* Candidate vector store: ChromaDB for fast local hackathon development.
* Candidate graph approach: NetworkX + JSON persistence instead of Neo4j to reduce infrastructure overhead.
* Graph nodes should include typed nodes such as `textbook`, `chapter`, `concept`, and possibly `chunk` if needed for traceability.
* Graph edges should include structural edges such as `contains` plus semantic edges such as `causes`, `belongs_to`, `manifests_as`, `located_in`, `related_to`, etc.
* Candidate agent workflow engine: LangGraph for iterative merge / deduplication flows if knowledge-graph merging is included.
* Teacher-facing rebuild controls can include chunk size, overlap, similarity threshold, and graph extraction scope.
* KG pipeline: textbook source -> LLM concept/relation extraction -> NetworkX graph -> JSON persistence -> react-force-graph visualization.
* RAG pipeline: textbook source -> chunking -> ModelScope embeddings -> ChromaDB -> cited retrieval -> DeepSeek answer generation.
* GraphRAG layer: use matched graph concepts/paths to guide retrieval and answer generation with cited textbook evidence.
* Integration pipeline: per-textbook graph -> candidate duplicate/complement/missing detection -> LLM decision with reason -> teacher dialogue -> graph operation tools -> integration report -> compressed essence output.
* Core problem decomposition should explicitly address GRAIN, DUPLICATE, FLOW, and RATIO.
* GRAIN: define knowledge points as independently teachable units rather than raw terms.
* DUPLICATE: use embedding similarity for candidate generation, graph structure for validation, and LLM judgment with evidence/reasoning for final merge/complement/conflict/distinct decisions.
* FLOW: use prerequisite graph constraints and topological ordering to generate the integrated teaching path; cycles or contradictory prerequisite edges become teacher-review conflicts.
* RATIO: use simple character counts for original parsed content and generated integrated essence content; display the ratio directly in the product and report.
* UI reference image path: `C:\Users\William\.codex\generated_images\019e0f97-34cb-7b02-b7d6-0740f77d8137\ig_061b4c0e84bfbd680169ffed88bf608193afe14931e86d08bb.png`.
* Main workspace layout:
  * `TopStatusBar`: product name, project status, textbook count, build status, compression target/current ratio, report export.
  * `LeftMaterialPanel`: multi-format material list, file type badges, textbook/chapter tree, chapter status.
  * `GraphCanvas`: dominant `react-force-graph` visualization for textbook, chapter, concept, and integration-decision nodes.
  * `RightIntegrationPanel`: duplicate/complement/missing/conflict decision queue with reason, evidence, confidence, accept/reject/follow-up actions.
  * `TeacherChatConsole`: natural-language teacher loop that exposes structured graph tool calls and explanations.
  * `BottomProgressBar`: multi-stage build progress for parsing, chapter recognition, single-graph construction, cross-textbook integration, RAG indexing, and essence generation.
* Suggested frontend route structure: `/` for project overview, `/projects/[projectId]/workspace` for the main integration workspace, and `/projects/[projectId]/report` for report and compressed essence output.
* Frontend graph library preference: `react-force-graph` instead of raw D3.js for faster product development with built-in zoom, drag, click, and force simulation.
* Realtime updates: FastAPI WebSocket can push updated graph JSON after teacher-driven graph changes. Full graph replacement is acceptable until graph scale proves otherwise.
* Graph operation primitives should be structured, for example `merge`, `split`, `restore`, `remove`, instead of applying natural-language changes directly.
* Core graph tools should include `merge_nodes`, `split_node`, `add_edge`, `remove_edge`, `restore_node`, `update_definition`, and `rebuild_scope`.
* Graph tool execution must update NetworkX state, persist JSON, append an operation log entry, and push updated graph data over WebSocket.
* Core shared data models:
  * `Project`: project metadata, build status, compression target, original/essence char counts, compression ratio.
  * `Material`: uploaded source file, file type, parsing status, char count.
  * `Section`: parsed textbook/chapter/section unit with hierarchy, order, page range, char count.
  * `Chunk`: section-scoped text chunk with citation metadata.
  * `KnowledgeNode`: textbook/chapter/concept node with definition, sources, frequency, merge status, teacher overrides.
  * `KnowledgeEdge`: typed relation edge with relation enum, evidence, and confidence.
  * `Evidence`: material, section, textbook, chapter, page range, quote.
  * `IntegrationDecision`: duplicate/complementary/missing/conflict decision with status, involved nodes, reason, evidence, confidence, suggested operation.
  * `GraphOperation`: structured graph tool call such as merge, split, add/remove edge, update definition, rename, restore, rebuild scope.
  * `BuildJob`: long-running build/rebuild state with per-stage progress.
  * `ChatMessage`: teacher/agent/system message with optional tool call and evidence.
  * `IntegrationReport`: generated report, teaching flow, decisions, essence content, and compression ratio.
* Build flow:
  * Upload materials and persist originals.
  * Parse each file through its format-specific loader into a common document model.
  * Identify sections/chapters and produce section-scoped chunks.
  * After parsing/sectioning, run KG construction and RAG indexing in parallel.
  * RAG path: chunk -> ModelScope embedding -> ChromaDB.
  * KG path: chunk/section -> DeepSeek concept/relation extraction -> NetworkX graph.
  * Integration path: per-textbook graph -> duplicate/complement/missing/conflict detection -> reasoned decisions -> teacher loop -> graph operations.
  * Report path: final graph + operation log + decisions -> teaching flow -> essence generation -> char-count ratio -> report export.
* Agent design:
  * `IntegrationAgent`: analyzes cross-textbook duplicate, complementary, missing, and conflict cases; outputs `IntegrationDecision` with reason and evidence.
  * `TeacherDialogueAgent`: converts teacher natural language plus selected graph context into structured `GraphOperation` calls or cited answers.
  * `ReportAgent`: generates teaching flow, compressed essence, compression ratio summary, and integration report.
  * Agents may reason with LLMs, but all state mutation must go through deterministic tools.
* Agent tool groups:
  * Graph tools: `merge_nodes`, `split_node`, `add_edge`, `remove_edge`, `update_definition`, `rename_node`, `restore_node`, `rebuild_scope`.
  * Integration tools: `find_duplicates`, `find_complements`, `find_missing_points`, `propose_merge`, `accept_decision`, `reject_decision`, `revise_decision`.
  * Evidence/RAG tools: `search_chunks`, `get_node_evidence`, `get_textbook_context`, `answer_with_citations`.
  * Report tools: `generate_teaching_flow`, `generate_essence`, `calculate_compression_ratio`, `generate_integration_report`, `export_report`.
  * Build tools: `load_documents`, `parse_sections`, `build_single_graph`, `build_rag_index`, `run_integration`.
* API contract:
  * `POST /api/projects`
  * `GET /api/projects/{project_id}`
  * `POST /api/projects/{project_id}/materials`
  * `GET /api/projects/{project_id}/materials`
  * `POST /api/projects/{project_id}/build`
  * `GET /api/projects/{project_id}/build/{job_id}`
  * `WS /api/projects/{project_id}/build/ws`
  * `GET /api/projects/{project_id}/graph`
  * `WS /api/projects/{project_id}/graph/ws`
  * `GET /api/projects/{project_id}/decisions`
  * `POST /api/projects/{project_id}/decisions/{decision_id}/accept`
  * `POST /api/projects/{project_id}/decisions/{decision_id}/reject`
  * `POST /api/projects/{project_id}/chat`
  * `POST /api/projects/{project_id}/ask`
  * `POST /api/projects/{project_id}/report/generate`
  * `GET /api/projects/{project_id}/report`
* Implementation principles:
  * Frontend displays state and collects user actions; it does not directly call model providers.
  * Backend model calls must go through `model_clients`.
  * Agents output structured decisions/operations, not direct graph mutations.
  * Graph tools must be deterministic, testable, logged, and reversible where feasible.
  * Every integration suggestion must include reason and evidence.
  * Long tasks must expose progress and allow failed scopes to be retried.
  * No prebuilt graph/RAG artifacts may be used for user-supplied materials.
  * Compression ratio is calculated by simple character count.
* Proposed environment variable names:
  * `DEEPSEEK_API_KEY`
  * `DEEPSEEK_BASE_URL`
  * `DEEPSEEK_MODEL`
  * `DEEPSEEK_FALLBACK_MODEL`
  * `DEEPSEEK_REASONING_EFFORT`
  * `DEEPSEEK_THINKING_TYPE`
  * `MODELSCOPE_API_KEY`
  * `MODELSCOPE_BASE_URL`
  * `MODELSCOPE_EMBEDDING_MODEL`
