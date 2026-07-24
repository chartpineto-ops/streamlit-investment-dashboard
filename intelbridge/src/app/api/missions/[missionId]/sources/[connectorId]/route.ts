import { removeMissionSourceForCurrentWorkspace } from "@/server/services/foundation";
import { apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ connectorId: string; missionId: string }> },
) {
  try {
    const { connectorId, missionId } = await params;
    return apiSuccess({
      removed: await removeMissionSourceForCurrentWorkspace(
        missionId,
        connectorId,
      ),
    });
  } catch (error) {
    return safeApiError(error);
  }
}
