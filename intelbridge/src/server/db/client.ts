import { env } from "cloudflare:workers";

import {
  DEMO_WORKSPACE_ID,
  schemaStatements,
  seedStatements,
} from "@/server/db/bootstrap";

export { DEMO_WORKSPACE_ID };

export interface IntelBridgeQueryResult<T> {
  results: T[];
  success: boolean;
}

export interface IntelBridgePreparedStatement {
  all<T>(): Promise<IntelBridgeQueryResult<T>>;
  bind(...values: unknown[]): IntelBridgePreparedStatement;
  first<T>(): Promise<T | null>;
  run(): Promise<{
    meta?: { changes?: number };
    success: boolean;
  }>;
}

export interface IntelBridgeDatabase {
  batch(statements: IntelBridgePreparedStatement[]): Promise<unknown[]>;
  prepare(query: string): IntelBridgePreparedStatement;
}

let initializationPromise: Promise<void> | undefined;

async function ensureColumn(
  database: IntelBridgeDatabase,
  table: string,
  column: string,
  definition: string,
) {
  const columns = await database
    .prepare(`PRAGMA table_info(${table})`)
    .all<{ name: string }>();

  if (!columns.results.some((candidate) => candidate.name === column)) {
    await database
      .prepare(`ALTER TABLE ${table} ADD COLUMN ${column} ${definition}`)
      .run();
  }
}

async function ensureCompatibleSchema(database: IntelBridgeDatabase) {
  const compatibilityColumns = [
    ["connector_configurations", "last_tested_at", "TEXT"],
    ["connector_configurations", "last_test_message", "TEXT"],
    ["connector_configurations", "response_time_ms", "INTEGER"],
    ["mission_sources", "inclusion_rules_json", "TEXT DEFAULT '[]'"],
    ["mission_sources", "exclusion_rules_json", "TEXT DEFAULT '[]'"],
    ["mission_sources", "created_at", "TEXT"],
    ["research_runs", "idempotency_key", "TEXT"],
    ["research_runs", "cancel_requested_at", "TEXT"],
    ["research_runs", "documents_discovered", "INTEGER DEFAULT 0"],
    ["research_runs", "documents_created", "INTEGER DEFAULT 0"],
    ["research_runs", "documents_updated", "INTEGER DEFAULT 0"],
    ["research_runs", "documents_unchanged", "INTEGER DEFAULT 0"],
    ["research_runs", "retry_of_run_id", "TEXT"],
    ["research_runs", "created_at", "TEXT"],
    ["research_runs", "updated_at", "TEXT"],
    ["run_steps", "step_type", "TEXT"],
    ["run_steps", "attempt", "INTEGER DEFAULT 1"],
    ["run_steps", "error_code", "TEXT"],
    ["run_steps", "metadata_json", "TEXT DEFAULT '{}'"],
    ["run_steps", "created_at", "TEXT"],
    ["run_steps", "updated_at", "TEXT"],
    ["source_documents", "current_version_id", "TEXT"],
    ["source_documents", "first_retrieved_at", "TEXT"],
    ["source_documents", "last_retrieved_at", "TEXT"],
    ["source_documents", "last_research_run_id", "TEXT"],
    ["source_documents", "change_status", "TEXT DEFAULT 'CREATED'"],
  ] as const;

  for (const [table, column, definition] of compatibilityColumns) {
    await ensureColumn(database, table, column, definition);
  }

  await database.batch([
    database.prepare(
      `UPDATE research_runs
       SET idempotency_key = 'legacy:' || id
       WHERE idempotency_key IS NULL`,
    ),
    database.prepare(
      `UPDATE research_runs
       SET created_at = COALESCE(created_at, started_at),
           updated_at = COALESCE(updated_at, completed_at, started_at),
           documents_discovered = COALESCE(documents_discovered, documents_processed),
           documents_created = COALESCE(documents_created, documents_processed)
       WHERE created_at IS NULL
          OR updated_at IS NULL
          OR documents_discovered IS NULL
          OR documents_created IS NULL`,
    ),
    database.prepare(
      `UPDATE run_steps
       SET step_type = COALESCE(
             step_type,
             CASE agent_type
               WHEN 'PLANNER' THEN 'PLAN'
               WHEN 'RETRIEVAL' THEN 'RETRIEVE'
               ELSE agent_type
             END
           ),
           attempt = COALESCE(attempt, 1),
           metadata_json = COALESCE(metadata_json, '{}'),
           created_at = COALESCE(created_at, started_at),
           updated_at = COALESCE(updated_at, completed_at, started_at)
       WHERE step_type IS NULL
          OR created_at IS NULL
          OR updated_at IS NULL`,
    ),
    database.prepare(
      `UPDATE source_documents
       SET first_retrieved_at = COALESCE(first_retrieved_at, retrieved_at),
           last_retrieved_at = COALESCE(last_retrieved_at, retrieved_at),
           change_status = COALESCE(change_status, 'CREATED')
       WHERE first_retrieved_at IS NULL
          OR last_retrieved_at IS NULL
          OR change_status IS NULL`,
    ),
    database
      .prepare(
        `UPDATE mission_sources
       SET inclusion_rules_json = COALESCE(inclusion_rules_json, '[]'),
           exclusion_rules_json = COALESCE(exclusion_rules_json, '[]'),
           created_at = COALESCE(created_at, ?)
       WHERE inclusion_rules_json IS NULL
          OR exclusion_rules_json IS NULL
          OR created_at IS NULL`,
      )
      .bind(new Date().toISOString()),
    database.prepare(
      `UPDATE users
       SET role = CASE role
         WHEN 'OWNER' THEN 'ADMIN'
         WHEN 'ANALYST' THEN 'EDITOR'
         ELSE role
       END
       WHERE role IN ('OWNER', 'ANALYST')`,
    ),
    database.prepare(
      `UPDATE source_connectors
       SET type = CASE type
             WHEN 'RSS_ATOM' THEN 'RSS'
             WHEN 'PUBLIC_WEB' THEN 'WEBPAGE'
             WHEN 'GITHUB_PUBLIC' THEN 'GITHUB'
             ELSE type
           END,
           status = CASE status
             WHEN 'AVAILABLE' THEN 'CONNECTED'
             WHEN 'NOT_CONNECTED' THEN 'DISCONNECTED'
             WHEN 'DEGRADED' THEN 'ERROR'
             ELSE status
           END
       WHERE type IN ('RSS_ATOM', 'PUBLIC_WEB', 'GITHUB_PUBLIC')
          OR status IN ('AVAILABLE', 'NOT_CONNECTED', 'DEGRADED')`,
    ),
    database.prepare(
      `UPDATE missions
       SET status = CASE status
         WHEN 'ACTIVE' THEN 'READY'
         WHEN 'PAUSED' THEN 'DRAFT'
         ELSE status
       END
       WHERE status IN ('ACTIVE', 'PAUSED')`,
    ),
    database.prepare(
      `UPDATE research_runs
       SET status = 'RUNNING'
       WHERE status = 'ACTIVE'`,
    ),
    database.prepare(
      `UPDATE research_runs
       SET status = 'COMPLETED',
           completed_at = COALESCE(completed_at, updated_at, started_at),
           progress_percent = 100,
           updated_at = COALESCE(updated_at, completed_at, started_at)
       WHERE status = 'RUNNING'
         AND NOT EXISTS (
           SELECT 1 FROM job_queue jq WHERE jq.run_id = research_runs.id
         )`,
    ),
    database.prepare(
      `UPDATE run_steps
       SET status = 'COMPLETED',
           progress_percent = 100,
           completed_at = COALESCE(completed_at, updated_at, started_at),
           updated_at = COALESCE(updated_at, completed_at, started_at)
       WHERE research_run_id IN (
         SELECT rr.id FROM research_runs rr
         WHERE rr.status = 'COMPLETED'
           AND NOT EXISTS (
             SELECT 1 FROM job_queue jq WHERE jq.run_id = rr.id
           )
       )
       AND status IN ('RUNNING', 'PENDING')`,
    ),
  ]);

  await database
    .prepare(
      `CREATE UNIQUE INDEX IF NOT EXISTS research_runs_idempotency_key_unique
       ON research_runs (idempotency_key)`,
    )
    .run();
  await database
    .prepare(
      `CREATE INDEX IF NOT EXISTS source_documents_last_retrieved_idx
       ON source_documents (workspace_id, last_retrieved_at DESC)`,
    )
    .run();
}

