# Hook Guidelines

> How hooks are used in this project.

---

## Overview

Custom hooks own all data fetching, WebSocket subscriptions, and server state. Components stay presentational. Hooks live in `frontend/hooks/`. Data fetching uses the typed API client in `lib/api.ts` — **no React Query, SWR, or Zustand** for this hackathon.

---

## Hooks That Exist Today

| Hook | File | Returns | Notes |
|------|------|---------|-------|
| `useProjects()` | `use-project.ts` | `{ projects, loading, error, create }` | Lists all projects; `create(name)` POSTs and appends locally. |
| `useProject(projectId)` | `use-project.ts` | `{ project, loading, error, setProject }` | Single project fetch; setter exposed for optimistic updates. |
| `useMaterials(projectId)` | `use-materials.ts` | `{ materials, loading, error, upload }` | Lists + multipart upload via `api.uploadMaterial`. |
| `useBuild(projectId)` | `use-build.ts` | `{ job, loading, error, startBuild, isBuilding, stages }` | WebSocket subscription via `createBuildWs`; `startBuild(chunkSize?, chunkOverlap?)` POSTs and seeds `job` from the response. |
| `useGraph(projectId)` | `use-graph.ts` | `{ graph, loading, error, selectedNode, highlightIds, handleNodeClick, clearSelection }` | Initial REST fetch + WebSocket; tracks selection and highlights connected neighbors. |
| `useDecisions(projectId)` | `use-decisions.ts` | `{ decisions, loading, error, accept, reject }` | Optimistic accept/reject with automatic rollback on failure. |
| `useChat(projectId)` | `use-chat.ts` | `{ messages, sending, error, sendMessage, askQuestion, clearMessages }` | Posts to `/chat` (with tool-call rendering) and `/ask` (RAG cited answer); merges tool-call previews into the message stream. |

If you need a new resource family (e.g., reports as a stream), add a new file `use-<resource>.ts` rather than expanding an existing hook past its single concern.

---

## Standard Hook Pattern

```ts
// hooks/use-graph.ts (real)
"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { createGraphWs } from "@/lib/ws";
import type { GraphData, GraphLink, GraphNode, ProjectId } from "@/lib/types";

const EMPTY_GRAPH: GraphData = { nodes: [], links: [] };

export function useGraph(projectId: ProjectId) {
  const [graph, setGraph] = useState<GraphData>(EMPTY_GRAPH);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightIds, setHighlightIds] = useState<string[]>([]);

  // Initial REST fetch — cancelled flag guards against state-after-unmount
  useEffect(() => {
    let cancelled = false;
    api.getGraph(projectId)
      .then((data) => { if (!cancelled) setGraph(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [projectId]);

  // WebSocket — cleanup closes the socket on projectId change / unmount
  useEffect(() => {
    const ws = createGraphWs(projectId, (newGraph) => setGraph(newGraph));
    return () => ws.close();
  }, [projectId]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    const connected = graph.links
      .filter((l) => endpointId(l.source) === node.id || endpointId(l.target) === node.id)
      .flatMap((l) => [endpointId(l.source), endpointId(l.target)]);
    setHighlightIds([...new Set([node.id, ...connected])]);
  }, [graph.links]);

  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setHighlightIds([]);
  }, []);

  return { graph, loading, error, selectedNode, highlightIds, handleNodeClick, clearSelection };
}
```

Key rules:
- `"use client"` on every hook file (they all use React state/effects).
- `cancelled` flag inside async `useEffect` to prevent state updates after unmount.
- Cleanup in `useEffect` return: close WebSocket, abort fetch, clear timer.
- Wrap event handlers in `useCallback` with stable deps.
- Return shape is `{ <data fields>, loading, error, <action functions> }`.
- One hook per backend resource family — don't combine graph + build + chat.

---

## Data Fetching

- **REST:** Always go through `api.*` from `lib/api.ts`. The wrapper handles JSON/FormData headers and throws on `!res.ok`.
- **WebSocket:** Use `createGraphWs(projectId, onUpdate)` and `createBuildWs(projectId, onUpdate)` from `lib/ws.ts`. They JSON-parse the message and adapt `edges` ↔ `links` shape so the consumer always gets `GraphData`.
- **No polling.** WebSocket pushes graph updates and build progress.
- **Optimistic updates:** For accept/reject decisions, update local state immediately, then fire the API call. Roll back if the call fails. Real example from `use-decisions.ts`:

```ts
const accept = useCallback(async (decisionId: string) => {
  setDecisions((prev) =>
    prev.map((d) => (d.id === decisionId ? { ...d, status: "accepted" as const } : d)),
  );
  try {
    await api.acceptDecision(projectId, decisionId);
  } catch {
    setDecisions((prev) =>
      prev.map((d) => (d.id === decisionId ? { ...d, status: "pending" as const } : d)),
    );
  }
}, [projectId]);
```

---

## Tool-Call Rendering Pattern (`use-chat.ts`)

The `/chat` endpoint returns `{ message, toolCalls, toolResults, modelUsed }`. The hook synthesizes synthetic `ChatMessage` rows for each tool call so the chat UI can render them inline:

```ts
const toolMessages = buildToolMessages(projectId, result.toolCalls, result.toolResults ?? []);
setMessages((prev) => [...prev, ...toolMessages, result.message]);
```

`buildToolMessages` normalizes both `{function: {name, arguments}}` (DeepSeek shape) and `{name, params}` shapes via `normalizeToolCall`, parses string arguments as JSON, and tags each row with `role: "tool_call"`. When you add a new tool category, extend the normalization here rather than in the component.

---

## Naming Conventions

| Pattern | Convention | Example |
|---------|-----------|---------|
| Hook export | `use` + camelCase | `useGraph`, `useDecisions` |
| Hook file | `use-` + kebab-case | `use-graph.ts`, `use-decisions.ts` |
| Return data | named after the resource | `graph`, `decisions`, `messages` |
| Loading/error | always `loading: boolean`, `error: string \| null` | every hook |
| Action function | verb, optionally async | `accept`, `reject`, `upload`, `startBuild`, `sendMessage` |

---

## Common Mistakes

- Don't fetch data in components — always extract to a hook.
- Don't forget cleanup in `useEffect` (cancel fetch via `cancelled` flag, close WebSocket via `ws.close()`).
- Don't combine multiple resource families into one hook (no `useWorkspace` mega-hook).
- Don't use `useEffect` for user-action side effects — use event handlers wrapped in `useCallback`.
- Don't introduce React Query/SWR/Zustand without checking with the team — the current hook pattern is intentional for hackathon speed.
- Don't poll backend endpoints when a WebSocket exists (`/build/ws`, `/graph/ws` are the live channels).
