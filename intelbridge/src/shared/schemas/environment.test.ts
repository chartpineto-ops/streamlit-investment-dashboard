import { describe, expect, it } from "vitest";

import { parseServerEnvironment } from "@/shared/schemas/environment";

describe("parseServerEnvironment", () => {
  it("accepts the documented local PostgreSQL configuration", () => {
    const environment = parseServerEnvironment({
      AI_PROVIDER: "mock",
      DATABASE_URL:
        "postgresql://intelbridge:local@localhost:5434/intelbridge?schema=public",
      DIRECT_URL:
        "postgresql://intelbridge:local@localhost:5434/intelbridge?schema=public",
      INTELBRIDGE_DEMO_USER_EMAIL: "alex.parker@intelbridge.demo",
      NODE_ENV: "test",
    });

    expect(environment.AI_PROVIDER).toBe("mock");
    expect(environment.NODE_ENV).toBe("test");
  });

  it("rejects a non-PostgreSQL database URL", () => {
    expect(() =>
      parseServerEnvironment({
        DATABASE_URL: "file:./intelbridge.db",
      }),
    ).toThrow();
  });
});
