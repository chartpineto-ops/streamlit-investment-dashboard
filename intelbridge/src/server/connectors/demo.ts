import {
  containsPromptInjectionPattern,
  stripUntrustedMarkup,
} from "@/server/connectors/security";
import type {
  ConnectorCheckpoint,
  DiscoveredItem,
  DiscoveryInput,
  RetrievedDocument,
  SourceConnectorAdapter,
} from "@/server/connectors/types";

const item: DiscoveredItem = {
  externalId: "demo-governance-update",
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
  private checkpoint: ConnectorCheckpoint | null = null;

  async testConnection() {
    return {
      message: "Deterministic fictional source is available.",
      ok: true,
      testedAt: "2026-07-22T18:30:00.000Z",
    };
  }

  async discover(input: DiscoveryInput) {
    void input;
    return [item];
  }

  async retrieve(discovered: DiscoveredItem): Promise<RetrievedDocument> {
    return {
      ...discovered,
      contentType: "text/plain",
      rawContent:
        "Fictional documentation states that governed citation controls are available to enterprise administrators.",
      retrievedAt: "2026-07-22T18:30:00.000Z",
    };
  }

  async normalize(document: RetrievedDocument) {
    const normalizedContent = stripUntrustedMarkup(document.rawContent);
    return {
      ...document,
      contentHash: await sha256(normalizedContent),
      normalizedContent,
      promptInjectionFlag: containsPromptInjectionPattern(normalizedContent),
      trustState: "UNTRUSTED_SOURCE" as const,
    };
  }

  async getCheckpoint() {
    return this.checkpoint;
  }

  async saveCheckpoint(checkpoint: ConnectorCheckpoint) {
    this.checkpoint = checkpoint;
  }
}
