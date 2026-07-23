"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main className="grid min-h-screen place-items-center bg-[var(--canvas)] p-6">
          <div
            className="w-full max-w-xl rounded-[4px] border border-[var(--status-negative-border)] bg-[var(--surface-1)] p-6"
            role="alert"
          >
            <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--status-negative-text)]">
              Workspace unavailable
            </div>
            <h1 className="mb-0 mt-2 text-[19px] font-semibold">
              IntelBridge could not load persisted data
            </h1>
            <p className="mb-4 mt-2 text-[12px] leading-5 text-[var(--text-2)]">
              The application did not substitute fixture rows. Confirm the
              PostgreSQL database is running, migrated, and seeded before
              retrying.
            </p>
            <button
              className="rounded-[3px] border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-[11px] font-semibold text-[var(--accent-contrast)]"
              onClick={reset}
              type="button"
            >
              Retry workspace
            </button>
            {error.digest ? (
              <div className="mt-3 text-[10px] text-[var(--text-3)]">
                Diagnostic reference: {error.digest}
              </div>
            ) : null}
          </div>
        </main>
      </body>
    </html>
  );
}
