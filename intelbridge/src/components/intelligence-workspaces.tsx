import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  BookOpenText,
  Bot,
  Braces,
  Database,
  FileBarChart,
  FileSearch,
  FolderKanban,
  Link2,
  Play,
  RadioTower,
  ShieldCheck,
  Upload,
} from "lucide-react";
import Link from "next/link";

import {
  createReportAction,
  ingestSourceAction,
  setMonitorStatusAction,
  startResearchAction,
} from "@/app/actions";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import type {
  getAgentStudioWorkspace,
  getDatasetsWorkspace,
  getEvidenceWorkspace,
  getInsightsWorkspace,
  getMonitoringWorkspace,
  getProjectsWorkspace,
  getReportsWorkspace,
  getSourcesWorkspace,
} from "@/server/services/intelligence";
import {
  formatDateTime,
  formatEnumLabel,
  formatNumber,
  formatPercent,
} from "@/shared/presentation";

const inputClass =
  "h-9 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] outline-none";
const primaryButtonClass =
  "inline-flex min-h-9 items-center justify-center gap-2 rounded-[3px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)] hover:bg-[var(--accent-hover)]";
const secondaryButtonClass =
  "inline-flex min-h-8 items-center justify-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[10px] font-semibold text-[var(--text-2)] hover:bg-[var(--surface-2)]";

function Notice({ error, notice }: { error?: string; notice?: string }) {
  if (!notice && !error) {
    return null;
  }
  return (
    <div
      className={`mb-4 rounded-[3px] border px-4 py-3 text-[11px] ${
        error
          ? "border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] text-[var(--status-negative-text)]"
          : "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]"
      }`}
      role={error ? "alert" : "status"}
    >
      {error
        ? `Source action failed: ${formatEnumLabel(error)}.`
        : `Action completed: ${formatEnumLabel(notice ?? "")}.`}
    </div>
  );
}

