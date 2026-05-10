# Directory Structure

> How frontend code is organized in this project.

---

## Overview

Next.js **16.2.6** App Router project (React 19.2.4) with Tailwind **v4** and shadcn/ui (built on `@base-ui/react`). Components are grouped by workspace area (graph, materials, decisions, chat, build, report). Shared utilities live in `lib/`. Custom hooks live in `hooks/`.

> ⚠️ Heads-up: Next.js 16 introduces breaking changes versus prior versions — `params` in route components is now `Promise<{...}>` (must be `await`-ed in Server Components or unwrapped via `use(params)` in Client Components). See `frontend/AGENTS.md` for the canonical reminder. Read `node_modules/next/dist/docs/` before reaching for stale Next.js patterns.

---

## Directory Layout (real, as of 2026-05-10)

```
frontend/
├── app/
│   ├── layout.tsx                              # Root layout (Geist fonts, TooltipProvider, globals.css)
│   ├── page.tsx                                # Project overview + "Create Project" form (/)
│   ├── globals.css
│   ├── favicon.ico
│   └── projects/
│       └── [projectId]/
│           ├── layout.tsx                      # Server component, awaits params, mounts <TopStatusBar/>
│           ├── workspace/
│           │   └── page.tsx                    # Client; uses use(params), renders <WorkspaceLayout/>
│           └── report/
│               └── page.tsx                    # Client; report view + Generate/Regenerate
├── components/
│   ├── ui/                                     # shadcn/ui v4 primitives (14 files)
│   │   ├── avatar.tsx  badge.tsx  button.tsx  card.tsx  dialog.tsx
│   │   ├── dropdown-menu.tsx  input.tsx  progress.tsx  scroll-area.tsx
│   │   ├── separator.tsx  sheet.tsx  tabs.tsx  textarea.tsx  tooltip.tsx
│   ├── shell/                                  # Layout + chrome
│   │   ├── top-status-bar.tsx                  # Header: project name, build status, compression badge, export
│   │   └── workspace-layout.tsx                # 3-col grid (332px / fluid / 374px) wiring all panels
│   ├── materials/
│   │   └── left-material-panel.tsx             # File-type filter, upload, textbook/chapter tree
│   ├── graph/
│   │   ├── graph-canvas.tsx                    # Dynamic-imports react-force-graph-2d, custom canvas paint
│   │   ├── graph-toolbar.tsx                   # Zoom/layer/legend controls above canvas
│   │   └── node-details.tsx                    # Floating panel for the selected concept
│   ├── decisions/
│   │   └── right-integration-panel.tsx         # Decision queue with accept/reject/follow-up
│   ├── chat/
│   │   └── teacher-chat-console.tsx            # Teacher dialogue with tool-call previews
│   ├── build/
│   │   └── bottom-progress-bar.tsx             # 5-stage pipeline strip + chunk-size sheet
│   └── report/                                 # ⚠️ Currently EMPTY — report UI is inline in app/projects/[projectId]/report/page.tsx
├── lib/
│   ├── api.ts                                  # Typed REST client (fetch wrapper, throws on !res.ok)
│   ├── ws.ts                                   # createGraphWs / createBuildWs helpers
│   ├── types.ts                                # All shared types (mirrors backend CamelModel JSON shape)
│   ├── graph-styles.ts                         # NODE_COLORS, EDGE_COLORS, NODE_TYPE_LABELS, RELATION_LABELS
│   └── utils.ts                                # cn(clsx + tailwind-merge)
├── hooks/                                      # 6 hooks today (one per backend resource family)
│   ├── use-project.ts                          # useProjects() list+create AND useProject(id)
│   ├── use-materials.ts                        # list + upload (multipart)
│   ├── use-build.ts                            # WebSocket subscription + startBuild()
│   ├── use-graph.ts                            # initial fetch + WebSocket + selectedNode/highlight state
│   ├── use-decisions.ts                        # list + optimistic accept/reject with rollback
│   └── use-chat.ts                             # sendMessage (chat) + askQuestion (RAG ask)
├── public/
├── components.json                             # shadcn config
├── eslint.config.mjs                           # ESLint 9 flat config + eslint-config-next
├── next-env.d.ts
├── next.config.ts
├── package.json                                # next 16.2.6, react 19.2.4, tailwind 4
├── postcss.config.mjs                          # @tailwindcss/postcss plugin (NO tailwind.config.ts in v4)
├── tsconfig.json
├── AGENTS.md                                   # Reminder: this is Next 16, not your training-cutoff Next
├── CLAUDE.md                                   # Re-exports AGENTS.md
└── README.md
```

