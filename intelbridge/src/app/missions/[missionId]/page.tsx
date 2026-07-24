import { Cable, Pencil, Play, Radio } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import {
  assignMissionSourceAction,
  startResearchAction,
  updateMissionAction,
} from "@/app/actions";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getSourcesWorkspaceData } from "@/server/services/foundation";
import { getMissionDetailData } from "@/server/services/missions";
import { listRunsForCurrentWorkspace } from "@/server/services/runs";
import { formatDateTime, formatEnumLabel } from "@/shared/presentation";

const inputClass =
  "h-9 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] outline-none focus:border-[var(--accent)]";

export default async function MissionDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ missionId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ missionId }, query] = await Promise.all([params, searchParams]);
  const [result, sourceData, runs] = await Promise.all([
    getMissionDetailData(missionId),
    getSourcesWorkspaceData(),
    listRunsForCurrentWorkspace(missionId),
  ]);
  if (!result) notFound();
  const { mission } = result;
  const canRun = ["READY", "COMPLETED", "FAILED"].includes(mission.status);
  const notice = typeof query.notice === "string" ? query.notice : undefined;

  return (
    <>
      <PageHeader
        actions={
          canRun ? (
            <form action={startResearchAction}>
              <input name="missionId" type="hidden" value={mission.id} />
              <input
                name="idempotencyKey"
                type="hidden"
                value={`manual:${mission.id}:${crypto.randomUUID()}`}
              />
              <button
                className="inline-flex h-9 items-center gap-2 rounded-[3px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)]"
                type="submit"
              >
                <Play aria-hidden="true" className="size-3.5" />
                Run research
              </button>
            </form>
          ) : null
        }
        description={`${mission.project.name} · owned by ${mission.createdBy.name} · updated ${formatDateTime(mission.updatedAt)}`}
        eyebrow={`Mission · ${mission.id.slice(-12).toUpperCase()}`}
        title={mission.title}
      />
      {notice ? (
        <div
          className="mb-4 border border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] px-4 py-3 text-[11px] text-[var(--status-positive-text)]"
          role="status"
        >
          {formatEnumLabel(notice)}
        </div>
      ) : null}

      <section className="mb-4 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex items-start justify-between gap-4 border-b border-[var(--rule)] p-5">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <h2 className="m-0 text-[13px] font-semibold">
                Research objective
              </h2>
              <StatusBadge status={mission.status} />
            </div>
            <p className="m-0 max-w-5xl text-[13px] leading-6">
              {mission.objective}
            </p>
          </div>
        </div>
        <dl className="grid bg-[var(--surface-2)] sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Project", mission.project.name],
            ["Depth", formatEnumLabel(mission.researchDepth)],
            ["Time horizon", `${mission.scope.timeHorizonMonths} months`],
            ["Regions", mission.scope.regions.join(", ")],
            ["Focus areas", mission.scope.focusAreas.join(", ")],
            ["Sources", mission.sources.length],
            ["Runs", runs.length],
            ["Status", formatEnumLabel(mission.status)],
          ].map(([label, value]) => (
            <div
              className="border-b border-[var(--rule-subtle)] px-4 py-3 even:sm:border-l"
              key={label}
            >
              <dt className="text-[9px] uppercase text-[var(--text-3)]">
                {label}
              </dt>
              <dd className="m-0 mt-1 text-[11px] font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Cable aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">Assigned sources</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {mission.sources.length ? (
              mission.sources.map(({ sourceConnector }) => (
                <div
                  className="flex items-center gap-3 px-4 py-3"
                  key={sourceConnector.id}
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-[11px] font-semibold">
                      {sourceConnector.name}
                    </div>
                    <div className="mt-1 text-[9px] text-[var(--text-3)]">
                      {formatEnumLabel(sourceConnector.type)}
                    </div>
                  </div>
                  <StatusBadge status={sourceConnector.status} />
                </div>
              ))
            ) : (
              <div className="px-4 py-10 text-center text-[11px] text-[var(--text-3)]">
                No sources are assigned.
              </div>
            )}
          </div>
        </section>

        <form
          action={assignMissionSourceAction}
          className="h-fit rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
        >
          <div className="border-b border-[var(--rule)] px-4 py-3 text-[12px] font-semibold">
            Assign source
          </div>
          <div className="grid gap-3 p-4">
            <input name="missionId" type="hidden" value={mission.id} />
            <select className={inputClass} name="connectorId" required>
              <option value="">Select a connector</option>
              {sourceData.connectors.map((connector) => (
                <option key={connector.id} value={connector.id}>
                  {connector.name} · {formatEnumLabel(connector.status)}
                </option>
              ))}
            </select>
            <input
              className={inputClass}
              name="inclusionRules"
              placeholder="Include terms, comma separated"
            />
            <input
              className={inputClass}
              name="exclusionRules"
              placeholder="Exclude terms, comma separated"
            />
            <input
              className={inputClass}
              defaultValue="50"
              max="100"
              min="1"
              name="priority"
              type="number"
            />
            <button
              className="h-9 rounded-[3px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)]"
              type="submit"
            >
              Assign source
            </button>
          </div>
        </form>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Radio aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">Recent runs</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {runs.length ? (
              runs.slice(0, 10).map((run) => (
                <Link
                  className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3 hover:bg-[var(--surface-2)]"
                  href={`/runs/${run.id}`}
                  key={run.id}
                >
                  <div>
                    <div className="font-mono text-[10px]">{run.id}</div>
                    <div className="mt-1 text-[9px] text-[var(--text-3)]">
                      {run.documentsProcessed} documents · {run.progressPercent}
                      %
                    </div>
                  </div>
                  <StatusBadge status={run.status} />
                </Link>
              ))
            ) : (
              <div className="px-4 py-10 text-center text-[11px] text-[var(--text-3)]">
                This mission has not run.
              </div>
            )}
          </div>
        </section>

        <form
          action={updateMissionAction}
          className="h-fit rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
        >
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Pencil aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">Edit mission</h2>
          </div>
          <div className="grid gap-3 p-4">
            <input name="missionId" type="hidden" value={mission.id} />
            <input
              className={inputClass}
              defaultValue={mission.title}
              name="title"
              required
            />
            <textarea
              className="min-h-28 rounded-[3px] border border-[var(--rule)] p-3 text-[11px]"
              defaultValue={mission.objective}
              name="objective"
              required
            />
            <input
              className={inputClass}
              defaultValue={mission.scope.focusAreas.join(", ")}
              name="focusAreas"
              required
            />
            <input
              className={inputClass}
              defaultValue={mission.scope.regions.join(", ")}
              name="regions"
              required
            />
            <input
              className={inputClass}
              defaultValue={mission.scope.timeHorizonMonths}
              max="60"
              min="1"
              name="timeHorizonMonths"
              type="number"
            />
            <select
              className={inputClass}
              defaultValue={mission.researchDepth}
              name="researchDepth"
            >
              <option value="RAPID">Rapid</option>
              <option value="STANDARD">Standard</option>
              <option value="DEEP">Deep</option>
            </select>
            <select
              className={inputClass}
              defaultValue={mission.status}
              name="status"
            >
              {!["DRAFT", "READY", "ARCHIVED"].includes(mission.status) ? (
                <option value={mission.status}>
                  {formatEnumLabel(mission.status)}
                </option>
              ) : null}
              <option value="DRAFT">Draft</option>
              <option value="READY">Ready</option>
              <option value="ARCHIVED">Archived</option>
            </select>
            <button
              className="h-9 rounded-[3px] bg-[var(--accent)] px-4 text-[11px] font-semibold text-[var(--accent-contrast)]"
              type="submit"
            >
              Save mission
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
