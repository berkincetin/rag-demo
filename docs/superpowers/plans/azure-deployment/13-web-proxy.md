# Task 13: Server-Side Proxy

**Goal:** Route every backend call through a Next.js server handler that
attaches the internal token and substitutes the session id from the cookie.

**Files:**
- Create: `azure/web/app/api/proxy/[...path]/route.ts`
- Modify: `azure/web/lib/api.ts` (BASE → `/api/proxy`, drop client session id)
- Modify: `azure/web/app/page.tsx` (remove key/Ollama/evaluation UI, add logout)
- Create: `azure/web/__tests__/proxy.test.ts`
- Create: `azure/web/Dockerfile`

**Interfaces:**
- Consumes: `verifySessionToken`, `SESSION_COOKIE` (Task 12); the API contract (Task 10)
- Produces: the deployable `nobel-rag-web:local` image

---

## 🚨 The vulnerability this closes

`web/lib/api.ts` mints `X-Session-Id` in the browser and stores it in
`sessionStorage`. Any caller can send any id and read another session's chat
history. Network isolation does not fix this — the proxy would forward a
spoofed header just as faithfully.

**The proxy must overwrite `X-Session-Id` with the cookie's `sid`,** never
forward the client's value. This is the single most important line in the task.

- [ ] **Step 1: Write the failing tests**

Create `azure/web/__tests__/proxy.test.ts`:

```typescript
import { describe, expect, it, beforeAll, vi } from "vitest";

beforeAll(() => {
  process.env.SESSION_SECRET = "test-secret-at-least-32-characters-long";
  process.env.BACKEND_URL = "http://backend:8000";
  process.env.INTERNAL_TOKEN = "internal-secret";
});

/** Capture what the proxy sends upstream. */
function stubFetch() {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit) => {
      calls.push({ url, init });
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

async function authedRequest(url: string, extraHeaders: Record<string, string> = {}) {
  const { createSessionToken, SESSION_COOKIE } = await import("../lib/auth");
  const token = await createSessionToken("demo");
  const { NextRequest } = await import("next/server");

  const request = new NextRequest(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...extraHeaders },
    body: JSON.stringify({ question: "soru" }),
  });
  request.cookies.set(SESSION_COOKIE, token);
  return request;
}

describe("proxy", () => {
  it("ignores a client-supplied session id and uses the cookie's", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/ask", {
      "X-Session-Id": "attacker-controlled-id",
    });
    await POST(request, { params: Promise.resolve({ path: ["api", "ask"] }) });

    const sent = new Headers(calls[0].init.headers);
    expect(sent.get("X-Session-Id")).not.toBe("attacker-controlled-id");
    expect(sent.get("X-Session-Id")).toBeTruthy();
  });

  it("attaches the internal token", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/ask");
    await POST(request, { params: Promise.resolve({ path: ["api", "ask"] }) });

    expect(new Headers(calls[0].init.headers).get("X-Internal-Token")).toBe("internal-secret");
  });

  it("never calls the backend without a valid session", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");
    const { NextRequest } = await import("next/server");

    const request = new NextRequest("http://localhost:3000/api/proxy/api/ask", {
      method: "POST",
      body: JSON.stringify({ question: "soru" }),
    });
    const response = await POST(request, { params: Promise.resolve({ path: ["api", "ask"] }) });

    expect(response.status).toBe(401);
    expect(calls).toHaveLength(0);
  });

  it("refuses to proxy removed endpoints", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/keys");
    const response = await POST(request, { params: Promise.resolve({ path: ["api", "keys"] }) });

    expect(response.status).toBe(404);
    expect(calls).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `cd azure/web && npx vitest run proxy`
Expected: FAIL — cannot resolve the proxy route

- [ ] **Step 3: Write the proxy**

Create `azure/web/app/api/proxy/[...path]/route.ts`:

```typescript
/**
 * Server-side proxy to the internal backend.
 *
 * The backend has internal ingress, so the browser cannot reach it; every call
 * goes through here. Two things happen that a client could otherwise subvert:
 *
 * 1. `X-Session-Id` is taken from the signed cookie and OVERWRITES whatever the
 *    client sent. Without this, a caller could address another user's session
 *    by guessing an id — the header used to be minted in the browser.
 * 2. `X-Internal-Token` is attached here. The browser never sees it.
 */

import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, verifySessionToken } from "@/lib/auth";

export const runtime = "nodejs";

// Explicit allow-list: anything not named here cannot be reached, even if a
// future backend accidentally exposes it.
const ALLOWED = new Set(["api/ask", "api/chat/clear", "api/models", "api/metrics"]);

async function forward(request: NextRequest, path: string[]) {
  const session = await verifySessionToken(request.cookies.get(SESSION_COOKIE)?.value ?? "");
  if (!session) {
    return NextResponse.json({ error: "Oturum gerekli." }, { status: 401 });
  }

  const target = path.join("/");
  if (!ALLOWED.has(target)) {
    return NextResponse.json({ error: "Bulunamadı." }, { status: 404 });
  }

  const backend = process.env.BACKEND_URL ?? "";
  const body = request.method === "GET" ? undefined : await request.text();

  const response = await fetch(`${backend}/${target}`, {
    method: request.method,
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Token": process.env.INTERNAL_TOKEN ?? "",
      // Server-derived: the client's value is deliberately discarded.
      "X-Session-Id": session.sid,
    },
    body,
    cache: "no-store",
  });

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `cd azure/web && npx vitest run proxy`
Expected: 4 passed

