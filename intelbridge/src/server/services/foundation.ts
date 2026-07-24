import { getAuthContext } from "@/server/auth/context";
import { connectorRegistry } from "@/server/connectors/registry";
import {
  assignWorkspaceMissionSource,
  createWorkspaceConnector,
  createWorkspaceProject,
  getWorkspaceConnector,
  getWorkspaceProject,
  listWorkspaceConnectors,
  listWorkspaceProjects,
  removeWorkspaceMissionSource,
  saveConnectorTestResult,
  updateWorkspaceConnector,
  updateWorkspaceMission,
  updateWorkspaceProject,
} from "@/server/repositories/foundation";
import {
  createMission,
  getMissionById,
  listMissions,
} from "@/server/repositories/missions";
import { ConnectorType, MissionStatus } from "@/shared/domain";
import {
  connectorCreateSchema,
  connectorUpdateSchema,
  missionCreateApiSchema,
  missionSourceAssignmentSchema,
  missionUpdateSchema,
  projectCreateSchema,
  projectUpdateSchema,
} from "@/shared/schemas/platform";

export async function listProjectsForCurrentWorkspace(includeArchived = true) {
  const context = await getAuthContext();
  return listWorkspaceProjects(context.workspace.id, includeArchived);
}

export async function getProjectForCurrentWorkspace(projectId: string) {
  const context = await getAuthContext();
  return getWorkspaceProject(context.workspace.id, projectId);
}

export async function createProjectForCurrentWorkspace(values: unknown) {
  const context = await getAuthContext();
  return createWorkspaceProject({
    project: projectCreateSchema.parse(values),
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function updateProjectForCurrentWorkspace(
  projectId: string,
  values: unknown,
) {
  const context = await getAuthContext();
  return updateWorkspaceProject({
    project: projectUpdateSchema.parse(values),
    projectId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function listMissionsForCurrentWorkspace() {
  const context = await getAuthContext();
  return listMissions(context.workspace.id);
}

export async function getMissionForCurrentWorkspace(missionId: string) {
  const context = await getAuthContext();
  return getMissionById(context.workspace.id, missionId);
}

export async function createMissionApiForCurrentWorkspace(values: unknown) {
  const context = await getAuthContext();
  const input = missionCreateApiSchema.parse(values);
  const mission = await createMission({
    connectorIds: input.connectorIds,
    createdById: context.user.id,
    focusAreas: input.scope.focusAreas,
    monitoringMode: "MANUAL",
    objective: input.objective,
    projectId: input.projectId,
    regions: input.scope.regions,
    researchDepth: input.researchDepth,
    timeHorizonMonths: input.scope.timeHorizonMonths,
    title: input.title,
    workspaceId: context.workspace.id,
  });

  if (input.status === MissionStatus.DRAFT) {
    await updateWorkspaceMission({
      mission: { status: MissionStatus.DRAFT },
      missionId: mission.id,
      userId: context.user.id,
      workspaceId: context.workspace.id,
    });
  }

  return getMissionById(context.workspace.id, mission.id);
}

export async function updateMissionForCurrentWorkspace(
  missionId: string,
  values: unknown,
) {
  const context = await getAuthContext();
  const updated = await updateWorkspaceMission({
    mission: missionUpdateSchema.parse(values),
    missionId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
  return updated ? getMissionById(context.workspace.id, missionId) : null;
}

export async function assignMissionSourceForCurrentWorkspace(
  missionId: string,
  values: unknown,
) {
  const context = await getAuthContext();
  const input = missionSourceAssignmentSchema.parse(values);
  return assignWorkspaceMissionSource({
    ...input,
    missionId,
    workspaceId: context.workspace.id,
  });
}

export async function removeMissionSourceForCurrentWorkspace(
  missionId: string,
  connectorId: string,
) {
  const context = await getAuthContext();
  return removeWorkspaceMissionSource({
    connectorId,
    missionId,
    workspaceId: context.workspace.id,
  });
}

export async function listConnectorsForCurrentWorkspace() {
  const context = await getAuthContext();
  return listWorkspaceConnectors(context.workspace.id);
}

export async function getConnectorForCurrentWorkspace(connectorId: string) {
  const context = await getAuthContext();
  return getWorkspaceConnector(context.workspace.id, connectorId);
}

export async function createConnectorForCurrentWorkspace(values: unknown) {
  const context = await getAuthContext();
  return createWorkspaceConnector({
    connector: connectorCreateSchema.parse(values),
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function updateConnectorForCurrentWorkspace(
  connectorId: string,
  values: unknown,
) {
  const context = await getAuthContext();
  return updateWorkspaceConnector({
    connector: connectorUpdateSchema.parse(values),
    connectorId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function testConnectorForCurrentWorkspace(connectorId: string) {
  const context = await getAuthContext();
  const connector = await getWorkspaceConnector(
    context.workspace.id,
    connectorId,
  );
  if (!connector) {
    return null;
  }

  const startedAt = Date.now();
  let result: {
    message: string;
    ok: boolean;
    responseTimeMs: number;
    testedAt: string;
  };
  if (!connectorRegistry.has(connector.type as ConnectorType)) {
    result = {
      message:
        "The connector configuration is valid. Retrieval activates after its required public endpoint is configured.",
      ok: connector.status === "CONNECTED",
      responseTimeMs: Date.now() - startedAt,
      testedAt: new Date().toISOString(),
    };
  } else {
    try {
      result = await connectorRegistry
        .get(connector.type as ConnectorType)
        .testConnection({
          configuration: connector.configuration,
          connectorId: connector.id,
          requestId: crypto.randomUUID(),
          workspaceId: context.workspace.id,
        });
    } catch {
      result = {
        message:
          "The connector test failed. Review its public endpoint and server-side credentials.",
        ok: false,
        responseTimeMs: Date.now() - startedAt,
        testedAt: new Date().toISOString(),
      };
    }
  }

  return saveConnectorTestResult({
    connectorId,
    message: result.message,
    ok: result.ok,
    responseTimeMs: result.responseTimeMs,
    workspaceId: context.workspace.id,
  });
}

export async function getProjectsWorkspaceData() {
  const context = await getAuthContext();
  return {
    context,
    projects: await listWorkspaceProjects(context.workspace.id, true),
  };
}

export async function getSourcesWorkspaceData() {
  const context = await getAuthContext();
  const [connectors, missions] = await Promise.all([
    listWorkspaceConnectors(context.workspace.id),
    listMissions(context.workspace.id),
  ]);
  return { connectors, context, missions };
}

export async function getSettingsWorkspaceData() {
  const context = await getAuthContext();
  return { context };
}
