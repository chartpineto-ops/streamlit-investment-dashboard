import { apiSuccess, safeApiError } from "@/server/http/responses";
import { retryRunForCurrentWorkspace } from "@/server/services/runs";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  try {
    const { runId } = await params;
    const result = await retryRunForCurrentWorkspace(
      runId,
      request.headers.get("idempotency-key") ?? undefined,
    );
    return apiSuccess(result, { status: result.created ? 201 : 200 });
  } catch (error) {
    return safeApiError(error);
  }
}
