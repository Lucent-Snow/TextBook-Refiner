// Typed REST API client — all backend calls go through here.
// Frontend must NEVER call DeepSeek/ModelScope directly.

import type {
  Project,
  ProjectId,
  Material,
  IntegrationDecision,
  BuildJob,
  ChatMessage,
  GraphData,
  GraphLink,
  GraphNode,
  IntegrationReport,
  ToolResultData,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: isFormData
      ? init?.headers
      : { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    console.error(`[api] ${path} failed with ${res.status}`, body);
    throw new Error(`API ${res.status}: ${getFriendlyError(res.status)}`);
  }
  return res.json() as Promise<T>;
}

function getFriendlyError(status: number): string {
  if (status === 400) return "请求参数不正确，请检查输入后重试。";
  if (status === 401 || status === 403) return "当前没有权限执行该操作。";
  if (status === 404) return "请求的资源不存在或尚未生成。";
  if (status >= 500) return "服务暂时不可用，请稍后重试。";
  return "请求失败，请稍后重试。";
}

// ── Projects ─────────────────────────────────────────────
export const api = {
  createProject(name: string) {
    return request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  getProject(projectId: ProjectId) {
    return request<Project>(`/api/projects/${projectId}`);
  },

  listProjects() {
    return request<Project[]>("/api/projects");
  },

  // ── Materials ────────────────────────────────────────────
  uploadMaterial(projectId: ProjectId, file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<Material>(`/api/projects/${projectId}/materials`, {
      method: "POST",
      headers: {},
      body: form,
    });
  },

  listMaterials(projectId: ProjectId) {
    return request<Material[]>(`/api/projects/${projectId}/materials`);
  },

  // ── Build ────────────────────────────────────────────────
  startBuild(projectId: ProjectId, params?: { chunkSize?: number; chunkOverlap?: number }) {
    return request<{ jobId: string; status: string }>(
      `/api/projects/${projectId}/build`,
      {
        method: "POST",
        body: JSON.stringify(params ?? {}),
      },
    );
  },

  getBuildStatus(projectId: ProjectId, jobId: string) {
    return request<BuildJob>(`/api/projects/${projectId}/build/${jobId}`);
  },

  // ── Graph ────────────────────────────────────────────────
  async getGraph(projectId: ProjectId): Promise<GraphData> {
    const data = await request<{ nodes: GraphNode[]; edges?: GraphLink[]; links?: GraphLink[] }>(
      `/api/projects/${projectId}/graph`,
    );
    return {
      nodes: data.nodes,
      links: data.edges ?? data.links ?? [],
    };
  },

  // ── Decisions ────────────────────────────────────────────
  listDecisions(projectId: ProjectId) {
    return request<IntegrationDecision[]>(
      `/api/projects/${projectId}/decisions`,
    );
  },

  runIntegrationDetect(projectId: ProjectId) {
    return request<IntegrationDecision[]>(
      `/api/projects/${projectId}/decisions/detect`,
      { method: "POST" },
    );
  },

  acceptDecision(projectId: ProjectId, decisionId: string, note?: string) {
    return request<{ applied: boolean; operation: string }>(
      `/api/projects/${projectId}/decisions/${decisionId}/accept`,
      { method: "POST", body: JSON.stringify({ note }) },
    );
  },

  rejectDecision(projectId: ProjectId, decisionId: string, reason: string) {
    return request<{ rejected: boolean; decisionId: string }>(
      `/api/projects/${projectId}/decisions/${decisionId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) },
    );

  },

  // ── Chat ─────────────────────────────────────────────────
  sendMessage(projectId: ProjectId, message: string, contextNodeIds: string[] = []) {
    return request<{
      message: ChatMessage;
      toolCalls: unknown[];
      toolResults?: ToolResultData[];
      modelUsed: string;
    }>(
      `/api/projects/${projectId}/chat`,
      {
        method: "POST",
        body: JSON.stringify({ message, contextNodeIds }),
      },
    );
  },

  askQuestion(projectId: ProjectId, question: string, topK: number = 5) {
    return request<{ answer: string; citations: unknown[]; modelUsed: string }>(
      `/api/projects/${projectId}/ask`,
      {
        method: "POST",
        body: JSON.stringify({ question, topK }),
      },
    );
  },

  // ── Report ───────────────────────────────────────────────
  generateReport(projectId: ProjectId) {
    return request<IntegrationReport>(
      `/api/projects/${projectId}/report/generate`,
      { method: "POST" },
    );
  },

  getReport(projectId: ProjectId) {
    return request<IntegrationReport>(`/api/projects/${projectId}/report`);
  },
};
