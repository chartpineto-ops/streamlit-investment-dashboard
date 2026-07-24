import { env } from "cloudflare:workers";

import { getAuthContext } from "@/server/auth/context";
import { validatePublicUrl } from "@/server/connectors/security";
import { getDatabase } from "@/server/db/client";
import { sha256 } from "@/server/repositories/documents";
import { ConnectorType } from "@/shared/domain";

const MAX_UPLOAD_BYTES = 10_000_000;
const uploadContentTypes = new Set([
  "application/atom+xml",
  "application/json",
  "application/pdf",
  "application/rss+xml",
  "application/xml",
  "text/csv",
  "text/html",
  "text/markdown",
  "text/plain",
  "text/xml",
]);

interface R2BucketLike {
  put(
    key: string,
    value: ArrayBuffer,
    options?: { httpMetadata?: { contentType?: string } },
  ): Promise<unknown>;
}

async function getAssignedConnector(input: {
  connectorId?: string;
  missionId: string;
  type: string;
  workspaceId: string;
}) {
  const database = await getDatabase();
  const connector = await database
    .prepare(
      `SELECT sc.id, cc.configuration_json
       FROM mission_sources ms
       INNER JOIN source_connectors sc ON sc.id = ms.source_connector_id
       INNER JOIN missions m ON m.id = ms.mission_id
       INNER JOIN projects p ON p.id = m.project_id
       LEFT JOIN connector_configurations cc ON cc.connector_id = sc.id
       WHERE p.workspace_id = ? AND m.id = ? AND sc.type = ?
         AND sc.status = 'CONNECTED'
         AND (? IS NULL OR sc.id = ?)
       ORDER BY ms.priority DESC
       LIMIT 1`,
    )
    .bind(
      input.workspaceId,
      input.missionId,
      input.type,
      input.connectorId ?? null,
      input.connectorId ?? null,
    )
    .first<{ configuration_json: string | null; id: string }>();
  if (!connector) {
    throw new Error("CONNECTOR_NOT_FOUND");
  }
  return {
    configuration: JSON.parse(connector.configuration_json ?? "{}") as Record<
      string,
      unknown
    >,
    database,
    id: connector.id,
  };
}

export async function registerPublicUrl(input: {
  connectorId?: string;
  missionId: string;
  url: string;
  workspaceId: string;
}) {
  const url = validatePublicUrl(input.url);
  const connector = await getAssignedConnector({
    ...input,
    type: ConnectorType.MANUAL_URL,
  });
  const urls = new Set(
    Array.isArray(connector.configuration.urls)
      ? (connector.configuration.urls as string[])
      : [],
  );
  urls.add(url);
  const configuration = {
    ...connector.configuration,
    type: ConnectorType.MANUAL_URL,
    urls: [...urls].slice(-100),
  };
  const now = new Date().toISOString();
  await connector.database
    .prepare(
      `UPDATE connector_configurations
       SET configuration_json = ?, updated_at = ?
       WHERE connector_id = ?`,
    )
    .bind(JSON.stringify(configuration), now, connector.id)
    .run();
  return { connectorId: connector.id, queuedForNextRun: true, url };
}

export async function registerUploadedFile(input: {
  connectorId?: string;
  file: File;
  missionId: string;
  workspaceId: string;
}) {
  if (input.file.size <= 0 || input.file.size > MAX_UPLOAD_BYTES) {
    throw new Error("SOURCE_FILE_SIZE_INVALID");
  }
  const mimeType = (input.file.type || "text/plain")
    .split(";")[0]
    .trim()
    .toLowerCase();
  if (!uploadContentTypes.has(mimeType)) {
    throw new Error("SOURCE_CONTENT_TYPE_UNSUPPORTED");
  }
  const connector = await getAssignedConnector({
    ...input,
    type: ConnectorType.FILE_UPLOAD,
  });
  const bucket = (env as { FILES?: R2BucketLike }).FILES;
  if (!bucket) {
    throw new Error("R2_BINDING_UNAVAILABLE");
  }
  const bytes = await input.file.arrayBuffer();
  const contentHash = await sha256(bytes);
  const safeFileName = input.file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const storageKey = `${input.workspaceId}/${connector.id}/${contentHash}/${safeFileName}`;
  await bucket.put(storageKey, bytes, {
    httpMetadata: { contentType: mimeType },
  });

  const uploads = Array.isArray(connector.configuration.uploads)
    ? (connector.configuration.uploads as Record<string, unknown>[])
    : [];
  const uploadedAt = new Date().toISOString();
  const upload = {
    contentHash,
    externalId: `upload:${contentHash}`,
    fileName: input.file.name,
    mimeType,
    size: input.file.size,
    storageKey,
    uploadedAt,
  };
  const configuration = {
    ...connector.configuration,
    type: ConnectorType.FILE_UPLOAD,
    uploads: [
      ...uploads.filter((candidate) => candidate.contentHash !== contentHash),
      upload,
    ].slice(-100),
  };
  await connector.database
    .prepare(
      `UPDATE connector_configurations
       SET configuration_json = ?, updated_at = ?
       WHERE connector_id = ?`,
    )
    .bind(JSON.stringify(configuration), uploadedAt, connector.id)
    .run();
  return {
    connectorId: connector.id,
    contentHash,
    fileName: input.file.name,
    mimeType,
    queuedForNextRun: true,
    size: input.file.size,
    storageKey,
  };
}

// Compatibility wrappers keep existing server actions on the governed queue.
export function ingestPublicUrl(input: {
  missionId: string;
  url: string;
  workspaceId: string;
}) {
  return registerPublicUrl(input);
}

export function ingestUploadedFile(input: {
  file: File;
  missionId: string;
  workspaceId: string;
}) {
  return registerUploadedFile(input);
}

export async function registerPublicUrlForCurrentWorkspace(
  missionId: string,
  url: string,
) {
  const context = await getAuthContext();
  return registerPublicUrl({
    missionId,
    url,
    workspaceId: context.workspace.id,
  });
}

export async function registerUploadedFileForCurrentWorkspace(
  missionId: string,
  file: File,
) {
  const context = await getAuthContext();
  return registerUploadedFile({
    file,
    missionId,
    workspaceId: context.workspace.id,
  });
}
