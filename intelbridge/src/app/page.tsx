import {
  Activity,
  ArrowRight,
  BookOpenText,
  FileSearch,
  Lightbulb,
  RadioTower,
} from "lucide-react";
import Link from "next/link";

import {
  DiagnosticsSummary,
  OperationalArchitectureNote,
} from "@/components/intelligence-workspaces";
import { MissionTable } from "@/components/mission-table";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getIntelligenceOverview } from "@/server/services/intelligence";
import { getHomeData } from "@/server/services/missions";
import { formatDateTime, formatPercent } from "@/shared/presentation";

export const metadata = {
  title: "Research Operations",
};

export default async function HomePage() {
  const [home, intelligence] = await Promise.all([
    getHomeData(),
    getIntelligenceOverview(),
  ]);

  return (
    <>
      <PageHeader
        actions={
          <Link
            className="inline-flex min-h-9 items-center gap-2 rounded-[4px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)] hover:bg-[var(--accent-hover)]"
            href="/missions/new"
          >
            New research mission
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        }
        description={`Persistent intelligence operations for ${home.context.workspace.name}. Research runs, evidence, insights, monitors, reports, and audit records remain workspace scoped.`}
        eyebrow="Workspace overview · DEMO corpus"
        title="Research operations"
      />

      <div className="mb-4">
        <DiagnosticsSummary diagnostics={intelligence.diagnostics} />
      </div>

      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
        <section>
          <div className="mb-2 flex items-end justify-between">
            <div>
              <h2 className="m-0 text-[13px] font-semibold">
                Recently updated missions
              </h2>
              <p className="mb-0 mt-1 text-[10px] text-[var(--text-3)]">
                Durable objectives, source policies, run counts, and output
                counts.
              </p>
            </div>
            <Link
              className="text-[10px] font-semibold text-[var(--accent-strong)]"
              href="/missions"
            >
              View all
            </Link>
          </div>
          <MissionTable missions={home.missions} />
        </section>

        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-3">
            <div className="flex items-center gap-2">
              <Lightbulb
                aria-hidden="true"
                className="size-4 text-[var(--accent-strong)]"
              />
              <h2 className="m-0 text-[13px] font-semibold">Key insights</h2>
            </div>
            <Link
              className="text-[10px] font-semibold text-[var(--accent-strong)]"
              href="/insights"
            >
              View all
            </Link>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {intelligence.insights.map((insight) => (
              <Link
                className="block p-4 hover:bg-[var(--row-hover)]"
                href={`/insights?selected=${insight.id}`}
                key={insight.id}
              >
                <div className="flex items-center gap-2">
                  <StatusBadge status={insight.category} />
                  <span className="ml-auto font-mono text-[9px] text-[var(--text-3)]">
                    {formatPercent(insight.confidenceScore)}
                  </span>
                </div>
                <div className="mt-2 text-[12px] font-semibold">
                  {insight.title}
                </div>
                <p className="mb-0 mt-1 line-clamp-2 text-[10px] leading-4 text-[var(--text-2)]">
                  {insight.summary}
                </p>
              </Link>
            ))}
          </div>
        </section>
      </div>

      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <BookOpenText
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[12px] font-semibold">Recent sources</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {intelligence.sources.map((source) => (
              <Link
                className="block px-4 py-3 hover:bg-[var(--row-hover)]"
                href={`/sources?q=${encodeURIComponent(source.publisher)}`}
                key={source.id}
              >
                <div className="truncate text-[11px] font-semibold">
                  {source.title}
                </div>
                <div className="mt-1 text-[9px] text-[var(--text-3)]">
                  {source.publisher} · {source.evidenceCount} evidence ·{" "}
                  {formatDateTime(source.retrievedAt)}
                </div>
              </Link>
            ))}
          </div>
        </section>

        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <RadioTower
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[12px] font-semibold">Monitor health</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {intelligence.monitors.map((monitor) => (
              <Link
                className="flex items-center gap-3 px-4 py-3 hover:bg-[var(--row-hover)]"
                href="/monitoring"
                key={monitor.id}
              >
                <span className="grid size-7 place-items-center rounded-[3px] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                  <Activity aria-hidden="true" className="size-3.5" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[11px] font-semibold">
                    {monitor.missionTitle}
                  </div>
                  <div className="mt-1 text-[9px] text-[var(--text-3)]">
                    {monitor.schedule} · threshold{" "}
                    {formatPercent(monitor.materialityThreshold)}
                  </div>
                </div>
                <StatusBadge status={monitor.status} />
              </Link>
            ))}
          </div>
        </section>

        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <FileSearch
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[12px] font-semibold">
              Evidence operations
            </h2>
          </div>
          <div className="grid gap-3 p-4">
            <Link
              className="rounded-[3px] border border-[var(--rule)] p-3 hover:bg-[var(--surface-2)]"
              href="/evidence"
            >
              <div className="text-[11px] font-semibold">
                Search evidence ledger
              </div>
              <div className="mt-1 text-[9px] leading-4 text-[var(--text-3)]">
                Inspect excerpts, claims, contradictions, source metadata, and
                quality.
              </div>
            </Link>
            <Link
              className="rounded-[3px] border border-[var(--rule)] p-3 hover:bg-[var(--surface-2)]"
              href="/reports"
            >
              <div className="text-[11px] font-semibold">
                Generate decision package
              </div>
              <div className="mt-1 text-[9px] leading-4 text-[var(--text-3)]">
                Export an executive brief, evidence CSV, or structured JSON.
              </div>
            </Link>
          </div>
        </section>
      </div>

      <OperationalArchitectureNote />
    </>
  );
}
