import { formatEnumLabel } from "@/shared/presentation";

const statusStyles: Record<string, string> = {
  ACTIVE:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  AVAILABLE:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  COMPLETED:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  CONFIRMED:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  HIGH: "border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] text-[var(--status-negative-text)]",
  LIVE: "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  OPEN: "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  READ: "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  STRENGTHENED:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  VALIDATED:
    "border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] text-[var(--status-positive-text)]",
  READY:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  CONTRADICTION:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  DEMO: "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  KNOWLEDGE_GAP:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  MATERIAL_CHANGE:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  PRODUCT_GAP:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  STRATEGIC:
    "border-[var(--status-info-border)] bg-[var(--status-info-fill)] text-[var(--status-info-text)]",
  DRAFT:
    "border-[var(--status-neutral-border)] bg-[var(--status-neutral-fill)] text-[var(--text-2)]",
  LOW: "border-[var(--status-neutral-border)] bg-[var(--status-neutral-fill)] text-[var(--text-2)]",
  NOT_CONNECTED:
    "border-[var(--status-neutral-border)] bg-[var(--status-neutral-fill)] text-[var(--text-2)]",
  PENDING:
    "border-[var(--status-neutral-border)] bg-[var(--status-neutral-fill)] text-[var(--text-2)]",
  PAUSED:
    "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  MEDIUM:
    "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  OPPORTUNITY:
    "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  RISK: "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  SINGLE_SOURCE:
    "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  UNREAD:
    "border-[var(--status-warning-border)] bg-[var(--status-warning-fill)] text-[var(--status-warning-text)]",
  CANCELLED:
    "border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] text-[var(--status-negative-text)]",
  CONTRADICTED:
    "border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] text-[var(--status-negative-text)]",
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
