"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { createGraphWs } from "@/lib/ws";
import type { GraphData, GraphLink, GraphNode, ProjectId } from "@/lib/types";

const EMPTY_GRAPH: GraphData = { nodes: [], links: [] };

export function useGraph(projectId: ProjectId) {
  const [graph, setGraph] = useState<GraphData>(EMPTY_GRAPH);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightIds, setHighlightIds] = useState<string[]>([]);

  // Initial fetch
  useEffect(() => {
    let cancelled = false;
    api
      .getGraph(projectId)
      .then((data) => {
        if (!cancelled) setGraph(data);
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

  // WebSocket subscription for live updates
  useEffect(() => {
    const ws = createGraphWs(projectId, (newGraph) => setGraph(newGraph));
    return () => ws.close();
  }, [projectId]);

  const handleNodeClick = useCallback(
    (node: GraphNode) => {
      setSelectedNode(node);
      // Highlight connected nodes
      const connected = graph.links
        .filter(
          (l) =>
            getEndpointId(l.source) === node.id ||
            getEndpointId(l.target) === node.id,
        )
        .flatMap((l) => [getEndpointId(l.source), getEndpointId(l.target)]);
      setHighlightIds([...new Set([node.id, ...connected])]);
    },
    [graph.links],
  );

  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setHighlightIds([]);
  }, []);

  return {
    graph,
    loading,
    error,
    selectedNode,
    highlightIds,
    handleNodeClick,
    clearSelection,
  };
}

function getEndpointId(endpoint: GraphLink["source"]): string {
  return typeof endpoint === "string" ? endpoint : endpoint.id;
}
