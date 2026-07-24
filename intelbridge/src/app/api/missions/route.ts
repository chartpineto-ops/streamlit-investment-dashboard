import {
  createMissionApiForCurrentWorkspace,
  listMissionsForCurrentWorkspace,
} from "@/server/services/foundation";
import { apiSuccess, safeApiError } from "@/server/http/responses";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    return apiSuccess(await listMissionsForCurrentWorkspace());
  } catch (error) {
    return safeApiError(error);
  }
}

export async function POST(request: Request) {
  try {
    return apiSuccess(
      await createMissionApiForCurrentWorkspace(await request.json()),
      { status: 201 },
    );
  } catch (error) {
    return safeApiError(error);
  }
}
