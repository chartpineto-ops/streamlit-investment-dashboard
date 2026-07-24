import { z } from "zod";

import { getAuthContext } from "@/server/auth/context";
import {
  apiSuccess,
  parseJsonBody,
  safeApiError,
} from "@/server/http/responses";
import { registerPublicUrl } from "@/server/services/ingestion";

const bodySchema = z.object({
  missionId: z.string().min(3).max(180),
  url: z.string().url().max(2_000),
});

export async function POST(
  request: Request,
  { params }: { params: Promise<{ sourceId: string }> },
) {
  try {
    const [{ sourceId }, context, body] = await Promise.all([
      params,
      getAuthContext(),
      request.json(),
    ]);
    const input = parseJsonBody(bodySchema, body);
    return apiSuccess(
      await registerPublicUrl({
        connectorId: sourceId,
        missionId: input.missionId,
        url: input.url,
        workspaceId: context.workspace.id,
      }),
      { status: 201 },
    );
  } catch (error) {
    return safeApiError(error);
  }
}
