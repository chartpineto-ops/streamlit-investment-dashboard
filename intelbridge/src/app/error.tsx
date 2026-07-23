"use client";

import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const isDatabaseUnavailable =
    error.message.includes("connect") || error.message.includes("DATABASE_URL");

  return (
    <div
      className="rounded-[4px] border border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] p-5"
      role="alert"
    >
      <div className="text-[13px] font-semibold text-[var(--status-negative-text)]">
        {isDatabaseUnavailable
          ? "IntelBridge data is unavailable"
          : "This workspace could not load"}
      </div>
      <p className="mb-4 mt-1 max-w-2xl text-[11px] leading-5 text-[var(--text-2)]">
        {isDatabaseUnavailable
          ? "The application could not reach its PostgreSQL database. Start the documented local database and apply the migration before retrying."
          : "The request failed before persisted workspace data could be displayed. No fallback data has been substituted."}
      </p>
      <button
        className="rounded-[3px] border border-[var(--accent)] bg-[var(--accent)] px-3 py-2 text-[11px] font-semibold text-[var(--accent-contrast)]"
        onClick={reset}
        type="button"
      >
        Retry
      </button>
    </div>
  );
}
