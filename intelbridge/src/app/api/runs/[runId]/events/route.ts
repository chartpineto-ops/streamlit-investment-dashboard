import { getEventsForCurrentWorkspace } from "@/server/services/intelligence";

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
  const events = await getEventsForCurrentWorkspace(runId, afterSequence);

  if (!events) {
    return Response.json(
      { code: "RUN_NOT_FOUND", message: "Research run not found." },
      { status: 404 },
    );
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      controller.enqueue(
        encoder.encode(": IntelBridge durable run event stream\n\n"),
      );
      for (const event of events) {
        controller.enqueue(
          encoder.encode(
            `id: ${event.sequenceNumber}\ndata: ${JSON.stringify(event)}\n\n`,
          ),
        );
        await new Promise((resolve) => setTimeout(resolve, 90));
      }
      controller.enqueue(encoder.encode(": stream checkpoint complete\n\n"));
      controller.close();
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
