import { apiSuccess, safeApiError } from "@/server/http/responses";
import {
  cancelRunForCurrentWorkspace,
  getRunForCurrentWorkspace,
} from "@/server/services/runs";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await params;
    const result = await getRunForCurrentWorkspace(runId);
    if (!result) {
      throw new Error("RUN_NOT_FOUND");
    }
    return apiSuccess(result);
  } catch (error) {
    return safeApiError(error);
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await params;
    return apiSuccess(await cancelRunForCurrentWorkspace(runId));
  } catch (error) {
    return safeApiError(error);
  }
}
