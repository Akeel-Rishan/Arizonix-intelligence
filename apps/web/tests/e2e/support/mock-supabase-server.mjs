import { createServer } from "node:http";
import { generateKeyPairSync, sign } from "node:crypto";

const host = "127.0.0.1";
const port = 54321;
const issuer = `http://${host}:${port}/auth/v1`;
const kid = "arizonix-test-key";
const userId = "1309ec68-70d6-47e8-9dc2-bd9d73177a84";
const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const publicJwk = publicKey.export({ format: "jwk" });
const counts = { login: 0, refresh: 0, signup: 0, verify: 0, logout: 0 };

function encode(value) {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function accessToken(email = "analyst@example.com") {
  const now = Math.floor(Date.now() / 1000);
  const header = encode({ alg: "RS256", typ: "JWT", kid });
  const payload = encode({
    iss: issuer,
    aud: "authenticated",
    sub: userId,
    email,
    role: "authenticated",
    iat: now,
    exp: now + 3600,
  });
  const signature = sign("RSA-SHA256", Buffer.from(`${header}.${payload}`), privateKey).toString(
    "base64url",
  );
  return `${header}.${payload}.${signature}`;
}

function user(email = "analyst@example.com") {
  const timestamp = new Date().toISOString();
  return {
    id: userId,
    aud: "authenticated",
    role: "authenticated",
    email,
    email_confirmed_at: timestamp,
    phone: "",
    confirmed_at: timestamp,
    last_sign_in_at: timestamp,
    app_metadata: { provider: "email", providers: ["email"] },
    user_metadata: {},
    identities: [],
    created_at: timestamp,
    updated_at: timestamp,
    is_anonymous: false,
  };
}

function session(email = "analyst@example.com") {
  return {
    access_token: accessToken(email),
    token_type: "bearer",
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    refresh_token: "test-refresh-token",
    user: user(email),
  };
}

function json(response, status, body) {
  response.writeHead(status, {
    "content-type": "application/json",
    "cache-control": "no-store",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "authorization, apikey, content-type, x-client-info",
    "access-control-allow-methods": "GET, POST, OPTIONS",
    connection: "close",
  });
  response.end(JSON.stringify(body));
}

async function body(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString("utf8");
  try {
    return JSON.parse(text || "{}");
  } catch {
    return {};
  }
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", issuer);
  if (request.method === "OPTIONS") {
    response.writeHead(204, {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "authorization, apikey, content-type, x-client-info",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      connection: "close",
    });
    return response.end();
  }
  if (request.method === "GET" && url.pathname === "/health")
    return json(response, 200, { ok: true });
  if (request.method === "GET" && url.pathname === "/auth/v1/.well-known/jwks.json") {
    return json(response, 200, {
      keys: [{ ...publicJwk, kid, use: "sig", alg: "RS256" }],
    });
  }
  if (request.method === "POST" && url.pathname === "/test/reset") {
    Object.keys(counts).forEach((key) => {
      counts[key] = 0;
    });
    return json(response, 200, counts);
  }
  if (request.method === "GET" && url.pathname === "/test/counts")
    return json(response, 200, counts);

  const payload = await body(request);
  if (
    request.method === "POST" &&
    url.pathname === "/auth/v1/token" &&
    url.searchParams.get("grant_type") === "password"
  ) {
    counts.login += 1;
    if (payload.email !== "analyst@example.com" || payload.password !== "correct-password") {
      return json(response, 400, {
        code: "invalid_credentials",
        message: "Invalid login credentials",
      });
    }
    return json(response, 200, session(payload.email));
  }
  if (
    request.method === "POST" &&
    url.pathname === "/auth/v1/token" &&
    url.searchParams.get("grant_type") === "refresh_token"
  ) {
    counts.refresh += 1;
    return json(response, 200, session());
  }
  if (request.method === "POST" && url.pathname === "/auth/v1/signup") {
    counts.signup += 1;
    await new Promise((resolve) => setTimeout(resolve, 250));
    return json(response, 200, { user: user(payload.email), session: null });
  }
  if (request.method === "POST" && url.pathname === "/auth/v1/verify") {
    counts.verify += 1;
    if (payload.token_hash === "valid-token") return json(response, 200, session());
    return json(response, 403, { code: "otp_expired", message: "Token has expired" });
  }
  if (request.method === "POST" && url.pathname === "/auth/v1/logout") {
    counts.logout += 1;
    response.writeHead(204, { "cache-control": "no-store", connection: "close" });
    return response.end();
  }
  return json(response, 404, { message: "Not found" });
});

server.listen(port, host, () => process.stdout.write(`mock Supabase listening on ${issuer}\n`));

function close() {
  server.closeAllConnections();
  server.close(() => process.exit(0));
}
process.on("SIGINT", close);
process.on("SIGTERM", close);
