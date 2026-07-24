import {
  index,
  integer,
  primaryKey,
  real,
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

export const connectorConfigurations = sqliteTable("connector_configurations", {
  checkpointJson: text("checkpoint_json"),
  configurationJson: text("configuration_json").notNull(),
  connectorId: text("connector_id")
    .primaryKey()
    .references(() => sourceConnectors.id, { onDelete: "cascade" }),
  lastErrorAt: text("last_error_at"),
  lastSuccessfulSyncAt: text("last_successful_sync_at"),
  updatedAt: text("updated_at").notNull(),
});

export const researchRuns = sqliteTable(
  "research_runs",
  {
    completedAt: text("completed_at"),
    confidenceScore: real("confidence_score"),
    createdById: text("created_by_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    dataStatus: text("data_status").notNull(),
    documentsProcessed: integer("documents_processed").notNull().default(0),
    errorSummary: text("error_summary"),
    evidenceCreated: integer("evidence_created").notNull().default(0),
    id: text("id").primaryKey(),
    idempotencyKey: text("idempotency_key").notNull().unique(),
    insightsCreated: integer("insights_created").notNull().default(0),
    isDemo: integer("is_demo").notNull(),
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    modelProvider: text("model_provider").notNull(),
    progressPercent: integer("progress_percent").notNull().default(0),
    promptVersion: text("prompt_version").notNull(),
    sourcesScanned: integer("sources_scanned").notNull().default(0),
    startedAt: text("started_at").notNull(),
    status: text("status").notNull(),
    triggerType: text("trigger_type").notNull(),
  },
  (table) => [
    index("research_runs_mission_started_idx").on(
      table.missionId,
      table.startedAt,
    ),
  ],
);

export const runSteps = sqliteTable(
  "run_steps",
  {
    agentType: text("agent_type").notNull(),
    completedAt: text("completed_at"),
    durationMs: integer("duration_ms"),
    errorMessage: text("error_message"),
    id: text("id").primaryKey(),
    inputSummary: text("input_summary").notNull(),
    name: text("name").notNull(),
    outputSummary: text("output_summary"),
    progressPercent: integer("progress_percent").notNull().default(0),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    sequenceNumber: integer("sequence_number").notNull(),
    startedAt: text("started_at"),
    status: text("status").notNull(),
    tokenUsage: integer("token_usage").notNull().default(0),
    toolName: text("tool_name").notNull(),
  },
  (table) => [
    uniqueIndex("run_steps_run_sequence_unique").on(
      table.researchRunId,
      table.sequenceNumber,
    ),
    index("run_steps_run_status_idx").on(table.researchRunId, table.status),
  ],
);

export const runEvents = sqliteTable(
  "run_events",
  {
    createdAt: text("created_at").notNull(),
    eventType: text("event_type").notNull(),
    id: integer("id").primaryKey({ autoIncrement: true }),
    payloadJson: text("payload_json").notNull(),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    sequenceNumber: integer("sequence_number").notNull(),
  },
  (table) => [
    uniqueIndex("run_events_run_sequence_unique").on(
      table.researchRunId,
      table.sequenceNumber,
    ),
    index("run_events_run_sequence_idx").on(
      table.researchRunId,
      table.sequenceNumber,
    ),
  ],
);

export const sourceDocuments = sqliteTable(
  "source_documents",
  {
    author: text("author"),
    canonicalUrl: text("canonical_url").notNull(),
    connectorId: text("connector_id")
      .notNull()
      .references(() => sourceConnectors.id, { onDelete: "restrict" }),
    contentHash: text("content_hash").notNull(),
    dataStatus: text("data_status").notNull(),
    externalId: text("external_id").notNull(),
    id: text("id").primaryKey(),
    isDemo: integer("is_demo").notNull(),
    metadataJson: text("metadata_json").notNull(),
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    normalizedContent: text("normalized_content").notNull(),
    promptInjectionFlag: integer("prompt_injection_flag").notNull().default(0),
    publishedAt: text("published_at").notNull(),
    publisher: text("publisher").notNull(),
    rawContent: text("raw_content").notNull(),
    retrievedAt: text("retrieved_at").notNull(),
    sourceType: text("source_type").notNull(),
    title: text("title").notNull(),
    trustState: text("trust_state").notNull(),
    version: integer("version").notNull(),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
  },
  (table) => [
    uniqueIndex("source_documents_workspace_url_version_unique").on(
      table.workspaceId,
      table.canonicalUrl,
      table.version,
    ),
    index("source_documents_mission_retrieved_idx").on(
      table.missionId,
      table.retrievedAt,
    ),
    index("source_documents_content_hash_idx").on(table.contentHash),
  ],
);

export const evidence = sqliteTable(
  "evidence",
  {
    confidenceScore: real("confidence_score").notNull(),
    contentHash: text("content_hash").notNull(),
    contextText: text("context_text").notNull(),
    dataStatus: text("data_status").notNull(),
    entitiesJson: text("entities_json").notNull(),
    eventDate: text("event_date"),
    evidenceType: text("evidence_type").notNull(),
    excerpt: text("excerpt").notNull(),
    extractedAt: text("extracted_at").notNull(),
    id: text("id").primaryKey(),
    isDemo: integer("is_demo").notNull(),
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    normalizedClaim: text("normalized_claim").notNull(),
    noveltyScore: real("novelty_score").notNull(),
    relationship: text("relationship").notNull(),
    relevanceScore: real("relevance_score").notNull(),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    sourceDocumentId: text("source_document_id")
      .notNull()
      .references(() => sourceDocuments.id, { onDelete: "cascade" }),
    sourceQualityScore: real("source_quality_score").notNull(),
    topicsJson: text("topics_json").notNull(),
    validationStatus: text("validation_status").notNull(),
  },
  (table) => [
    uniqueIndex("evidence_document_hash_unique").on(
      table.sourceDocumentId,
      table.contentHash,
    ),
    index("evidence_mission_extracted_idx").on(
      table.missionId,
      table.extractedAt,
    ),
    index("evidence_validation_idx").on(
      table.missionId,
      table.validationStatus,
    ),
  ],
);

export const claims = sqliteTable(
  "claims",
  {
    calculationFactorsJson: text("calculation_factors_json").notNull(),
    claimType: text("claim_type").notNull(),
    confidenceScore: real("confidence_score").notNull(),
    dataStatus: text("data_status").notNull(),
    firstObservedAt: text("first_observed_at").notNull(),
    id: text("id").primaryKey(),
    isDemo: integer("is_demo").notNull(),
    lastObservedAt: text("last_observed_at").notNull(),
    materialityScore: real("materiality_score").notNull(),
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    statement: text("statement").notNull(),
    status: text("status").notNull(),
  },
  (table) => [
    uniqueIndex("claims_mission_statement_unique").on(
      table.missionId,
      table.statement,
    ),
    index("claims_mission_materiality_idx").on(
      table.missionId,
      table.materialityScore,
    ),
  ],
);

export const claimEvidence = sqliteTable(
  "claim_evidence",
  {
    claimId: text("claim_id")
      .notNull()
      .references(() => claims.id, { onDelete: "cascade" }),
    evidenceId: text("evidence_id")
      .notNull()
      .references(() => evidence.id, { onDelete: "cascade" }),
    relationship: text("relationship").notNull(),
    supportStrength: real("support_strength").notNull(),
  },
  (table) => [
    primaryKey({ columns: [table.claimId, table.evidenceId] }),
    index("claim_evidence_evidence_idx").on(table.evidenceId),
  ],
);

export const insights = sqliteTable(
  "insights",
  {
    assumptionsJson: text("assumptions_json").notNull(),
    calculationRefsJson: text("calculation_refs_json").notNull(),
    category: text("category").notNull(),
    confidenceScore: real("confidence_score").notNull(),
    createdAt: text("created_at").notNull(),
    dataStatus: text("data_status").notNull(),
    id: text("id").primaryKey(),
    isDemo: integer("is_demo").notNull(),
    materialityScore: real("materiality_score").notNull(),
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    noveltyScore: real("novelty_score").notNull(),
    owner: text("owner").notNull(),
    recommendedAction: text("recommended_action").notNull(),
    researchRunId: text("research_run_id")
      .notNull()
      .references(() => researchRuns.id, { onDelete: "cascade" }),
    severity: text("severity").notNull(),
    status: text("status").notNull(),
    summary: text("summary").notNull(),
    title: text("title").notNull(),
    uncertaintyNote: text("uncertainty_note").notNull(),
    updatedAt: text("updated_at").notNull(),
  },
  (table) => [
    index("insights_mission_materiality_idx").on(
      table.missionId,
      table.materialityScore,
    ),
  ],
);

export const insightClaims = sqliteTable(
  "insight_claims",
  {
    claimId: text("claim_id")
      .notNull()
      .references(() => claims.id, { onDelete: "cascade" }),
    importance: integer("importance").notNull(),
    insightId: text("insight_id")
      .notNull()
      .references(() => insights.id, { onDelete: "cascade" }),
  },
  (table) => [primaryKey({ columns: [table.insightId, table.claimId] })],
);

export const monitors = sqliteTable(
  "monitors",
  {
    alertCooldownMinutes: integer("alert_cooldown_minutes").notNull(),
    contradictionAlerts: integer("contradiction_alerts").notNull(),
    entityWatchlistJson: text("entity_watchlist_json").notNull(),
    id: text("id").primaryKey(),
    lastCheckedAt: text("last_checked_at"),
    materialityThreshold: real("materiality_threshold").notNull(),
    minimumConfidence: real("minimum_confidence").notNull(),
    missionId: text("mission_id")
      .notNull()
      .unique()
      .references(() => missions.id, { onDelete: "cascade" }),
    nextCheckAt: text("next_check_at"),
    requiredSourceCount: integer("required_source_count").notNull(),
    schedule: text("schedule").notNull(),
    sourceFailureAlerts: integer("source_failure_alerts").notNull(),
    status: text("status").notNull(),
    topicAllowlistJson: text("topic_allowlist_json").notNull(),
    topicBlocklistJson: text("topic_blocklist_json").notNull(),
    updatedAt: text("updated_at").notNull(),
  },
  (table) => [
    index("monitors_status_next_check_idx").on(table.status, table.nextCheckAt),
  ],
);

export const alerts = sqliteTable(
  "alerts",
  {
    alertType: text("alert_type").notNull(),
    createdAt: text("created_at").notNull(),
    deliveredAt: text("delivered_at"),
    id: text("id").primaryKey(),
    insightId: text("insight_id").references(() => insights.id, {
      onDelete: "set null",
    }),
    materialityScore: real("materiality_score").notNull(),
    monitorId: text("monitor_id")
      .notNull()
      .references(() => monitors.id, { onDelete: "cascade" }),
    status: text("status").notNull(),
    summary: text("summary").notNull(),
    title: text("title").notNull(),
  },
  (table) => [
    index("alerts_monitor_created_idx").on(table.monitorId, table.createdAt),
  ],
);

export const reports = sqliteTable(
  "reports",
  {
    content: text("content").notNull(),
    dataStatus: text("data_status").notNull(),
    generatedAt: text("generated_at").notNull(),
    generatedById: text("generated_by_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    id: text("id").primaryKey(),
    isDemo: integer("is_demo").notNull(),
    missionId: text("mission_id")
      .notNull()
      .references(() => missions.id, { onDelete: "cascade" }),
    researchRunId: text("research_run_id").references(() => researchRuns.id, {
      onDelete: "set null",
    }),
    status: text("status").notNull(),
    title: text("title").notNull(),
    type: text("type").notNull(),
  },
  (table) => [
    index("reports_mission_generated_idx").on(
      table.missionId,
      table.generatedAt,
    ),
  ],
);

export const agentDefinitions = sqliteTable(
  "agent_definitions",
  {
    agentType: text("agent_type").notNull(),
    allowedToolsJson: text("allowed_tools_json").notNull(),
    id: text("id").primaryKey(),
    model: text("model").notNull(),
    name: text("name").notNull(),
    outputSchema: text("output_schema").notNull(),
    promptName: text("prompt_name").notNull(),
    promptVersion: text("prompt_version").notNull(),
    purpose: text("purpose").notNull(),
    status: text("status").notNull(),
    updatedAt: text("updated_at").notNull(),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
  },
  (table) => [
    uniqueIndex("agent_definitions_workspace_type_unique").on(
      table.workspaceId,
      table.agentType,
    ),
  ],
);

export const auditLogs = sqliteTable(
  "audit_logs",
  {
    action: text("action").notNull(),
    createdAt: text("created_at").notNull(),
    detailsJson: text("details_json").notNull(),
    entityId: text("entity_id").notNull(),
    entityType: text("entity_type").notNull(),
    id: text("id").primaryKey(),
    requestId: text("request_id").notNull(),
    userId: text("user_id").references(() => users.id, {
      onDelete: "set null",
    }),
    workspaceId: text("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
  },
  (table) => [
    index("audit_logs_workspace_created_idx").on(
      table.workspaceId,
      table.createdAt,
    ),
  ],
);

export const questionHistory = sqliteTable("question_history", {
  answer: text("answer").notNull(),
  confidenceScore: real("confidence_score").notNull(),
  createdAt: text("created_at").notNull(),
  evidenceIdsJson: text("evidence_ids_json").notNull(),
  id: text("id").primaryKey(),
  limitations: text("limitations").notNull(),
  missionId: text("mission_id")
    .notNull()
    .references(() => missions.id, { onDelete: "cascade" }),
  question: text("question").notNull(),
  userId: text("user_id")
    .notNull()
    .references(() => users.id, { onDelete: "restrict" }),
  workspaceId: text("workspace_id")
    .notNull()
    .references(() => workspaces.id, { onDelete: "cascade" }),
});
