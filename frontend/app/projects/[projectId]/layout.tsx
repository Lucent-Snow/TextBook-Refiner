import { TopStatusBar } from "@/components/shell/top-status-bar";

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;

  return (
    <div className="flex flex-1 flex-col h-screen overflow-hidden">
      <TopStatusBar projectId={projectId} />
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
