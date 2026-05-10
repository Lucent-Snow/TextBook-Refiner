"use client";

import { use, useEffect, useState } from "react";
import { Loader2, FileText, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import type { IntegrationReport } from "@/lib/types";

export default function ReportPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  const [report, setReport] = useState<IntegrationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getReport(projectId)
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch(() => {
        // Report doesn't exist yet — not an error
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const newReport = await api.generateReport(projectId);
      setReport(newReport);
    } catch (err) {
      setError(err instanceof Error ? err.message : "报告生成失败");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col p-6 overflow-auto">
      <div className="max-w-4xl mx-auto w-full space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-6 w-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900">整合报告</h1>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleGenerate} disabled={generating}>
              {generating ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              {report ? "重新生成" : "生成报告"}
            </Button>
            {report && (
              <Button variant="outline">
                <Download className="h-4 w-4 mr-2" />
                导出
              </Button>
            )}
          </div>
        </div>

        {error && (
          <p className="text-sm text-red-500 bg-red-50 dark:bg-red-950 p-3 rounded-md">
            {error}
          </p>
        )}

        {!report && !generating && (
          <Card>
            <CardContent className="py-12 text-center text-zinc-500">
              <FileText className="h-12 w-12 mx-auto mb-4 text-zinc-300" />
              <p>暂无报告</p>
              <p className="text-sm mt-1">
                点击"生成报告"创建整合报告和压缩精华内容
              </p>
            </CardContent>
          </Card>
        )}

        {report && (
          <>
            {/* Compression Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">压缩概况</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-sm text-zinc-500">压缩率</p>
                    <p className="text-2xl font-bold">
                      {(report.compressionRatio * 100).toFixed(1)}%
                    </p>
                  </div>
                  <Separator orientation="vertical" className="h-12" />
                  <div>
                    <p className="text-sm text-zinc-500">目标</p>
                    <p className="text-2xl font-bold">30%</p>
                  </div>
                  <Separator orientation="vertical" className="h-12" />
                  <div>
                    <p className="text-sm text-zinc-500">状态</p>
                    <Badge
                      variant={
                        report.compressionRatio <= 0.3
                          ? "default"
                          : "secondary"
                      }
                    >
                      {report.compressionRatio <= 0.3 ? "已达标" : "超目标"}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Teaching Flow */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">教学流程</CardTitle>
              </CardHeader>
              <CardContent>
                {report.teachingFlow.length > 0 ? (
                  <div className="space-y-3">
                    {report.teachingFlow.map((step) => (
                      <div key={`${step.order}-${step.conceptId}`} className="rounded-md border p-3">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{step.order}</Badge>
                          <p className="font-medium">{step.conceptLabel}</p>
                        </div>
                        <p className="mt-2 text-xs text-zinc-500">
                          教材来源 {step.textbookRefs.length} 处，前置知识 {step.prerequisiteIds.length} 个
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">尚未生成教学流程</p>
                )}
              </CardContent>
            </Card>

            {/* Essence Content */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">压缩精华</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose dark:prose-invert max-w-none whitespace-pre-wrap">
                  {report.essenceContent}
                </div>
              </CardContent>
            </Card>

            {/* Decisions Summary */}
            {Object.keys(report.decisionsSummary).length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">整合决策汇总</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(report.decisionsSummary).map(([label, count]) => (
                      <div key={label} className="rounded-md border p-3">
                        <p className="text-sm text-zinc-500">{label}</p>
                        <p className="text-2xl font-bold">{String(count)}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
}
