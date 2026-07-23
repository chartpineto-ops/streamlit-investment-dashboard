import { ConnectorStatus, MissionStatus, ProjectStatus } from "@prisma/client";

import { prisma } from "@/server/db/client";
import {
  missionScopeWhere,
  type MissionListOptions,
} from "@/server/repositories/mission-scope";
import type { CreateMissionInput } from "@/shared/schemas/mission";

export {
  missionScopeWhere,
  type MissionListOptions,
} from "@/server/repositories/mission-scope";

export async function listMissions(
  workspaceId: string,
  options: MissionListOptions = {},
) {
  return prisma.mission.findMany({
    where: missionScopeWhere(workspaceId, options),
    orderBy: [{ updatedAt: "desc" }, { title: "asc" }],
    include: {
      createdBy: {
        select: {
          id: true,
          name: true,
        },
      },
      project: {
        select: {
          id: true,
          name: true,
        },
      },
      sources: {
        include: {
          sourceConnector: {
            select: {
              id: true,
              name: true,
              status: true,
              type: true,
            },
          },
        },
        orderBy: {
          priority: "desc",
        },
      },
      _count: {
        select: {
          insights: true,
          researchRuns: true,
        },
      },
    },
  });
}

export async function getMissionById(workspaceId: string, missionId: string) {
  return prisma.mission.findFirst({
    where: {
      id: missionId,
      ...missionScopeWhere(workspaceId),
    },
    include: {
      createdBy: {
        select: {
          id: true,
          name: true,
        },
      },
      project: {
        select: {
          id: true,
          name: true,
        },
      },
      sources: {
        include: {
          sourceConnector: {
            select: {
              id: true,
              name: true,
              status: true,
              type: true,
            },
          },
        },
        orderBy: {
          priority: "desc",
        },
      },
      researchRuns: {
        orderBy: {
          createdAt: "desc",
        },
        take: 5,
      },
      _count: {
        select: {
          claims: true,
          evidence: true,
          insights: true,
          researchRuns: true,
        },
      },
    },
  });
}

export async function listProjects(workspaceId: string) {
  return prisma.project.findMany({
    where: {
      status: ProjectStatus.ACTIVE,
      workspaceId,
    },
    orderBy: {
      name: "asc",
    },
    include: {
      _count: {
        select: {
          missions: true,
        },
      },
    },
  });
}

export async function listConnectors(workspaceId: string) {
  return prisma.sourceConnector.findMany({
    where: {
      workspaceId,
    },
    orderBy: [{ status: "asc" }, { name: "asc" }],
  });
}

export async function getWorkspaceSummary(workspaceId: string) {
  const [
    missionCount,
    activeMissionCount,
    projectCount,
    availableConnectorCount,
    connectorCount,
  ] = await Promise.all([
    prisma.mission.count({ where: missionScopeWhere(workspaceId) }),
    prisma.mission.count({
      where: {
        ...missionScopeWhere(workspaceId),
        status: {
          in: [MissionStatus.READY, MissionStatus.ACTIVE],
        },
      },
    }),
    prisma.project.count({
      where: {
        status: ProjectStatus.ACTIVE,
        workspaceId,
      },
    }),
    prisma.sourceConnector.count({
      where: {
        status: ConnectorStatus.AVAILABLE,
        workspaceId,
      },
    }),
    prisma.sourceConnector.count({
      where: {
        workspaceId,
      },
    }),
  ]);

  return {
    activeMissionCount,
    availableConnectorCount,
    connectorCount,
    missionCount,
    projectCount,
  };
}

type ScopedCreateMissionInput = CreateMissionInput & {
  createdById: string;
  workspaceId: string;
};

export async function createMission(input: ScopedCreateMissionInput) {
  return prisma.$transaction(async (transaction) => {
    const connectorIds = [...new Set(input.connectorIds)];
    const [project, connectorCount] = await Promise.all([
      transaction.project.findFirst({
        where: {
          id: input.projectId,
          status: ProjectStatus.ACTIVE,
          workspaceId: input.workspaceId,
        },
        select: {
          id: true,
        },
      }),
      transaction.sourceConnector.count({
        where: {
          id: {
            in: connectorIds,
          },
          workspaceId: input.workspaceId,
        },
      }),
    ]);

    if (!project) {
      throw new Error("PROJECT_NOT_FOUND");
    }

    if (connectorCount !== connectorIds.length) {
      throw new Error("CONNECTOR_NOT_FOUND");
    }

    return transaction.mission.create({
      data: {
        createdById: input.createdById,
        monitoringInterval:
          input.monitoringMode === "MANUAL"
            ? null
            : input.monitoringMode === "HOURLY"
              ? 60
              : input.monitoringMode === "DAILY"
                ? 1440
                : 10080,
        monitoringMode: input.monitoringMode,
        objective: input.objective,
        projectId: project.id,
        researchDepth: input.researchDepth,
        scope: {
          focusAreas: input.focusAreas,
          regions: input.regions,
          timeHorizonMonths: input.timeHorizonMonths,
        },
        status: MissionStatus.READY,
        title: input.title,
        sources: {
          create: connectorIds.map((sourceConnectorId, index) => ({
            priority: 100 - index,
            sourceConnectorId,
          })),
        },
      },
      select: {
        id: true,
      },
    });
  });
}
