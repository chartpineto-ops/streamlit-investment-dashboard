import { getDatabase } from "@/server/db/client";
import type {
  CreateConnectorInput,
  CreateProjectInput,
  UpdateConnectorInput,
  UpdateMissionInput,
  UpdateProjectInput,
} from "@/shared/schemas/platform";

type ProjectRow = {
  created_at: string;
  description: string;
  id: string;
  mission_count: number;
  name: string;
  status: string;
  updated_at: string;
};

type ConnectorRow = {
  configuration_json: string;
  created_at: string;
  id: string;
  last_error_at: string | null;
  last_successful_sync_at: string | null;
  last_test_message: string | null;
  last_tested_at: string | null;
  mission_count: number;
  name: string;
  project_ids: string | null;
  response_time_ms: number | null;
  status: string;
  type: string;
  updated_at: string;
};

function mapProject(row: ProjectRow) {
  return {
    createdAt: row.created_at,
    description: row.description,
    id: row.id,
    missionCount: Number(row.mission_count),
    name: row.name,
    status: row.status,
    updatedAt: row.updated_at,
  };
}

function mapConnector(row: ConnectorRow) {
  return {
    configuration: JSON.parse(row.configuration_json) as Record<
      string,
      unknown
    >,
    createdAt: row.created_at,
    id: row.id,
    lastErrorAt: row.last_error_at,
    lastSuccessfulSyncAt: row.last_successful_sync_at,
    lastTestMessage: row.last_test_message,
    lastTestedAt: row.last_tested_at,
    missionCount: Number(row.mission_count),
    name: row.name,
    projectIds: row.project_ids?.split(",").filter(Boolean) ?? [],
    responseTimeMs:
      row.response_time_ms === null ? null : Number(row.response_time_ms),
    status: row.status,
    type: row.type,
    updatedAt: row.updated_at,
  };
}

const projectSelect = `SELECT
  p.id,
  p.name,
  p.description,
  p.status,
  p.created_at,
  p.updated_at,
  COUNT(m.id) AS mission_count
FROM projects p
LEFT JOIN missions m ON m.project_id = p.id`;

const connectorSelect = `SELECT
  sc.id,
  sc.name,
  sc.type,
  sc.status,
  sc.created_at,
  sc.updated_at,
  cc.configuration_json,
  cc.last_successful_sync_at,
  cc.last_error_at,
  cc.last_tested_at,
  cc.last_test_message,
  cc.response_time_ms,
  COUNT(ms.mission_id) AS mission_count,
  GROUP_CONCAT(DISTINCT m.project_id) AS project_ids
FROM source_connectors sc
INNER JOIN connector_configurations cc ON cc.connector_id = sc.id
LEFT JOIN mission_sources ms ON ms.source_connector_id = sc.id
LEFT JOIN missions m ON m.id = ms.mission_id`;

export async function listWorkspaceProjects(
  workspaceId: string,
  includeArchived = true,
) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `${projectSelect}
       WHERE p.workspace_id = ?
         ${includeArchived ? "" : "AND p.status = 'ACTIVE'"}
       GROUP BY p.id
       ORDER BY p.status ASC, p.updated_at DESC, p.name ASC`,
    )
    .bind(workspaceId)
    .all<ProjectRow>();

  return result.results.map(mapProject);
}

export async function getWorkspaceProject(
  workspaceId: string,
  projectId: string,
) {
  const database = await getDatabase();
  const project = await database
    .prepare(
      `${projectSelect}
       WHERE p.workspace_id = ? AND p.id = ?
       GROUP BY p.id
       LIMIT 1`,
    )
    .bind(workspaceId, projectId)
    .first<ProjectRow>();

  if (!project) {
    return null;
  }

  const missions = await database
    .prepare(
      `SELECT id, title, objective, status, research_depth, updated_at
       FROM missions
       WHERE project_id = ?
       ORDER BY updated_at DESC`,
    )
    .bind(projectId)
    .all<{
      id: string;
      objective: string;
      research_depth: string;
      status: string;
      title: string;
      updated_at: string;
    }>();

  return {
    ...mapProject(project),
    missions: missions.results.map((mission) => ({
      id: mission.id,
      objective: mission.objective,
      researchDepth: mission.research_depth,
      status: mission.status,
      title: mission.title,
      updatedAt: mission.updated_at,
    })),
  };
}

