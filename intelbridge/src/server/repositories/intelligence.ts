import { getDatabase } from "@/server/db/client";
import { generateGroundedAnswer } from "@/server/agents/provider";
import { calculateMateriality } from "@/shared/materiality";

export { calculateMateriality };

function parseJson<T>(value: string, fallback: T): T {
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

function asDate(value: string | null) {
  return value ? new Date(value) : null;
}

async function hashText(value: string) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function inferTopics(value: string) {
  const normalized = value.toLowerCase();
  return [
    ["analytics", /analytics|diagnostic|metric|benchmark/],
    ["governance", /governance|security|policy|retention|audit/],
    ["pricing", /pricing|price|fee|cost|overage|package/],
    ["developer-platform", /api|sdk|trace|deployment|checkpoint/],
    ["adoption", /adoption|onboarding|implementation|procurement/],
  ]
    .filter(([, pattern]) => (pattern as RegExp).test(normalized))
    .map(([topic]) => topic as string)
    .slice(0, 3);
}

type SourceRow = {
  author: string | null;
  canonical_url: string;
  connector_name: string;
  connector_type: string;
  content_hash: string;
  data_status: string;
  evidence_count: number;
  id: string;
  is_demo: number;
  mission_id: string;
  mission_title: string;
  prompt_injection_flag: number;
  published_at: string;
  publisher: string;
  retrieved_at: string;
  source_type: string;
  title: string;
  trust_state: string;
  version: number;
};

export async function listSourceDocuments(
  workspaceId: string,
  options: { missionId?: string; query?: string } = {},
) {
  const database = await getDatabase();
  const conditions = ["sd.workspace_id = ?"];
  const values: unknown[] = [workspaceId];

  if (options.missionId) {
    conditions.push("sd.mission_id = ?");
    values.push(options.missionId);
  }
  if (options.query) {
    conditions.push(
      "(sd.title LIKE ? OR sd.publisher LIKE ? OR sd.normalized_content LIKE ?)",
    );
    const query = `%${options.query}%`;
    values.push(query, query, query);
  }

  const result = await database
    .prepare(
      `SELECT
        sd.id,
        sd.mission_id,
        sd.canonical_url,
        sd.title,
        sd.author,
        sd.publisher,
        sd.source_type,
        sd.published_at,
        sd.retrieved_at,
        sd.content_hash,
        sd.version,
        sd.trust_state,
        sd.prompt_injection_flag,
        sd.data_status,
        sd.is_demo,
        m.title AS mission_title,
        sc.name AS connector_name,
        sc.type AS connector_type,
        COUNT(e.id) AS evidence_count
      FROM source_documents sd
      INNER JOIN missions m ON m.id = sd.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      INNER JOIN source_connectors sc ON sc.id = sd.connector_id
      LEFT JOIN evidence e ON e.source_document_id = sd.id
      WHERE ${conditions.join(" AND ")} AND p.workspace_id = ?
      GROUP BY sd.id
      ORDER BY sd.retrieved_at DESC, sd.title ASC`,
    )
    .bind(...values, workspaceId)
    .all<SourceRow>();

  return result.results.map((row) => ({
    author: row.author,
    canonicalUrl: row.canonical_url,
    connectorName: row.connector_name,
    connectorType: row.connector_type,
    contentHash: row.content_hash,
    dataStatus: row.data_status,
    evidenceCount: Number(row.evidence_count),
    id: row.id,
    isDemo: Boolean(row.is_demo),
    missionId: row.mission_id,
    missionTitle: row.mission_title,
    promptInjectionFlag: Boolean(row.prompt_injection_flag),
    publishedAt: new Date(row.published_at),
    publisher: row.publisher,
    retrievedAt: new Date(row.retrieved_at),
    sourceType: row.source_type,
    title: row.title,
    trustState: row.trust_state,
    version: Number(row.version),
  }));
}

type EvidenceRow = {
  canonical_url: string;
  claim_id: string | null;
  claim_statement: string | null;
  confidence_score: number;
  context_text: string;
  data_status: string;
  document_title: string;
  evidence_type: string;
  excerpt: string;
  extracted_at: string;
  id: string;
  is_demo: number;
  mission_id: string;
  mission_title: string;
  novelty_score: number;
  published_at: string;
  publisher: string;
  relationship: string;
  relevance_score: number;
  retrieved_at: string;
  source_quality_score: number;
  source_type: string;
  topics_json: string;
  validation_status: string;
  version: number;
};

export async function listEvidence(
  workspaceId: string,
  options: {
    missionId?: string;
    query?: string;
    selectedId?: string;
    status?: string;
  } = {},
) {
  const database = await getDatabase();
  const conditions = ["p.workspace_id = ?"];
  const values: unknown[] = [workspaceId];

  if (options.missionId) {
    conditions.push("e.mission_id = ?");
    values.push(options.missionId);
  }
  if (options.status) {
    conditions.push("e.validation_status = ?");
    values.push(options.status);
  }
  if (options.query) {
    conditions.push(
      "(e.excerpt LIKE ? OR e.normalized_claim LIKE ? OR sd.publisher LIKE ?)",
    );
    const query = `%${options.query}%`;
    values.push(query, query, query);
  }

  const result = await database
    .prepare(
      `SELECT
        e.id,
        e.mission_id,
        e.evidence_type,
        e.excerpt,
        e.context_text,
        e.topics_json,
        e.extracted_at,
        e.relevance_score,
        e.source_quality_score,
        e.novelty_score,
        e.confidence_score,
        e.validation_status,
        e.relationship,
        e.data_status,
        e.is_demo,
        sd.title AS document_title,
        sd.publisher,
        sd.source_type,
        sd.canonical_url,
        sd.published_at,
        sd.retrieved_at,
        sd.version,
        m.title AS mission_title,
        c.id AS claim_id,
        c.statement AS claim_statement
      FROM evidence e
      INNER JOIN source_documents sd ON sd.id = e.source_document_id
      INNER JOIN missions m ON m.id = e.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      LEFT JOIN claim_evidence ce ON ce.evidence_id = e.id
      LEFT JOIN claims c ON c.id = ce.claim_id
      WHERE ${conditions.join(" AND ")}
      ORDER BY e.extracted_at DESC, e.confidence_score DESC, e.id ASC`,
    )
    .bind(...values)
    .all<EvidenceRow>();

  const records = result.results.map((row) => ({
    canonicalUrl: row.canonical_url,
    claimId: row.claim_id,
    claimStatement: row.claim_statement,
    confidenceScore: Number(row.confidence_score),
    contextText: row.context_text,
    dataStatus: row.data_status,
    documentTitle: row.document_title,
    evidenceType: row.evidence_type,
    excerpt: row.excerpt,
    extractedAt: new Date(row.extracted_at),
    id: row.id,
    isDemo: Boolean(row.is_demo),
    missionId: row.mission_id,
    missionTitle: row.mission_title,
    noveltyScore: Number(row.novelty_score),
    publishedAt: new Date(row.published_at),
    publisher: row.publisher,
    relationship: row.relationship,
    relevanceScore: Number(row.relevance_score),
    retrievedAt: new Date(row.retrieved_at),
    sourceQualityScore: Number(row.source_quality_score),
    sourceType: row.source_type,
    topics: parseJson<string[]>(row.topics_json, []),
    validationStatus: row.validation_status,
    version: Number(row.version),
  }));

  return {
    records,
    selected:
      records.find((record) => record.id === options.selectedId) ?? null,
  };
}

type InsightRow = {
  assumptions_json: string;
  calculation_refs_json: string;
  category: string;
  claim_count: number;
  confidence_score: number;
  created_at: string;
  data_status: string;
  id: string;
  is_demo: number;
  materiality_score: number;
  mission_id: string;
  mission_title: string;
  novelty_score: number;
  owner: string;
  recommended_action: string;
  research_run_id: string;
  severity: string;
  source_count: number;
  status: string;
  summary: string;
  title: string;
  uncertainty_note: string;
  updated_at: string;
};

export async function listInsights(
  workspaceId: string,
  options: { category?: string; missionId?: string; selectedId?: string } = {},
) {
  const database = await getDatabase();
  const conditions = ["p.workspace_id = ?"];
  const values: unknown[] = [workspaceId];

  if (options.missionId) {
    conditions.push("i.mission_id = ?");
    values.push(options.missionId);
  }
  if (options.category) {
    conditions.push("i.category = ?");
    values.push(options.category);
  }

  const result = await database
    .prepare(
      `SELECT
        i.id,
        i.mission_id,
        i.research_run_id,
        i.title,
        i.summary,
        i.category,
        i.severity,
        i.confidence_score,
        i.materiality_score,
        i.novelty_score,
        i.status,
        i.recommended_action,
        i.owner,
        i.uncertainty_note,
        i.assumptions_json,
        i.calculation_refs_json,
        i.created_at,
        i.updated_at,
        i.data_status,
        i.is_demo,
        m.title AS mission_title,
        COUNT(DISTINCT ic.claim_id) AS claim_count,
        COUNT(DISTINCT sd.id) AS source_count
      FROM insights i
      INNER JOIN missions m ON m.id = i.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      LEFT JOIN insight_claims ic ON ic.insight_id = i.id
      LEFT JOIN claim_evidence ce ON ce.claim_id = ic.claim_id
      LEFT JOIN evidence e ON e.id = ce.evidence_id
      LEFT JOIN source_documents sd ON sd.id = e.source_document_id
      WHERE ${conditions.join(" AND ")}
      GROUP BY i.id
      ORDER BY i.materiality_score DESC, i.created_at DESC`,
    )
    .bind(...values)
    .all<InsightRow>();

  const records = result.results.map((row) => ({
    assumptions: parseJson<string[]>(row.assumptions_json, []),
    calculationReferences: parseJson<string[]>(row.calculation_refs_json, []),
    category: row.category,
    claimCount: Number(row.claim_count),
    confidenceScore: Number(row.confidence_score),
    createdAt: new Date(row.created_at),
    dataStatus: row.data_status,
    id: row.id,
    isDemo: Boolean(row.is_demo),
    materialityScore: Number(row.materiality_score),
    missionId: row.mission_id,
    missionTitle: row.mission_title,
    noveltyScore: Number(row.novelty_score),
    owner: row.owner,
    recommendedAction: row.recommended_action,
    researchRunId: row.research_run_id,
    severity: row.severity,
    sourceCount: Number(row.source_count),
    status: row.status,
    summary: row.summary,
    title: row.title,
    uncertaintyNote: row.uncertainty_note,
    updatedAt: new Date(row.updated_at),
  }));
  const selected =
    records.find((record) => record.id === options.selectedId) ?? null;

  if (!selected) {
    return { records, selected: null, selectedClaims: [] };
  }

  const claims = await database
    .prepare(
      `SELECT
        c.id,
        c.statement,
        c.status,
        c.confidence_score,
        c.materiality_score,
        ic.importance,
        COUNT(DISTINCT CASE WHEN ce.relationship = 'supports' THEN e.id END) AS supporting_count,
        COUNT(DISTINCT CASE WHEN ce.relationship = 'contradicts' THEN e.id END) AS contradicting_count
      FROM insight_claims ic
      INNER JOIN claims c ON c.id = ic.claim_id
      LEFT JOIN claim_evidence ce ON ce.claim_id = c.id
      LEFT JOIN evidence e ON e.id = ce.evidence_id
      WHERE ic.insight_id = ?
      GROUP BY c.id
      ORDER BY ic.importance DESC`,
    )
    .bind(selected.id)
    .all<{
      confidence_score: number;
      contradicting_count: number;
      id: string;
      importance: number;
      materiality_score: number;
      statement: string;
      status: string;
      supporting_count: number;
    }>();

  return {
    records,
    selected,
    selectedClaims: claims.results.map((claim) => ({
      confidenceScore: Number(claim.confidence_score),
      contradictingCount: Number(claim.contradicting_count),
      id: claim.id,
      importance: Number(claim.importance),
      materialityScore: Number(claim.materiality_score),
      statement: claim.statement,
      status: claim.status,
      supportingCount: Number(claim.supporting_count),
    })),
  };
}

type MonitorRow = {
  alert_cooldown_minutes: number;
  contradiction_alerts: number;
  entity_watchlist_json: string;
  id: string;
  last_checked_at: string | null;
  materiality_threshold: number;
  minimum_confidence: number;
  mission_id: string;
  mission_title: string;
  next_check_at: string | null;
  required_source_count: number;
  schedule: string;
  source_failure_alerts: number;
  status: string;
  topic_allowlist_json: string;
  topic_blocklist_json: string;
  updated_at: string;
};

export async function listMonitors(workspaceId: string) {
  const database = await getDatabase();
  const monitors = await database
    .prepare(
      `SELECT
        mo.id,
        mo.mission_id,
        mo.status,
        mo.schedule,
        mo.materiality_threshold,
        mo.minimum_confidence,
        mo.required_source_count,
        mo.topic_allowlist_json,
        mo.topic_blocklist_json,
        mo.entity_watchlist_json,
        mo.alert_cooldown_minutes,
        mo.contradiction_alerts,
        mo.source_failure_alerts,
        mo.last_checked_at,
        mo.next_check_at,
        mo.updated_at,
        m.title AS mission_title
      FROM monitors mo
      INNER JOIN missions m ON m.id = mo.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ?
      ORDER BY mo.status ASC, mo.next_check_at ASC`,
    )
    .bind(workspaceId)
    .all<MonitorRow>();
  const alerts = await database
    .prepare(
      `SELECT
        a.id,
        a.monitor_id,
        a.insight_id,
        a.alert_type,
        a.title,
        a.summary,
        a.status,
        a.materiality_score,
        a.created_at,
        a.delivered_at,
        m.title AS mission_title
      FROM alerts a
      INNER JOIN monitors mo ON mo.id = a.monitor_id
      INNER JOIN missions m ON m.id = mo.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ?
      ORDER BY a.created_at DESC`,
    )
    .bind(workspaceId)
    .all<{
      alert_type: string;
      created_at: string;
      delivered_at: string | null;
      id: string;
      insight_id: string | null;
      materiality_score: number;
      mission_title: string;
      monitor_id: string;
      status: string;
      summary: string;
      title: string;
    }>();

  return {
    alerts: alerts.results.map((row) => ({
      alertType: row.alert_type,
      createdAt: new Date(row.created_at),
      deliveredAt: asDate(row.delivered_at),
      id: row.id,
      insightId: row.insight_id,
      materialityScore: Number(row.materiality_score),
      missionTitle: row.mission_title,
      monitorId: row.monitor_id,
      status: row.status,
      summary: row.summary,
      title: row.title,
    })),
    monitors: monitors.results.map((row) => ({
      alertCooldownMinutes: Number(row.alert_cooldown_minutes),
      contradictionAlerts: Boolean(row.contradiction_alerts),
      entityWatchlist: parseJson<string[]>(row.entity_watchlist_json, []),
      id: row.id,
      lastCheckedAt: asDate(row.last_checked_at),
      materialityThreshold: Number(row.materiality_threshold),
      minimumConfidence: Number(row.minimum_confidence),
      missionId: row.mission_id,
      missionTitle: row.mission_title,
      nextCheckAt: asDate(row.next_check_at),
      requiredSourceCount: Number(row.required_source_count),
      schedule: row.schedule,
      sourceFailureAlerts: Boolean(row.source_failure_alerts),
      status: row.status,
      topicAllowlist: parseJson<string[]>(row.topic_allowlist_json, []),
      topicBlocklist: parseJson<string[]>(row.topic_blocklist_json, []),
      updatedAt: new Date(row.updated_at),
    })),
  };
}

export async function listReports(workspaceId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `SELECT
        r.id,
        r.mission_id,
        r.research_run_id,
        r.type,
        r.status,
        r.title,
        r.generated_at,
        r.data_status,
        r.is_demo,
        m.title AS mission_title,
        u.name AS generated_by
      FROM reports r
      INNER JOIN missions m ON m.id = r.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      INNER JOIN users u ON u.id = r.generated_by_id
      WHERE p.workspace_id = ?
      ORDER BY r.generated_at DESC`,
    )
    .bind(workspaceId)
    .all<{
      data_status: string;
      generated_at: string;
      generated_by: string;
      id: string;
      is_demo: number;
      mission_id: string;
      mission_title: string;
      research_run_id: string | null;
      status: string;
      title: string;
      type: string;
    }>();

  return result.results.map((row) => ({
    dataStatus: row.data_status,
    generatedAt: new Date(row.generated_at),
    generatedBy: row.generated_by,
    id: row.id,
    isDemo: Boolean(row.is_demo),
    missionId: row.mission_id,
    missionTitle: row.mission_title,
    researchRunId: row.research_run_id,
    status: row.status,
    title: row.title,
    type: row.type,
  }));
}

