import { DemoConnectorAdapter } from "@/server/connectors/demo";
import { FileUploadConnectorAdapter } from "@/server/connectors/file-upload";
import { GithubConnectorAdapter } from "@/server/connectors/github";
import { RssConnectorAdapter } from "@/server/connectors/rss";
import type { SourceConnectorAdapter } from "@/server/connectors/types";
import {
  ManualUrlConnectorAdapter,
  WebpageConnectorAdapter,
} from "@/server/connectors/web";
import type { ConnectorType } from "@/shared/domain";

class ConnectorRegistry {
  private readonly adapters = new Map<ConnectorType, SourceConnectorAdapter>();

  register(adapter: SourceConnectorAdapter) {
    this.adapters.set(adapter.type, adapter);
    return this;
  }

  get(type: ConnectorType) {
    const adapter = this.adapters.get(type);
    if (!adapter) {
      throw new Error("CONNECTOR_ADAPTER_UNAVAILABLE");
    }
    return adapter;
  }

  has(type: ConnectorType) {
    return this.adapters.has(type);
  }
}

export const connectorRegistry = new ConnectorRegistry()
  .register(new DemoConnectorAdapter())
  .register(new RssConnectorAdapter())
  .register(new WebpageConnectorAdapter())
  .register(new ManualUrlConnectorAdapter())
  .register(new GithubConnectorAdapter())
  .register(new FileUploadConnectorAdapter());

export function registerConnectorAdapter(adapter: SourceConnectorAdapter) {
  connectorRegistry.register(adapter);
}
