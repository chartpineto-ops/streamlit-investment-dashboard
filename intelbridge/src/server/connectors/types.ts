import type { ConnectorType } from "@/shared/domain";
import type {
  DiscoveredItem,
  DiscoveryResult,
  NormalizedDocument,
  RetrievedDocument,
} from "@/shared/schemas/connectors";

export type ConnectionTestResult = {
  message: string;
  ok: boolean;
  responseTimeMs: number;
  testedAt: string;
};

export type ConnectorCheckpointValue = Record<string, unknown>;

export type ConnectorContext = {
  configuration: Record<string, unknown>;
  connectorId: string;
  requestId: string;
  workspaceId: string;
};

export type DiscoveryInput = {
  missionId: string;
  query?: string;
  since?: string;
};

export interface SourceConnectorAdapter {
  readonly type: ConnectorType;
  testConnection(context: ConnectorContext): Promise<ConnectionTestResult>;
  discover(
    input: DiscoveryInput,
    context: ConnectorContext,
  ): Promise<DiscoveryResult>;
  retrieve(
    item: DiscoveredItem,
    context: ConnectorContext,
  ): Promise<RetrievedDocument>;
  normalize(
    document: RetrievedDocument,
    context: ConnectorContext,
  ): Promise<NormalizedDocument>;
  getCheckpoint(
    connectorId: string,
    key: string,
  ): Promise<ConnectorCheckpointValue | null>;
  saveCheckpoint(
    connectorId: string,
    key: string,
    value: ConnectorCheckpointValue,
  ): Promise<void>;
}

export type {
  DiscoveredItem,
  DiscoveryResult,
  NormalizedDocument,
  RetrievedDocument,
};