export async function getReport(workspaceId: string, reportId: string) {
  const database = await getDatabase();
  const row = await database
    .prepare(
      `SELECT r.id, r.type, r.title, r.content, r.generated_at
      FROM reports r
      INNER JOIN missions m ON m.id = r.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND r.id = ?
      LIMIT 1`,
    )
    .bind(workspaceId, reportId)
    .first<{
      content: string;
      generated_at: string;
      id: string;
      title: string;
      type: string;
    }>();

  return row
    ? {
        content: row.content,
        generatedAt: new Date(row.generated_at),
        id: row.id,
        title: row.title,
        type: row.type,
      }
    : null;
}

export async function listAgents(workspaceId: string) {
  const database = await getDatabase();
  const result = await database
    .prepare(
      `SELECT
        id,
        name,
        agent_type,
        purpose,
        status,
        prompt_name,
        prompt_version,
        model,
        allowed_tools_json,
        output_schema,
        updated_at
      FROM agent_definitions
      WHERE workspace_id = ?
      ORDER BY id ASC`,
    )
    .bind(workspaceId)
    .all<{
      agent_type: string;
      allowed_tools_json: string;
      id: string;
      model: string;
      name: string;
      output_schema: string;
      prompt_name: string;
      prompt_version: string;
      purpose: string;
      status: string;
      updated_at: string;
    }>();

  return result.results.map((row) => ({
    agentType: row.agent_type,
    allowedTools: parseJson<string[]>(row.allowed_tools_json, []),
    id: row.id,
    model: row.model,
    name: row.name,
    outputSchema: row.output_schema,
    promptName: row.prompt_name,
    promptVersion: row.prompt_version,
    purpose: row.purpose,
    status: row.status,
    updatedAt: new Date(row.updated_at),
  }));
}

