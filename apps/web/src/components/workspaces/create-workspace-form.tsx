"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { useWorkspace } from "@/components/workspaces/workspace-provider";
import { createWorkspace, WorkspaceApiError } from "@/lib/api-client";

export function CreateWorkspaceForm({
  compact = false,
  onCreated,
}: {
  compact?: boolean;
  onCreated?: () => void;
}) {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const { refreshWorkspaces } = useWorkspace();
  const router = useRouter();

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = name.trim().replace(/\s+/g, " ");
    if (normalized.length < 2) {
      setMessage("Enter at least 2 characters.");
      return;
    }
    if (pending) return;
    setPending(true);
    setMessage(null);
    try {
      const workspace = await createWorkspace(normalized);
      await refreshWorkspaces(workspace.id);
      setName("");
      onCreated?.();
      router.push("/");
    } catch (caught: unknown) {
      setMessage(
        caught instanceof WorkspaceApiError
          ? caught.userMessage
          : "The workspace could not be created.",
      );
    } finally {
      setPending(false);
    }
  };

  return (
    <form className={compact ? "mt-2" : "mt-8 max-w-xl"} onSubmit={submit}>
      <label
        className={`block font-semibold ${compact ? "text-xs text-slate-300" : "text-sm text-slate-800"}`}
      >
        Workspace name
        <input
          autoComplete="organization"
          className={`mt-2 min-h-11 w-full rounded-xl border px-3 outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${compact ? "border-slate-700 bg-slate-900 text-sm text-white" : "border-slate-300 bg-white text-slate-950"}`}
          disabled={pending}
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
          placeholder="Northstar research"
          value={name}
        />
      </label>
      {message ? (
        <p className={`mt-2 text-sm ${compact ? "text-amber-300" : "text-rose-700"}`} role="status">
          {message}
        </p>
      ) : null}
      <button
        className={`mt-3 min-h-11 rounded-xl px-4 text-sm font-semibold outline-none disabled:cursor-not-allowed disabled:opacity-60 ${compact ? "bg-cyan-300 text-slate-950" : "bg-slate-950 text-white hover:bg-slate-800"}`}
        disabled={pending}
        type="submit"
      >
        {pending ? "Creating…" : "Create workspace"}
      </button>
    </form>
  );
}
