"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchHealth, HealthCheckError } from "@/lib/api-client";
import type { HealthCheckState } from "@/lib/types";

export function ApiHealthCard() {
  const [state, setState] = useState<HealthCheckState>({ kind: "loading" });
  const requestRef = useRef<AbortController | null>(null);

  const runCheck = useCallback(async () => {
    if (requestRef.current) return;
    const controller = new AbortController();
    requestRef.current = controller;
    setState({ kind: "loading" });

    try {
      const data = await fetchHealth(controller.signal);
      setState({ kind: "healthy", data });
    } catch (error: unknown) {
      if (controller.signal.aborted) return;
      const message =
        error instanceof HealthCheckError
          ? error.userMessage
          : "The API status could not be checked. Start the backend and retry.";
      setState({ kind: "error", message });
    } finally {
      if (requestRef.current === controller) requestRef.current = null;
    }
  }, []);

  useEffect(() => {
    const initialCheck = window.setTimeout(() => void runCheck(), 0);
    return () => {
      window.clearTimeout(initialCheck);
      requestRef.current?.abort();
    };
  }, [runCheck]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-7" aria-labelledby="api-health-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-cyan-800">System connection</p>
          <h2 id="api-health-title" className="mt-1 text-xl font-semibold tracking-[-0.02em] text-slate-950">API health</h2>
        </div>
        <StatusBadge state={state} />
      </div>

      <div className="mt-7 min-h-24" aria-live="polite" aria-atomic="true">
        {state.kind === "loading" ? (
          <div data-testid="health-loading">
            <p className="font-medium text-slate-800">Checking the local API</p>
            <div className="mt-4 h-2 w-full max-w-xs overflow-hidden rounded-full bg-slate-100">
              <div className="h-full w-2/5 animate-pulse rounded-full bg-cyan-600 motion-reduce:animate-none" />
            </div>
          </div>
        ) : null}

        {state.kind === "healthy" ? (
          <div data-testid="health-success">
            <p className="font-medium text-slate-950">Connected to {state.data.service}</p>
            <p className="mt-1 text-sm text-slate-600">Liveness check passed. API version {state.data.version}.</p>
          </div>
        ) : null}

        {state.kind === "error" ? (
          <div data-testid="health-error">
            <p className="font-medium text-slate-950">Connection needs attention</p>
            <p className="mt-1 max-w-xl text-sm leading-6 text-slate-600">{state.message}</p>
            <button
              className="mt-5 min-h-11 rounded-xl bg-slate-950 px-5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-60"
              onClick={() => void runCheck()}
              type="button"
            >
              Retry connection
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function StatusBadge({ state }: { state: HealthCheckState }) {
  const label = state.kind === "healthy" ? "Healthy" : state.kind === "error" ? "Unavailable" : "Checking";
  const styles =
    state.kind === "healthy"
      ? "border-cyan-300 bg-cyan-50 text-cyan-900"
      : state.kind === "error"
        ? "border-rose-200 bg-rose-50 text-rose-800"
        : "border-slate-200 bg-slate-100 text-slate-600";

  return <span className={`rounded-lg border px-3 py-1.5 text-xs font-bold uppercase tracking-wider ${styles}`}>{label}</span>;
}
