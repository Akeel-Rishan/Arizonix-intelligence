import assert from "node:assert/strict";
import test from "node:test";

import { PublicConfigurationError, parsePublicApiBaseUrl } from "../src/lib/config.ts";

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
