/**
 * Server-side proxy to the internal backend.
 *
 * The backend has internal ingress, so the browser cannot reach it; every call
 * goes through here. Two things happen that a client could otherwise subvert:
 *
 * 1. `X-Session-Id` is taken from the signed cookie and OVERWRITES whatever the
 *    client sent. In the local build the browser minted this id itself, so any
 *    caller could address another user's session by guessing an id.
 * 2. `X-Internal-Token` is attached here. The browser never sees it.
 */

import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, verifySessionToken } from "@/lib/auth";

export const runtime = "nodejs";

// Explicit allow-list: anything not named here cannot be reached, even if the
// backend later grows an endpoint we did not intend to expose.
const ALLOWED = new Set([
  "api/ask",
  "api/ask/stream",
  "api/chat/clear",
  "api/models",
  "api/metrics",
  "api/summarize",
  "api/documents",
  "api/documents/upload",
]);

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
  // Query strings carry conversation_id and filename for the document endpoints.
  const query = request.nextUrl.search;

  const headers: Record<string, string> = {
    "X-Internal-Token": process.env.INTERNAL_TOKEN ?? "",
    // Server-derived: the client's value is deliberately discarded.
    "X-Session-Id": session.sid,
  };
  // Forwarded verbatim rather than forced to JSON: a multipart upload carries
  // its boundary in this header, and rewriting it makes the body unparseable.
  const incomingType = request.headers.get("content-type");
  if (incomingType) headers["Content-Type"] = incomingType;

  const hasBody = request.method !== "GET" && request.method !== "DELETE";

  const response = await fetch(`${backend}/${target}${query}`, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });

  const contentType = response.headers.get("Content-Type") ?? "application/json";

  // SSE must reach the browser as it arrives; buffering it into a string would
  // deliver the whole answer at once and defeat streaming entirely.
  if (contentType.startsWith("text/event-stream")) {
    return new NextResponse(response.body, {
      status: response.status,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  }

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: { "Content-Type": contentType },
  });
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}

export async function POST(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}

export async function DELETE(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}
