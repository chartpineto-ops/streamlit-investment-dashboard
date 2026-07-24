"use client";

import { ArrowUp, FileSearch } from "lucide-react";
import Link from "next/link";
import { useActionState } from "react";

import { askIntelBridgeAction, type AskState } from "@/app/actions";

const initialState: AskState = {
  answer: "",
  citations: [],
  confidence: 0,
  limitations: "",
  status: "idle",
};

export function AskPanel({ missionId }: { missionId: string }) {
  const [state, action, pending] = useActionState(
    askIntelBridgeAction,
    initialState,
  );

  return (
    <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
      <div className="flex items-center gap-2 border-b border-[var(--rule)] px-4 py-3">
        <FileSearch
          aria-hidden="true"
          className="size-4 text-[var(--accent-strong)]"
        />
        <h2 className="m-0 text-[13px] font-semibold">Ask IntelBridge</h2>
      </div>
      <div className="p-4">
        <form action={action}>
          <input name="missionId" type="hidden" value={missionId} />
          <label className="sr-only" htmlFor={`question-${missionId}`}>
            Ask a question about mission evidence
          </label>
          <div className="flex min-h-10 items-center gap-2 rounded-[3px] border border-[var(--rule)] bg-[var(--surface-2)] px-3">
            <input
              className="min-w-0 flex-1 bg-transparent text-[11px] outline-none placeholder:text-[var(--text-3)]"
              disabled={pending}
              id={`question-${missionId}`}
              maxLength={500}
              name="question"
              placeholder="Ask a question about this evidence"
              required
            />
            <button
              aria-label="Ask IntelBridge"
              className="grid size-7 place-items-center rounded-[3px] bg-[var(--accent)] text-[var(--accent-contrast)] disabled:opacity-50"
              disabled={pending}
              type="submit"
            >
              <ArrowUp aria-hidden="true" className="size-3.5" />
            </button>
          </div>
        </form>

        {state.status !== "idle" ? (
          <div
            aria-live="polite"
            className="mt-3 border-t border-[var(--rule-subtle)] pt-3"
          >
            <div className="whitespace-pre-line text-[11px] leading-5 text-[var(--text-1)]">
              {state.answer}
            </div>
            {state.citations.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {state.citations.map((citation) => (
                  <Link
                    className="rounded-[3px] border border-[var(--status-info-border)] bg-[var(--status-info-fill)] px-2 py-1 text-[10px] font-semibold text-[var(--status-info-text)]"
                    href={`/evidence?selected=${citation.evidenceId}`}
                    key={citation.evidenceId}
                  >
                    [{citation.label}] {citation.publisher}
                  </Link>
                ))}
              </div>
            ) : null}
            <div className="mt-3 text-[10px] leading-4 text-[var(--text-3)]">
              Confidence: {(state.confidence * 100).toFixed(0)}% ·{" "}
              {state.limitations}
            </div>
          </div>
        ) : (
          <p className="mb-0 mt-2 text-[10px] leading-4 text-[var(--text-3)]">
            Answers use only mission-linked evidence, separate retrieved facts
            from inference, and expose every citation.
          </p>
        )}
      </div>
    </section>
  );
}
