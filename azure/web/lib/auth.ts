/**
 * Session authentication.
 *
 * JWT work uses `jose` because middleware runs on the Edge runtime, where
 * Node's crypto — and therefore `jsonwebtoken` — is unavailable. bcrypt is
 * Node-only, so password comparison happens exclusively in route handlers
 * that declare `runtime = "nodejs"`. Getting this split wrong produces a build
 * that works under `next dev` and fails inside the container.
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
