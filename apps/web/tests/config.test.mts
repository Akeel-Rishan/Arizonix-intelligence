import assert from "node:assert/strict";
import test from "node:test";

import {
  getPublicAuthConfig,
  PublicConfigurationError,
  parsePublicApiBaseUrl,
  parsePublicOrigin,
} from "../src/lib/config.ts";

test("public API URL uses the valid local default", () => {
  assert.equal(parsePublicApiBaseUrl(undefined), "http://127.0.0.1:8000");
});

test("public API URL normalizes a trailing slash", () => {
  assert.equal(parsePublicApiBaseUrl("https://api.example.test/"), "https://api.example.test");
});

test("public API URL rejects invalid protocols and path prefixes", () => {
  assert.throws(
    () => parsePublicApiBaseUrl("ftp://api.example.test"),
    (error: unknown) =>
      error instanceof PublicConfigurationError && error.message.includes("HTTP and HTTPS"),
  );
  assert.throws(
    () => parsePublicApiBaseUrl("https://api.example.test/api/v1"),
    (error: unknown) =>
      error instanceof PublicConfigurationError && error.message.includes("without credentials"),
  );
});

test("public auth origins accept only bare HTTP(S) origins", () => {
  assert.equal(
    parsePublicOrigin("https://project.supabase.co/", "NEXT_PUBLIC_SUPABASE_URL"),
    "https://project.supabase.co",
  );
  assert.throws(
    () => parsePublicOrigin("https://project.supabase.co/auth/v1", "NEXT_PUBLIC_SUPABASE_URL"),
    PublicConfigurationError,
  );
  assert.throws(
    () => parsePublicOrigin(undefined, "NEXT_PUBLIC_SUPABASE_URL"),
    /NEXT_PUBLIC_SUPABASE_URL is missing/,
  );
});

test("missing browser auth configuration fails with setup guidance", () => {
  const originalUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const originalKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  try {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    assert.throws(
      () => getPublicAuthConfig(),
      (error: unknown) =>
        error instanceof PublicConfigurationError && error.message.includes("not configured"),
    );
  } finally {
    if (originalUrl === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    else process.env.NEXT_PUBLIC_SUPABASE_URL = originalUrl;
    if (originalKey === undefined) delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
    else process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = originalKey;
  }
});
