import { getDatabase } from "@/server/db/client";
import type { NormalizedDocument } from "@/server/connectors/types";

export async function sha256(value: string | ArrayBuffer) {
  const input =
    typeof value === "string" ? new TextEncoder().encode(value) : value;
  const digest = await crypto.subtle.digest("SHA-256", input);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export type PersistedDocumentResult = {
  change: "created" | "unchanged" | "updated";
  documentId: string;
  versionId: string | null;
  versionNumber: number;
};

export async function persistNormalizedDocument(input: {
  connectorId: string;
  dataStatus: "demo" | "live";
  document: NormalizedDocument;
  isDemo: boolean;
  missionId: string;
  researchRunId: string;
  storageKey?: string;
  workspaceId: string;
}): Promise<PersistedDocumentResult> {
  const database = await getDatabase();
  const retrievedAt = new Date().toISOString();
  const contentHash =
    typeof input.document.metadata.contentHash === "string"
      ? input.document.metadata.contentHash
      : await sha256(input.document.normalizedContent);
  const canonicalUrl =
    input.document.canonicalUrl ??
    `intelbridge://${input.connectorId}/${encodeURIComponent(input.document.externalId)}`;
  const previous = await database
    .prepare(
      `SELECT id, content_hash, version
       FROM source_documents
       WHERE workspace_id = ? AND connector_id = ?
         AND (external_id = ? OR canonical_url = ?)
       ORDER BY version DESC
       LIMIT 1`,
    )
    .bind(
      input.workspaceId,
      input.connectorId,
      input.document.externalId,
      canonicalUrl,
    )
    .first<{ content_hash: string; id: string; version: number }>();

  if (previous?.content_hash === contentHash) {
    await database
      .prepare(
        `UPDATE source_documents
         SET last_retrieved_at = ?, retrieved_at = ?, last_research_run_id = ?,
             change_status = 'UNCHANGED', metadata_json = ?
         WHERE id = ?`,
      )
      .bind(
        retrievedAt,
        retrievedAt,
        input.researchRunId,
        JSON.stringify(input.document.metadata),
        previous.id,
      )
      .run();
    return {
      change: "unchanged",
      documentId: previous.id,
      versionId: null,
      versionNumber: Number(previous.version),
    };
  }

  const documentId = previous?.id ?? `document-${crypto.randomUUID()}`;
  const versionNumber = Number(previous?.version ?? 0) + 1;
  const versionId = `version-${crypto.randomUUID()}`;
  const publishedAt = input.document.publishedAt ?? retrievedAt;
  const publisher =
    input.document.publisher ??
    (input.document.canonicalUrl
      ? new URL(input.document.canonicalUrl).hostname
      : "Uploaded source");
  const promptInjectionFlag =
    input.document.metadata.promptInjectionFlag === true ? 1 : 0;
  const trustState =
    typeof input.document.metadata.trustState === "string"
      ? input.document.metadata.trustState
      : "UNTRUSTED_SOURCE";
  const metadataJson = JSON.stringify(input.document.metadata);
  const storedRawContent = input.storageKey
    ? `[Raw object stored in R2: ${input.storageKey}]`
    : input.document.rawContent;

  if (previous) {
    await database.batch([
      database
        .prepare(
          `INSERT INTO source_document_versions
            (id, source_document_id, research_run_id, version_number,
             content_hash, raw_content, normalized_content, mime_type,
             language, metadata_json, storage_key, retrieved_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .bind(
          versionId,
          documentId,
          input.researchRunId,
          versionNumber,
          contentHash,
          storedRawContent,
          input.document.normalizedContent,
          input.document.mimeType,
          input.document.language ?? null,
          metadataJson,
          input.storageKey ?? null,
          retrievedAt,
          retrievedAt,
        ),
      database
        .prepare(
          `UPDATE source_documents
           SET mission_id = ?, external_id = ?, canonical_url = ?, title = ?,
               author = ?, publisher = ?, source_type = ?, published_at = ?,
               retrieved_at = ?, content_hash = ?, raw_content = ?,
               normalized_content = ?, metadata_json = ?, version = ?,
               trust_state = ?, prompt_injection_flag = ?, data_status = ?,
               is_demo = ?, current_version_id = ?, last_retrieved_at = ?,
               last_research_run_id = ?, change_status = 'UPDATED'
           WHERE id = ?`,
        )
        .bind(
          input.missionId,
          input.document.externalId,
          canonicalUrl,
          input.document.title,
          input.document.author ?? null,
          publisher,
          input.document.mimeType,
          publishedAt,
          retrievedAt,
          contentHash,
          storedRawContent,
          input.document.normalizedContent,
          metadataJson,
          versionNumber,
          trustState,
          promptInjectionFlag,
          input.dataStatus,
          input.isDemo ? 1 : 0,
          versionId,
          retrievedAt,
          input.researchRunId,
          documentId,
        ),
    ]);
    return {
      change: "updated",
      documentId,
      versionId,
      versionNumber,
    };
  }

  await database.batch([
    database
      .prepare(
        `INSERT INTO source_documents
          (id, workspace_id, mission_id, connector_id, external_id,
           canonical_url, title, author, publisher, source_type, published_at,
           retrieved_at, content_hash, raw_content, normalized_content,
           metadata_json, version, trust_state, prompt_injection_flag,
           data_status, is_demo, current_version_id, first_retrieved_at,
           last_retrieved_at, last_research_run_id, change_status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                 ?, NULL, ?, ?, ?, 'CREATED')`,
      )
      .bind(
        documentId,
        input.workspaceId,
        input.missionId,
        input.connectorId,
        input.document.externalId,
        canonicalUrl,
        input.document.title,
        input.document.author ?? null,
        publisher,
        input.document.mimeType,
        publishedAt,
        retrievedAt,
        contentHash,
        storedRawContent,
        input.document.normalizedContent,
        metadataJson,
        versionNumber,
        trustState,
        promptInjectionFlag,
        input.dataStatus,
        input.isDemo ? 1 : 0,
        retrievedAt,
        retrievedAt,
        input.researchRunId,
      ),
    database
      .prepare(
        `INSERT INTO source_document_versions
          (id, source_document_id, research_run_id, version_number,
           content_hash, raw_content, normalized_content, mime_type, language,
           metadata_json, storage_key, retrieved_at, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        versionId,
        documentId,
        input.researchRunId,
        versionNumber,
        contentHash,
        input.document.rawContent,
        input.document.normalizedContent,
        input.document.mimeType,
        input.document.language ?? null,
        metadataJson,
        input.storageKey ?? null,
        retrievedAt,
        retrievedAt,
      ),
    database
      .prepare(
        `UPDATE source_documents SET current_version_id = ? WHERE id = ?`,
      )
      .bind(versionId, documentId),
  ]);
  return {
    change: "created",
    documentId,
    versionId,
    versionNumber,
  };
}

type DocumentRow = {
  author: string | null;
  canonical_url: string;
  change_status: string;
  connector_id: string;
  connector_name: string;
  content_hash: string;
  current_version_id: string | null;
  data_status: string;
  external_id: string;
  first_retrieved_at: string | null;
  id: string;
  is_demo: number;
  last_retrieved_at: string | null;
  metadata_json: string;
  mime_type: string;
  mission_id: string;
  mission_title: string;
  normalized_content: string;
  published_at: string;
  publisher: string;
  title: string;
  version: number;
};

function mapDocument(row: DocumentRow) {
  return {
    author: row.author,
    canonicalUrl: row.canonical_url,
    changeStatus: row.change_status,
    connector: { id: row.connector_id, name: row.connector_name },
    contentHash: row.content_hash,
    currentVersionId: row.current_version_id,
    dataStatus: row.data_status,
    externalId: row.external_id,
    firstRetrievedAt: row.first_retrieved_at,
    id: row.id,
    isDemo: Boolean(row.is_demo),
    lastRetrievedAt: row.last_retrieved_at,
    metadata: JSON.parse(row.metadata_json) as Record<string, unknown>,
    mimeType: row.mime_type,
    mission: { id: row.mission_id, title: row.mission_title },
    normalizedContent: row.normalized_content,
    publishedAt: row.published_at,
    publisher: row.publisher,
    title: row.title,
    version: Number(row.version),
  };
}

const documentSelect = `SELECT
  sd.id, sd.mission_id, sd.connector_id, sd.external_id, sd.canonical_url,
  sd.title, sd.author, sd.publisher, sd.source_type AS mime_type,
  sd.published_at, sd.content_hash, sd.normalized_content, sd.metadata_json,
  sd.version, sd.current_version_id, sd.first_retrieved_at,
  sd.last_retrieved_at, sd.change_status, sd.data_status, sd.is_demo,
  m.title AS mission_title, sc.name AS connector_name
FROM source_documents sd
INNER JOIN missions m ON m.id = sd.mission_id
INNER JOIN projects p ON p.id = m.project_id
INNER JOIN source_connectors sc ON sc.id = sd.connector_id`;

export async function listWorkspaceDocuments(
  workspaceId: string,
  filters: {
    change?: string;
    connectorId?: string;
    limit?: number;
    missionId?: string;
    query?: string;
    retrievedAfter?: string;
  } = {},
) {
  const database = await getDatabase();
  const conditions = ["p.workspace_id = ?"];
  const values: unknown[] = [workspaceId];
  if (filters.missionId) {
    conditions.push("sd.mission_id = ?");
    values.push(filters.missionId);
  }
  if (filters.connectorId) {
    conditions.push("sd.connector_id = ?");
    values.push(filters.connectorId);
  }
  if (filters.change) {
    conditions.push("sd.change_status = ?");
    values.push(filters.change);
  }
  if (filters.retrievedAfter) {
    conditions.push("sd.last_retrieved_at >= ?");
    values.push(filters.retrievedAfter);
  }
  if (filters.query) {
    conditions.push(
      "(LOWER(sd.title) LIKE ? OR LOWER(sd.normalized_content) LIKE ?)",
    );
    const query = `%${filters.query.toLowerCase()}%`;
    values.push(query, query);
  }
  values.push(filters.limit ?? 50);
  const result = await database
    .prepare(
      `${documentSelect}
       WHERE ${conditions.join(" AND ")}
       ORDER BY sd.last_retrieved_at DESC, sd.id ASC
       LIMIT ?`,
    )
    .bind(...values)
    .all<DocumentRow>();
  return result.results.map(mapDocument);
}

export async function getWorkspaceDocument(
  workspaceId: string,
  documentId: string,
) {
  const database = await getDatabase();
  const row = await database
    .prepare(
      `${documentSelect}
       WHERE p.workspace_id = ? AND sd.id = ?
       LIMIT 1`,
    )
    .bind(workspaceId, documentId)
    .first<DocumentRow>();
  if (!row) {
    return null;
  }
  const versions = await database
    .prepare(
      `SELECT id, research_run_id, version_number, content_hash,
              normalized_content, mime_type, language, metadata_json,
              storage_key, retrieved_at, created_at
       FROM source_document_versions
       WHERE source_document_id = ?
       ORDER BY version_number DESC`,
    )
    .bind(documentId)
    .all<{
      content_hash: string;
      created_at: string;
      id: string;
      language: string | null;
      metadata_json: string;
      mime_type: string;
      normalized_content: string;
      research_run_id: string | null;
      retrieved_at: string;
      storage_key: string | null;
      version_number: number;
    }>();
  return {
    document: mapDocument(row),
    versions: versions.results.map((version) => ({
      contentHash: version.content_hash,
      createdAt: version.created_at,
      id: version.id,
      language: version.language,
      metadata: JSON.parse(version.metadata_json) as Record<string, unknown>,
      mimeType: version.mime_type,
      normalizedContent: version.normalized_content,
      researchRunId: version.research_run_id,
      retrievedAt: version.retrieved_at,
      storageKey: version.storage_key,
      versionNumber: Number(version.version_number),
    })),
  };
}

export async function getWorkspaceDocumentVersion(
  workspaceId: string,
  documentId: string,
  versionId: string,
) {
  const detail = await getWorkspaceDocument(workspaceId, documentId);
  return detail?.versions.find((version) => version.id === versionId) ?? null;
}
