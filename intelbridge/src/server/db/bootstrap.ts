export type BootstrapStatement = {
  sql: string;
  values: unknown[];
};

export const DEMO_WORKSPACE_ID = "workspace-intelbridge-demo";
export const DEMO_AS_OF = "2026-07-22T18:30:00.000Z";

const fixedCreatedAt = "2026-07-15T13:00:00.000Z";

export const schemaStatements = [
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
  `CREATE TABLE IF NOT EXISTS connector_configurations (
    connector_id TEXT PRIMARY KEY NOT NULL REFERENCES source_connectors(id) ON DELETE CASCADE,
    configuration_json TEXT NOT NULL,
    last_successful_sync_at TEXT,
    last_error_at TEXT,
    checkpoint_json TEXT,
    last_tested_at TEXT,
    last_test_message TEXT,
    response_time_ms INTEGER,
    updated_at TEXT NOT NULL
  )`,
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
    inclusion_rules_json TEXT NOT NULL DEFAULT '[]',
    exclusion_rules_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT,
    PRIMARY KEY (mission_id, source_connector_id)
  )`,
  `CREATE INDEX IF NOT EXISTS mission_sources_connector_idx
    ON mission_sources (source_connector_id)`,
  `CREATE TABLE IF NOT EXISTS research_runs (
    id TEXT PRIMARY KEY NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    trigger_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    cancel_requested_at TEXT,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    sources_scanned INTEGER NOT NULL DEFAULT 0,
    documents_discovered INTEGER NOT NULL DEFAULT 0,
    documents_processed INTEGER NOT NULL DEFAULT 0,
    documents_created INTEGER NOT NULL DEFAULT 0,
    documents_updated INTEGER NOT NULL DEFAULT 0,
    documents_unchanged INTEGER NOT NULL DEFAULT 0,
    evidence_created INTEGER NOT NULL DEFAULT 0,
    insights_created INTEGER NOT NULL DEFAULT 0,
    confidence_score REAL,
    error_summary TEXT,
    model_provider TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    data_status TEXT NOT NULL,
    is_demo INTEGER NOT NULL,
    created_by_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    retry_of_run_id TEXT REFERENCES research_runs(id) ON DELETE SET NULL,
    created_at TEXT,
    updated_at TEXT
  )`,
  `CREATE INDEX IF NOT EXISTS research_runs_mission_started_idx
    ON research_runs (mission_id, started_at DESC)`,
  `CREATE TABLE IF NOT EXISTS run_steps (
    id TEXT PRIMARY KEY NOT NULL,
    research_run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL,
    step_type TEXT,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    progress_percent INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    input_summary TEXT NOT NULL,
    output_summary TEXT,
    tool_name TEXT NOT NULL,
    token_usage INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,
    attempt INTEGER NOT NULL DEFAULT 1,
    error_code TEXT,
    error_message TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(research_run_id, sequence_number)
  )`,
  `CREATE INDEX IF NOT EXISTS run_steps_run_status_idx
    ON run_steps (research_run_id, status)`,
  `CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    research_run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    sequence_number INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(research_run_id, sequence_number)
  )`,
  `CREATE INDEX IF NOT EXISTS run_events_run_sequence_idx
    ON run_events (research_run_id, sequence_number)`,
  `CREATE TABLE IF NOT EXISTS source_documents (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL REFERENCES source_connectors(id) ON DELETE RESTRICT,
    external_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    publisher TEXT NOT NULL,
    source_type TEXT NOT NULL,
    published_at TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    normalized_content TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    version INTEGER NOT NULL,
    current_version_id TEXT,
    first_retrieved_at TEXT,
    last_retrieved_at TEXT,
    last_research_run_id TEXT REFERENCES research_runs(id) ON DELETE SET NULL,
    change_status TEXT NOT NULL DEFAULT 'CREATED',
    trust_state TEXT NOT NULL,
    prompt_injection_flag INTEGER NOT NULL DEFAULT 0,
    data_status TEXT NOT NULL,
    is_demo INTEGER NOT NULL,
    UNIQUE(workspace_id, canonical_url, version)
  )`,
  `CREATE INDEX IF NOT EXISTS source_documents_mission_retrieved_idx
    ON source_documents (mission_id, retrieved_at DESC)`,
  `CREATE INDEX IF NOT EXISTS source_documents_content_hash_idx
    ON source_documents (content_hash)`,
  `CREATE INDEX IF NOT EXISTS source_documents_workspace_connector_idx
    ON source_documents (workspace_id, connector_id)`,
  `CREATE TABLE IF NOT EXISTS source_document_versions (
    id TEXT PRIMARY KEY NOT NULL,
    source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    research_run_id TEXT REFERENCES research_runs(id) ON DELETE SET NULL,
    version_number INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    raw_content TEXT NOT NULL,
    normalized_content TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    language TEXT,
    metadata_json TEXT NOT NULL,
    storage_key TEXT,
    retrieved_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source_document_id, version_number),
    UNIQUE(source_document_id, content_hash)
  )`,
  `CREATE INDEX IF NOT EXISTS source_document_versions_run_idx
    ON source_document_versions (research_run_id)`,
  `CREATE TABLE IF NOT EXISTS connector_checkpoints (
    id TEXT PRIMARY KEY NOT NULL,
    connector_id TEXT NOT NULL REFERENCES source_connectors(id) ON DELETE CASCADE,
    checkpoint_key TEXT NOT NULL,
    checkpoint_value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(connector_id, checkpoint_key)
  )`,
  `CREATE TABLE IF NOT EXISTS retrieval_failures (
    id TEXT PRIMARY KEY NOT NULL,
    research_run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    connector_id TEXT NOT NULL REFERENCES source_connectors(id) ON DELETE RESTRICT,
    external_id TEXT,
    url TEXT,
    error_code TEXT NOT NULL,
    safe_message TEXT NOT NULL,
    retryable INTEGER NOT NULL,
    attempt INTEGER NOT NULL,
    created_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS retrieval_failures_run_created_idx
    ON retrieval_failures (research_run_id, created_at DESC)`,
  `CREATE TABLE IF NOT EXISTS job_queue (
    id TEXT PRIMARY KEY NOT NULL,
    queue_name TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    available_at TEXT NOT NULL,
    lease_expires_at TEXT,
    completed_at TEXT,
    dead_lettered_at TEXT,
    last_error_code TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS job_queue_claim_idx
    ON job_queue (queue_name, status, available_at)`,
  `CREATE INDEX IF NOT EXISTS job_queue_run_idx ON job_queue (run_id)`,
  `CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY NOT NULL,
    source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    research_run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    context_text TEXT NOT NULL,
    normalized_claim TEXT NOT NULL,
    entities_json TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    event_date TEXT,
    extracted_at TEXT NOT NULL,
    relevance_score REAL NOT NULL,
    source_quality_score REAL NOT NULL,
    novelty_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    validation_status TEXT NOT NULL,
    relationship TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    data_status TEXT NOT NULL,
    is_demo INTEGER NOT NULL,
    UNIQUE(source_document_id, content_hash)
  )`,
  `CREATE INDEX IF NOT EXISTS evidence_mission_extracted_idx
    ON evidence (mission_id, extracted_at DESC)`,
  `CREATE INDEX IF NOT EXISTS evidence_validation_idx
    ON evidence (mission_id, validation_status)`,
  `CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY NOT NULL,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    first_observed_at TEXT NOT NULL,
    last_observed_at TEXT NOT NULL,
    materiality_score REAL NOT NULL,
    calculation_factors_json TEXT NOT NULL,
    data_status TEXT NOT NULL,
    is_demo INTEGER NOT NULL,
    UNIQUE(mission_id, statement)
  )`,
  `CREATE INDEX IF NOT EXISTS claims_mission_materiality_idx
    ON claims (mission_id, materiality_score DESC)`,
  `CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    support_strength REAL NOT NULL,
    PRIMARY KEY (claim_id, evidence_id)
  )`,
  `CREATE INDEX IF NOT EXISTS claim_evidence_evidence_idx
    ON claim_evidence (evidence_id)`,
  `CREATE TABLE IF NOT EXISTS insights (
    id TEXT PRIMARY KEY NOT NULL,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    research_run_id TEXT NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    materiality_score REAL NOT NULL,
    novelty_score REAL NOT NULL,
    status TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    owner TEXT NOT NULL,
    uncertainty_note TEXT NOT NULL,
    assumptions_json TEXT NOT NULL,
    calculation_refs_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    data_status TEXT NOT NULL,
    is_demo INTEGER NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS insights_mission_materiality_idx
    ON insights (mission_id, materiality_score DESC)`,
  `CREATE TABLE IF NOT EXISTS insight_claims (
    insight_id TEXT NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
    claim_id TEXT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    importance INTEGER NOT NULL,
    PRIMARY KEY (insight_id, claim_id)
  )`,
  `CREATE TABLE IF NOT EXISTS monitors (
    id TEXT PRIMARY KEY NOT NULL,
    mission_id TEXT NOT NULL UNIQUE REFERENCES missions(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    schedule TEXT NOT NULL,
    materiality_threshold REAL NOT NULL,
    minimum_confidence REAL NOT NULL,
    required_source_count INTEGER NOT NULL,
    topic_allowlist_json TEXT NOT NULL,
    topic_blocklist_json TEXT NOT NULL,
    entity_watchlist_json TEXT NOT NULL,
    alert_cooldown_minutes INTEGER NOT NULL,
    contradiction_alerts INTEGER NOT NULL,
    source_failure_alerts INTEGER NOT NULL,
    last_checked_at TEXT,
    next_check_at TEXT,
    updated_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS monitors_status_next_check_idx
    ON monitors (status, next_check_at)`,
  `CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY NOT NULL,
    monitor_id TEXT NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    insight_id TEXT REFERENCES insights(id) ON DELETE SET NULL,
    alert_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    materiality_score REAL NOT NULL,
    created_at TEXT NOT NULL,
    delivered_at TEXT
  )`,
  `CREATE INDEX IF NOT EXISTS alerts_monitor_created_idx
    ON alerts (monitor_id, created_at DESC)`,
  `CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY NOT NULL,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    research_run_id TEXT REFERENCES research_runs(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generated_by_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    data_status TEXT NOT NULL,
    is_demo INTEGER NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS reports_mission_generated_idx
    ON reports (mission_id, generated_at DESC)`,
  `CREATE TABLE IF NOT EXISTS agent_definitions (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    model TEXT NOT NULL,
    allowed_tools_json TEXT NOT NULL,
    output_schema TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(workspace_id, agent_type)
  )`,
  `CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details_json TEXT NOT NULL,
    request_id TEXT NOT NULL,
    created_at TEXT NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS audit_logs_workspace_created_idx
    ON audit_logs (workspace_id, created_at DESC)`,
  `CREATE TABLE IF NOT EXISTS question_history (
    id TEXT PRIMARY KEY NOT NULL,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    mission_id TEXT NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    limitations TEXT NOT NULL,
    created_at TEXT NOT NULL
  )`,
] as const;

const projects = [
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
] as const;

const connectors = [
  ["connector-demo", "Deterministic demo corpus", "DEMO", "CONNECTED"],
  ["connector-rss", "RSS and Atom feeds", "RSS", "DISCONNECTED"],
  [
    "connector-public-web",
    "Approved public webpages",
    "WEBPAGE",
    "DISCONNECTED",
  ],
  ["connector-manual-url", "Manual URL submissions", "MANUAL_URL", "CONNECTED"],
  ["connector-file-upload", "Uploaded documents", "FILE_UPLOAD", "CONNECTED"],
  [
    "connector-github-public",
    "GitHub public repositories",
    "GITHUB",
    "DISCONNECTED",
  ],
] as const;

const missions = [
  {
    createdBy: "user-alex-parker",
    depth: "DEEP",
    id: "mission-enterprise-search",
    interval: 1440,
    mode: "DAILY",
    objective:
      "Assess how recent competitor launches in enterprise search affect the product roadmap and identify capability gaps, customer implications, and recommended actions.",
    projectId: "project-competitive-intelligence",
    scope: {
      focusAreas: ["Products", "Pricing", "Go-to-market"],
      regions: ["North America", "Europe"],
      timeHorizonMonths: 12,
    },
    status: "READY",
    title: "Enterprise search launch impact",
  },
  {
    createdBy: "user-maya-chen",
    depth: "STANDARD",
    id: "mission-mid-market",
    interval: 10080,
    mode: "WEEKLY",
    objective:
      "Identify unresolved information-retrieval needs among teams with 200 to 1,000 employees and map the evidence to pricing and packaging decisions.",
    projectId: "project-market-entry",
    scope: {
      focusAreas: ["Customer needs", "Pricing", "Adoption barriers"],
      regions: ["United States"],
      timeHorizonMonths: 18,
    },
    status: "READY",
    title: "Mid-market buyer requirements",
  },
  {
    createdBy: "user-alex-parker",
    depth: "RAPID",
    id: "mission-developer-platforms",
    interval: null,
    mode: "MANUAL",
    objective:
      "Establish an evidence-backed baseline for retrieval APIs, deployment controls, and observability across approved developer platforms.",
    projectId: "project-product-strategy",
    scope: {
      focusAreas: ["APIs", "Deployment", "Observability"],
      regions: ["Global"],
      timeHorizonMonths: 6,
    },
    status: "READY",
    title: "Developer platform capability baseline",
  },
] as const;

const runs = [
  {
    completedAt: "2026-07-22T18:30:00.000Z",
    confidence: 0.91,
    documents: 12,
    evidence: 36,
    id: "run-enterprise-0421",
    insights: 5,
    missionId: "mission-enterprise-search",
    progress: 100,
    sources: 12,
    startedAt: "2026-07-22T18:12:00.000Z",
    status: "COMPLETED",
    trigger: "MANUAL",
    userId: "user-alex-parker",
  },
  {
    completedAt: "2026-07-21T15:18:00.000Z",
    confidence: 0.82,
    documents: 5,
    evidence: 15,
    id: "run-midmarket-0317",
    insights: 2,
    missionId: "mission-mid-market",
    progress: 100,
    sources: 5,
    startedAt: "2026-07-21T15:02:00.000Z",
    status: "COMPLETED",
    trigger: "SCHEDULED",
    userId: "user-maya-chen",
  },
  {
    completedAt: "2026-07-23T12:18:00.000Z",
    confidence: 0.74,
    documents: 3,
    evidence: 9,
    id: "run-developer-0514",
    insights: 1,
    missionId: "mission-developer-platforms",
    progress: 100,
    sources: 3,
    startedAt: "2026-07-23T12:02:00.000Z",
    status: "COMPLETED",
    trigger: "MANUAL",
    userId: "user-alex-parker",
  },
] as const;

const sourceDefinitions = [
  [
    "Nimbus Search",
    "Product update adds governed generative summaries",
    "Primary product documentation states that governed generative summaries are now available to enterprise administrators. The feature includes citation controls and per-workspace policy settings. The launch is limited to selected enterprise plans.",
    "product_page",
  ],
  [
    "Helio Index",
    "Usage-based retrieval pricing announced",
    "The published pricing schedule introduces usage-based retrieval charges above the included monthly allowance. Mid-market packages retain an annual platform commitment. Overage pricing varies by document volume.",
    "pricing_page",
  ],
  [
    "VectorStack",
    "Analytics dashboard expands query diagnostics",
    "Release notes describe new query diagnostics, relevance trend views, and failed-search cohorts. Administrators can export diagnostic events in structured form. Benchmark comparison remains available only on the highest plan.",
    "release_notes",
  ],
  [
    "Meridian Research",
    "Enterprise retrieval buyer study",
    "A fictional buyer study reports that governance and analytics are recurring evaluation criteria. Respondents cite integration effort as the most common adoption barrier. The study covers 48 fictional enterprise teams.",
    "research_report",
  ],
  [
    "Northstar Labs",
    "Connector framework documentation revised",
    "Developer documentation adds a checkpoint API for incremental indexing. The framework supports retry tokens and version-aware retrieval. Private network deployment remains listed as a roadmap item.",
    "documentation",
  ],
  [
    "Signal Forge",
    "Customer advisory on retrieval evaluation",
    "The advisory recommends measuring citation coverage and unresolved-query rates together. It warns that answer fluency alone can conceal retrieval gaps. The recommended evaluation window is four weeks.",
    "advisory",
  ],
  [
    "CortexWorks",
    "Regional deployment controls released",
    "The product update adds region-specific processing controls for European workspaces. Audit exports include processing region and policy version. Customer-managed encryption keys remain in private preview.",
    "product_page",
  ],
  [
    "Atlas Query",
    "Mid-market package removes seat minimum",
    "The public package sheet removes the prior fifty-seat minimum. It retains a base platform fee and includes three standard connectors. Advanced analytics is sold as an add-on.",
    "pricing_page",
  ],
  [
    "Beacon Retrieval",
    "Public issue tracker shows observability demand",
    "Several fictional issues request trace-level retrieval diagnostics and exportable latency data. Maintainers accepted an event-hook proposal. No delivery date is committed.",
    "issue_tracker",
  ],
  [
    "Prism Archive",
    "Security controls matrix updated",
    "The controls matrix adds configurable retention and legal-hold exports. The update documents role-scoped evidence access. External key management is not generally available.",
    "controls_matrix",
  ],
  [
    "Quarry AI",
    "Partner program targets system integrators",
    "The partner announcement introduces implementation certification for regional integrators. Certified partners receive sandbox capacity and migration tooling. Referral economics are not disclosed.",
    "announcement",
  ],
  [
    "Lattice Find",
    "Benchmark suite publishes retrieval results",
    "A fictional benchmark reports improved recall on multilingual policy documents. The methodology uses a curated test set and excludes scanned PDFs. Results have not been independently reproduced.",
    "benchmark",
  ],
  [
    "Harbor Search",
    "Buyer guide emphasizes predictable pricing",
    "The guide says mid-market teams prefer predictable platform fees over uncapped usage charges. Procurement cycles lengthen when security review requires custom terms. The guide is based on a fictional advisory panel.",
    "buyer_guide",
  ],
  [
    "Aperture Index",
    "Implementation playbook reduces initial scope",
    "The playbook recommends starting with two repositories and one workflow. It reports shorter fictional pilot cycles when access policies are mapped before indexing. It does not provide a control group.",
    "playbook",
  ],
  [
    "Orchid Data",
    "Pricing calculator adds capacity guardrails",
    "The calculator displays monthly capacity ranges and explicit overage caps. Customers can select annual reconciliation. Data residency remains an enterprise-only option.",
    "pricing_page",
  ],
  [
    "Kite Systems",
    "Survey identifies packaging friction",
    "A fictional survey of 32 teams identifies connector bundles and implementation services as common pricing friction. Teams under one thousand employees report limited analytics staff. Respondents favor guided defaults.",
    "survey",
  ],
  [
    "Relay Search",
    "Channel release adds guided onboarding",
    "The release adds a guided source-mapping workflow for partner-led deployments. Default dashboards focus on content freshness and query failure. Custom metrics require a higher plan.",
    "release_notes",
  ],
  [
    "Forge Retrieval",
    "API changelog adds trace identifiers",
    "The changelog introduces stable trace identifiers across retrieval and ranking calls. Developers can query a trace endpoint for thirty days. Batch export is planned but unavailable.",
    "api_changelog",
  ],
  [
    "Sable Index",
    "Deployment guide documents private endpoints",
    "The deployment guide supports private endpoints in two fictional cloud regions. Health events include indexing lag and connector failures. Customer-managed routing is not supported.",
    "documentation",
  ],
  [
    "Orbit Query",
    "SDK release standardizes evaluation hooks",
    "The SDK release adds typed evaluation hooks and structured error codes. It includes examples for latency and citation checks. The release is marked beta.",
    "release_notes",
  ],
] as const;

const claimStatements = [
  "Governed generative answer controls are becoming a baseline enterprise requirement.",
  "Advanced retrieval analytics remain concentrated in premium plans.",
  "Usage-based pricing creates budgeting friction for mid-market buyers.",
  "Predictable capacity limits improve procurement readiness.",
  "Integration effort is a leading barrier to enterprise adoption.",
  "Regional processing controls influence European evaluations.",
  "Citation coverage must be evaluated alongside answer quality.",
  "Checkpointed incremental indexing is becoming a developer expectation.",
  "Trace-level observability is requested across developer platforms.",
  "Partner-led onboarding can reduce implementation burden.",
  "Customer-managed encryption remains inconsistently available.",
  "Multilingual retrieval performance is an emerging differentiator.",
  "Smaller teams prefer guided analytics defaults.",
  "Security review lengthens mid-market procurement cycles.",
  "Structured export access remains uneven across competitors.",
] as const;

const insightDefinitions = [
  {
    action:
      "Make governed answer controls and citation policy a committed release criterion.",
    category: "STRATEGIC",
    confidence: 0.94,
    materiality: 0.89,
    novelty: 0.78,
    severity: "HIGH",
    summary:
      "Four independent fictional sources now treat governance, citations, and administrator policy controls as standard enterprise evaluation criteria.",
    title: "Governed generative retrieval is becoming table stakes",
  },
  {
    action:
      "Prioritize exportable query diagnostics and benchmark comparison in the analytics roadmap.",
    category: "PRODUCT_GAP",
    confidence: 0.91,
    materiality: 0.87,
    novelty: 0.81,
    severity: "HIGH",
    summary:
      "Competitor material consistently offers deeper failed-search analysis and exportable diagnostics than the current IntelBridge demo scope.",
    title: "Advanced retrieval analytics is the clearest capability gap",
  },
  {
    action:
      "Test a predictable mid-market package with explicit capacity caps and guided defaults.",
    category: "OPPORTUNITY",
    confidence: 0.84,
    materiality: 0.79,
    novelty: 0.74,
    severity: "MEDIUM",
    summary:
      "Fictional buyer evidence suggests a packaging opening between uncapped usage pricing and enterprise-only commitments.",
    title: "Predictable mid-market packaging is an underserved opening",
  },
  {
    action:
      "Add processing-region evidence and encryption-key status to every enterprise evaluation.",
    category: "RISK",
    confidence: 0.88,
    materiality: 0.82,
    novelty: 0.68,
    severity: "HIGH",
    summary:
      "Regional controls are shipping while customer-managed encryption remains uneven, creating a moving security baseline.",
    title: "Security-control parity could delay European evaluations",
  },
  {
    action:
      "Validate multilingual benchmark claims with an internal reproducible corpus before using them in positioning.",
    category: "CONTRADICTION",
    confidence: 0.73,
    materiality: 0.62,
    novelty: 0.83,
    severity: "MEDIUM",
    summary:
      "A published fictional benchmark claims improved multilingual recall but excludes scanned documents and lacks independent reproduction.",
    title:
      "Multilingual performance claims are not yet independently validated",
  },
  {
    action:
      "Package source mapping, policy setup, and dashboard defaults into a constrained launch service.",
    category: "OPPORTUNITY",
    confidence: 0.82,
    materiality: 0.76,
    novelty: 0.7,
    severity: "MEDIUM",
    summary:
      "Guided onboarding and limited initial scope repeatedly correlate with shorter fictional pilot cycles.",
    title: "Guided deployment can offset mid-market implementation friction",
  },
  {
    action:
      "Standardize trace IDs, structured errors, and health events across every retrieval endpoint.",
    category: "PRODUCT_GAP",
    confidence: 0.9,
    materiality: 0.85,
    novelty: 0.77,
    severity: "HIGH",
    summary:
      "Developer-facing competitors are converging on traceable calls, checkpoint APIs, and exportable operational events.",
    title: "Developer observability now defines platform credibility",
  },
  {
    action:
      "Keep batch export and private deployment on the monitored gap list until primary documentation confirms availability.",
    category: "KNOWLEDGE_GAP",
    confidence: 0.76,
    materiality: 0.65,
    novelty: 0.69,
    severity: "LOW",
    summary:
      "Several capabilities are announced or in preview, but generally available delivery evidence is incomplete.",
    title: "Preview-stage platform claims require continued monitoring",
  },
] as const;

const agents = [
  [
    "agent-planner",
    "Planner Agent",
    "PLANNER",
    "Decompose mission objectives into bounded questions and source priorities.",
    "mission-plan",
    "planner-output-v1",
    '["mission.read","connector.list","run.write"]',
  ],
  [
    "agent-retrieval",
    "Retrieval Agent",
    "RETRIEVAL",
    "Discover and retrieve approved source material with checkpoints and limits.",
    "source-retrieval",
    "retrieval-result-v1",
    '["source.fetch","checkpoint.read","checkpoint.write"]',
  ],
  [
    "agent-extraction",
    "Evidence Extractor",
    "EVIDENCE_EXTRACTION",
    "Extract source-bound excerpts and normalized evidence records.",
    "evidence-extraction",
    "evidence-extraction-v1",
    '["document.read","evidence.write"]',
  ],
  [
    "agent-validation",
    "Validation Agent",
    "VALIDATION",
    "Group claims, identify support and contradiction, and explain uncertainty.",
    "claim-validation",
    "claim-validation-v1",
    '["evidence.read","claim.write","relationship.write"]',
  ],
  [
    "agent-synthesis",
    "Synthesis Agent",
    "SYNTHESIS",
    "Generate supported findings, risks, opportunities, and open questions.",
    "insight-synthesis",
    "insight-output-v1",
    '["claim.read","insight.write"]',
  ],
  [
    "agent-report",
    "Report Agent",
    "REPORTING",
    "Generate executive briefs and evidence export packages.",
    "report-generation",
    "report-package-v1",
    '["insight.read","evidence.read","report.write"]',
  ],
] as const;

function statement(sql: string, values: unknown[]): BootstrapStatement {
  return { sql, values };
}

const baseSeedStatements: BootstrapStatement[] = [
  statement(
    `INSERT OR IGNORE INTO workspaces (id, name, created_at, updated_at)
      VALUES (?, ?, ?, ?)`,
    [
      DEMO_WORKSPACE_ID,
      "IntelBridge Demo Workspace",
      fixedCreatedAt,
      DEMO_AS_OF,
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO users
      (id, workspace_id, name, email, role, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [
      "user-alex-parker",
      DEMO_WORKSPACE_ID,
      "Alex Parker",
      "alex.parker@intelbridge.demo",
      "ADMIN",
      fixedCreatedAt,
      DEMO_AS_OF,
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO users
      (id, workspace_id, name, email, role, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
    [
      "user-maya-chen",
      DEMO_WORKSPACE_ID,
      "Maya Chen",
      "maya.chen@intelbridge.demo",
      "EDITOR",
      fixedCreatedAt,
      DEMO_AS_OF,
    ],
  ),
  ...projects.map(([id, name, description]) =>
    statement(
      `INSERT OR IGNORE INTO projects
        (id, workspace_id, name, description, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        DEMO_WORKSPACE_ID,
        name,
        description,
        "ACTIVE",
        fixedCreatedAt,
        DEMO_AS_OF,
      ],
    ),
  ),
  ...connectors.map(([id, name, type, status]) =>
    statement(
      `INSERT OR IGNORE INTO source_connectors
        (id, workspace_id, name, type, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [id, DEMO_WORKSPACE_ID, name, type, status, fixedCreatedAt, DEMO_AS_OF],
    ),
  ),
  ...connectors.map(([id]) =>
    statement(
      `INSERT OR IGNORE INTO connector_configurations
        (connector_id, configuration_json, last_successful_sync_at, last_error_at,
         checkpoint_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)`,
      [
        id,
        JSON.stringify({
          maximumItemsPerRun: 25,
          mode: id === "connector-demo" ? "deterministic-demo" : "user-managed",
          type:
            id === "connector-rss"
              ? "RSS"
              : id === "connector-public-web"
                ? "WEBPAGE"
                : id === "connector-manual-url"
                  ? "MANUAL_URL"
                  : id === "connector-file-upload"
                    ? "FILE_UPLOAD"
                    : id === "connector-github-public"
                      ? "GITHUB"
                      : "DEMO",
        }),
        id === "connector-demo" ? DEMO_AS_OF : null,
        null,
        id === "connector-demo"
          ? JSON.stringify({ cursor: "demo-2026-07-22", version: 1 })
          : null,
        DEMO_AS_OF,
      ],
    ),
  ),
  ...missions.map((mission) =>
    statement(
      `INSERT OR IGNORE INTO missions
        (id, project_id, title, objective, scope_json, status, research_depth,
         monitoring_mode, monitoring_interval, created_by_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        mission.id,
        mission.projectId,
        mission.title,
        mission.objective,
        JSON.stringify(mission.scope),
        mission.status,
        mission.depth,
        mission.mode,
        mission.interval,
        mission.createdBy,
        fixedCreatedAt,
        DEMO_AS_OF,
      ],
    ),
  ),
  ...missions.map((mission) =>
    statement(
      `INSERT OR IGNORE INTO mission_sources
        (mission_id, source_connector_id, priority, inclusion_rules_json,
         exclusion_rules_json, created_at) VALUES (?, ?, ?, ?, ?, ?)`,
      [mission.id, "connector-demo", 100, "[]", "[]", fixedCreatedAt],
    ),
  ),
  ...runs.map((run) =>
    statement(
      `INSERT OR IGNORE INTO research_runs
        (id, idempotency_key, mission_id, trigger_type, status, started_at, completed_at,
         progress_percent, sources_scanned, documents_processed, evidence_created,
         insights_created, confidence_score, error_summary, model_provider,
         prompt_version, data_status, is_demo, created_by_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        run.id,
        `seed:${run.id}`,
        run.missionId,
        run.trigger,
        run.status,
        run.startedAt,
        run.completedAt,
        run.progress,
        run.sources,
        run.documents,
        run.evidence,
        run.insights,
        run.confidence,
        null,
        "mock",
        "pipeline-v1.0.0",
        "demo",
        1,
        run.userId,
      ],
    ),
  ),
];

const stepDefinitions = [
  ["PLAN", "Mission plan", "plan_run"],
  ["DISCOVER", "Source discovery", "discover_sources"],
  ["RETRIEVE", "Document retrieval", "retrieve_documents"],
  ["NORMALIZE", "Content normalization", "normalize_documents"],
  ["DEDUPLICATE", "Document deduplication", "deduplicate_documents"],
  ["PERSIST", "Document persistence", "persist_documents"],
  ["FINALIZE", "Run finalization", "finalize_run"],
] as const;

const runSeedStatements = runs.flatMap((run) => {
  const completedStepCount =
    run.status === "COMPLETED" ? stepDefinitions.length : 4;
  const events: BootstrapStatement[] = [
    statement(
      `INSERT OR IGNORE INTO run_events
        (research_run_id, sequence_number, event_type, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?)`,
      [
        run.id,
        1,
        "run.started",
        JSON.stringify({ runId: run.id, triggerType: run.trigger }),
        run.startedAt,
      ],
    ),
  ];

  const steps = stepDefinitions.map(([agentType, name, toolName], index) => {
    const stepNumber = index + 1;
    const status =
      stepNumber <= completedStepCount
        ? "COMPLETED"
        : stepNumber === completedStepCount + 1
          ? "RUNNING"
          : "PENDING";
    const progress =
      status === "COMPLETED" ? 100 : status === "RUNNING" ? 42 : 0;
    const startedAt =
      status === "PENDING"
        ? null
        : new Date(
            new Date(run.startedAt).getTime() + index * 120_000,
          ).toISOString();
    const completedAt =
      status === "COMPLETED" && startedAt
        ? new Date(new Date(startedAt).getTime() + 85_000).toISOString()
        : null;
    const stepId = `${run.id}-step-${stepNumber}`;

    events.push(
      statement(
        `INSERT OR IGNORE INTO run_events
          (research_run_id, sequence_number, event_type, payload_json, created_at)
          VALUES (?, ?, ?, ?, ?)`,
        [
          run.id,
          stepNumber + 1,
          status === "COMPLETED" ? "step.completed" : "step.started",
          JSON.stringify({
            message:
              status === "COMPLETED"
                ? `${name} completed`
                : `${name} is in progress`,
            progress,
            stepId,
          }),
          completedAt ?? startedAt ?? run.startedAt,
        ],
      ),
    );

    return statement(
      `INSERT OR IGNORE INTO run_steps
        (id, research_run_id, agent_type, name, status, sequence_number,
         progress_percent, started_at, completed_at, input_summary, output_summary,
         tool_name, token_usage, duration_ms, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        stepId,
        run.id,
        agentType,
        name,
        status,
        stepNumber,
        progress,
        startedAt,
        completedAt,
        `Mission-scoped ${name.toLowerCase()} input`,
        status === "COMPLETED"
          ? `${name} persisted an inspectable output record.`
          : null,
        toolName,
        status === "COMPLETED" ? 620 + index * 87 : 0,
        status === "COMPLETED" ? 85_000 : null,
        null,
      ],
    );
  });

  if (run.status === "COMPLETED") {
    events.push(
      statement(
        `INSERT OR IGNORE INTO run_events
          (research_run_id, sequence_number, event_type, payload_json, created_at)
          VALUES (?, ?, ?, ?, ?)`,
        [
          run.id,
          8,
          "run.completed",
          JSON.stringify({
            confidenceScore: run.confidence,
            documentsProcessed: run.documents,
            evidenceCreated: run.evidence,
            insightsCreated: run.insights,
          }),
          run.completedAt,
        ],
      ),
    );
  }

  return [...steps, ...events];
});

