"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Material, ProjectId } from "@/lib/types";

export function useMaterials(projectId: ProjectId) {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listMaterials(projectId)
      .then((data) => {
        if (!cancelled) setMaterials(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const upload = useCallback(
    async (file: File) => {
      const material = await api.uploadMaterial(projectId, file);
      setMaterials((prev) => [...prev, material]);
      return material;
    },
    [projectId],
  );

  return { materials, loading, error, upload };
}
