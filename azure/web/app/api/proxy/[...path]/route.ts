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
