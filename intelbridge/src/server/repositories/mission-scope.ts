import type { MissionStatus, Prisma } from "@prisma/client";

export type MissionListOptions = {
  projectId?: string;
  status?: MissionStatus;
};

export function missionScopeWhere(
  workspaceId: string,
  options: MissionListOptions = {},
): Prisma.MissionWhereInput {
  return {
    project: {
      workspaceId,
      ...(options.projectId ? { id: options.projectId } : {}),
    },
    ...(options.status ? { status: options.status } : {}),
  };
}
