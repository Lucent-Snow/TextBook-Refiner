"use client";

import { BookMarked, GitMerge, Hash, Layers3, X } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { NODE_TYPE_LABELS } from "@/lib/graph-styles";
import type { GraphNode } from "@/lib/types";

interface NodeDetailsProps {
  node: GraphNode;
  onClose: () => void;
}

export function NodeDetails({ node, onClose }: NodeDetailsProps) {
  const sources = node.sources ?? [];
  const confidence = Math.min(100, Math.max(18, node.frequency * 16));

  return (
    <div className="absolute bottom-28 left-[44%] z-20 w-[340px] rounded-md border border-slate-200 bg-white shadow-lg">
      <div className="flex items-start justify-between border-b border-slate-100 px-4 py-3">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2">
            <Badge variant="outline" className="rounded border-blue-200 bg-blue-50 text-blue-700">
              {NODE_TYPE_LABELS[node.type]}
            </Badge>
            {node.mergeStatus && (
              <Badge variant="outline" className="rounded border-emerald-200 bg-emerald-50 text-emerald-700">
                合并候选
              </Badge>
            )}
          </div>
          <h3 className="truncate text-base font-semibold text-slate-900">{node.label}</h3>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0 text-slate-500" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="space-y-3 px-4 py-3 text-sm">
        {node.definition && (
          <div>
            <p className="mb-1 text-xs font-medium text-slate-500">定义</p>
            <p className="line-clamp-3 leading-6 text-slate-700">{node.definition}</p>
          </div>
        )}

        <div className="grid grid-cols-3 gap-2 text-xs">
          <Metric icon={<Hash className="h-3.5 w-3.5" />} label="ID" value={node.id.slice(0, 8)} />
          <Metric icon={<Layers3 className="h-3.5 w-3.5" />} label="出现" value={`${node.frequency} 处`} />
          <Metric icon={<BookMarked className="h-3.5 w-3.5" />} label="来源" value={`${sources.length} 条`} />
        </div>

        <Separator />

        <div>
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="flex items-center gap-1 font-medium text-slate-600">
              <GitMerge className="h-3.5 w-3.5 text-blue-500" />
              置信度
            </span>
            <span className="font-mono text-slate-700">{confidence}%</span>
          </div>
          <Progress value={confidence} className="h-2" />
        </div>

        {sources.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-slate-500">证据来源</p>
            <div className="max-h-24 space-y-1 overflow-auto">
              {sources.slice(0, 4).map((source) => (
                <div key={source} className="rounded border border-slate-100 bg-slate-50 px-2 py-1 text-xs text-slate-600">
                  {source}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-2">
      <div className="mb-1 flex items-center gap-1 text-slate-400">{icon}{label}</div>
      <div className="truncate font-semibold text-slate-700">{value}</div>
    </div>
  );
}
