import { env } from "cloudflare:workers";

import { BaseConnectorAdapter } from "@/server/connectors/base";
import { fetchPublicResource } from "@/server/connectors/fetch";
import { normalizeRetrievedDocument } from "@/server/connectors/normalize";
import type {
  ConnectorContext,
  DiscoveredItem,
  DiscoveryInput,
} from "@/server/connectors/types";
import { ConnectorType } from "@/shared/domain";

function repositoryUrl(context: ConnectorContext) {
  const owner = encodeURIComponent(String(context.configuration.owner ?? ""));
  const repository = encodeURIComponent(
    String(context.configuration.repository ?? ""),
  );
  return `https://api.github.com/repos/${owner}/${repository}`;
}

function githubHeaders() {
  const token = (env as { GITHUB_TOKEN?: string }).GITHUB_TOKEN;
  return {
    Accept: "application/vnd.github+json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function githubJson(url: string) {
  const result = await fetchPublicResource(url, {
    accept: "application/json",
    headers: githubHeaders(),
    maxBytes: 2_000_000,
  });
  return JSON.parse(new TextDecoder().decode(result.bytes)) as unknown;
}

export class GithubConnectorAdapter extends BaseConnectorAdapter {
  readonly type = ConnectorType.GITHUB;

  async testConnection(context: ConnectorContext) {
    const startedAt = Date.now();
    await githubJson(repositoryUrl(context));
    return {
      message: "The public GitHub repository is reachable.",
      ok: true,
      responseTimeMs: Date.now() - startedAt,
      testedAt: new Date().toISOString(),
    };
  }

  async discover(input: DiscoveryInput, context: ConnectorContext) {
    void input;
    const maximum = Number(context.configuration.maximumItemsPerRun ?? 25);
    const items: DiscoveredItem[] = [];
    if (context.configuration.includeIssues !== false) {
      const issues = (await githubJson(
        `${repositoryUrl(context)}/issues?state=all&per_page=${maximum}`,
      )) as {
        body?: string;
        html_url: string;
        id: number;
        number: number;
        pull_request?: unknown;
        title: string;
        updated_at: string;
        user?: { login?: string };
      }[];
      for (const issue of issues) {
        if (issue.pull_request) continue;
        items.push({
          externalId: `issue:${issue.id}`,
          metadata: {
            author: issue.user?.login,
            body: issue.body ?? "",
            githubKind: "issue",
            number: issue.number,
          },
          publishedAt: issue.updated_at,
          title: issue.title,
          url: issue.html_url,
        });
      }
    }
    if (context.configuration.includeReleases !== false) {
      const releases = (await githubJson(
        `${repositoryUrl(context)}/releases?per_page=${maximum}`,
      )) as {
        author?: { login?: string };
        body?: string;
        html_url: string;
        id: number;
        name?: string;
        published_at?: string;
        tag_name: string;
      }[];
      for (const release of releases) {
        items.push({
          externalId: `release:${release.id}`,
          metadata: {
            author: release.author?.login,
            body: release.body ?? "",
            githubKind: "release",
            tagName: release.tag_name,
          },
          publishedAt: release.published_at,
          title: release.name || release.tag_name,
          url: release.html_url,
        });
      }
    }
    const limited = items
      .sort((left, right) =>
        String(right.publishedAt ?? "").localeCompare(
          String(left.publishedAt ?? ""),
        ),
      )
      .slice(0, maximum);
    return {
      items: limited,
      nextCheckpoint: {
        externalIds: limited.map((item) => item.externalId),
        retrievedAt: new Date().toISOString(),
      },
    };
  }

  async retrieve(item: DiscoveredItem, context: ConnectorContext) {
    return {
      author:
        typeof item.metadata.author === "string"
          ? item.metadata.author
          : undefined,
      canonicalUrl: item.url,
      externalId: item.externalId,
      metadata: item.metadata,
      mimeType: "text/markdown",
      publishedAt: item.publishedAt,
      publisher: `github.com/${String(context.configuration.owner)}/${String(
        context.configuration.repository,
      )}`,
      rawContent: String(item.metadata.body ?? ""),
      title: item.title,
    };
  }

  async normalize(document: Parameters<BaseConnectorAdapter["normalize"]>[0]) {
    return normalizeRetrievedDocument(document);
  }
}
