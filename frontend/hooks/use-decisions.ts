"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { IntegrationDecision, ProjectId } from "@/lib/types";

export function useDecisions(projectId: ProjectId) {
  const [decisions, setDecisions] = useState<IntegrationDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .listDecisions(projectId)
      .then((data) => {
        if (!cancelled) setDecisions(data);
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

  const accept = useCallback(
    async (decisionId: string) => {
      setDecisions((prev) =>
        prev.map((d) =>
          d.id === decisionId ? { ...d, status: "accepted" as const } : d,
        ),
      );
      try {
        await api.acceptDecision(projectId, decisionId);
      } catch {
        setDecisions((prev) =>
          prev.map((d) =>
            d.id === decisionId ? { ...d, status: "pending" as const } : d,
          ),
        );
      }
    },
    [projectId],
  );

  const reject = useCallback(
    async (decisionId: string) => {
      setDecisions((prev) =>
        prev.map((d) =>
          d.id === decisionId ? { ...d, status: "rejected" as const } : d,
        ),
      );
      try {
        await api.rejectDecision(projectId, decisionId, "Rejected by teacher");
      } catch {
        setDecisions((prev) =>
          prev.map((d) =>
            d.id === decisionId ? { ...d, status: "pending" as const } : d,
          ),
        );
      }
    },
    [projectId],
  );

  return { decisions, loading, error, accept, reject };
}
