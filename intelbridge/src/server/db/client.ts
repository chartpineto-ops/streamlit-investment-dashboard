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
  run(): Promise<{ success: boolean }>;
}

export interface IntelBridgeDatabase {
  batch(statements: IntelBridgePreparedStatement[]): Promise<unknown[]>;
  prepare(query: string): IntelBridgePreparedStatement;
}

let initializationPromise: Promise<void> | undefined;

async function ensureCompatibleSchema(database: IntelBridgeDatabase) {
  const researchRunColumns = await database
    .prepare("PRAGMA table_info(research_runs)")
    .all<{ name: string }>();

  if (
    !researchRunColumns.results.some(
      (column) => column.name === "idempotency_key",
    )
  ) {
    await database
      .prepare("ALTER TABLE research_runs ADD COLUMN idempotency_key TEXT")
      .run();
  }

  await database
    .prepare(
      `UPDATE research_runs
       SET idempotency_key = 'legacy:' || id
       WHERE idempotency_key IS NULL`,
    )
    .run();
  await database
    .prepare(
      `CREATE UNIQUE INDEX IF NOT EXISTS research_runs_idempotency_key_unique
       ON research_runs (idempotency_key)`,
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
