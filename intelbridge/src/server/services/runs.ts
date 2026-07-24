import { getAuthContext } from "@/server/auth/context";
import { listRunEvents } from "@/server/events/run-events";
import {
  createResearchRun,
  getRunSteps,
  getWorkspaceRun,
  getWorkspaceRunDetail,
  listWorkspaceRuns,
  requestRunCancellation,
  retryResearchRun,
} from "@/server/repositories/runs";

export async function listRunsForCurrentWorkspace(missionId?: string) {
  const context = await getAuthContext();
  return listWorkspaceRuns(context.workspace.id, missionId);
}

export async function getRunForCurrentWorkspace(runId: string) {
  const context = await getAuthContext();
  return getWorkspaceRunDetail(context.workspace.id, runId);
}

export async function getRunRecordForCurrentWorkspace(runId: string) {
  const context = await getAuthContext();
  return getWorkspaceRun(context.workspace.id, runId);
}

export async function getRunStepsForCurrentWorkspace(runId: string) {
  const context = await getAuthContext();
  const run = await getWorkspaceRun(context.workspace.id, runId);
  return run ? getRunSteps(runId) : null;
}

export async function getRunEventsForCurrentWorkspace(
  runId: string,
  afterSequence = 0,
) {
  const context = await getAuthContext();
  return listRunEvents(context.workspace.id, runId, afterSequence);
}

export async function startRunForCurrentWorkspace(
  missionId: string,
  idempotencyKey?: string,
) {
  const context = await getAuthContext();
  return createResearchRun({
    idempotencyKey,
    missionId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function cancelRunForCurrentWorkspace(runId: string) {
  const context = await getAuthContext();
  return requestRunCancellation({
    runId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function retryRunForCurrentWorkspace(
  runId: string,
  idempotencyKey?: string,
) {
  const context = await getAuthContext();
  return retryResearchRun({
    idempotencyKey,
    runId,
    userId: context.user.id,
    workspaceId: context.workspace.id,
  });
}

export async function getRunsWorkspaceData() {
  const context = await getAuthContext();
  return {
    context,
    runs: await listWorkspaceRuns(context.workspace.id),
  };
}
