"use client";

import { RadioTower } from "lucide-react";
import { useEffect, useState } from "react";

type StreamEvent = {
  createdAt: string;
  payload: {
    message?: string;
  };
  sequenceNumber: number;
  type: string;
};

export function RunEventStream({
  runId,
  terminal,
}: {
  runId: string;
  terminal: boolean;
}) {
  const [connection, setConnection] = useState<
    "connecting" | "live" | "reconnecting" | "complete"
  >(terminal ? "complete" : "connecting");
  const [events, setEvents] = useState<StreamEvent[]>([]);

  useEffect(() => {
    const source = new EventSource(`/api/runs/${runId}/events`);
    source.onopen = () => setConnection("live");
    source.onmessage = (message) => {
      const event = JSON.parse(message.data) as StreamEvent;
      setEvents((current) =>
        current.some(
          (existing) => existing.sequenceNumber === event.sequenceNumber,
        )
          ? current
          : [...current, event],
      );
      if (event.type === "run.completed" || event.type === "run.failed") {
        setConnection("complete");
        source.close();
      }
    };
    source.onerror = () => {
      if (!terminal) {
        setConnection("reconnecting");
      }
    };

    return () => source.close();
  }, [runId, terminal]);

  return (
    <section className="rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)]">
      <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-3">
        <div className="flex items-center gap-2">
          <RadioTower
            aria-hidden="true"
            className="size-4 text-[var(--accent-strong)]"
          />
          <h2 className="m-0 text-[13px] font-semibold">
            Durable event stream
          </h2>
        </div>
        <span className="text-[10px] font-semibold uppercase text-[var(--text-3)]">
          {connection}
        </span>
      </div>
      <ol
        aria-live="polite"
        className="m-0 max-h-80 list-none divide-y divide-[var(--rule-subtle)] overflow-y-auto p-0"
      >
        {events.length ? (
          events.map((event) => (
            <li
              className="grid grid-cols-[32px_1fr_auto] gap-3 px-4 py-3"
              key={event.sequenceNumber}
            >
              <span className="grid size-6 place-items-center rounded-full bg-[var(--accent-soft)] text-[10px] font-semibold text-[var(--accent-strong)]">
                {event.sequenceNumber}
              </span>
              <div>
                <div className="text-[11px] font-semibold">
                  {event.payload.message ?? event.type.replaceAll(".", " ")}
                </div>
                <div className="mt-1 text-[10px] uppercase text-[var(--text-3)]">
                  {event.type}
                </div>
              </div>
              <time className="text-[10px] text-[var(--text-3)]">
                {new Date(event.createdAt).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
              </time>
            </li>
          ))
        ) : (
          <li className="px-4 py-8 text-center text-[11px] text-[var(--text-3)]">
            {connection === "connecting"
              ? "Connecting to the run event ledger…"
              : "No new events after the saved sequence."}
          </li>
        )}
      </ol>
    </section>
  );
}
