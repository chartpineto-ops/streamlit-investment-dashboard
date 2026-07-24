import { apiSuccess, safeApiError } from "@/server/http/responses";
import { listDocumentsForCurrentWorkspace } from "@/server/services/documents";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const query = Object.fromEntries(new URL(request.url).searchParams);
    return apiSuccess(await listDocumentsForCurrentWorkspace(query));
  } catch (error) {
    return safeApiError(error);
  }
}
