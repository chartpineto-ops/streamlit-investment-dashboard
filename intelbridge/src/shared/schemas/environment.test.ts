import { describe, expect, it } from "vitest";

import { parseServerEnvironment } from "@/shared/schemas/environment";

describe("parseServerEnvironment", () => {
  it("accepts the documented Sites configuration", () => {
    const environment = parseServerEnvironment({
      AI_PROVIDER: "mock",
      INTELBRIDGE_DEMO_USER_EMAIL: "alex.parker@intelbridge.demo",
      NODE_ENV: "test",
    });

    expect(environment.AI_PROVIDER).toBe("mock");
    expect(environment.NODE_ENV).toBe("test");
  });

  it("rejects an unsupported AI provider", () => {
    expect(() =>
      parseServerEnvironment({
        AI_PROVIDER: "unsupported",
      }),
    ).toThrow();
  });
});
