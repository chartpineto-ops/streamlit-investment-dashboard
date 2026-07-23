import {
  index,
  integer,
  primaryKey,
  sqliteTable,
  text,
  uniqueIndex,
} from "drizzle-orm/sqlite-core";

export const workspaces = sqliteTable(
  "workspaces",
  {
    createdAt: text("created_at").notNull(),
    id: text("id").primaryKey(),
    name: text("name").notNull(),
    updatedAt: text("updated_at").notNull(),
  },
  (table) => [index("workspaces_name_idx").on(table.name)],
);

export const users = sqliteTable(
  "users",
  {
    createdAt: text("created_at").notNull(),
    email: text("email").notNull(),
    id: text("id").primaryKey(),
    name: text("name").notNull(),
    role: text("role").notNull(),
    updatedAt: text("updated_at").notNull(),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
  },
  (table) => [
    uniqueIndex("users_email_unique").on(table.email),
    index("users_workspace_role_idx").on(table.workspaceId, table.role),
  ],
);

export const projects = sqliteTable(
  "projects",
  {
    createdAt: text("created_at").notNull(),
    description: text("description").notNull(),
    id: text("id").primaryKey(),
    name: text("name").notNull(),
    status: text("status").notNull(),
    updatedAt: text("updated_at").notNull(),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
  },
  (table) => [
    uniqueIndex("projects_workspace_name_unique").on(
      table.workspaceId,
      table.name,
    ),
    index("projects_workspace_status_idx").on(table.workspaceId, table.status),
  ],
);

export const sourceConnectors = sqliteTable(
  "source_connectors",
  {
    createdAt: text("created_at").notNull(),
    id: text("id").primaryKey(),
    name: text("name").notNull(),
    status: text("status").notNull(),
    type: text("type").notNull(),
    updatedAt: text("updated_at").notNull(),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
  },
  (table) => [
    uniqueIndex("source_connectors_workspace_name_unique").on(
      table.workspaceId,
      table.name,
    ),
    index("source_connectors_workspace_type_status_idx").on(
      table.workspaceId,
      table.type,
      table.status,
    ),
  ],
);

export const missions = sqliteTable(
  "missions",
  {
    createdAt: text("created_at").notNull(),
    createdById: text("created_by_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    id: text("id").primaryKey(),
    monitoringInterval: integer("monitoring_interval"),
    monitoringMode: text("monitoring_mode").notNull(),
    objective: text("objective").notNull(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    researchDepth: text("research_depth").notNull(),
    scopeJson: text("scope_json").notNull(),
    status: text("status").notNull(),
    title: text("title").notNull(),
    updatedAt: text("updated_at").notNull(),
  },
  (table) => [
    index("missions_project_status_idx").on(table.projectId, table.status),
    index("missions_created_by_idx").on(table.createdById),
    index("missions_updated_at_idx").on(table.updatedAt),
  ],
);

export const missionSources = sqliteTable(
  "mission_sources",
  {
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    priority: integer("priority").notNull().default(50),
    sourceConnectorId: text("source_connector_id")
      .notNull()
      .references(() => sourceConnectors.id, { onDelete: "cascade" }),
  },
  (table) => [
    primaryKey({ columns: [table.missionId, table.sourceConnectorId] }),
    index("mission_sources_connector_idx").on(table.sourceConnectorId),
  ],
);