const documentSeedStatements = sourceDefinitions.map(
  ([publisher, title, content, sourceType], index) => {
    const number = index + 1;
    const missionId =
      index < 12
        ? "mission-enterprise-search"
        : index < 17
          ? "mission-mid-market"
          : "mission-developer-platforms";
    const slug = publisher.toLowerCase().replaceAll(" ", "-");
    const publishedAt = new Date(
      Date.UTC(2026, 6, 2 + index, 13 + (index % 4), 0, 0),
    ).toISOString();

    return statement(
      `INSERT OR IGNORE INTO source_documents
        (id, workspace_id, mission_id, connector_id, external_id, canonical_url,
         title, author, publisher, source_type, published_at, retrieved_at,
         content_hash, raw_content, normalized_content, metadata_json, version,
         trust_state, prompt_injection_flag, data_status, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        `document-${number.toString().padStart(2, "0")}`,
        DEMO_WORKSPACE_ID,
        missionId,
        "connector-demo",
        `demo-source-${number}`,
        `https://${slug}.example/research/${number}`,
        title,
        index % 3 === 0 ? "Research desk" : null,
        publisher,
        sourceType,
        publishedAt,
        DEMO_AS_OF,
        `demo-document-hash-${number}`,
        content,
        content,
        JSON.stringify({
          contentType: "text/plain",
          demo: true,
          fictionalPublisher: true,
          language: "en",
        }),
        1,
        "UNTRUSTED_SOURCE",
        0,
        "demo",
        1,
      ],
    );
  },
);

