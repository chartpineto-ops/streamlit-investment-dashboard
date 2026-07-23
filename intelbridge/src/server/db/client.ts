import { env } from "cloudflare:workers";

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

export const DEMO_WORKSPACE_ID = "workspace-intelbridge-demo";

const fixedCreatedAt = "2026-07-15T13:00:00.000Z";
const fixedUpdatedAt = "2026-07-22T18:30:00.000Z";

const schemaStatements = [
  `CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS workspaces_name_idx ON workspaces (name)`,
  `CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS users_workspace_role_idx ON users (workspace_id, role)`,
  `CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, name)
  )`,
  `CREATE INDEX IF NOT EXISTS projects_workspace_status_idx ON projects (workspace_id, status)`,
  `CREATE TABLE IF NOT EXISTS source_connectors (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, name)
  )`,
  `CREATE INDEX IF NOT EXISTS source_connectors_workspace_type_status_idx
    ON source_connectors (workspace_id, type, status)`,
  `CREATE TABLE IF NOT EXISTS missions (
    id TEXT PRIMARY KEY NOT NULL,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    status TEXT NOT NULL,
    research_depth TEXT NOT NULL,
    monitoring_mode TEXT NOT NULL,
    monitoring_interval INTEGER,
    created_by_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS missions_project_status_idx ON missions (project_id, status)`,
  `CREATE INDEX IF NOT EXISTS missions_created_by_idx ON missions (created_by_id)`,
  `CREATE INDEX IF NOT EXISTS missions_updated_at_idx ON missions (updated_at)`,
  `CREATE TABLE IF NOT EXISTS mission_sources (
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    source_connector_id TEXT NOT NULL REFERENCES source_connectors(id) ON DELETE CASCADE,
    priority INTEGER NOT NULL DEFAULT 50,
    PRIMARY KEY (mission_id, source_connector_id)
  )`,
  `CREATE INDEX IF NOT EXISTS mission_sources_connector_idx
    ON mission_sources (source_connector_id)`,
] as const;

const seedStatements: { sql: string; values: unknown[] }[] = [
  {
    sql: `INSERT OR IGNORE INTO workspaces (id, name, created_at, updated_at)
      VALUES (?, ?, ?, ?)`,
    values: [
      DEMO_WORKSPACE_ID,
      "IntelBridge Demo Workspace",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  },
  {
    sql: `INSERT OR IGNORE INTO users
      (id, workspace_id, name, email, role, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
    values: [
      "user-alex-parker",
      DEMO_WORKSPACE_ID,
      "Alex Parker",
      "alex.parker@intelbridge.demo",
      "OWNER",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  },
  {
    sql: `INSERT OR IGNORE INTO users
      (id, workspace_id, name, email, role, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
    values: [
      "user-maya-chen",
      DEMO_WORKSPACE_ID,
      "Maya Chen",
      "maya.chen@intelbridge.demo",
      "ANALYST",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  },
  ...[
    [
      "project-competitive-intelligence",
      "Competitive Intelligence",
      "Track product, pricing, and go-to-market changes across the enterprise search market.",
    ],
    [
      "project-market-entry",
      "Market Entry",
      "Evaluate underserved customer segments and evidence-backed routes to market.",
    ],
    [
      "project-product-strategy",
      "Product Strategy",
      "Maintain a durable record of capability gaps, customer implications, and roadmap choices.",
    ],
  ].map(([id, name, description]) => ({
    sql: `INSERT OR IGNORE INTO projects
      (id, workspace_id, name, description, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
    values: [
      id,
      DEMO_WORKSPACE_ID,
      name,
      description,
      "ACTIVE",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  })),
  ...[
    ["connector-demo", "Deterministic demo corpus", "DEMO", "AVAILABLE"],
    ["connector-rss", "RSS and Atom feeds", "RSS_ATOM", "NOT_CONNECTED"],
    [
      "connector-public-web",
      "Approved public webpages",
      "PUBLIC_WEB",
      "NOT_CONNECTED",
    ],
    [
      "connector-manual-url",
      "Manual URL submissions",
      "MANUAL_URL",
      "NOT_CONNECTED",
    ],
    [
      "connector-file-upload",
      "Uploaded documents",
      "FILE_UPLOAD",
      "NOT_CONNECTED",
    ],
    [
      "connector-github-public",
      "GitHub public repositories",
      "GITHUB_PUBLIC",
      "NOT_CONNECTED",
    ],
  ].map(([id, name, type, status]) => ({
    sql: `INSERT OR IGNORE INTO source_connectors
      (id, workspace_id, name, type, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
    values: [
      id,
      DEMO_WORKSPACE_ID,
      name,
      type,
      status,
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  })),
  {
    sql: `INSERT OR IGNORE INTO missions
      (id, project_id, title, objective, scope_json, status, research_depth,
       monitoring_mode, monitoring_interval, created_by_id, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    values: [
      "mission-enterprise-search",
      "project-competitive-intelligence",
      "Enterprise search launch impact",
      "Assess how recent competitor launches in enterprise search affect the product roadmap and identify capability gaps, customer implications, and recommended actions.",
      JSON.stringify({
        focusAreas: ["Products", "Pricing", "Go-to-market"],
        regions: ["North America", "Europe"],
        timeHorizonMonths: 12,
      }),
      "READY",
      "DEEP",
      "MANUAL",
      null,
      "user-alex-parker",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  },
  {
    sql: `INSERT OR IGNORE INTO missions
      (id, project_id, title, objective, scope_json, status, research_depth,
       monitoring_mode, monitoring_interval, created_by_id, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    values: [
      "mission-mid-market",
      "project-market-entry",
      "Mid-market buyer requirements",
      "Identify unresolved information-retrieval needs among teams with 200 to 1,000 employees and map the evidence to pricing and packaging decisions.",
      JSON.stringify({
        focusAreas: ["Customer needs", "Pricing", "Adoption barriers"],
        regions: ["United States"],
        timeHorizonMonths: 18,
      }),
      "PAUSED",
      "STANDARD",
      "WEEKLY",
      10080,
      "user-maya-chen",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  },
  {
    sql: `INSERT OR IGNORE INTO missions
      (id, project_id, title, objective, scope_json, status, research_depth,
       monitoring_mode, monitoring_interval, created_by_id, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    values: [
      "mission-developer-platforms",
      "project-product-strategy",
      "Developer platform capability baseline",
      "Establish an evidence-backed baseline for retrieval APIs, deployment controls, and observability across approved developer platforms.",
      JSON.stringify({
        focusAreas: ["APIs", "Deployment", "Observability"],
        regions: ["Global"],
        timeHorizonMonths: 6,
      }),
      "DRAFT",
      "RAPID",
      "MANUAL",
      null,
      "user-alex-parker",
      fixedCreatedAt,
      fixedUpdatedAt,
    ],
  },
  ...[
    ["mission-enterprise-search", "connector-demo"],
    ["mission-mid-market", "connector-demo"],
    ["mission-developer-platforms", "connector-demo"],
  ].map(([missionId, connectorId]) => ({
    sql: `INSERT OR IGNORE INTO mission_sources
      (mission_id, source_connector_id, priority) VALUES (?, ?, ?)`,
    values: [missionId, connectorId, 100],
  })),
];

let initializationPromise: Promise<void> | undefined;

async function initializeDatabase(database: IntelBridgeDatabase) {
  await database.batch(
    schemaStatements.map((statement) => database.prepare(statement)),
  );
  await database.batch(
    seedStatements.map(({ sql, values }) =>
      database.prepare(sql).bind(...values),
    ),
  );
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
