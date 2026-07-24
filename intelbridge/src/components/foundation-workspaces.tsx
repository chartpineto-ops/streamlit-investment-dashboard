import {
  Archive,
  Cable,
  FolderPlus,
  Link2,
  Settings2,
  TestTube2,
  Upload,
} from "lucide-react";

import {
  archiveProjectAction,
  createConnectorAction,
  createProjectAction,
  ingestSourceAction,
  testConnectorAction,
} from "@/app/actions";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import type {
  getProjectsWorkspaceData,
  getSettingsWorkspaceData,
  getSourcesWorkspaceData,
} from "@/server/services/foundation";
import { formatDateTime, formatEnumLabel } from "@/shared/presentation";

const inputClass =
  "h-9 min-w-0 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[11px] outline-none focus:border-[var(--accent)]";
const buttonClass =
  "inline-flex h-9 items-center justify-center gap-2 rounded-[3px] border border-[var(--accent)] bg-[var(--accent)] px-3 text-[11px] font-semibold text-[var(--accent-contrast)] hover:bg-[var(--accent-hover)]";
const secondaryButtonClass =
  "inline-flex h-8 items-center justify-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 text-[10px] font-semibold text-[var(--text-2)] hover:bg-[var(--surface-2)]";

function Notice({ value }: { value?: string }) {
  return value ? (
    <div
      className="mb-4 border border-[var(--status-positive-border)] bg-[var(--status-positive-fill)] px-4 py-3 text-[11px] text-[var(--status-positive-text)]"
      role="status"
    >
      {formatEnumLabel(value)}
    </div>
  ) : null;
}

