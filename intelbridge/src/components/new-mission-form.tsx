"use client";

import type { ConnectorStatus, ConnectorType } from "@prisma/client";
import Link from "next/link";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import {
  createMissionAction,
  type CreateMissionState,
} from "@/app/missions/new/actions";
import { formatEnumLabel } from "@/shared/presentation";
import { StatusBadge } from "./status-badge";

type ConnectorOption = {
  id: string;
  name: string;
  status: ConnectorStatus;
  type: ConnectorType;
};

type ProjectOption = {
  id: string;
  name: string;
};

const initialState: CreateMissionState = {
  message: null,
};

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button
      className="h-10 rounded-[3px] border border-[var(--accent)] bg-[var(--accent)] px-5 text-[11px] font-semibold text-[var(--accent-contrast)] disabled:cursor-wait disabled:opacity-60"
      disabled={pending}
      type="submit"
    >
      {pending ? "Creating mission…" : "Create mission"}
    </button>
  );
}

export function NewMissionForm({
  connectors,
  projects,
}: {
  connectors: ConnectorOption[];
  projects: ProjectOption[];
}) {
  const [state, action] = useActionState(createMissionAction, initialState);

  return (
    <form action={action} className="grid gap-4">
      {state.message ? (
        <div
          className="rounded-[3px] border border-[var(--status-negative-border)] bg-[var(--status-negative-fill)] px-4 py-3 text-[11px] text-[var(--status-negative-text)]"
          role="alert"
        >
          {state.message}
        </div>
      ) : null}

      <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <div className="border-b border-[var(--rule)] px-5 py-3">
          <h2 className="m-0 text-[13px] font-semibold">Mission definition</h2>
          <p className="mb-0 mt-1 text-[10px] text-[var(--text-3)]">
            These fields create the persistent, accountable scope record.
          </p>
        </div>
        <div className="grid gap-4 p-5">
          <label className="grid gap-1.5 text-[11px] font-semibold">
            Mission title
            <input
              className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
              maxLength={140}
              minLength={5}
              name="title"
              placeholder="Enterprise search launch impact"
              required
            />
          </label>

          <label className="grid gap-1.5 text-[11px] font-semibold">
            Research objective
            <textarea
              className="min-h-28 resize-y rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] p-3 font-normal leading-5"
              maxLength={2000}
              minLength={30}
              name="objective"
              placeholder="State the decision, evidence requirement, and intended output."
              required
            />
          </label>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1.5 text-[11px] font-semibold">
              Project
              <select
                className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
                name="projectId"
                required
              >
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1.5 text-[11px] font-semibold">
              Research depth
              <select
                className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
                defaultValue="DEEP"
                name="researchDepth"
              >
                <option value="RAPID">Rapid</option>
                <option value="STANDARD">Standard</option>
                <option value="DEEP">Deep</option>
              </select>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1.5 text-[11px] font-semibold">
              Time horizon
              <select
                className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
                defaultValue="12"
                name="timeHorizonMonths"
              >
                <option value="3">Last 3 months</option>
                <option value="6">Last 6 months</option>
                <option value="12">Last 12 months</option>
                <option value="24">Last 24 months</option>
              </select>
            </label>

            <label className="grid gap-1.5 text-[11px] font-semibold">
              Monitoring policy
              <select
                className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
                defaultValue="MANUAL"
                name="monitoringMode"
              >
                <option value="MANUAL">Manual</option>
                <option value="HOURLY">Hourly</option>
                <option value="DAILY">Daily</option>
                <option value="WEEKLY">Weekly</option>
              </select>
            </label>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="grid gap-1.5 text-[11px] font-semibold">
              Focus areas
              <input
                className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
                defaultValue="Products, Pricing, Go-to-market"
                name="focusAreas"
                required
              />
              <span className="text-[10px] font-normal text-[var(--text-3)]">
                Separate focus areas with commas.
              </span>
            </label>

            <label className="grid gap-1.5 text-[11px] font-semibold">
              Regions
              <input
                className="h-10 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-1)] px-3 font-normal"
                defaultValue="Global"
                name="regions"
                required
              />
              <span className="text-[10px] font-normal text-[var(--text-3)]">
                Separate regions with commas.
              </span>
            </label>
          </div>
        </div>
      </section>

      <fieldset className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
        <legend className="sr-only">Approved source connectors</legend>
        <div className="border-b border-[var(--rule)] px-5 py-3">
          <h2 className="m-0 text-[13px] font-semibold">Approved sources</h2>
          <p className="mb-0 mt-1 text-[10px] text-[var(--text-3)]">
            Unimplemented production connectors remain visibly unavailable and
            cannot be selected.
          </p>
        </div>
        <div className="grid gap-px bg-[var(--rule)] sm:grid-cols-2 xl:grid-cols-3">
          {connectors.map((connector) => {
            const available = connector.status === "AVAILABLE";

            return (
              <label
                className={`flex min-h-24 gap-3 bg-[var(--surface-1)] p-4 ${
                  available ? "cursor-pointer" : "cursor-not-allowed opacity-65"
                }`}
                key={connector.id}
              >
                <input
                  className="mt-0.5 size-4 accent-[var(--accent)]"
                  defaultChecked={connector.type === "DEMO"}
                  disabled={!available}
                  name="connectorIds"
                  type="checkbox"
                  value={connector.id}
                />
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-semibold">
                      {connector.name}
                    </span>
                    <StatusBadge status={connector.status} />
                  </span>
                  <span className="mt-1 block text-[10px] text-[var(--text-3)]">
                    {formatEnumLabel(connector.type)}
                    {!available ? " - Connection delivered in Milestone 3" : ""}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="flex items-center justify-end gap-3">
        <Link
          className="inline-flex h-10 items-center px-3 text-[11px] font-semibold text-[var(--text-2)]"
          href="/missions"
        >
          Cancel
        </Link>
        <SubmitButton />
      </div>
    </form>
  );
}
