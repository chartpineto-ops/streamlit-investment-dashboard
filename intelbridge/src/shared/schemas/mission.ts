import { z } from "zod";

import { MonitoringMode, ResearchDepth } from "@/shared/domain";

export const missionScopeSchema = z.object({
  focusAreas: z.array(z.string().min(1)).min(1),
  regions: z.array(z.string().min(1)).min(1),
  timeHorizonMonths: z.number().int().min(1).max(60),
});

export type MissionScope = z.infer<typeof missionScopeSchema>;

export const createMissionSchema = z.object({
  connectorIds: z.array(z.string().min(1)).min(1),
  focusAreas: z.array(z.string().min(1)).min(1),
  monitoringMode: z.enum(MonitoringMode),
  objective: z.string().trim().min(30).max(2_000),
  projectId: z.string().min(1),
  regions: z.array(z.string().min(1)).min(1),
  researchDepth: z.enum(ResearchDepth),
  timeHorizonMonths: z.number().int().min(1).max(60),
  title: z.string().trim().min(5).max(140),
});

export type CreateMissionInput = z.infer<typeof createMissionSchema>;
