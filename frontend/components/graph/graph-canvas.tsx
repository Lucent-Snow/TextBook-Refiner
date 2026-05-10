"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ComponentType, MutableRefObject, ReactNode } from "react";
import type {
  ForceGraphMethods,
  ForceGraphProps,
  LinkObject,
  NodeObject,
} from "react-force-graph-2d";
import {
  Crosshair,
  Focus,
  Hand,
  Loader2,
  Maximize2,
  Network,
  RefreshCw,
  ScanSearch,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getEdgeColor, getNodeColor, getNodeSize } from "@/lib/graph-styles";
import type { GraphData, GraphLink, GraphNode } from "@/lib/types";

type GraphRef = MutableRefObject<ForceGraphMethods<GraphNode, GraphLink> | undefined>;
type ForceGraphComponent = ComponentType<ForceGraphProps<GraphNode, GraphLink> & { ref?: GraphRef }>;
type ForceNode = NodeObject<GraphNode>;
type ForceLink = LinkObject<GraphNode, GraphLink>;

interface GraphCanvasProps {
  data: GraphData;
  loading: boolean;
  highlightNodeIds?: string[];
  onNodeClick?: (node: GraphNode) => void;
}

export function GraphCanvas({
  data,
  loading,
  highlightNodeIds,
  onNodeClick,
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(undefined);
  const [ForceGraph, setForceGraph] = useState<ForceGraphComponent | null>(null);
  const [size, setSize] = useState({ width: 960, height: 640 });

  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setForceGraph(() => mod.default as unknown as ForceGraphComponent);
    });
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const updateSize = () => {
      const rect = element.getBoundingClientRect();
      setSize({
        width: Math.max(320, Math.floor(rect.width)),
        height: Math.max(320, Math.floor(rect.height)),
      });
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const handleNodeClick = useCallback(
    (node: ForceNode) => {
      onNodeClick?.({
        id: String(node.id ?? ""),
        type: node.type,
        label: node.label,
        definition: node.definition,
        frequency: node.frequency,
        mergeStatus: node.mergeStatus,
        sources: node.sources,
        teacherOverrides: node.teacherOverrides,
        createdAt: node.createdAt,
        x: node.x,
        y: node.y,
      });
    },
    [onNodeClick],
  );

  const nodeCanvasObject = useCallback(
    (node: ForceNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const label = node.label ?? "";
      const nodeType = node.type ?? "concept";
      const isHighlighted = highlightNodeIds?.includes(String(node.id ?? ""));
      const size = getNodeSize(nodeType, node.frequency ?? 1);
      const color = getNodeColor(nodeType, node.mergeStatus);
      const labelSize = Math.max(9, 12 / globalScale);

      ctx.beginPath();
      ctx.arc(x, y, size + 5, 0, 2 * Math.PI);
      ctx.fillStyle = `${color}1f`;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
      ctx.lineWidth = isHighlighted ? 3 : 1.6;
      ctx.strokeStyle = isHighlighted ? "#ef4444" : color;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(x, y, Math.max(2.5, size * 0.34), 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#0f172a";
      ctx.font = `600 ${labelSize}px sans-serif`;
      ctx.fillText(label, x, y + size + labelSize + 4);
    },
    [highlightNodeIds],
  );

  const nodePointerAreaPaint = useCallback(
    (node: ForceNode, color: string, ctx: CanvasRenderingContext2D) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const size = getNodeSize(node.type ?? "concept", node.frequency ?? 1) + 9;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fill();
    },
    [],
  );

  const fitToView = useCallback(() => {
    graphRef.current?.zoomToFit(360, 80);
  }, []);

  const zoomBy = useCallback((delta: number) => {
    const graph = graphRef.current;
    if (!graph) return;
    graph.zoom(Math.max(0.3, Math.min(4, graph.zoom() + delta)), 180);
  }, []);

  const reheat = useCallback(() => {
    graphRef.current?.d3ReheatSimulation();
  }, []);

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden" aria-label="教材知识图谱画布">
      <CanvasState loading={loading} empty={!loading && data.nodes.length === 0} graphReady={Boolean(ForceGraph)} />

      {!loading && data.nodes.length > 0 && ForceGraph && (
        <ForceGraph
          ref={graphRef}
          graphData={data as unknown as ForceGraphProps<GraphNode, GraphLink>["graphData"]}
          width={size.width}
          height={size.height}
          backgroundColor="rgba(255,255,255,0)"
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={nodePointerAreaPaint}
          nodeLabel={(node: ForceNode) => `${node.label ?? "知识点"} | ${node.type ?? "concept"}`}
          onNodeClick={handleNodeClick}
          linkColor={(link: ForceLink) => getEdgeColor(link.relation ?? "related_to")}
          linkWidth={(link: ForceLink) => Math.max(1, (link.confidence ?? 0.5) * 2)}
          linkLineDash={(link: ForceLink) =>
            link.relation === "prerequisite" || link.relation === "duplicate" ? [4, 4] : null
          }
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          cooldownTicks={120}
          d3VelocityDecay={0.28}
          minZoom={0.3}
          maxZoom={4}
        />
      )}

      <div className="absolute left-3 top-1/2 z-10 flex -translate-y-1/2 flex-col gap-1 rounded-md border border-slate-200 bg-white/95 p-1 shadow-sm">
        <IconTool label="拖拽平移">
          <Hand className="h-4 w-4" />
        </IconTool>
        <IconTool label="框选知识点">
          <ScanSearch className="h-4 w-4" />
        </IconTool>
        <IconTool label="关系聚焦">
          <Network className="h-4 w-4" />
        </IconTool>
        <IconTool label="定位选中节点">
          <Crosshair className="h-4 w-4" />
        </IconTool>
      </div>

      <div className="absolute bottom-4 left-4 z-10 h-[86px] w-[124px] rounded-md border-2 border-blue-500 bg-white p-2 shadow-sm">
        <div className="relative h-full w-full overflow-hidden rounded bg-slate-50">
          <span className="absolute left-4 top-5 h-4 w-4 rounded-full bg-blue-200" />
          <span className="absolute left-12 top-8 h-5 w-5 rounded-full bg-emerald-200" />
          <span className="absolute right-5 top-3 h-4 w-4 rounded-full bg-violet-200" />
          <span className="absolute bottom-3 left-8 h-3 w-3 rounded-full bg-orange-200" />
          <span className="absolute inset-x-4 top-10 h-px rotate-12 bg-slate-300" />
          <span className="absolute left-10 right-5 top-8 h-px -rotate-12 bg-slate-300" />
        </div>
      </div>

      <div className="absolute bottom-5 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 rounded-md border border-slate-200 bg-white/95 px-2 py-1.5 shadow-sm">
        <BottomTool label="缩小" onClick={() => zoomBy(-0.2)}>
          <ZoomOut className="h-4 w-4" />
        </BottomTool>
        <span className="min-w-12 text-center text-xs font-medium text-slate-600">100%</span>
        <BottomTool label="放大" onClick={() => zoomBy(0.2)}>
          <ZoomIn className="h-4 w-4" />
        </BottomTool>
        <span className="h-5 w-px bg-slate-200" />
        <BottomTool label="聚焦选中" onClick={fitToView}>
          <Focus className="h-4 w-4" />
        </BottomTool>
        <BottomTool label="重新布局" onClick={reheat}>
          <RefreshCw className="h-4 w-4" />
        </BottomTool>
        <BottomTool label="适配全图" onClick={fitToView}>
          <Maximize2 className="h-4 w-4" />
        </BottomTool>
      </div>
    </div>
  );
}

function CanvasState({
  loading,
  empty,
  graphReady,
}: {
  loading: boolean;
  empty: boolean;
  graphReady: boolean;
}) {
  if (loading || !graphReady) {
    return (
      <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/70">
        <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-500 shadow-sm">
          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
          正在加载动态图谱引擎
        </div>
      </div>
    );
  }
  if (!empty) return null;
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center">
      <div className="w-[360px] rounded-md border border-dashed border-slate-300 bg-white/90 p-5 text-center shadow-sm">
        <Network className="mx-auto mb-3 h-9 w-9 text-slate-300" />
        <p className="text-base font-semibold text-slate-800">等待构建知识图谱</p>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          上传教材后启动流水线，系统会从章节结构和知识点关系两层动态生成图谱。
        </p>
      </div>
    </div>
  );
}

function IconTool({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Tooltip>
      <TooltipTrigger render={<Button variant="ghost" size="icon" className="h-8 w-8 text-slate-600" />}>
        {children}
      </TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  );
}

function BottomTool({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger
        render={<Button variant="ghost" size="icon" className="h-7 w-7 text-slate-600" />}
        onClick={onClick}
      >
        {children}
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