export function SourcesWorkspace({
  data,
  error,
  missionId,
  notice,
  query,
}: {
  data: Awaited<ReturnType<typeof getSourcesWorkspace>>;
  error?: string;
  missionId?: string;
  notice?: string;
  query?: string;
}) {
  return (
    <>
      <PageHeader
        description="Approved connectors, retrieval health, checkpoints, and versioned source records. Retrieved content is always treated as untrusted."
        eyebrow="Collection"
        title="Sources"
      />
      <Notice error={error} notice={notice} />

      <section className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] md:grid-cols-2 xl:grid-cols-3">
        {data.connectors.map((connector, index) => (
          <article
            className={`p-4 ${index ? "border-t border-[var(--rule)] md:border-l md:border-t-0" : ""} ${
              index === 2
                ? "md:border-l-0 md:border-t xl:border-l xl:border-t-0"
                : ""
            } ${index > 2 ? "border-t border-[var(--rule)]" : ""}`}
            key={connector.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[12px] font-semibold">
                  {connector.name}
                </div>
                <div className="mt-1 text-[10px] text-[var(--text-3)]">
                  {formatEnumLabel(connector.type)}
                </div>
              </div>
              <StatusBadge status={connector.status} />
            </div>
            <p className="mb-0 mt-3 text-[10px] leading-4 text-[var(--text-3)]">
              {connector.status === "AVAILABLE"
                ? connector.type === "DEMO"
                  ? "Deterministic fictional corpus with a durable checkpoint."
                  : "Available for governed user-initiated ingestion."
                : "No active production connection. Credentials and retrieval are not simulated."}
            </p>
          </article>
        ))}
      </section>

      <div className="mb-4 grid gap-4 xl:grid-cols-2">
        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Link2
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">
              Retrieve a public URL
            </h2>
          </div>
          <form action={ingestSourceAction} className="grid gap-3 p-4">
            <input name="mode" type="hidden" value="url" />
            <label className="grid gap-1 text-[10px] font-semibold">
              Mission
              <select
                className={inputClass}
                defaultValue={missionId ?? data.missions[0]?.id}
                name="missionId"
                required
              >
                {data.missions.map((mission) => (
                  <option key={mission.id} value={mission.id}>
                    {mission.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-[10px] font-semibold">
              Approved HTTPS URL
              <input
                className={inputClass}
                name="url"
                placeholder="https://example.com/research"
                required
                type="url"
              />
            </label>
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] leading-4 text-[var(--text-3)]">
                Private hosts, insecure URLs, redirects to blocked hosts, and
                oversized responses are rejected.
              </span>
              <button className={primaryButtonClass} type="submit">
                <Play aria-hidden="true" className="size-3.5" />
                Retrieve
              </button>
            </div>
          </form>
        </section>

        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Upload
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">
              Upload a governed source
            </h2>
          </div>
          <form
            action={ingestSourceAction}
            className="grid gap-3 p-4"
            encType="multipart/form-data"
          >
            <input name="mode" type="hidden" value="file" />
            <label className="grid gap-1 text-[10px] font-semibold">
              Mission
              <select className={inputClass} name="missionId" required>
                {data.missions.map((mission) => (
                  <option key={mission.id} value={mission.id}>
                    {mission.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-[10px] font-semibold">
              Text, Markdown, CSV, JSON, XML, or PDF · 10 MB maximum
              <input
                accept=".txt,.md,.csv,.json,.xml,.pdf,text/plain,text/markdown,text/csv,application/json,application/pdf"
                className={`${inputClass} py-2`}
                name="file"
                required
                type="file"
              />
            </label>
            <div className="flex items-center justify-between gap-3">
              <span className="text-[10px] leading-4 text-[var(--text-3)]">
                Small text is normalized in D1; binary and larger objects use
                private R2 storage.
              </span>
              <button className={primaryButtonClass} type="submit">
                <Upload aria-hidden="true" className="size-3.5" />
                Upload
              </button>
            </div>
          </form>
        </section>
      </div>

      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex flex-col gap-3 border-b border-[var(--rule)] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="m-0 text-[13px] font-semibold">
              Source document ledger
            </h2>
            <p className="mb-0 mt-1 text-[10px] text-[var(--text-3)]">
              {formatNumber(data.documents.length)} versioned records
            </p>
          </div>
          <form className="flex gap-2" method="get">
            <input
              className={inputClass}
              defaultValue={query}
              name="q"
              placeholder="Search title, publisher, or content"
            />
            <button className={secondaryButtonClass} type="submit">
              Search
            </button>
          </form>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] border-collapse text-left text-[11px]">
            <caption className="sr-only">
              Versioned source documents in the authenticated workspace
            </caption>
            <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
              <tr>
                <th className="px-4 py-2.5">Document</th>
                <th className="px-3 py-2.5">Mission</th>
                <th className="px-3 py-2.5">Type</th>
                <th className="px-3 py-2.5">Published</th>
                <th className="px-3 py-2.5">Retrieved</th>
                <th className="px-3 py-2.5 text-right">Evidence</th>
                <th className="px-3 py-2.5">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--rule-subtle)]">
              {data.documents.length ? (
                data.documents.map((document) => (
                  <tr className="hover:bg-[var(--row-hover)]" key={document.id}>
                    <td className="max-w-[310px] px-4 py-3">
                      <a
                        className="font-semibold text-[var(--accent-strong)]"
                        href={document.canonicalUrl}
                        rel="noreferrer"
                        target="_blank"
                      >
                        {document.title}
                      </a>
                      <div className="mt-1 text-[10px] text-[var(--text-3)]">
                        {document.publisher} · version {document.version} ·{" "}
                        {document.trustState}
                      </div>
                    </td>
                    <td className="px-3 py-3">{document.missionTitle}</td>
                    <td className="px-3 py-3">
                      {formatEnumLabel(document.sourceType)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3">
                      {formatDateTime(document.publishedAt)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3">
                      {formatDateTime(document.retrievedAt)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono">
                      {document.evidenceCount}
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge
                        status={document.isDemo ? "DEMO" : "AVAILABLE"}
                      />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    className="px-4 py-10 text-center text-[var(--text-3)]"
                    colSpan={7}
                  >
                    No source documents match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

export function EvidenceWorkspace({
  data,
  missionId,
  query,
  status,
}: {
  data: Awaited<ReturnType<typeof getEvidenceWorkspace>>;
  missionId?: string;
  query?: string;
  status?: string;
}) {
  return (
    <>
      <PageHeader
        description="Searchable excerpts with complete source, retrieval, extraction, quality, novelty, relationship, and validation metadata."
        eyebrow="Evidence ledger"
        title="Evidence"
      />
      <form
        className="mb-4 grid gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-3 md:grid-cols-[1fr_220px_180px_auto]"
        method="get"
      >
        <input
          className={inputClass}
          defaultValue={query}
          name="q"
          placeholder="Search excerpts, claims, or publishers"
        />
        <select
          className={inputClass}
          defaultValue={missionId ?? ""}
          name="mission"
        >
          <option value="">All missions</option>
          {data.missions.map((mission) => (
            <option key={mission.id} value={mission.id}>
              {mission.title}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          defaultValue={status ?? ""}
          name="status"
        >
          <option value="">All validation states</option>
          <option value="VALIDATED">Validated</option>
          <option value="CONTRADICTED">Contradicted</option>
          <option value="SINGLE_SOURCE">Single source</option>
        </select>
        <button className={primaryButtonClass} type="submit">
          Apply filters
        </button>
      </form>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,0.45fr)]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="border-b border-[var(--rule)] px-4 py-3">
            <h2 className="m-0 text-[13px] font-semibold">
              Evidence records · {formatNumber(data.records.length)}
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] border-collapse text-left text-[11px]">
              <caption className="sr-only">
                Searchable mission evidence with source and validation fields
              </caption>
              <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
                <tr>
                  <th className="px-4 py-2.5">Excerpt</th>
                  <th className="px-3 py-2.5">Source</th>
                  <th className="px-3 py-2.5">Topic</th>
                  <th className="px-3 py-2.5">Relationship</th>
                  <th className="px-3 py-2.5 text-right">Relevance</th>
                  <th className="px-3 py-2.5 text-right">Confidence</th>
                  <th className="px-3 py-2.5">Validation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--rule-subtle)]">
                {data.records.length ? (
                  data.records.map((record) => (
                    <tr
                      className="align-top hover:bg-[var(--row-hover)]"
                      key={record.id}
                    >
                      <td className="max-w-[360px] px-4 py-3">
                        <Link
                          className="line-clamp-3 font-medium leading-5 text-[var(--text-1)]"
                          href={`/evidence?selected=${record.id}`}
                        >
                          {record.excerpt}
                        </Link>
                        <div className="mt-1 text-[10px] text-[var(--text-3)]">
                          {record.missionTitle} · {record.evidenceType}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <div className="font-semibold">{record.publisher}</div>
                        <div className="mt-1 text-[10px] text-[var(--text-3)]">
                          {formatDateTime(record.publishedAt)}
                        </div>
                      </td>
                      <td className="px-3 py-3">{record.topics.join(", ")}</td>
                      <td className="px-3 py-3">
                        {formatEnumLabel(record.relationship)}
                      </td>
                      <td className="px-3 py-3 text-right font-mono">
                        {formatPercent(record.relevanceScore)}
                      </td>
                      <td className="px-3 py-3 text-right font-mono">
                        {formatPercent(record.confidenceScore)}
                      </td>
                      <td className="px-3 py-3">
                        <StatusBadge status={record.validationStatus} />
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      className="px-4 py-10 text-center text-[var(--text-3)]"
                      colSpan={7}
                    >
                      No evidence matches the selected filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <FileSearch
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">Evidence detail</h2>
          </div>
          {data.selected ? (
            <div className="grid gap-4 p-4">
              <div>
                <div className="text-[10px] font-semibold uppercase text-[var(--text-3)]">
                  Full excerpt
                </div>
                <p className="mb-0 mt-2 text-[12px] leading-5">
                  {data.selected.excerpt}
                </p>
              </div>
              <div>
                <div className="text-[10px] font-semibold uppercase text-[var(--text-3)]">
                  Surrounding context
                </div>
                <p className="mb-0 mt-2 text-[10px] leading-5 text-[var(--text-2)]">
                  {data.selected.contextText}
                </p>
              </div>
              <dl className="m-0 grid gap-2 text-[10px]">
                {[
                  ["Publisher", data.selected.publisher],
                  ["Document", data.selected.documentTitle],
                  ["Document version", data.selected.version.toString()],
                  ["Published", formatDateTime(data.selected.publishedAt)],
                  ["Retrieved", formatDateTime(data.selected.retrievedAt)],
                  ["Extracted", formatDateTime(data.selected.extractedAt)],
                  ["Claim", data.selected.claimStatement ?? "Not linked"],
                  ["Relationship", formatEnumLabel(data.selected.relationship)],
                  [
                    "Source quality",
                    formatPercent(data.selected.sourceQualityScore),
                  ],
                  ["Novelty", formatPercent(data.selected.noveltyScore)],
                  ["Data state", data.selected.dataStatus.toUpperCase()],
                ].map(([label, value]) => (
                  <div
                    className="grid grid-cols-[120px_1fr] gap-3 border-t border-[var(--rule-subtle)] pt-2"
                    key={label}
                  >
                    <dt className="text-[var(--text-3)]">{label}</dt>
                    <dd className="m-0 break-words font-medium">{value}</dd>
                  </div>
                ))}
              </dl>
              <a
                className={secondaryButtonClass}
                href={data.selected.canonicalUrl}
                rel="noreferrer"
                target="_blank"
              >
                <Link2 aria-hidden="true" className="size-3.5" />
                Open canonical source
              </a>
            </div>
          ) : (
            <div className="grid min-h-64 place-items-center p-6 text-center text-[11px] leading-5 text-[var(--text-3)]">
              Select an evidence row to inspect its source trail, context,
              linked claim, and validation state.
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

export function InsightsWorkspace({
  category,
  data,
  missionId,
}: {
  category?: string;
  data: Awaited<ReturnType<typeof getInsightsWorkspace>>;
  missionId?: string;
}) {
  return (
    <>
      <PageHeader
        description="Decision-ready findings that remain linked to persisted claims, evidence relationships, source diversity, assumptions, and uncertainty."
        eyebrow="Synthesis"
        title="Insights"
      />
      <form
        className="mb-4 flex flex-wrap gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-3"
        method="get"
      >
        <select
          className={inputClass}
          defaultValue={missionId ?? ""}
          name="mission"
        >
          <option value="">All missions</option>
          {data.missions.map((mission) => (
            <option key={mission.id} value={mission.id}>
              {mission.title}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          defaultValue={category ?? ""}
          name="category"
        >
          <option value="">All categories</option>
          {[
            "STRATEGIC",
            "PRODUCT_GAP",
            "OPPORTUNITY",
            "RISK",
            "CONTRADICTION",
            "KNOWLEDGE_GAP",
          ].map((value) => (
            <option key={value} value={value}>
              {formatEnumLabel(value)}
            </option>
          ))}
        </select>
        <button className={primaryButtonClass} type="submit">
          Apply filters
        </button>
      </form>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(480px,1.1fr)]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="border-b border-[var(--rule)] px-4 py-3">
            <h2 className="m-0 text-[13px] font-semibold">
              Ranked findings · {data.records.length}
            </h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {data.records.length ? (
              data.records.map((insight) => (
                <Link
                  className="block p-4 hover:bg-[var(--row-hover)]"
                  href={`/insights?selected=${insight.id}`}
                  key={insight.id}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={insight.category} />
                    <StatusBadge status={insight.severity} />
                    <span className="ml-auto text-[10px] font-mono text-[var(--text-3)]">
                      {formatPercent(insight.confidenceScore)} confidence
                    </span>
                  </div>
                  <h3 className="mb-0 mt-3 text-[13px] font-semibold">
                    {insight.title}
                  </h3>
                  <p className="mb-0 mt-1 line-clamp-2 text-[11px] leading-5 text-[var(--text-2)]">
                    {insight.summary}
                  </p>
                  <div className="mt-3 text-[10px] text-[var(--text-3)]">
                    {insight.sourceCount} sources · {insight.claimCount} linked
                    claims · owner {insight.owner}
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-10 text-center text-[11px] text-[var(--text-3)]">
                No supported insights match the selected filters.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <ShieldCheck
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">Insight detail</h2>
          </div>
          {data.selected ? (
            <div className="grid gap-5 p-5">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={data.selected.category} />
                  <StatusBadge status={data.selected.severity} />
                  <StatusBadge status="DEMO" />
                </div>
                <h3 className="mb-0 mt-3 text-[17px] font-semibold">
                  {data.selected.title}
                </h3>
                <p className="mb-0 mt-2 text-[12px] leading-6 text-[var(--text-2)]">
                  {data.selected.summary}
                </p>
              </div>
              <dl className="m-0 grid grid-cols-2 overflow-hidden rounded-[3px] border border-[var(--rule)] text-[10px]">
                {[
                  ["Confidence", formatPercent(data.selected.confidenceScore)],
                  [
                    "Materiality",
                    formatPercent(data.selected.materialityScore),
                  ],
                  ["Novelty", formatPercent(data.selected.noveltyScore)],
                  ["Source diversity", `${data.selected.sourceCount} sources`],
                  ["Owner", data.selected.owner],
                  ["Generated", formatDateTime(data.selected.createdAt)],
                ].map(([label, value], index) => (
                  <div
                    className={`p-3 ${index % 2 ? "border-l border-[var(--rule)]" : ""} ${index > 1 ? "border-t border-[var(--rule)]" : ""}`}
                    key={label}
                  >
                    <dt className="uppercase text-[var(--text-3)]">{label}</dt>
                    <dd className="m-0 mt-1 font-semibold">{value}</dd>
                  </div>
                ))}
              </dl>
              <div>
                <div className="text-[10px] font-semibold uppercase text-[var(--text-3)]">
                  Recommended action
                </div>
                <p className="mb-0 mt-2 text-[11px] leading-5">
                  {data.selected.recommendedAction}
                </p>
              </div>
              <div>
                <div className="text-[10px] font-semibold uppercase text-[var(--text-3)]">
                  Supporting claims
                </div>
                <ul className="m-0 mt-2 list-none divide-y divide-[var(--rule-subtle)] border-y border-[var(--rule-subtle)] p-0">
                  {data.selectedClaims.map((claim) => (
                    <li className="py-3" key={claim.id}>
                      <div className="text-[11px] font-medium">
                        {claim.statement}
                      </div>
                      <div className="mt-1 text-[10px] text-[var(--text-3)]">
                        {claim.supportingCount} supporting ·{" "}
                        {claim.contradictingCount} contradicting ·{" "}
                        {formatPercent(claim.confidenceScore)} confidence
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-[3px] border border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] p-3 text-[10px] leading-5 text-[var(--status-warning-text)]">
                <strong>Uncertainty:</strong> {data.selected.uncertaintyNote}
              </div>
              <div className="text-[10px] leading-5 text-[var(--text-3)]">
                <strong>Assumptions:</strong>{" "}
                {data.selected.assumptions.join(" · ")}
                <br />
                <strong>Calculation references:</strong>{" "}
                {data.selected.calculationReferences.join(" · ")}
              </div>
            </div>
          ) : (
            <div className="grid min-h-72 place-items-center p-6 text-center text-[11px] text-[var(--text-3)]">
              Select an insight to inspect its claims, evidence diversity,
              uncertainty, owner, and recommended action.
            </div>
          )}
        </section>
      </div>
    </>
  );
}

export function MonitoringWorkspace({
  data,
  notice,
}: {
  data: Awaited<ReturnType<typeof getMonitoringWorkspace>>;
  notice?: string;
}) {
  return (
    <>
      <PageHeader
        description="Incremental mission schedules and materiality gates. Alerts are withheld when no meaningful change clears every threshold."
        eyebrow="Change detection"
        title="Monitoring"
      />
      <Notice notice={notice} />
      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.7fr)]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <RadioTower
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">Monitor policies</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {data.monitors.map((monitor) => (
              <article className="p-4" key={monitor.id}>
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] font-semibold">
                      {monitor.missionTitle}
                    </div>
                    <div className="mt-1 text-[10px] text-[var(--text-3)]">
                      {formatEnumLabel(monitor.schedule)} · next{" "}
                      {monitor.nextCheckAt
                        ? formatDateTime(monitor.nextCheckAt)
                        : "not scheduled"}
                    </div>
                  </div>
                  <StatusBadge status={monitor.status} />
                  <form action={startResearchAction}>
                    <input
                      name="missionId"
                      type="hidden"
                      value={monitor.missionId}
                    />
                    <input
                      name="idempotencyKey"
                      type="hidden"
                      value={`monitor-manual:${monitor.id}:${crypto.randomUUID()}`}
                    />
                    <button className={secondaryButtonClass} type="submit">
                      Run now
                    </button>
                  </form>
                  <form action={setMonitorStatusAction}>
                    <input name="monitorId" type="hidden" value={monitor.id} />
                    <input
                      name="status"
                      type="hidden"
                      value={monitor.status === "ACTIVE" ? "PAUSED" : "ACTIVE"}
                    />
                    <button className={secondaryButtonClass} type="submit">
                      {monitor.status === "ACTIVE" ? "Pause" : "Resume"}
                    </button>
                  </form>
                </div>
                <dl className="m-0 mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-[10px] md:grid-cols-4">
                  <div>
                    <dt className="text-[var(--text-3)]">Materiality</dt>
                    <dd className="m-0 mt-1 font-mono font-semibold">
                      ≥ {formatPercent(monitor.materialityThreshold)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-3)]">Confidence</dt>
                    <dd className="m-0 mt-1 font-mono font-semibold">
                      ≥ {formatPercent(monitor.minimumConfidence)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-3)]">Source minimum</dt>
                    <dd className="m-0 mt-1 font-mono font-semibold">
                      {monitor.requiredSourceCount}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[var(--text-3)]">Cooldown</dt>
                    <dd className="m-0 mt-1 font-mono font-semibold">
                      {monitor.alertCooldownMinutes / 60}h
                    </dd>
                  </div>
                </dl>
                <div className="mt-3 text-[10px] leading-4 text-[var(--text-3)]">
                  Topics: {monitor.topicAllowlist.join(", ") || "all"} ·
                  Entities: {monitor.entityWatchlist.join(", ") || "all"} ·
                  Contradictions {monitor.contradictionAlerts ? "on" : "off"} ·
                  Source failures {monitor.sourceFailureAlerts ? "on" : "off"}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <AlertTriangle
              aria-hidden="true"
              className="size-4 text-[var(--warning)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">
              Material-change alerts
            </h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {data.alerts.map((alert) => (
              <article className="p-4" key={alert.id}>
                <div className="flex items-center gap-2">
                  <StatusBadge status={alert.alertType} />
                  <StatusBadge status={alert.status} />
                  <span className="ml-auto font-mono text-[10px] text-[var(--text-3)]">
                    {formatPercent(alert.materialityScore)}
                  </span>
                </div>
                <div className="mt-3 text-[12px] font-semibold">
                  {alert.title}
                </div>
                <p className="mb-0 mt-1 text-[10px] leading-5 text-[var(--text-2)]">
                  {alert.summary}
                </p>
                <div className="mt-2 text-[10px] text-[var(--text-3)]">
                  {alert.missionTitle} · {formatDateTime(alert.createdAt)}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
      <div className="rounded-[3px] border border-[var(--status-info-border)] bg-[var(--status-info-fill)] p-3 text-[10px] leading-5 text-[var(--status-info-text)]">
        Schedules and checkpoints are durable. In this Sites release, scheduled
        workers are represented by persisted next-check state; use Run Research
        for an immediate incremental scan until managed cron execution is
        enabled for the project.
      </div>
    </>
  );
}

export function ReportsWorkspace({
  data,
  notice,
}: {
  data: Awaited<ReturnType<typeof getReportsWorkspace>>;
  notice?: string;
}) {
  return (
    <>
      <PageHeader
        description="Generate executive briefs, evidence tables, and machine-readable packages directly from persisted mission records."
        eyebrow="Decision packages"
        title="Reports"
      />
      <Notice notice={notice} />
      <section className="mb-4 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
          <FileBarChart
            aria-hidden="true"
            className="size-4 text-[var(--accent-strong)]"
          />
          <h2 className="m-0 text-[13px] font-semibold">Generate report</h2>
        </div>
        <form
          action={createReportAction}
          className="grid gap-3 p-4 sm:grid-cols-[1fr_260px_auto]"
        >
          <select className={inputClass} name="missionId" required>
            {data.missions.map((mission) => (
              <option key={mission.id} value={mission.id}>
                {mission.title}
              </option>
            ))}
          </select>
          <select className={inputClass} name="type" required>
            <option value="EXECUTIVE_BRIEF">Executive brief</option>
            <option value="SOURCE_APPENDIX">Source appendix</option>
            <option value="COMPETITOR_MATRIX">Competitor matrix</option>
            <option value="EVIDENCE_CSV">Evidence CSV</option>
            <option value="JSON_PACKAGE">Structured JSON</option>
          </select>
          <button className={primaryButtonClass} type="submit">
            Generate
          </button>
        </form>
      </section>

      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <table className="w-full min-w-[780px] border-collapse text-left text-[11px]">
          <caption className="sr-only">
            Generated mission reports available for download
          </caption>
          <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
            <tr>
              <th className="px-4 py-2.5">Report</th>
              <th className="px-3 py-2.5">Mission</th>
              <th className="px-3 py-2.5">Type</th>
              <th className="px-3 py-2.5">Generated</th>
              <th className="px-3 py-2.5">Owner</th>
              <th className="px-3 py-2.5">State</th>
              <th className="px-3 py-2.5 text-right">Download</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--rule-subtle)]">
            {data.reports.map((report) => (
              <tr key={report.id}>
                <td className="px-4 py-3 font-semibold">{report.title}</td>
                <td className="px-3 py-3">{report.missionTitle}</td>
                <td className="px-3 py-3">{formatEnumLabel(report.type)}</td>
                <td className="px-3 py-3">
                  {formatDateTime(report.generatedAt)}
                </td>
                <td className="px-3 py-3">{report.generatedBy}</td>
                <td className="px-3 py-3">
                  <StatusBadge status={report.isDemo ? "DEMO" : "READY"} />
                </td>
                <td className="px-3 py-3 text-right">
                  <a
                    className={secondaryButtonClass}
                    href={`/api/reports/${report.id}`}
                  >
                    <ArrowDownToLine aria-hidden="true" className="size-3.5" />
                    Export
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

export function DatasetsWorkspace({
  data,
}: {
  data: Awaited<ReturnType<typeof getDatasetsWorkspace>>;
}) {
  return (
    <>
      <PageHeader
        description="Normalized, workspace-scoped records that power research, provenance inspection, exports, and grounded questions."
        eyebrow="Data catalog"
        title="Datasets"
      />
      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <table className="w-full min-w-[720px] border-collapse text-left text-[11px]">
          <caption className="sr-only">
            IntelBridge managed datasets and their current record counts
          </caption>
          <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
            <tr>
              <th className="px-4 py-2.5">Dataset</th>
              <th className="px-3 py-2.5">Purpose</th>
              <th className="px-3 py-2.5 text-right">Records</th>
              <th className="px-3 py-2.5">Updated</th>
              <th className="px-3 py-2.5">State</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--rule-subtle)]">
            {data.datasets.map((dataset) => (
              <tr key={dataset.id}>
                <td className="px-4 py-4">
                  <div className="flex items-center gap-2 font-semibold">
                    <Database
                      aria-hidden="true"
                      className="size-4 text-[var(--accent-strong)]"
                    />
                    {dataset.name}
                  </div>
                  <div className="mt-1 font-mono text-[9px] text-[var(--text-3)]">
                    {dataset.id}
                  </div>
                </td>
                <td className="max-w-xl px-3 py-4 leading-5 text-[var(--text-2)]">
                  {dataset.description}
                </td>
                <td className="px-3 py-4 text-right font-mono font-semibold">
                  {formatNumber(dataset.recordCount)}
                </td>
                <td className="px-3 py-4">
                  {dataset.updatedAt
                    ? formatDateTime(dataset.updatedAt)
                    : "Unavailable"}
                </td>
                <td className="px-3 py-4">
                  <StatusBadge status={dataset.state} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

export function AgentStudioWorkspace({
  data,
}: {
  data: Awaited<ReturnType<typeof getAgentStudioWorkspace>>;
}) {
  return (
    <>
      <PageHeader
        description="Inspectable agent responsibilities, prompt versions, structured outputs, and explicit allow-listed tools."
        eyebrow="Governed automation"
        title="Agent Studio"
      />
      <div className="grid gap-4 lg:grid-cols-2">
        {data.agents.map((agent) => (
          <article
            className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
            key={agent.id}
          >
            <div className="flex items-start gap-3 border-b border-[var(--rule)] p-4">
              <span className="grid size-9 place-items-center rounded-[3px] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                <Bot aria-hidden="true" className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="m-0 text-[13px] font-semibold">{agent.name}</h2>
                <div className="mt-1 text-[10px] uppercase text-[var(--text-3)]">
                  {formatEnumLabel(agent.agentType)}
                </div>
              </div>
              <StatusBadge status={agent.status} />
            </div>
            <div className="p-4">
              <p className="m-0 text-[11px] leading-5 text-[var(--text-2)]">
                {agent.purpose}
              </p>
              <dl className="m-0 mt-4 grid gap-2 text-[10px]">
                {[
                  ["Model", agent.model],
                  [
                    "Prompt",
                    `${agent.promptName} · version ${agent.promptVersion}`,
                  ],
                  ["Output schema", agent.outputSchema],
                  ["Updated", formatDateTime(agent.updatedAt)],
                ].map(([label, value]) => (
                  <div
                    className="grid grid-cols-[110px_1fr] gap-3 border-t border-[var(--rule-subtle)] pt-2"
                    key={label}
                  >
                    <dt className="text-[var(--text-3)]">{label}</dt>
                    <dd className="m-0 font-mono">{value}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-4">
                <div className="text-[10px] font-semibold uppercase text-[var(--text-3)]">
                  Allow-listed tools
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {agent.allowedTools.map((tool) => (
                    <code
                      className="rounded-[3px] border border-[var(--rule)] bg-[var(--surface-2)] px-2 py-1 text-[9px]"
                      key={tool}
                    >
                      {tool}
                    </code>
                  ))}
                </div>
              </div>
            </div>
          </article>
        ))}
      </div>
      <div className="mt-4 rounded-[3px] border border-[var(--status-info-border)] bg-[var(--status-info-fill)] p-3 text-[10px] leading-5 text-[var(--status-info-text)]">
        Model provider: deterministic mock. Set AI_PROVIDER=openai and provide
        server-side credentials to activate the live provider; no client bundle
        contains model credentials or arbitrary tool execution.
      </div>
    </>
  );
}

export function ProjectsWorkspace({
  data,
}: {
  data: Awaited<ReturnType<typeof getProjectsWorkspace>>;
}) {
  return (
    <>
      <PageHeader
        actions={
          <Link className={primaryButtonClass} href="/missions/new">
            New research mission
          </Link>
        }
        description="Workspace-scoped research programs with durable mission ownership and activity."
        eyebrow="Programs"
        title="Projects"
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {data.projects.map((project) => (
          <article
            className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-5"
            key={project.id}
          >
            <div className="flex items-start gap-3">
              <FolderKanban
                aria-hidden="true"
                className="size-5 text-[var(--accent-strong)]"
              />
              <div>
                <h2 className="m-0 text-[14px] font-semibold">
                  {project.name}
                </h2>
                <p className="mb-0 mt-2 text-[11px] leading-5 text-[var(--text-2)]">
                  {project.description}
                </p>
              </div>
            </div>
            <div className="mt-5 flex items-center justify-between border-t border-[var(--rule-subtle)] pt-3">
              <span className="text-[10px] text-[var(--text-3)]">
                {project._count.missions} missions · updated{" "}
                {formatDateTime(project.updatedAt)}
              </span>
              <Link
                className="text-[10px] font-semibold text-[var(--accent-strong)]"
                href={`/missions?project=${project.id}`}
              >
                Open missions
              </Link>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

export function DiagnosticsSummary({
  diagnostics,
}: {
  diagnostics: {
    activeRuns: number;
    evidenceCount: number;
    failedRuns: number;
    healthyConnectors: number;
    modelProvider: string;
    queueMode: string;
    sseStatus: string;
    unreadAlerts: number;
  };
}) {
  const metrics = [
    { icon: Activity, label: "Active runs", value: diagnostics.activeRuns },
    {
      icon: BookOpenText,
      label: "Evidence records",
      value: diagnostics.evidenceCount,
    },
    {
      icon: Link2,
      label: "Healthy connectors",
      value: diagnostics.healthyConnectors,
    },
    {
      icon: AlertTriangle,
      label: "Unread alerts",
      value: diagnostics.unreadAlerts,
    },
  ];

  return (
    <section className="grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric, index) => {
        const MetricIcon = metric.icon;
        return (
          <div
            className={`${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} p-4`}
            key={metric.label}
          >
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              <MetricIcon
                aria-hidden="true"
                className="size-3.5 text-[var(--accent-strong)]"
              />
              {metric.label}
            </div>
            <div className="mt-2 text-[22px] font-semibold">{metric.value}</div>
          </div>
        );
      })}
    </section>
  );
}

export function OperationalArchitectureNote() {
  return (
    <div className="flex items-start gap-3 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-2)] p-3 text-[10px] leading-5 text-[var(--text-3)]">
      <Braces
        aria-hidden="true"
        className="mt-0.5 size-4 shrink-0 text-[var(--accent-strong)]"
      />
      D1 is the authoritative relational store; R2 retains governed binary
      uploads; the run event ledger supports ordered SSE replay and refresh
      recovery. Every DEMO record carries status=demo and is_demo=true.
    </div>
  );
}
