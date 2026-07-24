import { z } from "zod";

import { RunStatus, RunStepType, RunTriggerType } from "@/shared/domain";

const timestampSchema = z.string().datetime({ offset: true });
const runIdentitySchema = z.object({
  runId: z.string().min(3),
  timestamp: timestampSchema,
});

export const researchRunEventPayloadSchema = z.discriminatedUnion("type", [
  runIdentitySchema.extend({
    type: z.literal("run.queued"),
    triggerType: z.enum(RunTriggerType),
  }),
  runIdentitySchema.extend({ type: z.literal("run.started") }),
  z.object({
    message: z.string(),
    stepId: z.string(),
    stepType: z.enum(RunStepType),
    timestamp: timestampSchema,
    type: z.literal("step.started"),
  }),
  z.object({
    message: z.string(),
    progress: z.number().int().min(0).max(100),
    stepId: z.string(),
    timestamp: timestampSchema,
    type: z.literal("step.progress"),
  }),
  z.object({
    connectorId: z.string(),
    publishedAt: timestampSchema.optional(),
    timestamp: timestampSchema,
    title: z.string(),
    type: z.literal("source.discovered"),
    url: z.string().url().optional(),
  }),
  z.object({
    documentId: z.string().optional(),
    result: z.enum(["created", "updated", "unchanged", "failed"]),
    timestamp: timestampSchema,
    title: z.string(),
    type: z.literal("document.processed"),
  }),
  z.object({
    metrics: z.object({
      documentsCreated: z.number().int().nonnegative(),
      documentsDiscovered: z.number().int().nonnegative(),
      documentsProcessed: z.number().int().nonnegative(),
      documentsUnchanged: z.number().int().nonnegative(),
      documentsUpdated: z.number().int().nonnegative(),
      progressPercent: z.number().int().min(0).max(100),
      sourcesScanned: z.number().int().nonnegative(),
    }),
    timestamp: timestampSchema,
    type: z.literal("run.metrics"),
  }),
  z.object({
    stepId: z.string(),
    timestamp: timestampSchema,
    type: z.literal("step.completed"),
  }),
  runIdentitySchema.extend({
    status: z.enum([RunStatus.COMPLETED, RunStatus.PARTIALLY_COMPLETED]),
    type: z.literal("run.completed"),
  }),
  runIdentitySchema.extend({ type: z.literal("run.cancelled") }),
  runIdentitySchema.extend({
    errorCode: z.string(),
    message: z.string(),
    type: z.literal("run.failed"),
  }),
]);

export const durableRunEventSchema = z.object({
  createdAt: timestampSchema,
  payload: researchRunEventPayloadSchema,
  sequenceNumber: z.number().int().positive(),
  type: z.string(),
});

export type DurableRunEvent = z.infer<typeof durableRunEventSchema>;
export type ResearchRunEventPayload = z.infer<
  typeof researchRunEventPayloadSchema
>;
