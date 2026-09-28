import assert from "node:assert/strict";
import test from "node:test";

import { safeRedirectPath } from "../src/lib/auth/redirect.ts";

test("safe return destinations preserve local paths and queries", () => {
  assert.equal(safeRedirectPath("/settings?tab=account"), "/settings?tab=account");
  assert.equal(safeRedirectPath("/"), "/");
});

test("safe return destinations reject external, encoded, and auth-loop targets", () => {
  const unsafe = [
    "https://attacker.example",
    "//attacker.example/path",
    "/\\attacker.example",
    "/%5c%5cattacker.example",
    "/%255c%255cattacker.example",
    "/login?next=/settings",
    "/auth/confirm?token_hash=secret",
    "/settings#fragment",
    "/%E0%A4%A",
    "javascript:alert(1)",
  ];
  for (const destination of unsafe) {
    assert.equal(safeRedirectPath(destination), "/", destination);
  }
});
