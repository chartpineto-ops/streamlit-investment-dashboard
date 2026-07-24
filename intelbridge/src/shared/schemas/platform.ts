import { z } from "zod";

import {
  ConnectorStatus,
  ConnectorType,
  MissionStatus,
  ProjectStatus,
  ResearchDepth,
} from "@/shared/domain";

export const entityIdSchema = z
  .string()
  .trim()
  .min(3)
  .max(180)
  .regex(/^[a-zA-Z0-9:_-]+$/);

export const paginationQuerySchema = z.object({
  cursor: z.string().trim().max(180).optional(),
  limit: z.coerce.number().int().min(1).max(100).default(50),
  query: z.string().trim().max(200).optional(),
});

export const projectCreateSchema = z.object({
  description: z.string().trim().min(10).max(1_000),
  name: z.string().trim().min(3).max(100),
});

export const projectUpdateSchema = projectCreateSchema
  .partial()
  .extend({ status: z.enum(ProjectStatus).optional() })
  .refine((value) => Object.keys(value).length > 0, {
    message: "At least one project field is required.",
  });

export const missionScopeInputSchema = z.object({
  focusAreas: z.array(z.string().trim().min(1).max(80)).min(1).max(12),
  regions: z.array(z.string().trim().min(1).max(80)).min(1).max(12),
  timeHorizonMonths: z.number().int().min(1).max(60),
});

export const missionCreateApiSchema = z.object({
  connectorIds: z.array(entityIdSchema).min(1).max(20),
  objective: z.string().trim().min(30).max(2_000),
  projectId: entityIdSchema,
  researchDepth: z.enum(ResearchDepth),
  scope: missionScopeInputSchema,
  status: z
    .enum([MissionStatus.DRAFT, MissionStatus.READY])
    .default(MissionStatus.READY),
  title: z.string().trim().min(5).max(140),
});

export const missionUpdateSchema = z
  .object({
    objective: z.string().trim().min(30).max(2_000).optional(),
    projectId: entityIdSchema.optional(),
    researchDepth: z.enum(ResearchDepth).optional(),
    scope: missionScopeInputSchema.optional(),
    status: z.enum(MissionStatus).optional(),
    title: z.string().trim().min(5).max(140).optional(),
  })
  .refine((value) => Object.keys(value).length > 0, {
    message: "At least one mission field is required.",
  });

const publicUrlSchema = z
  .string()
  .trim()
  .url()
  .max(2_000)
  .refine((value) => ["http:", "https:"].includes(new URL(value).protocol), {
    message: "Only HTTP and HTTPS URLs are supported.",
  });

export const connectorConfigurationSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal(ConnectorType.DEMO) }),
  z.object({ type: z.literal(ConnectorType.FILE_UPLOAD) }),
  z.object({
    maximumItemsPerRun: z.number().int().min(1).max(100).default(25),
    type: z.literal(ConnectorType.RSS),
    feedUrl: publicUrlSchema,
  }),
  z.object({
    allowedDomains: z.array(z.string().trim().min(1).max(253)).min(1).max(25),
    maximumPagesPerRun: z.number().int().min(1).max(50).default(10),
    startUrls: z.array(publicUrlSchema).min(1).max(25),
    type: z.literal(ConnectorType.WEBPAGE),
  }),
  z.object({
    urls: z.array(publicUrlSchema).max(100).default([]),
    type: z.literal(ConnectorType.MANUAL_URL),
  }),
  z.object({
    includeIssues: z.boolean().default(true),
    includeReleases: z.boolean().default(true),
    maximumItemsPerRun: z.number().int().min(1).max(100).default(25),
    owner: z.string().trim().min(1).max(100),
    repository: z.string().trim().min(1).max(100),
    type: z.literal(ConnectorType.GITHUB),
  }),
]);

export const connectorCreateSchema = z.object({
  configuration: connectorConfigurationSchema,
  name: z.string().trim().min(3).max(120),
  status: z.enum(ConnectorStatus).default(ConnectorStatus.CONNECTED),
});

export const connectorUpdateSchema = z
  .object({
    configuration: connectorConfigurationSchema.optional(),
    name: z.string().trim().min(3).max(120).optional(),
    status: z.enum(ConnectorStatus).optional(),
  })
  .refine((value) => Object.keys(value).length > 0, {
    message: "At least one connector field is required.",
  });

export const missionSourceAssignmentSchema = z.object({
  connectorId: entityIdSchema,
  exclusionRules: z
    .array(z.string().trim().min(1).max(200))
    .max(30)
    .default([]),
  inclusionRules: z
    .array(z.string().trim().min(1).max(200))
    .max(30)
    .default([]),
  priority: z.number().int().min(1).max(100).default(50),
});

export const documentListQuerySchema = paginationQuerySchema.extend({
  change: z.enum(["CREATED", "UPDATED", "UNCHANGED"]).optional(),
  connectorId: entityIdSchema.optional(),
  missionId: entityIdSchema.optional(),
  retrievedAfter: z.string().datetime({ offset: true }).optional(),
});

export type ConnectorConfiguration = z.infer<
  typeof connectorConfigurationSchema
>;
export type CreateConnectorInput = z.infer<typeof connectorCreateSchema>;
export type CreateProjectInput = z.infer<typeof projectCreateSchema>;
export type CreateMissionApiInput = z.infer<typeof missionCreateApiSchema>;
export type UpdateConnectorInput = z.infer<typeof connectorUpdateSchema>;
export type UpdateMissionInput = z.infer<typeof missionUpdateSchema>;
export type UpdateProjectInput = z.infer<typeof projectUpdateSchema>;
