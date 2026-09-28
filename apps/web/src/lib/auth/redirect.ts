const DEFAULT_DESTINATION = "/";
const AUTH_PATHS = ["/login", "/signup", "/check-email", "/auth"];

function decodeRepeatedly(value: string): string | null {
  let decoded = value;
  try {
    for (let index = 0; index < 3; index += 1) {
      const next = decodeURIComponent(decoded);
      if (next === decoded) return next;
      decoded = next;
    }
    return decoded;
  } catch {
    return null;
  }
}

export function safeRedirectPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return DEFAULT_DESTINATION;
  if (value.includes("\\") || /[\u0000-\u001f\u007f]/.test(value)) return DEFAULT_DESTINATION;

  const decoded = decodeRepeatedly(value);
  if (!decoded || decoded.startsWith("//") || decoded.includes("\\") || decoded.includes("#")) {
    return DEFAULT_DESTINATION;
  }

  let parsed: URL;
  try {
    parsed = new URL(value, "https://arizonix.invalid");
  } catch {
    return DEFAULT_DESTINATION;
  }
  if (parsed.origin !== "https://arizonix.invalid") return DEFAULT_DESTINATION;
  const pathname = parsed.pathname.toLowerCase();
  if (AUTH_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`))) {
    return DEFAULT_DESTINATION;
  }
  return `${parsed.pathname}${parsed.search}`;
}
