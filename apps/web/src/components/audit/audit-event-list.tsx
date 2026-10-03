"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AuditEventDetails } from "@/components/audit/audit-event-details";
import { AuditFilters, type AppliedAuditFilters } from "@/components/audit/audit-filters";
import { useWorkspace } from "@/components/workspaces/workspace-provider";
import { fetchAuditEvents, WorkspaceApiError } from "@/lib/api-client";
import type { AuditEvent } from "@/lib/types";

const descriptions: Record<AuditEvent["action"], string> = {
  "workspace.created": "Created the workspace",
  "workspace.renamed": "Renamed the workspace",
  "membership.added": "Added a workspace member",
  "membership.role_changed": "Changed a member role",
  "membership.removed": "Removed a workspace member",
  "membership.left": "Left the workspace",
  "company.created": "Created a company",
  "company.updated": "Updated a company",
  "company.archived": "Archived a company",
  "company.restored": "Restored a company",
};

export function AuditEventList() {
  const { activeWorkspace, error: workspaceError, loading: workspaceLoading } = useWorkspace();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [filters, setFilters] = useState<AppliedAuditFilters>({});
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState<WorkspaceApiError | null>(null);
  const requestVersion = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const authorized = activeWorkspace && ["owner", "admin"].includes(activeWorkspace.role);

  const load = useCallback(
    async (cursor: string | undefined, append: boolean) => {
      if (!activeWorkspace || !authorized) return;
      const version = ++requestVersion.current;
      activeRequest.current?.abort();
      const controller = new AbortController();
      activeRequest.current = controller;
      setLoading(true);
      setFailure(null);
      try {
        const page = await fetchAuditEvents(activeWorkspace.id, filters, cursor, controller.signal);
        if (version !== requestVersion.current) return;
        setEvents((current) => (append ? [...current, ...page.items] : page.items));
        setNextCursor(page.next_cursor);
      } catch (caught: unknown) {
        if (version !== requestVersion.current) return;
        setEvents([]);
        setNextCursor(null);
        setFailure(
          caught instanceof WorkspaceApiError
            ? caught
            : new WorkspaceApiError(0, "unavailable", "Audit history is temporarily unavailable."),
        );
      } finally {
        if (version === requestVersion.current) {
          activeRequest.current = null;
          setLoading(false);
        }
      }
    },
    [activeWorkspace, authorized, filters],
  );

  useEffect(() => {
    activeRequest.current?.abort();
    activeRequest.current = null;
    requestVersion.current += 1;
    const timer = window.setTimeout(() => {
      setEvents([]);
      setNextCursor(null);
      setFailure(null);
      setLoading(false);
      if (activeWorkspace && authorized) void load(undefined, false);
    }, 0);
    return () => {
      window.clearTimeout(timer);
      activeRequest.current?.abort();
      activeRequest.current = null;
      requestVersion.current += 1;
    };
  }, [activeWorkspace, authorized, filters, load]);

  if (workspaceLoading) return <p role="status">Loading workspace access…</p>;
  if (workspaceError) return <p role="alert">{workspaceError}</p>;
  if (!activeWorkspace) return <p role="alert">This workspace is no longer accessible.</p>;
  if (!authorized)
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4" role="alert">
        Audit history is available only to workspace owners and admins.
      </p>
    );

  const hasFilters = Object.keys(filters).length > 0;
  return (
    <div className="space-y-6">
      <AuditFilters
        disabled={loading}
        onApply={(next) => {
          setFilters(next);
          setEvents([]);
          setNextCursor(null);
        }}
      />
      {failure ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4" role="alert">
          <p>
            {failure.status === 403
              ? "Your permission to view audit history was revoked."
              : failure.status === 404
                ? "This workspace is no longer accessible."
                : failure.userMessage}
          </p>
          <button
            className="mt-3 rounded-lg border border-rose-300 px-3 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
            onClick={() => void load(undefined, false)}
            type="button"
          >
            Retry
          </button>
        </div>
      ) : null}
      {loading && events.length === 0 ? <p role="status">Loading audit history…</p> : null}
      {!loading && !failure && events.length === 0 ? (
        <p className="rounded-xl border border-slate-200 bg-white p-5 text-slate-600" role="status">
          {hasFilters
            ? "No events match these filters."
            : "No audit events have been recorded yet."}
        </p>
      ) : null}
      <ol className="space-y-4" aria-label="Audit events">
        {events.map((event) => (
          <li
            className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            key={event.id}
          >
            <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="font-semibold text-slate-950">{descriptions[event.action]}</p>
                <p className="mt-1 break-all text-sm text-slate-600">Actor {event.actor_user_id}</p>
              </div>
              <time className="text-sm text-slate-500" dateTime={event.occurred_at}>
                {new Date(event.occurred_at).toLocaleString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "numeric",
                  minute: "2-digit",
                  second: "2-digit",
                  timeZoneName: "short",
                })}
              </time>
            </div>
            <AuditEventDetails event={event} />
          </li>
        ))}
      </ol>
      {nextCursor ? (
        <button
          className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 disabled:opacity-60"
          disabled={loading}
          onClick={() => void load(nextCursor, true)}
          type="button"
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      ) : null}
    </div>
  );
}
