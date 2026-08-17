/**
 * Login. Runs on the Node runtime because bcrypt cannot run on Edge.
 *
 * Failures return one generic message: distinguishing "unknown user" from
 * "wrong password" tells an attacker which half to keep guessing. The bcrypt
 * comparison also runs even when the username is wrong, so response time does
 * not reveal which field failed.
 */

import { NextRequest, NextResponse } from "next/server";

import { SESSION_COOKIE, createSessionToken, verifyPassword } from "@/lib/auth";

export const runtime = "nodejs";

const WINDOW_MS = 60_000;
const MAX_ATTEMPTS = 5;

// Per-replica, in memory. Effective at this deployment's scale; a shared store
// would be needed for a guarantee across replicas.
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

  const hashOk = await verifyPassword(String(password ?? ""), expectedHash).catch(() => false);
  const userOk = typeof username === "string" && username === expectedUser;

  if (!userOk || !hashOk) {
    record(ip);
    return NextResponse.json({ error: "Kullanıcı adı veya parola hatalı." }, { status: 401 });
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
