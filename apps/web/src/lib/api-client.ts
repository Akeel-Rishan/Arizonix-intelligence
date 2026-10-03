import type {
  HealthResponse,
  AuditAction,
  AuditEventPage,
  Company,
  CompanyArchiveFilter,
  CompanyInput,
  CompanyPage,
  MeResponse,
  MemberPage,
  Workspace,
  WorkspacePage,
  WorkspaceRole,
} from "@/lib/types";
import { parsePublicApiBaseUrl, PublicConfigurationError } from "@/lib/config";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

const REQUEST_TIMEOUT_MS = 5_000;

export class HealthCheckError extends Error {
  constructor(public readonly userMessage: string) {
    super(userMessage);
    this.name = "HealthCheckError";
  }
}

export class IdentityRequestError extends Error {
  constructor(
    public readonly kind: "authentication" | "configuration" | "unavailable" | "invalid-response",
    public readonly userMessage: string,
  ) {
    super(userMessage);
    this.name = "IdentityRequestError";
  }
}

export class WorkspaceApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly userMessage: string,
  ) {
    super(userMessage);
    this.name = "WorkspaceApiError";
  }
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    candidate.service === "arizonix-api" &&
    typeof candidate.version === "string" &&
    candidate.version.length > 0
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort("timeout"), REQUEST_TIMEOUT_MS);
  const abortFromCaller = () => timeoutController.abort("cancelled");
  signal?.addEventListener("abort", abortFromCaller, { once: true });

  try {
    let apiBaseUrl: string;
    try {
      apiBaseUrl = parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
    } catch (error: unknown) {
      if (error instanceof PublicConfigurationError) {
        throw new HealthCheckError(error.userMessage);
      }
      throw error;
    }

    const response = await fetch(`${apiBaseUrl}/api/v1/health`, {
      headers: { Accept: "application/json" },
      method: "GET",
      signal: timeoutController.signal,
    });
    if (!response.ok) {
      throw new HealthCheckError("The API returned an error. Confirm it is running and retry.");
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new HealthCheckError(
        "The API response was not recognized. Check that both apps are current.",
      );
    }
    if (!isHealthResponse(payload)) {
      throw new HealthCheckError(
        "The API response was not recognized. Check that both apps are current.",
      );
    }
    return payload;
  } catch (error: unknown) {
    if (error instanceof HealthCheckError) throw error;
    if (timeoutController.signal.reason === "timeout") {
      throw new HealthCheckError("The API request timed out. Check the backend and retry.");
    }
    if (signal?.aborted) {
      throw error;
    }
    throw new HealthCheckError("The API could not be reached. Start the backend and retry.");
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", abortFromCaller);
  }
}

function isMeResponse(value: unknown): value is MeResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.user_id === "string" &&
    (typeof candidate.email === "string" || candidate.email === null)
  );
}

let refreshPromise: ReturnType<
  ReturnType<typeof createSupabaseBrowserClient>["auth"]["refreshSession"]
> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const supabase = createSupabaseBrowserClient();
  refreshPromise ??= supabase.auth.refreshSession().finally(() => {
    refreshPromise = null;
  });
  const { data, error } = await refreshPromise;
  if (error) return null;
  return data.session?.access_token ?? null;
}

async function requestMe(apiBaseUrl: string, accessToken: string, signal?: AbortSignal) {
  return fetch(`${apiBaseUrl}/api/v1/me`, {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
    signal,
  });
}

