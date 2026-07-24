import { connectorRegistry } from "@/server/connectors/registry";
import { saveConnectorCheckpoint } from "@/server/connectors/checkpoints";
import type {
  DiscoveredItem,
  NormalizedDocument,
  RetrievedDocument,
} from "@/server/connectors/types";
import { getDatabase } from "@/server/db/client";
import { appendRunEvent } from "@/server/events/run-events";
import { persistNormalizedDocument } from "@/server/repositories/documents";
import {
  ConnectorType,
  MissionStatus,
  RunStatus,
  RunStepStatus,
  RunStepType,
  type ConnectorType as ConnectorTypeValue,
  type RunStepType as RunStepTypeValue,
} from "@/shared/domain";

type RunSource = {
  configuration: Record<string, unknown>;
  id: string;
  isDemo: boolean;
  type: ConnectorTypeValue;
};

type DiscoveredSourceItem = {
  connector: RunSource;
  item: DiscoveredItem;
};

type RetrievedSourceItem = {
  connector: RunSource;
  document: RetrievedDocument;
};

type NormalizedSourceItem = {
  connector: RunSource;
  document: NormalizedDocument;
};

type RunMetrics = {
  documentsCreated: number;
  documentsDiscovered: number;
  documentsProcessed: number;
  documentsUnchanged: number;
  documentsUpdated: number;
  progressPercent: number;
  sourcesScanned: number;
};

class CooperativeCancellation extends Error {
  constructor() {
    super("RUN_CANCELLED");
  }
}

function safeErrorCode(error: unknown) {
  if (!(error instanceof Error)) {
    return "CONNECTOR_PROCESSING_FAILED";
  }
  return /^[A-Z0-9_]{3,80}$/.test(error.message)
    ? error.message
    : "CONNECTOR_PROCESSING_FAILED";
}

async function getRunStatus(runId: string) {
  const database = await getDatabase();
  return database
    .prepare(`SELECT status FROM research_runs WHERE id = ? LIMIT 1`)
    .bind(runId)
    .first<{ status: string }>();
}

async function assertNotCancelled(runId: string) {
  const run = await getRunStatus(runId);
  if (!run || run.status === RunStatus.CANCEL_REQUESTED) {
    throw new CooperativeCancellation();
  }
}

async function loadRunSources(runId: string) {
  const database = await getDatabase();
  const run = await database
    .prepare(
      `SELECT rr.id, rr.mission_id, rr.status, rr.data_status, rr.is_demo,
              p.workspace_id
       FROM research_runs rr
       INNER JOIN missions m ON m.id = rr.mission_id
       INNER JOIN projects p ON p.id = m.project_id
       WHERE rr.id = ?
       LIMIT 1`,
    )
    .bind(runId)
    .first<{
      data_status: "demo" | "live";
      id: string;
      is_demo: number;
      mission_id: string;
      status: string;
      workspace_id: string;
    }>();
  if (!run) {
    throw new Error("RUN_NOT_FOUND");
  }

  const sources = await database
    .prepare(
      `SELECT sc.id, sc.type, cc.configuration_json
       FROM mission_sources ms
       INNER JOIN source_connectors sc ON sc.id = ms.source_connector_id
       LEFT JOIN connector_configurations cc ON cc.connector_id = sc.id
       WHERE ms.mission_id = ? AND sc.status = 'CONNECTED'
       ORDER BY ms.priority DESC, sc.id ASC`,
    )
    .bind(run.mission_id)
    .all<{
      configuration_json: string | null;
      id: string;
      type: ConnectorTypeValue;
    }>();
  return {
    ...run,
    sources: sources.results.map(
      (source): RunSource => ({
        configuration: JSON.parse(source.configuration_json ?? "{}") as Record<
          string,
          unknown
        >,
        id: source.id,
        isDemo: source.type === ConnectorType.DEMO,
        type: source.type,
      }),
    ),
  };
}

async function claimJob(runId: string) {
  const database = await getDatabase();
  const now = new Date();
  const leaseExpiresAt = new Date(now.getTime() + 60_000).toISOString();
  const result = await database
    .prepare(
      `UPDATE job_queue
       SET status = 'PROCESSING', attempts = attempts + 1,
           lease_expires_at = ?, updated_at = ?
       WHERE run_id = ?
         AND (
           (status = 'PENDING' AND available_at <= ?)
           OR (status = 'PROCESSING' AND lease_expires_at < ?)
         )`,
    )
    .bind(
      leaseExpiresAt,
      now.toISOString(),
      runId,
      now.toISOString(),
      now.toISOString(),
    )
    .run();
  return Number(result.meta?.changes ?? 0) > 0;
}

