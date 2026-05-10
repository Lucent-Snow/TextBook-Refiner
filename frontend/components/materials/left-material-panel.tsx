"use client";

import { useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  File,
  FileSpreadsheet,
  FileText,
  Plus,
  Search,
  Settings2,
  Upload,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useMaterials } from "@/hooks/use-materials";
import type { FileType, Material, ParseStatus } from "@/lib/types";

const FILE_ICONS: Record<FileType, typeof FileText> = {
  pdf: FileText,
  md: FileText,
  docx: File,
  xlsx: FileSpreadsheet,
};

const FILE_LABELS: Record<FileType, string> = {
  pdf: "PDF",
  md: "MD",
  docx: "Word",
  xlsx: "Excel",
};

const FILE_STYLES: Record<FileType, string> = {
  pdf: "border-red-100 bg-red-50 text-red-600",
  md: "border-slate-200 bg-slate-50 text-slate-600",
  docx: "border-blue-100 bg-blue-50 text-blue-600",
  xlsx: "border-emerald-100 bg-emerald-50 text-emerald-600",
};

const STATUS_LABELS: Record<ParseStatus, string> = {
  pending: "待解析",
  parsing: "解析中",
  done: "解析完成",
  failed: "解析失败",
};

interface LeftMaterialPanelProps {
  projectId: string;
}

