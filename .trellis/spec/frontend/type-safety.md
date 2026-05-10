# Type Safety

> Type safety patterns in this project.

---

## Overview

TypeScript strict mode. All shared types live in **`frontend/lib/types.ts`** and mirror the backend's `CamelModel` JSON output exactly. The backend's `models/base.py:CamelModel` uses `alias_generator=to_camel`, so Python `parse_status` becomes JSON `parseStatus`, `involved_node_ids` becomes `involvedNodeIds`, and so on. Keep this file in sync manually whenever a backend Pydantic model changes.

There is no Zod / runtime validation library — trust the typed API client and surface parse errors at the hook's `error` boundary.

---

## Type Organization

```
lib/
├── types.ts        # All shared types (mirrors backend models)
├── api.ts          # Typed REST wrapper, request/response types per method
└── ws.ts           # WebSocket message types (GraphData / BuildJob)
```

- **Single source of truth:** `lib/types.ts` for domain types.
- **No per-component type files.** Component props are defined inline with `interface`.
- **No type generation.** Manually keep `lib/types.ts` aligned with `backend/models/*.py`. When a backend model changes, update the matching TS interface and search-replace any consumer.

---

## Core Types (real, as of 2026-05-10)

These match the actual `lib/types.ts`. Field names use camelCase because the backend's `CamelModel` serializes that way.

```ts
// Project
export type BuildStatus = "pending" | "running" | "completed" | "failed" | "partial";

export interface Project {
  id: ProjectId;
  name: string;
  status: BuildStatus;                 // not `buildStatus`
  compressionTarget: number;           // default 0.3 from backend
  originalCharCount: number;
  essenceCharCount: number;
  compressionRatio: number | null;
  createdAt: string;
  updatedAt: string;
}

// Material
export type FileType = "pdf" | "md" | "docx" | "xlsx";   // matches FileType enum (NOT "markdown"/"word"/"excel")
export type ParseStatus = "pending" | "parsing" | "done" | "failed";

export interface Material {
  id: string;
  projectId: ProjectId;
  filename: string;
  fileType: FileType;
  filePath: string;
  parseStatus: ParseStatus;
  charCount: number;
  createdAt: string;
}

// Knowledge Graph
export type NodeType = "textbook" | "chapter" | "concept";
export type RelationType =
  | "contains" | "prerequisite" | "parallel" | "containment" | "application"
  | "duplicate" | "complementary" | "missing"
  | "causes" | "belongs_to" | "manifests_as" | "located_in" | "related_to";

export interface KnowledgeNode {
  id: string;
  type: NodeType;                      // not `nodeType`
  label: string;
  definition: string;
  sources: string[];                   // chunk IDs
  frequency: number;
  mergeStatus: string | null;          // null | "merged_into_<canonical_id>"
  teacherOverrides: Record<string, unknown>;
  createdAt: string;
}

export interface KnowledgeEdge {
  id: string;
  source: string;
  target: string;
  relation: RelationType;
  evidence: Evidence[];
  confidence: number;
  createdAt: string;
}

export interface Evidence {
  materialId: string;
  textbook: string;
  chapter: string;
  pageStart: number | null;
  pageEnd: number | null;
  quote: string;
}

// Integration
export type DecisionType = "duplicate" | "complementary" | "missing" | "conflict";
export type DecisionStatus = "pending" | "accepted" | "rejected" | "revised";

export interface IntegrationDecision {
  id: string;
  projectId: ProjectId;
  type: DecisionType;                  // not `decisionType`
  status: DecisionStatus;
  involvedNodeIds: string[];
  reason: string;
  evidence: string[];
  confidence: number;
  suggestedOperation: GraphOperation | null;
  teacherFeedback: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface GraphOperation {
  id: string;
  operation: string;                   // "merge_nodes" | "split_node" | "add_edge" | ...
  params: Record<string, unknown>;
  reason: string;
  success: boolean;
  error: string | null;
  timestamp: string;
}

// Build
export interface BuildJob {
  id: string;
  projectId: ProjectId;
  status: BuildStatus;
  stages: Record<string, BuildStage>;  // keyed by stage name
  currentStage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BuildStage {
  name: string;
  status: BuildStatus;
  progress: number;                    // 0..1, NOT 0..100
  message: string;
  error: string | null;
}

// Chat
export type MessageRole = "teacher" | "agent" | "system" | "tool_call";

export interface ChatMessage {
  id: string;
  projectId: ProjectId;
  role: MessageRole;
  content: string;
  toolCall: ToolCallData | null;
  evidence: string[];
  createdAt: string;
}

// Graph data shape consumed by react-force-graph-2d
export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];                  // backend sends `edges`; lib/api.ts adapts to `links`
}

export interface GraphNode {
  id: string;
  type: NodeType;
  label: string;
  definition?: string;
  frequency: number;
  mergeStatus: string | null;
  sources?: string[];
  teacherOverrides?: Record<string, unknown>;
  createdAt?: string;
  x?: number;                          // injected by force-simulation
  y?: number;
}

export interface GraphLink {
  id?: string;
  source: string | GraphNode;          // resolves to GraphNode after first tick
  target: string | GraphNode;
  relation: RelationType;
  confidence: number;
  evidence?: Evidence[];
  createdAt?: string;
}

// Report
export interface IntegrationReport {
  id: string;
  projectId: ProjectId;
  teachingFlow: TeachingFlowStep[];
  decisionsSummary: Record<string, number>;
  essenceContent: string;
  originalCharCount: number;
  essenceCharCount: number;
  compressionRatio: number;            // 0..1
  generatedAt: string;
}
```