async function updateRunMetrics(runId: string, metrics: RunMetrics) {
  const database = await getDatabase();
  const now = new Date().toISOString();
  await database
    .prepare(
      `UPDATE research_runs
       SET sources_scanned = ?, documents_discovered = ?,
           documents_processed = ?, documents_created = ?,
           documents_updated = ?, documents_unchanged = ?,
           progress_percent = ?, updated_at = ?
       WHERE id = ?`,
    )
    .bind(
      metrics.sourcesScanned,
      metrics.documentsDiscovered,
      metrics.documentsProcessed,
      metrics.documentsCreated,
      metrics.documentsUpdated,
      metrics.documentsUnchanged,
      metrics.progressPercent,
      now,
      runId,
    )
    .run();
  await appendRunEvent(runId, {
    metrics,
    timestamp: now,
    type: "run.metrics",
  });
}

async function executeStep<T>(
  runId: string,
  stepType: RunStepTypeValue,
  progressPercent: number,
  operation: () => Promise<T>,
) {
  void progressPercent;
  const database = await getDatabase();
  const step = await database
    .prepare(
      `SELECT id, name, attempt
       FROM run_steps
       WHERE research_run_id = ? AND step_type = ?
       LIMIT 1`,
    )
    .bind(runId, stepType)
    .first<{ attempt: number; id: string; name: string }>();
  if (!step) {
    throw new Error("RUN_STEP_NOT_FOUND");
  }
  await assertNotCancelled(runId);
  const startedAt = new Date().toISOString();
  await database
    .prepare(
      `UPDATE run_steps
       SET status = ?, progress_percent = 0, started_at = ?,
           completed_at = NULL, error_code = NULL, error_message = NULL,
           updated_at = ?
       WHERE id = ?`,
    )
    .bind(RunStepStatus.RUNNING, startedAt, startedAt, step.id)
    .run();
  await appendRunEvent(runId, {
    message: `${step.name} started`,
    stepId: step.id,
    stepType,
    timestamp: startedAt,
    type: "step.started",
  });

  try {
    const output = await operation();
    await assertNotCancelled(runId);
    const completedAt = new Date().toISOString();
    const durationMs = Date.parse(completedAt) - Date.parse(startedAt);
    await database
      .prepare(
        `UPDATE run_steps
         SET status = ?, progress_percent = 100, completed_at = ?,
             duration_ms = ?, output_summary = ?, updated_at = ?
         WHERE id = ?`,
      )
      .bind(
        RunStepStatus.COMPLETED,
        completedAt,
        durationMs,
        `${step.name} completed.`,
        completedAt,
        step.id,
      )
      .run();
    await appendRunEvent(runId, {
      message: `${step.name} completed`,
      progress: 100,
      stepId: step.id,
      timestamp: completedAt,
      type: "step.progress",
    });
    await appendRunEvent(runId, {
      stepId: step.id,
      timestamp: completedAt,
      type: "step.completed",
    });
    return output;
  } catch (error) {
    if (error instanceof CooperativeCancellation) {
      throw error;
    }
    const failedAt = new Date().toISOString();
    await database
      .prepare(
        `UPDATE run_steps
         SET status = ?, completed_at = ?, error_code = ?,
             error_message = ?, updated_at = ?
         WHERE id = ?`,
      )
      .bind(
        RunStepStatus.FAILED,
        failedAt,
        safeErrorCode(error),
        "The run step could not be completed.",
        failedAt,
        step.id,
      )
      .run();
    throw error;
  }
}

async function recordRetrievalFailure(input: {
  connectorId: string;
  error: unknown;
  externalId?: string;
  runId: string;
  url?: string;
}) {
  const database = await getDatabase();
  const now = new Date().toISOString();
  await database.batch([
    database
      .prepare(
        `INSERT INTO retrieval_failures
        (id, research_run_id, connector_id, external_id, url, attempt,
         error_code, safe_message, retryable, created_at)
       VALUES (?, ?, ?, ?, ?, 1, ?, ?, 1, ?)`,
      )
      .bind(
        `failure-${crypto.randomUUID()}`,
        input.runId,
        input.connectorId,
        input.externalId ?? null,
        input.url ?? null,
        safeErrorCode(input.error),
        "This source item could not be processed.",
        now,
      ),
    database
      .prepare(
        `UPDATE connector_configurations
         SET last_error_at = ?, updated_at = ?
         WHERE connector_id = ?`,
      )
      .bind(now, now, input.connectorId),
  ]);
}

