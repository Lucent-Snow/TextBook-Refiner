# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Hackathon-speed quality: type safety + lint pass, but no formal test suite. Focus on preventing runtime crashes and keeping the UI functional during demo. Stack: **Next.js 16.2.6, React 19.2.4, Tailwind v4, shadcn/ui (on `@base-ui/react`), TypeScript strict**.

---

## Forbidden Patterns

| Pattern | Why |
|---------|-----|
| `any` type | Defeats TypeScript — use `unknown` + type guard if needed |
| `// @ts-ignore` / `// @ts-expect-error` | Masks real errors — fix the type instead |
| Direct `fetch()` in components | Bypasses typed API client — use `api.*` from `lib/api.ts` |
| Calling DeepSeek/ModelScope from browser | Security violation — all LLM calls go through backend |
| Default exports in components | Inconsistent imports — use named exports |
| CSS modules / styled-components / `<style jsx>` | Project uses Tailwind v4 only |
| `useEffect` without cleanup | Memory leaks — always return cleanup for subscriptions, timers, fetches |
| Hardcoded API URLs | Use `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` (defaults to `http://localhost:8000` / `ws://localhost:8000`) |
| Committing `.env` or API keys | Security — `.env` is gitignored; keys belong in backend env only |
| `params: { id: string }` in Next 16 routes | `params` is now `Promise<{...}>`. Use `await params` (Server) or `use(params)` (Client). |
| PascalCase component filenames (`GraphCanvas.tsx`) | Project convention is kebab-case (`graph-canvas.tsx`) — matches shadcn/ui defaults |
| Top-level `import` of `react-force-graph-2d` | Touches `window` on import — load via `useEffect → import(...)` |
| Creating `tailwind.config.ts` | Tailwind v4 reads config from `globals.css`; no JS config file |

---

## Required Patterns

| Pattern | Where |
|---------|-------|
| `"use client"` directive on any component/hook using browser APIs or React hooks | Top of file |
| Typed props via `interface` | Every component |
| `cn()` for conditional class merging | All Tailwind class composition (`lib/utils.ts`) |
| `cancelled` flag in async `useEffect` | Every hook with `fetch` |
| Cleanup in `useEffect` return | Every hook with WebSocket / timer / subscription |
| Named exports | All components and hooks |
| `aria-label` on non-semantic interactive elements | Accessibility (graph canvas, icon-only buttons inside `<TooltipTrigger render={<Button/>}>`) |
| Optimistic update with rollback for user actions | `use-decisions.ts` is the reference pattern |

---

## Testing Requirements

**Hackathon minimum — no formal frontend test suite required.** Instead:

- TypeScript strict mode must pass (`tsc --noEmit`).
- ESLint must pass with zero errors (`npm run lint` — uses `eslint-config-next` 16.2.6 flat config).
- Manual smoke test: workspace page loads, graph renders, upload works, chat sends, build progress streams over WebSocket.
- Browser check after UI changes via Chrome DevTools MCP (start with `C:\Users\William\.codex\scripts\start-chrome.bat` per global protocol).

---

## Code Review Checklist

- [ ] No `any` or `@ts-ignore`
- [ ] Components use kebab-case filenames + PascalCase named exports
- [ ] Hooks clean up effects (WebSocket close, fetch cancel via `cancelled` flag)
- [ ] API calls go through `lib/api.ts`, not raw `fetch`
- [ ] No model provider calls from frontend (DeepSeek/ModelScope must go through backend)
- [ ] Tailwind v4 only — no CSS modules, styled-components, or inline `style` (one documented exception: dynamic `borderLeft` in `right-integration-panel.tsx`)
- [ ] Props typed with `interface`
- [ ] `"use client"` on all client components/hooks
- [ ] Next 16 `params: Promise<{...}>` pattern with `await` (Server) or `use()` (Client)
- [ ] shadcn/ui v4 triggers use `render={<Button .../>}` rather than passing children directly

