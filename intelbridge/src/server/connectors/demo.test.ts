import { describe, expect, it } from "vitest";

import { DemoConnectorAdapter } from "@/server/connectors/demo";

describe("DemoConnectorAdapter", () => {
  it("persists and returns a connector checkpoint", async () => {
    const adapter = new DemoConnectorAdapter();
    const checkpoint = {
      cursor: "demo-cursor-1",
      updatedAt: "2026-07-22T18:30:00.000Z",
      version: 1,
    };

    expect(await adapter.getCheckpoint()).toBeNull();
    await adapter.saveCheckpoint(checkpoint);
    expect(await adapter.getCheckpoint()).toEqual(checkpoint);
  });

  it("normalizes retrieved source content with a stable hash", async () => {
    const adapter = new DemoConnectorAdapter();
    const [item] = await adapter.discover({
      missionId: "mission-test",
    });
    const retrieved = await adapter.retrieve(item);
    const first = await adapter.normalize(retrieved);
    const second = await adapter.normalize(retrieved);

    expect(first.contentHash).toBe(second.contentHash);
    expect(first.trustState).toBe("UNTRUSTED_SOURCE");
    expect(first.promptInjectionFlag).toBe(false);
  });
});
