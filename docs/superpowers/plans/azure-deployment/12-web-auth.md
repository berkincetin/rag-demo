# Task 12: Web Authentication

**Goal:** Login with a bcrypt-hashed password, a signed JWT session cookie, and
middleware that blocks every unauthenticated route.

**Files:**
- Create: `azure/web/` (copy of `web/`)
- Create: `azure/web/lib/auth.ts`
- Create: `azure/web/app/login/page.tsx`
- Create: `azure/web/app/api/auth/login/route.ts`
- Create: `azure/web/app/api/auth/logout/route.ts`
- Create: `azure/web/middleware.ts`
- Create: `azure/web/__tests__/auth.test.ts`
- Modify: `azure/web/package.json` (add `jose`, `bcryptjs`, `vitest`)

**Interfaces:**
- Consumes: nothing from the Python side
- Produces:
  ```typescript
  // lib/auth.ts
  export type Session = { sid: string; username: string };
  export async function createSessionToken(username: string): Promise<string>;
  export async function verifySessionToken(token: string): Promise<Session | null>;
  export async function verifyPassword(plain: string, hash: string): Promise<boolean>;
  export const SESSION_COOKIE = "nobel_session";
  ```

---

## 🚨 The runtime split that breaks naive implementations

Next.js middleware runs on the **Edge runtime**, which has no Node crypto and
cannot run `bcryptjs` or `jsonwebtoken`. Getting this wrong produces a build
that works locally with `next dev` and fails in the container.

| Concern | Library | Runtime |
|---|---|---|
| JWT sign/verify | `jose` (Web Crypto) | Edge **and** Node |
| bcrypt compare | `bcryptjs` | Node only |

So: middleware verifies the JWT with `jose`; the login route handler does the
bcrypt comparison and declares `export const runtime = "nodejs"`.

- [ ] **Step 1: Copy the web app**

```bash
cp -r web azure/web
rm -rf azure/web/node_modules azure/web/.next azure/web/tsconfig.tsbuildinfo
```

- [ ] **Step 2: Add the dependencies**

```bash
cd azure/web
npm install jose bcryptjs
npm install --save-dev vitest @types/bcryptjs
cd ../..
```

Add to `azure/web/package.json` scripts:

```json
"test": "vitest run"
```

> ⚠️ **Controller ruling (pre-flight scan).** The route handlers import
> `@/lib/auth`. Without a path alias, vitest cannot resolve that module and
> the security tests in this task and Task 13 will not run at all.

Create `azure/web/vitest.config.ts`:

```typescript
import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Mirrors the "@/*" path mapping in tsconfig.json; without it the route
    // handlers under test cannot resolve their own imports.
    alias: { "@": path.resolve(__dirname, ".") },
  },
  test: {
    environment: "node",
  },
});
```

Confirm `tsconfig.json` maps `@/*` to `./*`; if it maps somewhere else, match
that path here instead.

- [ ] **Step 3: Write the failing tests**

Create `azure/web/__tests__/auth.test.ts`:

```typescript
import { describe, expect, it, beforeAll } from "vitest";

beforeAll(() => {
  process.env.SESSION_SECRET = "test-secret-at-least-32-characters-long";
});

describe("session tokens", () => {
  it("round-trips a username", async () => {
    const { createSessionToken, verifySessionToken } = await import("../lib/auth");

    const token = await createSessionToken("demo");
    const session = await verifySessionToken(token);

    expect(session?.username).toBe("demo");
  });

  it("mints a unique session id per login", async () => {
    const { createSessionToken, verifySessionToken } = await import("../lib/auth");

    const first = await verifySessionToken(await createSessionToken("demo"));
    const second = await verifySessionToken(await createSessionToken("demo"));

    expect(first?.sid).not.toBe(second?.sid);
  });

  it("rejects a tampered token", async () => {
    const { createSessionToken, verifySessionToken } = await import("../lib/auth");

    const token = await createSessionToken("demo");
    const tampered = token.slice(0, -4) + "aaaa";

    expect(await verifySessionToken(tampered)).toBeNull();
  });

  it("rejects a token signed with a different secret", async () => {
    const { SignJWT } = await import("jose");
    const { verifySessionToken } = await import("../lib/auth");

    const foreign = await new SignJWT({ sid: "x", username: "demo" })
      .setProtectedHeader({ alg: "HS256" })
      .setExpirationTime("8h")
      .sign(new TextEncoder().encode("a-completely-different-secret-value"));

    expect(await verifySessionToken(foreign)).toBeNull();
  });

  it("rejects an expired token", async () => {
    const { SignJWT } = await import("jose");
    const { verifySessionToken } = await import("../lib/auth");

    const expired = await new SignJWT({ sid: "x", username: "demo" })
      .setProtectedHeader({ alg: "HS256" })
      .setExpirationTime(Math.floor(Date.now() / 1000) - 60)
      .sign(new TextEncoder().encode(process.env.SESSION_SECRET!));

    expect(await verifySessionToken(expired)).toBeNull();
  });

  it("rejects garbage", async () => {
    const { verifySessionToken } = await import("../lib/auth");

    expect(await verifySessionToken("not-a-token")).toBeNull();
    expect(await verifySessionToken("")).toBeNull();
  });
});

describe("password verification", () => {
  it("accepts the correct password and rejects a wrong one", async () => {
    const bcrypt = await import("bcryptjs");
    const { verifyPassword } = await import("../lib/auth");

    const hash = bcrypt.hashSync("dogru-parola", 10);

    expect(await verifyPassword("dogru-parola", hash)).toBe(true);
    expect(await verifyPassword("yanlis-parola", hash)).toBe(false);
  });
});
```

