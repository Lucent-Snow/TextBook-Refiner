// Graph visualization style helpers for react-force-graph.

import type { NodeType, RelationType } from "./types";

// Node colors by type
const NODE_COLORS: Record<NodeType, string> = {
  textbook: "#3b82f6", // blue-500
  chapter: "#8b5cf6",  // violet-500
  concept: "#10b981",  // emerald-500
};

// Highlight color for selected/merged nodes
const HIGHLIGHT_COLOR = "#f59e0b"; // amber-500
export function getNodeColor(nodeType: NodeType, mergeStatus?: string | null): string {
  if (mergeStatus && mergeStatus.startsWith("merged_into")) return HIGHLIGHT_COLOR;
  return NODE_COLORS[nodeType] ?? "#6b7280";
}

// Node size by type
const NODE_SIZES: Record<NodeType, number> = {
  textbook: 10,
  chapter: 7,
  concept: 5,
};

export function getNodeSize(nodeType: NodeType, frequency: number): number {
  const base = NODE_SIZES[nodeType] ?? 5;
  return base + Math.min(frequency, 10);
}

// Edge colors by relation
const EDGE_COLORS: Record<RelationType, string> = {
  prerequisite: "#ef4444", // red
  parallel: "#6366f1",     // indigo
  contains: "#94a3b8",     // slate
  containment: "#94a3b8",  // slate
  application: "#22c55e",  // green
  duplicate: "#ef4444",
  complementary: "#22c55e",
  missing: "#f59e0b",
  causes: "#f97316",       // orange
  belongs_to: "#a855f7",   // purple
  manifests_as: "#ec4899", // pink
  located_in: "#14b8a6",   // teal
  related_to: "#9ca3af",   // gray
};

export function getEdgeColor(relation: RelationType): string {
  return EDGE_COLORS[relation] ?? "#9ca3af";
}

// Node labels for graph legend
export const NODE_TYPE_LABELS: Record<NodeType, string> = {
  textbook: "教材",
  chapter: "章节",
  concept: "知识点",
};

export const RELATION_LABELS: Record<RelationType, string> = {
  prerequisite: "前置依赖",
  parallel: "并列关系",
  contains: "包含关系",
  containment: "包含关系",
  application: "应用关系",
  duplicate: "重复关系",
  complementary: "互补关系",
  missing: "缺失提示",
  causes: "致因关系",
  belongs_to: "归属关系",
  manifests_as: "表现为",
  located_in: "定位于",
  related_to: "相关关系",
};

// Decision type colors
export const DECISION_COLORS = {
  duplicate: "#ef4444",
  complementary: "#22c55e",
  missing: "#f59e0b",
  conflict: "#8b5cf6",
} as const;
