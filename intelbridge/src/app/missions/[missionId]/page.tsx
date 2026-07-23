import {
  BookOpenText,
  CalendarClock,
  CirclePause,
  FileSearch,
  Lightbulb,
  Play,
  RadioTower,
  ShieldCheck,
  Target,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getMissionDetailData } from "@/server/services/missions";
import { formatDateTime, formatEnumLabel } from "@/shared/presentation";

type MissionDetailPageProps = {
  params: Promise<{
    missionId: string;
  }>;
};

export async function generateMetadata({ params }: MissionDetailPageProps) {
  const { missionId } = await params;
  const result = await getMissionDetailData(missionId);

  return {
    title: result?.mission.title ?? "Mission",
  };
}

export default async function MissionDetailPage({
  params,
}: MissionDetailPageProps) {
  const { missionId } = await params;
  const result = await getMissionDetailData(missionId);

  if (!result) {
    notFound();
  }

  const { mission } = result;
  const shortId = mission.id.slice(-10).toUpperCase();
  const hasRuns = mission._count.researchRuns > 0;

  return (
    <>
      <PageHeader
        actions={
          <>
            <Link
              className="inline-flex h-9 items-center rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] font-semibold text-[var(--text-2)]"
              href="/missions"
            >
              All missions
            </Link>
            <button
              className="inline-flex h-9 cursor-not-allowed items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-3)] px-4 text-[11px] font-semibold text-[var(--text-3)]"
              disabled
              title="The durable research-run engine is delivered in Milestone 2"
              type="button"
            >
              <Play aria-hidden="true" className="size-4" />
              Run research
            </button>
          </>
        }
        description={`${mission.project.name} · owned by ${mission.createdBy.name} · updated ${formatDateTime(mission.updatedAt)}`}
        eyebrow={`Mission ${shortId}`}
        title={mission.title}
      />

      <section className="mb-4 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex flex-col gap-4 p-5 xl:flex-row xl:items-start">
          <div className="flex-1">
            <div className="mb-2 flex items-center gap-2">
              <Target
                aria-hidden="true"
                className="size-4 text-[var(--accent-strong)]"
              />
              <h2 className="m-0 text-[13px] font-semibold">
                Research objective
              </h2>
              <StatusBadge status={mission.status} />
            </div>
            <p className="mb-0 max-w-4xl text-[13px] leading-6 text-[var(--text-1)]">
              {mission.objective}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2 rounded-[3px] border border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] px-3 py-2 text-[10px] font-medium text-[var(--status-positive-text)]">
            <ShieldCheck aria-hidden="true" className="size-4" />
            Workspace scope enforced
          </div>
        </div>

        <dl className="grid border-t border-[var(--rule)] bg-[var(--surface-2)] sm:grid-cols-2 xl:grid-cols-4">
          <div className="border-b border-[var(--rule)] p-4 sm:border-r xl:border-b-0">
            <dt className="text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
              Research depth
            </dt>
            <dd className="m-0 mt-1.5 text-[12px] font-semibold">
              {formatEnumLabel(mission.researchDepth)}
            </dd>
          </div>
          <div className="border-b border-[var(--rule)] p-4 xl:border-b-0 xl:border-r">
            <dt className="text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
              Time horizon
            </dt>
            <dd className="m-0 mt-1.5 text-[12px] font-semibold">
              {mission.scope.timeHorizonMonths} months
            </dd>
          </div>
          <div className="border-b border-[var(--rule)] p-4 sm:border-r xl:border-b-0">
            <dt className="text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
              Monitoring
            </dt>
            <dd className="m-0 mt-1.5 text-[12px] font-semibold">
              {formatEnumLabel(mission.monitoringMode)}
            </dd>
          </div>
          <div className="p-4">
            <dt className="text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
              Focus areas
            </dt>
            <dd className="m-0 mt-1.5 text-[12px] font-semibold">
              {mission.scope.focusAreas.join(", ")}
            </dd>
          </div>
        </dl>
      </section>

      <section
        aria-label="Research metrics"
        className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 lg:grid-cols-4"
      >
        {[
          ["Sources selected", mission.sources.length.toString()],
          [
            "Research runs",
            hasRuns ? mission._count.researchRuns.toString() : "--",
          ],
          [
            "Evidence records",
            hasRuns ? mission._count.evidence.toString() : "--",
          ],
          ["Insights", hasRuns ? mission._count.insights.toString() : "--"],
        ].map(([label, value], index) => (
          <div
            className={`p-4 ${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} ${
              index === 2
                ? "sm:border-l-0 sm:border-t lg:border-l lg:border-t-0"
                : ""
            }`}
            key={label}
          >
            <div className="text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
              {label}
            </div>
            <div className="mt-1 text-[21px] font-semibold">{value}</div>
            <div className="mt-1 text-[10px] text-[var(--text-3)]">
              {label === "Sources selected"
                ? "Approved mission inputs"
                : hasRuns
                  ? "Persisted run output"
                  : "Unavailable until first run"}
            </div>
          </div>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
        <div className="grid gap-4">
          <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
            <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-3">
              <div className="flex items-center gap-2">
                <CalendarClock
                  aria-hidden="true"
                  className="size-4 text-[var(--accent-strong)]"
                />
                <h2 className="m-0 text-[13px] font-semibold">
                  Research progress
                </h2>
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-[0.05em] text-[var(--text-3)]">
                No active run
              </span>
            </div>
            <div className="grid min-h-44 place-items-center p-6 text-center">
              <div>
                <CirclePause
                  aria-hidden="true"
                  className="mx-auto size-6 text-[var(--text-3)]"
                />
                <div className="mt-3 text-[12px] font-semibold">
                  Research has not started
                </div>
                <p className="mb-0 mt-1 max-w-md text-[11px] leading-5 text-[var(--text-3)]">
                  The mission, source policy, and ownership record are
                  persisted. Live steps, cancellation, and reconnectable
                  progress arrive with the Milestone 2 run engine.
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
            <div className="border-b border-[var(--rule)] px-4 py-3">
              <h2 className="m-0 text-[13px] font-semibold">
                Scope and accountability
              </h2>
            </div>
            <dl className="grid sm:grid-cols-2">
              <div className="border-b border-[var(--rule)] p-4 sm:border-r">
                <dt className="text-[10px] uppercase text-[var(--text-3)]">
                  Regions
                </dt>
                <dd className="m-0 mt-1.5 text-[11px]">
                  {mission.scope.regions.join(", ")}
                </dd>
              </div>
              <div className="border-b border-[var(--rule)] p-4">
                <dt className="text-[10px] uppercase text-[var(--text-3)]">
                  Accountable owner
                </dt>
                <dd className="m-0 mt-1.5 text-[11px]">
                  {mission.createdBy.name}
                </dd>
              </div>
              <div className="p-4 sm:border-r">
                <dt className="text-[10px] uppercase text-[var(--text-3)]">
                  Created
                </dt>
                <dd className="m-0 mt-1.5 text-[11px]">
                  {formatDateTime(mission.createdAt)}
                </dd>
              </div>
              <div className="p-4">
                <dt className="text-[10px] uppercase text-[var(--text-3)]">
                  Project
                </dt>
                <dd className="m-0 mt-1.5 text-[11px]">
                  {mission.project.name}
                </dd>
              </div>
            </dl>
          </section>
        </div>

        <div className="grid content-start gap-4">
          <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
            <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
              <BookOpenText
                aria-hidden="true"
                className="size-4 text-[var(--accent-strong)]"
              />
              <h2 className="m-0 text-[13px] font-semibold">
                Selected connectors
              </h2>
            </div>
            <ul className="m-0 list-none divide-y divide-[var(--rule-subtle)] p-0">
              {mission.sources.map(({ sourceConnector }) => (
                <li
                  className="flex items-center gap-3 px-4 py-3"
                  key={sourceConnector.id}
                >
                  <span className="grid size-8 place-items-center rounded-[3px] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                    <RadioTower aria-hidden="true" className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[11px] font-semibold">
                      {sourceConnector.name}
                    </div>
                    <div className="mt-1 text-[10px] text-[var(--text-3)]">
                      {formatEnumLabel(sourceConnector.type)}
                    </div>
                  </div>
                  <StatusBadge status={sourceConnector.status} />
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
            <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
              <Lightbulb
                aria-hidden="true"
                className="size-4 text-[var(--accent-strong)]"
              />
              <h2 className="m-0 text-[13px] font-semibold">Ask IntelBridge</h2>
            </div>
            <div className="p-4">
              <div className="flex h-10 items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-2)] px-3">
                <FileSearch
                  aria-hidden="true"
                  className="size-4 text-[var(--text-3)]"
                />
                <input
                  aria-label="Ask IntelBridge unavailable until evidence exists"
                  className="min-w-0 flex-1 bg-transparent text-[11px] outline-none placeholder:text-[var(--text-3)]"
                  disabled
                  placeholder="Ask a question about this mission"
                  title="Evidence-grounded questions arrive in Milestone 6"
                />
              </div>
              <p className="mb-0 mt-2 text-[10px] leading-4 text-[var(--text-3)]">
                Disabled until persisted evidence and citation validation are
                available.
              </p>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
