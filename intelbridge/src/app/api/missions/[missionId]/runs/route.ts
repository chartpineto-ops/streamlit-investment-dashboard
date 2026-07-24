import { startResearchForCurrentUser } from "@/server/services/intelligence";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ missionId: string }> },
) {
  try {
    const { missionId } = await params;
    const run = await startResearchForCurrentUser(
      missionId,
      request.headers.get("idempotency-key") ?? undefined,
    );
    return Response.json(
      {
        data: run,
        is_demo: run.isDemo,
        status: run.dataStatus,
      },
      { status: run.created ? 201 : 200 },
    );
  } catch (error) {
    const code = error instanceof Error ? error.message : "RUN_CREATE_FAILED";
    return Response.json(
      { code, message: "The research run could not be created." },
      { status: code === "MISSION_NOT_FOUND" ? 404 : 400 },
    );
  }
}
