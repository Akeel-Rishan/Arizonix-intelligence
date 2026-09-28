"use client";

import { useState } from "react";

import { CreateWorkspaceForm } from "@/components/workspaces/create-workspace-form";
import { useWorkspace } from "@/components/workspaces/workspace-provider";

export function WorkspaceSwitcher({ compact = false }: { compact?: boolean }) {
  const { activeWorkspace, error, loading, selectWorkspace, workspaces } = useWorkspace();
  const [creating, setCreating] = useState(false);

  return (
    <div className={compact ? "mt-5" : "mt-7 px-3"}>
      <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
        Workspace
        <select
          aria-label="Active workspace"
          className="mt-2 min-h-11 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 text-sm text-white outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
          disabled={loading || workspaces.length === 0}
          onChange={(event) => selectWorkspace(event.target.value)}
          value={activeWorkspace?.id ?? ""}
        >
          {workspaces.length === 0 ? (
            <option value="">{loading ? "Loading…" : "No workspace"}</option>
          ) : null}
          {workspaces.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>
              {workspace.name}
            </option>
          ))}
        </select>
      </label>
      {error ? <p className="mt-2 text-xs text-amber-300">{error}</p> : null}
      <button
        className="mt-2 min-h-10 text-left text-xs font-semibold text-cyan-300 outline-none hover:text-cyan-200 focus-visible:ring-2 focus-visible:ring-cyan-300"
        onClick={() => setCreating((value) => !value)}
        type="button"
      >
        {creating ? "Cancel" : "+ Create workspace"}
      </button>
      {creating ? <CreateWorkspaceForm compact onCreated={() => setCreating(false)} /> : null}
    </div>
  );
}
