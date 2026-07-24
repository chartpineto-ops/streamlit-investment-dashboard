import {
  getConnectorForCurrentWorkspace,
  updateConnectorForCurrentWorkspace,
} from "@/server/services/foundation";
import { apiError, apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ sourceId: string }> };

export async function GET(_request: Request, { params }: Params) {
  try {
    const { sourceId } = await params;
    const source = await getConnectorForCurrentWorkspace(sourceId);
    return source
      ? apiSuccess(source)
      : apiError("CONNECTOR_NOT_FOUND", "Source connector not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}

export async function PATCH(request: Request, { params }: Params) {
  try {
    const { sourceId } = await params;
    const source = await updateConnectorForCurrentWorkspace(
      sourceId,
      await request.json(),
    );
    return source
      ? apiSuccess(source)
      : apiError("CONNECTOR_NOT_FOUND", "Source connector not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}
