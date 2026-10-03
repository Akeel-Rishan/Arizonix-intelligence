"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { MemberList } from "@/components/workspaces/member-list";
import { useWorkspace } from "@/components/workspaces/workspace-provider";
import { leaveWorkspace, renameWorkspace, WorkspaceApiError } from "@/lib/api-client";
import type { Workspace } from "@/lib/types";

export function WorkspaceSettings() {
  const context = useWorkspace();
  const { activeWorkspace, error, loading } = context;

  if (loading) return <p className="text-sm text-slate-600">Loading workspace settings…</p>;
  if (error)
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
        {error}
      </p>
    );
  if (!activeWorkspace) return null;
  return (
    <WorkspaceSettingsContent
      context={context}
      key={activeWorkspace.id}
      workspace={activeWorkspace}
    />
  );
}

function WorkspaceSettingsContent({
  context,
  workspace: activeWorkspace,
}: {
  context: ReturnType<typeof useWorkspace>;
  workspace: Workspace;
}) {
  const [name, setName] = useState(activeWorkspace.name);
  const [pending, setPending] = useState<"rename" | "leave" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const router = useRouter();
  const { refreshWorkspaces } = context;
  const canRename = ["owner", "admin"].includes(activeWorkspace.role);

  const rename = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    setPending("rename");
    setMessage(null);
    try {
      await renameWorkspace(activeWorkspace.id, name.trim());
      await refreshWorkspaces(activeWorkspace.id);
      setMessage("Workspace name updated.");
    } catch (caught: unknown) {
      setMessage(caught instanceof WorkspaceApiError ? caught.userMessage : "Rename failed.");
    } finally {
      setPending(null);
    }
  };

  const leave = async () => {
    if (
      pending ||
      !window.confirm(`Leave ${activeWorkspace.name}? You will immediately lose access.`)
    )
      return;
    setPending("leave");
    setMessage(null);
    try {
      await leaveWorkspace(activeWorkspace.id);
      await refreshWorkspaces();
      router.push("/");
    } catch (caught: unknown) {
      setMessage(
        caught instanceof WorkspaceApiError && caught.code === "last_owner"
          ? "Promote another member to owner before the last owner leaves."
          : caught instanceof WorkspaceApiError
            ? caught.userMessage
            : "The workspace could not be left.",
      );
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">Workspace</h2>
            <p className="mt-1 text-sm text-slate-600">
              Your current role is{" "}
              <strong className="capitalize text-slate-900">{activeWorkspace.role}</strong>.
            </p>
          </div>
          <button
            className="min-h-10 self-start rounded-lg border border-rose-200 px-3 text-sm font-semibold text-rose-700 outline-none hover:bg-rose-50 focus-visible:ring-2 focus-visible:ring-rose-500 disabled:opacity-60"
            disabled={pending !== null}
            onClick={() => void leave()}
            type="button"
          >
            {pending === "leave" ? "Leaving…" : "Leave workspace"}
          </button>
        </div>
        {canRename ? (
          <form className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={rename}>
            <label className="min-w-0 flex-1 text-sm font-semibold text-slate-800">
              Workspace name
              <input
                className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
                disabled={pending !== null}
                maxLength={100}
                onChange={(event) => setName(event.target.value)}
                value={name}
              />
            </label>
            <button
              className="min-h-11 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white disabled:opacity-60"
              disabled={pending !== null || name.trim().length < 2}
              type="submit"
            >
              {pending === "rename" ? "Saving…" : "Save name"}
            </button>
          </form>
        ) : null}
        {message ? (
          <p className="mt-4 text-sm text-slate-700" role="status">
            {message}
          </p>
        ) : null}
      </section>
      {canRename ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-950">Audit history</h2>
          <p className="mt-1 text-sm text-slate-600">
            Review committed workspace and membership changes for this workspace.
          </p>
          <Link
            className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
            href="/settings/audit"
          >
            View audit history
          </Link>
        </section>
      ) : null}
      <MemberList actorRole={activeWorkspace.role} workspaceId={activeWorkspace.id} />
    </div>
  );
}
