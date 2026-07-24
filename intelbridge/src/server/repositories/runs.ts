import { getDatabase } from "@/server/db/client";
import { appendRunEvent, listRunEvents } from "@/server/events/run-events";
import { canRetryRun } from "@/server/jobs/run-state";
import {
  ConnectorStatus,
  ConnectorType,
  MissionStatus,
  RunStatus,
  RunStepStatus,
  RunStepType,
  RunTriggerType,
  type RunStatus as RunStatusType,
  type RunTriggerType as RunTriggerTypeValue,
} from "@/shared/domain";

const stepDefinitions = [
  [RunStepType.PLAN, "Plan source retrieval"],
  [RunStepType.DISCOVER, "Discover source items"],
  [RunStepType.RETRIEVE, "Retrieve source content"],
  [RunStepType.NORMALIZE, "Normalize retrieved content"],
  [RunStepType.DEDUPLICATE, "Detect content changes"],
  [RunStepType.PERSIST, "Persist document versions"],
  [RunStepType.FINALIZE, "Finalize run metrics"],
] as const;

type RunRow = {
  cancel_requested_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  data_status: string;
  documents_created: number;
  documents_discovered: number;
  documents_processed: number;
  documents_unchanged: number;
  documents_updated: number;
  error_summary: string | null;
  id: string;
  is_demo: number;
  mission_id: string;
  mission_title?: string;
  progress_percent: number;
  retry_of_run_id: string | null;
  sources_scanned: number;
  started_at: string;
  status: RunStatusType;
  trigger_type: RunTriggerTypeValue;
  updated_at: string | null;
};

export function mapResearchRun(row: RunRow) {
  return {
    cancelRequestedAt: row.cancel_requested_at,
    completedAt: row.completed_at,
    createdAt: row.created_at ?? row.started_at,
    dataStatus: row.data_status,
    documentsCreated: Number(row.documents_created),
    documentsDiscovered: Number(row.documents_discovered),
    documentsProcessed: Number(row.documents_processed),
    documentsUnchanged: Number(row.documents_unchanged),
    documentsUpdated: Number(row.documents_updated),
    errorSummary: row.error_summary,
    id: row.id,
    isDemo: Boolean(row.is_demo),
    missionId: row.mission_id,
    missionTitle: row.mission_title,
    progressPercent: Number(row.progress_percent),
    retryOfRunId: row.retry_of_run_id,
    sourcesScanned: Number(row.sources_scanned),
    startedAt: row.started_at,
    status: row.status,
    triggerType: row.trigger_type,
    updatedAt: row.updated_at ?? row.completed_at ?? row.started_at,
  };
}

const runSelect = `SELECT
  rr.id,
  rr.mission_id,
  rr.trigger_type,
  rr.status,
  rr.started_at,
  rr.completed_at,
  rr.cancel_requested_at,
  rr.progress_percent,
  rr.sources_scanned,
  rr.documents_discovered,
  rr.documents_processed,
  rr.documents_created,
  rr.documents_updated,
  rr.documents_unchanged,
  rr.error_summary,
  rr.data_status,
  rr.is_demo,
  rr.retry_of_run_id,
  rr.created_at,
  rr.updated_at,
  m.title AS mission_title
FROM research_runs rr
INNER JOIN missions m ON m.id = rr.mission_id
INNER JOIN projects p ON p.id = m.project_id`;

export async function listWorkspaceRuns(
  workspaceId: string,
  missionId?: string,
) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `${runSelect}
       WHERE p.workspace_id = ?${missionId ? " AND m.id = ?" : ""}
       ORDER BY rr.started_at DESC
       LIMIT 100`,
    )
    .bind(...(missionId ? [workspaceId, missionId] : [workspaceId]))
    .all<RunRow>();
  return result.results.map(mapResearchRun);
}

export async function getWorkspaceRun(workspaceId: string, runId: string) {
  const database = await getDatabase();
  const row = await database
    .prepare(`${runSelect} WHERE p.workspace_id = ? AND rr.id = ? LIMIT 1`)
    .bind(workspaceId, runId)
    .first<RunRow>();
  return row ? mapResearchRun(row) : null;
}

export async function getRunSteps(runId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `SELECT id, step_type, name, status, sequence_number, progress_percent,
              started_at, completed_at, input_summary, output_summary,
              duration_ms, attempt, error_code, error_message, metadata_json
       FROM run_steps
       WHERE research_run_id = ?
       ORDER BY sequence_number ASC`,
    )
    .bind(runId)
    .all<{
      attempt: number;
      completed_at: string | null;
      duration_ms: number | null;
      error_code: string | null;
      error_message: string | null;
      id: string;
      input_summary: string;
      metadata_json: string;
      name: string;
      output_summary: string | null;
      progress_percent: number;
      sequence_number: number;
      started_at: string | null;
      status: string;
      step_type: string;
    }>();

  return result.results.map((row) => ({
    attempt: Number(row.attempt),
    completedAt: row.completed_at,
    durationMs: row.duration_ms === null ? null : Number(row.duration_ms),
    errorCode: row.error_code,
    errorMessage: row.error_message,
    id: row.id,
    inputSummary: row.input_summary,
    metadata: JSON.parse(row.metadata_json) as Record<string, unknown>,
    name: row.name,
    outputSummary: row.output_summary,
    progressPercent: Number(row.progress_percent),
    sequenceNumber: Number(row.sequence_number),
    startedAt: row.started_at,
    status: row.status,
    stepType: row.step_type,
  }));
}

