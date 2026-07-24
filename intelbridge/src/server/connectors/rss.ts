import { BaseConnectorAdapter } from "@/server/connectors/base";
import { fetchPublicResource } from "@/server/connectors/fetch";
import {
  decodeUtf8,
  normalizeRetrievedDocument,
} from "@/server/connectors/normalize";
import { canonicalizePublicUrl } from "@/server/connectors/security";
import type {
  ConnectorContext,
  DiscoveredItem,
  DiscoveryInput,
} from "@/server/connectors/types";
import { sha256 } from "@/server/repositories/documents";
import { ConnectorType } from "@/shared/domain";

function decodeXml(value: string) {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&apos;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&")
    .trim();
}

function xmlValue(block: string, names: string[]) {
  for (const name of names) {
    const match = block.match(
      new RegExp(`<${name}\\b[^>]*>([\\s\\S]*?)<\\/${name}>`, "i"),
    );
    if (match?.[1]) return decodeXml(match[1]);
  }
  return undefined;
}

function atomLink(block: string) {
  const match = block.match(/<link\b[^>]*\bhref=["']([^"']+)["'][^>]*\/?>/i);
  return match?.[1];
}

async function parseFeed(xml: string, feedUrl: string, maximum: number) {
  const blocks = [
    ...xml.matchAll(/<item\b[^>]*>([\s\S]*?)<\/item>/gi),
    ...xml.matchAll(/<entry\b[^>]*>([\s\S]*?)<\/entry>/gi),
  ].slice(0, maximum);
  const items: DiscoveredItem[] = [];
  for (const match of blocks) {
    const block = match[1];
    const link = xmlValue(block, ["link"]) ?? atomLink(block);
    const resolvedUrl = link
      ? canonicalizePublicUrl(new URL(link, feedUrl).toString())
      : undefined;
    const title = xmlValue(block, ["title"]) ?? "Untitled feed item";
    const published = xmlValue(block, [
      "pubDate",
      "published",
      "updated",
      "dc:date",
    ]);
    const parsedPublished = published
      ? new Date(published).toISOString()
      : undefined;
    const content =
      xmlValue(block, [
        "content:encoded",
        "content",
        "description",
        "summary",
      ]) ?? "";
    const guid = xmlValue(block, ["guid", "id"]);
    items.push({
      externalId:
        guid ?? (resolvedUrl ? await sha256(resolvedUrl) : await sha256(block)),
      metadata: {
        author: xmlValue(block, ["author", "dc:creator"]),
        feedUrl,
        syndicatedContent: content,
      },
      publishedAt: parsedPublished,
      title,
      url: resolvedUrl,
    });
  }
  return items;
}

export class RssConnectorAdapter extends BaseConnectorAdapter {
  readonly type = ConnectorType.RSS;

  async testConnection(context: ConnectorContext) {
    const started = Date.now();
    const feedUrl = String(context.configuration.feedUrl ?? "");
    const result = await fetchPublicResource(feedUrl, {
      accept:
        "application/rss+xml,application/atom+xml,application/xml,text/xml",
    });
    const text = decodeUtf8(result.bytes);
    if (!/<(?:rss|feed)\b/i.test(text)) {
      throw new Error("SOURCE_FEED_INVALID");
    }
    return {
      message: "Feed is reachable and contains RSS or Atom entries.",
      ok: true,
      responseTimeMs: Date.now() - started,
      testedAt: new Date().toISOString(),
    };
  }

  async discover(input: DiscoveryInput, context: ConnectorContext) {
    void input;
    const feedUrl = String(context.configuration.feedUrl ?? "");
    const maximum = Number(context.configuration.maximumItemsPerRun ?? 25);
    const result = await fetchPublicResource(feedUrl, {
      accept:
        "application/rss+xml,application/atom+xml,application/xml,text/xml",
    });
    const items = await parseFeed(
      decodeUtf8(result.bytes),
      result.canonicalUrl,
      maximum,
    );
    return {
      items,
      nextCheckpoint: {
        externalIds: items.map((item) => item.externalId),
        retrievedAt: new Date().toISOString(),
      },
    };
  }

  async retrieve(item: DiscoveredItem, context: ConnectorContext) {
    void context;
    if (item.url) {
      const result = await fetchPublicResource(item.url);
      return {
        author:
          typeof item.metadata.author === "string"
            ? item.metadata.author
            : undefined,
        canonicalUrl: result.canonicalUrl,
        externalId: item.externalId,
        metadata: item.metadata,
        mimeType: result.contentType,
        publishedAt: item.publishedAt,
        publisher: new URL(result.canonicalUrl).hostname,
        rawContent:
          result.contentType === "application/pdf"
            ? new TextDecoder("latin1").decode(result.bytes)
            : decodeUtf8(result.bytes),
        title: item.title,
      };
    }
    return {
      externalId: item.externalId,
      metadata: item.metadata,
      mimeType: "text/html",
      publishedAt: item.publishedAt,
      publisher: new URL(String(item.metadata.feedUrl)).hostname,
      rawContent: String(item.metadata.syndicatedContent ?? ""),
      title: item.title,
    };
  }

  async normalize(document: Parameters<BaseConnectorAdapter["normalize"]>[0]) {
    return normalizeRetrievedDocument(document);
  }
}
