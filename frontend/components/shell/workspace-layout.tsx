"use client";

import { BottomProgressBar } from "@/components/build/bottom-progress-bar";
import { TeacherChatConsole } from "@/components/chat/teacher-chat-console";
import { RightIntegrationPanel } from "@/components/decisions/right-integration-panel";
import { GraphCanvas } from "@/components/graph/graph-canvas";
import { GraphToolbar } from "@/components/graph/graph-toolbar";
import { NodeDetails } from "@/components/graph/node-details";
import { LeftMaterialPanel } from "@/components/materials/left-material-panel";
import { useGraph } from "@/hooks/use-graph";

interface WorkspaceLayoutProps {
  projectId: string;
}

export function WorkspaceLayout({ projectId }: WorkspaceLayoutProps) {
  const {
    graph,
    loading,
    selectedNode,
    highlightIds,
    handleNodeClick,
    clearSelection,
  } = useGraph(projectId);

  return (
    <div className="flex h-[calc(100vh-68px)] min-h-0 flex-col bg-slate-100 text-slate-900">
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(260px,332px)_minmax(420px,1fr)_minmax(320px,374px)] gap-2 overflow-hidden p-2">
        <aside className="min-h-0 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
          <LeftMaterialPanel projectId={projectId} />
        </aside>

        <main className="relative flex min-h-0 flex-col overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
          <GraphToolbar />
          <div className="min-h-0 flex-1 bg-[radial-gradient(circle_at_center,#f8fbff_0,#ffffff_55%,#f8fafc_100%)]">
            <GraphCanvas
              data={graph}
              loading={loading}
              highlightNodeIds={highlightIds}
              onNodeClick={handleNodeClick}
            />
          </div>
          {selectedNode && <NodeDetails node={selectedNode} onClose={clearSelection} />}
        </main>

        <aside className="grid min-h-0 grid-rows-[1fr_290px] gap-2 overflow-hidden">
          <section className="min-h-0 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
            <RightIntegrationPanel projectId={projectId} />
          </section>
          <section className="min-h-0 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
            <TeacherChatConsole projectId={projectId} />
          </section>
        </aside>
      </div>

      <BottomProgressBar projectId={projectId} />
    </div>
  );
}
