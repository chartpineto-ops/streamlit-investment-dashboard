import { getAuthContext } from "@/server/auth/context";
import { getDatabase } from "@/server/db/client";

export async function searchCurrentWorkspace(query: string) {
  const context = await getAuthContext();
  const normalized = query.trim();
  if (!normalized) return { context, results: [] };
  const database = await getDatabase();
  const like = `%${normalized}%`;
  const result = await database
    .prepare(
      `SELECT * FROM (
        SELECT m.id, 'MISSION' AS result_type, m.title,
               m.objective AS excerpt, '/missions/' || m.id AS href,
               m.updated_at AS sort_at
        FROM missions m
        INNER JOIN projects p ON p.id = m.project_id
        WHERE p.workspace_id = ? AND (m.title LIKE ? OR m.objective LIKE ?)
        UNION ALL
        SELECT p.id, 'PROJECT', p.name, p.description,
               '/projects', p.updated_at
        FROM projects p
        WHERE p.workspace_id = ? AND (p.name LIKE ? OR p.description LIKE ?)
        UNION ALL
        SELECT sc.id, 'SOURCE', sc.name, sc.type || ' · ' || sc.status,
               '/sources', sc.updated_at
        FROM source_connectors sc
        WHERE sc.workspace_id = ? AND sc.name LIKE ?
        UNION ALL
        SELECT rr.id, 'RUN', m.title, rr.status || ' · ' || rr.trigger_type,
               '/runs/' || rr.id, rr.updated_at
        FROM research_runs rr
        INNER JOIN missions m ON m.id = rr.mission_id
        INNER JOIN projects p ON p.id = m.project_id
        WHERE p.workspace_id = ? AND (rr.id LIKE ? OR m.title LIKE ?)
        UNION ALL
        SELECT sd.id, 'DOCUMENT', sd.title, sd.normalized_content,
               '/documents/' || sd.id, sd.last_retrieved_at
        FROM source_documents sd
        WHERE sd.workspace_id = ?
          AND (sd.title LIKE ? OR sd.normalized_content LIKE ?)
      )
      ORDER BY sort_at DESC
      LIMIT 50`,
    )
    .bind(
      context.workspace.id,
      like,
      like,
      context.workspace.id,
      like,
      like,
      context.workspace.id,
      like,
      context.workspace.id,
      like,
      like,
      context.workspace.id,
      like,
      like,
    )
    .all<{
      excerpt: string;
      href: string;
      id: string;
      result_type: string;
      title: string;
    }>();
  return {
    context,
    results: result.results.map((row) => ({
      excerpt: row.excerpt.slice(0, 320),
      href: row.href,
      id: row.id,
      resultType: row.result_type,
      title: row.title,
    })),
  };
}