- [ ] **Step 4: Run the tests and watch them fail**

Run: `cd azure/web && npx vitest run`
Expected: FAIL — cannot resolve `../lib/auth`

- [ ] **Step 5: Write the auth library**

Create `azure/web/lib/auth.ts`:

```typescript
/**
 * Session authentication.
 *
 * JWT work uses `jose` because middleware runs on the Edge runtime, where
 * Node's crypto — and therefore `jsonwebtoken` — is unavailable. bcrypt is
 * Node-only, so password comparison happens exclusively in route handlers
 * that declare `runtime = "nodejs"`.
 */

import { SignJWT, jwtVerify } from "jose";

export const SESSION_COOKIE = "nobel_session";
const SESSION_HOURS = 8;

export type Session = { sid: string; username: string };

function secret(): Uint8Array {
  const value = process.env.SESSION_SECRET;
  if (!value || value.length < 32) {
    throw new Error("SESSION_SECRET must be set and at least 32 characters");
  }
  return new TextEncoder().encode(value);
}

/** Mint a token carrying a fresh, server-generated session id. */
export async function createSessionToken(username: string): Promise<string> {
  return new SignJWT({ sid: crypto.randomUUID(), username })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_HOURS}h`)
    .sign(secret());
}

/** Verify a token. Returns null for anything invalid — never throws. */
export async function verifySessionToken(token: string): Promise<Session | null> {
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, secret(), { algorithms: ["HS256"] });
    const sid = payload.sid;
    const username = payload.username;
    if (typeof sid !== "string" || typeof username !== "string") return null;
    return { sid, username };
  } catch {
    return null;
  }
}

/** Node runtime only — bcrypt cannot run on Edge. */
export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  const bcrypt = await import("bcryptjs");
  return bcrypt.compare(plain, hash);
}
```

- [ ] **Step 6: Run the tests and verify they pass**

Run: `cd azure/web && npx vitest run`
Expected: 7 passed

- [ ] **Step 7: Write the login route**

Create `azure/web/app/api/auth/login/route.ts`:

```typescript
/**
 * Login. Runs on the Node runtime because bcrypt cannot run on Edge.
 *
 * Failures return one generic message: distinguishing "unknown user" from
 * "wrong password" tells an attacker which half to keep guessing.
 */

import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, createSessionToken, verifyPassword } from "@/lib/auth";

export const runtime = "nodejs";

const WINDOW_MS = 60_000;
const MAX_ATTEMPTS = 5;
const attempts = new Map<string, number[]>();

function throttled(ip: string): boolean {
  const now = Date.now();
  const recent = (attempts.get(ip) ?? []).filter((t) => now - t < WINDOW_MS);
  attempts.set(ip, recent);
  return recent.length >= MAX_ATTEMPTS;
}

function record(ip: string): void {
  attempts.set(ip, [...(attempts.get(ip) ?? []), Date.now()]);
}

