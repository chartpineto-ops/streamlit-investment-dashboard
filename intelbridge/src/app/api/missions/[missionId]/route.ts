import {
  getMissionForCurrentWorkspace,
  updateMissionForCurrentWorkspace,
} from "@/server/services/foundation";
import { apiError, apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ missionId: string }> };

export async function GET(_request: Request, { params }: Params) {
  try {
    const { missionId } = await params;
    const mission = await getMissionForCurrentWorkspace(missionId);
    return mission
      ? apiSuccess(mission)
      : apiError("MISSION_NOT_FOUND", "Research mission not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}

export async function PATCH(request: Request, { params }: Params) {
  try {
    const { missionId } = await params;
    const mission = await updateMissionForCurrentWorkspace(
      missionId,
      await request.json(),
    );
    return mission
      ? apiSuccess(mission)
      : apiError("MISSION_NOT_FOUND", "Research mission not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}
