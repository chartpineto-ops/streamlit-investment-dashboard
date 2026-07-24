import { cancelResearchForCurrentUser } from "@/server/services/intelligence";

export const dynamic = "force-dynamic";

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const cancelled = await cancelResearchForCurrentUser(runId);

  if (!cancelled) {
    return Response.json(
      {
        code: "RUN_NOT_ACTIVE",
        message: "The run does not exist or is not active.",
      },
      { status: 409 },
    );
  }

  return Response.json({ data: { id: runId, status: "CANCELLED" } });
}
