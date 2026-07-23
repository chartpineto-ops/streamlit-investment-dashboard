-- CreateEnum
CREATE TYPE "UserRole" AS ENUM ('OWNER', 'ADMIN', 'ANALYST', 'VIEWER');

-- CreateEnum
CREATE TYPE "ProjectStatus" AS ENUM ('ACTIVE', 'ARCHIVED');

-- CreateEnum
CREATE TYPE "MissionStatus" AS ENUM ('DRAFT', 'READY', 'ACTIVE', 'PAUSED', 'COMPLETED', 'FAILED', 'ARCHIVED');

-- CreateEnum
CREATE TYPE "ResearchDepth" AS ENUM ('RAPID', 'STANDARD', 'DEEP');

-- CreateEnum
CREATE TYPE "MonitoringMode" AS ENUM ('MANUAL', 'HOURLY', 'DAILY', 'WEEKLY');

-- CreateEnum
CREATE TYPE "ConnectorType" AS ENUM ('RSS_ATOM', 'PUBLIC_WEB', 'MANUAL_URL', 'FILE_UPLOAD', 'GITHUB_PUBLIC', 'DEMO', 'GOOGLE_DRIVE', 'GMAIL', 'SLACK', 'NOTION', 'CRM', 'DATA_WAREHOUSE', 'MARKET_DATA');

-- CreateEnum
CREATE TYPE "ConnectorStatus" AS ENUM ('AVAILABLE', 'NOT_CONNECTED', 'DEGRADED', 'ERROR', 'DISABLED');

-- CreateEnum
CREATE TYPE "RunTriggerType" AS ENUM ('MANUAL', 'SCHEDULED', 'RETRY');

-- CreateEnum
CREATE TYPE "RunStatus" AS ENUM ('QUEUED', 'RUNNING', 'PAUSED', 'CANCELLING', 'CANCELLED', 'COMPLETED', 'PARTIAL', 'FAILED');

-- CreateEnum
CREATE TYPE "RunStepStatus" AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'SKIPPED', 'FAILED');

-- CreateEnum
CREATE TYPE "EvidenceType" AS ENUM ('FACT', 'METRIC', 'EVENT', 'QUOTE', 'FORECAST', 'OPINION', 'RISK', 'OPPORTUNITY');

-- CreateEnum
CREATE TYPE "EvidenceValidationStatus" AS ENUM ('UNVALIDATED', 'SUPPORTED', 'CONTESTED', 'CONTRADICTED', 'DUPLICATE', 'SUPERSEDED', 'REJECTED');

-- CreateEnum
CREATE TYPE "ClaimType" AS ENUM ('FACT', 'TREND', 'RISK', 'OPPORTUNITY', 'FORECAST', 'OPINION');

-- CreateEnum
CREATE TYPE "ClaimStatus" AS ENUM ('NEW', 'CONFIRMED', 'STRENGTHENED', 'WEAKENED', 'CONTRADICTED', 'SUPERSEDED', 'UNCHANGED', 'REJECTED');

-- CreateEnum
CREATE TYPE "EvidenceRelationship" AS ENUM ('SUPPORTS', 'CONTRADICTS', 'CONTEXTUALIZES', 'DUPLICATES', 'SUPERSEDES');

-- CreateEnum
CREATE TYPE "InsightCategory" AS ENUM ('STRATEGIC', 'PRODUCT_GAP', 'OPPORTUNITY', 'RISK', 'CONTRADICTION', 'KNOWLEDGE_GAP');

