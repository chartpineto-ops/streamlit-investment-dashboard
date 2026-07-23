import Link from "next/link";

export default function NotFound() {
  return (
    <div className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-6">
      <h1 className="m-0 text-[18px] font-semibold">Record not found</h1>
      <p className="mb-4 mt-2 text-[12px] text-[var(--text-2)]">
        The record does not exist in the authenticated workspace, or access is
        not allowed.
      </p>
      <Link
        className="font-semibold text-[var(--accent-strong)]"
        href="/missions"
      >
        Return to missions
      </Link>
    </div>
  );
}
