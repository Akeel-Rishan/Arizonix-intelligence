"use client";

import { useEffect, useState } from "react";

import { fetchCurrentPrincipal, IdentityRequestError } from "@/lib/api-client";
import type { MeResponse } from "@/lib/types";

type AccountState =
  | { kind: "loading" }
  | { kind: "ready"; principal: MeResponse }
  | { kind: "error"; message: string };

export function AccountCard() {
  const [state, setState] = useState<AccountState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();
    void fetchCurrentPrincipal(controller.signal)
      .then((principal) => setState({ kind: "ready", principal }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          kind: "error",
          message:
            error instanceof IdentityRequestError
              ? error.userMessage
              : "Account details are temporarily unavailable.",
        });
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-950">Account</h2>
      {state.kind === "loading" ? (
        <p className="mt-3 text-sm text-slate-600" aria-live="polite">
          Loading verified identity…
        </p>
      ) : state.kind === "error" ? (
        <div
          className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"
          role="status"
        >
          {state.message}
        </div>
      ) : (
        <dl className="mt-4 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">Email</dt>
            <dd className="mt-1 break-all text-sm text-slate-900">
              {state.principal.email ?? "Not provided"}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              User ID
            </dt>
            <dd className="mt-1 break-all font-mono text-xs text-slate-700">
              {state.principal.user_id}
            </dd>
          </div>
        </dl>
      )}
    </section>
  );
}
