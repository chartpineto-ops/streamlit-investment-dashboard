import { env } from "cloudflare:workers";

import {
  containsPromptInjectionPattern,
  stripUntrustedMarkup,
  validatePublicUrl,
} from "@/server/connectors/security";
import { getDatabase } from "@/server/db/client";

const MAX_REMOTE_BYTES = 1_000_000;
const MAX_UPLOAD_BYTES = 10_000_000;
const TEXT_UPLOAD_BYTES = 500_000;

const remoteContentTypes = [
  "application/atom+xml",
  "application/json",
  "application/rss+xml",
  "application/xml",
  "text/csv",
  "text/html",
  "text/markdown",
  "text/plain",
] as const;

const uploadContentTypes = [...remoteContentTypes, "application/pdf"] as const;

interface R2BucketLike {
  put(
    key: string,
    value: ArrayBuffer,
    options?: {
      httpMetadata?: { contentType?: string };
    },
  ): Promise<unknown>;
}

async function sha256(value: string | ArrayBuffer) {
  const input =
    typeof value === "string" ? new TextEncoder().encode(value) : value;
  const digest = await crypto.subtle.digest("SHA-256", input);
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function titleFromHtml(value: string) {
  const match = value.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  return match ? stripUntrustedMarkup(match[1]).slice(0, 180) : null;
}

function assertAllowedContentType(
  contentType: string,
  allowlist: readonly string[],
) {
  const normalized = contentType.split(";")[0]?.trim().toLowerCase();
  if (!normalized || !allowlist.includes(normalized)) {
    throw new Error("SOURCE_CONTENT_TYPE_UNSUPPORTED");
  }
  return normalized;
}

async function assertMissionScope(workspaceId: string, missionId: string) {
  const database = await getDatabase();
  const mission = await database
    .prepare(
      `SELECT m.id
       FROM missions m
       INNER JOIN projects p ON p.id = m.project_id
       WHERE p.workspace_id = ? AND m.id = ?
       LIMIT 1`,
    )
    .bind(workspaceId, missionId)
    .first<{ id: string }>();

  if (!mission) {
    throw new Error("MISSION_NOT_FOUND");
  }
  return database;
}

async function persistDocument(input: {
  canonicalUrl: string;
  connectorId: string;
  contentHash: string;
  dataStatus: "live" | "demo";
  externalId: string;
  isDemo: boolean;
  metadata: Record<string, unknown>;
  missionId: string;
  normalizedContent: string;
  promptInjectionFlag: boolean;
  publishedAt: string;
  publisher: string;
  rawContent: string;
  sourceType: string;
  title: string;
  workspaceId: string;
}) {
  const database = await assertMissionScope(input.workspaceId, input.missionId);
  const previous = await database
    .prepare(
      `SELECT id, content_hash, version
       FROM source_documents
       WHERE workspace_id = ? AND canonical_url = ?
       ORDER BY version DESC
       LIMIT 1`,
    )
    .bind(input.workspaceId, input.canonicalUrl)
    .first<{ content_hash: string; id: string; version: number }>();

  if (previous?.content_hash === input.contentHash) {
    return { changeState: "UNCHANGED" as const, id: previous.id };
  }

  const documentId = `document-${crypto.randomUUID()}`;
  const retrievedAt = new Date().toISOString();
  const version = Number(previous?.version ?? 0) + 1;
  await database.batch([
    database
      .prepare(
        `INSERT INTO source_documents
          (id, workspace_id, mission_id, connector_id, external_id,
           canonical_url, title, author, publisher, source_type, published_at,
           retrieved_at, content_hash, raw_content, normalized_content,
           metadata_json, version, trust_state, prompt_injection_flag,
           data_status, is_demo)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        documentId,
        input.workspaceId,
        input.missionId,
        input.connectorId,
        input.externalId,
        input.canonicalUrl,
        input.title,
        null,
        input.publisher,
        input.sourceType,
        input.publishedAt,
        retrievedAt,
        input.contentHash,
        input.rawContent,
        input.normalizedContent,
        JSON.stringify(input.metadata),
        version,
        "UNTRUSTED_SOURCE",
        input.promptInjectionFlag ? 1 : 0,
        input.dataStatus,
        input.isDemo ? 1 : 0,
      ),
    database
      .prepare(
        `UPDATE connector_configurations
         SET last_successful_sync_at = ?, last_error_at = NULL,
             checkpoint_json = ?, updated_at = ?
         WHERE connector_id = ?`,
      )
      .bind(
        retrievedAt,
        JSON.stringify({ canonicalUrl: input.canonicalUrl, version }),
        retrievedAt,
        input.connectorId,
      ),
  ]);

  return {
    changeState: previous ? ("CHANGED" as const) : ("NEW" as const),
    id: documentId,
  };
}

export async function ingestPublicUrl(input: {
  missionId: string;
  url: string;
  workspaceId: string;
}) {
  const canonicalUrl = validatePublicUrl(input.url);
  let currentUrl = canonicalUrl;
  let response: Response | null = null;

  for (let redirect = 0; redirect < 4; redirect += 1) {
    response = await fetch(currentUrl, {
      headers: {
        Accept:
          "text/html,text/plain,text/markdown,text/csv,application/json,application/rss+xml,application/atom+xml",
        "User-Agent": "IntelBridge/1.0 source retrieval",
      },
      redirect: "manual",
      signal: AbortSignal.timeout(8_000),
    });
    if (response.status < 300 || response.status >= 400) {
      break;
    }
    const location = response.headers.get("location");
    if (!location) {
      throw new Error("SOURCE_REDIRECT_INVALID");
    }
    currentUrl = validatePublicUrl(new URL(location, currentUrl).toString());
  }

  if (!response?.ok) {
    throw new Error("SOURCE_RETRIEVAL_FAILED");
  }

  const declaredLength = Number(response.headers.get("content-length") ?? 0);
  if (declaredLength > MAX_REMOTE_BYTES) {
    throw new Error("SOURCE_CONTENT_TOO_LARGE");
  }
  const contentType = assertAllowedContentType(
    response.headers.get("content-type") ?? "",
    remoteContentTypes,
  );
  const rawContent = await response.text();
  if (new TextEncoder().encode(rawContent).byteLength > MAX_REMOTE_BYTES) {
    throw new Error("SOURCE_CONTENT_TOO_LARGE");
  }
  const normalizedContent =
    contentType === "text/html"
      ? stripUntrustedMarkup(rawContent)
      : rawContent.replace(/\s+/g, " ").trim();
  const host = new URL(currentUrl).hostname;

  return persistDocument({
    canonicalUrl: currentUrl,
    connectorId: "connector-manual-url",
    contentHash: await sha256(normalizedContent),
    dataStatus: "live",
    externalId: `url-${await sha256(currentUrl)}`,
    isDemo: false,
    metadata: {
      contentType,
      fetchedFrom: currentUrl,
      retrievedBy: "manual-url-v1",
    },
    missionId: input.missionId,
    normalizedContent,
    promptInjectionFlag: containsPromptInjectionPattern(normalizedContent),
    publishedAt: new Date().toISOString(),
    publisher: host,
    rawContent,
    sourceType: contentType,
    title: titleFromHtml(rawContent) ?? host,
    workspaceId: input.workspaceId,
  });
}

export async function ingestUploadedFile(input: {
  file: File;
  missionId: string;
  workspaceId: string;
}) {
  if (input.file.size <= 0 || input.file.size > MAX_UPLOAD_BYTES) {
    throw new Error("SOURCE_FILE_SIZE_INVALID");
  }
  const contentType = assertAllowedContentType(
    input.file.type || "text/plain",
    uploadContentTypes,
  );
  const bytes = await input.file.arrayBuffer();
  const contentHash = await sha256(bytes);
  const objectKey = `${input.workspaceId}/${input.missionId}/${contentHash}/${input.file.name}`;
  const isText =
    contentType.startsWith("text/") ||
    ["application/json", "application/xml", "application/rss+xml"].includes(
      contentType,
    );
  let rawContent = "";
  let normalizedContent = "";
  let storage: "d1" | "r2" = "d1";

  if (isText && bytes.byteLength <= TEXT_UPLOAD_BYTES) {
    rawContent = new TextDecoder().decode(bytes);
    normalizedContent = rawContent.replace(/\s+/g, " ").trim();
  } else {
    const bucket = (env as unknown as { FILES?: R2BucketLike }).FILES;
    if (!bucket) {
      throw new Error("R2_BINDING_UNAVAILABLE");
    }
    await bucket.put(objectKey, bytes, {
      httpMetadata: { contentType },
    });
    storage = "r2";
    rawContent = `[Binary content stored in R2: ${objectKey}]`;
    normalizedContent =
      contentType === "application/pdf"
        ? "PDF uploaded successfully. Text extraction is unavailable in the Sites runtime; the document remains available for governed retrieval."
        : `Uploaded object stored in R2: ${input.file.name}`;
  }

  return persistDocument({
    canonicalUrl: `https://uploads.intelbridge.example/${encodeURIComponent(objectKey)}`,
    connectorId: "connector-file-upload",
    contentHash,
    dataStatus: "live",
    externalId: objectKey,
    isDemo: false,
    metadata: {
      contentType,
      filename: input.file.name,
      objectKey: storage === "r2" ? objectKey : null,
      size: input.file.size,
      storage,
    },
    missionId: input.missionId,
    normalizedContent,
    promptInjectionFlag:
      isText && containsPromptInjectionPattern(normalizedContent),
    publishedAt: new Date(input.file.lastModified || Date.now()).toISOString(),
    publisher: "User upload",
    rawContent,
    sourceType: contentType,
    title: input.file.name,
    workspaceId: input.workspaceId,
  });
}