export async function getWorkspaceRunDetail(
  workspaceId: string,
  runId: string,
) {
  const run = await getWorkspaceRun(workspaceId, runId);
  if (!run) {
    return null;
  }
  const [steps, events] = await Promise.all([
    getRunSteps(runId),
    listRunEvents(workspaceId, runId),
  ]);
  return { events, run, steps };
}

async function createRun(input: {
  idempotencyKey?: string;
  missionId: string;
  retryOfRunId?: string;
  triggerType: RunTriggerTypeValue;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const mission = await database
    .prepare(
      `SELECT m.id, m.status
       FROM missions m
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND m.id = ? AND p.status = 'ACTIVE'
       LIMIT 1`,
    )
    .bind(input.workspaceId, input.missionId)
    .first<{ id: string; status: string }>();
  if (!mission) {
    throw new Error("MISSION_NOT_FOUND");
  }
  if (
    mission.status !== MissionStatus.READY &&
    mission.status !== MissionStatus.COMPLETED &&
    mission.status !== MissionStatus.FAILED
  ) {
    throw new Error("MISSION_NOT_RUNNABLE");
  }

  const sourceResult = await database
    .prepare(
      `SELECT sc.id, sc.type
       FROM mission_sources ms
       INNER JOIN source_connectors sc ON sc.id = ms.source_connector_id
       WHERE ms.mission_id = ? AND sc.workspace_id = ? AND sc.status = ?
       ORDER BY ms.priority DESC, sc.id ASC`,
    )
    .bind(input.missionId, input.workspaceId, ConnectorStatus.CONNECTED)
    .all<{ id: string; type: string }>();
  if (sourceResult.results.length === 0) {
    throw new Error("MISSION_SOURCE_REQUIRED");
  }

  const requestedIdempotencyKey =
    input.idempotencyKey?.trim() ||
    `${input.triggerType.toLowerCase()}:${crypto.randomUUID()}`;
  const idempotencyKey = `${input.workspaceId}:${requestedIdempotencyKey}`;
  const existing = await database
    .prepare(
      `${runSelect}
       WHERE p.workspace_id = ? AND rr.idempotency_key = ?
       LIMIT 1`,
    )
    .bind(input.workspaceId, idempotencyKey)
    .first<RunRow>();
  if (existing) {
    return { created: false, run: mapResearchRun(existing) };
  }
  const active = await database
    .prepare(
      `SELECT id FROM research_runs
       WHERE mission_id = ? AND status IN (?, ?, ?)
       LIMIT 1`,
    )
    .bind(
      input.missionId,
      RunStatus.QUEUED,
      RunStatus.RUNNING,
      RunStatus.CANCEL_REQUESTED,
    )
    .first<{ id: string }>();
  if (active) {
    throw new Error("RUN_ALREADY_ACTIVE");
  }

  const now = new Date().toISOString();
  const runId = `run-${crypto.randomUUID()}`;
  const isDemo = sourceResult.results.every(
    (source) => source.type === ConnectorType.DEMO,
  );
  const dataStatus = isDemo ? "demo" : "live";
  const statements = [
    database
      .prepare(
        `INSERT INTO research_runs
          (id, idempotency_key, mission_id, trigger_type, status, started_at,
           completed_at, cancel_requested_at, progress_percent, sources_scanned,
           documents_discovered, documents_processed, documents_created,
           documents_updated, documents_unchanged, evidence_created,
           insights_created, confidence_score, error_summary, model_provider,
           prompt_version, data_status, is_demo, created_by_id, retry_of_run_id,
           created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                 NULL, NULL, 'none', 'ingestion-v1', ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        runId,
        idempotencyKey,
        input.missionId,
        input.triggerType,
        RunStatus.QUEUED,
        now,
        dataStatus,
        isDemo ? 1 : 0,
        input.userId,
        input.retryOfRunId ?? null,
        now,
        now,
      ),
    ...stepDefinitions.map(([stepType, name], index) =>
      database
        .prepare(
          `INSERT INTO run_steps
            (id, research_run_id, agent_type, step_type, name, status,
             sequence_number, progress_percent, started_at, completed_at,
             input_summary, output_summary, tool_name, token_usage, duration_ms,
             attempt, error_code, error_message, metadata_json, created_at,
             updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL, ?, NULL, ?, 0, NULL, 1,
                   NULL, NULL, '{}', ?, ?)`,
        )
        .bind(
          `${runId}-step-${index + 1}`,
          runId,
          stepType,
          stepType,
          name,
          RunStepStatus.PENDING,
          index + 1,
          `Run ${stepType.toLowerCase()} input`,
          `connector.${stepType.toLowerCase()}`,
          now,
          now,
        ),
    ),
    database
      .prepare(
        `INSERT INTO job_queue
          (id, queue_name, run_id, idempotency_key, status, payload_json,
           attempts, max_attempts, available_at, lease_expires_at, completed_at,
           dead_lettered_at, last_error_code, created_at, updated_at)
         VALUES (?, 'research-runs', ?, ?, 'PENDING', ?, 0, 3, ?, NULL, NULL,
                 NULL, NULL, ?, ?)`,
      )
      .bind(
        `job-${crypto.randomUUID()}`,
        runId,
        `run:${runId}`,
        JSON.stringify({ runId }),
        now,
        now,
        now,
      ),
    database
      .prepare(
        `INSERT INTO run_events
          (research_run_id, sequence_number, event_type, payload_json, created_at)
         VALUES (?, 1, 'run.queued', ?, ?)`,
      )
      .bind(
        runId,
        JSON.stringify({
          runId,
          timestamp: now,
          triggerType: input.triggerType,
          type: "run.queued",
        }),
        now,
      ),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
         VALUES (?, ?, ?, 'RESEARCH_RUN_QUEUED', 'RESEARCH_RUN', ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        runId,
        JSON.stringify({
          retryOfRunId: input.retryOfRunId ?? null,
          triggerType: input.triggerType,
        }),
        `request-${crypto.randomUUID()}`,
        now,
      ),
  ];

  await database.batch(statements);
  const createdRun = await getWorkspaceRun(input.workspaceId, runId);
  if (!createdRun) {
    throw new Error("RUN_CREATE_FAILED");
  }
  return { created: true, run: createdRun };
}

export function createResearchRun(input: {
  idempotencyKey?: string;
  missionId: string;
  userId: string;
  workspaceId: string;
}) {
  return createRun({ ...input, triggerType: RunTriggerType.MANUAL });
}

export async function requestRunCancellation(input: {
  runId: string;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const run = await getWorkspaceRun(input.workspaceId, input.runId);
  if (!run) {
    throw new Error("RUN_NOT_FOUND");
  }
  if (
    run.status === RunStatus.CANCELLED ||
    run.status === RunStatus.CANCEL_REQUESTED
  ) {
    return run;
  }
  const now = new Date().toISOString();
  if (run.status === RunStatus.QUEUED) {
    await database.batch([
      database
        .prepare(
          `UPDATE research_runs
           SET status = ?, completed_at = ?, updated_at = ?,
               error_summary = 'CANCELLED_BY_USER'
           WHERE id = ? AND status = ?`,
        )
        .bind(RunStatus.CANCELLED, now, now, input.runId, RunStatus.QUEUED),
      database
        .prepare(
          `UPDATE run_steps
           SET status = ?, completed_at = ?, updated_at = ?
           WHERE research_run_id = ? AND status = ?`,
        )
        .bind(
          RunStepStatus.CANCELLED,
          now,
          now,
          input.runId,
          RunStepStatus.PENDING,
        ),
      database
        .prepare(
          `UPDATE job_queue
           SET status = 'CANCELLED', completed_at = ?, updated_at = ?
           WHERE run_id = ? AND status = 'PENDING'`,
        )
        .bind(now, now, input.runId),
    ]);
    await appendRunEvent(input.runId, {
      runId: input.runId,
      timestamp: now,
      type: "run.cancelled",
    });
  } else if (run.status === RunStatus.RUNNING) {
    await database
      .prepare(
        `UPDATE research_runs
         SET status = ?, cancel_requested_at = ?, updated_at = ?
         WHERE id = ? AND status = ?`,
      )
      .bind(
        RunStatus.CANCEL_REQUESTED,
        now,
        now,
        input.runId,
        RunStatus.RUNNING,
      )
      .run();
  } else {
    throw new Error("INVALID_RUN_TRANSITION");
  }

  await database
    .prepare(
      `INSERT INTO audit_logs
        (id, workspace_id, user_id, action, entity_type, entity_id,
         details_json, request_id, created_at)
       VALUES (?, ?, ?, 'RESEARCH_RUN_CANCEL_REQUESTED', 'RESEARCH_RUN', ?,
               '{}', ?, ?)`,
    )
    .bind(
      `audit-${crypto.randomUUID()}`,
      input.workspaceId,
      input.userId,
      input.runId,
      `request-${crypto.randomUUID()}`,
      now,
    )
    .run();
  return getWorkspaceRun(input.workspaceId, input.runId);
}

export async function retryResearchRun(input: {
  idempotencyKey?: string;
  runId: string;
  userId: string;
  workspaceId: string;
}) {
  const original = await getWorkspaceRun(input.workspaceId, input.runId);
  if (!original) {
    throw new Error("RUN_NOT_FOUND");
  }
  if (!canRetryRun(original.status)) {
    throw new Error("INVALID_RUN_TRANSITION");
  }
  return createRun({
    idempotencyKey: input.idempotencyKey,
    missionId: original.missionId,
    retryOfRunId: original.id,
    triggerType: RunTriggerType.RETRY,
    userId: input.userId,
    workspaceId: input.workspaceId,
  });
}