export async function getMissionIntelligence(
  workspaceId: string,
  missionId: string,
) {
  const database = await getDatabase();
  const latestRun = await database
    .prepare(
      `SELECT rr.*
      FROM research_runs rr
      INNER JOIN missions m ON m.id = rr.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND rr.mission_id = ?
      ORDER BY rr.started_at DESC
      LIMIT 1`,
    )
    .bind(workspaceId, missionId)
    .first<RunRow>();

  const run = latestRun ? mapRun(latestRun) : null;
  const steps = run ? await getRunSteps(database, run.id) : [];
  const { records: insights } = await listInsights(workspaceId, { missionId });
  const { records: evidenceRecords } = await listEvidence(workspaceId, {
    missionId,
  });
  const sources = await listSourceDocuments(workspaceId, { missionId });

  const typeCounts = new Map<string, number>();
  const topicCounts = new Map<string, number>();
  for (const item of evidenceRecords) {
    typeCounts.set(
      item.evidenceType,
      (typeCounts.get(item.evidenceType) ?? 0) + 1,
    );
    for (const topic of item.topics) {
      topicCounts.set(topic, (topicCounts.get(topic) ?? 0) + 1);
    }
  }

  return {
    evidenceSnapshot: [...typeCounts.entries()]
      .map(([label, count]) => ({ count, label }))
      .sort((left, right) => right.count - left.count),
    evidenceTotal: evidenceRecords.length,
    highQualityEvidence: evidenceRecords.filter(
      (item) => item.confidenceScore >= 0.8 && item.sourceQualityScore >= 0.8,
    ).length,
    insights: insights.slice(0, 5),
    latestRun: run,
    sources: sources
      .sort((left, right) => right.evidenceCount - left.evidenceCount)
      .slice(0, 6),
    steps,
    topTopics: [...topicCounts.entries()]
      .map(([label, count]) => ({ count, label }))
      .sort((left, right) => right.count - left.count)
      .slice(0, 8),
  };
}

