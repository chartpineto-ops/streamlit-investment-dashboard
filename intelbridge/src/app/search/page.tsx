import { FileSearch, Search } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { searchCurrentWorkspace } from "@/server/services/search";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = typeof params.q === "string" ? params.q.trim() : "";
  const data = await searchCurrentWorkspace(query);
  return (
    <>
      <PageHeader
        description="Workspace-scoped lookup across projects, missions, sources, runs, and versioned documents."
        eyebrow="Global search"
        title="Search research records"
      />
      <form
        className="mb-4 flex gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-3"
        method="get"
      >
        <label className="sr-only" htmlFor="workspace-search">
          Search research records
        </label>
        <div className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-2)] px-3">
          <Search aria-hidden="true" className="size-4 text-[var(--text-3)]" />
          <input
            autoFocus
            className="min-w-0 flex-1 bg-transparent text-[12px] outline-none"
            defaultValue={query}
            id="workspace-search"
            name="q"
            placeholder="Search projects, missions, sources, runs, or documents"
          />
        </div>
        <button
          className="rounded-[3px] bg-[var(--accent)] px-5 text-[11px] font-semibold text-[var(--accent-contrast)]"
          type="submit"
        >
          Search
        </button>
      </form>
      <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="border-b border-[var(--rule)] px-4 py-3">
          <h2 className="m-0 text-[13px] font-semibold">
            {query
              ? `${data.results.length} results for “${query}”`
              : "Enter a search query"}
          </h2>
        </div>
        {data.results.length ? (
          <div className="divide-y divide-[var(--rule-subtle)]">
            {data.results.map((result) => (
              <Link
                className="flex gap-3 p-4 hover:bg-[var(--row-hover)]"
                href={result.href}
                key={`${result.resultType}-${result.id}`}
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-[3px] bg-[var(--accent-soft)] text-[var(--accent-strong)]">
                  <FileSearch aria-hidden="true" className="size-4" />
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <div className="text-[12px] font-semibold">
                      {result.title}
                    </div>
                    <StatusBadge status={result.resultType} />
                  </div>
                  <p className="mb-0 mt-1 line-clamp-2 text-[10px] leading-5 text-[var(--text-2)]">
                    {result.excerpt}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="grid min-h-64 place-items-center p-8 text-center text-[11px] leading-5 text-[var(--text-3)]">
            {query
              ? "No project, mission, source, run, or document matches this query."
              : "Search is ready. Results remain scoped to the authenticated workspace."}
          </div>
        )}
      </section>
    </>
  );
}
