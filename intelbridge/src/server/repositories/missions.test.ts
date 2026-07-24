import { describe, expect, it } from "vitest";

import { missionScopeWhere } from "@/server/repositories/mission-scope";
import { MissionStatus } from "@/shared/domain";

describe("missionScopeWhere", () => {
  it("always scopes mission queries through the authenticated workspace", () => {
    expect(missionScopeWhere("workspace-a")).toEqual({
      project: {
        workspaceId: "workspace-a",
      },
    });
  });

  it("keeps project and status filters inside the workspace boundary", () => {
    expect(
      missionScopeWhere("workspace-a", {
        projectId: "project-a",
        status: MissionStatus.RUNNING,
      }),
    ).toEqual({
      project: {
        id: "project-a",
        workspaceId: "workspace-a",
      },
      status: MissionStatus.RUNNING,
    });
  });
});