-- CreateEnum
CREATE TYPE "Severity" AS ENUM ('INFORMATIONAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- CreateEnum
CREATE TYPE "InsightStatus" AS ENUM ('NEW', 'REVIEWED', 'ASSIGNED', 'RESOLVED', 'DISMISSED');

-- CreateEnum
CREATE TYPE "MonitorStatus" AS ENUM ('ACTIVE', 'PAUSED', 'DISABLED', 'ERROR');

-- CreateEnum
CREATE TYPE "AlertType" AS ENUM ('MATERIAL_CHANGE', 'CONTRADICTION', 'SOURCE_FAILURE', 'MONITOR_FAILURE');

-- CreateEnum
CREATE TYPE "AlertStatus" AS ENUM ('NEW', 'READ', 'ACKNOWLEDGED', 'DISMISSED');

-- CreateEnum
CREATE TYPE "ReportType" AS ENUM ('EXECUTIVE_BRIEF', 'SOURCE_APPENDIX', 'COMPETITOR_MATRIX', 'EVIDENCE_CSV', 'JSON_PACKAGE');

-- CreateEnum
CREATE TYPE "ReportStatus" AS ENUM ('QUEUED', 'GENERATING', 'COMPLETED', 'FAILED');

-- CreateTable
CREATE TABLE "Workspace" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Workspace_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "workspaceId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "role" "UserRole" NOT NULL DEFAULT 'ANALYST',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Project" (
    "id" TEXT NOT NULL,
    "workspaceId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "status" "ProjectStatus" NOT NULL DEFAULT 'ACTIVE',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Project_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Mission" (
    "id" TEXT NOT NULL,
    "projectId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "objective" TEXT NOT NULL,
    "scope" JSONB NOT NULL,
    "status" "MissionStatus" NOT NULL DEFAULT 'DRAFT',
    "researchDepth" "ResearchDepth" NOT NULL DEFAULT 'STANDARD',
    "monitoringMode" "MonitoringMode" NOT NULL DEFAULT 'MANUAL',
    "monitoringInterval" INTEGER,
    "createdById" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Mission_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SourceConnector" (
    "id" TEXT NOT NULL,
    "workspaceId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "type" "ConnectorType" NOT NULL,
    "status" "ConnectorStatus" NOT NULL DEFAULT 'NOT_CONNECTED',
    "configurationEncrypted" TEXT,
    "lastSuccessfulSyncAt" TIMESTAMP(3),
    "lastErrorAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SourceConnector_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "MissionSource" (
    "missionId" TEXT NOT NULL,
    "sourceConnectorId" TEXT NOT NULL,
    "inclusionRules" JSONB,
    "exclusionRules" JSONB,
    "priority" INTEGER NOT NULL DEFAULT 50,

    CONSTRAINT "MissionSource_pkey" PRIMARY KEY ("missionId","sourceConnectorId")
);

-- CreateTable
CREATE TABLE "ResearchRun" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "triggerType" "RunTriggerType" NOT NULL,
    "status" "RunStatus" NOT NULL DEFAULT 'QUEUED',
    "startedAt" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "progressPercent" INTEGER NOT NULL DEFAULT 0,
    "sourcesScanned" INTEGER NOT NULL DEFAULT 0,
    "documentsProcessed" INTEGER NOT NULL DEFAULT 0,
    "evidenceCreated" INTEGER NOT NULL DEFAULT 0,
    "insightsCreated" INTEGER NOT NULL DEFAULT 0,
    "confidenceScore" DOUBLE PRECISION,
    "errorSummary" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ResearchRun_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "RunStep" (
    "id" TEXT NOT NULL,
    "researchRunId" TEXT NOT NULL,
    "agentType" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "status" "RunStepStatus" NOT NULL DEFAULT 'PENDING',
    "startedAt" TIMESTAMP(3),
    "completedAt" TIMESTAMP(3),
    "inputSummary" TEXT,
    "outputSummary" TEXT,
    "toolName" TEXT,
    "tokenUsage" INTEGER,
    "errorMessage" TEXT,
    "sequence" INTEGER NOT NULL,

    CONSTRAINT "RunStep_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SourceDocument" (
    "id" TEXT NOT NULL,
    "connectorId" TEXT NOT NULL,
    "externalId" TEXT NOT NULL,
    "canonicalUrl" TEXT,
    "title" TEXT NOT NULL,
    "author" TEXT,
    "publisher" TEXT,
    "publishedAt" TIMESTAMP(3),
    "retrievedAt" TIMESTAMP(3) NOT NULL,
    "contentHash" TEXT NOT NULL,
    "rawContent" TEXT NOT NULL,
    "normalizedContent" TEXT NOT NULL,
    "metadata" JSONB NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT "SourceDocument_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Evidence" (
    "id" TEXT NOT NULL,
    "sourceDocumentId" TEXT NOT NULL,
    "researchRunId" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "evidenceType" "EvidenceType" NOT NULL,
    "excerpt" TEXT NOT NULL,
    "normalizedClaim" TEXT NOT NULL,
    "entities" TEXT[],
    "topics" TEXT[],
    "eventDate" TIMESTAMP(3),
    "extractedAt" TIMESTAMP(3) NOT NULL,
    "relevanceScore" DOUBLE PRECISION NOT NULL,
    "sourceQualityScore" DOUBLE PRECISION NOT NULL,
    "noveltyScore" DOUBLE PRECISION NOT NULL,
    "confidenceScore" DOUBLE PRECISION NOT NULL,
    "validationStatus" "EvidenceValidationStatus" NOT NULL DEFAULT 'UNVALIDATED',
    "contentHash" TEXT NOT NULL,

    CONSTRAINT "Evidence_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Claim" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "statement" TEXT NOT NULL,
    "claimType" "ClaimType" NOT NULL,
    "status" "ClaimStatus" NOT NULL DEFAULT 'NEW',
    "confidenceScore" DOUBLE PRECISION NOT NULL,
    "firstObservedAt" TIMESTAMP(3) NOT NULL,
    "lastObservedAt" TIMESTAMP(3) NOT NULL,
    "materialityScore" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "Claim_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ClaimEvidence" (
    "claimId" TEXT NOT NULL,
    "evidenceId" TEXT NOT NULL,
    "relationship" "EvidenceRelationship" NOT NULL,
    "supportStrength" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "ClaimEvidence_pkey" PRIMARY KEY ("claimId","evidenceId")
);

-- CreateTable
CREATE TABLE "Insight" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "researchRunId" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "category" "InsightCategory" NOT NULL,
    "severity" "Severity" NOT NULL,
    "confidenceScore" DOUBLE PRECISION NOT NULL,
    "materialityScore" DOUBLE PRECISION NOT NULL,
    "noveltyScore" DOUBLE PRECISION NOT NULL,
    "status" "InsightStatus" NOT NULL DEFAULT 'NEW',
    "recommendedAction" TEXT,
    "owner" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Insight_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "InsightClaim" (
    "insightId" TEXT NOT NULL,
    "claimId" TEXT NOT NULL,
    "importance" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "InsightClaim_pkey" PRIMARY KEY ("insightId","claimId")
);

-- CreateTable
CREATE TABLE "Monitor" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "status" "MonitorStatus" NOT NULL DEFAULT 'PAUSED',
    "schedule" TEXT NOT NULL,
    "materialityThreshold" DOUBLE PRECISION NOT NULL,
    "notificationPolicy" JSONB NOT NULL,
    "lastCheckedAt" TIMESTAMP(3),
    "nextCheckAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Monitor_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Alert" (
    "id" TEXT NOT NULL,
    "monitorId" TEXT NOT NULL,
    "insightId" TEXT,
    "alertType" "AlertType" NOT NULL,
    "title" TEXT NOT NULL,
    "summary" TEXT NOT NULL,
    "status" "AlertStatus" NOT NULL DEFAULT 'NEW',
    "deliveredAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Alert_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Report" (
    "id" TEXT NOT NULL,
    "missionId" TEXT NOT NULL,
    "researchRunId" TEXT,
    "type" "ReportType" NOT NULL,
    "status" "ReportStatus" NOT NULL DEFAULT 'QUEUED',
    "content" JSONB,
    "generatedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Report_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "Workspace_name_idx" ON "Workspace"("name");

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "User_workspaceId_role_idx" ON "User"("workspaceId", "role");

-- CreateIndex
CREATE INDEX "Project_workspaceId_status_idx" ON "Project"("workspaceId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "Project_workspaceId_name_key" ON "Project"("workspaceId", "name");

-- CreateIndex
CREATE INDEX "Mission_projectId_status_idx" ON "Mission"("projectId", "status");

-- CreateIndex
CREATE INDEX "Mission_createdById_idx" ON "Mission"("createdById");

-- CreateIndex
CREATE INDEX "Mission_updatedAt_idx" ON "Mission"("updatedAt");

-- CreateIndex
CREATE INDEX "SourceConnector_workspaceId_type_status_idx" ON "SourceConnector"("workspaceId", "type", "status");

-- CreateIndex
CREATE UNIQUE INDEX "SourceConnector_workspaceId_name_key" ON "SourceConnector"("workspaceId", "name");

-- CreateIndex
CREATE INDEX "MissionSource_sourceConnectorId_idx" ON "MissionSource"("sourceConnectorId");

-- CreateIndex
CREATE INDEX "ResearchRun_missionId_createdAt_idx" ON "ResearchRun"("missionId", "createdAt");

-- CreateIndex
CREATE INDEX "ResearchRun_status_createdAt_idx" ON "ResearchRun"("status", "createdAt");

-- CreateIndex
CREATE INDEX "RunStep_researchRunId_status_idx" ON "RunStep"("researchRunId", "status");

-- CreateIndex
CREATE UNIQUE INDEX "RunStep_researchRunId_sequence_key" ON "RunStep"("researchRunId", "sequence");

-- CreateIndex
CREATE INDEX "SourceDocument_canonicalUrl_idx" ON "SourceDocument"("canonicalUrl");

-- CreateIndex
CREATE INDEX "SourceDocument_retrievedAt_idx" ON "SourceDocument"("retrievedAt");

-- CreateIndex
CREATE UNIQUE INDEX "SourceDocument_connectorId_externalId_version_key" ON "SourceDocument"("connectorId", "externalId", "version");

-- CreateIndex
CREATE UNIQUE INDEX "SourceDocument_connectorId_contentHash_key" ON "SourceDocument"("connectorId", "contentHash");

-- CreateIndex
CREATE INDEX "Evidence_missionId_validationStatus_idx" ON "Evidence"("missionId", "validationStatus");

-- CreateIndex
CREATE INDEX "Evidence_sourceDocumentId_idx" ON "Evidence"("sourceDocumentId");

-- CreateIndex
CREATE UNIQUE INDEX "Evidence_researchRunId_contentHash_key" ON "Evidence"("researchRunId", "contentHash");

-- CreateIndex
CREATE INDEX "Claim_missionId_status_materialityScore_idx" ON "Claim"("missionId", "status", "materialityScore");

-- CreateIndex
CREATE UNIQUE INDEX "Claim_missionId_statement_key" ON "Claim"("missionId", "statement");

-- CreateIndex
CREATE INDEX "ClaimEvidence_evidenceId_relationship_idx" ON "ClaimEvidence"("evidenceId", "relationship");

-- CreateIndex
CREATE INDEX "Insight_missionId_status_materialityScore_idx" ON "Insight"("missionId", "status", "materialityScore");

-- CreateIndex
CREATE INDEX "Insight_researchRunId_idx" ON "Insight"("researchRunId");

-- CreateIndex
CREATE INDEX "InsightClaim_claimId_idx" ON "InsightClaim"("claimId");

-- CreateIndex
CREATE INDEX "Monitor_missionId_status_idx" ON "Monitor"("missionId", "status");

-- CreateIndex
CREATE INDEX "Monitor_status_nextCheckAt_idx" ON "Monitor"("status", "nextCheckAt");

-- CreateIndex
CREATE INDEX "Alert_monitorId_status_createdAt_idx" ON "Alert"("monitorId", "status", "createdAt");

-- CreateIndex
CREATE INDEX "Alert_insightId_idx" ON "Alert"("insightId");

-- CreateIndex
CREATE INDEX "Report_missionId_createdAt_idx" ON "Report"("missionId", "createdAt");

-- CreateIndex
CREATE INDEX "Report_researchRunId_idx" ON "Report"("researchRunId");

-- AddForeignKey
ALTER TABLE "User" ADD CONSTRAINT "User_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "Workspace"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Project" ADD CONSTRAINT "Project_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "Workspace"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mission" ADD CONSTRAINT "Mission_projectId_fkey" FOREIGN KEY ("projectId") REFERENCES "Project"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Mission" ADD CONSTRAINT "Mission_createdById_fkey" FOREIGN KEY ("createdById") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SourceConnector" ADD CONSTRAINT "SourceConnector_workspaceId_fkey" FOREIGN KEY ("workspaceId") REFERENCES "Workspace"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "MissionSource" ADD CONSTRAINT "MissionSource_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "MissionSource" ADD CONSTRAINT "MissionSource_sourceConnectorId_fkey" FOREIGN KEY ("sourceConnectorId") REFERENCES "SourceConnector"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ResearchRun" ADD CONSTRAINT "ResearchRun_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "RunStep" ADD CONSTRAINT "RunStep_researchRunId_fkey" FOREIGN KEY ("researchRunId") REFERENCES "ResearchRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SourceDocument" ADD CONSTRAINT "SourceDocument_connectorId_fkey" FOREIGN KEY ("connectorId") REFERENCES "SourceConnector"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_sourceDocumentId_fkey" FOREIGN KEY ("sourceDocumentId") REFERENCES "SourceDocument"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_researchRunId_fkey" FOREIGN KEY ("researchRunId") REFERENCES "ResearchRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Evidence" ADD CONSTRAINT "Evidence_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Claim" ADD CONSTRAINT "Claim_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClaimEvidence" ADD CONSTRAINT "ClaimEvidence_claimId_fkey" FOREIGN KEY ("claimId") REFERENCES "Claim"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ClaimEvidence" ADD CONSTRAINT "ClaimEvidence_evidenceId_fkey" FOREIGN KEY ("evidenceId") REFERENCES "Evidence"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Insight" ADD CONSTRAINT "Insight_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Insight" ADD CONSTRAINT "Insight_researchRunId_fkey" FOREIGN KEY ("researchRunId") REFERENCES "ResearchRun"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "InsightClaim" ADD CONSTRAINT "InsightClaim_insightId_fkey" FOREIGN KEY ("insightId") REFERENCES "Insight"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "InsightClaim" ADD CONSTRAINT "InsightClaim_claimId_fkey" FOREIGN KEY ("claimId") REFERENCES "Claim"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Monitor" ADD CONSTRAINT "Monitor_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_monitorId_fkey" FOREIGN KEY ("monitorId") REFERENCES "Monitor"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Alert" ADD CONSTRAINT "Alert_insightId_fkey" FOREIGN KEY ("insightId") REFERENCES "Insight"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Report" ADD CONSTRAINT "Report_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Report" ADD CONSTRAINT "Report_researchRunId_fkey" FOREIGN KEY ("researchRunId") REFERENCES "ResearchRun"("id") ON DELETE SET NULL ON UPDATE CASCADE;