export async function fetchCurrentPrincipal(signal?: AbortSignal): Promise<MeResponse> {
  let apiBaseUrl: string;
  try {
    apiBaseUrl = parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) {
      throw new IdentityRequestError("configuration", error.userMessage);
    }
    throw error;
  }

  const supabase = createSupabaseBrowserClient();
  const { data } = await supabase.auth.getSession();
  let token = data.session?.access_token;
  if (!token) {
    throw new IdentityRequestError("authentication", "Your session has ended. Sign in again.");
  }

  let response: Response;
  try {
    response = await requestMe(apiBaseUrl, token, signal);
    if (response.status === 401) {
      token = (await refreshAccessToken()) ?? undefined;
      if (!token) {
        throw new IdentityRequestError("authentication", "Your session has ended. Sign in again.");
      }
      response = await requestMe(apiBaseUrl, token, signal);
    }
  } catch (error: unknown) {
    if (error instanceof IdentityRequestError || signal?.aborted) throw error;
    throw new IdentityRequestError("unavailable", "The identity service could not be reached.");
  }

  if (response.status === 401) {
    throw new IdentityRequestError("authentication", "Your session has ended. Sign in again.");
  }
  if (response.status === 503) {
    throw new IdentityRequestError(
      "unavailable",
      "Authentication verification is unavailable on the API.",
    );
  }
  if (!response.ok) {
    throw new IdentityRequestError("unavailable", "The identity service returned an error.");
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new IdentityRequestError("invalid-response", "The identity response was not recognized.");
  }
  if (!isMeResponse(payload)) {
    throw new IdentityRequestError("invalid-response", "The identity response was not recognized.");
  }
  return payload;
}

async function authenticatedRequest(
  path: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<Response> {
  let apiBaseUrl: string;
  try {
    apiBaseUrl = parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) {
      throw new WorkspaceApiError(0, "configuration", error.userMessage);
    }
    throw error;
  }
  const supabase = createSupabaseBrowserClient();
  const { data } = await supabase.auth.getSession();
  let token = data.session?.access_token;
  if (!token) throw new WorkspaceApiError(401, "authentication", "Your session has ended.");

  const request = (accessToken: string) =>
    fetch(`${apiBaseUrl}/api/v1${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
        Authorization: `Bearer ${accessToken}`,
      },
      cache: "no-store",
      signal,
    });
  let response: Response;
  try {
    response = await request(token);
    if (response.status === 401) {
      token = (await refreshAccessToken()) ?? undefined;
      if (!token) throw new WorkspaceApiError(401, "authentication", "Your session has ended.");
      response = await request(token);
    }
  } catch (error: unknown) {
    if (error instanceof WorkspaceApiError || signal?.aborted) throw error;
    throw new WorkspaceApiError(0, "unavailable", "The workspace service could not be reached.");
  }
  if (!response.ok) {
    let detail: { code?: string; message?: string } = {};
    try {
      const payload = (await response.json()) as { detail?: typeof detail };
      if (typeof payload.detail === "object" && payload.detail) detail = payload.detail;
    } catch {
      // The status still produces a controlled generic message.
    }
    throw new WorkspaceApiError(
      response.status,
      detail.code ?? "request_failed",
      detail.message ??
        (response.status === 401
          ? "Your session has ended."
          : "The workspace operation could not be completed."),
    );
  }
  return response;
}

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new WorkspaceApiError(502, "invalid_response", "The API response was not recognized.");
  }
}

export async function fetchWorkspaces(signal?: AbortSignal): Promise<WorkspacePage> {
  return readJson<WorkspacePage>(await authenticatedRequest("/workspaces?limit=100", {}, signal));
}

export async function createWorkspace(name: string): Promise<Workspace> {
  return readJson<Workspace>(
    await authenticatedRequest("/workspaces", { method: "POST", body: JSON.stringify({ name }) }),
  );
}

export async function renameWorkspace(workspaceId: string, name: string): Promise<Workspace> {
  return readJson<Workspace>(
    await authenticatedRequest(`/workspaces/${workspaceId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  );
}

export async function fetchWorkspaceMembers(
  workspaceId: string,
  signal?: AbortSignal,
): Promise<MemberPage> {
  return readJson<MemberPage>(
    await authenticatedRequest(`/workspaces/${workspaceId}/members?limit=100`, {}, signal),
  );
}

export async function addWorkspaceMember(
  workspaceId: string,
  userId: string,
  role: WorkspaceRole,
): Promise<void> {
  await authenticatedRequest(`/workspaces/${workspaceId}/members`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, role }),
  });
}

