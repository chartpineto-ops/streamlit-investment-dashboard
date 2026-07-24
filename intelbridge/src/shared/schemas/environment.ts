import { z } from "zod";

export const serverEnvironmentSchema = z.object({
  AI_PROVIDER: z.enum(["mock", "openai"]).default("mock"),
  INTELBRIDGE_DEMO_USER_EMAIL: z
    .email()
    .default("alex.parker@intelbridge.demo"),
  NODE_ENV: z
    .enum(["development", "test", "production"])
    .default("development"),
  OPENAI_API_KEY: z.string().min(20).optional(),
  OPENAI_MODEL: z.string().min(3).default("gpt-5.6-sol"),
  OPENAI_TIMEOUT_MS: z.coerce
    .number()
    .int()
    .min(1_000)
    .max(60_000)
    .default(20_000),
});

export type ServerEnvironment = z.infer<typeof serverEnvironmentSchema>;

let cachedEnvironment: ServerEnvironment | undefined;

export function parseServerEnvironment(
  values: Record<string, string | undefined>,
): ServerEnvironment {
  return serverEnvironmentSchema.parse(values);
}

export function getServerEnvironment(): ServerEnvironment {
  if (!cachedEnvironment) {
    cachedEnvironment = parseServerEnvironment(process.env);
  }

  return cachedEnvironment;
}
