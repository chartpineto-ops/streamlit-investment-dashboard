import { describe, expect, it } from "vitest";

import { validateGroundedAnswerForEvidence } from "@/server/agents/provider";

const evidence = [
  {
    confidence: 0.9,
    evidenceId: "evidence-1",
    excerpt: "A source-bound excerpt.",
    publishedAt: "2026-07-22T12:00:00.000Z",
    publisher: "Fictional Publisher",
    sourceUrl: "https://publisher.example/source",
  },
];

describe("grounded answer validation", () => {
  it("rejects a citation that was not included in model context", () => {
    expect(() =>
      validateGroundedAnswerForEvidence(
        {
          citationEvidenceIds: ["evidence-invented"],
          confidence: 0.9,
          establishedFacts: ["Unsupported"],
          inference: "Unsupported",
          limitations: "None",
        },
        evidence,
      ),
    ).toThrow("MODEL_CITATION_NOT_IN_CONTEXT");
  });

  it("requires citations for established facts", () => {
    expect(() =>
      validateGroundedAnswerForEvidence(
        {
          citationEvidenceIds: [],
          confidence: 0.5,
          establishedFacts: ["A fact"],
          inference: "Inference",
          limitations: "Limited",
        },
        evidence,
      ),
    ).toThrow("MODEL_FACTS_REQUIRE_CITATIONS");
  });
});
