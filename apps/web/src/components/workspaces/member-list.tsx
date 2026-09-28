"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";

import { MemberRoleControl } from "@/components/workspaces/member-role-control";
import { useWorkspace } from "@/components/workspaces/workspace-provider";
import {
  addWorkspaceMember,
  fetchWorkspaceMembers,
  removeWorkspaceMember,
  updateWorkspaceMemberRole,
  WorkspaceApiError,
} from "@/lib/api-client";
import type { WorkspaceMember, WorkspaceRole } from "@/lib/types";

export function MemberList({
  workspaceId,
  actorRole,
}: {
  workspaceId: string;
  actorRole: WorkspaceRole;
}) {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [userId, setUserId] = useState("");
  const [newRole, setNewRole] = useState<WorkspaceRole>(
    actorRole === "owner" ? "viewer" : "viewer",
  );
  const requestNumber = useRef(0);
  const { refreshWorkspaces } = useWorkspace();
  const canAdd = actorRole === "owner" || actorRole === "admin";

  const load = async (signal?: AbortSignal) => {
    const current = ++requestNumber.current;
    setLoading(true);
    try {
      const page = await fetchWorkspaceMembers(workspaceId, signal);
      if (current === requestNumber.current) {
        setMembers(page.items);
        setMessage(null);
      }
    } catch (caught: unknown) {
      if (signal?.aborted || current !== requestNumber.current) return;
      if (caught instanceof WorkspaceApiError && caught.status === 404) {
        await refreshWorkspaces();
      }
      setMessage(
        caught instanceof WorkspaceApiError ? caught.userMessage : "Members could not be loaded.",
      );
    } finally {
      if (current === requestNumber.current) setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      requestNumber.current += 1;
      controller.abort();
    };
    // load is intentionally scoped to the active workspace ID.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  const mutate = async (key: string, operation: () => Promise<void>) => {
    if (pending) return;
    setPending(key);
    setMessage(null);
    try {
      await operation();
      await load();
    } catch (caught: unknown) {
      setMessage(
        caught instanceof WorkspaceApiError
          ? caught.code === "last_owner"
            ? "Promote another member to owner before changing or removing the last owner."
            : caught.userMessage
          : "The member change could not be completed.",
      );
    } finally {
      setPending(null);
    }
  };

  const add = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const exactId = userId.trim();
    if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(exactId)
    ) {
      setMessage("Enter the exact UUID shown in the other user’s account settings.");
      return;
    }
    await mutate("add", async () => {
      await addWorkspaceMember(workspaceId, exactId, newRole);
      setUserId("");
    });
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-950">Members</h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          Add an existing user by the exact ID from their account settings. This does not send an
          invitation.
        </p>
      </div>
      {message ? (
        <p
          className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"
          role="status"
        >
          {message}
        </p>
      ) : null}
      {canAdd ? (
        <form
          className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_10rem_auto] sm:items-end"
          onSubmit={add}
        >
          <label className="text-sm font-semibold text-slate-800">
            Existing user UUID
            <input
              className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 font-mono text-xs outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              disabled={pending !== null}
              onChange={(event) => setUserId(event.target.value)}
              placeholder="00000000-0000-0000-0000-000000000000"
              value={userId}
            />
          </label>
          <label className="text-sm font-semibold text-slate-800">
            Role
            <select
              className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 capitalize outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
              disabled={pending !== null}
              onChange={(event) => setNewRole(event.target.value as WorkspaceRole)}
              value={newRole}
            >
              {(actorRole === "owner"
                ? ["owner", "admin", "analyst", "viewer"]
                : ["analyst", "viewer"]
              ).map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>
          <button
            className="min-h-11 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white disabled:opacity-60"
            disabled={pending !== null}
            type="submit"
          >
            {pending === "add" ? "Adding…" : "Add user"}
          </button>
        </form>
      ) : null}
      <div className="mt-6 space-y-3" aria-busy={loading}>
        {loading ? <p className="text-sm text-slate-600">Loading members…</p> : null}
        {!loading && members.length === 0 ? (
          <p className="text-sm text-slate-600">No members found.</p>
        ) : null}
        {members.map((member) => {
          const canRemove =
            actorRole === "owner" ||
            (actorRole === "admin" && ["analyst", "viewer"].includes(member.role));
          const label = member.email ?? member.user_id;
          return (
            <article
              className="grid min-w-0 gap-3 rounded-xl border border-slate-200 p-4 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center"
              key={member.user_id}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950" title={label}>
                  {label}
                </p>
                <p className="mt-1 break-all font-mono text-[11px] text-slate-500">
                  {member.user_id}
                </p>
              </div>
              <MemberRoleControl
                actorRole={actorRole}
                disabled={pending !== null}
                onChange={(role) =>
                  void mutate(`role:${member.user_id}`, () =>
                    updateWorkspaceMemberRole(workspaceId, member.user_id, role),
                  )
                }
                role={member.role}
                targetRole={member.role}
              />
              {canRemove ? (
                <button
                  className="min-h-10 rounded-lg border border-rose-200 px-3 text-sm font-semibold text-rose-700 outline-none hover:bg-rose-50 focus-visible:ring-2 focus-visible:ring-rose-500 disabled:opacity-60"
                  disabled={pending !== null}
                  onClick={() => {
                    if (window.confirm(`Remove ${label} from this workspace?`)) {
                      void mutate(`remove:${member.user_id}`, () =>
                        removeWorkspaceMember(workspaceId, member.user_id),
                      );
                    }
                  }}
                  type="button"
                >
                  {pending === `remove:${member.user_id}` ? "Removing…" : "Remove"}
                </button>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