async function finalizeCancellation(runId: string) {
  const database = await getDatabase();
  const now = new Date().toISOString();
  await database.batch([
    database
      .prepare(
        `UPDATE research_runs
         SET status = ?, completed_at = ?, updated_at = ?,
             error_summary = 'CANCELLED_BY_USER'
         WHERE id = ? AND status IN (?, ?)`,
      )
      .bind(
        RunStatus.CANCELLED,
        now,
        now,
        runId,
        RunStatus.RUNNING,
        RunStatus.CANCEL_REQUESTED,
      ),
    database
      .prepare(
        `UPDATE run_steps
         SET status = ?, completed_at = COALESCE(completed_at, ?),
             updated_at = ?
         WHERE research_run_id = ? AND status IN (?, ?)`,
      )
      .bind(
        RunStepStatus.CANCELLED,
        now,
        now,
        runId,
        RunStepStatus.PENDING,
        RunStepStatus.RUNNING,
      ),
    database
      .prepare(
        `UPDATE job_queue
         SET status = 'CANCELLED', completed_at = ?, lease_expires_at = NULL,
             updated_at = ?
         WHERE run_id = ?`,
      )
      .bind(now, now, runId),
  ]);
  await appendRunEvent(runId, {
    runId,
    timestamp: now,
    type: "run.cancelled",
  });
}

async function finalizeFailure(runId: string, error: unknown) {
  const database = await getDatabase();
  const job = await database
    .prepare(`SELECT attempts, max_attempts FROM job_queue WHERE run_id = ?`)
    .bind(runId)
    .first<{ attempts: number; max_attempts: number }>();
  const now = new Date();
  const errorCode = safeErrorCode(error);
  if (job && Number(job.attempts) < Number(job.max_attempts)) {
    const delaySeconds = 2 ** Number(job.attempts);
    const availableAt = new Date(
      now.getTime() + delaySeconds * 1_000,
    ).toISOString();
    await database.batch([
      database
        .prepare(
          `UPDATE job_queue
           SET status = 'PENDING', available_at = ?, lease_expires_at = NULL,
               last_error_code = ?, updated_at = ?
           WHERE run_id = ?`,
        )
        .bind(availableAt, errorCode, now.toISOString(), runId),
      database
        .prepare(
          `UPDATE run_steps
           SET status = ?, attempt = attempt + 1, started_at = NULL,
               completed_at = NULL, progress_percent = 0, updated_at = ?
           WHERE research_run_id = ? AND status IN (?, ?)`,
        )
        .bind(
          RunStepStatus.PENDING,
          now.toISOString(),
          runId,
          RunStepStatus.RUNNING,
          RunStepStatus.FAILED,
        ),
    ]);
    return;
  }

  await database.batch([
    database
      .prepare(
        `UPDATE research_runs
         SET status = ?, completed_at = ?, error_summary = ?, updated_at = ?
         WHERE id = ?`,
      )
      .bind(
        RunStatus.FAILED,
        now.toISOString(),
        errorCode,
        now.toISOString(),
        runId,
      ),
    database
      .prepare(
        `UPDATE job_queue
         SET status = 'DEAD_LETTER', dead_lettered_at = ?,
             lease_expires_at = NULL, last_error_code = ?, updated_at = ?
         WHERE run_id = ?`,
      )
      .bind(now.toISOString(), errorCode, now.toISOString(), runId),
    database
      .prepare(
        `UPDATE missions
         SET status = ?, updated_at = ?
         WHERE id = (SELECT mission_id FROM research_runs WHERE id = ?)`,
      )
      .bind(MissionStatus.FAILED, now.toISOString(), runId),
  ]);
  await appendRunEvent(runId, {
    errorCode,
    message: "The research run failed after its retry limit.",
    runId,
    timestamp: now.toISOString(),
    type: "run.failed",
  });
}

