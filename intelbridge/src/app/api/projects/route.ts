import {
  createProjectForCurrentWorkspace,
  listProjectsForCurrentWorkspace,
} from "@/server/services/foundation";
import { apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const includeArchived =
      new URL(request.url).searchParams.get("includeArchived") !== "false";
    return apiSuccess(await listProjectsForCurrentWorkspace(includeArchived));
  } catch (error) {
    return safeApiError(error);
  }
}

export async function POST(request: Request) {
  try {
    return apiSuccess(
      await createProjectForCurrentWorkspace(await request.json()),
      { status: 201 },
    );
  } catch (error) {
    return safeApiError(error);
  }
}
