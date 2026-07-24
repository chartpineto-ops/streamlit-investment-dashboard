import { env } from "cloudflare:workers";

import { BaseConnectorAdapter } from "@/server/connectors/base";
import {
  decodePdfBytes,
  decodeUtf8,
  normalizeRetrievedDocument,
} from "@/server/connectors/normalize";
import type {
  ConnectorContext,
  DiscoveredItem,
  DiscoveryInput,
} from "@/server/connectors/types";
import { ConnectorType } from "@/shared/domain";

type R2ObjectBody = {
  arrayBuffer(): Promise<ArrayBuffer>;
};

type UploadItem = {
  externalId: string;
  fileName: string;
  mimeType: string;
  storageKey: string;
  uploadedAt: string;
};

export class FileUploadConnectorAdapter extends BaseConnectorAdapter {
  readonly type = ConnectorType.FILE_UPLOAD;

  async testConnection(context: ConnectorContext) {
    void context;
    return {
      message: "The managed upload store is available.",
      ok: Boolean(
        (env as { FILES?: { get(key: string): Promise<R2ObjectBody | null> } })
          .FILES,
      ),
      responseTimeMs: 1,
      testedAt: new Date().toISOString(),
    };
  }

  async discover(input: DiscoveryInput, context: ConnectorContext) {
    void input;
    const uploads =
      (context.configuration.uploads as UploadItem[] | undefined) ?? [];
    return {
      items: uploads.map(
        (upload): DiscoveredItem => ({
          externalId: upload.externalId,
          metadata: upload,
          publishedAt: upload.uploadedAt,
          title: upload.fileName,
        }),
      ),
      nextCheckpoint: {
        externalIds: uploads.map((upload) => upload.externalId),
        retrievedAt: new Date().toISOString(),
      },
    };
  }

  async retrieve(item: DiscoveredItem, context: ConnectorContext) {
    void context;
    const storageKey = String(item.metadata.storageKey ?? "");
    const bucket = (
      env as {
        FILES?: { get(key: string): Promise<R2ObjectBody | null> };
      }
    ).FILES;
    const object = await bucket?.get(storageKey);
    if (!object) throw new Error("SOURCE_FILE_NOT_FOUND");
    const bytes = await object.arrayBuffer();
    const mimeType = String(item.metadata.mimeType ?? "text/plain");
    return {
      externalId: item.externalId,
      metadata: item.metadata,
      mimeType,
      publishedAt: item.publishedAt,
      publisher: "Workspace upload",
      rawContent:
        mimeType === "application/pdf"
          ? decodePdfBytes(bytes)
          : decodeUtf8(bytes),
      title: item.title,
    };
  }

  async normalize(document: Parameters<BaseConnectorAdapter["normalize"]>[0]) {
    return normalizeRetrievedDocument(document);
  }
}
