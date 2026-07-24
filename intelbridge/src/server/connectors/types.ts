export type ConnectionTestResult = {
  message: string;
  ok: boolean;
  testedAt: string;
};

export type DiscoveryInput = {
  missionId: string;
  query?: string;
  since?: string;
};

export type DiscoveredItem = {
  externalId: string;
  publishedAt: string;
  title: string;
  url: string;
};

export type RetrievedDocument = DiscoveredItem & {
  contentType: string;
  rawContent: string;
  retrievedAt: string;
};

export type NormalizedDocument = RetrievedDocument & {
  contentHash: string;
  normalizedContent: string;
  promptInjectionFlag: boolean;
  trustState: "UNTRUSTED_SOURCE";
};

export type ConnectorCheckpoint = {
  cursor: string;
  updatedAt: string;
  version: number;
};

export interface SourceConnectorAdapter {
  testConnection(): Promise<ConnectionTestResult>;
  discover(input: DiscoveryInput): Promise<DiscoveredItem[]>;
  retrieve(item: DiscoveredItem): Promise<RetrievedDocument>;
  normalize(document: RetrievedDocument): Promise<NormalizedDocument>;
  getCheckpoint(): Promise<ConnectorCheckpoint | null>;
  saveCheckpoint(checkpoint: ConnectorCheckpoint): Promise<void>;
}
