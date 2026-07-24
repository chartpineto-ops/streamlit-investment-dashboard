import { RunStatus, type RunStatus as RunStatusType } from "@/shared/domain";

const allowedTransitions: Record<RunStatusType, readonly RunStatusType[]> = {
  [RunStatus.QUEUED]: [RunStatus.RUNNING, RunStatus.CANCELLED],
  [RunStatus.RUNNING]: [
    RunStatus.CANCEL_REQUESTED,
    RunStatus.COMPLETED,
    RunStatus.PARTIALLY_COMPLETED,
    RunStatus.FAILED,
  ],
  [RunStatus.CANCEL_REQUESTED]: [RunStatus.CANCELLED],
  [RunStatus.CANCELLED]: [],
  [RunStatus.COMPLETED]: [],
  [RunStatus.PARTIALLY_COMPLETED]: [],
  [RunStatus.FAILED]: [],
};

export function canTransitionRun(current: RunStatusType, next: RunStatusType) {
  return allowedTransitions[current].includes(next);
}

export function assertRunTransition(
  current: RunStatusType,
  next: RunStatusType,
) {
  if (!canTransitionRun(current, next)) {
    throw new Error("INVALID_RUN_TRANSITION");
  }
}

export function canRetryRun(status: RunStatusType) {
  return (
    status === RunStatus.CANCELLED ||
    status === RunStatus.FAILED ||
    status === RunStatus.PARTIALLY_COMPLETED
  );
}

export function isTerminalRunStatus(status: string) {
  return (
    status === RunStatus.CANCELLED ||
    status === RunStatus.COMPLETED ||
    status === RunStatus.FAILED ||
    status === RunStatus.PARTIALLY_COMPLETED
  );
}
