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
