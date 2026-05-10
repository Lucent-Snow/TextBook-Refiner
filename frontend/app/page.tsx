"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useProjects } from "@/hooks/use-project";

export default function HomePage() {
  const router = useRouter();
  const { projects, loading, error, create } = useProjects();
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

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
            <h1 className="text-3xl font-bold tracking-tight">
              TextBook Refiner
            </h1>
          </div>
          <p className="text-zinc-500 dark:text-zinc-400">
            Knowledge Integration Agent — build knowledge graphs from textbooks,
            integrate cross-textbook knowledge, and generate compressed essence.
          </p>
        </div>

        {/* Create Project */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">New Project</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="Project name (e.g., Medical Textbooks)"
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
                Create
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Project List */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
          </div>
        )}

        {error && (
          <p className="text-center text-sm text-red-500">{error}</p>
        )}

        {projects.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold">Projects</h2>
            {projects.map((project) => (
              <Card
                key={project.id}
                className="cursor-pointer hover:border-blue-300 transition-colors"
                onClick={() =>
                  router.push(`/projects/${project.id}/workspace`)
                }
              >
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-3">
                    <BookOpen className="h-5 w-5 text-blue-500" />
                    <div>
                      <p className="font-medium">{project.name}</p>
                      <p className="text-sm text-zinc-500">
                        {(project.compressionRatio ?? 0) > 0
                          ? `Compression: ${((project.compressionRatio ?? 0) * 100).toFixed(1)}%`
                          : "No report generated yet"}
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
                    {project.status}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!loading && projects.length === 0 && !error && (
          <p className="text-center text-sm text-zinc-400 py-4">
            No projects yet. Create one to get started.
          </p>
        )}
      </div>
    </div>
  );
}
