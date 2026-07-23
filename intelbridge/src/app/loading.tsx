export default function Loading() {
  return (
    <div aria-live="polite" className="grid gap-4" role="status">
      <div className="h-14 animate-pulse rounded-[4px] bg-[var(--surface-3)]" />
      <div className="h-24 animate-pulse rounded-[4px] bg-[var(--surface-3)]" />
      <div className="h-72 animate-pulse rounded-[4px] bg-[var(--surface-3)]" />
      <span className="sr-only">Loading IntelBridge workspace</span>
    </div>
  );
}
