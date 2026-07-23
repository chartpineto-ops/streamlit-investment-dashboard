import type { MissionStatus } from "@/shared/domain";

export type MissionListOptions = {
  projectId?: string;
  status?: MissionStatus;
};

export function missionScopeWhere(
  workspaceId: string,
  options: MissionListOptions = {},
): {
  project: {
    id?: string;
    workspaceId: string;
  };
  status?: MissionStatus;
} {
  return {
    project: {
      workspaceId,
      ...(options.projectId ? { id: options.projectId } : {}),
    },
    ...(options.status ? { status: options.status } : {}),
  };
}
