"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { z } from "zod";

import {
  askForCurrentUser,
  cancelResearchForCurrentUser,
  createReportForCurrentUser,
  ingestFileForCurrentUser,
  ingestUrlForCurrentUser,
  setMonitorStatusForCurrentUser,
  startResearchForCurrentUser,
} from "@/server/services/intelligence";

const idSchema = z.string().min(3).max(180);

export async function startResearchAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  const idempotencyKey = z
    .string()
    .min(8)
    .max(220)
    .optional()
    .parse(formData.get("idempotencyKey") || undefined);
  const run = await startResearchForCurrentUser(missionId, idempotencyKey);
  revalidatePath(`/missions/${missionId}`);
  redirect(`/runs/${run.id}`);
}

export async function cancelResearchAction(formData: FormData) {
  const runId = idSchema.parse(formData.get("runId"));
  await cancelResearchForCurrentUser(runId);
  revalidatePath(`/runs/${runId}`);
  redirect(`/runs/${runId}?notice=cancelled`);
}

export async function setMonitorStatusAction(formData: FormData) {
  const monitorId = idSchema.parse(formData.get("monitorId"));
  const status = z.enum(["ACTIVE", "PAUSED"]).parse(formData.get("status"));
  await setMonitorStatusForCurrentUser(monitorId, status);
  revalidatePath("/monitoring");
  redirect(`/monitoring?notice=${status.toLowerCase()}`);
}

export async function createReportAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  const type = z
    .enum([
      "EXECUTIVE_BRIEF",
      "SOURCE_APPENDIX",
      "COMPETITOR_MATRIX",
      "EVIDENCE_CSV",
      "JSON_PACKAGE",
    ])
    .parse(formData.get("type"));
  const report = await createReportForCurrentUser(missionId, type);
  revalidatePath("/reports");
  redirect(`/reports?notice=generated&report=${report.id}`);
}

export async function ingestSourceAction(formData: FormData) {
  const missionId = idSchema.parse(formData.get("missionId"));
  const mode = z.enum(["url", "file"]).parse(formData.get("mode"));

  try {
    const result =
      mode === "url"
        ? await ingestUrlForCurrentUser(
            missionId,
            z.url().parse(formData.get("url")),
          )
        : await ingestFileForCurrentUser(
            missionId,
            z.instanceof(File).parse(formData.get("file")),
          );
    revalidatePath("/sources");
    redirect(
      `/sources?notice=${result.changeState.toLowerCase()}&document=${result.id}`,
    );
  } catch (error) {
    const code =
      error instanceof Error ? error.message : "SOURCE_INGEST_FAILED";
    redirect(`/sources?error=${encodeURIComponent(code)}`);
  }
}

export type AskState = {
  answer: string;
  citations: {
    evidenceId: string;
    label: number;
    publisher: string;
  }[];
  confidence: number;
  limitations: string;
  status: "idle" | "answered" | "error";
};

export async function askIntelBridgeAction(
  _previousState: AskState,
  formData: FormData,
): Promise<AskState> {
  try {
    const missionId = idSchema.parse(formData.get("missionId"));
    const question = z
      .string()
      .trim()
      .min(5, "Enter a specific evidence question.")
      .max(500)
      .parse(formData.get("question"));
    const result = await askForCurrentUser(missionId, question);

    return {
      answer: result.answer,
      citations: result.citations,
      confidence: result.confidence,
      limitations: result.limitations,
      status: "answered",
    };
  } catch (error) {
    return {
      answer:
        error instanceof Error
          ? error.message
          : "The grounded answer could not be generated.",
      citations: [],
      confidence: 0,
      limitations: "No answer was persisted.",
      status: "error",
    };
  }
}
