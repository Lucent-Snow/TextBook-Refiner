// WebSocket client helpers for real-time graph and build updates.

import type { GraphData, BuildJob, ProjectId } from "./types";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type MessageHandler<T> = (data: T) => void;

function createWs(path: string, onMessage: (raw: MessageEvent) => void): WebSocket {
  const ws = new WebSocket(`${WS_BASE}${path}`);
  ws.onmessage = onMessage;
  ws.onerror = (e) => console.error("[ws] error:", e);
  return ws;
}

export function createGraphWs(
  projectId: ProjectId,
  onUpdate: MessageHandler<GraphData>,
): WebSocket {
  return createWs(`/api/projects/${projectId}/graph/ws`, (event) => {
    try {
      const data = JSON.parse(event.data as string) as { nodes?: unknown[]; edges?: unknown[]; links?: unknown[] };
      onUpdate({
        nodes: data.nodes ?? [],
        links: data.links ?? data.edges ?? [],
      } as GraphData);
    } catch (e) {
      console.error("[ws] failed to parse graph message:", e);
    }
  });
}

export function createBuildWs(
  projectId: ProjectId,
  onUpdate: MessageHandler<BuildJob>,
): WebSocket {
  return createWs(`/api/projects/${projectId}/build/ws`, (event) => {
    try {
      const data = JSON.parse(event.data as string) as BuildJob;
      onUpdate(data);
    } catch (e) {
      console.error("[ws] failed to parse build message:", e);
    }
  });
}
