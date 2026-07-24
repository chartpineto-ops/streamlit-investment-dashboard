"use client";

import {
  Bell,
  BookOpenText,
  Bot,
  Boxes,
  ChevronDown,
  Database,
  FileBarChart,
  FileSearch,
  Folder,
  Home,
  Lightbulb,
  ListChecks,
  Plus,
  RadioTower,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { getInitials } from "@/shared/presentation";

type ShellProject = {
  id: string;
  missionCount: number;
  name: string;
};

type ShellProps = {
  children: ReactNode;
  missionCount: number;
  projects: ShellProject[];
  user: {
    email: string;
    name: string;
    role: string;
  };
  workspace: {
    name: string;
  };
};

const navigation = [
  { href: "/", icon: Home, label: "Home" },
  { href: "/missions", icon: ListChecks, label: "Missions" },
  { href: "/sources", icon: BookOpenText, label: "Sources" },
  { href: "/evidence", icon: FileSearch, label: "Evidence" },
  { href: "/insights", icon: Lightbulb, label: "Insights" },
  { href: "/monitoring", icon: RadioTower, label: "Monitoring" },
  { href: "/reports", icon: FileBarChart, label: "Reports" },
  { href: "/datasets", icon: Database, label: "Datasets" },
  { href: "/agent-studio", icon: Bot, label: "Agent Studio" },
  { href: "/projects", icon: Folder, label: "Projects" },
] as const;

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname.startsWith(href);
}

