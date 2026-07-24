import {
  getProjectForCurrentWorkspace,
  updateProjectForCurrentWorkspace,
} from "@/server/services/foundation";
import { apiError, apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ projectId: string }> };

export async function GET(_request: Request, { params }: Params) {
  try {
    const { projectId } = await params;
    const project = await getProjectForCurrentWorkspace(projectId);
    return project
      ? apiSuccess(project)
      : apiError("PROJECT_NOT_FOUND", "Project not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}

export async function PATCH(request: Request, { params }: Params) {
  try {
    const { projectId } = await params;
    const project = await updateProjectForCurrentWorkspace(
      projectId,
      await request.json(),
    );
    return project
      ? apiSuccess(project)
      : apiError("PROJECT_NOT_FOUND", "Project not found.", 404);
  } catch (error) {
    return safeApiError(error);
  }
}
