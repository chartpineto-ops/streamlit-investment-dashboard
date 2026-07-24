import { describe, expect, it } from "vitest";

import { DemoConnectorAdapter } from "@/server/connectors/demo";

describe("DemoConnectorAdapter", () => {
  it("normalizes retrieved source content with a stable hash", async () => {
    const adapter = new DemoConnectorAdapter();
    const context = {
      configuration: { type: "DEMO" },
      connectorId: "connector-demo",
      requestId: "request-test",
      workspaceId: "workspace-test",
    };
    const discovery = await adapter.discover(
      {
        missionId: "mission-test",
      },
      context,
    );
    const item = discovery.items[0]!;
    const retrieved = await adapter.retrieve(item, context);
    const first = await adapter.normalize(retrieved, context);
    const second = await adapter.normalize(retrieved, context);

    expect(first.metadata.contentHash).toBe(second.metadata.contentHash);
    expect(first.metadata.trustState).toBe("UNTRUSTED_SOURCE");
    expect(first.metadata.promptInjectionFlag).toBe(false);
  });
});