function Navigation({
  missionCount,
  pathname,
}: {
  missionCount: number;
  pathname: string;
}) {
  return (
    <nav aria-label="Primary navigation" className="flex flex-col gap-0.5">
      {navigation.map((item) => {
        const Icon = item.icon;
        const active = isActive(pathname, item.href);

        return (
          <Link
            aria-current={active ? "page" : undefined}
            className={`group flex min-h-10 items-center gap-3 border-l-2 px-4 text-[13px] font-medium transition-colors ${
              active
                ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                : "border-transparent text-[var(--text-2)] hover:bg-[var(--surface-2)] hover:text-[var(--text-1)]"
            }`}
            href={item.href}
            key={item.href}
          >
            <Icon
              aria-hidden="true"
              className="size-4 shrink-0"
              strokeWidth={1.8}
            />
            <span>{item.label}</span>
            {item.href === "/missions" ? (
              <span className="ml-auto min-w-5 rounded-full bg-[var(--accent-tint)] px-1.5 py-0.5 text-center text-[10px] font-semibold text-[var(--accent-strong)]">
                {missionCount}
              </span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}

export function ApplicationShell({
  children,
  missionCount,
  projects,
  user,
  workspace,
}: ShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--text-1)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[248px] flex-col border-r border-[var(--rule)] bg-[var(--surface-1)] lg:flex">
        <div className="flex h-[68px] items-center gap-3 border-b border-[var(--rule)] px-4">
          <div
            aria-hidden="true"
            className="grid size-8 rotate-45 place-items-center rounded-[6px] border-2 border-[var(--accent)] bg-[var(--accent-tint)]"
          >
            <ShieldCheck
              className="size-5 -rotate-45 text-[var(--accent-strong)]"
              strokeWidth={2}
            />
          </div>
          <div>
            <div className="text-[17px] font-bold leading-none">
              IntelBridge
            </div>
            <div className="mt-1.5 text-[10px] text-[var(--text-3)]">
              INFORMATION INTELLIGENCE
            </div>
          </div>
        </div>

        <div className="p-3">
          <Link
            className="flex min-h-10 items-center justify-center gap-2 rounded-[4px] bg-[var(--accent)] px-4 text-[12px] font-semibold text-[var(--accent-contrast)] shadow-[var(--shadow-control)] hover:bg-[var(--accent-hover)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus)]"
            href="/missions/new"
          >
            <Plus aria-hidden="true" className="size-4" />
            New Research
          </Link>
        </div>

        <Navigation missionCount={missionCount} pathname={pathname} />

        <div className="mx-4 mt-5 border-t border-[var(--rule)] pt-4">
          <div className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--text-3)]">
            Projects
          </div>
          <nav aria-label="Projects" className="flex flex-col">
            {projects.map((project) => (
              <Link
                className="flex min-h-9 items-center gap-2 px-1 text-[12px] text-[var(--text-2)] hover:text-[var(--text-1)]"
                href={`/missions?project=${project.id}`}
                key={project.id}
              >
                <Folder
                  aria-hidden="true"
                  className="size-4 text-[var(--text-3)]"
                />
                <span className="truncate">{project.name}</span>
                <span className="ml-auto text-[10px] text-[var(--text-3)]">
                  {project.missionCount}
                </span>
              </Link>
            ))}
          </nav>
        </div>

        <div className="m-3 mt-auto rounded-[4px] border border-[var(--rule)] bg-[var(--surface-2)] p-3">
          <div className="text-[12px] font-semibold">Full vertical slice</div>
          <p className="mb-0 mt-1 text-[10px] leading-4 text-[var(--text-3)]">
            D1-backed missions, runs, evidence, insights, monitors, reports,
            Q&amp;A, agents, and audit records are active.
          </p>
        </div>
      </aside>

      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex h-[68px] items-center gap-3 border-b border-[var(--rule)] bg-[var(--surface-1)] px-4 md:px-6">
          <div className="flex min-w-0 items-center gap-3 lg:hidden">
            <div className="grid size-8 place-items-center rounded-[4px] bg-[var(--accent)] text-[12px] font-bold text-[var(--accent-contrast)]">
              IB
            </div>
            <span className="hidden font-semibold sm:inline">IntelBridge</span>
          </div>

          <div className="hidden min-w-0 items-center gap-2 lg:flex">
            <Boxes aria-hidden="true" className="size-4 text-[var(--text-3)]" />
            <span className="max-w-[260px] truncate text-[12px] font-medium">
              {workspace.name}
            </span>
            <ChevronDown
              aria-hidden="true"
              className="size-3 text-[var(--text-3)]"
            />
          </div>

          <form
            action="/search"
            className="ml-auto hidden w-full max-w-[360px] md:block"
            method="get"
            role="search"
          >
            <label className="sr-only" htmlFor="global-search">
              Search missions, evidence, and insights
            </label>
            <div className="flex h-9 items-center gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-2)] px-3 text-[var(--text-3)]">
              <Search aria-hidden="true" className="size-4" />
              <input
                className="min-w-0 flex-1 bg-transparent text-[12px] outline-none placeholder:text-[var(--text-3)]"
                id="global-search"
                name="q"
                placeholder="Search missions and evidence"
              />
            </div>
          </form>

          <Link
            aria-label="Open notifications"
            className="grid size-9 shrink-0 place-items-center rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] text-[var(--text-2)] disabled:cursor-not-allowed disabled:opacity-60"
            href="/monitoring?view=alerts"
          >
            <Bell aria-hidden="true" className="size-4" />
          </Link>

          <Link
            className="flex min-w-0 items-center gap-2 border-l border-[var(--rule)] pl-3"
            href="/diagnostics"
            title="Open diagnostics and audit activity"
          >
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-[var(--brand-user)] text-[10px] font-semibold text-[var(--accent-contrast)]">
              {getInitials(user.name)}
            </span>
            <div className="hidden min-w-0 sm:block">
              <div className="max-w-[150px] truncate text-[11px] font-semibold">
                {user.name}
              </div>
              <div className="text-[10px] text-[var(--text-3)]">
                {user.role}
              </div>
            </div>
          </Link>
        </header>

        <div className="border-b border-[var(--rule)] bg-[var(--surface-1)] lg:hidden">
          <nav
            aria-label="Mobile primary navigation"
            className="flex gap-1 overflow-x-auto px-3 py-2"
          >
            {navigation.map((item) => (
              <Link
                className={`shrink-0 rounded-[3px] px-3 py-2 text-[11px] font-medium ${
                  isActive(pathname, item.href)
                    ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                    : "text-[var(--text-2)]"
                }`}
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <main className="mx-auto min-h-[calc(100vh-68px)] max-w-[1540px] p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
