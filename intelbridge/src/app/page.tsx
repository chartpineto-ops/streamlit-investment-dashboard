import {
  ArrowRight,
  BookOpenText,
  FolderKanban,
  ListChecks,
  PlugZap,
} from "lucide-react";
import Link from "next/link";

import { MissionTable } from "@/components/mission-table";
import { PageHeader } from "@/components/page-header";
import { getHomeData } from "@/server/services/missions";

export const metadata = {
  title: "Research Operations",
};

export default async function HomePage() {
  const { context, missions, summary } = await getHomeData();

  const metrics = [
    {
      detail: `${summary.activeMissionCount} ready or active`,
      icon: ListChecks,
      label: "Research missions",
      value: summary.missionCount,
    },
    {
      detail: "Authenticated workspace",
      icon: FolderKanban,
      label: "Active projects",
      value: summary.projectCount,
    },
    {
      detail: `${summary.connectorCount - summary.availableConnectorCount} not connected`,
      icon: PlugZap,
      label: "Available connectors",
      value: summary.availableConnectorCount,
    },
    {
      detail: "Deterministic demo source",
      icon: BookOpenText,
      label: "Data mode",
      value: "DEMO",
    },
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
        description={`Persistent mission records and source configuration for ${context.workspace.name}. Research execution is deliberately withheld until the Milestone 2 run engine is available.`}
        eyebrow="Workspace overview"
        title="Research operations"
      />

      <section
        aria-label="Workspace summary"
        className="mb-5 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 xl:grid-cols-4"
      >
        {metrics.map((metric, index) => {
          const Icon = metric.icon;

          return (
            <div
              className={`flex min-h-24 items-start gap-3 p-4 ${
                index
                  ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0"
                  : ""
              } ${index === 2 ? "sm:border-l-0 sm:border-t xl:border-l xl:border-t-0" : ""}`}
              key={metric.label}
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-[4px] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                <Icon aria-hidden="true" className="size-4" />
              </span>
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-[0.05em] text-[var(--text-3)]">
                  {metric.label}
                </div>
                <div className="mt-1 text-[22px] font-semibold">
                  {metric.value}
                </div>
                <div className="mt-1 text-[10px] text-[var(--text-3)]">
                  {metric.detail}
                </div>
              </div>
            </div>
          );
        })}
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <div>
            <h2 className="m-0 text-[13px] font-semibold">
              Recently updated missions
            </h2>
            <p className="mb-0 mt-1 text-[10px] text-[var(--text-3)]">
              Values below are read from persistent D1 storage and scoped to the
              authenticated workspace.
            </p>
          </div>
          <Link
            className="text-[11px] font-semibold text-[var(--accent-strong)]"
            href="/missions"
          >
            View all
          </Link>
        </div>
        <MissionTable missions={missions} />
      </section>
    </>
  );
}