There is **no `tailwind.config.ts`** — Tailwind v4 reads its config from `globals.css` via `@import "tailwindcss"` and CSS layer directives. Don't reach for `tailwind.config.ts` patterns from older docs.

---

## Module Organization

- **Routes** in `app/` follow the PRD: project overview (`/`), main workspace (`/projects/[id]/workspace`), report (`/projects/[id]/report`). The `[projectId]/layout.tsx` mounts `<TopStatusBar/>` and is shared across workspace + report.
- **Components** are grouped by workspace area, not by widget type (no `buttons/`, `cards/` top-level dirs). Most groups have a single dominant component file today; split only when one file exceeds ~300 lines or hosts multiple unrelated concerns.
- **Shared types** live in `lib/types.ts` and mirror the backend's `CamelModel` JSON output exactly (snake_case attributes serialize to camelCase, hence `parseStatus`, `compressionRatio`, `involvedNodeIds`).
- **Hooks** encapsulate all data fetching, WebSocket subscriptions, and optimistic mutations — components stay presentational.
- **`lib/api.ts`** is the only place that calls `fetch`. Components and hooks always go through `api.*`.

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Component files | **kebab-case** (matches shadcn) | `graph-canvas.tsx`, `top-status-bar.tsx` |
| Component exports | PascalCase named export | `export function GraphCanvas(...)` |
| Hook files | `use-` + kebab-case | `use-graph.ts`, `use-decisions.ts` |
| Hook exports | camelCase | `export function useGraph(...)` |
| Utility files | camelCase or kebab-case | `graph-styles.ts`, `utils.ts` |
| Type files | camelCase | `types.ts` |
| Route directories | bracketed dynamic segments | `[projectId]/` |
| Tailwind | utility-first, never CSS modules | `className="flex gap-2"` |

> ⚠️ Don't import a component as `GraphCanvas.tsx` — the file on disk is `graph-canvas.tsx`. The exported symbol is PascalCase, the filename is kebab-case.

---

## Examples

- `components/graph/graph-canvas.tsx` — dynamic-imports `react-force-graph-2d` (`useEffect → import(...).then`) so SSR doesn't pull canvas code; uses `nodeCanvasObject` for custom rendering.
- `hooks/use-graph.ts` — initial REST fetch + WebSocket subscription via `createGraphWs(projectId, setGraph)`, plus `selectedNode`/`highlightIds` UI state and `handleNodeClick` that highlights connected neighbors.
- `lib/api.ts` — single `request<T>()` wrapper that handles JSON vs `FormData` headers, throws `Error("API <status>: <body>")` on `!res.ok`. The `getGraph` adapter normalizes `edges` ↔ `links` so the response works directly with `react-force-graph`.
- `app/projects/[projectId]/workspace/page.tsx` — client component, uses `use(params)` (React 19 / Next 16 unwrap) to read `projectId` from a `Promise`.
- `components/shell/workspace-layout.tsx` — defines the 3-col grid `grid-cols-[332px_minmax(520px,1fr)_374px]` and stitches `LeftMaterialPanel` / `GraphToolbar+GraphCanvas+NodeDetails` / `RightIntegrationPanel+TeacherChatConsole`, with `BottomProgressBar` underneath.
