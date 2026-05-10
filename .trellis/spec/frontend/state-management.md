# State Management

> How state is managed in this project.

---

## Overview

No global state library. State lives in three layers: **local** (component `useState`), **hook-level** (custom hooks owning a single backend resource family), and **URL** (Next 16 `Promise<{ projectId }>`). Server state is fetched/cached inside hooks. WebSocket updates push directly into hook-level state via `lib/ws.ts` helpers.

The 6 hooks today (`use-project`, `use-materials`, `use-build`, `use-graph`, `use-decisions`, `use-chat`) each own one backend resource family. Components consume them and never call `fetch` directly.

---

## State Categories

| Category | Where it lives | Example |
|----------|---------------|---------|
| **Local UI state** | `useState` in component | dialog open/close, selected tab, chunk-size slider position |
| **Domain data** | Custom hook in `hooks/` | graph data, materials list, decisions queue, build progress, chat messages |
| **URL state** | Next 16 `Promise<{ projectId }>` route params | `projectId`, route path (`/workspace`, `/report`) |
| **Server state** | Fetched via hook, stored in `useState` | project metadata, chat history, report content |
| **Live state** | Pushed by WebSocket into the hook's `useState` | graph snapshot (`/graph/ws`), build job (`/build/ws`) |

---

## When to Use Global State

**Almost never for this hackathon.** The workspace page is the only complex screen, and its data flows through 4-5 hooks that each own their domain. Cross-hook communication is handled by:

- Passing callbacks as props (e.g., `onNodeClick` from graph hook to GraphCanvas to NodeDetails).
- Lifting shared state to the workspace page component when two sibling hooks need the same data.

If a piece of state is needed by 3+ unrelated components, consider a React Context — but this hasn't happened yet.

---

## Server State

- **Fetch-once data** (project, materials list): fetched in `useEffect` on mount, stored in `useState`, no refetch unless user triggers mutation.
- **Live data** (graph, build progress): WebSocket pushes updates into `useState` via the hook's `onMessage` handler.
- **Mutation results** (accept decision, upload material): optimistic local update → API call → rollback on failure.
- **No cache invalidation library.** For a hackathon, re-fetching on mount or relying on WebSocket push is sufficient.

```ts
// Pattern: optimistic update with rollback
const handleAccept = useCallback(async (decisionId: string) => {
  setDecisions((prev) => updateDecisionStatus(prev, decisionId, "accepted"));
  try {
    await api.acceptDecision(projectId, decisionId);
  } catch {
    setDecisions((prev) => updateDecisionStatus(prev, decisionId, "pending"));
  }
}, [projectId]);
```

---

## Common Mistakes

- Don't store server data in React Context — use hooks with `useState`.
- Don't use `useEffect` to sync derived state — compute it inline or with `useMemo`.
- Don't create a global store for the hackathon — the workspace page component is the natural coordination point.
- Don't forget to clean up WebSocket subscriptions in `useEffect` return.
