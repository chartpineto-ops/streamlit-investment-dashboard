import { getDatabase } from "@/server/db/client";
import {
  durableRunEventSchema,
  researchRunEventPayloadSchema,
  type ResearchRunEventPayload,
} from "@/shared/schemas/run-events";

export async function appendRunEvent(
  researchRunId: string,
  payload: ResearchRunEventPayload,
) {
  const database = await getDatabase();
  const validated = researchRunEventPayloadSchema.parse(payload);
  const createdAt = validated.timestamp;

  await database
    .prepare(
      `INSERT INTO run_events
        (research_run_id, sequence_number, event_type, payload_json, created_at)
       SELECT ?, COALESCE(MAX(sequence_number), 0) + 1, ?, ?, ?
       FROM run_events
       WHERE research_run_id = ?`,
    )
    .bind(
      researchRunId,
      validated.type,
      JSON.stringify(validated),
      createdAt,
      researchRunId,
    )
    .run();

  return database
    .prepare(
      `SELECT sequence_number, event_type, payload_json, created_at
       FROM run_events
       WHERE research_run_id = ?
       ORDER BY sequence_number DESC
       LIMIT 1`,
    )
    .bind(researchRunId)
    .first<{
      created_at: string;
      event_type: string;
      payload_json: string;
      sequence_number: number;
    }>();
}

export async function listRunEvents(
  workspaceId: string,
  runId: string,
  afterSequence = 0,
  limit = 250,
) {
  const database = await getDatabase();
  const scope = await database
    .prepare(
      `SELECT rr.id
       FROM research_runs rr
       INNER JOIN missions m ON m.id = rr.mission_id
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND rr.id = ?
       LIMIT 1`,
    )
    .bind(workspaceId, runId)
    .first<{ id: string }>();
  if (!scope) {
    return null;
  }

  const result = await database
    .prepare(
      `SELECT sequence_number, event_type, payload_json, created_at
       FROM run_events
       WHERE research_run_id = ? AND sequence_number > ?
       ORDER BY sequence_number ASC
       LIMIT ?`,
    )
    .bind(runId, afterSequence, limit)
    .all<{
      created_at: string;
      event_type: string;
      payload_json: string;
      sequence_number: number;
    }>();

  return result.results.map((event) => {
    const parsedPayload = JSON.parse(event.payload_json) as Record<
      string,
      unknown
    >;
    const candidate = {
      createdAt: event.created_at,
      payload: parsedPayload,
      sequenceNumber: Number(event.sequence_number),
      type: event.event_type,
    };
    const parsed = durableRunEventSchema.safeParse(candidate);
    if (parsed.success) return parsed.data;

    const timestamp = event.created_at;
    const stepId = String(parsedPayload.stepId ?? "legacy-step");
    const legacyPayload =
      event.event_type === "run.started"
        ? {
            runId,
            timestamp,
            type: "run.started" as const,
          }
        : event.event_type === "run.completed"
          ? {
              runId,
              status: "COMPLETED" as const,
              timestamp,
              type: "run.completed" as const,
            }
          : event.event_type === "step.started"
            ? {
                message: String(parsedPayload.message ?? "Step started"),
                stepId,
                stepType: "PLAN" as const,
                timestamp,
                type: "step.started" as const,
              }
            : {
                stepId,
                timestamp,
                type: "step.completed" as const,
              };
    return durableRunEventSchema.parse({
      createdAt: timestamp,
      payload: legacyPayload,
      sequenceNumber: Number(event.sequence_number),
      type: legacyPayload.type,
    });
  });
}
