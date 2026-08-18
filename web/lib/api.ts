/**
 * Typed client for the FastAPI backend (src/rag/api.py).
 *
 * Every session-scoped call carries an `X-Session-Id` header. The id lives in
 * sessionStorage, so API keys entered in one tab stay bound to that tab and are
 * gone when it closes — the browser half of ADR-012.
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  resources: {
    peakCpuPercent: number | null;
    peakRamMb: number | null;
    gpuVramMb: number | null;
  } | null;
};

export type Model = {
  id: string;
  label: string;
  provider: string;
  local: boolean;
  contextTokens: number | null;
};

export type ProviderStatus = {
  provider: string;
  configured: boolean;
  masked: string;
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
  peakCpuPercent: number | null;
  peakRamMb: number | null;
  gpuVramMb: number | null;
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
  peakCpuPercent: number | null;
  peakRamMb: number | null;
};

export type EvalRow = {
  modelId: string;
  cases: number;
  citationRate: number | null;
  sourceAccuracy: number | null;
  evidenceHit: number | null;
  refusalAccuracy: number | null;
  avgLatencyMs: number | null;
  totalCostUsd: number | null;
  unpricedRuns: number;
};

export type OllamaModel = { name: string; sizeBytes: number | null };

function sessionId(): string {
  if (typeof window === "undefined") return "server";
  let id = sessionStorage.getItem("rag-session-id");
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem("rag-session-id", id);
  }
  return id;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": sessionId(),
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
    call<{ models: Model[]; activeId: string | null; ollamaAvailable: boolean }>(
      "/api/models",
    ),

  setActiveModel: (modelId: string) =>
    call<{ activeId: string; priced: boolean }>("/api/models/active", {
      method: "POST",
      body: JSON.stringify({ modelId }),
    }),

  providers: () => call<{ providers: ProviderStatus[] }>("/api/keys"),

  saveKey: (provider: string, key: string) =>
    call<{ providers: ProviderStatus[] }>("/api/keys", {
      method: "POST",
      body: JSON.stringify({ provider, key }),
    }),

  ollama: () =>
    call<{ available: boolean; baseUrl: string; models: OllamaModel[] }>(
      "/api/ollama",
    ),

  pullModel: (name: string) =>
    call<{ ok: boolean }>("/api/ollama/pull", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  deleteModel: (name: string) =>
    call<{ ok: boolean }>("/api/ollama/delete", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  metrics: () =>
    call<{ summaries: ModelSummary[]; runs: RunRecord[] }>("/api/metrics"),

  clearMetrics: () => call<{ ok: boolean }>("/api/metrics", { method: "DELETE" }),

  evalCases: () => call<{ count: number }>("/api/evaluation/cases"),

  evalEstimate: (modelIds: string[]) =>
    call<{ cases: number; knownCostUsd: number; unpricedModels: string[] }>(
      "/api/evaluation/estimate",
      { method: "POST", body: JSON.stringify({ modelIds }) },
    ),

  runEvaluation: (modelIds: string[]) =>
    call<{ results: EvalRow[] }>("/api/evaluation/run", {
      method: "POST",
      body: JSON.stringify({ modelIds }),
    }),
};