type RunRow = {
  completed_at: string | null;
  confidence_score: number | null;
  data_status: string;
  documents_processed: number;
  error_summary: string | null;
  evidence_created: number;
  id: string;
  insights_created: number;
  is_demo: number;
  mission_id: string;
  model_provider: string;
  progress_percent: number;
  prompt_version: string;
  sources_scanned: number;
  started_at: string;
  status: string;
  trigger_type: string;
};

function mapRun(row: RunRow) {
  return {
    completedAt: asDate(row.completed_at),
    confidenceScore:
      row.confidence_score === null ? null : Number(row.confidence_score),
    dataStatus: row.data_status,
    documentsProcessed: Number(row.documents_processed),
    errorSummary: row.error_summary,
    evidenceCreated: Number(row.evidence_created),
    id: row.id,
    insightsCreated: Number(row.insights_created),
    isDemo: Boolean(row.is_demo),
    missionId: row.mission_id,
    modelProvider: row.model_provider,
    progressPercent: Number(row.progress_percent),
    promptVersion: row.prompt_version,
    sourcesScanned: Number(row.sources_scanned),
    startedAt: new Date(row.started_at),
    status: row.status,
    triggerType: row.trigger_type,
  };
}

async function getRunSteps(
  database: Awaited<ReturnType<typeof getDatabase>>,
  runId: string,
) {
  const result = await database
    .prepare(
      `SELECT *
      FROM run_steps
      WHERE research_run_id = ?
      ORDER BY sequence_number ASC`,
    )
    .bind(runId)
    .all<{
      agent_type: string;
      completed_at: string | null;
      duration_ms: number | null;
      error_message: string | null;
      id: string;
      input_summary: string;
      name: string;
      output_summary: string | null;
      progress_percent: number;
      sequence_number: number;
      started_at: string | null;
      status: string;
      token_usage: number;
      tool_name: string;
    }>();

  return result.results.map((row) => ({
    agentType: row.agent_type,
    completedAt: asDate(row.completed_at),
    durationMs: row.duration_ms ? Number(row.duration_ms) : null,
    errorMessage: row.error_message,
    id: row.id,
    inputSummary: row.input_summary,
    name: row.name,
    outputSummary: row.output_summary,
    progressPercent: Number(row.progress_percent),
    sequenceNumber: Number(row.sequence_number),
    startedAt: asDate(row.started_at),
    status: row.status,
    tokenUsage: Number(row.token_usage),
    toolName: row.tool_name,
  }));
}

export async function getRun(workspaceId: string, runId: string) {
  const database = await getDatabase();
  const row = await database
    .prepare(
      `SELECT rr.*, m.title AS mission_title
      FROM research_runs rr
      INNER JOIN missions m ON m.id = rr.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND rr.id = ?
      LIMIT 1`,
    )
    .bind(workspaceId, runId)
    .first<RunRow & { mission_title: string }>();

  if (!row) {
    return null;
  }

  return {
    missionTitle: row.mission_title,
    run: mapRun(row),
    steps: await getRunSteps(database, runId),
  };
}

export async function getRunEvents(
  workspaceId: string,
  runId: string,
  afterSequence = 0,
) {
  const database = await getDatabase();
  const scopedRun = await database
    .prepare(
      `SELECT rr.id
      FROM research_runs rr
      INNER JOIN missions m ON m.id = rr.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND rr.id = ?
      LIMIT 1`,
    )
    .bind(workspaceId, runId)
    .first<{ id: string }>();

  if (!scopedRun) {
    return null;
  }

  const result = await database
    .prepare(
      `SELECT sequence_number, event_type, payload_json, created_at
      FROM run_events
      WHERE research_run_id = ? AND sequence_number > ?
      ORDER BY sequence_number ASC`,
    )
    .bind(runId, afterSequence)
    .all<{
      created_at: string;
      event_type: string;
      payload_json: string;
      sequence_number: number;
    }>();

  return result.results.map((row) => ({
    createdAt: row.created_at,
    payload: parseJson<Record<string, unknown>>(row.payload_json, {}),
    sequenceNumber: Number(row.sequence_number),
    type: row.event_type,
  }));
}

