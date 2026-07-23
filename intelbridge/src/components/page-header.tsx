import type { ReactNode } from "react";

export function PageHeader({
  actions,
  description,
  eyebrow,
  title,
}: {
  actions?: ReactNode;
  description?: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <header className="mb-5 flex flex-col gap-3 border-b border-[var(--rule)] pb-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--accent-strong)]">
          {eyebrow}
        </div>
        <h1 className="m-0 text-[22px] font-semibold tracking-[-0.01em]">
          {title}
        </h1>
        {description ? (
          <p className="mb-0 mt-1 max-w-3xl text-[12px] leading-5 text-[var(--text-2)]">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-2">{actions}</div>
      ) : null}
    </header>
  );
}
