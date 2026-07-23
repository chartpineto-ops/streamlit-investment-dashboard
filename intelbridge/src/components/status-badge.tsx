import { formatEnumLabel } from "@/shared/presentation";

const statusStyles: Record<string, string> = {
  ACTIVE:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  AVAILABLE:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  COMPLETED:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  READY:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  DRAFT:
    "border-[var(--status-neutral-border)] bg-[var(--status-neutral-fill)] text-[var(--text-2)]",
  NOT_CONNECTED:
    "border-[var(--status-neutral-border)] bg-[var(--status-neutral-fill)] text-[var(--text-2)]",
  PAUSED:
    "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  FAILED:
    "border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] text-[var(--status-negative-text)]",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex min-h-5 items-center rounded-[3px] border px-2 text-[10px] font-semibold uppercase tracking-[0.04em] ${
        statusStyles[status] ?? statusStyles.DRAFT
      }`}
    >
      {formatEnumLabel(status)}
    </span>
  );
}
