import { Activity, ShieldCheck } from "lucide-react";

import {
  DiagnosticsSummary,
  OperationalArchitectureNote,
} from "@/components/intelligence-workspaces";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getDiagnosticsWorkspace } from "@/server/services/intelligence";
import { formatDateTime } from "@/shared/presentation";

export default async function DiagnosticsPage() {
  const { diagnostics } = await getDiagnosticsWorkspace();

  return (
    <>
      <PageHeader
        description="Runtime state, durable processing counts, connector availability, event delivery mode, and recent accountable actions."
        eyebrow="Internal operations"
        title="Diagnostics"
      />
      <div className="mb-4">
        <DiagnosticsSummary diagnostics={diagnostics} />
      </div>
      <div className="mb-4 grid gap-4 lg:grid-cols-3">
        {[
          [
            "Event delivery",
            diagnostics.sseStatus.toUpperCase(),
            "Ordered D1 event replay with SSE Last-Event-ID support.",
          ],
          [
            "Job state",
            diagnostics.queueMode,
            `${diagnostics.activeRuns} active and ${diagnostics.failedRuns} failed research runs.`,
          ],
          [
            "Model provider",
            diagnostics.modelProvider.toUpperCase(),
            "Deterministic structured provider; live calls require server-side configuration.",
          ],
        ].map(([label, value, detail]) => (
          <section
            className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-4"
            key={label}
          >
            <div className="flex items-center gap-2 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              <Activity
                aria-hidden="true"
                className="size-3.5 text-[var(--accent-strong)]"
              />
              {label}
            </div>
            <div className="mt-2 text-[13px] font-semibold">{value}</div>
            <p className="mb-0 mt-2 text-[10px] leading-5 text-[var(--text-3)]">
              {detail}
            </p>
          </section>
        ))}
      </div>

      <section className="mb-4 overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
          <ShieldCheck
            aria-hidden="true"
            className="size-4 text-[var(--accent-strong)]"
          />
          <h2 className="m-0 text-[13px] font-semibold">
            Recent audit activity
          </h2>
        </div>
        <table className="w-full min-w-[720px] border-collapse text-left text-[11px]">
          <caption className="sr-only">
            Recent accountable actions in the authenticated workspace
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
            {diagnostics.auditLogs.map((entry) => (
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
                <td className="px-3 py-3">{formatDateTime(entry.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <OperationalArchitectureNote />
    </>
  );
}
