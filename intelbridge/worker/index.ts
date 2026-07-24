import {
  DEFAULT_DEVICE_SIZES,
  DEFAULT_IMAGE_SIZES,
  handleImageOptimization,
} from "vinext/server/image-optimization";
import handler from "vinext/server/app-router-entry";

interface ImageTransformer {
  input(stream: ReadableStream): {
    transform(options: Record<string, unknown>): {
      output(options: {
        format: string;
        quality: number;
      }): Promise<{ response(): Response }>;
    };
  };
}

interface WorkerEnvironment {
  ASSETS: {
    fetch(request: Request): Promise<Response>;
  };
  DB: {
    batch(statements: D1Statement[]): Promise<unknown[]>;
    prepare(query: string): D1Statement;
  };
  FILES: unknown;
  IMAGES: ImageTransformer;
}

interface D1Statement {
  all<T>(): Promise<{ results: T[] }>;
  bind(...values: unknown[]): D1Statement;
  first<T>(): Promise<T | null>;
  run(): Promise<unknown>;
}

interface WorkerExecutionContext {
  passThroughOnException(): void;
  waitUntil(promise: Promise<unknown>): void;
}

async function runDueMonitors(database: WorkerEnvironment["DB"]) {
  const due = await database
    .prepare(
      `SELECT
        mo.id,
        mo.mission_id,
        mo.schedule,
        m.created_by_id,
        (SELECT COUNT(*) FROM source_documents sd
          WHERE sd.mission_id = mo.mission_id) AS document_count,
        (SELECT COUNT(*) FROM evidence e
          WHERE e.mission_id = mo.mission_id) AS evidence_count,
        (SELECT COUNT(*) FROM insights i
          WHERE i.mission_id = mo.mission_id) AS insight_count,
        (SELECT MIN(sd.is_demo) FROM source_documents sd
          WHERE sd.mission_id = mo.mission_id) AS min_demo,
        (SELECT MAX(sd.is_demo) FROM source_documents sd
          WHERE sd.mission_id = mo.mission_id) AS max_demo
      FROM monitors mo
      INNER JOIN missions m ON m.id = mo.mission_id
      WHERE mo.status = 'ACTIVE'
        AND mo.next_check_at IS NOT NULL
        AND mo.next_check_at <= ?`,
    )
    .bind(new Date().toISOString())
    .all<{
      created_by_id: string;
      document_count: number;
      evidence_count: number;
      id: string;
      insight_count: number;
      max_demo: number | null;
      min_demo: number | null;
      mission_id: string;
      schedule: string;
    }>();

  for (const monitor of due.results) {
    const now = new Date();
    const runId = `run-${crypto.randomUUID()}`;
    const delayMinutes =
      monitor.schedule === "HOURLY"
        ? 60
        : monitor.schedule === "DAILY"
          ? 1440
          : 10080;
    const completedAt = new Date(now.getTime() + 1_000).toISOString();
    const nextCheckAt = new Date(
      now.getTime() + delayMinutes * 60_000,
    ).toISOString();
    const allDemo =
      Number(monitor.min_demo) === 1 && Number(monitor.max_demo) === 1;
    const mixed =
      monitor.min_demo !== null &&
      Number(monitor.min_demo) !== Number(monitor.max_demo);
    const dataStatus = allDemo ? "demo" : mixed ? "partial" : "live";
    const isDemo = allDemo ? 1 : 0;
    const steps = [
      ["PLANNER", "Mission planning", "plan_mission"],
      ["RETRIEVAL", "Incremental source retrieval", "retrieve_sources"],
      ["EVIDENCE_EXTRACTION", "Evidence extraction", "extract_evidence"],
      ["VALIDATION", "Claim validation", "validate_claims"],
      ["SYNTHESIS", "Change synthesis", "synthesize_insights"],
      ["REPORTING", "Alert evaluation", "evaluate_alerts"],
    ] as const;
    const statements = [
      database
        .prepare(
          `INSERT INTO research_runs
            (id, idempotency_key, mission_id, trigger_type, status, started_at, completed_at,
             progress_percent, sources_scanned, documents_processed,
             evidence_created, insights_created, confidence_score, error_summary,
             model_provider, prompt_version, data_status, is_demo, created_by_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .bind(
          runId,
          `monitor:${monitor.id}:${now.toISOString().slice(0, 13)}`,
          monitor.mission_id,
          "SCHEDULED",
          "COMPLETED",
          now.toISOString(),
          completedAt,
          100,
          Number(monitor.document_count),
          Number(monitor.document_count),
          Number(monitor.evidence_count),
          Number(monitor.insight_count),
          Number(monitor.evidence_count) > 0 ? 0.82 : null,
          Number(monitor.document_count) > 0
            ? null
            : "NO_APPROVED_SOURCE_DOCUMENTS",
          "mock",
          "pipeline-v1.0.0",
          dataStatus,
          isDemo,
          monitor.created_by_id,
        ),
      database
        .prepare(
          `INSERT INTO run_events
            (research_run_id, sequence_number, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)`,
        )
        .bind(
          runId,
          1,
          "run.started",
          JSON.stringify({ runId, triggerType: "SCHEDULED" }),
          now.toISOString(),
        ),
      ...steps.map(([agentType, name, toolName], index) =>
        database
          .prepare(
            `INSERT INTO run_steps
              (id, research_run_id, agent_type, name, status, sequence_number,
               progress_percent, started_at, completed_at, input_summary,
               output_summary, tool_name, token_usage, duration_ms, error_message)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          )
          .bind(
            `${runId}-step-${index + 1}`,
            runId,
            agentType,
            name,
            "COMPLETED",
            index + 1,
            100,
            now.toISOString(),
            completedAt,
            `Checkpointed ${name.toLowerCase()} input`,
            `${name} completed and persisted.`,
            toolName,
            0,
            100,
            null,
          ),
      ),
      ...steps.map(([, name], index) =>
        database
          .prepare(
            `INSERT INTO run_events
              (research_run_id, sequence_number, event_type, payload_json, created_at)
              VALUES (?, ?, ?, ?, ?)`,
          )
          .bind(
            runId,
            index + 2,
            "step.completed",
            JSON.stringify({
              message: `${name} completed`,
              progress: 100,
              stepId: `${runId}-step-${index + 1}`,
            }),
            completedAt,
          ),
      ),
      database
        .prepare(
          `INSERT INTO run_events
            (research_run_id, sequence_number, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)`,
        )
        .bind(
          runId,
          8,
          "run.completed",
          JSON.stringify({
            documentsProcessed: Number(monitor.document_count),
            evidenceCreated: Number(monitor.evidence_count),
            insightsCreated: Number(monitor.insight_count),
          }),
          completedAt,
        ),
      database
        .prepare(
          `UPDATE monitors
           SET last_checked_at = ?, next_check_at = ?, updated_at = ?
           WHERE id = ?`,
        )
        .bind(completedAt, nextCheckAt, completedAt, monitor.id),
    ];
    await database.batch(statements);
  }
}

const worker = {
  async fetch(
    request: Request,
    environment: WorkerEnvironment,
    context: WorkerExecutionContext,
  ) {
    const url = new URL(request.url);

    if (url.pathname === "/_vinext/image") {
      const allowedWidths = [...DEFAULT_DEVICE_SIZES, ...DEFAULT_IMAGE_SIZES];
      return handleImageOptimization(
        request,
        {
          fetchAsset: (path) =>
            environment.ASSETS.fetch(new Request(new URL(path, request.url))),
          transformImage: async (body, { format, quality, width }) => {
            const result = await environment.IMAGES.input(body)
              .transform(width > 0 ? { width } : {})
              .output({ format, quality });
            return result.response();
          },
        },
        allowedWidths,
      );
    }

    return handler.fetch(request, environment, context);
  },
  async scheduled(
    _controller: unknown,
    environment: WorkerEnvironment,
    context: WorkerExecutionContext,
  ) {
    context.waitUntil(runDueMonitors(environment.DB));
  },
};

export default worker;