async function initializeDatabase(database: IntelBridgeDatabase) {
  await database.batch(
    schemaStatements.map((schemaStatement) =>
      database.prepare(schemaStatement),
    ),
  );
  await ensureCompatibleSchema(database);
  const chunkSize = 75;
  for (let index = 0; index < seedStatements.length; index += chunkSize) {
    await database.batch(
      seedStatements
        .slice(index, index + chunkSize)
        .map(({ sql, values }) => database.prepare(sql).bind(...values)),
    );
  }
  await ensureCompatibleSchema(database);
  await database
    .prepare(
      `INSERT OR IGNORE INTO source_document_versions
        (id, source_document_id, research_run_id, version_number, content_hash,
         raw_content, normalized_content, mime_type, language, metadata_json,
         storage_key, retrieved_at, created_at)
       SELECT
         'version-' || id,
         id,
         last_research_run_id,
         version,
         content_hash,
         raw_content,
         normalized_content,
         source_type,
         'en',
         metadata_json,
         NULL,
         retrieved_at,
         retrieved_at
       FROM source_documents`,
    )
    .run();
  await database
    .prepare(
      `UPDATE source_documents
       SET current_version_id = COALESCE(current_version_id, 'version-' || id)
       WHERE current_version_id IS NULL`,
    )
    .run();
}

export async function getDatabase(): Promise<IntelBridgeDatabase> {
  const database = (env as unknown as { DB?: IntelBridgeDatabase }).DB;

  if (!database) {
    throw new Error("D1_BINDING_UNAVAILABLE");
  }

  initializationPromise ??= initializeDatabase(database);
  await initializationPromise;

  return database;
}