const evidenceSeedStatements = sourceDefinitions.flatMap(
  ([publisher, , content], documentIndex) => {
    const documentNumber = documentIndex + 1;
    const missionId =
      documentIndex < 12
        ? "mission-enterprise-search"
        : documentIndex < 17
          ? "mission-mid-market"
          : "mission-developer-platforms";
    const runId =
      documentIndex < 12
        ? "run-enterprise-0421"
        : documentIndex < 17
          ? "run-midmarket-0317"
          : "run-developer-0514";
    const sentences = content
      .split(". ")
      .map((sentence) => (sentence.endsWith(".") ? sentence : `${sentence}.`));

    return sentences.slice(0, 3).map((excerpt, excerptIndex) => {
      const evidenceNumber = documentIndex * 3 + excerptIndex + 1;
      const claimIndex = (evidenceNumber - 1) % claimStatements.length;
      const relationship =
        evidenceNumber % 11 === 0
          ? "contradicts"
          : evidenceNumber % 7 === 0
            ? "contextualizes"
            : "supports";
      const validationStatus =
        relationship === "contradicts"
          ? "CONTRADICTED"
          : evidenceNumber % 13 === 0
            ? "SINGLE_SOURCE"
            : "VALIDATED";

      return statement(
        `INSERT OR IGNORE INTO evidence
          (id, source_document_id, research_run_id, mission_id, evidence_type,
           excerpt, context_text, normalized_claim, entities_json, topics_json,
           event_date, extracted_at, relevance_score, source_quality_score,
           novelty_score, confidence_score, validation_status, relationship,
           content_hash, data_status, is_demo)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          `evidence-${evidenceNumber.toString().padStart(2, "0")}`,
          `document-${documentNumber.toString().padStart(2, "0")}`,
          runId,
          missionId,
          excerptIndex === 0
            ? "FACT"
            : excerptIndex === 1
              ? "EVENT"
              : "OPINION",
          excerpt,
          content,
          claimStatements[claimIndex],
          JSON.stringify([publisher]),
          JSON.stringify([
            claimIndex % 3 === 0
              ? "governance"
              : claimIndex % 3 === 1
                ? "analytics"
                : "pricing",
          ]),
          null,
          DEMO_AS_OF,
          0.76 + (evidenceNumber % 5) * 0.04,
          0.72 + (documentIndex % 6) * 0.04,
          0.61 + (excerptIndex % 3) * 0.1,
          0.74 + (evidenceNumber % 6) * 0.035,
          validationStatus,
          relationship,
          `demo-evidence-hash-${evidenceNumber}`,
          "demo",
          1,
        ],
      );
    });
  },
);

const claimSeedStatements = claimStatements.map((claim, index) => {
  const missionId =
    index < 9
      ? "mission-enterprise-search"
      : index < 13
        ? "mission-mid-market"
        : "mission-developer-platforms";
  const factors = {
    confidence: 0.78 + (index % 4) * 0.04,
    impact: 0.72 + (index % 3) * 0.06,
    novelty: 0.66 + (index % 5) * 0.05,
    relevance: 0.88,
    sourceQuality: 0.82,
    urgency: 0.7 + (index % 2) * 0.09,
  };
  const materiality = Object.values(factors).reduce(
    (score, factor) => score * factor,
    1,
  );

  return statement(
    `INSERT OR IGNORE INTO claims
      (id, mission_id, statement, claim_type, status, confidence_score,
       first_observed_at, last_observed_at, materiality_score,
       calculation_factors_json, data_status, is_demo)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      `claim-${(index + 1).toString().padStart(2, "0")}`,
      missionId,
      claim,
      index % 5 === 0 ? "RISK" : index % 3 === 0 ? "TREND" : "FACT",
      index % 7 === 0 ? "STRENGTHENED" : "CONFIRMED",
      factors.confidence,
      fixedCreatedAt,
      DEMO_AS_OF,
      materiality,
      JSON.stringify(factors),
      "demo",
      1,
    ],
  );
});

const claimEvidenceSeedStatements = evidenceSeedStatements.map((_, index) => {
  const evidenceNumber = index + 1;
  const claimNumber = ((evidenceNumber - 1) % claimStatements.length) + 1;
  const relationship =
    evidenceNumber % 11 === 0
      ? "contradicts"
      : evidenceNumber % 7 === 0
        ? "contextualizes"
        : "supports";

  return statement(
    `INSERT OR IGNORE INTO claim_evidence
      (claim_id, evidence_id, relationship, support_strength)
      VALUES (?, ?, ?, ?)`,
    [
      `claim-${claimNumber.toString().padStart(2, "0")}`,
      `evidence-${evidenceNumber.toString().padStart(2, "0")}`,
      relationship,
      relationship === "supports" ? 0.88 : 0.67,
    ],
  );
});

const insightSeedStatements = insightDefinitions.map((insight, index) => {
  const missionId =
    index < 5
      ? "mission-enterprise-search"
      : index < 7
        ? "mission-mid-market"
        : "mission-developer-platforms";
  const runId =
    index < 5
      ? "run-enterprise-0421"
      : index < 7
        ? "run-midmarket-0317"
        : "run-developer-0514";

  return statement(
    `INSERT OR IGNORE INTO insights
      (id, mission_id, research_run_id, title, summary, category, severity,
       confidence_score, materiality_score, novelty_score, status,
       recommended_action, owner, uncertainty_note, assumptions_json,
       calculation_refs_json, created_at, updated_at, data_status, is_demo)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      `insight-${(index + 1).toString().padStart(2, "0")}`,
      missionId,
      runId,
      insight.title,
      insight.summary,
      insight.category,
      insight.severity,
      insight.confidence,
      insight.materiality,
      insight.novelty,
      "OPEN",
      insight.action,
      index % 2 === 0 ? "Alex Parker" : "Maya Chen",
      "All findings use a fictional deterministic corpus; live-market applicability must be confirmed against connected sources.",
      JSON.stringify([
        "Fictional source dates are comparable within the demo window.",
        "The mission scope and selected source policy remain unchanged.",
      ]),
      JSON.stringify([
        "materiality-v1",
        "source-diversity-v1",
        "claim-validation-v1",
      ]),
      DEMO_AS_OF,
      DEMO_AS_OF,
      "demo",
      1,
    ],
  );
});

const insightClaimSeedStatements = insightDefinitions.flatMap((_, index) => {
  const firstClaim = ((index * 2) % claimStatements.length) + 1;
  const secondClaim = (firstClaim % claimStatements.length) + 1;

  return [firstClaim, secondClaim].map((claimNumber, claimIndex) =>
    statement(
      `INSERT OR IGNORE INTO insight_claims
        (insight_id, claim_id, importance) VALUES (?, ?, ?)`,
      [
        `insight-${(index + 1).toString().padStart(2, "0")}`,
        `claim-${claimNumber.toString().padStart(2, "0")}`,
        claimIndex === 0 ? 100 : 80,
      ],
    ),
  );
});

const operationsSeedStatements: BootstrapStatement[] = [
  statement(
    `INSERT OR IGNORE INTO monitors
      (id, mission_id, status, schedule, materiality_threshold,
       minimum_confidence, required_source_count, topic_allowlist_json,
       topic_blocklist_json, entity_watchlist_json, alert_cooldown_minutes,
       contradiction_alerts, source_failure_alerts, last_checked_at,
       next_check_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "monitor-enterprise",
      "mission-enterprise-search",
      "ACTIVE",
      "DAILY",
      0.62,
      0.75,
      2,
      JSON.stringify(["governance", "analytics", "pricing"]),
      JSON.stringify(["careers"]),
      JSON.stringify(["Nimbus Search", "VectorStack", "CortexWorks"]),
      720,
      1,
      1,
      DEMO_AS_OF,
      "2026-07-23T18:30:00.000Z",
      DEMO_AS_OF,
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO monitors
      (id, mission_id, status, schedule, materiality_threshold,
       minimum_confidence, required_source_count, topic_allowlist_json,
       topic_blocklist_json, entity_watchlist_json, alert_cooldown_minutes,
       contradiction_alerts, source_failure_alerts, last_checked_at,
       next_check_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "monitor-midmarket",
      "mission-mid-market",
      "PAUSED",
      "WEEKLY",
      0.58,
      0.72,
      2,
      JSON.stringify(["pricing", "onboarding"]),
      JSON.stringify([]),
      JSON.stringify(["Atlas Query", "Orchid Data"]),
      1440,
      1,
      1,
      "2026-07-21T15:18:00.000Z",
      null,
      DEMO_AS_OF,
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO monitors
      (id, mission_id, status, schedule, materiality_threshold,
       minimum_confidence, required_source_count, topic_allowlist_json,
       topic_blocklist_json, entity_watchlist_json, alert_cooldown_minutes,
       contradiction_alerts, source_failure_alerts, last_checked_at,
       next_check_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "monitor-developer",
      "mission-developer-platforms",
      "ACTIVE",
      "HOURLY",
      0.64,
      0.76,
      2,
      JSON.stringify(["api", "observability"]),
      JSON.stringify([]),
      JSON.stringify(["Forge Retrieval", "Orbit Query"]),
      240,
      1,
      1,
      "2026-07-23T12:02:00.000Z",
      "2026-07-23T13:02:00.000Z",
      DEMO_AS_OF,
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO alerts
      (id, monitor_id, insight_id, alert_type, title, summary, status,
       materiality_score, created_at, delivered_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "alert-01",
      "monitor-enterprise",
      "insight-02",
      "MATERIAL_CHANGE",
      "Analytics capability gap strengthened",
      "Two additional fictional sources now support the query-diagnostics gap.",
      "UNREAD",
      0.87,
      DEMO_AS_OF,
      DEMO_AS_OF,
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO alerts
      (id, monitor_id, insight_id, alert_type, title, summary, status,
       materiality_score, created_at, delivered_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "alert-02",
      "monitor-enterprise",
      "insight-05",
      "CONTRADICTION",
      "Benchmark claim requires validation",
      "The benchmark methodology excludes scanned documents and lacks reproduction.",
      "READ",
      0.62,
      "2026-07-22T16:10:00.000Z",
      "2026-07-22T16:10:00.000Z",
    ],
  ),
  statement(
    `INSERT OR IGNORE INTO alerts
      (id, monitor_id, insight_id, alert_type, title, summary, status,
       materiality_score, created_at, delivered_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "alert-03",
      "monitor-developer",
      "insight-08",
      "KNOWLEDGE_GAP",
      "Batch export remains unconfirmed",
      "Primary documentation still labels batch export as planned.",
      "UNREAD",
      0.65,
      "2026-07-23T12:30:00.000Z",
      "2026-07-23T12:30:00.000Z",
    ],
  ),
  ...[
    [
      "report-executive-01",
      "mission-enterprise-search",
      "run-enterprise-0421",
      "EXECUTIVE_BRIEF",
      "Enterprise search launch impact — executive brief",
      "# Executive brief\n\nThe deterministic demo corpus supports three material conclusions: governance is becoming table stakes, advanced analytics remains the clearest capability gap, and predictable mid-market packaging is an actionable opening.\n\n## Recommended actions\n\n1. Commit governed citation controls as a release criterion.\n2. Prioritize exportable query diagnostics.\n3. Test capacity-capped packaging with guided defaults.\n\n## Limitations\n\nAll records are fictional DEMO evidence and must be replaced by connected sources before external decision use.",
    ],
    [
      "report-matrix-01",
      "mission-enterprise-search",
      "run-enterprise-0421",
      "COMPETITOR_MATRIX",
      "Enterprise retrieval capability matrix",
      "Capability,Observed state,Confidence\nGovernance controls,Common,0.94\nAdvanced analytics,Premium-plan concentration,0.91\nPredictable pricing,Uneven,0.84\nRegional controls,Expanding,0.88",
    ],
    [
      "report-json-01",
      "mission-mid-market",
      "run-midmarket-0317",
      "JSON_PACKAGE",
      "Mid-market evidence package",
      '{"status":"demo","is_demo":true,"mission_id":"mission-mid-market","generated_at":"2026-07-22T18:30:00.000Z","limitations":["Fictional deterministic corpus"]}',
    ],
  ].map(([id, missionId, runId, type, title, content]) =>
    statement(
      `INSERT OR IGNORE INTO reports
        (id, mission_id, research_run_id, type, status, title, content,
         generated_at, generated_by_id, data_status, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id,
        missionId,
        runId,
        type,
        "READY",
        title,
        content,
        DEMO_AS_OF,
        "user-alex-parker",
        "demo",
        1,
      ],
    ),
  ),
  ...agents.map(
    ([id, name, type, purpose, promptName, outputSchema, allowedTools]) =>
      statement(
        `INSERT OR IGNORE INTO agent_definitions
          (id, workspace_id, name, agent_type, purpose, status, prompt_name,
           prompt_version, model, allowed_tools_json, output_schema, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          id,
          DEMO_WORKSPACE_ID,
          name,
          type,
          purpose,
          "ACTIVE",
          promptName,
          "1.0.0",
          "deterministic-mock-v1",
          allowedTools,
          outputSchema,
          DEMO_AS_OF,
        ],
      ),
  ),
  statement(
    `INSERT OR IGNORE INTO audit_logs
      (id, workspace_id, user_id, action, entity_type, entity_id,
       details_json, request_id, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      "audit-seed-01",
      DEMO_WORKSPACE_ID,
      "user-alex-parker",
      "DEMO_WORKSPACE_INITIALIZED",
      "WORKSPACE",
      DEMO_WORKSPACE_ID,
      JSON.stringify({
        dataStatus: "demo",
        isDemo: true,
        source: "IntelBridge deterministic fixture",
      }),
      "request-demo-seed",
      fixedCreatedAt,
    ],
  ),
];

export const seedStatements: BootstrapStatement[] = [
  ...baseSeedStatements,
  ...runSeedStatements,
  ...documentSeedStatements,
  ...evidenceSeedStatements,
  ...claimSeedStatements,
  ...claimEvidenceSeedStatements,
  ...insightSeedStatements,
  ...insightClaimSeedStatements,
  ...operationsSeedStatements,
];
