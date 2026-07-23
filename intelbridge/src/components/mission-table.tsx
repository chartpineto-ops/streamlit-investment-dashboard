import { ArrowRight, Database, RadioTower } from "lucide-react";
import Link from "next/link";

import type {
  MissionStatus,
  MonitoringMode,
  ResearchDepth,
} from "@/shared/domain";
import { formatDateTime, formatEnumLabel } from "@/shared/presentation";
import { StatusBadge } from "./status-badge";

type MissionRow = {
  _count: {
    insights: number;
    researchRuns: number;
  };
  createdBy: {
    name: string;
  };
  id: string;
  monitoringMode: MonitoringMode;
  objective: string;
  project: {
    name: string;
  };
  researchDepth: ResearchDepth;
  sources: {
    sourceConnector: {
      name: string;
    };
  }[];
  status: MissionStatus;
  title: string;
  updatedAt: Date;
};

export function MissionTable({ missions }: { missions: MissionRow[] }) {
  return (
    <div className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[920px] border-collapse text-left">
          <caption className="sr-only">
            Research missions available in the authenticated workspace
          </caption>
          <thead className="bg-[var(--surface-2)] text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
            <tr>
              <th
                className="border-b border-[var(--rule)] px-4 py-3 font-semibold"
                scope="col"
              >
                Mission
              </th>
              <th
                className="border-b border-[var(--rule)] px-3 py-3 font-semibold"
                scope="col"
              >
                Project
              </th>
              <th
                className="border-b border-[var(--rule)] px-3 py-3 font-semibold"
                scope="col"
              >
                Status
              </th>
              <th
                className="border-b border-[var(--rule)] px-3 py-3 font-semibold"
                scope="col"
              >
                Research policy
              </th>
              <th
                className="border-b border-[var(--rule)] px-3 py-3 font-semibold"
                scope="col"
              >
                Records
              </th>
              <th
                className="border-b border-[var(--rule)] px-3 py-3 font-semibold"
                scope="col"
              >
                Updated
              </th>
              <th
                className="border-b border-[var(--rule)] px-3 py-3 text-right font-semibold"
                scope="col"
              >
                Open
              </th>
            </tr>
          </thead>
          <tbody>
            {missions.length ? (
              missions.map((mission) => (
                <tr
                  className="border-b border-[var(--rule-subtle)] last:border-b-0 hover:bg-[var(--row-hover)]"
                  key={mission.id}
                >
                  <td className="max-w-[360px] px-4 py-3 align-top">
                    <Link
                      className="font-semibold text-[var(--text-1)] hover:text-[var(--accent-strong)]"
                      href={`/missions/${mission.id}`}
                    >
                      {mission.title}
                    </Link>
                    <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-[var(--text-3)]">
                      {mission.objective}
                    </div>
                    <div className="mt-2 text-[10px] text-[var(--text-3)]">
                      Owner: {mission.createdBy.name}
                    </div>
                  </td>
                  <td className="px-3 py-3 align-top text-[11px] text-[var(--text-2)]">
                    {mission.project.name}
                  </td>
                  <td className="px-3 py-3 align-top">
                    <StatusBadge status={mission.status} />
                  </td>
                  <td className="px-3 py-3 align-top text-[11px] text-[var(--text-2)]">
                    <div>{formatEnumLabel(mission.researchDepth)}</div>
                    <div className="mt-1 flex items-center gap-1 text-[var(--text-3)]">
                      <RadioTower aria-hidden="true" className="size-3" />
                      {formatEnumLabel(mission.monitoringMode)}
                    </div>
                  </td>
                  <td className="px-3 py-3 align-top text-[11px] text-[var(--text-2)]">
                    <div className="flex items-center gap-1">
                      <Database
                        aria-hidden="true"
                        className="size-3 text-[var(--text-3)]"
                      />
                      {mission.sources.length} source
                      {mission.sources.length === 1 ? "" : "s"}
                    </div>
                    <div className="mt-1 text-[var(--text-3)]">
                      {mission._count.researchRuns
                        ? `${mission._count.researchRuns} run${mission._count.researchRuns === 1 ? "" : "s"}`
                        : "No runs"}
                    </div>
                  </td>
                  <td className="px-3 py-3 align-top text-[10px] leading-4 text-[var(--text-3)]">
                    {formatDateTime(mission.updatedAt)}
                  </td>
                  <td className="px-3 py-3 text-right align-top">
                    <Link
                      aria-label={`Open ${mission.title}`}
                      className="inline-grid size-8 place-items-center rounded-[3px] border border-[var(--rule)] text-[var(--text-2)] hover:border-[var(--accent)] hover:text-[var(--accent-strong)]"
                      href={`/missions/${mission.id}`}
                    >
                      <ArrowRight aria-hidden="true" className="size-4" />
                    </Link>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-12 text-center" colSpan={7}>
                  <div className="font-medium">
                    No missions match this view.
                  </div>
                  <p className="mb-0 mt-1 text-[11px] text-[var(--text-3)]">
                    Change the project filter or create a new research mission.
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
