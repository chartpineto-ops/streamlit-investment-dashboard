import { apiSuccess, safeApiError } from "@/server/http/responses";
import { getDocumentForCurrentWorkspace } from "@/server/services/documents";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ documentId: string }> },
) {
  try {
    const { documentId } = await params;
    const result = await getDocumentForCurrentWorkspace(documentId);
    if (!result) throw new Error("DOCUMENT_NOT_FOUND");
    return apiSuccess(result.versions);
  } catch (error) {
    return safeApiError(error);
  }
}
