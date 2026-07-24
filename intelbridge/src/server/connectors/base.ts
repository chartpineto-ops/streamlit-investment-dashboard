import type {
  ConnectorContext,
  ConnectorCheckpointValue,
  DiscoveredItem,
  DiscoveryInput,
  DiscoveryResult,
  NormalizedDocument,
  RetrievedDocument,
  SourceConnectorAdapter,
} from "@/server/connectors/types";
import type { ConnectorType } from "@/shared/domain";

export abstract class BaseConnectorAdapter implements SourceConnectorAdapter {
  abstract readonly type: ConnectorType;
  abstract testConnection(
    context: ConnectorContext,
  ): ReturnType<SourceConnectorAdapter["testConnection"]>;
  abstract discover(
    input: DiscoveryInput,
    context: ConnectorContext,
  ): Promise<DiscoveryResult>;
  abstract retrieve(
    item: DiscoveredItem,
    context: ConnectorContext,
  ): Promise<RetrievedDocument>;
  abstract normalize(
    document: RetrievedDocument,
    context: ConnectorContext,
  ): Promise<NormalizedDocument>;

  async getCheckpoint(connectorId: string, key: string) {
    const { getConnectorCheckpoint } =
      await import("@/server/connectors/checkpoints");
    return getConnectorCheckpoint(connectorId, key);
  }

  async saveCheckpoint(
    connectorId: string,
    key: string,
    value: ConnectorCheckpointValue,
  ) {
    const { saveConnectorCheckpoint } =
      await import("@/server/connectors/checkpoints");
    await saveConnectorCheckpoint(connectorId, key, value);
  }
}
