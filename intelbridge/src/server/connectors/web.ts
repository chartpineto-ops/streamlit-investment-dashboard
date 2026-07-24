import { BaseConnectorAdapter } from "@/server/connectors/base";
import { fetchPublicResource } from "@/server/connectors/fetch";
import {
  decodePdfBytes,
  decodeUtf8,
  normalizeRetrievedDocument,
} from "@/server/connectors/normalize";
import {
  canonicalizePublicUrl,
  validatePublicUrl,
} from "@/server/connectors/security";
import type {
  ConnectorContext,
  DiscoveredItem,
  DiscoveryInput,
} from "@/server/connectors/types";
import { sha256 } from "@/server/repositories/documents";
import { ConnectorType } from "@/shared/domain";
import type { ConnectorType as ConnectorTypeValue } from "@/shared/domain";

function isAllowedDomain(hostname: string, allowedDomains: string[]) {
  return allowedDomains.some((domain) => {
    const normalized = domain.toLowerCase();
    return hostname === normalized || hostname.endsWith(`.${normalized}`);
  });
}

function extractLinks(html: string, baseUrl: string) {
  const links = new Set<string>();
  for (const match of html.matchAll(/\bhref=["']([^"'#]+)["']/gi)) {
    try {
      links.add(validatePublicUrl(new URL(match[1], baseUrl).toString()));
    } catch {
      // Invalid, private, and non-HTTP links are excluded from discovery.
    }
  }
  return [...links];
}

async function itemsFromUrls(urls: string[]) {
  return Promise.all(
    urls.map(async (url) => ({
      externalId: await sha256(url),
      metadata: {},
      title: new URL(url).pathname.split("/").filter(Boolean).at(-1) ?? url,
      url,
    })),
  );
}

export class WebpageConnectorAdapter extends BaseConnectorAdapter {
  readonly type: ConnectorTypeValue = ConnectorType.WEBPAGE;

  async testConnection(context: ConnectorContext) {
    const startedAt = Date.now();
    const startUrls = context.configuration.startUrls as string[] | undefined;
    if (!startUrls?.[0]) throw new Error("SOURCE_URL_INVALID");
    await fetchPublicResource(startUrls[0]);
    return {
      message: "The start page is reachable through the public-source policy.",
      ok: true,
      responseTimeMs: Date.now() - startedAt,
      testedAt: new Date().toISOString(),
    };
  }

  async discover(input: DiscoveryInput, context: ConnectorContext) {
    void input;
    const startUrls =
      (context.configuration.startUrls as string[] | undefined) ?? [];
    const allowedDomains =
      (context.configuration.allowedDomains as string[] | undefined) ??
      startUrls.map((url) => new URL(url).hostname);
    const maximum = Number(context.configuration.maximumPagesPerRun ?? 10);
    const urls = new Set(startUrls.map(canonicalizePublicUrl));

    for (const startUrl of startUrls) {
      if (urls.size >= maximum) break;
      const result = await fetchPublicResource(startUrl, {
        accept: "text/html",
      });
      const html = decodeUtf8(result.bytes);
      for (const link of extractLinks(html, result.canonicalUrl)) {
        if (isAllowedDomain(new URL(link).hostname, allowedDomains)) {
          urls.add(link);
          if (urls.size >= maximum) break;
        }
      }
    }
    const limited = [...urls].slice(0, maximum);
    return {
      items: await itemsFromUrls(limited),
      nextCheckpoint: {
        retrievedAt: new Date().toISOString(),
        urls: limited,
      },
    };
  }

  async retrieve(item: DiscoveredItem, context: ConnectorContext) {
    void context;
    if (!item.url) throw new Error("SOURCE_URL_INVALID");
    const result = await fetchPublicResource(item.url);
    return {
      canonicalUrl: result.canonicalUrl,
      externalId: item.externalId,
      metadata: item.metadata,
      mimeType: result.contentType,
      publishedAt: item.publishedAt,
      publisher: new URL(result.canonicalUrl).hostname,
      rawContent:
        result.contentType === "application/pdf"
          ? decodePdfBytes(result.bytes)
          : decodeUtf8(result.bytes),
      title: item.title,
    };
  }

  async normalize(document: Parameters<BaseConnectorAdapter["normalize"]>[0]) {
    return normalizeRetrievedDocument(document);
  }
}

export class ManualUrlConnectorAdapter extends WebpageConnectorAdapter {
  readonly type = ConnectorType.MANUAL_URL;

  async testConnection(context: ConnectorContext) {
    const startedAt = Date.now();
    const urls = (context.configuration.urls as string[] | undefined) ?? [];
    if (urls.length === 0) {
      return {
        message: "Connector is ready. Add URLs before starting a run.",
        ok: true,
        responseTimeMs: Date.now() - startedAt,
        testedAt: new Date().toISOString(),
      };
    }
    await fetchPublicResource(urls[0]);
    return {
      message: "The first configured URL is reachable.",
      ok: true,
      responseTimeMs: Date.now() - startedAt,
      testedAt: new Date().toISOString(),
    };
  }

  async discover(input: DiscoveryInput, context: ConnectorContext) {
    void input;
    const urls = ((context.configuration.urls as string[] | undefined) ?? [])
      .map(validatePublicUrl)
      .slice(0, 100);
    return {
      items: await itemsFromUrls(urls),
      nextCheckpoint: {
        retrievedAt: new Date().toISOString(),
        urls,
      },
    };
  }
}
