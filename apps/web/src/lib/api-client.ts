import type { HealthResponse } from "@/lib/types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 5_000;

export class HealthCheckError extends Error {
  constructor(public readonly userMessage: string) {
    super(userMessage);
    this.name = "HealthCheckError";
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

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort("timeout"), REQUEST_TIMEOUT_MS);
  const abortFromCaller = () => timeoutController.abort("cancelled");
  signal?.addEventListener("abort", abortFromCaller, { once: true });

  try {
    const response = await fetch(`${getApiBaseUrl()}/api/v1/health`, {
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
      throw new HealthCheckError("The API response was not recognized. Check that both apps are current.");
    }
    if (!isHealthResponse(payload)) {
      throw new HealthCheckError("The API response was not recognized. Check that both apps are current.");
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
