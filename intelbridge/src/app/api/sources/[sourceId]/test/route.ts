import { testConnectorForCurrentWorkspace } from "@/server/services/foundation";
import { apiError, apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ sourceId: string }> },
) {
  try {
    const { sourceId } = await params;
    const result = await testConnectorForCurrentWorkspace(sourceId);
    return result
      ? apiSuccess(result)
      : apiError("CONNECTOR_NOT_FOUND", "Source connector not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}