export async function createWorkspaceProject(input: {
  project: CreateProjectInput;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const id = `project-${crypto.randomUUID()}`;
  const now = new Date().toISOString();
  const requestId = crypto.randomUUID();

  await database.batch([
    database
      .prepare(
        `INSERT INTO projects
          (id, workspace_id, name, description, status, created_at, updated_at)
         VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)`,
      )
      .bind(
        id,
        input.workspaceId,
        input.project.name,
        input.project.description,
        now,
        now,
      ),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
         VALUES (?, ?, ?, 'PROJECT_CREATED', 'PROJECT', ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        id,
        JSON.stringify({ name: input.project.name }),
        requestId,
        now,
      ),
  ]);

  return getWorkspaceProject(input.workspaceId, id);
}

export async function updateWorkspaceProject(input: {
  project: UpdateProjectInput;
  projectId: string;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const existing = await getWorkspaceProject(
    input.workspaceId,
    input.projectId,
  );
  if (!existing) {
    return null;
  }

  const name = input.project.name ?? existing.name;
  const description = input.project.description ?? existing.description;
  const status = input.project.status ?? existing.status;
  const now = new Date().toISOString();

  await database.batch([
    database
      .prepare(
        `UPDATE projects
         SET name = ?, description = ?, status = ?, updated_at = ?
         WHERE id = ? AND workspace_id = ?`,
      )
      .bind(name, description, status, now, input.projectId, input.workspaceId),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
         VALUES (?, ?, ?, 'PROJECT_UPDATED', 'PROJECT', ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        input.projectId,
        JSON.stringify(input.project),
        crypto.randomUUID(),
        now,
      ),
  ]);

  return getWorkspaceProject(input.workspaceId, input.projectId);
}

export async function listWorkspaceConnectors(workspaceId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `${connectorSelect}
       WHERE sc.workspace_id = ?
       GROUP BY sc.id
       ORDER BY sc.status ASC, sc.name ASC`,
    )
    .bind(workspaceId)
    .all<ConnectorRow>();

  return result.results.map(mapConnector);
}

export async function getWorkspaceConnector(
  workspaceId: string,
  connectorId: string,
) {
  const database = await getDatabase();
  const connector = await database
    .prepare(
      `${connectorSelect}
       WHERE sc.workspace_id = ? AND sc.id = ?
       GROUP BY sc.id
       LIMIT 1`,
    )
    .bind(workspaceId, connectorId)
    .first<ConnectorRow>();

  return connector ? mapConnector(connector) : null;
}

export async function createWorkspaceConnector(input: {
  connector: CreateConnectorInput;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const id = `connector-${crypto.randomUUID()}`;
  const now = new Date().toISOString();

  await database.batch([
    database
      .prepare(
        `INSERT INTO source_connectors
          (id, workspace_id, name, type, status, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        id,
        input.workspaceId,
        input.connector.name,
        input.connector.configuration.type,
        input.connector.status,
        now,
        now,
      ),
    database
      .prepare(
        `INSERT INTO connector_configurations
          (connector_id, configuration_json, last_successful_sync_at,
           last_error_at, checkpoint_json, last_tested_at, last_test_message,
           response_time_ms, updated_at)
         VALUES (?, ?, NULL, NULL, NULL, NULL, NULL, NULL, ?)`,
      )
      .bind(id, JSON.stringify(input.connector.configuration), now),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
         VALUES (?, ?, ?, 'CONNECTOR_CREATED', 'SOURCE_CONNECTOR', ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        id,
        JSON.stringify({
          name: input.connector.name,
          type: input.connector.configuration.type,
        }),
        crypto.randomUUID(),
        now,
      ),
  ]);

  return getWorkspaceConnector(input.workspaceId, id);
}

export async function updateWorkspaceConnector(input: {
  connector: UpdateConnectorInput;
  connectorId: string;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const existing = await getWorkspaceConnector(
    input.workspaceId,
    input.connectorId,
  );
  if (!existing) {
    return null;
  }

  const configuration = input.connector.configuration ?? existing.configuration;
  const type = input.connector.configuration?.type ?? String(existing.type);
  const now = new Date().toISOString();

  await database.batch([
    database
      .prepare(
        `UPDATE source_connectors
         SET name = ?, type = ?, status = ?, updated_at = ?
         WHERE id = ? AND workspace_id = ?`,
      )
      .bind(
        input.connector.name ?? existing.name,
        type,
        input.connector.status ?? existing.status,
        now,
        input.connectorId,
        input.workspaceId,
      ),
    database
      .prepare(
        `UPDATE connector_configurations
         SET configuration_json = ?, updated_at = ?
         WHERE connector_id = ?`,
      )
      .bind(JSON.stringify(configuration), now, input.connectorId),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
         VALUES (?, ?, ?, 'CONNECTOR_UPDATED', 'SOURCE_CONNECTOR', ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        input.connectorId,
        JSON.stringify(input.connector),
        crypto.randomUUID(),
        now,
      ),
  ]);

  return getWorkspaceConnector(input.workspaceId, input.connectorId);
}

export async function saveConnectorTestResult(input: {
  connectorId: string;
  message: string;
  ok: boolean;
  responseTimeMs: number;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const connector = await getWorkspaceConnector(
    input.workspaceId,
    input.connectorId,
  );
  if (!connector) {
    return null;
  }

  const testedAt = new Date().toISOString();
  await database.batch([
    database
      .prepare(
        `UPDATE connector_configurations
         SET last_tested_at = ?, last_test_message = ?, response_time_ms = ?,
             last_error_at = CASE WHEN ? = 1 THEN NULL ELSE ? END,
             updated_at = ?
         WHERE connector_id = ?`,
      )
      .bind(
        testedAt,
        input.message,
        input.responseTimeMs,
        input.ok ? 1 : 0,
        testedAt,
        testedAt,
        input.connectorId,
      ),
    database
      .prepare(
        `UPDATE source_connectors
         SET status = ?, updated_at = ?
         WHERE id = ? AND workspace_id = ?`,
      )
      .bind(
        input.ok ? "CONNECTED" : "ERROR",
        testedAt,
        input.connectorId,
        input.workspaceId,
      ),
  ]);

  return {
    message: input.message,
    ok: input.ok,
    responseTimeMs: input.responseTimeMs,
    testedAt,
  };
}

export async function updateWorkspaceMission(input: {
  mission: UpdateMissionInput;
  missionId: string;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const existing = await database
    .prepare(
      `SELECT m.*
       FROM missions m
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND m.id = ?
       LIMIT 1`,
    )
    .bind(input.workspaceId, input.missionId)
    .first<{
      objective: string;
      project_id: string;
      research_depth: string;
      scope_json: string;
      status: string;
      title: string;
    }>();
  if (!existing) {
    return null;
  }

  if (input.mission.projectId) {
    const project = await database
      .prepare(
        `SELECT id FROM projects
         WHERE id = ? AND workspace_id = ? AND status = 'ACTIVE'`,
      )
      .bind(input.mission.projectId, input.workspaceId)
      .first<{ id: string }>();
    if (!project) {
      throw new Error("PROJECT_NOT_FOUND");
    }
  }

  const now = new Date().toISOString();
  await database.batch([
    database
      .prepare(
        `UPDATE missions
         SET project_id = ?, title = ?, objective = ?, scope_json = ?,
             status = ?, research_depth = ?, updated_at = ?
         WHERE id = ?`,
      )
      .bind(
        input.mission.projectId ?? existing.project_id,
        input.mission.title ?? existing.title,
        input.mission.objective ?? existing.objective,
        JSON.stringify(input.mission.scope ?? JSON.parse(existing.scope_json)),
        input.mission.status ?? existing.status,
        input.mission.researchDepth ?? existing.research_depth,
        now,
        input.missionId,
      ),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
         VALUES (?, ?, ?, 'MISSION_UPDATED', 'MISSION', ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        input.missionId,
        JSON.stringify(input.mission),
        crypto.randomUUID(),
        now,
      ),
  ]);

  return { id: input.missionId };
}

export async function assignWorkspaceMissionSource(input: {
  connectorId: string;
  exclusionRules: string[];
  inclusionRules: string[];
  missionId: string;
  priority: number;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const scope = await database
    .prepare(
      `SELECT m.id AS mission_id, sc.id AS connector_id
       FROM missions m
       INNER JOIN projects p ON p.id = m.project_id
       INNER JOIN source_connectors sc ON sc.workspace_id = p.workspace_id
       WHERE p.workspace_id = ? AND m.id = ? AND sc.id = ?
       LIMIT 1`,
    )
    .bind(input.workspaceId, input.missionId, input.connectorId)
    .first<{ connector_id: string; mission_id: string }>();
  if (!scope) {
    return null;
  }

  const now = new Date().toISOString();
  await database
    .prepare(
      `INSERT INTO mission_sources
        (mission_id, source_connector_id, priority, inclusion_rules_json,
         exclusion_rules_json, created_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(mission_id, source_connector_id) DO UPDATE SET
         priority = excluded.priority,
         inclusion_rules_json = excluded.inclusion_rules_json,
         exclusion_rules_json = excluded.exclusion_rules_json`,
    )
    .bind(
      input.missionId,
      input.connectorId,
      input.priority,
      JSON.stringify(input.inclusionRules),
      JSON.stringify(input.exclusionRules),
      now,
    )
    .run();

  return { connectorId: input.connectorId, missionId: input.missionId };
}

export async function removeWorkspaceMissionSource(input: {
  connectorId: string;
  missionId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `DELETE FROM mission_sources
       WHERE mission_id IN (
         SELECT m.id
         FROM missions m
         INNER JOIN projects p ON p.id = m.project_id
         WHERE p.workspace_id = ? AND m.id = ?
       )
       AND source_connector_id = ?`,
    )
    .bind(input.workspaceId, input.missionId, input.connectorId)
    .run();

  return result.success;
}
