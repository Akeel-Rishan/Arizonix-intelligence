const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export type PublicConfig = {
  apiBaseUrl: string;
};

export class PublicConfigurationError extends Error {
  readonly userMessage: string;

  constructor(userMessage: string) {
    super(userMessage);
    this.name = "PublicConfigurationError";
    this.userMessage = userMessage;
  }
}

export function parsePublicApiBaseUrl(value: string | undefined): string {
  const candidate = (value ?? DEFAULT_API_BASE_URL).trim();
  let url: URL;

  try {
    url = new URL(candidate);
  } catch {
    throw new PublicConfigurationError(
      "The public API URL is invalid. Set NEXT_PUBLIC_API_BASE_URL to an HTTP(S) origin.",
    );
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new PublicConfigurationError(
      "The public API URL is invalid. Only HTTP and HTTPS URLs are supported.",
    );
  }
  if (url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
    throw new PublicConfigurationError(
      "The public API URL must be an origin without credentials, a path, query, or fragment.",
    );
  }

  return url.origin;
}

export function getPublicConfig(): PublicConfig {
  return {
    apiBaseUrl: parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
  };
}
