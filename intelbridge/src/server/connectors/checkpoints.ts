import { getDatabase } from "@/server/db/client";
import type { ConnectorCheckpointValue } from "@/server/connectors/types";

export async function getConnectorCheckpoint(connectorId: string, key: string) {
  const database = await getDatabase();
  const checkpoint = await database
    .prepare(
      `SELECT checkpoint_value
       FROM connector_checkpoints
       WHERE connector_id = ? AND checkpoint_key = ?
       LIMIT 1`,
    )
    .bind(connectorId, key)
    .first<{ checkpoint_value: string }>();

  return checkpoint
    ? (JSON.parse(checkpoint.checkpoint_value) as ConnectorCheckpointValue)
    : null;
}

export async function saveConnectorCheckpoint(
  connectorId: string,
  key: string,
  value: ConnectorCheckpointValue,
) {
  const database = await getDatabase();
  const now = new Date().toISOString();
  await database.batch([
    database
      .prepare(
        `INSERT INTO connector_checkpoints
        (id, connector_id, checkpoint_key, checkpoint_value, updated_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(connector_id, checkpoint_key) DO UPDATE SET
         checkpoint_value = excluded.checkpoint_value,
         updated_at = excluded.updated_at`,
      )
      .bind(
        `checkpoint-${crypto.randomUUID()}`,
        connectorId,
        key,
        JSON.stringify(value),
        now,
      ),
    database
      .prepare(
        `UPDATE connector_configurations
         SET checkpoint_json = ?, last_successful_sync_at = ?,
             last_error_at = NULL, updated_at = ?
         WHERE connector_id = ?`,
      )
      .bind(JSON.stringify(value), now, now, connectorId),
  ]);
}
