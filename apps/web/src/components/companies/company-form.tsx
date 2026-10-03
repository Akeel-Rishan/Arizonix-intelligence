"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { useWorkspace } from "@/components/workspaces/workspace-provider";
import { createCompany, fetchCompany, updateCompany, WorkspaceApiError } from "@/lib/api-client";
import type { Company, CompanyInput } from "@/lib/types";

const emptyInput: CompanyInput = {
  name: "",
  website_url: null,
  industry: null,
  country_code: null,
  description: null,
  notes: null,
};

export function CompanyForm({ companyId }: { companyId?: string }) {
  const { activeWorkspace, loading: workspaceLoading } = useWorkspace();
  const router = useRouter();
  const [company, setCompany] = useState<Company | null>(null);
  const [input, setInput] = useState<CompanyInput>(emptyInput);
  const [loading, setLoading] = useState(Boolean(companyId));
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [versionConflict, setVersionConflict] = useState(false);
  const canWrite = activeWorkspace?.role !== "viewer";

  useEffect(() => {
    if (!companyId || !activeWorkspace) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setCompany(null);
      setLoading(true);
      setFailure(null);
      void fetchCompany(activeWorkspace.id, companyId, controller.signal)
        .then((value) => {
          setCompany(value);
          setInput({
            name: value.name,
            website_url: value.website_url,
            industry: value.industry,
            country_code: value.country_code,
            description: value.description,
            notes: value.notes,
          });
        })
        .catch((error: unknown) => {
          if (!controller.signal.aborted)
            setFailure(
              error instanceof WorkspaceApiError ? error.userMessage : "Company unavailable.",
            );
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [activeWorkspace, companyId]);

  const setField = (field: keyof CompanyInput, value: string) =>
    setInput((current) => ({ ...current, [field]: value.trim() ? value : null }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!activeWorkspace || !canWrite) return;
    setSaving(true);
    setFailure(null);
    setVersionConflict(false);
    try {
      const normalized = { ...input, name: input.name.trim() };
      const saved = companyId
        ? await updateCompany(activeWorkspace.id, companyId, company?.version ?? 0, normalized)
        : await createCompany(activeWorkspace.id, normalized);
      router.push(`/prospects/${saved.id}`);
      router.refresh();
    } catch (error: unknown) {
      if (error instanceof WorkspaceApiError) {
        setFailure(error.userMessage);
        setVersionConflict(error.code === "version_conflict");
      } else setFailure("The company could not be saved. Try again.");
    } finally {
      setSaving(false);
    }
  }

  if (workspaceLoading || loading) return <p role="status">Loading company…</p>;
  if (!activeWorkspace) return <p role="alert">This workspace is no longer accessible.</p>;
  if (!canWrite)
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4" role="alert">
        Viewers can read company records but cannot create or edit them.
      </p>
    );
  if (company?.archived_at)
    return (
      <p className="rounded-xl border border-amber-200 bg-amber-50 p-4" role="alert">
        Restore this company before editing it.
      </p>
    );

  const fieldClass =
    "mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 py-2 font-normal outline-none focus-visible:ring-2 focus-visible:ring-cyan-500";
  return (
    <form className="max-w-3xl space-y-6" onSubmit={submit}>
      <p className="text-sm text-slate-600">
        This information is manually entered. Research has not yet been performed.
      </p>
      <div className="grid gap-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2 sm:p-7">
        <label className="text-sm font-semibold text-slate-800 sm:col-span-2">
          Company name <span className="text-rose-700">*</span>
          <input
            autoFocus
            className={fieldClass}
            maxLength={200}
            onChange={(event) => setInput((current) => ({ ...current, name: event.target.value }))}
            required
            value={input.name}
          />
        </label>
        <label className="text-sm font-semibold text-slate-800 sm:col-span-2">
          Website <span className="font-normal text-slate-500">(optional)</span>
          <input
            className={fieldClass}
            maxLength={2048}
            onChange={(event) => setField("website_url", event.target.value)}
            placeholder="https://example.com"
            type="url"
            value={input.website_url ?? ""}
          />
        </label>
        <label className="text-sm font-semibold text-slate-800">
          Industry <span className="font-normal text-slate-500">(optional)</span>
          <input
            className={fieldClass}
            maxLength={100}
            onChange={(event) => setField("industry", event.target.value)}
            value={input.industry ?? ""}
          />
        </label>
        <label className="text-sm font-semibold text-slate-800">
          Country code <span className="font-normal text-slate-500">(optional)</span>
          <input
            className={`${fieldClass} uppercase`}
            maxLength={2}
            onChange={(event) => setField("country_code", event.target.value.toUpperCase())}
            pattern="[A-Za-z]{2}"
            placeholder="US"
            value={input.country_code ?? ""}
          />
        </label>
        <label className="text-sm font-semibold text-slate-800 sm:col-span-2">
          Description <span className="font-normal text-slate-500">(optional)</span>
          <textarea
            className={fieldClass}
            maxLength={2000}
            onChange={(event) => setField("description", event.target.value)}
            rows={4}
            value={input.description ?? ""}
          />
        </label>
        <label className="text-sm font-semibold text-slate-800 sm:col-span-2">
          Private workspace notes <span className="font-normal text-slate-500">(optional)</span>
          <textarea
            className={fieldClass}
            maxLength={5000}
            onChange={(event) => setField("notes", event.target.value)}
            rows={6}
            value={input.notes ?? ""}
          />
          <span className="mt-2 block text-xs font-normal text-slate-500">
            Notes are excluded from company list responses and audit details.
          </span>
        </label>
      </div>
      {failure ? (
        <div className="rounded-xl bg-rose-50 p-4 text-rose-900" role="alert">
          <p>{failure}</p>
          {versionConflict ? (
            <button
              className="mt-3 font-semibold underline"
              onClick={() => {
                if (window.confirm("Reload the latest company and discard your unsaved changes?"))
                  window.location.reload();
              }}
              type="button"
            >
              Reload latest company
            </button>
          ) : null}
        </div>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <button
          className="min-h-11 rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white disabled:opacity-60"
          disabled={saving}
          type="submit"
        >
          {saving ? "Saving…" : companyId ? "Save changes" : "Create company"}
        </button>
        <Link
          className="inline-flex min-h-11 items-center rounded-xl border border-slate-300 bg-white px-5 text-sm font-semibold"
          href={companyId ? `/prospects/${companyId}` : "/prospects"}
        >
          Cancel
        </Link>
      </div>
    </form>
  );
}
