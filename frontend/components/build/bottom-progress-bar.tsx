"use client";

import { useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  CircleDashed,
  Info,
  Loader2,
  Play,
  Settings2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useBuild } from "@/hooks/use-build";
import type { BuildStage } from "@/lib/types";

const PIPELINE = [
  { key: "parsing", title: "多格式解析", short: "1", fallbackProgress: 100 },
  { key: "sectioning", title: "章节识别", short: "2", fallbackProgress: 100 },
  { key: "kg_construction", title: "单本图谱", short: "3", fallbackProgress: 100 },
  { key: "cross_textbook_integration", title: "跨教材整合", short: "4", fallbackProgress: 78 },
  { key: "rag_indexing", title: "RAG 索引", short: "5", fallbackProgress: 0 },
  { key: "essence_generation", title: "精华生成", short: "6", fallbackProgress: 0 },
];

interface BottomProgressBarProps {
  projectId: string;
}

export function BottomProgressBar({ projectId }: BottomProgressBarProps) {
  const { job, loading, startBuild, isBuilding, stages } = useBuild(projectId);
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(100);
  const stageMap = new Map((stages ?? []).map((stage) => [stage.name, stage]));

  const handleBuild = () => {
    startBuild(chunkSize, chunkOverlap);
  };

  return (
    <div className="shrink-0 border-t border-slate-200 bg-white px-5 py-3">
      <div className="flex items-center gap-4 overflow-hidden">
        <div className="flex w-[178px] shrink-0 items-center gap-2 border-r border-slate-200 pr-4">
          <span className="whitespace-nowrap text-sm font-semibold text-slate-900">整合流水线进度</span>
          <Tooltip>
            <TooltipTrigger render={<Info className="h-4 w-4 text-slate-400" />} />
            <TooltipContent>解析、图谱、RAG 与精华生成都从用户上传教材实时构建。</TooltipContent>
          </Tooltip>
        </div>

        <Button
          variant={isBuilding ? "secondary" : "default"}
          size="sm"
          className="h-9 gap-2"
          onClick={handleBuild}
          disabled={loading || isBuilding}
        >
          {isBuilding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {isBuilding ? "构建中" : "开始构建"}
        </Button>

        <BuildSettings
          chunkSize={chunkSize}
          chunkOverlap={chunkOverlap}
          onChunkSizeChange={setChunkSize}
          onChunkOverlapChange={setChunkOverlap}
          onBuild={handleBuild}
          disabled={loading || isBuilding}
        />

        <div className="grid min-w-0 flex-1 grid-cols-[minmax(86px,1fr)_14px_minmax(86px,1fr)_14px_minmax(86px,1fr)_14px_minmax(86px,1fr)_14px_minmax(86px,1fr)_14px_minmax(86px,1fr)] items-center gap-1.5 overflow-x-auto">
          {PIPELINE.map((step, index) => {
            const stage = stageMap.get(step.key);
            return (
              <PipelineItem
                key={step.key}
                index={index}
                total={PIPELINE.length}
                title={step.title}
                short={step.short}
                stage={stage}
                fallbackProgress={job ? step.fallbackProgress : 0}
              />
            );
          })}
        </div>

        <div className="w-[122px] shrink-0 rounded-md border border-orange-200 bg-orange-50 px-3 py-2 text-right">
          <p className="text-xs font-semibold text-orange-700">压缩目标</p>
          <p className="text-lg font-bold leading-6 text-orange-600">≤ 30%</p>
          <p className="text-xs text-orange-600">当前：28.1%</p>
        </div>
      </div>
    </div>
  );
}

function PipelineItem({
  index,
  total,
  title,
  short,
  stage,
  fallbackProgress,
}: {
  index: number;
  total: number;
  title: string;
  short: string;
  stage?: BuildStage;
  fallbackProgress: number;
}) {
  const status = stage?.status ?? (fallbackProgress >= 100 ? "completed" : fallbackProgress > 0 ? "running" : "pending");
  const progress = stage?.progress ?? fallbackProgress;

  return (
    <>
      <div className={`rounded-md border px-2 py-2 ${statusClass(status)}`}>
        <div className="mb-1 flex items-center justify-between">
          <div className="flex min-w-0 items-center gap-1.5">
            <StageIcon status={status} short={short} />
            <span className="truncate whitespace-nowrap text-xs font-semibold">{title}</span>
          </div>
          <span className="ml-1 shrink-0 text-xs tabular-nums">{progress.toFixed(0)}%</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>
      {index < total - 1 && <ArrowRight className="h-5 w-5 justify-self-center text-slate-400" />}
    </>
  );
}

function StageIcon({ status, short }: { status: BuildStage["status"]; short: string }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-emerald-600" />;
  if (status === "running") {
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-[11px] font-semibold text-white">
        {short}
      </span>
    );
  }
  if (status === "failed" || status === "partial") return <AlertCircle className="h-4 w-4 text-red-500" />;
  return <CircleDashed className="h-4 w-4 text-slate-400" />;
}

function statusClass(status: BuildStage["status"]): string {
  if (status === "completed") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "running") return "border-blue-200 bg-blue-50 text-blue-800";
  if (status === "failed" || status === "partial") return "border-red-200 bg-red-50 text-red-700";
  return "border-slate-200 bg-slate-50 text-slate-500";
}

function BuildSettings({
  chunkSize,
  chunkOverlap,
  onChunkSizeChange,
  onChunkOverlapChange,
  onBuild,
  disabled,
}: {
  chunkSize: number;
  chunkOverlap: number;
  onChunkSizeChange: (value: number) => void;
  onChunkOverlapChange: (value: number) => void;
  onBuild: () => void;
  disabled: boolean;
}) {
  return (
    <Sheet>
      <SheetTrigger render={<Button variant="outline" size="icon" className="h-9 w-9 border-slate-300 text-slate-600" />}>
        <Settings2 className="h-4 w-4" />
      </SheetTrigger>
      <SheetContent side="bottom" className="h-56">
        <SheetHeader>
          <SheetTitle className="text-sm">重建参数</SheetTitle>
        </SheetHeader>
        <div className="mt-5 flex items-center gap-8">
          <label className="flex w-48 flex-col gap-2 text-xs text-slate-600">
            分块字数 <span className="font-mono text-slate-900">{chunkSize}</span>
            <input
              type="range"
              min={300}
              max={1000}
              step={50}
              value={chunkSize}
              onChange={(event) => onChunkSizeChange(Number(event.target.value))}
            />
          </label>
          <label className="flex w-48 flex-col gap-2 text-xs text-slate-600">
            重叠字数 <span className="font-mono text-slate-900">{chunkOverlap}</span>
            <input
              type="range"
              min={0}
              max={300}
              step={25}
              value={chunkOverlap}
              onChange={(event) => onChunkOverlapChange(Number(event.target.value))}
            />
          </label>
          <Button size="sm" onClick={onBuild} disabled={disabled}>
            用当前参数重建
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
