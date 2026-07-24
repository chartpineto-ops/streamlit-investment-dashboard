import { apiSuccess, safeApiError } from "@/server/http/responses";
import {
  listRunsForCurrentWorkspace,
  startRunForCurrentWorkspace,
} from "@/server/services/runs";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ missionId: string }> },
) {
  try {
    const { missionId } = await params;
    return apiSuccess(await listRunsForCurrentWorkspace(missionId));
  } catch (error) {
    return safeApiError(error);
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ missionId: string }> },
) {
  try {
    const { missionId } = await params;
    const result = await startRunForCurrentWorkspace(
      missionId,
      request.headers.get("idempotency-key") ?? undefined,
    );
    return apiSuccess(result, { status: result.created ? 201 : 200 });
  } catch (error) {
    return safeApiError(error);
  }
}
