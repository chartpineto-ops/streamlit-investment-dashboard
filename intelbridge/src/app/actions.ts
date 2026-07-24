"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";

import {
  registerPublicUrlForCurrentWorkspace,
  registerUploadedFileForCurrentWorkspace,
} from "@/server/services/ingestion";
import {
  cancelRunForCurrentWorkspace,
  retryRunForCurrentWorkspace,
  startRunForCurrentWorkspace,
} from "@/server/services/runs";
import {
  assignMissionSourceForCurrentWorkspace,
  createConnectorForCurrentWorkspace,
  createProjectForCurrentWorkspace,
  testConnectorForCurrentWorkspace,
  updateMissionForCurrentWorkspace,
  updateProjectForCurrentWorkspace,
} from "@/server/services/foundation";
import { ConnectorStatus, ConnectorType, MissionStatus } from "@/shared/domain";

const idSchema = z.string().min(3).max(180);

function commaList(value: FormDataEntryValue | null) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function createProjectAction(formData: FormData) {
  await createProjectForCurrentWorkspace({
    description: formData.get("description"),
    name: formData.get("name"),
  });
  revalidatePath("/projects");
  redirect("/projects?notice=created");
}

export async function archiveProjectAction(formData: FormData) {
  const projectId = idSchema.parse(formData.get("projectId"));
  await updateProjectForCurrentWorkspace(projectId, { status: "ARCHIVED" });
  revalidatePath("/projects");
  redirect("/projects?notice=archived");
}

export async function createConnectorAction(formData: FormData) {
  const type = z.enum(ConnectorType).parse(formData.get("type"));
  const endpoint = z
    .string()
    .trim()
    .max(2_000)
    .optional()
    .parse(formData.get("endpoint") || undefined);
  let configuration: Record<string, unknown>;

  if (type === ConnectorType.RSS) {
    configuration = {
      feedUrl: z.url().parse(endpoint),
      maximumItemsPerRun: 25,
      type,
    };
  } else if (type === ConnectorType.WEBPAGE) {
    const startUrl = z.url().parse(endpoint);
    configuration = {
      allowedDomains: [new URL(startUrl).hostname],
      maximumPagesPerRun: 10,
      startUrls: [startUrl],
      type,
    };
  } else if (type === ConnectorType.GITHUB) {
    const [owner, repository] = String(endpoint ?? "").split("/");
    configuration = {
      includeIssues: true,
      includeReleases: true,
      maximumItemsPerRun: 25,
      owner,
      repository,
      type,
    };
  } else if (type === ConnectorType.MANUAL_URL) {
    configuration = {
      type,
      urls: endpoint ? [z.url().parse(endpoint)] : [],
    };
  } else {
    configuration = { type };
  }

  await createConnectorForCurrentWorkspace({
    configuration,
    name: formData.get("name"),
    status:
      type === ConnectorType.DEMO ||
      type === ConnectorType.FILE_UPLOAD ||
      type === ConnectorType.MANUAL_URL
        ? ConnectorStatus.CONNECTED
        : ConnectorStatus.DISCONNECTED,
  });
  revalidatePath("/sources");
  redirect("/sources?notice=created");
}

export async function testConnectorAction(formData: FormData) {
  const connectorId = idSchema.parse(formData.get("connectorId"));
  const result = await testConnectorForCurrentWorkspace(connectorId);
  revalidatePath("/sources");
  redirect(`/sources?notice=${result?.ok ? "test-passed" : "test-failed"}`);
}

export async function updateMissionAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  await updateMissionForCurrentWorkspace(missionId, {
    objective: formData.get("objective"),
    researchDepth: formData.get("researchDepth"),
    scope: {
      focusAreas: commaList(formData.get("focusAreas")),
      regions: commaList(formData.get("regions")),
      timeHorizonMonths: Number(formData.get("timeHorizonMonths")),
    },
    status: z.enum(MissionStatus).parse(formData.get("status")),
    title: formData.get("title"),
  });
  revalidatePath(`/missions/${missionId}`);
  redirect(`/missions/${missionId}?notice=updated`);
}

export async function assignMissionSourceAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  await assignMissionSourceForCurrentWorkspace(missionId, {
    connectorId: idSchema.parse(formData.get("connectorId")),
    exclusionRules: commaList(formData.get("exclusionRules")),
    inclusionRules: commaList(formData.get("inclusionRules")),
    priority: Number(formData.get("priority") ?? 50),
  });
  revalidatePath(`/missions/${missionId}`);
  redirect(`/missions/${missionId}?notice=source-assigned`);
}

export async function startResearchAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  const idempotencyKey = z
    .string()
    .min(8)
    .max(220)
    .optional()
    .parse(formData.get("idempotencyKey") || undefined);
  const result = await startRunForCurrentWorkspace(missionId, idempotencyKey);
  revalidatePath(`/missions/${missionId}`);
  redirect(`/runs/${result.run.id}`);
}

export async function cancelResearchAction(formData: FormData) {
  const runId = idSchema.parse(formData.get("runId"));
  await cancelRunForCurrentWorkspace(runId);
  revalidatePath(`/runs/${runId}`);
  redirect(`/runs/${runId}?notice=cancelled`);
}

export async function retryResearchAction(formData: FormData) {
  const runId = idSchema.parse(formData.get("runId"));
  const result = await retryRunForCurrentWorkspace(
    runId,
    `retry:${runId}:${crypto.randomUUID()}`,
  );
  revalidatePath("/runs");
  redirect(`/runs/${result.run.id}`);
}

export async function ingestSourceAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  const mode = z.enum(["url", "file"]).parse(formData.get("mode"));

  try {
    if (mode === "url") {
      await registerPublicUrlForCurrentWorkspace(
        missionId,
        z.url().parse(formData.get("url")),
      );
    } else {
      await registerUploadedFileForCurrentWorkspace(
        missionId,
        z.instanceof(File).parse(formData.get("file")),
      );
    }
  } catch (error) {
    const code =
      error instanceof Error ? error.message : "SOURCE_INGEST_FAILED";
    redirect(`/sources?error=${encodeURIComponent(code)}`);
  }
  revalidatePath("/sources");
  redirect("/sources?notice=queued");
}
