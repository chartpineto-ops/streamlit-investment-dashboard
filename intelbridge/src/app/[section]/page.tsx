import { notFound } from "next/navigation";

import {
  ProjectsWorkspace,
  SettingsWorkspace,
  SourcesWorkspace,
} from "@/components/foundation-workspaces";
import {
  DocumentsWorkspace,
  RunsWorkspace,
} from "@/components/operations-workspaces";
import { getDocumentsWorkspaceData } from "@/server/services/documents";
import {
  getProjectsWorkspaceData,
  getSettingsWorkspaceData,
  getSourcesWorkspaceData,
} from "@/server/services/foundation";
import { getRunsWorkspaceData } from "@/server/services/runs";

type WorkspacePageProps = {
  params: Promise<{ section: string }>;
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
  const notice = stringValue(query.notice);

  if (section === "sources") {
    const filters = {
      project: stringValue(query.project),
      q: stringValue(query.q),
      status: stringValue(query.status),
      type: stringValue(query.type),
    };
    return (
      <SourcesWorkspace
        data={await getSourcesWorkspaceData()}
        filters={filters}
        notice={notice}
      />
    );
  }
  if (section === "runs") {
    return <RunsWorkspace data={await getRunsWorkspaceData()} />;
  }
  if (section === "documents") {
    const filters = {
      after: stringValue(query.after),
      change: stringValue(query.change),
      connector: stringValue(query.connector),
      mission: stringValue(query.mission),
      q: stringValue(query.q),
    };
    return (
      <DocumentsWorkspace
        data={await getDocumentsWorkspaceData({
          change: filters.change || undefined,
          connectorId: filters.connector || undefined,
          missionId: filters.mission || undefined,
          query: filters.q || undefined,
          retrievedAfter: filters.after
            ? new Date(`${filters.after}T00:00:00.000Z`).toISOString()
            : undefined,
        })}
        filters={filters}
      />
    );
  }
  if (section === "projects") {
    return (
      <ProjectsWorkspace
        data={await getProjectsWorkspaceData()}
        notice={notice}
      />
    );
  }
  if (section === "settings") {
    return <SettingsWorkspace data={await getSettingsWorkspaceData()} />;
  }
  notFound();
}
