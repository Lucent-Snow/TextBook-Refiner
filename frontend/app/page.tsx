"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, FlaskConical, Loader2, Plus, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useProjects } from "@/hooks/use-project";

const STATUS_LABELS: Record<string, string> = {
  pending: "待构建",
  running: "构建中",
  completed: "已完成",
  failed: "失败",
  partial: "部分完成",
};

export default function HomePage() {
  const router = useRouter();
  const { projects, loading, error, create } = useProjects();
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const demoProject = projects.find((p) => p.id === "demo");
  const userProjects = projects.filter((p) => p.id !== "demo");

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const project = await create(newName.trim());
      setNewName("");
      router.push(`/projects/${project.id}/workspace`);
    } catch {
      // error handled by hook
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="flex flex-1 flex-col items-center justify-center bg-zinc-50 dark:bg-black p-8">
      <div className="w-full max-w-2xl space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2 mb-4">
            <BookOpen className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              智汇教材
            </h1>
          </div>
          <p className="text-zinc-500 dark:text-zinc-400">
            知识整合智能体 — 从多本教材中构建知识图谱，跨书整合知识点，生成压缩精华教学方案
          </p>
        </div>

        {/* Demo Project — featured card */}
        {demoProject && (
          <Card
            className="cursor-pointer border-2 border-blue-300 bg-gradient-to-br from-blue-50 to-white hover:border-blue-400 hover:shadow-md transition-all"
            onClick={() => router.push(`/projects/${demoProject.id}/workspace`)}
          >
            <CardContent className="flex items-center justify-between py-5">
              <div className="flex items-center gap-4">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-white">
                  <Zap className="h-5 w-5" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-bold text-slate-900">
                      {demoProject.name}
                    </p>
                    <Badge className="bg-blue-600 hover:bg-blue-600 text-white text-xs">
                      演示数据
                    </Badge>
                  </div>
                  <p className="text-sm text-slate-500 mt-0.5">
                    内置 5 本医学教材，已解析完毕可直接构建知识图谱
                  </p>
                </div>
              </div>
              <Button variant="default" size="sm" className="gap-1.5">
                立即进入
                <Zap className="h-3.5 w-3.5" />
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
          </div>
        )}

        {error && (
          <p className="text-center text-sm text-red-500">{error}</p>
        )}

        {/* Create New Project */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">新建项目</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="输入项目名称"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
              <Button onClick={handleCreate} disabled={creating || !newName.trim()}>
                {creating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                创建
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* User Project List */}
        {userProjects.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-slate-800">项目列表</h2>
            {userProjects.map((project) => (
              <Card
                key={project.id}
                className="cursor-pointer hover:border-blue-300 transition-colors"
                onClick={() =>
                  router.push(`/projects/${project.id}/workspace`)
                }
              >
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-3">
                    <FlaskConical className="h-5 w-5 text-blue-500" />
                    <div>
                      <p className="font-medium text-slate-800">{project.name}</p>
                      <p className="text-sm text-zinc-500">
                        {(project.compressionRatio ?? 0) > 0
                          ? `压缩率: ${((project.compressionRatio ?? 0) * 100).toFixed(1)}%`
                          : "暂无报告"}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      project.status === "completed"
                        ? "default"
                        : project.status === "running"
                          ? "secondary"
                          : "outline"
                    }
                  >
                    {STATUS_LABELS[project.status] ?? project.status}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!loading && userProjects.length === 0 && !demoProject && !error && (
          <p className="text-center text-sm text-zinc-400 py-4">
            暂无项目，创建一个开始使用
          </p>
        )}
      </div>
    </div>
  );
}