export function LeftMaterialPanel({ projectId }: LeftMaterialPanelProps) {
  const { materials, loading, upload } = useMaterials(projectId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"library" | "parsed">("library");
  const filtered = useMemo(
    () =>
      materials.filter((material) => {
        const matchesQuery = material.filename
          .toLowerCase()
          .includes(query.trim().toLowerCase());
        const matchesTab = tab === "library" || material.parseStatus === "done";
        return matchesQuery && matchesTab;
      }),
    [materials, query, tab],
  );

  const counts = useMemo(() => {
    const result: Record<FileType | "all", number> = { all: materials.length, pdf: 0, md: 0, docx: 0, xlsx: 0 };
    for (const material of materials) result[material.fileType] += 1;
    return result;
  }, [materials]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;
    for (const file of Array.from(files)) await upload(file);
    event.target.value = "";
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-10 items-end border-b border-slate-200 px-3">
        <button
          className={`h-10 border-b-2 px-1 text-sm font-semibold ${tab === "library" ? "border-blue-600 text-blue-700" : "border-transparent text-slate-500"}`}
          onClick={() => setTab("library")}
        >
          素材库
        </button>
        <button
          className={`ml-7 h-10 border-b-2 px-1 text-sm font-medium ${tab === "parsed" ? "border-blue-600 text-blue-700" : "border-transparent text-slate-500"}`}
          onClick={() => setTab("parsed")}
        >
          已解析
        </button>
      </div>

      <div className="space-y-3 border-b border-slate-200 p-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">多格式教材库</h2>
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7 border-slate-300"
            onClick={() => inputRef.current?.click()}
          >
            <Plus className="h-4 w-4" />
          </Button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.md,.markdown,.doc,.docx,.xls,.xlsx"
            className="hidden"
            onChange={handleUpload}
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          <Badge variant="outline" className="h-6 rounded-md border-blue-200 bg-blue-50 px-2 text-blue-700">
            全部 {counts.all}
          </Badge>
          {(["pdf", "md", "docx", "xlsx"] as FileType[]).map((type) => (
            <Badge key={type} variant="outline" className={`h-6 rounded-md px-2 ${FILE_STYLES[type]}`}>
              {FILE_LABELS[type]} {counts[type]}
            </Badge>
          ))}
        </div>

        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索教材或章节"
            className="h-9 rounded-md border-slate-200 pl-8 text-sm"
          />
        </div>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        {loading && (
          <div className="p-4 text-sm text-slate-400">正在读取教材列表...</div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="flex h-48 flex-col items-center justify-center px-6 text-center text-sm text-slate-400">
            <Upload className="mb-3 h-8 w-8 text-slate-300" />
            <p>{tab === "parsed" ? "暂无已解析教材" : "尚未加载教材"}</p>
            <p className="mt-1 text-xs">支持 PDF、Markdown、Word、Excel</p>
          </div>
        )}

        <div className="space-y-1 p-2">
          {filtered.map((material, index) => (
            <MaterialTreeItem key={material.id} material={material} index={index} />
          ))}
        </div>
      </ScrollArea>

      <Separator />
      <div className="flex items-center justify-between p-3">
        <Button variant="outline" className="h-8 w-full justify-center gap-2 border-slate-300 text-sm text-slate-700">
          <Settings2 className="h-4 w-4" />
          管理教材与解析
        </Button>
      </div>
    </div>
  );
}

interface MaterialTreeItemProps {
  material: Material;
  index: number;
}

function MaterialTreeItem({ material, index }: MaterialTreeItemProps) {
  const Icon = FILE_ICONS[material.fileType] ?? File;
  const pages = Math.max(12, Math.round(material.charCount / 900));
  const chapters = buildChapterRows(material, index);

  return (
    <div className="rounded-md border border-transparent hover:border-slate-200 hover:bg-slate-50">
      <div className="flex items-center gap-2 px-2 py-2">
        <ChevronRight className="h-4 w-4 text-slate-400" />
        <span className={`flex h-5 w-5 items-center justify-center rounded ${FILE_STYLES[material.fileType]}`}>
          <Icon className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-800">{material.filename.replace(/\.[^.]+$/, "")}</p>
        </div>
        <StatusPill status={material.parseStatus} />
      </div>

      <div className="ml-9 space-y-0.5 border-l border-slate-100 pb-1">
        {chapters.map((chapter, chapterIndex) => (
          <div
            key={`${material.id}-${chapter.title}`}
            className={`ml-2 grid grid-cols-[1fr_34px] items-center rounded px-2 py-1.5 text-xs ${chapterIndex === 2 ? "bg-blue-50 text-blue-700 ring-1 ring-blue-200" : "text-slate-600"}`}
          >
            <span className="truncate">{chapter.title}</span>
            <span className="text-right tabular-nums text-slate-500">{Math.max(8, pages + chapterIndex * 16)}</span>
          </div>
        ))}
        <div className="ml-2 px-2 py-0.5 text-xs text-slate-400">...</div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: ParseStatus }) {
  if (status === "done") {
    return (
      <span className="flex items-center gap-1 text-xs text-emerald-600">
        <CheckCircle2 className="h-3.5 w-3.5" />
        {STATUS_LABELS[status]}
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex items-center gap-1 text-xs text-red-500">
        <AlertCircle className="h-3.5 w-3.5" />
        {STATUS_LABELS[status]}
      </span>
    );
  }
  return <span className="text-xs text-slate-400">{STATUS_LABELS[status]}</span>;
}

function buildChapterRows(material: Material, index: number) {
  const stems = [
    ["第1章 绪论", "第2章 细胞的基本功能", "第3章 血液"],
    ["第一章 疾病概论", "第二章 细胞和组织的适应、损伤与修复", "第三章 局部血液循环障碍"],
    ["第一章 绪论", "第二章 疾病概论", "第三章 缺氧"],
    ["第一章 微生物与医学微生物学", "第二章 细菌的形态与结构", "第三章 细菌的生理"],
  ];
  if (material.fileType === "xlsx") {
    return [
      { title: "Sheet 1 知识点清单" },
      { title: "Sheet 2 章节映射" },
      { title: "Sheet 3 整合标注" },
    ];
  }
  if (material.fileType === "md") {
    return [{ title: "项目说明" }, { title: "教学目标" }, { title: "整合策略" }];
  }
  return stems[index % stems.length].map((title) => ({ title }));
}
