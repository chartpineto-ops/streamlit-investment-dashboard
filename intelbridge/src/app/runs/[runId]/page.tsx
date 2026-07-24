import {
  ArrowLeft,
  CircleStop,
  FileSearch,
  RotateCcw,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { cancelResearchAction, retryResearchAction } from "@/app/actions";
import { PageHeader } from "@/components/page-header";
import { RunEventStream } from "@/components/run-event-stream";
import { StatusBadge } from "@/components/status-badge";
import { getRunForCurrentWorkspace } from "@/server/services/runs";
import { formatDateTime, formatEnumLabel } from "@/shared/presentation";

export default async function RunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const result = await getRunForCurrentWorkspace(runId);
  if (!result) notFound();
  const { events, run, steps } = result;
  const terminal = [
    "CANCELLED",
    "COMPLETED",
    "FAILED",
    "PARTIALLY_COMPLETED",
  ].includes(run.status);
  const retryable = ["CANCELLED", "FAILED", "PARTIALLY_COMPLETED"].includes(
    run.status,
  );

  return (
    <>
      <PageHeader
        actions={
          <>
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-[3px] border border-[var(--rule)] px-3 text-[11px] font-semibold"
              href={`/missions/${run.missionId}`}
            >
              <ArrowLeft aria-hidden="true" className="size-3.5" />
              Mission
            </Link>
            {!terminal ? (
              <form action={cancelResearchAction}>
                <input name="runId" type="hidden" value={run.id} />
                <button
                  className="inline-flex h-9 items-center gap-2 rounded-[3px] border border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] px-3 text-[11px] font-semibold text-[var(--status-negative-text)]"
                  type="submit"
                >
                  <CircleStop aria-hidden="true" className="size-3.5" />
                  Cancel
                </button>
              </form>
            ) : null}
            {retryable ? (
              <form action={retryResearchAction}>
                <input name="runId" type="hidden" value={run.id} />
                <button
                  className="inline-flex h-9 items-center gap-2 rounded-[3px] bg-[var(--accent)] px-3 text-[11px] font-semibold text-[var(--accent-contrast)]"
                  type="submit"
                >
                  <RotateCcw aria-hidden="true" className="size-3.5" />
                  Retry
                </button>
              </form>
            ) : null}
          </>
        }
        description={`${run.missionTitle} · ${formatEnumLabel(run.triggerType)} · started ${formatDateTime(new Date(run.startedAt))}`}
        eyebrow={`Run · ${run.id.slice(-12).toUpperCase()}`}
        title="Run activity"
      />

      <section className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 xl:grid-cols-7">
        {[
          ["Status", <StatusBadge key="status" status={run.status} />],
          ["Progress", `${run.progressPercent}%`],
          ["Sources", run.sourcesScanned],
          ["Discovered", run.documentsDiscovered],
          ["Created", run.documentsCreated],
          ["Updated", run.documentsUpdated],
          ["Unchanged", run.documentsUnchanged],
        ].map(([label, value], index) => (
          <div
            className={`${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} p-4`}
            key={label as string}
          >
            <div className="text-[9px] uppercase text-[var(--text-3)]">
              {label}
            </div>
            <div className="mt-2 text-[17px] font-semibold">{value}</div>
          </div>
        ))}
      </section>

      {run.errorSummary ? (
        <div className="mb-4 border border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] px-4 py-3 text-[11px] text-[var(--status-warning-text)]">
          {formatEnumLabel(run.errorSummary)}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.75fr)]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="border-b border-[var(--rule)] px-4 py-3">
            <h2 className="m-0 text-[13px] font-semibold">Ingestion steps</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {steps.map((step) => (
              <article
                className="grid gap-3 p-4 sm:grid-cols-[36px_1fr_auto]"
                key={step.id}
              >
                <span className="grid size-8 place-items-center rounded-[3px] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                  <FileSearch aria-hidden="true" className="size-4" />
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="m-0 text-[11px] font-semibold">
                      {step.sequenceNumber}. {step.name}
                    </h3>
                    <StatusBadge status={step.status} />
                  </div>
                  <p className="mb-0 mt-1 text-[10px] leading-5 text-[var(--text-2)]">
                    {step.outputSummary ?? step.inputSummary}
                  </p>
                  {step.errorCode ? (
                    <div className="mt-1 text-[9px] text-[var(--status-negative-text)]">
                      {formatEnumLabel(step.errorCode)}
                    </div>
                  ) : null}
                </div>
                <div className="flex items-center gap-1 text-[9px] text-[var(--text-3)]">
                  <Timer aria-hidden="true" className="size-3" />
                  {step.durationMs === null ? "--" : `${step.durationMs} ms`}
                </div>
              </article>
            ))}
          </div>
        </section>

        <RunEventStream
          initialEvents={events ?? []}
          runId={run.id}
          terminal={terminal}
        />
      </div>
      <div className="mt-4 text-[10px] text-[var(--text-3)]">
        Data state {run.dataStatus.toUpperCase()} · durable events resume from
        Last-Event-ID · completed work is preserved on cancellation.
      </div>
    </>
  );
}
