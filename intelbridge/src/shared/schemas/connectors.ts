import { z } from "zod";

const optionalUrlSchema = z.string().url().optional();

export const discoveredItemSchema = z.object({
  externalId: z.string().min(1).max(500),
  metadata: z.record(z.string(), z.unknown()).default({}),
  publishedAt: z.string().datetime({ offset: true }).optional(),
  title: z.string().max(500).optional(),
  url: optionalUrlSchema,
});

export const discoveryResultSchema = z.object({
  items: z.array(discoveredItemSchema),
  nextCheckpoint: z.record(z.string(), z.unknown()).optional(),
});

export const retrievedDocumentSchema = z.object({
  author: z.string().max(300).optional(),
  canonicalUrl: optionalUrlSchema,
  externalId: z.string().min(1).max(500),
  metadata: z.record(z.string(), z.unknown()).default({}),
  mimeType: z.string().min(1).max(200),
  publishedAt: z.string().datetime({ offset: true }).optional(),
  publisher: z.string().max(300).optional(),
  rawContent: z.string(),
  title: z.string().max(500).optional(),
});

export const normalizedDocumentSchema = retrievedDocumentSchema.extend({
  language: z.string().max(40).optional(),
  normalizedContent: z.string(),
  title: z.string().min(1).max(500),
});

export type DiscoveredItem = z.infer<typeof discoveredItemSchema>;
export type DiscoveryResult = z.infer<typeof discoveryResultSchema>;
export type NormalizedDocument = z.infer<typeof normalizedDocumentSchema>;
export type RetrievedDocument = z.infer<typeof retrievedDocumentSchema>;