export async function updateWorkspaceMemberRole(
  workspaceId: string,
  userId: string,
  role: WorkspaceRole,
): Promise<void> {
  await authenticatedRequest(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export async function removeWorkspaceMember(workspaceId: string, userId: string): Promise<void> {
  await authenticatedRequest(`/workspaces/${workspaceId}/members/${userId}`, {
    method: "DELETE",
  });
}

export async function leaveWorkspace(workspaceId: string): Promise<void> {
  await authenticatedRequest(`/workspaces/${workspaceId}/leave`, { method: "POST" });
}

export type AuditEventFilters = {
  action?: AuditAction;
  occurredFrom?: string;
  occurredTo?: string;
};

export async function fetchAuditEvents(
  workspaceId: string,
  filters: AuditEventFilters,
  cursor?: string,
  signal?: AbortSignal,
): Promise<AuditEventPage> {
  const query = new URLSearchParams({ limit: "25" });
  if (filters.action) query.set("action", filters.action);
  if (filters.occurredFrom) query.set("occurred_from", filters.occurredFrom);
  if (filters.occurredTo) query.set("occurred_to", filters.occurredTo);
  if (cursor) query.set("cursor", cursor);
  return readJson<AuditEventPage>(
    await authenticatedRequest(
      `/workspaces/${workspaceId}/audit-events?${query.toString()}`,
      {},
      signal,
    ),
  );
}

export type CompanyFilters = {
  archive?: CompanyArchiveFilter;
  search?: string;
  industry?: string;
  countryCode?: string;
};

export async function fetchCompanies(
  workspaceId: string,
  filters: CompanyFilters,
  cursor?: string,
  signal?: AbortSignal,
): Promise<CompanyPage> {
  const query = new URLSearchParams({ limit: "25", archive: filters.archive ?? "active" });
  if (filters.search) query.set("search", filters.search);
  if (filters.industry) query.set("industry", filters.industry);
  if (filters.countryCode) query.set("country_code", filters.countryCode);
  if (cursor) query.set("cursor", cursor);
  return readJson<CompanyPage>(
    await authenticatedRequest(
      `/workspaces/${workspaceId}/companies?${query.toString()}`,
      {},
      signal,
    ),
  );
}

export async function fetchCompany(
  workspaceId: string,
  companyId: string,
  signal?: AbortSignal,
): Promise<Company> {
  return readJson<Company>(
    await authenticatedRequest(`/workspaces/${workspaceId}/companies/${companyId}`, {}, signal),
  );
}

export async function createCompany(workspaceId: string, input: CompanyInput): Promise<Company> {
  return readJson<Company>(
    await authenticatedRequest(`/workspaces/${workspaceId}/companies`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  );
}

export async function updateCompany(
  workspaceId: string,
  companyId: string,
  expectedVersion: number,
  input: CompanyInput,
): Promise<Company> {
  return readJson<Company>(
    await authenticatedRequest(`/workspaces/${workspaceId}/companies/${companyId}`, {
      method: "PATCH",
      body: JSON.stringify({ expected_version: expectedVersion, ...input }),
    }),
  );
}

async function changeCompanyArchiveState(
  workspaceId: string,
  companyId: string,
  expectedVersion: number,
  action: "archive" | "restore",
): Promise<Company> {
  return readJson<Company>(
    await authenticatedRequest(`/workspaces/${workspaceId}/companies/${companyId}/${action}`, {
      method: "POST",
      body: JSON.stringify({ expected_version: expectedVersion }),
    }),
  );
}

export function archiveCompany(workspaceId: string, companyId: string, expectedVersion: number) {
  return changeCompanyArchiveState(workspaceId, companyId, expectedVersion, "archive");
}

export function restoreCompany(workspaceId: string, companyId: string, expectedVersion: number) {
  return changeCompanyArchiveState(workspaceId, companyId, expectedVersion, "restore");
}
