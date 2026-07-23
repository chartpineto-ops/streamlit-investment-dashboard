export const UserRole = {
  ADMIN: "ADMIN",
  ANALYST: "ANALYST",
  OWNER: "OWNER",
  VIEWER: "VIEWER",
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const MissionStatus = {
  ACTIVE: "ACTIVE",
  ARCHIVED: "ARCHIVED",
  COMPLETED: "COMPLETED",
  DRAFT: "DRAFT",
  FAILED: "FAILED",
  PAUSED: "PAUSED",
  READY: "READY",
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
  AVAILABLE: "AVAILABLE",
  DEGRADED: "DEGRADED",
  DISABLED: "DISABLED",
  ERROR: "ERROR",
  NOT_CONNECTED: "NOT_CONNECTED",
} as const;
export type ConnectorStatus =
  (typeof ConnectorStatus)[keyof typeof ConnectorStatus];

export const ConnectorType = {
  DEMO: "DEMO",
  FILE_UPLOAD: "FILE_UPLOAD",
  GITHUB_PUBLIC: "GITHUB_PUBLIC",
  MANUAL_URL: "MANUAL_URL",
  PUBLIC_WEB: "PUBLIC_WEB",
  RSS_ATOM: "RSS_ATOM",
} as const;
export type ConnectorType = (typeof ConnectorType)[keyof typeof ConnectorType];
