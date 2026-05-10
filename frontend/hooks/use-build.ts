"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { createBuildWs } from "@/lib/ws";
import type { BuildJob, ProjectId } from "@/lib/types";

export function useBuild(projectId: ProjectId) {
  const [job, setJob] = useState<BuildJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket subscription for live build progress
  useEffect(() => {
    const ws = createBuildWs(projectId, (updatedJob) => setJob(updatedJob));
    return () => ws.close();
  }, [projectId]);

  const startBuild = useCallback(async (chunkSize?: number, chunkOverlap?: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.startBuild(
        projectId,
        chunkSize != null || chunkOverlap != null
          ? { chunkSize: chunkSize ?? 500, chunkOverlap: chunkOverlap ?? 100 }
          : undefined,
      );
      setJob({ ...result, stages: {}, status: result.status } as unknown as BuildJob);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Build failed");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const isBuilding =
    job?.status === "running" || job?.status === "pending";

  const stages = job?.stages ? Object.values(job.stages) : [];

  return { job, loading, error, startBuild, isBuilding, stages };
}
