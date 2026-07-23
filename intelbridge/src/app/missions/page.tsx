import { MissionStatus } from "@prisma/client";
import { Plus } from "lucide-react";
import Link from "next/link";

import { MissionTable } from "@/components/mission-table";
import { PageHeader } from "@/components/page-header";
import { getMissionListData } from "@/server/services/missions";
import { formatEnumLabel } from "@/shared/presentation";

export const metadata = {
  title: "Missions",
};

type MissionsPageProps = {
  searchParams: Promise<{
    project?: string;
    status?: string;
  }>;
};

export default async function MissionsPage({
  searchParams,
}: MissionsPageProps) {
  const filters = await searchParams;
  const status = Object.values(MissionStatus).includes(
    filters.status as MissionStatus,
  )
    ? (filters.status as MissionStatus)
    : undefined;
  const { missions, projects } = await getMissionListData({
    projectId: filters.project,
    status,
  });

  return (
    <>
      <PageHeader
        actions={
          <Link
            className="inline-flex min-h-9 items-center gap-2 rounded-[4px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)] hover:bg-[var(--accent-hover)]"
            href="/missions/new"
          >
            <Plus aria-hidden="true" className="size-4" />
            New research
          </Link>
        }
        description="Define accountable research objectives, approved sources, scope, depth, and monitoring policy before collection begins."
        eyebrow="Research registry"
        title="Missions"
      />

      <form
        action="/missions"
        className="mb-3 flex flex-wrap items-end gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-3"
        method="get"
      >
        <label className="grid gap-1 text-[10px] font-semibold uppercase tracking-[0.04em] text-[var(--text-3)]">
          Project
          <select
            className="h-9 min-w-[220px] rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] font-normal normal-case tracking-normal text-[var(--text-1)]"
            defaultValue={filters.project ?? ""}
            name="project"
          >
            <option value="">All projects</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1 text-[10px] font-semibold uppercase tracking-[0.04em] text-[var(--text-3)]">
          Status
          <select
            className="h-9 min-w-[160px] rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] font-normal normal-case tracking-normal text-[var(--text-1)]"
            defaultValue={status ?? ""}
            name="status"
          >
            <option value="">All statuses</option>
            {Object.values(MissionStatus).map((value) => (
              <option key={value} value={value}>
                {formatEnumLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <button
          className="h-9 rounded-[3px] border border-[var(--accent)] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)]"
          type="submit"
        >
          Apply filters
        </button>
        {filters.project || status ? (
          <Link
            className="inline-flex h-9 items-center px-3 text-[11px] font-semibold text-[var(--accent-strong)]"
            href="/missions"
          >
            Clear
          </Link>
        ) : null}
      </form>

      <MissionTable missions={missions} />
    </>
  );
}
