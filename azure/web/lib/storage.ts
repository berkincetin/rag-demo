/**
 * Conversations live in the browser, not on the server.
 *
 * The session holds N conversations but the backend keys memory by session, so
 * server-side state could not tell them apart. Browser storage also survives a
 * container restart, which server memory does not.
 */

import { Conversation } from "./types";

export const STORAGE_KEY = "nobel-rag-conversations";

export function newId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as Conversation[]) : [];
  } catch {
    return [];
  }
}

/** Returns an error message when the write failed, otherwise null. */
export function saveConversations(list: Conversation[]): string | null {
  if (typeof window === "undefined") return null;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
    return null;
  } catch {
    // Quota is the realistic cause. Say so rather than losing writes silently.
    return "Tarayıcı depolama alanı doldu. Eski sohbetleri silin.";
  }
}

export function createConversation(): Conversation {
  const now = Date.now();
  return {
    id: newId(),
    title: "Yeni sohbet",
    createdAt: now,
    updatedAt: now,
    documentName: null,
    messages: [],
    summary: null,
    summarizedUpTo: 0,
  };
}

export function generateTitle(text: string): string {
  const clean = text.trim().replace(/\s+/g, " ");
  return clean.length <= 40 ? clean : clean.slice(0, 40).trimEnd() + "…";
}

export function groupByDate(list: Conversation[]): { label: string; items: Conversation[] }[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86400000;

  const today: Conversation[] = [];
  const yesterday: Conversation[] = [];
  const older: Conversation[] = [];

  for (const item of list) {
    if (item.updatedAt >= startOfToday) today.push(item);
    else if (item.updatedAt >= startOfYesterday) yesterday.push(item);
    else older.push(item);
  }

  const groups: { label: string; items: Conversation[] }[] = [];
  if (today.length) groups.push({ label: "Bugün", items: today });
  if (yesterday.length) groups.push({ label: "Dün", items: yesterday });
  if (older.length) groups.push({ label: "Daha eski", items: older });
  return groups;
}
