import { getAuthContext } from "@/server/auth/context";
import {
  askGroundedQuestion,
  cancelResearchRun,
  createReport,
  createResearchRun,
  getDiagnostics,
  getMissionIntelligence,
  getReport,
  getRun,
  getRunEvents,
  listAgents,
  listEvidence,
  listInsights,
  listMonitors,
  listReports,
  listSourceDocuments,
  searchWorkspace,
  setMonitorStatus,
} from "@/server/repositories/intelligence";
import {
  listConnectors,
  listMissions,
  listProjects,
} from "@/server/repositories/missions";
import {
  ingestPublicUrl,
  ingestUploadedFile,
} from "@/server/services/ingestion";

export async function getIntelligenceOverview() {
  const context = await getAuthContext();
  const [diagnostics, insights, monitors, sources] = await Promise.all([
    getDiagnostics(context.workspace.id),
    listInsights(context.workspace.id),
    listMonitors(context.workspace.id),
    listSourceDocuments(context.workspace.id),
  ]);

  return {
    context,
    diagnostics,
    insights: insights.records.slice(0, 5),
    monitors: monitors.monitors,
    sources: sources.slice(0, 5),
  };
}

export async function getMissionWorkspace(missionId: string) {
  const context = await getAuthContext();
  return getMissionIntelligence(context.workspace.id, missionId);
}

export async function getSourcesWorkspace(options: {
  missionId?: string;
  query?: string;
}) {
  const context = await getAuthContext();
  const [connectors, documents, missions] = await Promise.all([
    listConnectors(context.workspace.id),
    listSourceDocuments(context.workspace.id, options),
    listMissions(context.workspace.id),
  ]);
  return { connectors, context, documents, missions };
}

export async function getEvidenceWorkspace(options: {
  missionId?: string;
  query?: string;
  selectedId?: string;
  status?: string;
}) {
  const context = await getAuthContext();
  const [evidence, missions] = await Promise.all([
    listEvidence(context.workspace.id, options),
    listMissions(context.workspace.id),
  ]);
  return { context, ...evidence, missions };
}

export async function getInsightsWorkspace(options: {
  category?: string;
  missionId?: string;
  selectedId?: string;
}) {
  const context = await getAuthContext();
  const [insights, missions] = await Promise.all([
    listInsights(context.workspace.id, options),
    listMissions(context.workspace.id),
  ]);
  return { context, ...insights, missions };
}

export async function getMonitoringWorkspace() {
  const context = await getAuthContext();
  return { context, ...(await listMonitors(context.workspace.id)) };
}

export async function getReportsWorkspace() {
  const context = await getAuthContext();
  const [missions, reports] = await Promise.all([
    listMissions(context.workspace.id),
    listReports(context.workspace.id),
  ]);
  return { context, missions, reports };
}

export async function getDatasetsWorkspace() {
  const context = await getAuthContext();
  const [documents, evidence, insights, missions, reports] = await Promise.all([
    listSourceDocuments(context.workspace.id),
    listEvidence(context.workspace.id),
    listInsights(context.workspace.id),
    listMissions(context.workspace.id),
    listReports(context.workspace.id),
  ]);

  return {
    context,
    datasets: [
      {
        description:
          "Versioned normalized source records with retrieval and trust metadata.",
        id: "dataset-source-documents",
        name: "Source documents",
        recordCount: documents.length,
        state: "DEMO",
        updatedAt: documents[0]?.retrievedAt ?? null,
      },
      {
        description:
          "Source-bound excerpts with quality, novelty, confidence, and validation state.",
        id: "dataset-evidence",
        name: "Evidence ledger",
        recordCount: evidence.records.length,
        state: "DEMO",
        updatedAt: evidence.records[0]?.extractedAt ?? null,
      },
      {
        description:
          "Supported findings linked through claims to underlying evidence.",
        id: "dataset-insights",
        name: "Insight register",
        recordCount: insights.records.length,
        state: "DEMO",
        updatedAt: insights.records[0]?.updatedAt ?? null,
      },
      {
        description:
          "Workspace-scoped mission definitions, objectives, and source policies.",
        id: "dataset-missions",
        name: "Mission registry",
        recordCount: missions.length,
        state: "LIVE",
        updatedAt: missions[0]?.updatedAt ?? null,
      },
      {
        description: "Generated briefs and machine-readable evidence packages.",
        id: "dataset-reports",
        name: "Report archive",
        recordCount: reports.length,
        state: "DEMO",
        updatedAt: reports[0]?.generatedAt ?? null,
      },
    ],
  };
}

export async function getAgentStudioWorkspace() {
  const context = await getAuthContext();
  return {
    agents: await listAgents(context.workspace.id),
    context,
  };
}

export async function getProjectsWorkspace() {
  const context = await getAuthContext();
  return {
    context,
    projects: await listProjects(context.workspace.id),
  };
}

export async function getDiagnosticsWorkspace() {
  const context = await getAuthContext();
  return {
    context,
    diagnostics: await getDiagnostics(context.workspace.id),
  };
}

export async function getSearchWorkspace(query: string) {
  const context = await getAuthContext();
  return {
    context,
    results: query ? await searchWorkspace(context.workspace.id, query) : [],
  };
}

export async function getRunWorkspace(runId: string) {
  const context = await getAuthContext();
  return getRun(context.workspace.id, runId);
}

export async function getEventsForCurrentWorkspace(
  runId: string,
  afterSequence: number,
) {
  const context = await getAuthContext();
  return getRunEvents(context.workspace.id, runId, afterSequence);
}

export async function getReportForCurrentWorkspace(reportId: string) {
  const context = await getAuthContext();
  return getReport(context.workspace.id, reportId);
}

export async function startResearchForCurrentUser(
  missionId: string,
  idempotencyKey?: string,
) {
  const context = await getAuthContext();
  return createResearchRun({
    idempotencyKey,
    missionId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function cancelResearchForCurrentUser(runId: string) {
  const context = await getAuthContext();
  return cancelResearchRun({
    runId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function setMonitorStatusForCurrentUser(
  monitorId: string,
  status: "ACTIVE" | "PAUSED",
) {
  const context = await getAuthContext();
  return setMonitorStatus({
    monitorId,
    status,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function createReportForCurrentUser(
  missionId: string,
  type:
    | "EXECUTIVE_BRIEF"
    | "SOURCE_APPENDIX"
    | "COMPETITOR_MATRIX"
    | "EVIDENCE_CSV"
    | "JSON_PACKAGE",
) {
  const context = await getAuthContext();
  return createReport({
    missionId,
    type,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function askForCurrentUser(missionId: string, question: string) {
  const context = await getAuthContext();
  return askGroundedQuestion({
    missionId,
    question,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function ingestUrlForCurrentUser(missionId: string, url: string) {
  const context = await getAuthContext();
  return ingestPublicUrl({
    missionId,
    url,
    workspaceId: context.workspace.id,
  });
}

export async function ingestFileForCurrentUser(missionId: string, file: File) {
  const context = await getAuthContext();
  return ingestUploadedFile({
    file,
    missionId,
    workspaceId: context.workspace.id,
  });
}
