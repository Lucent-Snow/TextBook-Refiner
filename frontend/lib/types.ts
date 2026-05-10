// Shared TypeScript types — mirrors backend Pydantic models.
// Backend serializes to camelCase (via CamelModel alias_generator).

export type ProjectId = string;

// ── Project ──────────────────────────────────────────────
export interface Project {
  id: ProjectId;
  name: string;
  status: BuildStatus;
  compressionTarget: number;
  originalCharCount: number;
  essenceCharCount: number;
  compressionRatio: number | null;
  createdAt: string;
  updatedAt: string;
}

export type BuildStatus = "pending" | "running" | "completed" | "failed" | "partial";

// ── Material ─────────────────────────────────────────────
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

export type FileType = "pdf" | "md" | "docx" | "xlsx";
export type ParseStatus = "pending" | "parsing" | "done" | "failed";

// ── Section ──────────────────────────────────────────────
export interface Section {
  id: string;
  materialId: string;
  textbook: string;
  chapter: string;
  order: number;
  level: number;
  pageStart: number | null;
  pageEnd: number | null;
  charCount: number;
  text: string;
}

// ── Knowledge Graph ──────────────────────────────────────
export type NodeType = "textbook" | "chapter" | "concept";

export type RelationType =
  | "contains"
  | "prerequisite"
  | "parallel"
  | "containment"
  | "application"
  | "duplicate"
  | "complementary"
  | "missing"
  | "causes"
  | "belongs_to"
  | "manifests_as"
  | "located_in"
  | "related_to";

export interface Evidence {
  materialId: string;
  textbook: string;
  chapter: string;
  pageStart: number | null;
  pageEnd: number | null;
  quote: string;
}

export interface KnowledgeNode {
  id: string;
  type: NodeType;
  label: string;
  definition: string;
  sources: string[]; // chunk_ids
  frequency: number;
  mergeStatus: string | null;
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

// ── Integration Decisions ────────────────────────────────
export type DecisionType = "duplicate" | "complementary" | "missing" | "conflict";
export type DecisionStatus = "pending" | "accepted" | "rejected" | "revised";

export interface IntegrationDecision {
  id: string;
  projectId: ProjectId;
  type: DecisionType;
  status: DecisionStatus;
  involvedNodeIds: string[];
  reason: string;
  evidence: string[]; // evidence refs
  confidence: number;
  suggestedOperation: GraphOperation | null;
  teacherFeedback: string | null;
  createdAt: string;
  updatedAt: string;
}

// ── Graph Operations ─────────────────────────────────────
export interface GraphOperation {
  id: string;
  operation: string;
  params: Record<string, unknown>;
  reason: string;
  success: boolean;
  error: string | null;
  timestamp: string;
}

// ── Build Job ────────────────────────────────────────────
export interface BuildJob {
  id: string;
  projectId: ProjectId;
  status: BuildStatus;
  stages: Record<string, BuildStage>;
  currentStage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BuildStage {
  name: string;
  status: BuildStatus;
  progress: number;
  message: string;
  error: string | null;
}

// ── Chat ─────────────────────────────────────────────────
export type MessageRole = "teacher" | "agent" | "system" | "tool_call";

export interface ToolCallData {
  name: string;
  params: Record<string, unknown>;
  result: Record<string, unknown> | null;
}

export interface ToolResultData {
  toolCallId?: string;
  name: string;
  result: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  projectId: ProjectId;
  role: MessageRole;
  content: string;
  toolCall: ToolCallData | null;
  evidence: string[];
  createdAt: string;
}

export interface ChatRequest {
  message: string;
  contextNodeIds: string[];
}

export interface AskRequest {
  question: string;
  topK: number;
}

// ── Graph Data (for react-force-graph) ───────────────────
export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
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
  x?: number;
  y?: number;
}

export interface GraphLink {
  id?: string;
  source: string | GraphNode;
  target: string | GraphNode;
  relation: RelationType;
  confidence: number;
  evidence?: Evidence[];
  createdAt?: string;
}

// ── Report ───────────────────────────────────────────────
export interface TeachingFlowStep {
  order: number;
  conceptId: string;
  conceptLabel: string;
  textbookRefs: string[];
  prerequisiteIds: string[];
}

export interface IntegrationReport {
  id: string;
  projectId: ProjectId;
  teachingFlow: TeachingFlowStep[];
  decisionsSummary: Record<string, number>;
  essenceContent: string;
  originalCharCount: number;
  essenceCharCount: number;
  compressionRatio: number;
  generatedAt: string;
}