> Common confusion: backend `BuildStage.progress` is a **0..1 float**, not a 0..100 percent. The UI multiplies by 100 when rendering (`bottom-progress-bar.tsx:137`).

---

## Validation

**No runtime validation library** (hackathon shortcut). Instead:

- API responses are typed via `api.*` return types — trust the backend.
- WebSocket messages are typed via `GraphData`, `BuildJob`. The `lib/ws.ts` parser tolerates both `data.edges` and `data.links` because the backend sends `edges`.
- If a response fails to parse, `lib/api.ts` throws `Error("API <status>: <body>")` — catch at the hook boundary and surface in the hook's `error` state.

If we eventually need runtime validation, add Zod schemas alongside each `interface` rather than introducing a separate `schemas/` tree.

---

## Common Patterns

```ts
// Discriminated unions for status fields
function statusBadgeColor(status: BuildStatus): string {
  switch (status) {
    case "completed": return "emerald";
    case "running":   return "blue";
    case "failed":    return "red";
    case "partial":   return "amber";
    default:          return "slate";
  }
}

// Type guard for graph endpoints (force-sim resolves string→object after first tick)
function endpointId(endpoint: GraphLink["source"]): string {
  return typeof endpoint === "string" ? endpoint : endpoint.id;
}

// Readonly for data that shouldn't be mutated
function getNodeLabel(node: Readonly<GraphNode>): string {
  return node.label;
}
```

---

## Forbidden Patterns

| Pattern | Why |
|---------|-----|
| `any` | Use `unknown` + type guard. The only `any` in the codebase is in `JSON.parse` boundaries — keep it confined to those. |
| `as` type assertion (except `as const` and the documented `react-force-graph-2d` cast in `graph-canvas.tsx`) | Hides type mismatches. Fix the source type instead. |
| `// @ts-ignore` / `// @ts-expect-error` | Masks real errors — fix the type. |
| Loose object types (`{}`, `object`) | Use explicit `interface` or `Record<string, unknown>`. |
| Enum types | Use string literal unions (matches backend Pydantic enums serialized as strings). |
| Renaming a backend-aliased field on the TS side | Breaks API contract — keep camelCase exactly as `CamelModel` emits. |
