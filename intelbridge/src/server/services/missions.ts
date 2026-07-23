import { getAuthContext } from "@/server/auth/context";
import {
  createMission,
  getMissionById,
  getWorkspaceSummary,
  listConnectors,
  listMissions,
  listProjects,
  type MissionListOptions,
} from "@/server/repositories/missions";
import {
  createMissionSchema,
  missionScopeSchema,
} from "@/shared/schemas/mission";

export async function getShellData() {
  const context = await getAuthContext();
  const [projects, missions] = await Promise.all([
    listProjects(context.workspace.id),
    listMissions(context.workspace.id),
  ]);

  return {
    context,
    missionCount: missions.length,
    projects,
  };
}

export async function getHomeData() {
  const context = await getAuthContext();
  const [missions, summary] = await Promise.all([
    listMissions(context.workspace.id),
    getWorkspaceSummary(context.workspace.id),
  ]);

  return {
    context,
    missions: missions.slice(0, 3),
    summary,
  };
}

export async function getMissionListData(options: MissionListOptions = {}) {
  const context = await getAuthContext();
  const [missions, projects] = await Promise.all([
    listMissions(context.workspace.id, options),
    listProjects(context.workspace.id),
  ]);

  return {
    context,
    missions,
    projects,
  };
}

export async function getMissionDetailData(missionId: string) {
  const context = await getAuthContext();
  const mission = await getMissionById(context.workspace.id, missionId);

  if (!mission) {
    return null;
  }

  return {
    context,
    mission: {
      ...mission,
      scope: missionScopeSchema.parse(mission.scope),
    },
  };
}

export async function getNewMissionData() {
  const context = await getAuthContext();
  const [connectors, projects] = await Promise.all([
    listConnectors(context.workspace.id),
    listProjects(context.workspace.id),
  ]);

  return {
    connectors,
    context,
    projects,
  };
}

export async function createMissionForCurrentUser(values: unknown) {
  const context = await getAuthContext();
  const input = createMissionSchema.parse(values);

  return createMission({
    ...input,
    createdById: context.user.id,
    workspaceId: context.workspace.id,
  });
}
