import { getAuthContext } from "@/server/auth/context";
import { listRunEvents } from "@/server/events/run-events";
import { processResearchRun } from "@/server/jobs/research-run";
import { isTerminalRunStatus } from "@/server/jobs/run-state";
import { apiError } from "@/server/http/responses";
import { getWorkspaceRun } from "@/server/repositories/runs";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ runId: string }> },
) {
  const { runId } = await params;
  const url = new URL(request.url);
  const headerSequence = Number(request.headers.get("last-event-id") ?? 0);
  const querySequence = Number(url.searchParams.get("after") ?? 0);
  const afterSequence = Math.max(
    Number.isFinite(headerSequence) ? headerSequence : 0,
    Number.isFinite(querySequence) ? querySequence : 0,
  );
  const context = await getAuthContext();
  const run = await getWorkspaceRun(context.workspace.id, runId);

  if (!run) {
    return apiError("RUN_NOT_FOUND", "Research run not found.", 404);
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let sequence = afterSequence;
      let lastHeartbeat = Date.now();
      const deadline = Date.now() + 25_000;
      const processing = processResearchRun(runId);

      try {
        controller.enqueue(
          encoder.encode(": IntelBridge durable run event stream\n\n"),
        );
        while (Date.now() < deadline && !request.signal.aborted) {
          const events = await listRunEvents(
            context.workspace.id,
            runId,
            sequence,
          );
          if (!events) {
            break;
          }
          for (const event of events) {
            sequence = event.sequenceNumber;
            controller.enqueue(
              encoder.encode(
                `id: ${event.sequenceNumber}\ndata: ${JSON.stringify(event)}\n\n`,
              ),
            );
          }
          const currentRun = await getWorkspaceRun(context.workspace.id, runId);
          if (
            currentRun &&
            isTerminalRunStatus(currentRun.status) &&
            events.length === 0
          ) {
            break;
          }
          if (Date.now() - lastHeartbeat >= 5_000) {
            controller.enqueue(encoder.encode(": heartbeat\n\n"));
            lastHeartbeat = Date.now();
          }
          await new Promise((resolve) => setTimeout(resolve, 250));
        }
        await processing;
      } catch {
        controller.enqueue(encoder.encode(": stream reconnect required\n\n"));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Type": "text/event-stream; charset=utf-8",
      "X-Accel-Buffering": "no",
    },
  });
}
