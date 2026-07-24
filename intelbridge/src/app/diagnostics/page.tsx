import { Activity, Database, HardDrive, ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getOperationsDiagnostics } from "@/server/services/diagnostics";
import { formatDateTime } from "@/shared/presentation";

export default async function DiagnosticsPage() {
  const diagnostics = await getOperationsDiagnostics();
  const metrics = [
    ["Active jobs", diagnostics.activeJobs],
    ["Dead-letter jobs", diagnostics.deadJobs],
    ["Connected sources", diagnostics.connectedSources],
    ["Source errors", diagnostics.failedSources],
    ["Documents", diagnostics.documentCount],
    ["Durable events", diagnostics.eventCount],
  ] as const;
  const environment = [
    ["D1 database", diagnostics.environment.database, Database],
    ["R2 object storage", diagnostics.environment.objectStorage, HardDrive],
    ["GitHub token", diagnostics.environment.githubToken, Activity],
  ] as const;
  return (
    <>
      <PageHeader
        description="Database, object storage, connector, durable queue, SSE ledger, and accountable-action health."
        eyebrow="Internal operations"
        title="Diagnostics"
      />
      <section className="mb-4 grid overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] sm:grid-cols-2 xl:grid-cols-6">
        {metrics.map(([label, value], index) => (
          <div
            className={`${index ? "border-t border-[var(--rule)] sm:border-l sm:border-t-0" : ""} p-4`}
            key={label}
          >
            <div className="text-[9px] uppercase text-[var(--text-3)]">
              {label}
            </div>
            <div className="mt-2 text-[20px] font-semibold">{value}</div>
          </div>
        ))}
      </section>
      <div className="mb-4 grid gap-4 md:grid-cols-3">
        {environment.map(([label, value, Icon]) => (
          <section
            className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-4"
            key={label}
          >
            <Icon
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <div className="mt-3 text-[10px] uppercase text-[var(--text-3)]">
              {label}
            </div>
            <div className="mt-1 text-[12px] font-semibold uppercase">
              {value}
            </div>
          </section>
        ))}
      </div>
      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
          <ShieldCheck aria-hidden="true" className="size-4" />
          <h2 className="m-0 text-[13px] font-semibold">
            Recent audit activity
          </h2>
        </div>
        <table className="w-full min-w-[720px] border-collapse text-left text-[11px]">
          <caption className="sr-only">
            Recent workspace-scoped accountable actions
          </caption>
          <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
            <tr>
              <th className="px-4 py-2.5">Action</th>
              <th className="px-3 py-2.5">Entity</th>
              <th className="px-3 py-2.5">Entity ID</th>
              <th className="px-3 py-2.5">Request ID</th>
              <th className="px-3 py-2.5">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--rule-subtle)]">
            {diagnostics.auditLogs.length ? (
              diagnostics.auditLogs.map((entry) => (
                <tr key={`${entry.requestId}-${entry.entityId}`}>
                  <td className="px-4 py-3">
                    <StatusBadge status={entry.action} />
                  </td>
                  <td className="px-3 py-3">{entry.entityType}</td>
                  <td className="px-3 py-3 font-mono text-[10px]">
                    {entry.entityId}
                  </td>
                  <td className="px-3 py-3 font-mono text-[10px]">
                    {entry.requestId}
                  </td>
                  <td className="px-3 py-3">
                    {formatDateTime(new Date(entry.createdAt))}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-10 text-center" colSpan={5}>
                  No audit entries are available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </>
  );
}
