import {
  ArrowRight,
  BookOpenText,
  Folder,
  ListChecks,
  Radio,
} from "lucide-react";
import Link from "next/link";

import { MissionTable } from "@/components/mission-table";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getHomeData } from "@/server/services/missions";
import { formatDateTime } from "@/shared/presentation";

export const metadata = { title: "Research Operations" };

export default async function HomePage() {
  const home = await getHomeData();
  const metrics = [
    ["Active projects", home.summary.projectCount, Folder],
    ["Active missions", home.summary.activeMissionCount, ListChecks],
    ["Connected sources", home.summary.availableConnectorCount, BookOpenText],
    ["Recent runs", home.summary.runCount, Radio],
    ["Ingested documents", home.summary.documentCount, BookOpenText],
  ] as const;

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
        description={`Durable project, mission, connector, ingestion-run, and source-document operations for ${home.context.workspace.name}.`}
        eyebrow="Workspace overview"
        title="Research operations"
      />

      <section className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 xl:grid-cols-5">
        {metrics.map(([label, value, Icon], index) => (
          <div
            className={`${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} p-4`}
            key={label}
          >
            <div className="flex items-center gap-2 text-[10px] uppercase text-[var(--text-3)]">
              <Icon aria-hidden="true" className="size-3.5" />
              {label}
            </div>
            <div className="mt-2 text-[22px] font-semibold">{value}</div>
          </div>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <section>
          <div className="mb-2 flex items-end justify-between">
            <div>
              <h2 className="m-0 text-[13px] font-semibold">
                Recently updated missions
              </h2>
              <p className="mb-0 mt-1 text-[10px] text-[var(--text-3)]">
                Objectives and source assignments are persisted by workspace.
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
            <h2 className="m-0 text-[13px] font-semibold">Recent runs</h2>
            <Link
              className="text-[10px] font-semibold text-[var(--accent-strong)]"
              href="/runs"
            >
              View all
            </Link>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {home.runs.length ? (
              home.runs.map((run) => (
                <Link
                  className="grid grid-cols-[1fr_auto] gap-2 px-4 py-3 hover:bg-[var(--row-hover)]"
                  href={`/runs/${run.id}`}
                  key={run.id}
                >
                  <div>
                    <div className="text-[11px] font-semibold">
                      {run.missionTitle}
                    </div>
                    <div className="mt-1 text-[9px] text-[var(--text-3)]">
                      {run.documentsProcessed} documents ·{" "}
                      {formatDateTime(new Date(run.startedAt))}
                    </div>
                  </div>
                  <StatusBadge status={run.status} />
                </Link>
              ))
            ) : (
              <div className="px-4 py-10 text-center text-[11px] text-[var(--text-3)]">
                No runs have been queued.
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  );
}