export async function processResearchRun(runId: string) {
  if (!(await claimJob(runId))) {
    return { claimed: false };
  }

  try {
    const database = await getDatabase();
    const run = await loadRunSources(runId);
    if (run.status === RunStatus.CANCELLED) {
      await database
        .prepare(
          `UPDATE job_queue SET status = 'CANCELLED', updated_at = ?
           WHERE run_id = ?`,
        )
        .bind(new Date().toISOString(), runId)
        .run();
      return { claimed: true, status: RunStatus.CANCELLED };
    }
    if (run.sources.length === 0) {
      throw new Error("MISSION_SOURCE_REQUIRED");
    }

    const startedAt = new Date().toISOString();
    if (run.status === RunStatus.QUEUED) {
      await database.batch([
        database
          .prepare(
            `UPDATE research_runs
             SET status = ?, started_at = ?, updated_at = ?
             WHERE id = ? AND status = ?`,
          )
          .bind(
            RunStatus.RUNNING,
            startedAt,
            startedAt,
            runId,
            RunStatus.QUEUED,
          ),
        database
          .prepare(
            `UPDATE missions SET status = ?, updated_at = ? WHERE id = ?`,
          )
          .bind(MissionStatus.RUNNING, startedAt, run.mission_id),
      ]);
      await appendRunEvent(runId, {
        runId,
        timestamp: startedAt,
        type: "run.started",
      });
    }

    const metrics: RunMetrics = {
      documentsCreated: 0,
      documentsDiscovered: 0,
      documentsProcessed: 0,
      documentsUnchanged: 0,
      documentsUpdated: 0,
      progressPercent: 2,
      sourcesScanned: 0,
    };
    const checkpoints = new Map<string, Record<string, unknown>>();
    let failures = 0;

    await executeStep(runId, RunStepType.PLAN, 8, async () => {
      metrics.sourcesScanned = run.sources.length;
      metrics.progressPercent = 8;
      await updateRunMetrics(runId, metrics);
    });

    const discovered = await executeStep(
      runId,
      RunStepType.DISCOVER,
      24,
      async () => {
        const records: DiscoveredSourceItem[] = [];
        for (const connector of run.sources) {
          await assertNotCancelled(runId);
          try {
            const adapter = connectorRegistry.get(connector.type);
            const result = await adapter.discover(
              { missionId: run.mission_id },
              {
                configuration: connector.configuration,
                connectorId: connector.id,
                requestId: crypto.randomUUID(),
                workspaceId: run.workspace_id,
              },
            );
            if (result.nextCheckpoint) {
              checkpoints.set(connector.id, result.nextCheckpoint);
            }
            for (const item of result.items) {
              records.push({ connector, item });
              await appendRunEvent(runId, {
                connectorId: connector.id,
                publishedAt: item.publishedAt,
                timestamp: new Date().toISOString(),
                title: item.title ?? item.externalId,
                type: "source.discovered",
                url: item.url,
              });
            }
          } catch (error) {
            failures += 1;
            await recordRetrievalFailure({
              connectorId: connector.id,
              error,
              runId,
            });
          }
        }
        metrics.documentsDiscovered = records.length;
        metrics.progressPercent = 24;
        await updateRunMetrics(runId, metrics);
        return records;
      },
    );

    const retrieved = await executeStep(
      runId,
      RunStepType.RETRIEVE,
      42,
      async () => {
        const records: RetrievedSourceItem[] = [];
        for (const record of discovered) {
          await assertNotCancelled(runId);
          try {
            const adapter = connectorRegistry.get(record.connector.type);
            records.push({
              connector: record.connector,
              document: await adapter.retrieve(record.item, {
                configuration: record.connector.configuration,
                connectorId: record.connector.id,
                requestId: crypto.randomUUID(),
                workspaceId: run.workspace_id,
              }),
            });
          } catch (error) {
            failures += 1;
            await recordRetrievalFailure({
              connectorId: record.connector.id,
              error,
              externalId: record.item.externalId,
              runId,
              url: record.item.url,
            });
          }
        }
        metrics.progressPercent = 42;
        await updateRunMetrics(runId, metrics);
        return records;
      },
    );

    const normalized = await executeStep(
      runId,
      RunStepType.NORMALIZE,
      58,
      async () => {
        const records: NormalizedSourceItem[] = [];
        for (const record of retrieved) {
          await assertNotCancelled(runId);
          try {
            const adapter = connectorRegistry.get(record.connector.type);
            records.push({
              connector: record.connector,
              document: await adapter.normalize(record.document, {
                configuration: record.connector.configuration,
                connectorId: record.connector.id,
                requestId: crypto.randomUUID(),
                workspaceId: run.workspace_id,
              }),
            });
          } catch (error) {
            failures += 1;
            await recordRetrievalFailure({
              connectorId: record.connector.id,
              error,
              externalId: record.document.externalId,
              runId,
              url: record.document.canonicalUrl,
            });
          }
        }
        metrics.progressPercent = 58;
        await updateRunMetrics(runId, metrics);
        return records;
      },
    );

    await executeStep(runId, RunStepType.DEDUPLICATE, 68, async () => {
      metrics.progressPercent = 68;
      await updateRunMetrics(runId, metrics);
    });

    await executeStep(runId, RunStepType.PERSIST, 88, async () => {
      for (const record of normalized) {
        await assertNotCancelled(runId);
        try {
          const result = await persistNormalizedDocument({
            connectorId: record.connector.id,
            dataStatus: record.connector.isDemo ? "demo" : "live",
            document: record.document,
            isDemo: record.connector.isDemo,
            missionId: run.mission_id,
            researchRunId: runId,
            storageKey:
              typeof record.document.metadata.storageKey === "string"
                ? record.document.metadata.storageKey
                : undefined,
            workspaceId: run.workspace_id,
          });
          metrics.documentsProcessed += 1;
          if (result.change === "created") {
            metrics.documentsCreated += 1;
          } else if (result.change === "updated") {
            metrics.documentsUpdated += 1;
          } else {
            metrics.documentsUnchanged += 1;
          }
          await appendRunEvent(runId, {
            documentId: result.documentId,
            result: result.change,
            timestamp: new Date().toISOString(),
            title: record.document.title,
            type: "document.processed",
          });
        } catch (error) {
          failures += 1;
          await recordRetrievalFailure({
            connectorId: record.connector.id,
            error,
            externalId: record.document.externalId,
            runId,
            url: record.document.canonicalUrl,
          });
          await appendRunEvent(runId, {
            result: "failed",
            timestamp: new Date().toISOString(),
            title: record.document.title,
            type: "document.processed",
          });
        }
      }
      metrics.progressPercent = 88;
      await updateRunMetrics(runId, metrics);
    });

    await executeStep(runId, RunStepType.FINALIZE, 100, async () => {
      for (const connector of run.sources) {
        const checkpoint = checkpoints.get(connector.id);
        if (checkpoint) {
          await saveConnectorCheckpoint(connector.id, "discovery", checkpoint);
        }
      }
      metrics.progressPercent = 100;
      await updateRunMetrics(runId, metrics);
    });

    if (metrics.documentsProcessed === 0 && failures > 0) {
      throw new Error("ALL_SOURCE_RETRIEVALS_FAILED");
    }
    const completedAt = new Date().toISOString();
    const status =
      failures > 0 ? RunStatus.PARTIALLY_COMPLETED : RunStatus.COMPLETED;
    await database.batch([
      database
        .prepare(
          `UPDATE research_runs
           SET status = ?, completed_at = ?, progress_percent = 100,
               error_summary = ?, updated_at = ?
           WHERE id = ?`,
        )
        .bind(
          status,
          completedAt,
          failures > 0 ? "SOME_SOURCE_ITEMS_FAILED" : null,
          completedAt,
          runId,
        ),
      database
        .prepare(
          `UPDATE job_queue
           SET status = 'COMPLETED', completed_at = ?, lease_expires_at = NULL,
               updated_at = ?
           WHERE run_id = ?`,
        )
        .bind(completedAt, completedAt, runId),
      database
        .prepare(`UPDATE missions SET status = ?, updated_at = ? WHERE id = ?`)
        .bind(MissionStatus.COMPLETED, completedAt, run.mission_id),
    ]);
    await appendRunEvent(runId, {
      runId,
      status,
      timestamp: completedAt,
      type: "run.completed",
    });
    return { claimed: true, status };
  } catch (error) {
    if (error instanceof CooperativeCancellation) {
      await finalizeCancellation(runId);
      return { claimed: true, status: RunStatus.CANCELLED };
    }
    await finalizeFailure(runId, error);
    return { claimed: true, status: RunStatus.FAILED };
  }
}

export async function processNextResearchJob() {
  const database = await getDatabase();
  const job = await database
    .prepare(
      `SELECT run_id
       FROM job_queue
       WHERE queue_name = 'research-runs'
         AND (
           (status = 'PENDING' AND available_at <= ?)
           OR (status = 'PROCESSING' AND lease_expires_at < ?)
         )
       ORDER BY available_at ASC, created_at ASC
       LIMIT 1`,
    )
    .bind(new Date().toISOString(), new Date().toISOString())
    .first<{ run_id: string }>();
  return job ? processResearchRun(job.run_id) : null;
}
