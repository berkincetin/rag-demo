import { beforeAll, describe, expect, it, vi } from "vitest";

beforeAll(() => {
  process.env.SESSION_SECRET = "test-secret-at-least-32-characters-long";
  process.env.BACKEND_URL = "http://backend:8000";
  process.env.INTERNAL_TOKEN = "internal-secret";
});

describe("session tokens", () => {
  it("round-trips a username", async () => {
    const { createSessionToken, verifySessionToken } = await import("../lib/auth");

    const session = await verifySessionToken(await createSessionToken("demo"));

    expect(session?.username).toBe("demo");
  });

  it("mints a unique session id per login", async () => {
    const { createSessionToken, verifySessionToken } = await import("../lib/auth");

    const first = await verifySessionToken(await createSessionToken("demo"));
    const second = await verifySessionToken(await createSessionToken("demo"));

    expect(first?.sid).toBeTruthy();
    expect(first?.sid).not.toBe(second?.sid);
  });

  it("rejects a tampered token", async () => {
    const { createSessionToken, verifySessionToken } = await import("../lib/auth");

    const token = await createSessionToken("demo");

    expect(await verifySessionToken(token.slice(0, -4) + "aaaa")).toBeNull();
  });

  it("rejects a token signed with a different secret", async () => {
    const { SignJWT } = await import("jose");
    const { verifySessionToken } = await import("../lib/auth");

    const foreign = await new SignJWT({ sid: "x", username: "demo" })
      .setProtectedHeader({ alg: "HS256" })
      .setExpirationTime("8h")
      .sign(new TextEncoder().encode("a-completely-different-secret-value-x"));

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

  it("rejects garbage and empty input", async () => {
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

  it("rejects rather than throwing when the hash is missing", async () => {
    const { verifyPassword } = await import("../lib/auth");

    await expect(verifyPassword("x", "")).resolves.toBe(false);
  });
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
  const { NextRequest } = await import("next/server");

  const request = new NextRequest(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...extraHeaders },
    body: JSON.stringify({ question: "soru" }),
  });
  request.cookies.set(SESSION_COOKIE, await createSessionToken("demo"));
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

  it("attaches the internal token the browser never sees", async () => {
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

  it("refuses to proxy endpoints outside the allow-list", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/keys");
    const response = await POST(request, { params: Promise.resolve({ path: ["api", "keys"] }) });

    expect(response.status).toBe(404);
    expect(calls).toHaveLength(0);
  });
});

describe("proxy transport", () => {
  it("forwards a streaming response without buffering", async () => {
    const encoder = new TextEncoder();
    const upstream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"start"}\n\n'));
        controller.close();
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(upstream, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          }),
      ),
    );
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/ask/stream");
    const response = await POST(request, {
      params: Promise.resolve({ path: ["api", "ask", "stream"] }),
    });

    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    expect(response.body).not.toBeNull();
  });

  it("allows the upload endpoint through", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/documents/upload");
    const response = await POST(request, {
      params: Promise.resolve({ path: ["api", "documents", "upload"] }),
    });

    expect(response.status).toBe(200);
    expect(calls).toHaveLength(1);
  });

  it("preserves the multipart content type so the boundary survives", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");
    const { createSessionToken, SESSION_COOKIE } = await import("../lib/auth");
    const { NextRequest } = await import("next/server");

    const boundary = "multipart/form-data; boundary=----abc123";
    const request = new NextRequest("http://localhost:3000/api/proxy/api/documents/upload", {
      method: "POST",
      headers: { "Content-Type": boundary },
      body: "irrelevant",
    });
    request.cookies.set(SESSION_COOKIE, await createSessionToken("demo"));
    await POST(request, { params: Promise.resolve({ path: ["api", "documents", "upload"] }) });

    expect(new Headers(calls[0].init.headers).get("Content-Type")).toBe(boundary);
  });

  it("supports DELETE and carries the query string upstream", async () => {
    const calls = stubFetch();
    const { DELETE } = await import("../app/api/proxy/[...path]/route");
    const { createSessionToken, SESSION_COOKIE } = await import("../lib/auth");
    const { NextRequest } = await import("next/server");

    const request = new NextRequest(
      "http://localhost:3000/api/proxy/api/documents?conversation_id=c1&filename=a.txt",
      { method: "DELETE" },
    );
    request.cookies.set(SESSION_COOKIE, await createSessionToken("demo"));
    const response = await DELETE(request, {
      params: Promise.resolve({ path: ["api", "documents"] }),
    });

    expect(response.status).toBe(200);
    expect(calls[0].url).toContain("conversation_id=c1");
    expect(calls[0].url).toContain("filename=a.txt");
  });

  it("still refuses an endpoint outside the allow-list", async () => {
    const calls = stubFetch();
    const { POST } = await import("../app/api/proxy/[...path]/route");

    const request = await authedRequest("http://localhost:3000/api/proxy/api/secret");
    const response = await POST(request, { params: Promise.resolve({ path: ["api", "secret"] }) });

    expect(response.status).toBe(404);
    expect(calls).toHaveLength(0);
  });

  it("requires a session for DELETE too", async () => {
    const calls = stubFetch();
    const { DELETE } = await import("../app/api/proxy/[...path]/route");
    const { NextRequest } = await import("next/server");

    const request = new NextRequest("http://localhost:3000/api/proxy/api/documents", {
      method: "DELETE",
    });
    const response = await DELETE(request, {
      params: Promise.resolve({ path: ["api", "documents"] }),
    });

    expect(response.status).toBe(401);
    expect(calls).toHaveLength(0);
  });
});
