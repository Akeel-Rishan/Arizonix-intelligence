"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { useWorkspace } from "@/components/workspaces/workspace-provider";
import { archiveCompany, fetchCompany, restoreCompany, WorkspaceApiError } from "@/lib/api-client";
import type { Company } from "@/lib/types";

export function CompanyDetail({ companyId }: { companyId: string }) {
  const { activeWorkspace, loading: workspaceLoading } = useWorkspace();
  const [company, setCompany] = useState<Company | null>(null);
  const [loading, setLoading] = useState(true);
  const [changing, setChanging] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const canWrite = activeWorkspace?.role !== "viewer";

  useEffect(() => {
    if (!activeWorkspace) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setCompany(null);
      setLoading(true);
      setFailure(null);
      void fetchCompany(activeWorkspace.id, companyId, controller.signal)
        .then(setCompany)
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

  async function toggleArchived() {
    if (!activeWorkspace || !company || !canWrite) return;
    setChanging(true);
    setFailure(null);
    try {
      const updated = company.archived_at
        ? await restoreCompany(activeWorkspace.id, company.id, company.version)
        : await archiveCompany(activeWorkspace.id, company.id, company.version);
      setCompany(updated);
      dialogRef.current?.close();
    } catch (error: unknown) {
      setFailure(
        error instanceof WorkspaceApiError
          ? error.userMessage
          : "The company status could not be changed.",
      );
    } finally {
      setChanging(false);
    }
  }

  if (workspaceLoading || loading) return <p role="status">Loading company…</p>;
  if (!activeWorkspace) return <p role="alert">This workspace is no longer accessible.</p>;
  if (!company)
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-4" role="alert">
        {failure ?? "Company not found."}
      </div>
    );

  const rows = [
    ["Industry", company.industry],
    ["Country", company.country_code],
    ["Website", company.website_url],
    ["Description", company.description],
    ["Notes", company.notes],
  ];
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-7 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="break-words text-3xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-4xl">
              {company.name}
            </h1>
            {company.archived_at ? (
              <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">
                Archived
              </span>
            ) : null}
          </div>
          <p className="mt-3 text-sm text-slate-600">
            Manually entered — research not started · Version {company.version}
          </p>
        </div>
        {canWrite ? (
          <div className="flex shrink-0 flex-wrap gap-2">
            {!company.archived_at ? (
              <Link
                className="inline-flex min-h-11 items-center rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold"
                href={`/prospects/${company.id}/edit`}
              >
                Edit
              </Link>
            ) : null}
            <button
              className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold"
              onClick={() => dialogRef.current?.showModal()}
              type="button"
            >
              {company.archived_at ? "Restore" : "Archive"}
            </button>
          </div>
        ) : null}
      </div>
      {failure ? (
        <p className="rounded-xl bg-rose-50 p-4 text-rose-900" role="alert">
          {failure}
        </p>
      ) : null}
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <dl className="divide-y divide-slate-100">
          {rows.map(([label, value]) => (
            <div className="grid gap-1 px-5 py-4 sm:grid-cols-[10rem_1fr] sm:gap-6" key={label}>
              <dt className="text-sm font-semibold text-slate-600">{label}</dt>
              <dd className="min-w-0 whitespace-pre-wrap break-words text-sm leading-6 text-slate-900">
                {label === "Website" && value ? (
                  <a
                    className="text-cyan-800 underline"
                    href={value}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {value}
                  </a>
                ) : (
                  value || "Not provided"
                )}
              </dd>
            </div>
          ))}
        </dl>
      </section>
      <p className="text-xs text-slate-500">
        Created {new Date(company.created_at).toLocaleString()} · Updated{" "}
        {new Date(company.updated_at).toLocaleString()}
      </p>
      <dialog
        className="m-auto w-[min(28rem,calc(100%-2rem))] rounded-2xl border border-slate-200 p-0 shadow-2xl backdrop:bg-slate-950/50"
        ref={dialogRef}
      >
        <div className="p-6">
          <h2 className="text-xl font-semibold text-slate-950">
            {company.archived_at ? "Restore company?" : "Archive company?"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {company.archived_at
              ? `${company.name} will return to active prospect lists.`
              : `${company.name} will be removed from the default list. Its record is preserved and can be restored later.`}
          </p>
          <div className="mt-6 flex justify-end gap-3">
            <button
              className="min-h-11 rounded-xl border border-slate-300 px-4 text-sm font-semibold"
              disabled={changing}
              onClick={() => dialogRef.current?.close()}
              type="button"
            >
              Cancel
            </button>
            <button
              className="min-h-11 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white disabled:opacity-60"
              disabled={changing}
              onClick={() => void toggleArchived()}
              type="button"
            >
              {changing ? "Saving…" : company.archived_at ? "Restore" : "Archive"}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
}