export async function createResearchRun(input: {
  idempotencyKey?: string;
  missionId: string;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const mission = await database
    .prepare(
      `SELECT m.id
      FROM missions m
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND m.id = ?
      LIMIT 1`,
    )
    .bind(input.workspaceId, input.missionId)
    .first<{ id: string }>();

  if (!mission) {
    throw new Error("MISSION_NOT_FOUND");
  }

  const idempotencyKey =
    input.idempotencyKey ?? `manual:${crypto.randomUUID()}`;
  const existingRun = await database
    .prepare(
      `SELECT rr.id, rr.data_status, rr.is_demo
       FROM research_runs rr
       INNER JOIN missions m ON m.id = rr.mission_id
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND rr.idempotency_key = ?
       LIMIT 1`,
    )
    .bind(input.workspaceId, idempotencyKey)
    .first<{ data_status: string; id: string; is_demo: number }>();

  if (existingRun) {
    return {
      created: false,
      dataStatus: existingRun.data_status,
      id: existingRun.id,
      isDemo: Boolean(existingRun.is_demo),
    };
  }

  const counts = await database
    .prepare(
      `SELECT
        (SELECT COUNT(*) FROM source_documents WHERE mission_id = ?) AS document_count,
        (SELECT COUNT(*) FROM evidence WHERE mission_id = ?) AS evidence_count,
        (SELECT COUNT(*) FROM insights WHERE mission_id = ?) AS insight_count,
        (SELECT MIN(is_demo) FROM source_documents WHERE mission_id = ?) AS min_demo,
        (SELECT MAX(is_demo) FROM source_documents WHERE mission_id = ?) AS max_demo`,
    )
    .bind(
      input.missionId,
      input.missionId,
      input.missionId,
      input.missionId,
      input.missionId,
    )
    .first<{
      document_count: number;
      evidence_count: number;
      insight_count: number;
      max_demo: number | null;
      min_demo: number | null;
    }>();
  const unprocessedDocuments = await database
    .prepare(
      `SELECT
        sd.id,
        sd.normalized_content,
        sd.data_status,
        sd.is_demo,
        sd.publisher,
        sd.source_type
      FROM source_documents sd
      WHERE sd.mission_id = ?
        AND sd.source_type != 'application/pdf'
        AND NOT EXISTS (
          SELECT 1 FROM evidence e WHERE e.source_document_id = sd.id
        )
      ORDER BY sd.retrieved_at ASC`,
    )
    .bind(input.missionId)
    .all<{
      data_status: string;
      id: string;
      is_demo: number;
      normalized_content: string;
      publisher: string;
      source_type: string;
    }>();

  const documentCount = Number(counts?.document_count ?? 0);
  const evidenceCount = Number(counts?.evidence_count ?? 0);
  const insightCount = Number(counts?.insight_count ?? 0);
  const allDemo =
    documentCount > 0 &&
    Number(counts?.min_demo) === 1 &&
    Number(counts?.max_demo) === 1;
  const mixed =
    documentCount > 0 &&
    counts?.min_demo !== null &&
    Number(counts?.min_demo) !== Number(counts?.max_demo);
  const dataStatus =
    documentCount === 0
      ? "unavailable"
      : allDemo
        ? "demo"
        : mixed
          ? "partial"
          : "live";
  const isDemo = allDemo ? 1 : 0;
  const runId = `run-${crypto.randomUUID()}`;
  const now = new Date();
  const completedAt = new Date(now.getTime() + 1_000).toISOString();
  const extractedEvidence = (
    await Promise.all(
      unprocessedDocuments.results.flatMap((document) =>
        document.normalized_content
          .split(/(?<=[.!?])\s+/)
          .map((excerpt) => excerpt.trim())
          .filter((excerpt) => excerpt.length >= 40)
          .slice(0, 3)
          .map(async (excerpt, index) => {
            const contentHash = await hashText(
              `${document.id}:${index}:${excerpt}`,
            );
            const factors = {
              confidence: 0.72,
              impact: 0.68,
              novelty: 0.75,
              relevance: 0.78,
              sourceQuality: 0.7,
              urgency: 0.62,
            };

            return {
              claimId: `claim-auto-${contentHash.slice(0, 24)}`,
              confidenceScore: factors.confidence,
              contentHash,
              contextText: document.normalized_content.slice(0, 5_000),
              dataStatus: document.data_status,
              evidenceId: `evidence-${crypto.randomUUID()}`,
              excerpt,
              isDemo: Number(document.is_demo),
              materialityScore: calculateMateriality(factors),
              publisher: document.publisher,
              sourceDocumentId: document.id,
              statement: excerpt,
              topics: inferTopics(excerpt),
            };
          }),
      ),
    )
  ).flat();
  const createdEvidenceCount = extractedEvidence.length;
  const totalEvidenceCount = evidenceCount + createdEvidenceCount;
  const confidence =
    totalEvidenceCount > 0
      ? Math.min(0.95, 0.62 + totalEvidenceCount * 0.006)
      : null;
  const steps = [
    ["PLANNER", "Mission planning", "plan_mission"],
    ["RETRIEVAL", "Source discovery and retrieval", "retrieve_sources"],
    ["EVIDENCE_EXTRACTION", "Evidence extraction", "extract_evidence"],
    ["VALIDATION", "Claim validation", "validate_claims"],
    ["SYNTHESIS", "Insight synthesis", "synthesize_insights"],
    ["REPORTING", "Report generation", "generate_report"],
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
        idempotencyKey,
        input.missionId,
        "MANUAL",
        "COMPLETED",
        now.toISOString(),
        completedAt,
        100,
        documentCount,
        documentCount,
        createdEvidenceCount,
        0,
        confidence,
        documentCount ? null : "NO_APPROVED_SOURCE_DOCUMENTS",
        "mock",
        "pipeline-v1.0.0",
        dataStatus,
        isDemo,
        input.userId,
      ),
    ...extractedEvidence.flatMap((item) => [
      database
        .prepare(
          `INSERT OR IGNORE INTO claims
            (id, mission_id, statement, claim_type, status, confidence_score,
             first_observed_at, last_observed_at, materiality_score,
             calculation_factors_json, data_status, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .bind(
          item.claimId,
          input.missionId,
          item.statement,
          "FACT",
          "SINGLE_SOURCE",
          item.confidenceScore,
          completedAt,
          completedAt,
          item.materialityScore,
          JSON.stringify({
            confidence: 0.72,
            impact: 0.68,
            novelty: 0.75,
            relevance: 0.78,
            sourceQuality: 0.7,
            urgency: 0.62,
          }),
          item.dataStatus,
          item.isDemo,
        ),
      database
        .prepare(
          `INSERT OR IGNORE INTO evidence
            (id, source_document_id, research_run_id, mission_id, evidence_type,
             excerpt, context_text, normalized_claim, entities_json, topics_json,
             event_date, extracted_at, relevance_score, source_quality_score,
             novelty_score, confidence_score, validation_status, relationship,
             content_hash, data_status, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .bind(
          item.evidenceId,
          item.sourceDocumentId,
          runId,
          input.missionId,
          "FACT",
          item.excerpt,
          item.contextText,
          item.statement,
          JSON.stringify([item.publisher]),
          JSON.stringify(item.topics),
          null,
          completedAt,
          0.78,
          0.7,
          0.75,
          item.confidenceScore,
          "SINGLE_SOURCE",
          "supports",
          item.contentHash,
          item.dataStatus,
          item.isDemo,
        ),
      database
        .prepare(
          `INSERT OR IGNORE INTO claim_evidence
            (claim_id, evidence_id, relationship, support_strength)
           SELECT id, ?, 'supports', 0.72
           FROM claims
           WHERE mission_id = ? AND statement = ?
           LIMIT 1`,
        )
        .bind(item.evidenceId, input.missionId, item.statement),
    ]),
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
        JSON.stringify({ runId, triggerType: "MANUAL" }),
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
          new Date(now.getTime() + index * 120).toISOString(),
          new Date(now.getTime() + index * 120 + 100).toISOString(),
          `Workspace-scoped ${name.toLowerCase()} input`,
          documentCount
            ? `${name} completed against ${documentCount} persisted documents.`
            : `${name} completed with no approved documents; unsupported conclusions were withheld.`,
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
          new Date(now.getTime() + index * 120 + 100).toISOString(),
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
          confidenceScore: confidence,
          documentsProcessed: documentCount,
          evidenceCreated: createdEvidenceCount,
          insightsCreated: 0,
        }),
        completedAt,
      ),
    database
      .prepare(
        `UPDATE missions SET status = 'ACTIVE', updated_at = ? WHERE id = ?`,
      )
      .bind(completedAt, input.missionId),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        "RESEARCH_RUN_CREATED",
        "RESEARCH_RUN",
        runId,
        JSON.stringify({
          documentsProcessed: documentCount,
          evidenceCreated: createdEvidenceCount,
          evidenceTotal: totalEvidenceCount,
          existingInsights: insightCount,
          triggerType: "MANUAL",
        }),
        `request-${crypto.randomUUID()}`,
        completedAt,
      ),
  ];

  await database.batch(statements);
  return {
    created: true,
    dataStatus,
    id: runId,
    isDemo: Boolean(isDemo),
  };
}

