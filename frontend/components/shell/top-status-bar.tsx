"use client";

import Link from "next/link";
import {
  Bell,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Download,
  HelpCircle,
  Layers3,
  UserRound,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useBuild } from "@/hooks/use-build";
import { useMaterials } from "@/hooks/use-materials";
import { useProject } from "@/hooks/use-project";
import type { BuildStatus } from "@/lib/types";

interface TopStatusBarProps {
  projectId: string;
}

const STATUS_LABELS: Record<BuildStatus, string> = {
  pending: "待构建",
  running: "构建中",
  completed: "已完成",
  failed: "失败",
  partial: "部分完成",
};

export function TopStatusBar({ projectId }: TopStatusBarProps) {
  const { project } = useProject(projectId);
  const { materials } = useMaterials(projectId);
  const { job } = useBuild(projectId);
  const status = job?.status ?? project?.status ?? "pending";
  const compressionRatio = project?.compressionRatio ?? 0.281;
  const target = project?.compressionTarget ?? 0.3;

  return (
    <header className="flex h-[68px] shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5 shadow-[0_1px_10px_rgba(15,23,42,0.04)]">
      <div className="flex min-w-0 items-center gap-5">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-blue-50 text-blue-600 ring-1 ring-blue-100">
            <BookOpen className="h-5 w-5" />
          </span>
          <span className="whitespace-nowrap text-xl font-semibold tracking-normal text-slate-900">
            智汇教材
          </span>
        </Link>
        <Separator orientation="vertical" className="h-8" />
        <button className="flex min-w-0 items-center gap-2 rounded-md px-2 py-1 text-sm font-semibold text-slate-800 hover:bg-slate-50">
          <span className="truncate">{project?.name ?? "医学教材整合项目"}</span>
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </button>
      </div>

      <div className="flex items-center gap-3">
        <Badge className="h-8 gap-2 rounded-md border border-blue-100 bg-blue-50 px-3 text-sm font-semibold text-blue-700 hover:bg-blue-50">
          <Layers3 className="h-3.5 w-3.5" />
          {materials.length || 7} 本教材
        </Badge>
        <Badge className="h-8 gap-2 rounded-md border border-emerald-100 bg-emerald-50 px-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-50">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          {STATUS_LABELS[status]}
        </Badge>
        <Badge className="h-8 rounded-md border border-orange-100 bg-orange-50 px-3 text-sm font-semibold text-orange-700 hover:bg-orange-50">
          压缩比 {(compressionRatio * 100).toFixed(1)}%
        </Badge>
        <Badge className="h-8 rounded-md border border-slate-200 bg-white px-3 text-sm font-medium text-slate-600 hover:bg-white">
          目标 ≤{(target * 100).toFixed(0)}%
        </Badge>
      </div>

      <div className="flex items-center gap-3">
        <Link href={`/projects/${projectId}/report`}>
          <Button variant="outline" size="sm" className="h-8 gap-2 border-slate-300 text-slate-700">
            <Download className="h-4 w-4" />
            导出整合报告
          </Button>
        </Link>
        <button className="relative flex h-8 w-8 items-center justify-center rounded-full text-slate-600 hover:bg-slate-100">
          <Bell className="h-4 w-4" />
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            3
          </span>
        </button>
        <button className="flex h-8 w-8 items-center justify-center rounded-full text-slate-600 hover:bg-slate-100">
          <HelpCircle className="h-4 w-4" />
        </button>
        <button className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-slate-50">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-700">
            <UserRound className="h-4 w-4" />
          </span>
          <span className="text-sm font-medium text-slate-700">张老师</span>
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
        </button>
      </div>
    </header>
  );
}
