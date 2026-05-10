# Component Guidelines

> How components are built in this project.

---

## Overview

Components use **shadcn/ui v4** primitives (under the hood: `@base-ui/react`) for base UI, **Tailwind v4** for layout/styling, and React 19 functional components with typed props. Each workspace area has its own component directory. Components are presentational — hooks own data and side effects.

The graph visualization library is **`react-force-graph-2d`** (loaded via dynamic import to keep canvas code out of the SSR bundle). Don't substitute `react-force-graph-3d` or raw D3 without checking the existing `graph-canvas.tsx` first.

---

## File Naming

- **File on disk: kebab-case.** `graph-canvas.tsx`, `top-status-bar.tsx`, `right-integration-panel.tsx`.
- **Exported symbol: PascalCase.** `export function GraphCanvas(...)`, `export function TopStatusBar(...)`.
- **No default exports.** Always named exports — keeps imports consistent with shadcn/ui.

---

## Component Structure

Real example from `components/graph/graph-canvas.tsx`:

```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ComponentType, MutableRefObject } from "react";
import type {
  ForceGraphMethods,
  ForceGraphProps,
  LinkObject,
  NodeObject,
} from "react-force-graph-2d";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { getEdgeColor, getNodeColor, getNodeSize } from "@/lib/graph-styles";
import type { GraphData, GraphLink, GraphNode } from "@/lib/types";

type GraphRef = MutableRefObject<ForceGraphMethods<GraphNode, GraphLink> | undefined>;
type ForceGraphComponent = ComponentType<ForceGraphProps<GraphNode, GraphLink> & { ref?: GraphRef }>;

interface GraphCanvasProps {
  data: GraphData;
  loading: boolean;
  highlightNodeIds?: string[];
  onNodeClick?: (node: GraphNode) => void;
}

export function GraphCanvas({ data, loading, highlightNodeIds, onNodeClick }: GraphCanvasProps) {
  const [ForceGraph, setForceGraph] = useState<ForceGraphComponent | null>(null);

  // Dynamic import — react-force-graph-2d touches `window` on import
  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default as unknown as ForceGraphComponent);
    });
  }, []);

  // ... ResizeObserver, custom canvas paint, ref handlers ...

  return (
    <div className="relative h-full w-full overflow-hidden" aria-label="教材知识图谱画布">
      {!loading && data.nodes.length > 0 && ForceGraph && (
        <ForceGraph
          graphData={data as unknown as ForceGraphProps<GraphNode, GraphLink>["graphData"]}
          nodeCanvasObject={nodeCanvasObject}
          linkColor={(link) => getEdgeColor(link.relation ?? "related_to")}
        />
      )}
    </div>
  );
}
```

Key rules from real code:
- `"use client"` at the top of any component using browser APIs, hooks, or event handlers.
- Props interface defined inline above the component — no separate `types.ts` per component.
- Destructure props in the function signature.
- Heavy/SSR-unsafe libraries (canvas, WebGL, force simulation) are loaded via `useEffect → import(...)`, **not** `next/dynamic` (the dynamic-import pattern is what `graph-canvas.tsx` uses today).

---

## Next.js 16 Page Pattern

Routes receive `params` as a **Promise** in Next 16. Two valid patterns:

**Server Component** (e.g., `app/projects/[projectId]/layout.tsx`):

```tsx
export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return (
    <div className="flex flex-1 flex-col h-screen overflow-hidden">
      <TopStatusBar projectId={projectId} />
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
```

**Client Component** (e.g., `app/projects/[projectId]/workspace/page.tsx`):

```tsx
"use client";
import { use } from "react";

export default function WorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);            // React 19 unwrap
  return <WorkspaceLayout projectId={projectId} />;
}
```

Don't write `params: { projectId: string }` — that pattern is from older Next versions and will break type-checks here.

---

## shadcn/ui v4 Specifics

shadcn v4 in this repo is built on `@base-ui/react`. Some primitives use a `render` prop instead of children to compose with arbitrary triggers/wrappers:

```tsx
<Tooltip>
  <TooltipTrigger render={<Button variant="ghost" size="icon" />}>
    <Hand className="h-4 w-4" />
  </TooltipTrigger>
  <TooltipContent side="right">拖拽平移</TooltipContent>
</Tooltip>
```

The same pattern applies to `Sheet`, `Dialog`, `DropdownMenu`. Look at `bottom-progress-bar.tsx` for `<SheetTrigger render={...}>` usage. Don't pass children directly to triggers — use `render` to inherit the wrapped element's behavior.

---

## Props Conventions

- Use `interface`, not `type`, for component props.
- Callback props use `on*` prefix: `onNodeClick`, `onAccept`, `onReject`.
- Optional callbacks use `?:` and are called with optional chaining: `onNodeClick?.(node)`.
- Avoid prop drilling beyond 2 levels — use hooks instead. Workspace-level state belongs in a hook (`useGraph`, `useDecisions`), not in `WorkspaceLayout`'s `useState`.
- No `children` in props unless the component is a layout/container (`WorkspaceLayout`, `ProjectLayout`).

---

## Styling

- **Tailwind v4 only.** No CSS modules, no styled-components, no inline `style` blocks (except the rare `borderLeft: '3px solid ...'` for dynamic decision colors — see `right-integration-panel.tsx:163`).
- Use `cn()` from `lib/utils.ts` (clsx + tailwind-merge) for conditional classes.
- shadcn/ui components handle their own styling — override with `className`. Don't fight the primitive's defaults; if you need a fundamentally different look, build a sibling component.
- Layout pattern: workspace uses fixed-width sidebars + flex-1 main: `grid-cols-[332px_minmax(520px,1fr)_374px]`. Desktop-first — no responsive breakpoints in the workspace.

```tsx
import { cn } from "@/lib/utils";

<div className={cn("flex items-center gap-2", isActive && "bg-blue-50", className)} />
```

---

## Accessibility

- Use semantic HTML: `<header>`, `<main>`, `<aside>`, `<section>`.
- The graph canvas container has `aria-label="教材知识图谱画布"` — keep `aria-label` on any non-text-content interactive surface.
- Dialogs/sheets/tooltips use shadcn primitives which handle focus trap and `aria-modal` automatically.
- Buttons inside icon-only triggers must remain real `<Button>` components (via `render={<Button .../>}`) so screen readers receive the role.

---

## Common Mistakes

- Don't put data fetching in components — extract to a hook in `hooks/`.
- Don't use `useEffect` to sync props into local state — use props directly or compute via `useMemo`.
- Don't use `any` in prop types — `unknown` + type guard if needed.
- Don't mix server components with client-only hooks — add `"use client"` at the top.
- Don't import `react-force-graph-2d` at module top-level — it touches `window` on import; use `useEffect → import(...)`.
- Don't forget `params: Promise<{...}>` in Next 16. Use `await params` (Server) or `use(params)` (Client).
- Don't write `tailwind.config.ts` — there isn't one. Tailwind v4 config lives in `globals.css`.
