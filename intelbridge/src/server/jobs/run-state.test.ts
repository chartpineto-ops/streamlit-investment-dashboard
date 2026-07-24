import { describe, expect, it } from "vitest";

import {
  assertRunTransition,
  canRetryRun,
  canTransitionRun,
  isTerminalRunStatus,
} from "@/server/jobs/run-state";

describe("research run state machine", () => {
  it("allows only declared forward transitions", () => {
    expect(canTransitionRun("QUEUED", "RUNNING")).toBe(true);
    expect(canTransitionRun("RUNNING", "COMPLETED")).toBe(true);
    expect(canTransitionRun("COMPLETED", "RUNNING")).toBe(false);
    expect(() => assertRunTransition("QUEUED", "COMPLETED")).toThrow(
      "INVALID_RUN_TRANSITION",
    );
  });

  it("keeps retries immutable and terminal states explicit", () => {
    expect(canRetryRun("FAILED")).toBe(true);
    expect(canRetryRun("CANCELLED")).toBe(true);
    expect(canRetryRun("COMPLETED")).toBe(false);
    expect(isTerminalRunStatus("PARTIALLY_COMPLETED")).toBe(true);
    expect(isTerminalRunStatus("RUNNING")).toBe(false);
  });
});