export function ProjectsWorkspace({
  data,
  notice,
}: {
  data: Awaited<ReturnType<typeof getProjectsWorkspaceData>>;
  notice?: string;
}) {
  return (
    <>
      <PageHeader
        description="Create durable research workstreams and archive completed scopes without deleting their missions."
        eyebrow="Foundation"
        title="Projects"
      />
      <Notice value={notice} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <table className="w-full border-collapse text-left text-[11px]">
            <caption className="sr-only">
              Projects in the active IntelBridge workspace
            </caption>
            <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
              <tr>
                <th className="px-4 py-2.5">Project</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5 text-right">Missions</th>
                <th className="px-4 py-2.5">Updated</th>
                <th className="px-4 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--rule-subtle)]">
              {data.projects.length ? (
                data.projects.map((project) => (
                  <tr key={project.id}>
                    <td className="px-4 py-3">
                      <div className="font-semibold">{project.name}</div>
                      <div className="mt-1 max-w-xl text-[10px] text-[var(--text-3)]">
                        {project.description}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={project.status} />
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {project.missionCount}
                    </td>
                    <td className="px-4 py-3 text-[10px] text-[var(--text-3)]">
                      {formatDateTime(new Date(project.updatedAt))}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {project.status === "ACTIVE" ? (
                        <form action={archiveProjectAction}>
                          <input
                            name="projectId"
                            type="hidden"
                            value={project.id}
                          />
                          <button
                            className={secondaryButtonClass}
                            type="submit"
                          >
                            <Archive aria-hidden="true" className="size-3.5" />
                            Archive
                          </button>
                        </form>
                      ) : (
                        <span className="text-[10px] text-[var(--text-3)]">
                          Read only
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    className="px-4 py-10 text-center text-[var(--text-3)]"
                    colSpan={5}
                  >
                    No projects exist. Create the first project to begin.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <form
          action={createProjectAction}
          className="h-fit rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
        >
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <FolderPlus
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[12px] font-semibold">Create project</h2>
          </div>
          <div className="grid gap-3 p-4">
            <label className="grid gap-1.5 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              Name
              <input
                className={inputClass}
                name="name"
                placeholder="Regulatory landscape"
                required
              />
            </label>
            <label className="grid gap-1.5 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              Description
              <textarea
                className="min-h-24 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] p-3 text-[11px] normal-case outline-none focus:border-[var(--accent)]"
                name="description"
                placeholder="Define the durable research workstream and its decision purpose."
                required
              />
            </label>
            <button className={buttonClass} type="submit">
              Create project
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

export function SourcesWorkspace({
  data,
  filters,
  notice,
}: {
  data: Awaited<ReturnType<typeof getSourcesWorkspaceData>>;
  filters: { project?: string; q?: string; status?: string; type?: string };
  notice?: string;
}) {
  const connectors = data.connectors.filter(
    (connector) =>
      (!filters.q ||
        connector.name.toLowerCase().includes(filters.q.toLowerCase())) &&
      (!filters.type || connector.type === filters.type) &&
      (!filters.status || connector.status === filters.status) &&
      (!filters.project || connector.projectIds.includes(filters.project)),
  );
  return (
    <>
      <PageHeader
        description="Configure governed source adapters, inspect their health, and test connections without exposing credentials."
        eyebrow="Foundation"
        title="Sources"
      />
      <Notice value={notice} />

      <form
        className="mb-4 grid gap-2 rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-3 sm:grid-cols-2 xl:grid-cols-[1fr_180px_180px_220px_auto]"
        method="get"
      >
        <input
          className={inputClass}
          defaultValue={filters.q}
          name="q"
          placeholder="Filter by connector name"
        />
        <select
          className={inputClass}
          defaultValue={filters.type ?? ""}
          name="type"
        >
          <option value="">All types</option>
          {[
            "RSS",
            "WEBPAGE",
            "MANUAL_URL",
            "FILE_UPLOAD",
            "GITHUB",
            "DEMO",
          ].map((type) => (
            <option key={type} value={type}>
              {formatEnumLabel(type)}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          defaultValue={filters.status ?? ""}
          name="status"
        >
          <option value="">All states</option>
          {["CONNECTED", "DISCONNECTED", "ERROR", "DISABLED"].map((status) => (
            <option key={status} value={status}>
              {formatEnumLabel(status)}
            </option>
          ))}
        </select>
        <select
          className={inputClass}
          defaultValue={filters.project ?? ""}
          name="project"
        >
          <option value="">All projects</option>
          {data.missions
            .map((mission) => mission.project)
            .filter(
              (project, index, projects) =>
                projects.findIndex(
                  (candidate) => candidate.id === project.id,
                ) === index,
            )
            .map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
        </select>
        <button className={buttonClass} type="submit">
          Filter
        </button>
      </form>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="overflow-hidden rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
          <table className="w-full border-collapse text-left text-[11px]">
            <caption className="sr-only">
              Source connectors configured in this workspace
            </caption>
            <thead className="bg-[var(--surface-3)] text-[10px] uppercase text-[var(--text-3)]">
              <tr>
                <th className="px-4 py-2.5">Connector</th>
                <th className="px-4 py-2.5">State</th>
                <th className="px-4 py-2.5">Last test</th>
                <th className="px-4 py-2.5">Last sync</th>
                <th className="px-4 py-2.5 text-right">Test</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--rule-subtle)]">
              {connectors.length ? (
                connectors.map((connector) => (
                  <tr key={connector.id}>
                    <td className="px-4 py-3">
                      <div className="font-semibold">{connector.name}</div>
                      <div className="mt-1 text-[10px] text-[var(--text-3)]">
                        {formatEnumLabel(connector.type)} ·{" "}
                        {connector.missionCount} missions
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={connector.status} />
                    </td>
                    <td className="px-4 py-3 text-[10px] text-[var(--text-3)]">
                      {connector.lastTestedAt
                        ? `${formatDateTime(new Date(connector.lastTestedAt))}${
                            connector.responseTimeMs !== null
                              ? ` · ${connector.responseTimeMs} ms`
                              : ""
                          }`
                        : "Not tested"}
                      {connector.lastTestMessage ? (
                        <div className="mt-1 max-w-xs">
                          {connector.lastTestMessage}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-[10px] text-[var(--text-3)]">
                      {connector.lastSuccessfulSyncAt
                        ? formatDateTime(
                            new Date(connector.lastSuccessfulSyncAt),
                          )
                        : "Never"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <form action={testConnectorAction}>
                        <input
                          name="connectorId"
                          type="hidden"
                          value={connector.id}
                        />
                        <button className={secondaryButtonClass} type="submit">
                          <TestTube2 aria-hidden="true" className="size-3.5" />
                          Test
                        </button>
                      </form>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    className="px-4 py-10 text-center text-[var(--text-3)]"
                    colSpan={5}
                  >
                    No connectors are configured.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <form
          action={createConnectorAction}
          className="h-fit rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
        >
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Cable
              aria-hidden="true"
              className="size-4 text-[var(--accent-strong)]"
            />
            <h2 className="m-0 text-[12px] font-semibold">Create connector</h2>
          </div>
          <div className="grid gap-3 p-4">
            <label className="grid gap-1.5 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              Name
              <input
                className={inputClass}
                name="name"
                placeholder="Industry release feed"
                required
              />
            </label>
            <label className="grid gap-1.5 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              Type
              <select className={inputClass} name="type">
                <option value="RSS">RSS / Atom</option>
                <option value="WEBPAGE">Public webpage</option>
                <option value="MANUAL_URL">Manual URL</option>
                <option value="FILE_UPLOAD">File upload</option>
                <option value="GITHUB">GitHub public</option>
                <option value="DEMO">Deterministic demo</option>
              </select>
            </label>
            <label className="grid gap-1.5 text-[10px] font-semibold uppercase text-[var(--text-3)]">
              Endpoint or repository
              <input
                className={inputClass}
                name="endpoint"
                placeholder="https://example.com/feed.xml or owner/repo"
              />
              <span className="normal-case font-normal leading-4">
                Leave blank only for Demo and File Upload connectors. Secrets
                are read from server environment variables.
              </span>
            </label>
            <button className={buttonClass} type="submit">
              Create connector
            </button>
          </div>
        </form>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <form
          action={ingestSourceAction}
          className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
        >
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Link2 aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">
              Register manual URL
            </h2>
          </div>
          <div className="grid gap-3 p-4">
            <input name="mode" type="hidden" value="url" />
            <select className={inputClass} name="missionId" required>
              <option value="">Select mission</option>
              {data.missions.map((mission) => (
                <option key={mission.id} value={mission.id}>
                  {mission.title}
                </option>
              ))}
            </select>
            <input
              className={inputClass}
              name="url"
              placeholder="https://public.example/research"
              required
              type="url"
            />
            <button className={buttonClass} type="submit">
              Register for next run
            </button>
            <p className="m-0 text-[9px] leading-4 text-[var(--text-3)]">
              The mission must have a connected Manual URL source. Retrieval
              occurs only in its background run.
            </p>
          </div>
        </form>

        <form
          action={ingestSourceAction}
          className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]"
        >
          <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
            <Upload aria-hidden="true" className="size-4" />
            <h2 className="m-0 text-[12px] font-semibold">
              Upload source file
            </h2>
          </div>
          <div className="grid gap-3 p-4">
            <input name="mode" type="hidden" value="file" />
            <select className={inputClass} name="missionId" required>
              <option value="">Select mission</option>
              {data.missions.map((mission) => (
                <option key={mission.id} value={mission.id}>
                  {mission.title}
                </option>
              ))}
            </select>
            <input
              accept=".txt,.md,.html,.csv,.json,.xml,.pdf"
              className="rounded-[3px] border border-[var(--rule)] p-2 text-[10px]"
              name="file"
              required
              type="file"
            />
            <button className={buttonClass} type="submit">
              Store for next run
            </button>
            <p className="m-0 text-[9px] leading-4 text-[var(--text-3)]">
              Files up to 10 MB are stored in R2. Text and supported PDFs are
              normalized by the assigned File Upload connector.
            </p>
          </div>
        </form>
      </div>
    </>
  );
}

export function SettingsWorkspace({
  data,
}: {
  data: Awaited<ReturnType<typeof getSettingsWorkspaceData>>;
}) {
  return (
    <>
      <PageHeader
        description="Workspace identity and runtime boundaries for this authenticated IntelBridge deployment."
        eyebrow="Administration"
        title="Settings"
      />
      <section className="max-w-3xl rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
          <Settings2
            aria-hidden="true"
            className="size-4 text-[var(--accent-strong)]"
          />
          <h2 className="m-0 text-[12px] font-semibold">Workspace context</h2>
        </div>
        <dl className="grid sm:grid-cols-2">
          {[
            ["Workspace", data.context.workspace.name],
            ["Workspace ID", data.context.workspace.id],
            ["Signed-in user", data.context.user.name],
            ["Role", data.context.user.role],
          ].map(([label, value]) => (
            <div
              className="border-b border-[var(--rule-subtle)] px-4 py-3 even:sm:border-l"
              key={label}
            >
              <dt className="text-[10px] uppercase text-[var(--text-3)]">
                {label}
              </dt>
              <dd className="mb-0 mt-1 break-all text-[11px] font-semibold">
                {value}
              </dd>
            </div>
          ))}
        </dl>
        <p className="m-0 px-4 py-3 text-[10px] leading-4 text-[var(--text-3)]">
          Sites authentication identifies the current user. All repository
          queries apply the active workspace ID on the server.
        </p>
      </section>
    </>
  );
}
