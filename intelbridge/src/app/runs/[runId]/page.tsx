import {
  Activity,
  ArrowLeft,
  CircleStop,
  FileSearch,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { cancelResearchAction } from "@/app/actions";
import { PageHeader } from "@/components/page-header";
import { RunEventStream } from "@/components/run-event-stream";
import { StatusBadge } from "@/components/status-badge";
import { getRunWorkspace } from "@/server/services/intelligence";
import {
  formatDateTime,
  formatEnumLabel,
  formatPercent,
} from "@/shared/presentation";

type RunPageProps = {
  params: Promise<{ runId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function RunPage({ params, searchParams }: RunPageProps) {
  const [{ runId }, query] = await Promise.all([params, searchParams]);
  const result = await getRunWorkspace(runId);

  if (!result) {
    notFound();
  }

  const { missionTitle, run, steps } = result;
  const terminal = ["CANCELLED", "COMPLETED", "FAILED"].includes(run.status);
  const notice = typeof query.notice === "string" ? query.notice : undefined;

  return (
    <>
      <PageHeader
        actions={
          <>
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] font-semibold text-[var(--text-2)]"
              href={`/missions/${run.missionId}`}
            >
              <ArrowLeft aria-hidden="true" className="size-3.5" />
              Mission
            </Link>
            {run.status === "ACTIVE" ? (
              <form action={cancelResearchAction}>
                <input name="runId" type="hidden" value={run.id} />
                <button
                  className="inline-flex h-9 items-center gap-2 rounded-[3px] border border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] px-3 text-[11px] font-semibold text-[var(--status-negative-text)]"
                  type="submit"
                >
                  <CircleStop aria-hidden="true" className="size-3.5" />
                  Cancel run
                </button>
              </form>
            ) : null}
          </>
        }
        description={`${missionTitle} · ${formatEnumLabel(run.triggerType)} trigger · started ${formatDateTime(run.startedAt)}`}
        eyebrow={`Research run · ${run.id.slice(-12).toUpperCase()}`}
        title="Run activity"
      />
      {notice ? (
        <div className="mb-4 rounded-[3px] border border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] px-4 py-3 text-[11px] text-[var(--status-warning-text)]">
          Run cancelled. Completed step records remain available.
        </div>
      ) : null}

      <section className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 xl:grid-cols-6">
        {[
          ["Status", <StatusBadge key="status" status={run.status} />],
          ["Progress", `${run.progressPercent}%`],
          ["Sources", run.sourcesScanned],
          ["Documents", run.documentsProcessed],
          ["Evidence", run.evidenceCreated],
          [
            "Confidence",
            run.confidenceScore === null
              ? "--"
              : formatPercent(run.confidenceScore),
          ],
        ].map(([label, value], index) => (
          <div
            className={`${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} p-4`}
            key={label as string}
          >
            <div className="text-[10px] uppercase text-[var(--text-3)]">
              {label}
            </div>
            <div className="mt-2 text-[18px] font-semibold">{value}</div>
          </div>
        ))}
      </section>

      {run.errorSummary ? (
        <div className="mb-4 rounded-[3px] border border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] p-3 text-[10px] leading-5 text-[var(--status-warning-text)]">
          Processing limitation: {formatEnumLabel(run.errorSummary)}.
          Unsupported insights were withheld.
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(420px,0.7fr)]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Activity
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[13px] font-semibold">Agent steps</h2>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {steps.map((step) => (
              <article
                className="grid gap-3 p-4 sm:grid-cols-[40px_1fr_auto]"
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
                  <div className="mt-2 font-mono text-[9px] text-[var(--text-3)]">
                    {step.agentType} · {step.toolName} · {step.tokenUsage}{" "}
                    tokens
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[9px] text-[var(--text-3)]">
                  <Timer aria-hidden="true" className="size-3" />
                  {step.durationMs ? `${step.durationMs}ms` : "--"}
                </div>
              </article>
            ))}
          </div>
        </section>

        <RunEventStream runId={run.id} terminal={terminal} />
      </div>
      <div className="mt-4 text-[10px] leading-5 text-[var(--text-3)]">
        Provider {run.modelProvider} · prompt {run.promptVersion} · data state{" "}
        {run.dataStatus.toUpperCase()} · events are ordered and recoverable with
        Last-Event-ID.
      </div>
    </>
  );
}
