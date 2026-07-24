export const UserRole = {
  ADMIN: "ADMIN",
  EDITOR: "EDITOR",
  VIEWER: "VIEWER",
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const MissionStatus = {
  ARCHIVED: "ARCHIVED",
  COMPLETED: "COMPLETED",
  DRAFT: "DRAFT",
  FAILED: "FAILED",
  READY: "READY",
  RUNNING: "RUNNING",
} as const;
export type MissionStatus = (typeof MissionStatus)[keyof typeof MissionStatus];

export const ResearchDepth = {
  DEEP: "DEEP",
  RAPID: "RAPID",
  STANDARD: "STANDARD",
} as const;
export type ResearchDepth = (typeof ResearchDepth)[keyof typeof ResearchDepth];

export const MonitoringMode = {
  DAILY: "DAILY",
  HOURLY: "HOURLY",
  MANUAL: "MANUAL",
  WEEKLY: "WEEKLY",
} as const;
export type MonitoringMode =
  (typeof MonitoringMode)[keyof typeof MonitoringMode];

export const ConnectorStatus = {
  CONNECTED: "CONNECTED",
  DISABLED: "DISABLED",
  DISCONNECTED: "DISCONNECTED",
  ERROR: "ERROR",
} as const;
export type ConnectorStatus =
  (typeof ConnectorStatus)[keyof typeof ConnectorStatus];

export const ConnectorType = {
  DEMO: "DEMO",
  FILE_UPLOAD: "FILE_UPLOAD",
  GITHUB: "GITHUB",
  MANUAL_URL: "MANUAL_URL",
  RSS: "RSS",
  WEBPAGE: "WEBPAGE",
} as const;
export type ConnectorType = (typeof ConnectorType)[keyof typeof ConnectorType];

export const ProjectStatus = {
  ACTIVE: "ACTIVE",
  ARCHIVED: "ARCHIVED",
} as const;
export type ProjectStatus = (typeof ProjectStatus)[keyof typeof ProjectStatus];

export const RunStatus = {
  CANCEL_REQUESTED: "CANCEL_REQUESTED",
  CANCELLED: "CANCELLED",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  PARTIALLY_COMPLETED: "PARTIALLY_COMPLETED",
  QUEUED: "QUEUED",
  RUNNING: "RUNNING",
} as const;
export type RunStatus = (typeof RunStatus)[keyof typeof RunStatus];

export const RunTriggerType = {
  MANUAL: "MANUAL",
  RETRY: "RETRY",
  SCHEDULED: "SCHEDULED",
} as const;
export type RunTriggerType =
  (typeof RunTriggerType)[keyof typeof RunTriggerType];

export const RunStepType = {
  DEDUPLICATE: "DEDUPLICATE",
  DISCOVER: "DISCOVER",
  FINALIZE: "FINALIZE",
  NORMALIZE: "NORMALIZE",
  PERSIST: "PERSIST",
  PLAN: "PLAN",
  RETRIEVE: "RETRIEVE",
} as const;
export type RunStepType = (typeof RunStepType)[keyof typeof RunStepType];

export const RunStepStatus = {
  CANCELLED: "CANCELLED",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  PENDING: "PENDING",
  RUNNING: "RUNNING",
  SKIPPED: "SKIPPED",
} as const;
export type RunStepStatus = (typeof RunStepStatus)[keyof typeof RunStepStatus];
