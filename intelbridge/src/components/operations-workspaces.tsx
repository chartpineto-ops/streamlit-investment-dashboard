import { FileText, History, RadioTower } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import type { getDocumentsWorkspaceData } from "@/server/services/documents";
import type { getRunsWorkspaceData } from "@/server/services/runs";
import { formatDateTime, formatEnumLabel } from "@/shared/presentation";

export function RunsWorkspace({
  data,
}: {
  data: Awaited<ReturnType<typeof getRunsWorkspaceData>>;
}) {
  return (
    <>
      <PageHeader
        description="Inspect queued and completed ingestion runs, durable step state, retries, and source-level processing metrics."
        eyebrow="Research-run engine"
        title="Runs"
      />
      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <table className="w-full border-collapse text-left text-[11px]">
          <caption className="sr-only">
            Research runs in the active IntelBridge workspace
          </caption>
          <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
            <tr>
              <th className="px-4 py-2.5">Mission</th>
              <th className="px-4 py-2.5">State</th>
              <th className="px-4 py-2.5">Trigger</th>
              <th className="px-4 py-2.5 text-right">Progress</th>
              <th className="px-4 py-2.5 text-right">Documents</th>
              <th className="px-4 py-2.5">Started</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--rule-subtle)]">
            {data.runs.length ? (
              data.runs.map((run) => (
                <tr key={run.id}>
                  <td className="px-4 py-3">
                    <Link
                      className="font-semibold text-[var(--accent-strong)]"
                      href={`/runs/${run.id}`}
                    >
                      {run.missionTitle}
                    </Link>
                    <div className="mt-1 font-mono text-[9px] text-[var(--text-3)]">
                      {run.id}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="px-4 py-3 text-[10px]">
                    {formatEnumLabel(run.triggerType)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {run.progressPercent}%
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {run.documentsProcessed}
                  </td>
                  <td className="px-4 py-3 text-[10px] text-[var(--text-3)]">
                    {formatDateTime(new Date(run.startedAt))}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  className="px-4 py-12 text-center text-[var(--text-3)]"
                  colSpan={6}
                >
                  No research runs exist. Start a ready mission to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </>
  );
}

export function DocumentsWorkspace({
  data,
  filters,
}: {
  data: Awaited<ReturnType<typeof getDocumentsWorkspaceData>>;
  filters: {
    after?: string;
    change?: string;
    connector?: string;
    mission?: string;
    q?: string;
  };
}) {
  return (
    <>
      <PageHeader
        description="Search canonical source documents and inspect retrieval state, current content hashes, and immutable version history."
        eyebrow="Connector ingestion"
        title="Documents"
      />
      <form
        className="mb-4 grid gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-3 md:grid-cols-2 xl:grid-cols-[1fr_190px_220px_170px_170px_auto]"
        method="get"
      >
        <label className="sr-only" htmlFor="document-query">
          Search documents
        </label>
        <input
          className="h-9 min-w-64 flex-1 rounded-[3px] border border-[var(--rule)] px-3 text-[11px]"
          defaultValue={filters.q}
          id="document-query"
          name="q"
          placeholder="Search title or normalized text"
        />
        <select
          aria-label="Change state"
          className="h-9 rounded-[3px] border border-[var(--rule)] px-3 text-[11px]"
          defaultValue={filters.change ?? ""}
          name="change"
        >
          <option value="">All change states</option>
          <option value="CREATED">Created</option>
          <option value="UPDATED">Updated</option>
          <option value="UNCHANGED">Unchanged</option>
        </select>
        <select
          aria-label="Source connector"
          className="h-9 rounded-[3px] border border-[var(--rule)] px-3 text-[11px]"
          defaultValue={filters.connector ?? ""}
          name="connector"
        >
          <option value="">All sources</option>
          {data.connectors.map((connector) => (
            <option key={connector.id} value={connector.id}>
              {connector.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Mission"
          className="h-9 rounded-[3px] border border-[var(--rule)] px-3 text-[11px]"
          defaultValue={filters.mission ?? ""}
          name="mission"
        >
          <option value="">All missions</option>
          {data.missions.map((mission) => (
            <option key={mission.id} value={mission.id}>
              {mission.title}
            </option>
          ))}
        </select>
        <input
          aria-label="Retrieved after"
          className="h-9 rounded-[3px] border border-[var(--rule)] px-3 text-[11px]"
          defaultValue={filters.after}
          name="after"
          type="date"
        />
        <button
          className="h-9 rounded-[3px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)]"
          type="submit"
        >
          Filter
        </button>
      </form>
      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <table className="w-full border-collapse text-left text-[11px]">
          <caption className="sr-only">
            Ingested documents in the active IntelBridge workspace
          </caption>
          <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
            <tr>
              <th className="px-4 py-2.5">Document</th>
              <th className="px-4 py-2.5">Source</th>
              <th className="px-4 py-2.5">Change</th>
              <th className="px-4 py-2.5 text-right">Version</th>
              <th className="px-4 py-2.5">Retrieved</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--rule-subtle)]">
            {data.documents.length ? (
              data.documents.map((document) => (
                <tr key={document.id}>
                  <td className="px-4 py-3">
                    <Link
                      className="font-semibold text-[var(--accent-strong)]"
                      href={`/documents/${document.id}`}
                    >
                      {document.title}
                    </Link>
                    <div className="mt-1 max-w-xl truncate text-[9px] text-[var(--text-3)]">
                      {document.canonicalUrl}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div>{document.connector.name}</div>
                    <div className="mt-1 text-[9px] text-[var(--text-3)]">
                      {document.mission.title}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={document.changeStatus} />
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {document.version}
                  </td>
                  <td className="px-4 py-3 text-[10px] text-[var(--text-3)]">
                    {document.lastRetrievedAt
                      ? formatDateTime(new Date(document.lastRetrievedAt))
                      : "Unavailable"}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  className="px-4 py-12 text-center text-[var(--text-3)]"
                  colSpan={5}
                >
                  No documents match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
      <div className="mt-4 flex items-center gap-2 text-[10px] text-[var(--text-3)]">
        <RadioTower aria-hidden="true" className="size-3.5" />
        Retrieval failures remain attached to their run; unchanged content does
        not create a new version.
      </div>
    </>
  );
}

export function DocumentDetail({
  detail,
  selectedVersionId,
}: {
  detail: NonNullable<
    Awaited<
      ReturnType<
        typeof import("@/server/services/documents").getDocumentForCurrentWorkspace
      >
    >
  >;
  selectedVersionId?: string;
}) {
  const selected =
    detail.versions.find((version) => version.id === selectedVersionId) ??
    detail.versions[0];
  return (
    <>
      <PageHeader
        description={`${detail.document.publisher} · ${detail.document.mimeType} · retrieved ${detail.document.lastRetrievedAt ? formatDateTime(new Date(detail.document.lastRetrievedAt)) : "unavailable"}`}
        eyebrow={`Document · ${detail.document.id.slice(-12).toUpperCase()}`}
        title={detail.document.title}
      />
      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="h-fit rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <History aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">Version history</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {detail.versions.map((version) => (
              <Link
                className={`block px-4 py-3 ${selected?.id === version.id ? "bg-[var(--accent-soft)]" : "hover:bg-[var(--surface-2)]"}`}
                href={`/documents/${detail.document.id}?version=${version.id}`}
                key={version.id}
              >
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-semibold">
                    Version {version.versionNumber}
                  </span>
                  {detail.document.currentVersionId === version.id ? (
                    <StatusBadge status="CURRENT" />
                  ) : null}
                </div>
                <div className="mt-1 text-[9px] text-[var(--text-3)]">
                  {formatDateTime(new Date(version.retrievedAt))}
                </div>
              </Link>
            ))}
          </div>
        </aside>
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <FileText aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">
              Normalized content
            </h2>
          </div>
          {selected ? (
            <>
              <dl className="grid border-b border-[var(--rule)] bg-[var(--surface-2)] sm:grid-cols-3">
                {[
                  ["Version", selected.versionNumber],
                  ["MIME type", selected.mimeType],
                  ["Hash", selected.contentHash.slice(0, 16)],
                ].map(([label, value]) => (
                  <div className="px-4 py-3" key={label}>
                    <dt className="text-[9px] uppercase text-[var(--text-3)]">
                      {label}
                    </dt>
                    <dd className="m-0 mt-1 font-mono text-[10px]">{value}</dd>
                  </div>
                ))}
              </dl>
              <pre className="m-0 max-h-[640px] overflow-auto whitespace-pre-wrap p-5 font-sans text-[11px] leading-6">
                {selected.normalizedContent}
              </pre>
            </>
          ) : (
            <div className="p-12 text-center text-[11px] text-[var(--text-3)]">
              No persisted version is available for this document.
            </div>
          )}
        </section>
      </div>
    </>
  );
}
