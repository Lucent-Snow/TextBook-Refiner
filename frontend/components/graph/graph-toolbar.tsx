"use client";

import {
  Filter,
  GitBranch,
  Grid3X3,
  ListTree,
  Network,
  Route,
  SlidersHorizontal,
} from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { NODE_TYPE_LABELS, RELATION_LABELS } from "@/lib/graph-styles";

const VIEW_TABS = [
  { key: "graph", label: "知识图谱", icon: Network, active: true },
  { key: "chapter", label: "章节视图", icon: ListTree, active: false },
  { key: "matrix", label: "矩阵视图", icon: Grid3X3, active: false },
  { key: "conflict", label: "冲突视图", icon: GitBranch, active: false },
];

export function GraphToolbar() {
  return (
    <div className="shrink-0 border-b border-slate-200 bg-white">
      <div className="flex h-12 items-center justify-between gap-3 overflow-hidden px-4">
        <div className="flex min-w-0 items-center gap-5">
          <h2 className="shrink-0 text-base font-semibold text-slate-900">整合工作台</h2>
          <div className="flex shrink-0 rounded-md border border-slate-200 bg-slate-50 p-0.5">
            {VIEW_TABS.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  className={`flex h-8 items-center gap-1.5 whitespace-nowrap rounded px-3 text-sm ${
                    tab.active
                      ? "bg-white font-semibold text-blue-700 shadow-sm"
                      : "text-slate-500 hover:text-slate-800"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span className="max-[1300px]:hidden">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <Tooltip>
            <TooltipTrigger render={<Button variant="outline" size="sm" className="h-8 gap-2 border-slate-300 text-slate-700" />}>
              <SlidersHorizontal className="h-4 w-4" />
              显示选项
            </TooltipTrigger>
            <TooltipContent>筛选教材、关系类型和置信度阈值</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger render={<Button variant="outline" size="icon" className="h-8 w-8 border-slate-300 text-slate-600" />}>
              <Filter className="h-4 w-4" />
            </TooltipTrigger>
            <TooltipContent>过滤低置信度关系</TooltipContent>
          </Tooltip>
        </div>
      </div>

      <div className="flex h-9 items-center gap-3 overflow-x-auto px-4 text-xs text-slate-500">
        <span className="shrink-0 font-medium text-slate-700">图例：</span>
        {Object.entries(NODE_TYPE_LABELS).map(([key, label]) => (
          <div key={key} className="flex shrink-0 items-center gap-1 whitespace-nowrap">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{
                backgroundColor:
                  key === "textbook"
                    ? "#3b82f6"
                    : key === "chapter"
                      ? "#8b5cf6"
                      : "#10b981",
              }}
            />
            {label}
          </div>
        ))}
        <Separator orientation="vertical" className="h-4" />
        <RelationLegend color="#ef4444" label={RELATION_LABELS.prerequisite} dashed />
        <RelationLegend color="#6366f1" label={RELATION_LABELS.parallel} />
        <RelationLegend color="#22c55e" label={RELATION_LABELS.contains} />
        <RelationLegend color="#f97316" label={RELATION_LABELS.application} />
        <RelationLegend color="#ef4444" label="选中路径" dashed icon={<Route className="h-3 w-3" />} />
      </div>
    </div>
  );
}

function RelationLegend({
  color,
  label,
  dashed,
  icon,
}: {
  color: string;
  label: string;
  dashed?: boolean;
  icon?: ReactNode;
}) {
  return (
    <div className="flex shrink-0 items-center gap-1 whitespace-nowrap">
      {icon}
      <span
        className={`inline-block h-0.5 w-6 ${dashed ? "border-t-2 border-dashed bg-transparent" : ""}`}
        style={dashed ? { borderColor: color } : { backgroundColor: color }}
      />
      {label}
    </div>
  );
}
