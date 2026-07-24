import {
  Activity,
  ArrowDownToLine,
  BookOpenText,
  Check,
  Circle,
  FileSearch,
  Lightbulb,
  Play,
  RadioTower,
  ShieldCheck,
  Target,
} from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { startResearchAction } from "@/app/actions";
import { AskPanel } from "@/components/ask-panel";
import { PageHeader } from "@/components/page-header";
import { ShareButton } from "@/components/share-button";
import { StatusBadge } from "@/components/status-badge";
import { getMissionDetailData } from "@/server/services/missions";
import { getMissionWorkspace } from "@/server/services/intelligence";
import {
  formatDateTime,
  formatEnumLabel,
  formatPercent,
} from "@/shared/presentation";

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
  const [result, intelligence] = await Promise.all([
    getMissionDetailData(missionId),
    getMissionWorkspace(missionId),
  ]);

  if (!result) {
    notFound();
  }

  const { mission } = result;
  const run = intelligence.latestRun;
  const shortId = mission.id.slice(-10).toUpperCase();

  return (
    <>
      <PageHeader
        actions={
          <>
            <ShareButton />
            <Link
              className="inline-flex h-9 items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] font-semibold text-[var(--text-2)]"
              href={`/reports?mission=${mission.id}`}
            >
              <ArrowDownToLine aria-hidden="true" className="size-3.5" />
              Export
            </Link>
          </>
        }
        description={`${mission.project.name} · owned by ${mission.createdBy.name} · updated ${formatDateTime(mission.updatedAt)}`}
        eyebrow={`Research mission · ${shortId}`}
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
              <StatusBadge status="DEMO" />
            </div>
            <p className="mb-0 max-w-5xl text-[13px] leading-6 text-[var(--text-1)]">
              {mission.objective}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="flex items-center gap-2 text-[10px] font-medium text-[var(--status-positive-text)]">
              <span className="size-2 rounded-full bg-[var(--positive)]" />
              Agent network online
            </span>
            <form action={startResearchAction}>
              <input name="missionId" type="hidden" value={mission.id} />
              <input
                name="idempotencyKey"
                type="hidden"
                value={`manual:${mission.id}:${crypto.randomUUID()}`}
              />
              <button
                className="inline-flex h-10 items-center gap-2 rounded-[3px] bg-[var(--accent)] px-5 text-[11px] font-semibold text-[var(--accent-contrast)] hover:bg-[var(--accent-hover)]"
                type="submit"
              >
                <Play aria-hidden="true" className="size-4" />
                Run Research
              </button>
            </form>
          </div>
        </div>

        <dl className="grid border-t border-[var(--rule)] bg-[var(--surface-2)] sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Research depth", formatEnumLabel(mission.researchDepth)],
            ["Time horizon", `${mission.scope.timeHorizonMonths} months`],
            ["Monitoring", formatEnumLabel(mission.monitoringMode)],
            ["Focus areas", mission.scope.focusAreas.join(", ")],
          ].map(([label, value], index) => (
            <div
              className={`p-4 ${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} ${
                index === 2
                  ? "sm:border-l-0 sm:border-t xl:border-l xl:border-t-0"
                  : ""
              }`}
              key={label}
            >
              <dt className="text-[10px] uppercase tracking-[0.05em] text-[var(--text-3)]">
                {label}
              </dt>
              <dd className="m-0 mt-1.5 text-[11px] font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section
        aria-label="Research metrics"
        className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6"
      >
        {[
          ["Sources scanned", run?.sourcesScanned ?? 0, "Approved documents"],
          ["Evidence found", intelligence.evidenceTotal, "Persisted excerpts"],
          [
            "High-quality evidence",
            intelligence.highQualityEvidence,
            "Quality and confidence ≥80%",
          ],
          ["Insights generated", mission._count.insights, "Claim-linked"],
          ["Claims", mission._count.claims, "Validated groups"],
          [
            "Confidence",
            run?.confidenceScore === null || run?.confidenceScore === undefined
              ? "--"
              : formatPercent(run.confidenceScore),
            run?.dataStatus.toUpperCase() ?? "Unavailable",
          ],
        ].map(([label, value, detail], index) => (
          <div
            className={`${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} p-4`}
            key={label}
          >
            <div className="text-[10px] uppercase text-[var(--text-3)]">
              {label}
            </div>
            <div className="mt-1 text-[20px] font-semibold">{value}</div>
            <div className="mt-1 text-[9px] text-[var(--text-3)]">{detail}</div>
          </div>
        ))}
      </section>

      <div className="mb-4 grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(390px,0.9fr)]">
        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-3">
            <div className="flex items-center gap-2">
              <Activity
                aria-hidden="true"
                className="size-4 text-[var(--accent-strong)]"
              />
              <h2 className="m-0 text-[13px] font-semibold">
                Research progress
              </h2>
            </div>
            {run ? (
              <Link href={`/runs/${run.id}`}>
                <StatusBadge status={run.status} />
              </Link>
            ) : (
              <StatusBadge status="PENDING" />
            )}
          </div>
          {run ? (
            <ol className="m-0 list-none p-4">
              {intelligence.steps.map((step, index) => (
                <li
                  className="relative grid grid-cols-[28px_1fr_auto] gap-3 pb-4 last:pb-0"
                  key={step.id}
                >
                  {index < intelligence.steps.length - 1 ? (
                    <span className="absolute bottom-0 left-[13px] top-6 w-px bg-[var(--rule)]" />
                  ) : null}
                  <span
                    className={`z-10 grid size-7 place-items-center rounded-full border ${
                      step.status === "COMPLETED"
                        ? "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]"
                        : step.status === "ACTIVE"
                          ? "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]"
                          : "border-[var(--rule)] bg-[var(--surface-1)] text-[var(--text-3)]"
                    }`}
                  >
                    {step.status === "COMPLETED" ? (
                      <Check aria-hidden="true" className="size-3.5" />
                    ) : (
                      <Circle aria-hidden="true" className="size-3.5" />
                    )}
                  </span>
                  <div>
                    <div className="text-[11px] font-semibold">{step.name}</div>
                    <div className="mt-1 text-[9px] text-[var(--text-3)]">
                      {step.outputSummary ?? step.inputSummary}
                    </div>
                  </div>
                  <div className="text-right text-[9px] text-[var(--text-3)]">
                    {step.status === "COMPLETED" && step.durationMs
                      ? `${Math.round(step.durationMs / 1000)}s`
                      : formatEnumLabel(step.status)}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <div className="grid min-h-52 place-items-center p-6 text-center text-[11px] text-[var(--text-3)]">
              Run Research to create a durable event ledger and inspectable
              agent steps.
            </div>
          )}
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
              href={`/insights?mission=${mission.id}`}
            >
              View all
            </Link>
          </div>
          <div className="divide-y divide-[var(--rule-subtle)]">
            {intelligence.insights.length ? (
              intelligence.insights.map((insight) => (
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
                  <div className="mt-2 text-[9px] text-[var(--text-3)]">
                    {insight.sourceCount} sources · {insight.claimCount} claims
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-8 text-center text-[11px] text-[var(--text-3)]">
                No supported insight exists. IntelBridge withholds unsupported
                conclusions.
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
        <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <div className="grid border-b border-[var(--rule)] sm:grid-cols-3">
            <div className="p-4 sm:border-r sm:border-[var(--rule)]">
              <div className="flex items-center gap-2">
                <BookOpenText
                  aria-hidden="true"
                  className="size-4 text-[var(--accent-strong)]"
                />
                <h2 className="m-0 text-[12px] font-semibold">
                  Evidence snapshot
                </h2>
              </div>
              <div className="mt-4 grid gap-2">
                {intelligence.evidenceSnapshot.map((item) => (
                  <div
                    className="flex items-center justify-between text-[10px]"
                    key={item.label}
                  >
                    <span>{formatEnumLabel(item.label)}</span>
                    <span className="font-mono text-[var(--text-3)]">
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="border-t border-[var(--rule)] p-4 sm:border-r sm:border-t-0">
              <div className="flex items-center gap-2">
                <FileSearch
                  aria-hidden="true"
                  className="size-4 text-[var(--accent-strong)]"
                />
                <h2 className="m-0 text-[12px] font-semibold">Top topics</h2>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {intelligence.topTopics.map((topic) => (
                  <span
                    className="rounded-[3px] bg-[var(--accent-soft)] px-2 py-1 text-[10px] text-[var(--accent-strong)]"
                    key={topic.label}
                  >
                    {topic.label} · {topic.count}
                  </span>
                ))}
              </div>
            </div>
            <div className="border-t border-[var(--rule)] p-4 sm:border-t-0">
              <div className="flex items-center gap-2">
                <RadioTower
                  aria-hidden="true"
                  className="size-4 text-[var(--accent-strong)]"
                />
                <h2 className="m-0 text-[12px] font-semibold">Top sources</h2>
              </div>
              <div className="mt-4 grid gap-2">
                {intelligence.sources.map((source) => (
                  <div
                    className="flex items-center justify-between gap-3 text-[10px]"
                    key={source.id}
                  >
                    <span className="truncate">{source.publisher}</span>
                    <span className="font-mono text-[var(--text-3)]">
                      {source.evidenceCount} evidence
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 text-[10px] text-[var(--text-3)]">
            <span className="flex items-center gap-2">
              <ShieldCheck aria-hidden="true" className="size-4" />
              Source trail, timestamps, validation, and demo state are retained
              on every conclusion.
            </span>
            <Link
              className="font-semibold text-[var(--accent-strong)]"
              href={`/evidence?mission=${mission.id}`}
            >
              Open evidence explorer
            </Link>
          </div>
        </section>

        <AskPanel missionId={mission.id} />
      </div>
    </>
  );
}
