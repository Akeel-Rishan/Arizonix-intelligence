"use client";

import { type FormEvent, useState } from "react";

import type { AuditAction } from "@/lib/types";

export type AppliedAuditFilters = {
  action?: AuditAction;
  occurredFrom?: string;
  occurredTo?: string;
};

const actions: AuditAction[] = [
  "workspace.created",
  "workspace.renamed",
  "membership.added",
  "membership.role_changed",
  "membership.removed",
  "membership.left",
  "company.created",
  "company.updated",
  "company.archived",
  "company.restored",
];

export function AuditFilters({
  disabled,
  onApply,
}: {
  disabled: boolean;
  onApply: (filters: AppliedAuditFilters) => void;
}) {
  const [action, setAction] = useState<AuditAction | "">("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onApply({
      ...(action ? { action } : {}),
      ...(from && to
        ? {
            occurredFrom: `${from}T00:00:00.000Z`,
            occurredTo: `${to}T23:59:59.999Z`,
          }
        : {}),
    });
  };

  return (
    <form
      className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-4 lg:items-end"
      onSubmit={submit}
    >
      <label className="text-sm font-semibold text-slate-800">
        Action
        <select
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
          disabled={disabled}
          onChange={(event) => setAction(event.target.value as AuditAction | "")}
          value={action}
        >
          <option value="">All actions</option>
          {actions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-semibold text-slate-800">
        From date (UTC)
        <input
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
          disabled={disabled}
          onChange={(event) => setFrom(event.target.value)}
          type="date"
          value={from}
        />
      </label>
      <label className="text-sm font-semibold text-slate-800">
        To date (UTC)
        <input
          className="mt-2 min-h-11 w-full rounded-xl border border-slate-300 px-3 outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
          disabled={disabled}
          min={from || undefined}
          onChange={(event) => setTo(event.target.value)}
          type="date"
          value={to}
        />
      </label>
      <button
        className="min-h-11 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 disabled:opacity-60"
        disabled={disabled || Boolean(from) !== Boolean(to)}
        type="submit"
      >
        Apply filters
      </button>
    </form>
  );
}