export async function cancelResearchRun(input: {
  runId: string;
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const run = await database
    .prepare(
      `SELECT rr.id
      FROM research_runs rr
      INNER JOIN missions m ON m.id = rr.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND rr.id = ? AND rr.status = 'ACTIVE'
      LIMIT 1`,
    )
    .bind(input.workspaceId, input.runId)
    .first<{ id: string }>();

  if (!run) {
    return false;
  }

  const now = new Date().toISOString();
  await database.batch([
    database
      .prepare(
        `UPDATE research_runs
         SET status = 'CANCELLED', completed_at = ?, error_summary = 'CANCELLED_BY_USER'
         WHERE id = ?`,
      )
      .bind(now, input.runId),
    database
      .prepare(
        `UPDATE run_steps
         SET status = CASE WHEN status = 'ACTIVE' THEN 'CANCELLED' ELSE status END,
             completed_at = CASE WHEN status = 'ACTIVE' THEN ? ELSE completed_at END
         WHERE research_run_id = ?`,
      )
      .bind(now, input.runId),
    database
      .prepare(
        `INSERT INTO audit_logs
          (id, workspace_id, user_id, action, entity_type, entity_id,
           details_json, request_id, created_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        `audit-${crypto.randomUUID()}`,
        input.workspaceId,
        input.userId,
        "RESEARCH_RUN_CANCELLED",
        "RESEARCH_RUN",
        input.runId,
        "{}",
        `request-${crypto.randomUUID()}`,
        now,
      ),
  ]);
  return true;
}

export async function setMonitorStatus(input: {
  monitorId: string;
  status: "ACTIVE" | "PAUSED";
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const monitor = await database
    .prepare(
      `SELECT mo.id, mo.schedule
      FROM monitors mo
      INNER JOIN missions m ON m.id = mo.mission_id
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND mo.id = ?
      LIMIT 1`,
    )
    .bind(input.workspaceId, input.monitorId)
    .first<{ id: string; schedule: string }>();

  if (!monitor) {
    throw new Error("MONITOR_NOT_FOUND");
  }

  const now = new Date();
  const delayMinutes =
    monitor.schedule === "HOURLY"
      ? 60
      : monitor.schedule === "DAILY"
        ? 1440
        : 10080;
  const nextCheckAt =
    input.status === "ACTIVE"
      ? new Date(now.getTime() + delayMinutes * 60_000).toISOString()
      : null;

  await database
    .prepare(
      `UPDATE monitors
       SET status = ?, next_check_at = ?, updated_at = ?
       WHERE id = ?`,
    )
    .bind(input.status, nextCheckAt, now.toISOString(), input.monitorId)
    .run();
}

export async function createReport(input: {
  missionId: string;
  type:
    | "EXECUTIVE_BRIEF"
    | "SOURCE_APPENDIX"
    | "COMPETITOR_MATRIX"
    | "EVIDENCE_CSV"
    | "JSON_PACKAGE";
  userId: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const mission = await database
    .prepare(
      `SELECT m.id, m.title, m.objective
      FROM missions m
      INNER JOIN projects p ON p.id = m.project_id
      WHERE p.workspace_id = ? AND m.id = ?
      LIMIT 1`,
    )
    .bind(input.workspaceId, input.missionId)
    .first<{ id: string; objective: string; title: string }>();

  if (!mission) {
    throw new Error("MISSION_NOT_FOUND");
  }

  const { records: insights } = await listInsights(input.workspaceId, {
    missionId: input.missionId,
  });
  const { records: evidenceRecords } = await listEvidence(input.workspaceId, {
    missionId: input.missionId,
  });
  const latestRun = await database
    .prepare(
      `SELECT id FROM research_runs
       WHERE mission_id = ? ORDER BY started_at DESC LIMIT 1`,
    )
    .bind(input.missionId)
    .first<{ id: string }>();
  const generatedAt = new Date().toISOString();
  const reportId = `report-${crypto.randomUUID()}`;
  const outputRecords = [...insights, ...evidenceRecords];
  const allDemo =
    outputRecords.length > 0 && outputRecords.every((item) => item.isDemo);
  const anyDemo = outputRecords.some((item) => item.isDemo);
  const dataStatus = allDemo ? "demo" : anyDemo ? "partial" : "live";
  let content: string;
  let title: string;

  if (input.type === "EVIDENCE_CSV") {
    title = `${mission.title} — evidence table`;
    content = [
      "evidence_id,source,validation_status,confidence,excerpt",
      ...evidenceRecords.map((item) =>
        [
          item.id,
          item.publisher,
          item.validationStatus,
          item.confidenceScore.toFixed(2),
          item.excerpt,
        ]
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(","),
      ),
    ].join("\n");
  } else if (input.type === "SOURCE_APPENDIX") {
    title = `${mission.title} — source appendix`;
    content = [
      `# ${title}`,
      "",
      ...evidenceRecords.map(
        (item, index) =>
          `${index + 1}. ${item.publisher} — ${item.documentTitle}\n   ${item.canonicalUrl}\n   Published ${item.publishedAt.toISOString()}; retrieved ${item.retrievedAt.toISOString()}; evidence ${item.id}; confidence ${item.confidenceScore.toFixed(2)}.`,
      ),
      "",
      "All DEMO publishers are fictional and use reserved .example domains.",
    ].join("\n");
  } else if (input.type === "COMPETITOR_MATRIX") {
    title = `${mission.title} — competitor matrix`;
    const publishers = new Map<
      string,
      { confidences: number[]; evidenceCount: number; topics: Set<string> }
    >();
    for (const item of evidenceRecords) {
      const publisher = publishers.get(item.publisher) ?? {
        confidences: [],
        evidenceCount: 0,
        topics: new Set<string>(),
      };
      publisher.evidenceCount += 1;
      publisher.confidences.push(item.confidenceScore);
      item.topics.forEach((topic) => publisher.topics.add(topic));
      publishers.set(item.publisher, publisher);
    }
    content = [
      "publisher,observed_topics,evidence_count,average_confidence",
      ...[...publishers.entries()].map(([publisher, values]) =>
        [
          publisher,
          [...values.topics].join(" | "),
          values.evidenceCount,
          (
            values.confidences.reduce((sum, value) => sum + value, 0) /
            values.confidences.length
          ).toFixed(2),
        ]
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(","),
      ),
    ].join("\n");
  } else if (input.type === "JSON_PACKAGE") {
    title = `${mission.title} — structured package`;
    content = JSON.stringify(
      {
        data_status: "demo",
        evidence: evidenceRecords.map((item) => ({
          confidence: item.confidenceScore,
          excerpt: item.excerpt,
          id: item.id,
          source: item.canonicalUrl,
          validation_status: item.validationStatus,
        })),
        generated_at: generatedAt,
        insights: insights.map((item) => ({
          confidence: item.confidenceScore,
          id: item.id,
          source_count: item.sourceCount,
          summary: item.summary,
          title: item.title,
          uncertainty: item.uncertaintyNote,
        })),
        is_demo: true,
        mission: {
          id: mission.id,
          objective: mission.objective,
          title: mission.title,
        },
      },
      null,
      2,
    );
  } else {
    title = `${mission.title} — executive brief`;
    content = [
      `# ${title}`,
      "",
      `Generated: ${generatedAt}`,
      "Data state: DEMO",
      "",
      "## Objective",
      "",
      mission.objective,
      "",
      "## Key findings",
      "",
      ...(insights.length
        ? insights.map(
            (item, index) =>
              `${index + 1}. **${item.title}** — ${item.summary} (confidence ${(item.confidenceScore * 100).toFixed(0)}%; ${item.sourceCount} sources)`,
          )
        : ["No supported findings are available."]),
      "",
      "## Limitations",
      "",
      "This package uses fictional deterministic DEMO evidence. Replace it with connected source records before external decision use.",
    ].join("\n");
  }

  await database
    .prepare(
      `INSERT INTO reports
        (id, mission_id, research_run_id, type, status, title, content,
         generated_at, generated_by_id, data_status, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .bind(
      reportId,
      mission.id,
      latestRun?.id ?? null,
      input.type,
      "READY",
      title,
      content,
      generatedAt,
      input.userId,
      dataStatus,
      allDemo ? 1 : 0,
    )
    .run();

  return { id: reportId };
}

export async function askGroundedQuestion(input: {
  missionId: string;
  question: string;
  userId: string;
  workspaceId: string;
}) {
  const { records } = await listEvidence(input.workspaceId, {
    missionId: input.missionId,
  });
  const queryTerms = input.question
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((term) => term.length > 3);
  const ranked = records
    .map((record) => ({
      record,
      score:
        queryTerms.filter((term) =>
          `${record.excerpt} ${record.claimStatement ?? ""} ${record.topics.join(" ")}`
            .toLowerCase()
            .includes(term),
        ).length +
        record.confidenceScore +
        record.relevanceScore,
    }))
    .sort((left, right) => right.score - left.score)
    .slice(0, 3);
  const hasMatch =
    ranked.length > 0 &&
    (queryTerms.length === 0 || ranked.some((item) => item.score > 2));
  const candidates = hasMatch ? ranked.map((item) => item.record) : [];
  const grounded = await generateGroundedAnswer({
    evidence: candidates.map((item) => ({
      confidence: item.confidenceScore,
      evidenceId: item.id,
      excerpt: item.excerpt,
      publishedAt: item.publishedAt.toISOString(),
      publisher: item.publisher,
      sourceUrl: item.canonicalUrl,
    })),
    question: input.question,
  });
  const cited = grounded.citationEvidenceIds
    .map((evidenceId) => candidates.find((item) => item.id === evidenceId))
    .filter((item): item is (typeof candidates)[number] => Boolean(item));
  const answer = [
    "Established evidence:",
    ...(grounded.establishedFacts.length
      ? grounded.establishedFacts.map((fact, index) => `[${index + 1}] ${fact}`)
      : ["No established fact cleared the evidence threshold."]),
    "",
    "Inference:",
    grounded.inference,
  ].join("\n");
  const confidence = grounded.confidence;
  const limitations = grounded.limitations;
  const database = await getDatabase();
  const questionId = `question-${crypto.randomUUID()}`;

  await database
    .prepare(
      `INSERT INTO question_history
        (id, workspace_id, mission_id, user_id, question, answer,
         evidence_ids_json, confidence_score, limitations, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .bind(
      questionId,
      input.workspaceId,
      input.missionId,
      input.userId,
      input.question,
      answer,
      JSON.stringify(cited.map((item) => item.id)),
      confidence,
      limitations,
      new Date().toISOString(),
    )
    .run();

  return {
    answer,
    citations: cited.map((item, index) => ({
      evidenceId: item.id,
      label: index + 1,
      publisher: item.publisher,
    })),
    confidence,
    id: questionId,
    limitations,
  };
}

export async function getDiagnostics(workspaceId: string) {
  const database = await getDatabase();
  const counts = await database
    .prepare(
      `SELECT
        (SELECT COUNT(*) FROM research_runs rr
          INNER JOIN missions m ON m.id = rr.mission_id
          INNER JOIN projects p ON p.id = m.project_id
          WHERE p.workspace_id = ? AND rr.status = 'ACTIVE') AS active_runs,
        (SELECT COUNT(*) FROM research_runs rr
          INNER JOIN missions m ON m.id = rr.mission_id
          INNER JOIN projects p ON p.id = m.project_id
          WHERE p.workspace_id = ? AND rr.status = 'FAILED') AS failed_runs,
        (SELECT COUNT(*) FROM source_connectors
          WHERE workspace_id = ? AND status = 'AVAILABLE') AS healthy_connectors,
        (SELECT COUNT(*) FROM evidence e
          INNER JOIN missions m ON m.id = e.mission_id
          INNER JOIN projects p ON p.id = m.project_id
          WHERE p.workspace_id = ?) AS evidence_count,
        (SELECT COUNT(*) FROM alerts a
          INNER JOIN monitors mo ON mo.id = a.monitor_id
          INNER JOIN missions m ON m.id = mo.mission_id
          INNER JOIN projects p ON p.id = m.project_id
          WHERE p.workspace_id = ? AND a.status = 'UNREAD') AS unread_alerts`,
    )
    .bind(workspaceId, workspaceId, workspaceId, workspaceId, workspaceId)
    .first<{
      active_runs: number;
      evidence_count: number;
      failed_runs: number;
      healthy_connectors: number;
      unread_alerts: number;
    }>();
  const audits = await database
    .prepare(
      `SELECT action, entity_type, entity_id, request_id, created_at
       FROM audit_logs
       WHERE workspace_id = ?
       ORDER BY created_at DESC
       LIMIT 10`,
    )
    .bind(workspaceId)
    .all<{
      action: string;
      created_at: string;
      entity_id: string;
      entity_type: string;
      request_id: string;
    }>();

  return {
    activeRuns: Number(counts?.active_runs ?? 0),
    auditLogs: audits.results.map((row) => ({
      action: row.action,
      createdAt: new Date(row.created_at),
      entityId: row.entity_id,
      entityType: row.entity_type,
      requestId: row.request_id,
    })),
    evidenceCount: Number(counts?.evidence_count ?? 0),
    failedRuns: Number(counts?.failed_runs ?? 0),
    healthyConnectors: Number(counts?.healthy_connectors ?? 0),
    modelProvider: "mock",
    queueMode: "D1 durable event ledger",
    sseStatus: "available",
    unreadAlerts: Number(counts?.unread_alerts ?? 0),
  };
}

export async function searchWorkspace(workspaceId: string, query: string) {
  const database = await getDatabase();
  const like = `%${query}%`;
  const result = await database
    .prepare(
      `SELECT m.id, m.title, 'MISSION' AS result_type, m.objective AS excerpt, '/missions/' || m.id AS href
       FROM missions m
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND (m.title LIKE ? OR m.objective LIKE ?)
       UNION ALL
       SELECT e.id, sd.publisher || ' evidence', 'EVIDENCE', e.excerpt,
              '/evidence?selected=' || e.id
       FROM evidence e
       INNER JOIN source_documents sd ON sd.id = e.source_document_id
       INNER JOIN missions m ON m.id = e.mission_id
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND (e.excerpt LIKE ? OR e.normalized_claim LIKE ?)
       UNION ALL
       SELECT i.id, i.title, 'INSIGHT', i.summary,
              '/insights?selected=' || i.id
       FROM insights i
       INNER JOIN missions m ON m.id = i.mission_id
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND (i.title LIKE ? OR i.summary LIKE ?)
       LIMIT 40`,
    )
    .bind(
      workspaceId,
      like,
      like,
      workspaceId,
      like,
      like,
      workspaceId,
      like,
      like,
    )
    .all<{
      excerpt: string;
      href: string;
      id: string;
      result_type: string;
      title: string;
    }>();

  return result.results.map((row) => ({
    excerpt: row.excerpt,
    href: row.href,
    id: row.id,
    resultType: row.result_type,
    title: row.title,
  }));
}
