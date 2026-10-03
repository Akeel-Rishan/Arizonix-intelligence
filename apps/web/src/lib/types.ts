export type HealthResponse = {
  status: "ok";
  service: "arizonix-api";
  version: string;
};

export type HealthCheckState =
  | { kind: "loading" }
  | { kind: "healthy"; data: HealthResponse }
  | { kind: "error"; message: string };

export type MeResponse = {
  user_id: string;
  email: string | null;
};

export type WorkspaceRole = "owner" | "admin" | "analyst" | "viewer";

export type Workspace = {
  id: string;
  name: string;
  role: WorkspaceRole;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type WorkspacePage = {
  items: Workspace[];
  limit: number;
  offset: number;
  has_more: boolean;
};

export type WorkspaceMember = {
  user_id: string;
  email: string | null;
  role: WorkspaceRole;
  created_at: string;
  updated_at: string;
};

export type MemberPage = {
  items: WorkspaceMember[];
  limit: number;
  offset: number;
  has_more: boolean;
};

export type AuditAction =
  | "workspace.created"
  | "workspace.renamed"
  | "membership.added"
  | "membership.role_changed"
  | "membership.removed"
  | "membership.left"
  | "company.created"
  | "company.updated"
  | "company.archived"
  | "company.restored";

export type AuditEvent = {
  id: string;
  workspace_id: string;
  actor_user_id: string;
  action: AuditAction;
  target_type: "workspace" | "membership" | "company";
  target_id: string;
  occurred_at: string;
  request_id: string;
  event_schema_version: number;
  details: Record<string, unknown>;
};

export type AuditEventPage = {
  items: AuditEvent[];
  next_cursor: string | null;
};

export type CompanyArchiveFilter = "active" | "archived" | "all";

export type CompanyListItem = {
  id: string;
  workspace_id: string;
  name: string;
  website_url: string | null;
  industry: string | null;
  country_code: string | null;
  description: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  archived_by: string | null;
  version: number;
};

export type Company = CompanyListItem & { notes: string | null };

export type CompanyPage = {
  items: CompanyListItem[];
  next_cursor: string | null;
};

export type CompanyInput = {
  name: string;
  website_url: string | null;
  industry: string | null;
  country_code: string | null;
  description: string | null;
  notes: string | null;
};