export async function POST(request: NextRequest) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";

  if (throttled(ip)) {
    return NextResponse.json(
      { error: "Çok fazla deneme yapıldı. Bir dakika sonra tekrar deneyin." },
      { status: 429 },
    );
  }

  const { username, password } = await request.json().catch(() => ({}));
  const expectedUser = process.env.APP_USERNAME ?? "";
  const expectedHash = process.env.APP_PASSWORD_HASH ?? "";

  // Always run the hash comparison, even when the username is wrong, so the
  // response time does not reveal which field failed.
  const hashOk = await verifyPassword(String(password ?? ""), expectedHash).catch(() => false);
  const userOk = typeof username === "string" && username === expectedUser;

  if (!userOk || !hashOk) {
    record(ip);
    return NextResponse.json(
      { error: "Kullanıcı adı veya parola hatalı." },
      { status: 401 },
    );
  }

  const token = await createSessionToken(expectedUser);
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 8 * 60 * 60,
  });
  return response;
}
```

- [ ] **Step 8: Write the logout route**

Create `azure/web/app/api/auth/logout/route.ts`:

```typescript
import { NextResponse } from "next/server";

import { SESSION_COOKIE } from "@/lib/auth";

export const runtime = "nodejs";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  return response;
}
```

- [ ] **Step 9: Write the middleware**

Create `azure/web/middleware.ts`:

```typescript
/**
 * Route guard. Runs on the Edge runtime, so it uses `jose` only.
 *
 * Pages redirect to /login; API calls get a bare 401 so the client shows an
 * error instead of rendering an HTML login page into a JSON parser.
 */

import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, verifySessionToken } from "@/lib/auth";

const PUBLIC_PATHS = ["/login", "/api/auth/login"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`))) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE)?.value ?? "";
  const session = await verifySessionToken(token);

  if (!session) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Oturum gerekli." }, { status: 401 });
    }
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except Next's own assets and the favicon.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

- [ ] **Step 10: Write the login page**

Create `azure/web/app/login/page.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");

    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (response.ok) {
      // replace(), not push(): the login page must not sit in history behind
      // an authenticated page.
      router.replace("/");
      router.refresh();
      return;
    }

    const body = await response.json().catch(() => ({}));
    setError(body.error ?? "Giriş yapılamadı.");
    setBusy(false);
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form
        onSubmit={submit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-gray-200 p-6"
      >
        <h1 className="text-xl font-semibold">Belge Asistanı</h1>
        <p className="text-sm text-gray-500">Devam etmek için giriş yapın.</p>

        <div className="space-y-1">
          <label htmlFor="username" className="text-sm font-medium">
            Kullanıcı adı
          </label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium">
            Parola
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-black px-4 py-2 text-white disabled:opacity-50"
        >
          {busy ? "Giriş yapılıyor…" : "Giriş yap"}
        </button>
      </form>
    </main>
  );
}
```

Adjust the Tailwind classes to match `azure/web/app/page.tsx` if its palette
differs — the structure above is what matters.

- [ ] **Step 11: Generate a password hash**

```bash
cd azure/web
node -e "console.log(require('bcryptjs').hashSync(process.argv[1], 10))" "SEC-ILEN-PAROLA"
cd ../..
```

Store the hash — Task 14 puts it in a Container Apps secret. **Never commit
the plaintext or the hash.**

- [ ] **Step 12: Verify the guard manually**

```bash
cd azure/web
APP_USERNAME=demo APP_PASSWORD_HASH='<hash>' SESSION_SECRET='<32+ chars>' npm run dev
```

In another shell:

```bash
curl -s -o /dev/null -w "no cookie: %{http_code}\n" -L localhost:3000/
curl -s -o /dev/null -w "wrong password: %{http_code}\n" -X POST localhost:3000/api/auth/login \
  -H "Content-Type: application/json" -d '{"username":"demo","password":"yanlis"}'
curl -s -i -X POST localhost:3000/api/auth/login \
  -H "Content-Type: application/json" -d '{"username":"demo","password":"SEC-ILEN-PAROLA"}' | grep -i set-cookie
```

Expected: the unauthenticated request lands on `/login`, the wrong password
gives 401, and the correct one returns a `Set-Cookie` with `HttpOnly`.

- [ ] **Step 13: Confirm the original web app is untouched**

```bash
git status --short web/ src/ tests/
```

Expected: no output.

- [ ] **Step 14: Commit**

```bash
git add azure/web
git commit -m "feat(azure): add login, JWT sessions and route guard"
```
