import { apiSuccess, safeApiError } from "@/server/http/responses";
import { getRunStepsForCurrentWorkspace } from "@/server/services/runs";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await params;
    const steps = await getRunStepsForCurrentWorkspace(runId);
    if (!steps) {
      throw new Error("RUN_NOT_FOUND");
    }
    return apiSuccess(steps);
  } catch (error) {
    return safeApiError(error);
  }
}
