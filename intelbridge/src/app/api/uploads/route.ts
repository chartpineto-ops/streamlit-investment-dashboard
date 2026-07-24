import { getAuthContext } from "@/server/auth/context";
import { apiSuccess, safeApiError } from "@/server/http/responses";
import { registerUploadedFile } from "@/server/services/ingestion";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const context = await getAuthContext();
    const form = await request.formData();
    const file = form.get("file");
    const missionId = String(form.get("missionId") ?? "");
    const connectorId = form.get("connectorId");
    if (!(file instanceof File)) {
      throw new Error("SOURCE_FILE_SIZE_INVALID");
    }
    return apiSuccess(
      await registerUploadedFile({
        connectorId:
          typeof connectorId === "string" && connectorId
            ? connectorId
            : undefined,
        file,
        missionId,
        workspaceId: context.workspace.id,
      }),
      { status: 201 },
    );
  } catch (error) {
    return safeApiError(error);
  }
}
