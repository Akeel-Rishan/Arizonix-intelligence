"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { useWorkspace } from "@/components/workspaces/workspace-provider";
import { fetchCompanies, WorkspaceApiError } from "@/lib/api-client";
import type { CompanyArchiveFilter, CompanyListItem } from "@/lib/types";

function websiteHost(value: string | null): string | null {
  if (!value) return null;
  try {
    return new URL(value).host;
  } catch {
    return null;
  }
}

export function CompanyList() {
  const { activeWorkspace, error: workspaceError, loading: workspaceLoading } = useWorkspace();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const requestedArchive = searchParams.get("archive");
  const archive: CompanyArchiveFilter =
    requestedArchive === "archived" || requestedArchive === "all" ? requestedArchive : "active";
  const search = searchParams.get("search") ?? "";
  const industry = searchParams.get("industry") ?? "";
  const countryCode = searchParams.get("country") ?? "";
  const [searchDraft, setSearchDraft] = useState(search);
  const [items, setItems] = useState<CompanyListItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const requestVersion = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const canWrite = activeWorkspace?.role !== "viewer";

  const replaceFilter = useCallback(
    (key: string, value: string) => {
      const next = new URLSearchParams(searchParams.toString());
      if (value) next.set(key, value);
      else next.delete(key);
      router.replace(`${pathname}${next.size ? `?${next.toString()}` : ""}`);
    },
    [pathname, router, searchParams],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setSearchDraft(search), 0);
    return () => window.clearTimeout(timer);
  }, [search]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (searchDraft !== search) replaceFilter("search", searchDraft.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [replaceFilter, search, searchDraft]);

  const load = useCallback(
    async (cursor?: string, append = false) => {
      if (!activeWorkspace) return;
      const version = ++requestVersion.current;
      activeRequest.current?.abort();
      const controller = new AbortController();
      activeRequest.current = controller;
      setLoading(true);
      setFailure(null);
      try {
        const page = await fetchCompanies(
          activeWorkspace.id,
          { archive, search, industry, countryCode },
          cursor,
          controller.signal,
        );
        if (version !== requestVersion.current) return;
        setItems((current) => (append ? [...current, ...page.items] : page.items));
        setNextCursor(page.next_cursor);
      } catch (error: unknown) {
        if (version !== requestVersion.current || controller.signal.aborted) return;
        setItems([]);
        setNextCursor(null);
        setFailure(
          error instanceof WorkspaceApiError
            ? error.userMessage
            : "Companies are temporarily unavailable.",
        );
      } finally {
        if (version === requestVersion.current) setLoading(false);
      }
    },
    [activeWorkspace, archive, countryCode, industry, search],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => {
      window.clearTimeout(timer);
      activeRequest.current?.abort();
      requestVersion.current += 1;
    };
  }, [load]);

  if (workspaceLoading) return <p role="status">Loading workspace access…</p>;
  if (workspaceError) return <p role="alert">{workspaceError}</p>;
  if (!activeWorkspace) return <p role="alert">This workspace is no longer accessible.</p>;

  const hasFilters = Boolean(search || industry || countryCode || archive !== "active");
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-600">
          Manually entered records are unverified until later research steps add evidence.
        </p>
        {canWrite ? (
          <Link
            className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2"
            href="/prospects/new"
          >
            Add company
          </Link>
        ) : null}
      </div>
      <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm font-semibold text-slate-700">
          Search
          <input
            className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 font-normal outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            maxLength={100}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Company name"
            type="search"
            value={searchDraft}
          />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Industry
          <input
            className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 font-normal outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            defaultValue={industry}
            key={`industry-${industry}`}
            maxLength={100}
            onBlur={(event) => replaceFilter("industry", event.target.value.trim())}
            placeholder="e.g. Logistics"
          />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Country
          <input
            className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 font-normal uppercase outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            defaultValue={countryCode}
            key={`country-${countryCode}`}
            maxLength={2}
            onBlur={(event) => replaceFilter("country", event.target.value.trim().toUpperCase())}
            placeholder="US"
          />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Status
          <select
            className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 font-normal outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
            onChange={(event) => replaceFilter("archive", event.target.value)}
            value={archive}
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </select>
        </label>
      </div>
      {hasFilters ? (
        <button
          className="text-sm font-semibold text-cyan-800 underline-offset-4 hover:underline"
          onClick={() => router.replace(pathname)}
          type="button"
        >
          Clear filters
        </button>
      ) : null}
      {failure ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4" role="alert">
          <p>{failure}</p>
          <button className="mt-3 font-semibold text-rose-800" onClick={() => void load()}>
            Retry
          </button>
        </div>
      ) : null}
      {loading && items.length === 0 ? <p role="status">Loading companies…</p> : null}
      {!loading && !failure && items.length === 0 ? (
        <EmptyState
          title={hasFilters ? "No matching companies" : "No companies yet"}
          description={
            hasFilters
              ? "Adjust the filters to broaden your results."
              : canWrite
                ? "Add the first company your team wants to qualify."
                : "A workspace editor has not added any companies yet."
          }
          action={
            canWrite && !hasFilters ? (
              <Link className="font-semibold text-cyan-800" href="/prospects/new">
                Add the first company
              </Link>
            ) : undefined
          }
        />
      ) : null}
      <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label="Companies">
        {items.map((company) => (
          <li key={company.id}>
            <Link
              className="block h-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm outline-none transition-colors hover:border-cyan-300 focus-visible:ring-2 focus-visible:ring-cyan-500"
              href={`/prospects/${company.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <h2 className="min-w-0 break-words text-lg font-semibold text-slate-950">
                  {company.name}
                </h2>
                {company.archived_at ? (
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                    Archived
                  </span>
                ) : null}
              </div>
              <p className="mt-3 text-sm text-slate-600">
                {[company.industry, company.country_code].filter(Boolean).join(" · ") ||
                  "Industry and country not set"}
              </p>
              {websiteHost(company.website_url) ? (
                <p className="mt-2 break-all text-sm text-cyan-800">
                  {websiteHost(company.website_url)}
                </p>
              ) : null}
              <p className="mt-5 text-xs font-medium uppercase tracking-wider text-slate-400">
                Updated {new Date(company.updated_at).toLocaleDateString()}
              </p>
            </Link>
          </li>
        ))}
      </ul>
      {nextCursor ? (
        <button
          className="min-h-11 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold disabled:opacity-60"
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
