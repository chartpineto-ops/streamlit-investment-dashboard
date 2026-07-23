"use server";

import { redirect } from "next/navigation";
import { ZodError } from "zod";

import { createMissionForCurrentUser } from "@/server/services/missions";

export type CreateMissionState = {
  message: string | null;
};

function splitList(value: FormDataEntryValue | null) {
  if (typeof value !== "string") {
    return [];
  }

  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export async function createMissionAction(
  _state: CreateMissionState,
  formData: FormData,
): Promise<CreateMissionState> {
  let missionId: string;

  try {
    const mission = await createMissionForCurrentUser({
      connectorIds: formData
        .getAll("connectorIds")
        .filter((value): value is string => {
          return typeof value === "string";
        }),
      focusAreas: splitList(formData.get("focusAreas")),
      monitoringMode: formData.get("monitoringMode"),
      objective: formData.get("objective"),
      projectId: formData.get("projectId"),
      regions: splitList(formData.get("regions")),
      researchDepth: formData.get("researchDepth"),
      timeHorizonMonths: Number(formData.get("timeHorizonMonths")),
      title: formData.get("title"),
    });
    missionId = mission.id;
  } catch (error) {
    if (error instanceof ZodError) {
      return {
        message:
          error.issues[0]?.message ??
          "Review the mission fields and try again.",
      };
    }

    if (error instanceof Error && error.message === "PROJECT_NOT_FOUND") {
      return {
        message: "The selected project is not available in this workspace.",
      };
    }

    if (error instanceof Error && error.message === "CONNECTOR_NOT_FOUND") {
      return {
        message:
          "One or more selected connectors are not available in this workspace.",
      };
    }

    throw error;
  }

  redirect(`/missions/${missionId}`);
}
