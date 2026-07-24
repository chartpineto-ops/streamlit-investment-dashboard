import { getAuthContext } from "@/server/auth/context";
import { getDatabase } from "@/server/db/client";

export async function getOperationsDiagnostics() {
  const context = await getAuthContext();
  const database = await getDatabase();
  const [counts, audits] = await Promise.all([
    database
      .prepare(
        `SELECT
          (SELECT COUNT(*) FROM job_queue jq
            INNER JOIN research_runs rr ON rr.id = jq.run_id
            INNER JOIN missions m ON m.id = rr.mission_id
            INNER JOIN projects p ON p.id = m.project_id
            WHERE p.workspace_id = ? AND jq.status IN ('PENDING','PROCESSING')) AS active_jobs,
          (SELECT COUNT(*) FROM job_queue jq
            INNER JOIN research_runs rr ON rr.id = jq.run_id
            INNER JOIN missions m ON m.id = rr.mission_id
            INNER JOIN projects p ON p.id = m.project_id
            WHERE p.workspace_id = ? AND jq.status = 'DEAD_LETTER') AS dead_jobs,
          (SELECT COUNT(*) FROM source_connectors
            WHERE workspace_id = ? AND status = 'CONNECTED') AS connected_sources,
          (SELECT COUNT(*) FROM source_connectors
            WHERE workspace_id = ? AND status = 'ERROR') AS failed_sources,
          (SELECT COUNT(*) FROM source_documents
            WHERE workspace_id = ?) AS document_count,
          (SELECT COUNT(*) FROM run_events re
            INNER JOIN research_runs rr ON rr.id = re.research_run_id
            INNER JOIN missions m ON m.id = rr.mission_id
            INNER JOIN projects p ON p.id = m.project_id
            WHERE p.workspace_id = ?) AS event_count`,
      )
      .bind(
        context.workspace.id,
        context.workspace.id,
        context.workspace.id,
        context.workspace.id,
        context.workspace.id,
        context.workspace.id,
      )
      .first<{
        active_jobs: number;
        connected_sources: number;
        dead_jobs: number;
        document_count: number;
        event_count: number;
        failed_sources: number;
      }>(),
    database
      .prepare(
        `SELECT action, entity_type, entity_id, request_id, created_at
         FROM audit_logs
         WHERE workspace_id = ?
         ORDER BY created_at DESC
         LIMIT 20`,
      )
      .bind(context.workspace.id)
      .all<{
        action: string;
        created_at: string;
        entity_id: string;
        entity_type: string;
        request_id: string;
      }>(),
  ]);
  return {
    activeJobs: Number(counts?.active_jobs ?? 0),
    auditLogs: audits.results.map((row) => ({
      action: row.action,
      createdAt: row.created_at,
      entityId: row.entity_id,
      entityType: row.entity_type,
      requestId: row.request_id,
    })),
    connectedSources: Number(counts?.connected_sources ?? 0),
    deadJobs: Number(counts?.dead_jobs ?? 0),
    documentCount: Number(counts?.document_count ?? 0),
    environment: {
      database: "bound",
      githubToken: process.env.GITHUB_TOKEN ? "configured" : "optional",
      objectStorage: "bound",
    },
    eventCount: Number(counts?.event_count ?? 0),
    failedSources: Number(counts?.failed_sources ?? 0),
  };
}
