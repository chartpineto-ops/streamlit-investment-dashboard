import { notFound } from "next/navigation";

import {
  AgentStudioWorkspace,
  DatasetsWorkspace,
  EvidenceWorkspace,
  InsightsWorkspace,
  MonitoringWorkspace,
  ProjectsWorkspace,
  ReportsWorkspace,
  SourcesWorkspace,
} from "@/components/intelligence-workspaces";
import {
  getAgentStudioWorkspace,
  getDatasetsWorkspace,
  getEvidenceWorkspace,
  getInsightsWorkspace,
  getMonitoringWorkspace,
  getProjectsWorkspace,
  getReportsWorkspace,
  getSourcesWorkspace,
} from "@/server/services/intelligence";

type WorkspacePageProps = {
  params: Promise<{
    section: string;
  }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function stringValue(value: string | string[] | undefined) {
  return typeof value === "string" ? value : undefined;
}

export default async function WorkspacePage({
  params,
  searchParams,
}: WorkspacePageProps) {
  const [{ section }, query] = await Promise.all([params, searchParams]);
  const missionId = stringValue(query.mission);
  const notice = stringValue(query.notice);

  if (section === "sources") {
    return (
      <SourcesWorkspace
        data={await getSourcesWorkspace({
          missionId,
          query: stringValue(query.q),
        })}
        error={stringValue(query.error)}
        missionId={missionId}
        notice={notice}
        query={stringValue(query.q)}
      />
    );
  }

  if (section === "evidence") {
    return (
      <EvidenceWorkspace
        data={await getEvidenceWorkspace({
          missionId,
          query: stringValue(query.q),
          selectedId: stringValue(query.selected),
          status: stringValue(query.status),
        })}
        missionId={missionId}
        query={stringValue(query.q)}
        status={stringValue(query.status)}
      />
    );
  }

  if (section === "insights") {
    return (
      <InsightsWorkspace
        category={stringValue(query.category)}
        data={await getInsightsWorkspace({
          category: stringValue(query.category),
          missionId,
          selectedId: stringValue(query.selected),
        })}
        missionId={missionId}
      />
    );
  }

  if (section === "monitoring") {
    return (
      <MonitoringWorkspace
        data={await getMonitoringWorkspace()}
        notice={notice}
      />
    );
  }

  if (section === "reports") {
    return (
      <ReportsWorkspace data={await getReportsWorkspace()} notice={notice} />
    );
  }

  if (section === "datasets") {
    return <DatasetsWorkspace data={await getDatasetsWorkspace()} />;
  }

  if (section === "agent-studio") {
    return <AgentStudioWorkspace data={await getAgentStudioWorkspace()} />;
  }

  if (section === "projects") {
    return <ProjectsWorkspace data={await getProjectsWorkspace()} />;
  }

  notFound();
}
