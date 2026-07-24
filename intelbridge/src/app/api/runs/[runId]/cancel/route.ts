import { apiSuccess, safeApiError } from "@/server/http/responses";
import { cancelRunForCurrentWorkspace } from "@/server/services/runs";

export const dynamic = "force-dynamic";

export async function POST(
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
