import { describe, expect, it } from "vitest";

import { calculateMateriality } from "@/shared/materiality";

describe("calculateMateriality", () => {
  it("multiplies the six documented normalized factors", () => {
    expect(
      calculateMateriality({
        confidence: 0.9,
        impact: 0.8,
        novelty: 0.7,
        relevance: 0.95,
        sourceQuality: 0.85,
        urgency: 0.75,
      }),
    ).toBeCloseTo(0.305235, 6);
  });

  it("clamps proposed factor values to the zero-to-one contract", () => {
    expect(
      calculateMateriality({
        confidence: 2,
        impact: 1,
        novelty: 1,
        relevance: 1,
        sourceQuality: 1,
        urgency: -0.2,
      }),
    ).toBe(0);
  });
});
