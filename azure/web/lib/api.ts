/**
 * Typed client for the backend, reached through the Next.js proxy.
 *
 * The backend has internal ingress on Azure, so the browser cannot call it
 * directly — every request goes to /api/proxy, which attaches the internal
 * token server-side.
 *
 * There is deliberately no `X-Session-Id` here. The proxy derives the session
 * id from the signed login cookie and overwrites anything the client sends;
 * minting it in the browser (as the local build does) let any caller address
 * another user's session by guessing an id.
 */

const BASE = "/api/proxy";

export type ToolCall = {
  name: string;
  arguments: Record<string, unknown>;
  chars: number;
  injected: boolean;
};

export type Answer = {
  text: string;
  citations: string[];
  grounded: boolean;
  toolTrace: ToolCall[];
  latencyMs: number;
  inputTokens: number | null;
  outputTokens: number | null;
  costUsd: number | null;
  modelId: string;
};

export type Model = {
  id: string;
  label: string;
  provider: string;
  local: boolean;
  contextTokens: number | null;
};

export type RunRecord = {
  ts: string | null;
  modelId: string;
  provider: string;
  question: string;
  latencyMs: number;
  inputTokens: number | null;
  outputTokens: number | null;
  costUsd: number | null;
  citationCount: number;
  gatePassed: boolean;
  toolCalls: number;
  repaired: boolean;
  turnIndex: number;
};

export type ModelSummary = {
  modelId: string;
  provider: string;
  runs: number;
  pricedRuns: number;
  avgLatencyMs: number;
  totalCostUsd: number | null;
  avgCitations: number;
  gatePassRate: number;
  totalInputTokens: number | null;
  totalOutputTokens: number | null;
};

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    // FastAPI puts the human-readable reason in `detail`; surface it verbatim
    // rather than a generic "request failed".
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body — keep the status line */
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  ask: (question: string, userName: string) =>
    call<Answer>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question, userName }),
    }),

  clearChat: () => call<{ ok: boolean }>("/api/chat/clear", { method: "POST" }),

  models: () =>
    call<{ models: Model[]; activeId: string | null }>(
      "/api/models",
    ),

  metrics: () =>
    call<{ summaries: ModelSummary[]; runs: RunRecord[] }>("/api/metrics"),
};
