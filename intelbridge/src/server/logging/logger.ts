type LogContext = {
  connectorId?: string;
  documentId?: string;
  durationMs?: number;
  errorCode?: string;
  jobId?: string;
  missionId?: string;
  projectId?: string;
  requestId?: string;
  runId?: string;
  status?: string;
  stepId?: string;
  userId?: string;
  workspaceId?: string;
};

const prohibitedKeys = new Set([
  "authorization",
  "configurationEncrypted",
  "encryptionKey",
  "rawContent",
  "sessionToken",
]);

function sanitize(context: LogContext) {
  return Object.fromEntries(
    Object.entries(context).filter(
      ([key, value]) => value !== undefined && !prohibitedKeys.has(key),
    ),
  );
}

export function logInfo(event: string, context: LogContext = {}) {
  console.info(
    JSON.stringify({
      ...sanitize(context),
      event,
      level: "info",
      timestamp: new Date().toISOString(),
    }),
  );
}

export function logError(event: string, context: LogContext = {}) {
  console.error(
    JSON.stringify({
      ...sanitize(context),
      event,
      level: "error",
      timestamp: new Date().toISOString(),
    }),
  );
}
