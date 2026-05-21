import { useEffect, useMemo, useRef, useState } from "react";
import { API_BASE } from "../api/client";
import { getToken } from "../lib/auth";

/**
 * A single line emitted by the backend SSE stream
 * (`GET /v1/api/jobs/:id/events`). The backend sends one JSON object per
 * event with named `event:` headers (phase_start, phase_end, agent_call,
 * cost_tick, error, done). We surface the lot as a tail-log.
 */
export interface ProgressEvent {
  id: number;
  kind: string;
  ts: number;
  payload: unknown;
}

interface ProgressStreamProps {
  jobId: string;
  /** Auto-scroll to the newest event. Default: true. */
  follow?: boolean;
  /** Cap on retained events; older ones are dropped from the head. */
  maxEvents?: number;
  /** Notify the parent when the stream emits a terminal state. */
  onDone?: () => void;
  /** Notify the parent on stream-level error. */
  onError?: (err: Event) => void;
}

const KNOWN_EVENT_KINDS = [
  "message",
  "phase_start",
  "phase_end",
  "agent_call",
  "cost_tick",
  "log",
  "done",
  "error",
] as const;

const KIND_COLORS: Record<string, string> = {
  phase_start: "text-blue-700",
  phase_end: "text-blue-500",
  agent_call: "text-purple-700",
  cost_tick: "text-amber-700",
  done: "text-emerald-700 font-semibold",
  error: "text-red-700 font-semibold",
  log: "text-gray-700",
  message: "text-gray-700",
};

export function ProgressStream({
  jobId,
  follow = true,
  maxEvents = 500,
  onDone,
  onError,
}: ProgressStreamProps): JSX.Element {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [status, setStatus] = useState<"connecting" | "open" | "closed" | "error">(
    "connecting",
  );
  const tailRef = useRef<HTMLDivElement | null>(null);
  const counterRef = useRef(0);

  // Memoized stream URL — only recomputed when the jobId changes.
  const streamUrl = useMemo(() => {
    const token = getToken();
    // EventSource cannot set custom headers, so we pass the JWT as a
    // one-shot query-string token. The backend validates it the same way
    // it validates the Authorization header.
    const qs = token ? `?token=${encodeURIComponent(token)}` : "";
    return `${API_BASE}/v1/api/jobs/${jobId}/events${qs}`;
  }, [jobId]);

  useEffect(() => {
    setEvents([]);
    counterRef.current = 0;
    setStatus("connecting");

    const es = new EventSource(streamUrl);

    const append = (kind: string, raw: string, lastEventId: string) => {
      let payload: unknown = raw;
      try {
        payload = JSON.parse(raw);
      } catch {
        /* keep raw string */
      }
      const id = Number.parseInt(lastEventId || "0", 10) || ++counterRef.current;
      setEvents((prev) => {
        const next = [...prev, { id, kind, ts: Date.now() / 1000, payload }];
        if (next.length > maxEvents) {
          return next.slice(next.length - maxEvents);
        }
        return next;
      });
      if (kind === "done") {
        onDone?.();
        es.close();
        setStatus("closed");
      }
    };

    es.onopen = () => setStatus("open");

    // Default `message` event (no `event:` header).
    es.onmessage = (ev: MessageEvent<string>) => {
      append("message", ev.data, ev.lastEventId);
    };

    // Named event listeners for the known kinds.
    const listeners: Array<[string, (ev: MessageEvent<string>) => void]> = [];
    for (const kind of KNOWN_EVENT_KINDS) {
      if (kind === "message") continue;
      const listener = (ev: MessageEvent<string>) => append(kind, ev.data, ev.lastEventId);
      es.addEventListener(kind, listener as EventListener);
      listeners.push([kind, listener]);
    }

    es.onerror = (ev) => {
      setStatus("error");
      onError?.(ev);
      // EventSource will auto-reconnect by default; do not close().
    };

    return () => {
      for (const [kind, listener] of listeners) {
        es.removeEventListener(kind, listener as EventListener);
      }
      es.close();
    };
    // We intentionally omit onDone/onError from deps so the stream isn't
    // torn down by parent callback identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [streamUrl, maxEvents]);

  // Auto-scroll to newest event.
  useEffect(() => {
    if (!follow) return;
    tailRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length, follow]);

  return (
    <div className="vedix-card">
      <header className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 text-sm">
        <span className="font-medium text-gray-700">Live progress</span>
        <span className={statusBadge(status)}>{statusLabel(status)}</span>
      </header>
      <div className="font-mono text-xs p-4 bg-white max-h-96 overflow-auto">
        {events.length === 0 ? (
          <p className="text-gray-400">Waiting for the first event…</p>
        ) : (
          <ul className="space-y-1">
            {events.map((e) => (
              <li key={e.id} className="flex gap-3">
                <span className="text-gray-400 shrink-0 w-20">
                  {formatTime(e.ts)}
                </span>
                <span
                  className={`shrink-0 w-28 ${KIND_COLORS[e.kind] ?? "text-gray-700"}`}
                >
                  {e.kind}
                </span>
                <span className="text-gray-800 break-all">
                  {formatPayload(e.payload)}
                </span>
              </li>
            ))}
          </ul>
        )}
        <div ref={tailRef} />
      </div>
    </div>
  );
}

function statusLabel(status: "connecting" | "open" | "closed" | "error"): string {
  switch (status) {
    case "connecting":
      return "connecting…";
    case "open":
      return "● live";
    case "closed":
      return "complete";
    case "error":
      return "reconnecting…";
  }
}

function statusBadge(status: "connecting" | "open" | "closed" | "error"): string {
  const base = "text-xs px-2 py-0.5 rounded-full ";
  switch (status) {
    case "open":
      return base + "bg-emerald-100 text-emerald-700";
    case "closed":
      return base + "bg-gray-200 text-gray-700";
    case "error":
      return base + "bg-amber-100 text-amber-800";
    case "connecting":
    default:
      return base + "bg-blue-100 text-blue-700";
  }
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString();
}

function formatPayload(payload: unknown): string {
  if (typeof payload === "string") return payload;
  try {
    return JSON.stringify(payload);
  } catch {
    return String(payload);
  }
}
