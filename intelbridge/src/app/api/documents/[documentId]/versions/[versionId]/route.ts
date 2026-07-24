import { apiSuccess, safeApiError } from "@/server/http/responses";
import { getDocumentVersionForCurrentWorkspace } from "@/server/services/documents";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ documentId: string; versionId: string }> },
) {
  try {
    const { documentId, versionId } = await params;
    const result = await getDocumentVersionForCurrentWorkspace(
      documentId,
      versionId,
    );
    if (!result) throw new Error("DOCUMENT_NOT_FOUND");
    return apiSuccess(result);
  } catch (error) {
    return safeApiError(error);
  }
}
