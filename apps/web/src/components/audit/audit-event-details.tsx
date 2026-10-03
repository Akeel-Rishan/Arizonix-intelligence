"use client";

import type { AuditEvent } from "@/lib/types";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "Not set";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function CopyButton({ label, value }: { label: string; value: string }) {
  return (
    <button
      className="rounded-lg border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 outline-none hover:bg-slate-50 focus-visible:ring-2 focus-visible:ring-cyan-500"
      onClick={() => void navigator.clipboard.writeText(value)}
      type="button"
    >
      Copy {label}
    </button>
  );
}

export function AuditEventDetails({ event }: { event: AuditEvent }) {
  return (
    <details className="mt-4 border-t border-slate-200 pt-4">
      <summary className="cursor-pointer rounded text-sm font-semibold text-slate-800 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500">
        Event details
      </summary>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        {Object.entries(event.details).map(([key, value]) => (
          <div className="min-w-0" key={key}>
            <dt className="font-medium text-slate-500">{key.replaceAll("_", " ")}</dt>
            <dd className="mt-1 break-words text-slate-900">{displayValue(value)}</dd>
          </div>
        ))}
        <div className="min-w-0">
          <dt className="font-medium text-slate-500">Event ID</dt>
          <dd className="mt-1 break-all font-mono text-xs text-slate-900">{event.id}</dd>
          <CopyButton label="event ID" value={event.id} />
        </div>
        <div className="min-w-0">
          <dt className="font-medium text-slate-500">Request ID</dt>
          <dd className="mt-1 break-all font-mono text-xs text-slate-900">{event.request_id}</dd>
          <CopyButton label="request ID" value={event.request_id} />
        </div>
      </dl>
    </details>
  );
}
