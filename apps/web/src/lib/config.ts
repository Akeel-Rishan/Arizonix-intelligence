const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const DEFAULT_SITE_URL = "http://127.0.0.1:3000";

export type PublicConfig = {
  apiBaseUrl: string;
  siteUrl: string;
  supabaseUrl: string;
  supabasePublishableKey: string;
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

export function parsePublicOrigin(value: string | undefined, label: string): string {
  const candidate = value?.trim();
  if (!candidate) {
    throw new PublicConfigurationError(`${label} is missing.`);
  }
  let url: URL;
  try {
    url = new URL(candidate);
  } catch {
    throw new PublicConfigurationError(`${label} must be a valid HTTP(S) origin.`);
  }
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new PublicConfigurationError(
      `${label} must be an HTTP(S) origin without credentials, a path, query, or fragment.`,
    );
  }
  return url.origin;
}

export function getPublicAuthConfig(): Omit<PublicConfig, "apiBaseUrl"> {
  const supabasePublishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();
  if (!supabasePublishableKey) {
    throw new PublicConfigurationError(
      "Supabase authentication is not configured. Set NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
    );
  }
  return {
    siteUrl: parsePublicOrigin(
      process.env.NEXT_PUBLIC_SITE_URL ?? DEFAULT_SITE_URL,
      "NEXT_PUBLIC_SITE_URL",
    ),
    supabaseUrl: parsePublicOrigin(
      process.env.NEXT_PUBLIC_SUPABASE_URL,
      "NEXT_PUBLIC_SUPABASE_URL",
    ),
    supabasePublishableKey,
  };
}

export function getPublicConfig(): PublicConfig {
  return {
    apiBaseUrl: parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL),
    ...getPublicAuthConfig(),
  };
}
