import { describe, expect, it } from "vitest";

import { createMissionSchema } from "@/shared/schemas/mission";

describe("createMissionSchema", () => {
  it("normalizes a complete Milestone 1 mission input", () => {
    const result = createMissionSchema.parse({
      connectorIds: ["connector-demo"],
      focusAreas: ["Products", "Pricing"],
      monitoringMode: "MANUAL",
      objective:
        "Assess the material product and pricing changes supported by the approved research sources.",
      projectId: "project-competitive-intelligence",
      regions: ["Global"],
      researchDepth: "DEEP",
      timeHorizonMonths: 12,
      title: "Competitive launch assessment",
    });

    expect(result.focusAreas).toEqual(["Products", "Pricing"]);
    expect(result.timeHorizonMonths).toBe(12);
  });

  it("rejects an objective too short to be accountable", () => {
    expect(() =>
      createMissionSchema.parse({
        connectorIds: ["connector-demo"],
        focusAreas: ["Products"],
        monitoringMode: "MANUAL",
        objective: "Research competitors.",
        projectId: "project-competitive-intelligence",
        regions: ["Global"],
        researchDepth: "DEEP",
        timeHorizonMonths: 12,
        title: "Competitive launch assessment",
      }),
    ).toThrow();
  });
});
