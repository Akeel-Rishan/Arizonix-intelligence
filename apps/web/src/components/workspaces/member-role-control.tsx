"use client";

import type { WorkspaceRole } from "@/lib/types";

const allRoles: WorkspaceRole[] = ["owner", "admin", "analyst", "viewer"];

export function MemberRoleControl({
  actorRole,
  disabled,
  onChange,
  role,
  targetRole,
}: {
  actorRole: WorkspaceRole;
  disabled: boolean;
  onChange: (role: WorkspaceRole) => void;
  role: WorkspaceRole;
  targetRole: WorkspaceRole;
}) {
  const editable =
    actorRole === "owner" || (actorRole === "admin" && ["analyst", "viewer"].includes(targetRole));
  if (!editable) return <span className="capitalize text-sm font-semibold">{role}</span>;
  const options = actorRole === "owner" ? allRoles : (["analyst", "viewer"] as WorkspaceRole[]);
  return (
    <select
      aria-label="Member role"
      className="min-h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm capitalize outline-none focus-visible:ring-2 focus-visible:ring-cyan-500"
      disabled={disabled}
      onChange={(event) => onChange(event.target.value as WorkspaceRole)}
      value={role}
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}