- [ ] **Step 5: Rewrite the client**

In `azure/web/lib/api.ts`:

- Change `const BASE = ...` to `const BASE = "/api/proxy";`
- **Delete the `sessionId()` function** and the `X-Session-Id` header from
  `call()` — the proxy supplies it now. Leaving it would be harmless but
  misleading, and the test above proves it is ignored.
- Delete `providers`, `saveKey`, `ollama`, `pullModel`, `deleteModel`,
  `clearMetrics`, `evalCases`, `evalEstimate`, `runEvaluation`, and
  `setActiveModel`
- Delete the `ProviderStatus`, `OllamaModel` and `EvalRow` types
- Remove `resources` from the `Answer` type and
  `peakCpuPercent` / `peakRamMb` / `gpuVramMb` from `RunRecord` and
  `ModelSummary` — Task 9 dropped those columns

- [ ] **Step 6: Update the page**

In `azure/web/app/page.tsx`:

- Remove the provider/API-key panel, the Ollama panel, and the evaluation
  panel along with their state and handlers
- Keep the chat, the sources panel, the tool-trace table, and the metrics view
- Add a logout control that POSTs `/api/auth/logout` then navigates to `/login`
- Add the signed-in username somewhere unobtrusive

Verify nothing references the deleted client functions:

```bash
cd azure/web
grep -rn "saveKey\|pullModel\|runEvaluation\|clearMetrics\|setActiveModel\|providers(" app components lib || echo "clean"
npx tsc --noEmit
```

Expected: `clean`, then a clean type-check.

- [ ] **Step 7: Write the web Dockerfile**

Create `azure/web/Dockerfile`:

```dockerfile
# Next.js tier — the only publicly reachable container.
#
# No NEXT_PUBLIC_API_URL build arg: the browser calls same-origin /api/proxy,
# and the backend address is a server-side runtime variable. Baking a backend
# URL into client bundles would leak the internal hostname.

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
```

- [ ] **Step 8: Add security headers**

In `azure/web/next.config.ts`, keep `output: "standalone"` and add:

```typescript
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Strict-Transport-Security",
            value: "max-age=31536000; includeSubDomains",
          },
          {
            key: "Content-Security-Policy",
            value:
              "default-src 'self'; script-src 'self' 'unsafe-inline'; " +
              "style-src 'self' 'unsafe-inline'; img-src 'self' data:; " +
              "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
          },
        ],
      },
    ];
  },
```

`'unsafe-inline'` for scripts is required by Next's hydration payload. Note it
as a known relaxation rather than claiming a strict CSP.

- [ ] **Step 9: Build and verify the full stack locally**

```bash
docker build -t nobel-rag-web:local azure/web

docker network create nobel-test || true
docker run --rm -d --name nobel-api --network nobel-test \
  -e INTERNAL_TOKEN=internal-secret \
  -e AZURE_OPENAI_ENDPOINT="https://foundry-lab-hbc26.openai.azure.com/" \
  -e AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
  -e MIN_COSINE="$MIN_COSINE" -e MIN_BM25="$MIN_BM25" \
  nobel-rag-api:local

docker run --rm -d --name nobel-web --network nobel-test -p 3001:3000 \
  -e BACKEND_URL=http://nobel-api:8000 \
  -e INTERNAL_TOKEN=internal-secret \
  -e APP_USERNAME=demo -e APP_PASSWORD_HASH='<hash from Task 12>' \
  -e SESSION_SECRET='<32+ chars>' \
  nobel-rag-web:local

sleep 10
```

Verify:

```bash
# unauthenticated → redirected to login
curl -s -o /dev/null -w "anon: %{http_code} → %{redirect_url}\n" localhost:3001/
# proxy without a session → 401
curl -s -o /dev/null -w "proxy anon: %{http_code}\n" -X POST localhost:3001/api/proxy/api/ask \
  -H "Content-Type: application/json" -d '{"question":"test"}'
# login, then ask through the proxy
curl -s -c /tmp/jar -X POST localhost:3001/api/auth/login \
  -H "Content-Type: application/json" -d '{"username":"demo","password":"<parola>"}'
curl -s -b /tmp/jar -X POST localhost:3001/api/proxy/api/ask \
  -H "Content-Type: application/json" -d '{"question":"Araç yakıt limiti ne kadar?"}'
```

Expected: a redirect to `/login`, a 401 from the proxy, then an answer with
citations. Clean up:

```bash
docker stop nobel-api nobel-web; docker network rm nobel-test
```

- [ ] **Step 10: Confirm the original web app is untouched**

```bash
git status --short web/ src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 11: Commit**

```bash
git add azure/web
git commit -m "feat(azure): add server-side proxy with session substitution"
```
