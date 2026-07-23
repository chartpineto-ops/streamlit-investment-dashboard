import { getDatabase } from "@/server/db/client";
import {
  type ConnectorStatus as ConnectorStatusType,
  type ConnectorType,
  MissionStatus,
  type MissionStatus as MissionStatusType,
  type MonitoringMode,
  type ResearchDepth,
} from "@/shared/domain";
import type { CreateMissionInput } from "@/shared/schemas/mission";
import type { MissionListOptions } from "@/server/repositories/mission-scope";

export {
  missionScopeWhere,
  type MissionListOptions,
} from "@/server/repositories/mission-scope";

type MissionJoinRow = {
  connector_id: string | null;
  connector_name: string | null;
  connector_status: ConnectorStatusType | null;
  connector_type: ConnectorType | null;
  created_at: string;
  creator_id: string;
  creator_name: string;
  id: string;
  monitoring_interval: number | null;
  monitoring_mode: MonitoringMode;
  objective: string;
  priority: number | null;
  project_id: string;
  project_name: string;
  research_depth: ResearchDepth;
  scope_json: string;
  status: MissionStatusType;
  title: string;
  updated_at: string;
};

type MissionRecord = {
  _count: {
    insights: number;
    researchRuns: number;
  };
  createdAt: Date;
  createdBy: {
    id: string;
    name: string;
  };
  id: string;
  monitoringInterval: number | null;
  monitoringMode: MonitoringMode;
  objective: string;
  project: {
    id: string;
    name: string;
  };
  researchDepth: ResearchDepth;
  scope: unknown;
  sources: {
    sourceConnector: {
      id: string;
      name: string;
      status: ConnectorStatusType;
      type: ConnectorType;
    };
  }[];
  status: MissionStatusType;
  title: string;
  updatedAt: Date;
};

function rowsToMissions(rows: MissionJoinRow[]): MissionRecord[] {
  const missionsById = new Map<string, MissionRecord>();

  for (const row of rows) {
    let mission = missionsById.get(row.id);
    if (!mission) {
      mission = {
        _count: {
          insights: 0,
          researchRuns: 0,
        },
        createdAt: new Date(row.created_at),
        createdBy: {
          id: row.creator_id,
          name: row.creator_name,
        },
        id: row.id,
        monitoringInterval: row.monitoring_interval,
        monitoringMode: row.monitoring_mode,
        objective: row.objective,
        project: {
          id: row.project_id,
          name: row.project_name,
        },
        researchDepth: row.research_depth,
        scope: JSON.parse(row.scope_json),
        sources: [],
        status: row.status,
        title: row.title,
        updatedAt: new Date(row.updated_at),
      };
      missionsById.set(row.id, mission);
    }

    if (
      row.connector_id &&
      row.connector_name &&
      row.connector_status &&
      row.connector_type
    ) {
      mission.sources.push({
        sourceConnector: {
          id: row.connector_id,
          name: row.connector_name,
          status: row.connector_status,
          type: row.connector_type,
        },
      });
    }
  }

  return [...missionsById.values()];
}

function missionSelectSql(whereClause: string) {
  return `SELECT
    m.id,
    m.title,
    m.objective,
    m.scope_json,
    m.status,
    m.research_depth,
    m.monitoring_mode,
    m.monitoring_interval,
    m.created_at,
    m.updated_at,
    p.id AS project_id,
    p.name AS project_name,
    u.id AS creator_id,
    u.name AS creator_name,
    sc.id AS connector_id,
    sc.name AS connector_name,
    sc.type AS connector_type,
    sc.status AS connector_status,
    ms.priority
  FROM missions m
  INNER JOIN projects p ON p.id = m.project_id
  INNER JOIN users u ON u.id = m.created_by_id
  LEFT JOIN mission_sources ms ON ms.mission_id = m.id
  LEFT JOIN source_connectors sc ON sc.id = ms.source_connector_id
  WHERE ${whereClause}
  ORDER BY m.updated_at DESC, m.title ASC, ms.priority DESC`;
}

export async function listMissions(
  workspaceId: string,
  options: MissionListOptions = {},
) {
  const database = await getDatabase();
  const conditions = ["p.workspace_id = ?"];
  const values: unknown[] = [workspaceId];

  if (options.projectId) {
    conditions.push("p.id = ?");
    values.push(options.projectId);
  }
  if (options.status) {
    conditions.push("m.status = ?");
    values.push(options.status);
  }

  const result = await database
    .prepare(missionSelectSql(conditions.join(" AND ")))
    .bind(...values)
    .all<MissionJoinRow>();

  return rowsToMissions(result.results);
}

export async function getMissionById(workspaceId: string, missionId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(missionSelectSql("p.workspace_id = ? AND m.id = ?"))
    .bind(workspaceId, missionId)
    .all<MissionJoinRow>();
  const mission = rowsToMissions(result.results)[0];

  if (!mission) {
    return null;
  }

  return {
    ...mission,
    _count: {
      claims: 0,
      evidence: 0,
      insights: 0,
      researchRuns: 0,
    },
    researchRuns: [],
  };
}

type ProjectRow = {
  created_at: string;
  description: string;
  id: string;
  mission_count: number;
  name: string;
  status: string;
  updated_at: string;
  workspace_id: string;
};

