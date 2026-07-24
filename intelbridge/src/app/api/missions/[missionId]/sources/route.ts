import { assignMissionSourceForCurrentWorkspace } from "@/server/services/foundation";
import { apiError, apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ missionId: string }> },
) {
  try {
    const { missionId } = await params;
    const assignment = await assignMissionSourceForCurrentWorkspace(
      missionId,
      await request.json(),
    );
    return assignment
      ? apiSuccess(assignment, { status: 201 })
      : apiError(
          "CONNECTOR_NOT_FOUND",
          "Mission or source connector not found.",
          404,
        );
  } catch (error) {
    return safeApiError(error);
  }
}
