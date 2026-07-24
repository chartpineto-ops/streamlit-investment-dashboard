import {
  containsPromptInjectionPattern,
  stripUntrustedMarkup,
} from "@/server/connectors/security";
import type {
  ConnectorContext,
  DiscoveredItem,
  DiscoveryInput,
  RetrievedDocument,
  SourceConnectorAdapter,
} from "@/server/connectors/types";
import { ConnectorType } from "@/shared/domain";

const item: DiscoveredItem = {
  externalId: "demo-governance-update",
  metadata: { fixture: "intelbridge-demo-v1" },
  publishedAt: "2026-07-22T12:00:00.000Z",
  title: "Fictional governance update",
  url: "https://demo-source.example/research/governance-update",
};

async function sha256(value: string) {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export class DemoConnectorAdapter implements SourceConnectorAdapter {
  readonly type = ConnectorType.DEMO;

  async testConnection(context: ConnectorContext) {
    void context;
    return {
      message: "Deterministic fictional source is available.",
      ok: true,
      responseTimeMs: 1,
      testedAt: "2026-07-22T18:30:00.000Z",
    };
  }

  async discover(input: DiscoveryInput, context: ConnectorContext) {
    void input;
    void context;
    return {
      items: [item],
      nextCheckpoint: {
        externalId: item.externalId,
        publishedAt: item.publishedAt,
      },
    };
  }

  async retrieve(
    discovered: DiscoveredItem,
    context: ConnectorContext,
  ): Promise<RetrievedDocument> {
    void context;
    return {
      canonicalUrl: discovered.url,
      externalId: discovered.externalId,
      metadata: discovered.metadata,
      mimeType: "text/plain",
      publishedAt: discovered.publishedAt,
      publisher: "IntelBridge fictional fixture",
      rawContent:
        "Fictional documentation states that governed citation controls are available to enterprise administrators.",
      title: discovered.title,
    };
  }

  async normalize(document: RetrievedDocument, context: ConnectorContext) {
    void context;
    const normalizedContent = stripUntrustedMarkup(document.rawContent);
    return {
      ...document,
      language: "en",
      metadata: {
        ...document.metadata,
        contentHash: await sha256(normalizedContent),
        promptInjectionFlag: containsPromptInjectionPattern(normalizedContent),
        trustState: "UNTRUSTED_SOURCE",
      },
      normalizedContent,
      title: document.title ?? "Fictional governance update",
    };
  }

  async getCheckpoint(connectorId: string, key: string) {
    const { getConnectorCheckpoint } =
      await import("@/server/connectors/checkpoints");
    return getConnectorCheckpoint(connectorId, key);
  }

  async saveCheckpoint(
    connectorId: string,
    key: string,
    value: Record<string, unknown>,
  ) {
    const { saveConnectorCheckpoint } =
      await import("@/server/connectors/checkpoints");
    await saveConnectorCheckpoint(connectorId, key, value);
  }
}