export async function listProjects(workspaceId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `SELECT
        p.id,
        p.workspace_id,
        p.name,
        p.description,
        p.status,
        p.created_at,
        p.updated_at,
        COUNT(m.id) AS mission_count
      FROM projects p
      LEFT JOIN missions m ON m.project_id = p.id
      WHERE p.workspace_id = ? AND p.status = 'ACTIVE'
      GROUP BY p.id
      ORDER BY p.name ASC`,
    )
    .bind(workspaceId)
    .all<ProjectRow>();

  return result.results.map((project) => ({
    _count: {
      missions: Number(project.mission_count),
    },
    createdAt: new Date(project.created_at),
    description: project.description,
    id: project.id,
    name: project.name,
    status: project.status,
    updatedAt: new Date(project.updated_at),
    workspaceId: project.workspace_id,
  }));
}

type ConnectorRow = {
  created_at: string;
  id: string;
  name: string;
  status: ConnectorStatusType;
  type: ConnectorType;
  updated_at: string;
  workspace_id: string;
};

export async function listConnectors(workspaceId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `SELECT id, workspace_id, name, type, status, created_at, updated_at
      FROM source_connectors
      WHERE workspace_id = ?
      ORDER BY status ASC, name ASC`,
    )
    .bind(workspaceId)
    .all<ConnectorRow>();

  return result.results.map((connector) => ({
    createdAt: new Date(connector.created_at),
    id: connector.id,
    name: connector.name,
    status: connector.status,
    type: connector.type,
    updatedAt: new Date(connector.updated_at),
    workspaceId: connector.workspace_id,
  }));
}

type WorkspaceSummaryRow = {
  active_mission_count: number;
  available_connector_count: number;
  connector_count: number;
  mission_count: number;
  project_count: number;
};

export async function getWorkspaceSummary(workspaceId: string) {
  const database = await getDatabase();
  const summary = await database
    .prepare(
      `SELECT
        (SELECT COUNT(*)
          FROM missions m
          INNER JOIN projects p ON p.id = m.project_id
          WHERE p.workspace_id = ?) AS mission_count,
        (SELECT COUNT(*)
          FROM missions m
          INNER JOIN projects p ON p.id = m.project_id
          WHERE p.workspace_id = ? AND m.status IN ('READY', 'ACTIVE')) AS active_mission_count,
        (SELECT COUNT(*) FROM projects
          WHERE workspace_id = ? AND status = 'ACTIVE') AS project_count,
        (SELECT COUNT(*) FROM source_connectors
          WHERE workspace_id = ? AND status = 'AVAILABLE') AS available_connector_count,
        (SELECT COUNT(*) FROM source_connectors
          WHERE workspace_id = ?) AS connector_count`,
    )
    .bind(workspaceId, workspaceId, workspaceId, workspaceId, workspaceId)
    .first<WorkspaceSummaryRow>();

  if (!summary) {
    throw new Error("WORKSPACE_SUMMARY_UNAVAILABLE");
  }

  return {
    activeMissionCount: Number(summary.active_mission_count),
    availableConnectorCount: Number(summary.available_connector_count),
    connectorCount: Number(summary.connector_count),
    missionCount: Number(summary.mission_count),
    projectCount: Number(summary.project_count),
  };
}

type ScopedCreateMissionInput = CreateMissionInput & {
  createdById: string;
  workspaceId: string;
};

export async function createMission(input: ScopedCreateMissionInput) {
  const database = await getDatabase();
  const connectorIds = [...new Set(input.connectorIds)];
  const project = await database
    .prepare(
      `SELECT id FROM projects
      WHERE id = ? AND workspace_id = ? AND status = 'ACTIVE'
      LIMIT 1`,
    )
    .bind(input.projectId, input.workspaceId)
    .first<{ id: string }>();

  if (!project) {
    throw new Error("PROJECT_NOT_FOUND");
  }

  const placeholders = connectorIds.map(() => "?").join(", ");
  const connectorResult = await database
    .prepare(
      `SELECT id FROM source_connectors
      WHERE workspace_id = ? AND id IN (${placeholders})`,
    )
    .bind(input.workspaceId, ...connectorIds)
    .all<{ id: string }>();

  if (connectorResult.results.length !== connectorIds.length) {
    throw new Error("CONNECTOR_NOT_FOUND");
  }

  const missionId = `mission-${crypto.randomUUID()}`;
  const now = new Date().toISOString();
  const monitoringInterval =
    input.monitoringMode === "MANUAL"
      ? null
      : input.monitoringMode === "HOURLY"
        ? 60
        : input.monitoringMode === "DAILY"
          ? 1440
          : 10080;
  const statements = [
    database
      .prepare(
        `INSERT INTO missions
          (id, project_id, title, objective, scope_json, status, research_depth,
           monitoring_mode, monitoring_interval, created_by_id, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        missionId,
        project.id,
        input.title,
        input.objective,
        JSON.stringify({
          focusAreas: input.focusAreas,
          regions: input.regions,
          timeHorizonMonths: input.timeHorizonMonths,
        }),
        MissionStatus.READY,
        input.researchDepth,
        input.monitoringMode,
        monitoringInterval,
        input.createdById,
        now,
        now,
      ),
    ...connectorIds.map((sourceConnectorId, index) =>
      database
        .prepare(
          `INSERT INTO mission_sources
            (mission_id, source_connector_id, priority) VALUES (?, ?, ?)`,
        )
        .bind(missionId, sourceConnectorId, 100 - index),
    ),
  ];

  await database.batch(statements);

  return {
    id: missionId,
  };
}
