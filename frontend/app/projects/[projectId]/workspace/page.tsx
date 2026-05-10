"use client";

import { use } from "react";
import { WorkspaceLayout } from "@/components/shell/workspace-layout";

export default function WorkspacePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = use(params);
  return <WorkspaceLayout projectId={projectId} />;
}
