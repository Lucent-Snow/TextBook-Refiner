"use client";

import { useMemo, useState } from "react";
import {
  AlertTriangle,
  Check,
  Filter,
  GitMerge,
  HelpCircle,
  Loader2,
  MessageSquare,
  Plus,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useDecisions } from "@/hooks/use-decisions";
import { DECISION_COLORS } from "@/lib/graph-styles";
import type { DecisionStatus, DecisionType, IntegrationDecision } from "@/lib/types";

const DECISION_ICONS: Record<DecisionType, typeof GitMerge> = {
  duplicate: GitMerge,
  complementary: Plus,
  missing: AlertTriangle,
  conflict: HelpCircle,
};

const DECISION_LABELS: Record<DecisionType, string> = {
  duplicate: "重复知识点",
  complementary: "互补知识点",
  missing: "缺失知识点",
  conflict: "冲突待确认",
};

const STATUS_LABELS: Record<DecisionStatus, string> = {
  pending: "待处理",
  accepted: "已接受",
  rejected: "已拒绝",
  revised: "已修订",
};

type DecisionFilter = "all" | "pending" | "resolved";

interface RightIntegrationPanelProps {
  projectId: string;
}

export function RightIntegrationPanel({ projectId }: RightIntegrationPanelProps) {
  const { decisions, loading, accept, reject } = useDecisions(projectId);
  const [filter, setFilter] = useState<DecisionFilter>("all");

  const pendingCount = decisions.filter((d) => d.status === "pending").length;
  const resolvedCount = decisions.length - pendingCount;
  const visible = useMemo(
    () =>
      decisions.filter((decision) => {
        if (filter === "pending") return decision.status === "pending";
        if (filter === "resolved") return decision.status !== "pending";
        return true;
      }),
    [decisions, filter],
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-12 items-center justify-between border-b border-slate-200 px-3">
        <h3 className="text-sm font-semibold text-slate-900">整合决策队列 ({decisions.length})</h3>
        <Tooltip>
          <TooltipTrigger render={<Button variant="outline" size="icon" className="h-8 w-8 border-slate-300 text-slate-600" />}>
            <Filter className="h-4 w-4" />
          </TooltipTrigger>
          <TooltipContent>按类型、状态和置信度过滤</TooltipContent>
        </Tooltip>
      </div>

      <div className="flex gap-2 border-b border-slate-100 px-3 py-2">
        <FilterTab active={filter === "all"} label="全部" count={decisions.length} onClick={() => setFilter("all")} />
        <FilterTab active={filter === "pending"} label="待处理" count={pendingCount} onClick={() => setFilter("pending")} />
        <FilterTab active={filter === "resolved"} label="已处理" count={resolvedCount} onClick={() => setFilter("resolved")} />
      </div>

      <ScrollArea className="min-h-0 flex-1">
        {loading && (
          <div className="flex items-center justify-center py-10 text-sm text-slate-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin text-blue-500" />
            正在读取跨教材整合建议
          </div>
        )}

        {!loading && visible.length === 0 && (
          <div className="flex h-48 flex-col items-center justify-center px-5 text-center text-sm text-slate-400">
            <GitMerge className="mb-2 h-8 w-8 text-slate-300" />
            <p>暂无整合建议</p>
            <p className="mt-1 text-xs">跨教材分析完成后会生成重复、互补、缺失和冲突项。</p>
          </div>
        )}

        <div className="space-y-2 p-3">
          {visible.map((decision) => (
            <DecisionCard
              key={decision.id}
              decision={decision}
              onAccept={() => accept(decision.id)}
              onReject={() => reject(decision.id)}
            />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

function FilterTab({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean;
  label: string;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      className={`h-8 rounded-md border px-3 text-xs ${
        active
          ? "border-blue-200 bg-blue-50 font-semibold text-blue-700"
          : "border-slate-200 bg-white text-slate-500 hover:text-slate-800"
      }`}
      onClick={onClick}
    >
      {label} <span className="ml-1 tabular-nums">{count}</span>
    </button>
  );
}

function DecisionCard({
  decision,
  onAccept,
  onReject,
}: {
  decision: IntegrationDecision;
  onAccept: () => void;
  onReject: () => void;
}) {
  const Icon = DECISION_ICONS[decision.type] ?? HelpCircle;
  const isPending = decision.status === "pending";
  const color = DECISION_COLORS[decision.type];
  const confidence = Math.round(decision.confidence * 100);
  const operationName = getOperationName(decision.suggestedOperation);

  return (
    <Card className={`overflow-hidden rounded-md border-slate-200 shadow-none transition-opacity ${!isPending ? "opacity-70" : ""}`}>
      <CardContent className="space-y-3 p-3" style={{ borderLeft: `3px solid ${color}` }}>
        <div className="flex items-start gap-2">
          <span className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full" style={{ backgroundColor: `${color}18`, color }}>
            <Icon className="h-3.5 w-3.5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-semibold text-slate-900">{DECISION_LABELS[decision.type]}</p>
              <Badge variant="outline" className="ml-auto rounded text-[10px] text-slate-500">
                {STATUS_LABELS[decision.status]}
              </Badge>
            </div>
            <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
              <span>节点 {decision.involvedNodeIds.length} 个</span>
              <span className="font-medium" style={{ color }}>
                {confidence >= 80 ? "高置信度" : confidence >= 55 ? "中置信度" : "低置信度"} {confidence / 100}
              </span>
            </div>
          </div>
        </div>

        <div>
          <p className="mb-1 text-[11px] font-medium text-slate-500">理由</p>
          <p className="line-clamp-2 text-xs leading-5 text-slate-700">{decision.reason || "等待模型给出整合理由。"}</p>
        </div>

        <div className="rounded-md border border-slate-100 bg-slate-50 px-2 py-1.5 text-[11px] text-slate-500">
          <div className="flex items-center justify-between">
            <span>建议操作：{operationName}</span>
            <span>证据：{decision.evidence.length} 处</span>
          </div>
          <Progress value={confidence} className="mt-1.5 h-1.5" />
        </div>

        {isPending ? (
          <div className="grid grid-cols-3 gap-2 pt-1">
            <Button variant="outline" size="sm" className="h-8 gap-1 border-emerald-200 text-emerald-700 hover:bg-emerald-50" onClick={onAccept}>
              <Check className="h-3.5 w-3.5" />
              接受
            </Button>
            <Button variant="outline" size="sm" className="h-8 gap-1 border-red-200 text-red-600 hover:bg-red-50" onClick={onReject}>
              <X className="h-3.5 w-3.5" />
              拒绝
            </Button>
            <Button variant="outline" size="sm" className="h-8 gap-1 border-blue-200 text-blue-700 hover:bg-blue-50">
              <MessageSquare className="h-3.5 w-3.5" />
              追问
            </Button>
          </div>
        ) : (
          <Badge variant="outline" className="rounded border-slate-200 bg-slate-50 text-xs text-slate-500">
            教师已处理
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}

function getOperationName(operation: IntegrationDecision["suggestedOperation"]): string {
  if (!operation) return "等待教师确认";
  const raw = String(operation.operation ?? operation.params?.operation ?? "graph_operation");
  const labels: Record<string, string> = {
    merge_nodes: "合并节点",
    merge: "合并节点",
    split_node: "拆分节点",
    add_edge: "新增关系",
    remove_edge: "移除关系",
    update_definition: "更新定义",
    rebuild_scope: "按范围重建",
  };
  return labels[raw] ?? raw;
}
